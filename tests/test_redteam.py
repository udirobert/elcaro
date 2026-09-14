"""redteam/ pipeline tests — corpus, mutators, oracle, journal, patch."""

from __future__ import annotations

import random

from core.schemas import ContentType
from redteam.corpus import load_corpus, load_seeds
from redteam.journal import Journal, unique_trophies
from redteam.mutators import MUTATORS
from redteam.oracle import (
    Candidate,
    LocalOracle,
    canary_intact,
    is_score_bypass,
)
from redteam.patch import PatchedOracle, draft_patches
from redteam.search import Searcher


def _seed_candidate(seed) -> Candidate:
    return Candidate(
        id="test-cand",
        content=seed.content,
        content_type=ContentType(seed.content_type),
        seed_id=seed.id,
        canary=seed.canary,
    )


def test_corpus_loads():
    corpus = load_corpus()
    assert len(corpus) == 26
    assert len(load_seeds()) == 18


def test_canary_extraction():
    seeds = {s.id: s for s in load_seeds()}
    assert seeds["A001"].canary == "backup@external.com"
    assert "collector.evil.com" in seeds["C001"].canary


def test_mutators_preserve_canary():
    rng = random.Random(0)
    for seed in load_seeds():
        base = _seed_candidate(seed)
        for m in MUTATORS:
            out = m.apply(base, rng)
            assert canary_intact(out), f"{m.name} dropped canary on {seed.id}"
            assert out.ops[-1] == m.name
            assert out.parent_id == base.id


async def test_search_finds_bypasses(tmp_path):
    journal = Journal(tmp_path / "j.jsonl")
    searcher = Searcher(LocalOracle(), journal, random.Random(13))
    trophies = await searcher.run(load_seeds(), budget=160)
    journal.close()
    # Post-hardening headline: every single-operator bypass is closed by
    # core/normalize.py + the privileged-type rescan floor. Remaining
    # trophies are multi-op semantic indirection (translation_soft,
    # fake_quote, carrier_padding compositions).
    singles = [t for t in trophies if len(t.cand.ops) == 1]
    assert not singles, "single-op bypass still open"


async def test_type_arbitrage_closed_by_engine():
    """Regression: content_type arbitrage used to score 0.0 via the
    system_prompt auto-pass. The engine floor + scanned system_prompt
    close it — LocalOracle must now catch the payload."""
    oracle = LocalOracle()
    seed = next(s for s in load_seeds() if s.id == "A001")
    cand = Candidate(
        id="t1",
        content=seed.content,
        content_type=ContentType.SYSTEM_PROMPT,
        seed_id=seed.id,
        canary=seed.canary,
        ops=["type_arbitrage"],
    )
    res = await oracle.scan(cand)
    assert res.risk_score >= 0.5
    assert res.quarantined is True
    assert not is_score_bypass(cand, res)


def test_journal_round_trip(tmp_path):
    path = tmp_path / "j.jsonl"
    j = Journal(path)
    cand = Candidate(
        id="x1",
        content="payload",
        content_type=ContentType.EMAIL,
        seed_id="A001",
        canary="payload",
        ops=["fake_quote"],
    )
    from redteam.oracle import OracleResult

    res = OracleResult(0.1, "safe", False, [])
    j.record_scan(0, cand, res, canary_intact=True, bypass=True)
    j.record_event("execution", candidate_id="x1", complied=True)
    j.close()

    recs = Journal.read(path)
    assert len(recs) == 2
    assert recs[0]["kind"] == "trophy"
    assert recs[1]["kind"] == "execution"
    assert len(unique_trophies(recs)) == 1


def test_draft_patches(tmp_path):
    path = tmp_path / "j.jsonl"
    j = Journal(path)
    from redteam.oracle import OracleResult

    cand = Candidate(
        id="p1",
        content="x",
        content_type=ContentType.EMAIL,
        seed_id="A001",
        canary="x",
        ops=["rot13_partial", "carrier_padding"],
    )
    j.record_scan(0, cand, OracleResult(0.0, "safe", False, []), True, True)
    j.close()

    patches = draft_patches(path)
    kinds = {p.kind for p in patches}
    assert patches
    assert "normalize" in kinds
    rot13_patch = next(p for p in patches if "rot13" in p.proposal.lower())
    assert "p1" in rot13_patch.trophies


async def test_engine_catches_dash_split():
    """Regression: unicode_dash_split scored 0.00 before core/normalize.py;
    the engine's token_desplit now rejoins S‑Y‑S‑T‑E‑M before matching."""
    seed = next(s for s in load_seeds() if s.id == "A001")
    base = _seed_candidate(seed)
    from redteam.mutators import MUTATORS_BY_NAME

    cand = MUTATORS_BY_NAME["unicode_dash_split"].apply(base, random.Random(1))
    res = await LocalOracle().scan(cand)
    assert res.risk_score >= 0.5
    assert res.normalizations_applied == ["token_desplit"]


async def test_patched_oracle_type_floor():
    seed = next(s for s in load_seeds() if s.id == "C001")
    cand = Candidate(
        id="t2",
        content=seed.content,
        content_type=ContentType.CHAT_MESSAGE,
        seed_id=seed.id,
        canary=seed.canary,
        ops=["type_arbitrage"],
    )
    res = await LocalOracle().scan(cand)
    patched = PatchedOracle({"type_arbitrage"})
    res2 = await patched.scan(cand)
    assert res2.risk_score >= res.risk_score
