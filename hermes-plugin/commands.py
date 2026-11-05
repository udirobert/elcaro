"""Slash command (/elcaro) and CLI subcommand (hermes elcaro) handlers.

Both read the same signed threat log the guard writes — in-session status
for the slash command, terminal output for the CLI.
"""

from __future__ import annotations

import time
from typing import Any

from . import threatlog


def _fmt_event(e: dict[str, Any]) -> str:
    ts = time.strftime("%H:%M:%S", time.localtime(e.get("ts") or 0))
    techs = ", ".join(e.get("flagged_techniques") or []) or "none"
    mark = "⛔" if e.get("quarantined") else "·"
    sig = " signed" if e.get("signature") else ""
    return (
        f"{mark} {ts} {e.get('tool_name')} — {e.get('risk_score')} "
        f"{e.get('risk_level')} ({e.get('surface')}) · {techs}{sig}"
    )


def _status_text(n: int = 10) -> str:
    events = threatlog.read_tail(500)
    if not events:
        return "[ELCARO] no verdicts logged yet — tool results are scanned as they arrive."
    quarantined = [e for e in events if e.get("quarantined")]
    lines = [
        f"[ELCARO] {len(events)} scan(s) logged, {len(quarantined)} quarantined.",
        f"Last {min(n, len(events))} verdicts:",
    ]
    lines += [f"  {_fmt_event(e)}" for e in events[-n:][::-1]]
    return "\n".join(lines)


def slash_elcaro(raw_args: str = "", **kwargs) -> str:
    """In-session `/elcaro` — recent verdicts or a lookup index."""
    arg = (raw_args or "").strip()
    if arg.isdigit():
        from . import tools

        return tools.elcaro_explain({"index": int(arg)})
    return _status_text()


def cli_setup(subparsers) -> None:
    """hermes elcaro {log,status} [n]"""
    parser = subparsers.add_parser("elcaro", help="Elcaro guard — threat log and status")
    sub = parser.add_subparsers(dest="elcaro_cmd")
    for name in ("log", "status"):
        p = sub.add_parser(name, help=f"show {'recent verdicts' if name == 'log' else 'summary'}")
        p.add_argument("n", nargs="?", type=int, default=10)
        p.set_defaults(elcaro_cmd=name)


def cli_handler(args) -> int:
    n = getattr(args, "n", 10) or 10
    print(_status_text(n if getattr(args, "elcaro_cmd", "log") == "log" else 10))
    return 0
