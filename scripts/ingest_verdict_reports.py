#!/usr/bin/env python3
"""Ingest verdict-report issues into eval TestCase candidates.

Closes the correction-surface loop (docs/ux-audit.md, R4): a verdict flagged
"missed" or "over-flagged" on the playground is filed as a GitHub issue from
the verdict-report template. This script pulls those issues and emits them as
JSON objects shaped like eval's TestCase ({content, content_type,
is_injection}) so they can be reviewed and merged into the corpus.

The miner stays stateless — reports live in the issue tracker, not a
database. Nothing here stores scanned content; it only reads what a human
already chose to file.

Usage:
    python scripts/ingest_verdict_reports.py [--repo udirobert/elcaro]
    python scripts/ingest_verdict_reports.py --stdin < issue_body.md

The report body format is produced by app/web/src/lib/report.ts:
    **Label:** missed|over-flagged
    **Content type:** email
    **Risk score:** 0.05
    **Risk level:** safe
    **Flagged techniques:** authority_framing

    ## Content
    <the scanned content>

    ## Notes
    <optional>
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from typing import Any

LABEL_OVER_FLAG = "over-flagged"  # clean content the engine flagged


def parse_report_body(body: str) -> dict[str, Any] | None:
    """Parse a verdict-report issue body into a TestCase-shaped dict.

    Returns None if the body is missing required fields. A "missed" label
    means the content IS an injection the engine scored safe/low →
    is_injection=True; "over-flagged" means clean content scored dangerous
    → is_injection=False.
    """
    fields: dict[str, str] = {}
    for line in body.splitlines():
        m = re.match(r"\*\*([^*]+):\*\*\s*(.+)", line.strip())
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()

    label = fields.get("label", "").lower()
    content_type = fields.get("content type", "")
    if not label or not content_type or label not in {"missed", "over-flagged"}:
        return None

    content_match = re.search(r"##\s*Content\s*\n(.+?)(?:\n##\s|$)", body, re.DOTALL)
    content = content_match.group(1).strip() if content_match else ""
    if not content:
        return None

    return {
        "content": content,
        "content_type": content_type,
        "is_injection": label == "missed",
        "reported_label": label,
        "risk_score": fields.get("risk score", ""),
        "risk_level": fields.get("risk level", ""),
        "flagged_techniques": fields.get("flagged techniques", ""),
    }


def fetch_issues(repo: str) -> list[dict[str, Any]]:
    """Pull verdict-report issues via gh. Empty list if gh is unavailable."""
    gh = shutil.which("gh")
    if gh is None:
        return []
    try:
        result = subprocess.run(
            [
                gh,
                "issue",
                "list",
                "--repo",
                repo,
                "--label",
                "verdict-report",
                "--state",
                "all",
                "--json",
                "number,title,body",
                "--limit",
                "200",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return json.loads(result.stdout) if result.stdout.strip() else []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest verdict-report issues into eval TestCase candidates."
    )
    parser.add_argument(
        "--repo",
        default="udirobert/elcaro",
        help="GitHub repo (default: %(default)s)",
    )
    parser.add_argument("--stdin", action="store_true", help="Parse a single body from stdin")
    args = parser.parse_args()

    if args.stdin:
        candidates = []
        body = sys.stdin.read()
        parsed = parse_report_body(body)
        if parsed:
            candidates.append(parsed)
    else:
        issues = fetch_issues(args.repo)
        candidates = [
            {**parse_report_body(i.get("body", "")), "issue": i["number"]}
            for i in issues
            if (parsed := parse_report_body(i.get("body", "")))
        ]

    json.dump(candidates, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
