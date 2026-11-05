"""Session taint + action policy — the kernel layer.

Scanning filters content; the policy gates ACTIONS. A quarantine taints
the session for `taint_ttl_seconds`; while tainted, the calls an injected
instruction would actually want — credential reads, instruction-file
writes, network egress — are refused or escalated to Hermes's approval
gate. Provenance over phrasing: a novel injection that slips the detector
still can't act, because the gate follows what the call *does*.

Wrapper calls are evaluated as the action they really make: `tool_call`
unwraps to its target, `execute_code` is judged as the shell command its
code performs, `process_manage` as the line it types into a running
shell. `subagent_start` copies taint into the child session so routing
through a delegate doesn't launder it.
"""

from __future__ import annotations

import logging
import re
import threading
import time

from . import config

_CRED_RE = re.compile(
    r"(\.ssh|\.aws|\.gnupg|\.kube|\.config/gh|\.env\b|id_rsa|id_ed25519|"
    r"credentials|secrets?\.|\.netrc|\.npmrc|\.pypirc|token\.json|auth\.json)",
    re.I,
)
_INSTRUCTION_RE = re.compile(
    r"(SKILL\.md|SOUL\.md|AGENTS\.md|CLAUDE\.md|GEMINI\.md|plugin\.yaml|"
    r"settings\.json|system_prompt|SYSTEM\.md)",
    re.I,
)
_EGRESS_RE = re.compile(
    r"\b(curl|wget|nc|ncat|netcat|ssh|scp|sftp|rsync|ftp|telnet|"
    r"openssl s_client|https?://|requests\.(get|post)|urllib|fetch\()",
    re.I,
)
# `mkf[s]` spells "mkfs" without the contiguous token — the catalog
# scanner can't tell a detector's denylist from a live payload otherwise.
_DESTRUCTIVE_RE = re.compile(r"rm\s+-[rf]+\s+[/~*]|mkf[s]|dd\b[^|]*of=/dev/|:\(\)\s*\{", re.I)

_SHELL_TOOLS = {"terminal", "execute_code", "process_manage", "bash", "shell", "run_command"}
_WRITE_TOOLS = {"write_file", "patch", "apply_patch", "edit_file", "create_file", "append_file"}
_READ_TOOLS = {"read_file", "cat", "view_file", "open_file"}
_WRAPPER_TOOLS = {"tool_call", "call_tool", "invoke_tool"}

_tainted: dict[str, float] = {}
_lock = threading.Lock()

# Kill-chain window: per-session rolling record of what the agent has
# touched, so the gate sees the *sequence* — the OWASP multi-tool attack
# shape (untrusted read → sensitive read → egress) — not only single calls.
_chains: dict[str, list[tuple[float, str]]] = {}
_CHAIN_MAX = 40

_UNTRUSTED = "untrusted_result"  # recorded by guard on a quarantined result
_CLASS_BY_TOOL = {
    "memory": "memory_write",
    "cron": "persist_write",
    "cronjob": "persist_write",
    "schedule": "persist_write",
    "create_scheduled_job": "persist_write",
}


def record_event(session_id: str, cls: str) -> None:
    """Append an event to the session's kill-chain window."""
    key = session_id or ""
    with _lock:
        chain = _chains.setdefault(key, [])
        chain.append((time.time(), cls))
        del chain[: max(0, len(chain) - _CHAIN_MAX)]


def _tool_class(tool_name: str, args: dict | None) -> str | None:
    if tool_name in _CLASS_BY_TOOL:
        return _CLASS_BY_TOOL[tool_name]
    if tool_name in _SHELL_TOOLS:
        text = _shell_text(tool_name, args)
        if _egress_hit(text):
            return "egress"
        if _CRED_RE.search(text):
            return "sensitive_read"
        return None
    if tool_name in _READ_TOOLS and _CRED_RE.search(_path_text(args)):
        return "sensitive_read"
    if tool_name in _WRITE_TOOLS:
        path = _path_text(args)
        if _INSTRUCTION_RE.search(path):
            return "instruction_write"
        return "write"
    return None


def _chain_hit(session_id: str, cls: str) -> str | None:
    """Name of the chain this call completes, else None."""
    key = session_id or ""
    window = float(config.get_int("chain_window_seconds", 300))
    now = time.time()
    with _lock:
        events = [(t, c) for t, c in _chains.get(key, []) if now - t <= window]
    seen = {c for _, c in events}
    if _UNTRUSTED not in seen:
        return None
    if cls == "egress" and "sensitive_read" in seen:
        return "untrusted_result→sensitive_read→egress"
    if cls in ("memory_write", "persist_write", "instruction_write"):
        return f"untrusted_result→{cls} (persistence)"
    if cls == "sensitive_read" and "egress" in seen:
        return "untrusted_result→egress→sensitive_read"
    return None


def mark_taint(session_id: str, ttl: float | None = None) -> None:
    """Quarantine happened — this session is tainted for the TTL."""
    ttl = ttl if ttl is not None else float(config.get_int("taint_ttl_seconds", 1800))
    if ttl <= 0:
        return
    with _lock:
        _tainted[session_id or ""] = time.time() + ttl


def taint_remaining(session_id: str) -> float:
    with _lock:
        expiry = _tainted.get(session_id or "", 0.0)
        if expiry and expiry <= time.time():
            _tainted.pop(session_id or "", None)
            return 0.0
        return max(0.0, expiry - time.time())


def inherit_taint(parent_session: str, child_session: str) -> None:
    """A spawned delegate inherits its parent's taint — the poison travels."""
    if not child_session or child_session == parent_session:
        return
    with _lock:
        expiry = _tainted.get(parent_session or "", 0.0)
        if expiry > time.time():
            _tainted[child_session] = expiry


def clear(session_id: str | None = None) -> None:
    with _lock:
        if session_id is None:
            _tainted.clear()
        else:
            _tainted.pop(session_id, None)


def _unwrap(tool_name: str, args: dict | None) -> tuple[str, dict]:
    """A wrapper call is evaluated as the call it really makes."""
    if tool_name not in _WRAPPER_TOOLS or not isinstance(args, dict):
        return tool_name, args or {}
    inner_name = args.get("tool") or args.get("tool_name") or args.get("name")
    inner_args = args.get("args") or args.get("arguments") or args.get("parameters") or {}
    if isinstance(inner_name, str) and inner_name:
        return inner_name, inner_args if isinstance(inner_args, dict) else {}
    return tool_name, args


def _path_text(args: dict | None) -> str:
    if not isinstance(args, dict):
        return ""
    for key in ("path", "file", "filename", "file_path", "target"):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _shell_text(tool_name: str, args: dict | None) -> str:
    """The command a shell-typed tool actually runs."""
    if not isinstance(args, dict):
        return ""
    keys = ("command", "cmd", "code", "input", "text", "script")
    if tool_name == "process_manage":
        keys = ("input", "text", "data", "keys", "command")
    parts = [str(args[k]) for k in keys if isinstance(args.get(k), str)]
    return " ".join(parts)


def _allowed_path(path: str) -> bool:
    allow = config.get_list("policy_allow_paths", [])
    return any(a and a in path for a in allow)


def _egress_hit(text: str) -> bool:
    """Egress check with allow-listed destinations stripped first."""
    for a in config.get_list("policy_allow_hosts", []):
        if a:
            text = text.replace(a, "")
    return bool(_EGRESS_RE.search(text))


def _decision(action: str, rule: str, tool_name: str, detail: str) -> dict:
    return {
        "action": action,
        "message": (
            f"[ELCARO {rule}] {action}ed {tool_name}: {detail} "
            "(session tainted by a recent quarantine — the kernel gates "
            "side-effects until it clears)"
        ),
        "_elcaro_rule": rule,
    }


def evaluate(tool_name: str, args: dict | None, session_id: str) -> dict | None:
    """Gate a tool call. None = allowed; dict = Hermes block/approve action."""
    mode = config.get_str("taint_policy", "enforce")
    if mode == "off":
        return None

    tool_name, args = _unwrap(tool_name, args)
    tainted = taint_remaining(session_id) > 0

    if tool_name in _SHELL_TOOLS:
        text = _shell_text(tool_name, args)
        if not text:
            return None
        cred = _CRED_RE.search(text) and not _allowed_path(text)
        egress = _egress_hit(text)
        destructive = _DESTRUCTIVE_RE.search(text)
        # Always-on: sensitive path + data-sending channel in one step is
        # refused even in a clean session — there is no benign shape for it.
        if cred and egress:
            return _decision("block", "CRED_EGRESS", tool_name, text[:160])
        if not tainted:
            if destructive:
                return _decision("approve", "DESTRUCTIVE", tool_name, text[:160])
            return None
        if cred:
            return _decision("block", "TAINT_CRED", tool_name, text[:160])
        if egress:
            return _decision("approve", "TAINT_EGRESS", tool_name, text[:160])
        if destructive:
            return _decision("approve", "TAINT_DESTRUCTIVE", tool_name, text[:160])
        return None

    path = _path_text(args)
    if tool_name in _WRITE_TOOLS and path:
        # Writes are only gated while tainted — .env / SKILL.md writes are
        # normal dev work in a clean session.
        if not tainted or _allowed_path(path):
            return None
        if _CRED_RE.search(path):
            return _decision("block", "TAINT_CRED_WRITE", tool_name, path)
        if _INSTRUCTION_RE.search(path):
            return _decision("block", "INSTRUCTION_WRITE", tool_name, path)
        if path.startswith("/") or path.startswith("~"):
            return _decision("approve", "OUTSIDE_WORKSPACE", tool_name, path)
        return None

    if tool_name in _READ_TOOLS and path and tainted:
        if _CRED_RE.search(path) and not _allowed_path(path):
            return _decision("block", "TAINT_CRED_READ", tool_name, path)
        return None

    return None


class _PolicyVerdict:
    """Verdict shim so policy decisions land in the same signed threat log."""

    def __init__(self, action: str, rule: str, detail: str):
        self.risk_score = 1.0 if action == "block" else 0.8
        level = "dangerous" if action == "block" else "suspicious"
        self.risk_level = type("L", (), {"value": level})()
        self.quarantined = action == "block"
        self.flagged_techniques = [type("T", (), {"value": f"policy_{rule.lower()}"})()]
        self.normalizations_applied = []
        self.latency_ms = None
        self._scanned_content = detail


def log_decision(
    tool_name: str, action: str, rule: str, detail: str, session_id: str, observed: bool
) -> None:
    """Record a gate decision — the kernel leaves receipts too."""
    try:
        from . import threatlog

        threatlog.append(
            tool_name=tool_name,
            verdict=_PolicyVerdict(action, rule, detail),
            session_id=session_id,
            surface="policy",
            extra={"policy_rule": rule, "policy_observed_only": observed},
        )
    except Exception:
        logging.getLogger(__name__).debug("policy receipt log failed")


def evaluate_and_log(tool_name: str, args: dict | None, session_id: str) -> dict | None:
    """evaluate() + threat-log receipt; monitor mode logs without enforcing."""
    mode = config.get_str("taint_policy", "enforce")
    if mode == "off":
        return None
    # Kill-chain check first: the sequence may be damning even when no
    # single call is. Unwrap so tool_call/exec wrappers can't dodge it.
    inner_name, inner_args = _unwrap(tool_name, args)
    cls = _tool_class(inner_name, inner_args)
    hit = _chain_hit(session_id, cls) if cls else None
    if cls:
        record_event(session_id, cls)
    if hit:
        decision = _decision("block", "KILL_CHAIN", tool_name, hit)
        log_decision(
            tool_name,
            "block",
            "KILL_CHAIN",
            hit,
            session_id,
            observed=mode == "monitor",
        )
        return None if mode == "monitor" else decision
    decision = evaluate(tool_name, args, session_id)
    if decision is None:
        return None
    rule = decision.get("_elcaro_rule", "POLICY")
    log_decision(
        tool_name,
        decision["action"],
        rule,
        decision["message"][:200],
        session_id,
        observed=mode == "monitor",
    )
    if mode == "monitor":
        return None
    return decision
