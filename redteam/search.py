"""The evolutionary search loop.

Budget-limited (total scans, not wall-clock — a --budget 800 run is ~800
oracle calls regardless of speed). Each generation:

    1. select parents — lowest risk_score among canary-intact candidates
       seen so far (hill-climb the detection gradient), always including a
       fresh seed so the population doesn't collapse onto one lineage
    2. mutate — 1–3 operators per child, drawn uniformly
    3. scan — batched through the oracle (async; HttpOracle is concurrency-
       limited, LocalOracle is just a fast sync call wrapped in the same
       signature)
    4. journal — every candidate logged; Tier-1 bypasses mirror as trophies
    5. evolve — survivors = best-of parents + children by score, canary
       intact only (a candidate that dropped the payload is a dead end even
       at score 0.0)

Determinism: --seed fixes the RNG for rehearsal; --no-seed for stage.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import uuid
from dataclasses import dataclass

from core.schemas import ContentType
from redteam.corpus import SeedCase
from redteam.journal import Journal
from redteam.mutators import MUTATORS
from redteam.oracle import (
    Candidate,
    LocalOracle,
    OracleResult,
    canary_intact,
    is_score_bypass,
)


@dataclass
class ScoredCandidate:
    cand: Candidate
    result: OracleResult


class Searcher:
    def __init__(
        self,
        oracle,
        journal: Journal,
        rng: random.Random,
        pop_size: int = 12,
        ops_per_child: tuple[int, int] = (1, 3),
        mutators: list | None = None,
    ) -> None:
        self.oracle = oracle
        self.journal = journal
        self.rng = rng
        self.pop_size = pop_size
        self.ops_lo, self.ops_hi = ops_per_child
        # Dev B can inject LLM mutators (redteam/mutators_llm.py) without
        # touching this file or mutators.py.
        self.mutators = mutators if mutators is not None else MUTATORS
        self._seen_hashes: set[str] = set()
        self.trophies: list[ScoredCandidate] = []
        self.scans = 0

    def _seed_candidates(self, seeds: list[SeedCase]) -> list[Candidate]:
        return [
            Candidate(
                id=f"c-{uuid.uuid4().hex[:8]}",
                content=s.content,
                content_type=ContentType(s.content_type),
                seed_id=s.id,
                canary=s.canary,
            )
            for s in seeds
        ]

    def _mutate(self, parent: Candidate) -> Candidate:
        n_ops = self.rng.randint(self.ops_lo, self.ops_hi)
        cand = parent
        for _ in range(n_ops):
            available = [m for m in self.mutators if not (m.once and m.name in cand.ops)]
            if not available:
                break
            cand = self.rng.choice(available).apply(cand, self.rng)
        return cand

    def _dedupe(self, cand: Candidate) -> bool:
        """True if novel (keep), False if we've scanned this exact payload."""
        h = hashlib.sha256(cand.content.encode() + cand.content_type.value.encode()).hexdigest()
        if h in self._seen_hashes:
            return False
        self._seen_hashes.add(h)
        return True

    async def _scan_batch(self, gen: int, cands: list[Candidate]) -> list[ScoredCandidate]:
        results = await asyncio.gather(*(self.oracle.scan(c) for c in cands))
        scored = []
        for cand, res in zip(cands, results, strict=True):
            self.scans += 1
            intact = canary_intact(cand)
            bypass = is_score_bypass(cand, res)
            self.journal.record_scan(gen, cand, res, intact, bypass)
            if bypass:
                self.trophies.append(ScoredCandidate(cand, res))
            scored.append(ScoredCandidate(cand, res))
        return scored

    async def _singles_sweep(self, seeds: list[SeedCase], budget: int) -> list[ScoredCandidate]:
        """Gen-0 sweep: every seed × every mutator, one operator each.

        Single-op bypasses are the cleanest findings — one operator, one
        detector gap, directly attributable. They also seed the population
        with proven-low-score parents for the evolutionary rounds.
        """
        cands: list[Candidate] = []
        for seed in seeds:
            base = Candidate(
                id=f"c-{uuid.uuid4().hex[:8]}",
                content=seed.content,
                content_type=ContentType(seed.content_type),
                seed_id=seed.id,
                canary=seed.canary,
            )
            for m in self.mutators:
                cand = m.apply(base, self.rng)
                if self._dedupe(cand):
                    cands.append(cand)
        return await self._scan_batch(0, cands[: max(0, budget - self.scans)])

    async def run(self, seeds: list[SeedCase], budget: int) -> list[ScoredCandidate]:
        population = self._seed_candidates(seeds)
        for c in population:
            self._dedupe(c)

        scored_pop = await self._singles_sweep(seeds, budget)

        gen = 0
        while self.scans < budget:
            gen += 1
            # Parents: best-scoring canary-intact candidates + one random seed
            viable = [
                sc
                for sc in scored_pop
                if canary_intact(sc.cand) and sc.cand.content_type != ContentType.SYSTEM_PROMPT
            ]
            viable.sort(key=lambda sc: sc.result.risk_score)
            parents = [sc.cand for sc in viable[: self.pop_size]]
            parents.append(self.rng.choice(population))  # fresh blood

            n_children = min(len(parents) * 2, budget - self.scans)
            children = []
            while len(children) < n_children:
                cand = self._mutate(self.rng.choice(parents))
                if self._dedupe(cand):
                    children.append(cand)

            scored_pop = await self._scan_batch(gen, children)
            if not scored_pop:
                break

        return self.trophies


async def run_search(
    seeds: list[SeedCase],
    oracle,
    journal: Journal,
    budget: int,
    seed: int | None,
    mutators: list | None = None,
) -> list[ScoredCandidate]:
    rng = random.Random(seed)
    searcher = Searcher(oracle, journal, rng, mutators=mutators)
    journal.record_event(
        "run_start",
        budget=budget,
        seed=seed,
        seeds=[s.id for s in seeds],
        oracle=type(oracle).__name__,
    )
    try:
        trophies = await searcher.run(seeds, budget)
    finally:
        journal.record_event("run_end", scans=searcher.scans, trophies=len(searcher.trophies))
        if isinstance(oracle, LocalOracle) is False:
            close = getattr(oracle, "close", None)
            if close:
                await close()
    return trophies
