"""Elcaro red team — adversarial searcher that attacks the detection engine.

Treats the IPI detection engine (or the live miner API) as the target oracle
and searches the mutation space for confirmed bypasses: content that still
carries an actionable injected instruction but scores below the quarantine
threshold (risk_score < 0.5).

Pipeline:
    corpus.load_corpus()          — seeds from eval/corpus.json
    mutators.MUTATORS             — deterministic str-level mutation operators
    oracle.LocalOracle/HttpOracle — the target (engine in-process, or live API)
    search.Searcher               — evolutionary loop over (select, mutate, scan)
    journal.Journal               — JSONL run log + trophy case

Interfaces other redteam modules build against (see each module's docstring):
    corpus.SeedCase / corpus.Canary
    mutators.Mutator (Candidate -> Candidate)
    oracle.OracleResult, oracle.is_score_bypass
    journal.Journal (append-only JSONL, read by the UI and patch drafter)

Run:
    python -m redteam --target local --budget 200 --seed 13
    python -m redteam --target https://api.elcaro.trustfall.xyz --budget 800
"""
