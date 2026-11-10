"""Signed JSONL threat log for the elcaro Hermes plugin.

Every scan verdict is appended under the plugin data dir so the Desktop
pane, `elcaro_explain`, and a human reviewer all read the same trail.
Entries carry the canonical Ed25519 signature when a signing key is
configured — the verdict is verifiable offline, the content never leaves
the box (only its SHA-256 is logged).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

_MAX_BYTES = 512 * 1024  # rotate to a single .1 backup beyond this
_TAIL_CHUNK = 8192  # backward-read block for the last line
# Serializes prev-hash reads and writes — concurrent appends racing a
# shared tail would cross-link the hash chain.
_append_lock = threading.Lock()


def data_dir() -> Path:
    """Plugin-owned state dir — Hermes's plugin_data_dir, or a local fallback."""
    try:
        from plugins.plugin_storage import plugin_data_dir

        return Path(plugin_data_dir("elcaro"))
    except Exception:
        return Path(os.environ.get("ELCARO_DATA_DIR", "~/.elcaro/hermes")).expanduser()


def log_path() -> Path:
    return data_dir() / "threat-log.jsonl"


def _signer():
    """Build the verdict signer from the profile's secrets; None = unsigned mode."""
    from . import config
    from .elcaro_engine import VerdictSigner

    key = config.get_secret("signing_key", "ELCARO_SIGNING_KEY")
    if not key:
        return None
    try:
        return VerdictSigner(key)
    except ValueError:
        return None


def _entry_hash(entry: dict[str, Any]) -> str:
    """SHA-256 over the canonical entry (minus its own hash field)."""
    payload = {
        k: v
        for k, v in entry.items()
        if k not in ("entry_hash", "signature", "key_id")  # signature/key_id are set after hashing
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    import hashlib

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prev_hash() -> str | None:
    """Hash of the last log entry — links the chain; None on first write.

    Tail-seeked in chunks, not a full read — appends happen on every scan.
    An unparseable last line returns None: the next entry then chains to
    nothing, which verify_chain reports as a break at exactly the corrupt
    point (same contract as reading the whole file).
    """
    path = log_path()
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            offset = f.tell()
            buf = ""
            while offset > 0:
                step = min(_TAIL_CHUNK, offset)
                offset -= step
                f.seek(offset)
                buf = f.read(step).decode("utf-8", errors="replace") + buf
                if "\n" in buf[:-1] or offset == 0:
                    break
    except OSError:
        return None
    for line in reversed(buf.splitlines()):
        if not line.strip():
            continue
        try:
            return json.loads(line).get("entry_hash")
        except (json.JSONDecodeError, AttributeError):
            return None
    return None


def verify_chain() -> dict[str, Any]:
    """Tamper check: every entry_hash recomputes and links to prev_hash.

    Verifies the whole file, not a tail window — the log rotates at
    _MAX_BYTES so a full read stays bounded, and a windowed check would
    flag the first in-window entry's real prev_hash as a break.
    """
    path = log_path()
    entries: list[dict[str, Any] | None] = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append(None)  # corrupt line breaks the chain here
        except OSError:
            pass
    broken = 0
    prev_hash: str | None = None
    for e in entries:
        if e is None or e.get("entry_hash") != _entry_hash(e):
            broken += 1
            prev_hash = None
            continue
        if e.get("prev_hash") != prev_hash:
            broken += 1
        prev_hash = e.get("entry_hash")
    return {"checked": len(entries), "broken": broken, "ok": broken == 0}


def append(
    *,
    tool_name: str,
    verdict: Any,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    surface: str = "tool_result",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a scan verdict to the threat log. Returns the entry written."""
    from .elcaro_engine import canonical_verdict_payload, sha256_hex

    scanned_at = int(time.time())
    techniques = [t.value if hasattr(t, "value") else str(t) for t in verdict.flagged_techniques]
    content_sha = sha256_hex(getattr(verdict, "_scanned_content", "") or "")
    entry: dict[str, Any] = {
        "ts": scanned_at,
        "surface": surface,
        "tool_name": tool_name,
        "task_id": task_id,
        "session_id": session_id,
        "tool_call_id": tool_call_id,
        "content_sha256": content_sha,
        "risk_score": round(float(verdict.risk_score), 4),
        "risk_level": getattr(verdict.risk_level, "value", str(verdict.risk_level)),
        "quarantined": bool(verdict.quarantined),
        "flagged_techniques": techniques,
        "normalizations": list(getattr(verdict, "normalizations_applied", []) or []),
        "latency_ms": getattr(verdict, "latency_ms", None),
    }
    if extra:
        entry.update(extra)
    signer = _signer()
    if signer is not None:
        payload = canonical_verdict_payload(
            content_sha256=content_sha,
            risk_score=verdict.risk_score,
            risk_level=entry["risk_level"],
            quarantined=entry["quarantined"],
            flagged_techniques=techniques,
            scanned_at=scanned_at,
        )
        entry["signature"] = signer.sign(payload)
        entry["key_id"] = signer.key_id
    else:
        entry["signature"] = None

    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # prev-hash read and the write are one critical section — two appends
    # racing the tail would both link to the same parent and break the chain.
    with _append_lock:
        entry["prev_hash"] = _prev_hash()
        entry["entry_hash"] = _entry_hash(entry)
        try:
            if path.exists() and path.stat().st_size > _MAX_BYTES:
                path.replace(path.with_suffix(".1.jsonl"))
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError:
            pass  # the log is a trail, never a failure surface

    # Live-update the Desktop threat-log pane (fire-and-forget; the plugin
    # event bus is a no-op when no desktop client is connected).
    try:
        from hermes_cli.plugin_events import broadcast_plugin_event

        broadcast_plugin_event("elcaro", "verdict.logged", {"quarantined": entry["quarantined"]})
    except Exception:
        logging.getLogger(__name__).debug("plugin event broadcast unavailable")
    return entry


def read_tail(n: int = 20) -> list[dict[str, Any]]:
    """Read the most recent n entries, oldest-first."""
    path = log_path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
