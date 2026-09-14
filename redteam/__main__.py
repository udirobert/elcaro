"""CLI entry: python -m redteam --target local --budget 200 --seed 13"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from redteam.corpus import load_seeds
from redteam.journal import Journal
from redteam.oracle import make_oracle
from redteam.search import run_search


def main() -> None:
    p = argparse.ArgumentParser(
        prog="redteam",
        description="Evolutionary IPI-bypass searcher against the Elcaro engine.",
    )
    p.add_argument(
        "--target",
        default="local",
        help="'local' (in-process engine) or a miner base URL",
    )
    p.add_argument("--budget", type=int, default=200, help="max oracle scans")
    p.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible runs")
    p.add_argument("--concurrency", type=int, default=8, help="HTTP parallelism (HttpOracle)")
    p.add_argument(
        "--out",
        default=None,
        help="journal path (default: redteam/runs/run-<ts>.jsonl)",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="run Tier-2 agent-execution oracle on each trophy (needs ELCARO_LLM_API_KEY)",
    )
    args = p.parse_args()

    out = (
        Path(args.out)
        if args.out
        else (Path(__file__).parent / "runs" / f"run-{int(time.time())}.jsonl")
    )
    journal = Journal(out)
    oracle = make_oracle(args.target, concurrency=args.concurrency)
    seeds = load_seeds()

    print(f"[redteam] {len(seeds)} seeds → target={args.target} budget={args.budget}")
    print(f"[redteam] journal → {out}")

    mutators = None
    try:
        from redteam.mutators import MUTATORS
        from redteam.mutators_llm import LLM_MUTATORS  # Dev B module (optional)

        mutators = [*MUTATORS, *LLM_MUTATORS]
    except ImportError:
        pass

    trophies = asyncio.run(run_search(seeds, oracle, journal, args.budget, args.seed, mutators))

    if args.execute:
        try:
            from redteam.executor import execute_trophies  # Dev B module

            asyncio.run(execute_trophies(trophies, journal))
        except ImportError:
            print("[redteam] --execute: redteam/executor.py not implemented yet")
    journal.close()

    singles = [t for t in trophies if len(t.cand.ops) == 1]
    multi = sorted((t for t in trophies if len(t.cand.ops) > 1), key=lambda t: len(t.cand.ops))

    print(
        f"\n[redteam] done — {len(trophies)} Tier-1 bypass(es): "
        f"{len(singles)} single-op, {len(multi)} multi-op"
    )

    if singles:
        print("\nSingle-operator bypasses (one op → one detector gap):")
        for t in singles:
            print(
                f"  • seed={t.cand.seed_id} op={t.cand.ops[0]} type={t.cand.content_type.value} "
                f"score={t.result.risk_score:.2f} :: {t.cand.content[:70]!r}"
            )

    if multi:
        print("\nShortest composed chains:")
        for t in multi[:10]:
            ops = "/".join(t.cand.ops)
            print(
                f"  • seed={t.cand.seed_id} ops=[{ops}] type={t.cand.content_type.value} "
                f"score={t.result.risk_score:.2f} :: {t.cand.content[:60]!r}"
            )


if __name__ == "__main__":
    main()
