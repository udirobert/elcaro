"""Attack autopsy — reconstruct what a quarantined payload wanted.

Detection says "blocked." This answers the question the user actually
asks: what did it want, how far did it get, what should I fix? A second
deterministic pass over the flagged content and verdict — no LLM, no
network, sub-ms. Objective class, named targets, kill-chain stage, and
concealment methods land in the threat-log entry and the pane.
"""

from __future__ import annotations

import re
from typing import Any

_PATH_RE = re.compile(r"(?:~/[A-Za-z0-9._\-/]+|/[A-Za-z0-9._\-/]{3,}|[A-Za-z0-9._\-]+\.env)")
_HOST_RE = re.compile(r"https?://([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})")
_TOOL_REF_RE = re.compile(
    r"\b(write_file|read_file|terminal|execute_code|process_manage|tool_call|"
    r"memory|cron|schedule|delegate_task|browser_\w+|web_\w+)\b"
)

_CRED_HINT = re.compile(
    r"\.ssh|\.aws|\.gnupg|\.kube|\.env|id_rsa|id_ed25519|credential|secret|token|password|netrc",
    re.I,
)
_PERSIST_HINT = re.compile(
    r"SKILL\.md|SOUL\.md|AGENTS\.md|CLAUDE\.md|memory|cron|schedule|startup|rc file|profile",
    re.I,
)

# Technique name → attack objective. Names outside the map default to
# "steering" — most injection classes exist to redirect the agent.
_OBJECTIVE = {
    "credential_access": "exfiltration",
    "exfiltration": "exfiltration",
    "decoy_exfiltration": "exfiltration",
    "persistence": "persistence",
    "memory_write": "persistence",
    "reward_hack": "reward hack",
    "privilege_escalation": "privilege escalation",
    "sudo": "privilege escalation",
    "self_reference": "self propagation",
    "swarm_directive": "swarm steering",
}
_CONCEALMENT = {
    "obfuscation": "obfuscation",
    "invisible_unicode": "invisible unicode",
    "unicode": "invisible unicode",
    "base64": "base64 encoding",
    "homoglyph": "homoglyphs",
    "delimiter_escape": "delimiter tricks",
    "hidden_placement": "hidden placement",
    "fragmentation": "token splitting",
    "encoding": "encoding tricks",
    "conditional": "conditional triggers",
}


def _techniques(verdict: Any) -> list[str]:
    return [
        (t.value if hasattr(t, "value") else str(t)).lower()
        for t in getattr(verdict, "flagged_techniques", []) or []
    ]


def summarize(verdict: Any, scan_text: str) -> dict[str, Any]:
    """Build the autopsy report for a quarantined scan."""
    techs = _techniques(verdict)
    text = scan_text or ""

    paths = sorted({m.group(0) for m in _PATH_RE.finditer(text)})[:6]
    hosts = sorted({m.group(1).lower() for m in _HOST_RE.finditer(text)})[:6]
    tools = sorted({m.group(1) for m in _TOOL_REF_RE.finditer(text)})[:6]

    objective = next(
        (_OBJECTIVE[t] for t in techs if t in _OBJECTIVE),
        "exfiltration" if _CRED_HINT.search(text) else "steering",
    )
    concealment = sorted({_CONCEALMENT[t] for t in techs if t in _CONCEALMENT})
    cred = any(_CRED_HINT.search(p) for p in paths) or _CRED_HINT.search(text)
    persist = bool(_PERSIST_HINT.search(text)) or any(
        t in ("persistence", "memory_write") for t in techs
    )
    stage = (
        "exfil"
        if (cred and hosts)
        else "persist"
        if persist
        else "steer"
        if tools or techs
        else "recon"
    )

    wanted_bits = []
    if objective == "exfiltration" and cred:
        wanted_bits.append(f"exfil {paths[0] if paths else 'credentials'}")
        if hosts:
            wanted_bits.append(f"→ {hosts[0]}")
    elif objective == "persistence" or stage == "persist":
        wanted_bits.append("persist into standing memory/instructions")
    elif tools:
        wanted_bits.append(f"steer agent into {'+'.join(tools[:2])}")
    else:
        wanted_bits.append(f"{objective} via {techs[0] if techs else 'injection'}")

    summary = "wanted: " + " ".join(wanted_bits)
    if concealment:
        summary += f" (concealed: {', '.join(concealment[:2])})"

    return {
        "objective": objective,
        "stage": stage,
        "targets": {"paths": paths, "hosts": hosts, "tools": tools},
        "concealment": concealment,
        "techniques": techs,
        "summary": summary,
    }
