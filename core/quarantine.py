"""Quarantine policy — the single source of truth for the block threshold and
the notice substituted for quarantined content.

Three consumers must agree on this policy, so they all read it from here:
    - the detection engine (populates ScanResponse.safe_content),
    - the agent middleware (app/middleware.py, "replace" quarantine mode),
    - the web playground (renders ScanResponse.safe_content verbatim).
"""

from __future__ import annotations

from core.schemas import RiskLevel

# Content at/above this score is quarantined. Matches the doctrine documented
# on the /integrate page (>= 0.5 block, >= 0.3 flag).
DEFAULT_RISK_THRESHOLD = 0.5

QUARANTINE_MESSAGE = (
    "[CONTENT QUARANTINED BY ELCARO — potential prompt injection detected. "
    "Risk score: {score:.2f}, level: {level}. Flagged techniques: {techniques}. "
    "Original content withheld from agent.]"
)


def build_quarantine_notice(
    score: float,
    level: RiskLevel | str,
    technique_values: list[str],
) -> str:
    """Build the quarantine notice that replaces quarantined content.

    Args:
        score: The risk score of the scan.
        level: The risk level (enum or its string value).
        technique_values: Flagged technique values (e.g. ["authority_framing"]).
    """
    techniques = ", ".join(technique_values) or "none"
    level_value = level.value if isinstance(level, RiskLevel) else str(level)
    return QUARANTINE_MESSAGE.format(
        score=score,
        level=level_value,
        techniques=techniques,
    )


def quarantine_decision(
    content: str,
    risk_score: float,
    risk_level: RiskLevel,
    flagged_techniques: list,
    threshold: float = DEFAULT_RISK_THRESHOLD,
) -> tuple[str, bool]:
    """Apply the quarantine policy to scanned content.

    Returns (safe_content, quarantined): the content the consuming agent
    should receive, and whether it was quarantined.
    """
    if risk_score >= threshold:
        notice = build_quarantine_notice(
            risk_score,
            risk_level,
            [t.value for t in flagged_techniques],
        )
        return notice, True
    return content, False
