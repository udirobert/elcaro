"""Backend routes for the elcaro plugin — mounted at /api/plugins/elcaro/.

Serves the signed threat log to the Desktop pane. Self-contained by
design: this module is imported by the web server as a standalone file,
so it resolves the plugin data dir through hermes's own plugin_storage
rather than the package's modules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter()


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


@router.get("/verdicts")
async def verdicts(n: int = Query(50, ge=1, le=500)):
    entries = _entries(n)
    quarantined = sum(1 for e in entries if e.get("quarantined"))
    return {
        "entries": list(reversed(entries)),
        "total": len(entries),
        "quarantined": quarantined,
    }


@router.get("/stats")
async def stats():
    entries = _entries(500)
    tools: dict[str, int] = {}
    for e in entries:
        if e.get("quarantined"):
            t = e.get("tool_name", "?")
            tools[t] = tools.get(t, 0) + 1
    return {
        "scanned": len(entries),
        "quarantined": sum(1 for e in entries if e.get("quarantined")),
        "by_tool": tools,
        "signed": sum(1 for e in entries if e.get("signature")),
    }
