"""Trophy minimization — chain ablation.

A 7-op trophy proves evasion but hides which ops were load-bearing.
Ablation replays the chain with each op removed in turn (fresh mutation
from the seed, fixed rng per attempt) and keeps a removal if the result
still bypasses. Approximate — mutators are stochastic — but it shrinks
demo chains from "7 ops, one of which mattered" to "these 2 mattered".

    python -m redteam.minimize <journal.jsonl>
"""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

from core.schemas import ContentType
from redteam.corpus import load_corpus
from redteam.journal import Journal
from redteam.mutators import MUTATORS_BY_NAME
from redteam.oracle import (
    Candidate,
    LocalOracle,
    is_score_bypass,
)


def _replay(seed: Candidate, ops: list[str], rng: random.Random) -> Candidate | None:
    """Re-apply an op chain to a seed candidate; None if an op is unknown."""
    cand = seed
    for op in ops:
        m = MUTATORS_BY_NAME.get(op)
        if m is None:
            return None
        cand = m.apply(cand, rng)
    return cand


async def ablate(
    trophy: dict,
    seeds_by_id: dict[str, Candidate],
    oracle: LocalOracle,
    rng: random.Random,
) -> dict:
    """Greedily shrink one trophy's op chain. Returns a minimized record."""
    seed = seeds_by_id.get(trophy["seed_id"])
    if seed is None:
        return trophy
    ops = list(trophy.get("ops", []))
    if len(ops) <= 1:
        return {**trophy, "min_ops": ops}

    improved = True
    while improved and len(ops) > 1:
        improved = False
        for i in range(len(ops)):
            trial_ops = ops[:i] + ops[i + 1 :]
            cand = _replay(seed, trial_ops, rng)
            if cand is None:
                continue
            res = await oracle.scan(cand)
            if is_score_bypass(cand, res):
                ops = trial_ops
                improved = True
                break
    return {**trophy, "min_ops": ops}


async def minimize_journal(journal_path: Path | str) -> list[dict]:
    """Ablate every unique trophy signature in a journal."""
    corpus = {s.id: s for s in load_corpus()}
    seeds_by_id = {
        sid: Candidate(
            id=f"seed-{sid}",
            content=s.content,
            content_type=ContentType(s.content_type),
            seed_id=s.id,
            canary=s.canary,
        )
        for sid, s in corpus.items()
    }
    from redteam.journal import unique_trophies

    trophies = unique_trophies(Journal.read(journal_path))
    oracle = LocalOracle()
    rng = random.Random(0)
    out = []
    for t in trophies:
        out.append(await ablate(t, seeds_by_id, oracle, rng))
    return out


async def _main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m redteam.minimize <journal.jsonl>")
        return
    results = await minimize_journal(sys.argv[1])
    shrunk = [r for r in results if len(r.get("min_ops", r["ops"])) < len(r["ops"])]
    print(f"[minimize] {len(results)} trophies → {len(shrunk)} chains shortened")
    for r in results:
        before = "/".join(r["ops"])
        after = "/".join(r.get("min_ops", r["ops"]))
        marker = "→" if len(after.split("/")) < len(r["ops"]) else " "
        print(f"  {marker} {r['seed_id']:5s} [{before}]  ⇒  [{after}]")


if __name__ == "__main__":
    asyncio.run(_main())
