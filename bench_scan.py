#!/usr/bin/env python3
"""Elcaro detector benchmark — scan every micro1-eval task payload.

Runs the production IpiDetectionEngine over each task's untrusted_content
and reports per-task verdicts plus aggregate catch rate. This is the
regression suite for detector changes: every new pattern family must move
catch rate without breaking the clean controls (T10, T11).

Usage:
    python bench_scan.py                 # human-readable table
    python bench_scan.py --json out.json # machine-readable for tracking
    python bench_scan.py --tasks DIR     # alternate task directory
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.schemas import ContentType, ScanRequest  # noqa: E402
from core.taxonomy import IpiDetectionEngine  # noqa: E402

REPO = Path(__file__).resolve().parent
DEFAULT_TASKS = REPO / "micro1-eval" / "tasks"

# Tasks whose payload is a clean control — a "catch" here is a false positive.
CONTROLS = {"T10", "T11"}


def is_control(task: dict) -> bool:
    return task.get("id") in CONTROLS or "clean control" in task.get("title", "").lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="risk_score at/above which a task counts as caught "
        "(matches quarantine DEFAULT_RISK_THRESHOLD)",
    )
    args = ap.parse_args()

    engine = IpiDetectionEngine()
    rows = []
    for path in sorted(args.tasks.glob("T*.json")):
        task = json.loads(path.read_text())
        try:
            ctype = ContentType(task["content_type"])
        except ValueError:
            ctype = ContentType.DOCUMENT
        resp = engine.scan(ScanRequest(content=task["untrusted_content"], content_type=ctype))
        rows.append(
            {
                "id": task["id"],
                "title": task["title"],
                "control": is_control(task),
                "content_type": ctype.value,
                "risk_score": round(resp.risk_score, 3),
                "risk_level": resp.risk_level.value,
                "caught": resp.risk_score >= args.threshold,
                "techniques": sorted({i.technique_name.split(":")[0] for i in resp.indicators}),
                "n_indicators": len(resp.indicators),
            }
        )

    attacks = [r for r in rows if not r["control"]]
    controls = [r for r in rows if r["control"]]
    caught = [r for r in attacks if r["caught"]]
    fp = [r for r in controls if r["caught"]]

    print(f"{'id':4} {'ctl':3} {'score':>6} {'level':<11} {'caught':<6} techniques")
    for r in rows:
        flag = (
            "FP!"
            if (r["control"] and r["caught"])
            else ("ok" if r["caught"] or r["control"] else "MISS")
        )
        print(
            f"{r['id']:4} {'yes' if r['control'] else '':3} {r['risk_score']:6.3f} "
            f"{r['risk_level']:<11} {flag:<6} {','.join(r['techniques']) or '-'}"
        )

    print(
        f"\nattack tasks caught : {len(caught)}/{len(attacks)} "
        f"({100 * len(caught) / max(len(attacks), 1):.0f}%)"
    )
    print(
        f"clean controls flagged: {len(fp)}/{len(controls)} "
        + (f"-> {[r['id'] for r in fp]}" if fp else "(none)")
    )

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "threshold": args.threshold,
                    "attack_caught": len(caught),
                    "attack_total": len(attacks),
                    "control_false_positives": [r["id"] for r in fp],
                    "rows": rows,
                },
                indent=2,
            )
        )
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
