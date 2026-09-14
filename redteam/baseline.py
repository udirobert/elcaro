"""Vulnerable-baseline oracle — the engine as it was BEFORE the hardening
that the searcher forced.

The demo arc needs both halves: trophies landing on a real engine, then
the same mutations caught by the live one. This oracle reproduces the
pre-hardening semantics exactly — same detector instances, same scoring
math — minus the three fixes:

  1. no evasion normalization (core/normalize.py didn't exist)
  2. old content-type weights (chat_message 0.3, system_prompt 0.0)
  3. system_prompt auto-passed at 0.0; no privileged-type rescan

It lives in redteam/ rather than behind an engine flag on purpose: the
vulnerable code path exists to demonstrate what was found and fixed —
it should never be reachable from the production /scan surface.
"""

from __future__ import annotations

from core.schemas import ContentType
from core.taxonomy import IpiDetectionEngine
from redteam.oracle import Candidate, OracleResult

# Scoring weights as they were before the arbitrage fix.
_BASELINE_WEIGHTS: dict[ContentType, float] = {
    ContentType.EMAIL: 1.0,
    ContentType.SEARCH_RESULT: 1.0,
    ContentType.WEBPAGE: 1.0,
    ContentType.DOCUMENT: 0.8,
    ContentType.CODE: 0.7,
    ContentType.CHAT_MESSAGE: 0.3,
    ContentType.SYSTEM_PROMPT: 0.0,
}


class BaselineOracle:
    """Drop-in oracle with pre-hardening scan semantics."""

    def __init__(self) -> None:
        self._engine = IpiDetectionEngine(classifier=None)

    async def scan(self, cand: Candidate) -> OracleResult:
        # The original hole: trusted by definition, never scanned.
        if cand.content_type == ContentType.SYSTEM_PROMPT:
            return OracleResult(
                risk_score=0.0,
                risk_level="safe",
                quarantined=False,
                flagged_techniques=[],
                latency_ms=0,
            )

        # Raw content — no normalization — through the same detectors.
        indicators = []
        for detector in self._engine.detectors:
            indicators.extend(detector.detect(cand.content, cand.content_type))

        raw = self._engine._compute_score(indicators)
        weight = _BASELINE_WEIGHTS.get(cand.content_type, 1.0)
        weighted = min(raw * weight, 1.0)

        classes = list({i.technique_class for i in indicators})
        weighted = self._engine._apply_multipliers(weighted, classes, indicators)
        # No privileged-type rescan — the second hole stays open.

        level = self._engine._risk_level(weighted)
        return OracleResult(
            risk_score=round(weighted, 4),
            risk_level=level.value,
            quarantined=weighted >= 0.5,
            flagged_techniques=[c.value for c in classes],
            latency_ms=0,
        )

    async def close(self) -> None:
        pass
