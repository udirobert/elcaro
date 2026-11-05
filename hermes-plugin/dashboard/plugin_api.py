"""Backend routes for the elcaro plugin — mounted at /api/plugins/elcaro/.

Serves the signed threat log to the Desktop pane. Self-contained by
design: this module is imported by the web server as a standalone file,
so it resolves the plugin data dir through hermes's own plugin_storage
rather than the package's modules.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter()

_DECOY_FILES = ("decoy-marker.txt", "service-credentials.env")


def _log_path() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir

        return Path(plugin_data_dir("elcaro")) / "threat-log.jsonl"
    except Exception:
        root = Path(os.environ.get("ELCARO_DATA_DIR", "~/.elcaro/hermes")).expanduser()
        return root / "threat-log.jsonl"


def _entries(n: int) -> list[dict]:
    path = _log_path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _is_scan(e: dict) -> bool:
    """Scan verdicts carry counts; edge records are annotations on them."""
    return e.get("type") != "edge"


def _entry_hash(entry: dict[str, Any]) -> str:
    """SHA-256 over the canonical entry — mirrors threatlog._entry_hash."""
    payload = {k: v for k, v in entry.items() if k not in ("entry_hash", "signature", "key_id")}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@router.get("/verdicts")
async def verdicts(n: int = Query(50, ge=1, le=500)):
    entries = _entries(n)
    scans = [e for e in entries if _is_scan(e)]
    return {
        "entries": list(reversed(entries)),
        "total": len(scans),
        "quarantined": sum(1 for e in scans if e.get("quarantined")),
    }


@router.get("/receipts")
async def receipts(n: int = Query(50, ge=1, le=500)):
    """Signed clean-scan receipts — proof a verdict was issued before acting."""
    entries = _entries(n)
    return {
        "receipts": [
            e
            for e in reversed(entries)
            if _is_scan(e) and e.get("signature") and not e.get("quarantined")
        ]
    }


@router.get("/edges")
async def edges(n: int = Query(50, ge=1, le=500)):
    """Propagation edges — canaries resurfacing inside later scans."""
    return {"edges": [e for e in reversed(_entries(n)) if e.get("type") == "edge"]}


@router.get("/verify")
async def verify():
    """Tamper check — recompute the full prev_hash → entry_hash chain."""
    path = _log_path()
    if not path.exists():
        return {"checked": 0, "broken": 0, "ok": True}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"checked": 0, "broken": 0, "ok": True}
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append(None)
    broken = 0
    prev_hash = None
    for e in entries:
        if e is None or e.get("entry_hash") != _entry_hash(e):
            broken += 1
            prev_hash = None
            continue
        if e.get("prev_hash") != prev_hash:
            broken += 1
        prev_hash = e.get("entry_hash")
    return {"checked": len(entries), "broken": broken, "ok": broken == 0}


@router.get("/decoy")
async def decoy():
    """Honeypot status — armed when the marker + bait file exist."""
    d = _log_path().parent
    armed = all((d / name).exists() for name in _DECOY_FILES)
    hits = sum(
        1 for e in _entries(500) if "decoy_exfiltration" in (e.get("flagged_techniques") or [])
    )
    return {"armed": armed, "hits": hits}


@router.get("/stats")
async def stats():
    entries = _entries(500)
    scans = [e for e in entries if _is_scan(e)]
    tools: dict[str, int] = {}
    for e in scans:
        if e.get("quarantined"):
            t = e.get("tool_name", "?")
            tools[t] = tools.get(t, 0) + 1
    return {
        "scanned": len(scans),
        "quarantined": sum(1 for e in scans if e.get("quarantined")),
        "edges": len(entries) - len(scans),
        "by_tool": tools,
        "signed": sum(1 for e in scans if e.get("signature")),
    }
