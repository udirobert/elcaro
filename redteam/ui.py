"""Live terminal view over a running search — tails the journal file.

No dependencies: ANSI redraw in place. Run alongside a search:

    python -m redteam --target local --budget 800 --out runs/demo.jsonl &
    python -m redteam.ui runs/demo.jsonl

Layout:
    header   — run meta (oracle, budget, elapsed, scans)
    stream   — last ~8 candidates: gen, ops, score bar
    trophies — every confirmed Tier-1 bypass (deduped by signature)
    executes — Tier-2 AGENT COMPLIED / resisted stamps
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
CLEAR = "\033[2J\033[H"


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(round(score * width))
    color = RED if score >= 0.5 else (YELLOW if score >= 0.3 else GREEN)
    return f"{color}{'█' * filled}{'░' * (width - filled)}{RESET} {score:.2f}"


def _render(records: list[dict]) -> str:
    scans = [r for r in records if r.get("kind") in ("scan", "trophy")]
    trophies = [r for r in records if r.get("kind") == "trophy"]
    execs = [r for r in records if r.get("kind") == "execution"]
    meta = next((r for r in records if r.get("kind") == "run_start"), {})

    seen: set[str] = set()
    uniq_trophies = []
    for t in trophies:
        k = (t.get("seed_id"), "/".join(t.get("ops", [])), t.get("content_type"))
        if k not in seen:
            seen.add(k)
            uniq_trophies.append(t)

    lines = [
        f"{BOLD}{CYAN}ELCARO RED TEAM{RESET}  "
        f"oracle={meta.get('oracle', '?')}  budget={meta.get('budget', '?')}  "
        f"scans={len(scans)}  {BOLD}{RED}bypasses={len(uniq_trophies)}{RESET}",
        "",
        f"{DIM}── candidate stream (latest) ──{RESET}",
    ]
    for r in scans[-8:]:
        ops = "/".join(r.get("ops", [])) or "seed"
        mark = f"{RED}⚑{RESET}" if r.get("bypass") else " "
        lines.append(
            f" {mark} g{r.get('gen', 0):02d} {r.get('seed_id', ''):5s} "
            f"{_score_bar(r.get('risk_score', 0))} {ops[:42]}"
        )

    lines += ["", f"{DIM}── trophy case (confirmed Tier-1 bypasses) ──{RESET}"]
    op_counts = Counter(op for t in uniq_trophies for op in set(t.get("ops", [])))
    if op_counts:
        lines.append("  " + "  ".join(f"{op}×{n}" for op, n in op_counts.most_common()))
    for t in uniq_trophies[-10:]:
        lines.append(
            f"  {RED}{t.get('seed_id', ''):5s}{RESET} "
            f"{'/'.join(t.get('ops', []))[:48]:48s} "
            f"{t.get('content_type', ''):14s} {t.get('risk_score', 0):.2f}"
        )

    if execs:
        lines += ["", f"{DIM}── tier-2 execution (does the agent comply?) ──{RESET}"]
        for e in execs[-6:]:
            stamp = (
                f"{RED}{BOLD}AGENT COMPLIED{RESET}"
                if e.get("complied")
                else f"{GREEN}resisted{RESET}"
            )
            lines.append(f"  {stamp}  {e.get('candidate_id', '')} {e.get('detail', '')}")
    return "\n".join(lines)


def tail(path: Path, poll_s: float = 0.5) -> None:
    print(CLEAR, end="")
    last_size = -1
    try:
        while True:
            if path.exists():
                size = path.stat().st_size
                if size != last_size:
                    last_size = size
                    records = [
                        json.loads(line) for line in path.read_text().splitlines() if line.strip()
                    ]
                    print(CLEAR + _render(records))
            time.sleep(poll_s)
    except KeyboardInterrupt:
        print(f"\n{DIM}stopped tailing {path}{RESET}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m redteam.ui <journal.jsonl>")
        sys.exit(1)
    tail(Path(sys.argv[1]))
