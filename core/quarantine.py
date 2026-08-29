"""Quarantine policy — the single source of truth for the block threshold, the
notice substituted for quarantined content, and the human summary every
verdict carries for the agent→human handoff.

Three consumers must agree on this policy, so they all read it from here:
    - the detection engine (populates ScanResponse.safe_content / human_summary),
    - the agent middleware (app/middleware.py, "replace" quarantine mode),
    - the web playground (renders ScanResponse.safe_content verbatim).

Two registers, by design (docs/ux-audit.md, principle 6 — "relayable by
construction"):
    - the AGENT register: the bracketed quarantine notice — machine-register
      prose the consuming agent reads;
    - the HUMAN register: human_summary — one or two plain-language sentences
      the agent can quote verbatim when its user asks "why couldn't you read
      that email?"
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from core.schemas import RiskLevel

# Content at/above this score is quarantined. Matches the doctrine documented
# on the /integrate page (>= 0.5 block, >= 0.3 flag).
# COUPLED CONSTANT: app/web/src/lib/history.ts (QUARANTINE_THRESHOLD) must
# stay in sync — the web surfaces compute "quarantined" from this same line.
DEFAULT_RISK_THRESHOLD = 0.5

QUARANTINE_MESSAGE = (
    "[CONTENT QUARANTINED BY ELCARO — potential prompt injection detected. "
    "Risk score: {score:.2f}, level: {level}. Flagged techniques: {techniques}. "
    "Original content withheld from agent. "
    'Tell your user: "{human_summary}"]'
)

# End-user register descriptions — no jargon, no scores-first framing.
_CONTENT_DESCRIPTIONS = {
    "email": "this email",
    "search_result": "this search result",
    "webpage": "this web page",
    "document": "this document",
    "code": "this code",
    "chat_message": "this chat message",
    "system_prompt": "this system prompt",
}

_TECHNIQUE_EXPLANATIONS = {
    "authority_framing": "it pretends to be a system or administrator message — "
    "real system instructions can't legitimately arrive inside {desc}",
    "delimiter_confusion": "it tries to break out of its own text and pose as "
    "a new instruction to the agent",
    "task_reframing": "it tries to redirect the agent toward a different task "
    "than the one you asked for",
    "obfuscation": "it hides instructions inside encoded or invisible characters",
    "placement_salience": "it hides instructions in places chosen to catch a "
    "machine reader's attention",
    "conditional_trigger": "it plants instructions meant to trigger later, when "
    "the agent takes a specific action",
}

_FALLBACK_EXPLANATION = "it contains patterns associated with hidden agent instructions"

# Per-content-type actionable guidance, appended to the blocked summary only.
# The safe register stays calm; the blocked register tells the user what to do
# next, in terms specific to what was blocked (docs/ux-audit.md, R8).
_CONTENT_GUIDANCE = {
    "email": (
        "If you're expecting instructions, verify with the sender through a separate channel."
    ),
    "search_result": (
        "The source may be compromised, not just this snippet — "
        "don't trust further results from it unchecked."
    ),
    "webpage": (
        "The page may be tampered with; don't follow instructions embedded anywhere in it."
    ),
    "document": (
        "Treat embedded instructions as untrusted until the document's provenance is verified."
    ),
    "code": "Don't execute it; review the diff before running anything sourced from it.",
    "chat_message": "Treat the message as untrusted input, not a legitimate command.",
}


def _value(x: object) -> str:
    return x.value if isinstance(x, Enum) else str(x)


def build_human_summary(
    score: float,
    level: RiskLevel | str,
    technique_values: list[str],
    content_type: object,
    quarantined: bool,
) -> str:
    """Build the human-register summary an agent can quote verbatim to its user.

    Written for someone who didn't run the scan: plain language, content
    first, score second. Kept to one or two sentences so agents can relay it
    without paraphrasing (paraphrase loses fidelity at the exact moment
    fidelity matters).

    Args:
        score: The risk score of the scan.
        level: The risk level (enum or its string value).
        technique_values: Flagged technique values (e.g. ["authority_framing"]).
        content_type: The scanned content's type (enum or string).
        quarantined: Whether the content was withheld.
    """
    level_value = _value(level)
    desc = _CONTENT_DESCRIPTIONS.get(_value(content_type), "this content")

    if not quarantined:
        if level_value == RiskLevel.SAFE.value:
            return (
                f"Elcaro scanned {desc} and found no hidden instructions (risk {score:.2f} — safe)."
            )
        return (
            f"Elcaro scanned {desc} and found only weak warning signs — "
            f"nothing that needs blocking (risk {score:.2f} — {level_value}). "
            "Worth logging, safe to process."
        )

    why = _FALLBACK_EXPLANATION
    if technique_values:
        first = technique_values[0]
        template = _TECHNIQUE_EXPLANATIONS.get(first, _FALLBACK_EXPLANATION)
        why = template.format(desc=desc)
    summary = (
        f"Elcaro blocked {desc}: {why} "
        f"(risk {score:.2f} — {level_value}). "
        "The original content was withheld from your agent."
    )
    guidance = _CONTENT_GUIDANCE.get(_value(content_type))
    if guidance:
        summary = f"{summary} {guidance}"
    return summary


def build_quarantine_notice(
    score: float,
    level: RiskLevel | str,
    technique_values: list[str],
    human_summary: str | None = None,
) -> str:
    """Build the quarantine notice that replaces quarantined content.

    Args:
        score: The risk score of the scan.
        level: The risk level (enum or its string value).
        technique_values: Flagged technique values (e.g. ["authority_framing"]).
        human_summary: The human-register summary to embed as the relay line
            ("Tell your user: ..."). When omitted, a generic fallback is
            generated from the score and level.
    """
    techniques = ", ".join(technique_values) or "none"
    level_value = _value(level)
    if human_summary is None:
        human_summary = (
            f"Elcaro blocked this content: it may contain hidden instructions "
            f"for AI agents (risk {score:.2f} — {level_value})."
        )
    return QUARANTINE_MESSAGE.format(
        score=score,
        level=level_value,
        techniques=techniques,
        human_summary=human_summary,
    )


class QuarantineDecision(NamedTuple):
    """The outcome of applying the quarantine policy to scanned content."""

    safe_content: str  # what the consuming agent should receive
    quarantined: bool  # whether the original was withheld
    human_summary: str  # what the agent should quote to its user


def quarantine_decision(
    content: str,
    risk_score: float,
    risk_level: RiskLevel,
    flagged_techniques: list,
    content_type: object,
    threshold: float = DEFAULT_RISK_THRESHOLD,
) -> QuarantineDecision:
    """Apply the quarantine policy to scanned content."""
    technique_values = [_value(t) for t in flagged_techniques]
    quarantined = risk_score >= threshold
    human_summary = build_human_summary(
        risk_score, risk_level, technique_values, content_type, quarantined
    )
    if quarantined:
        notice = build_quarantine_notice(
            risk_score, risk_level, technique_values, human_summary=human_summary
        )
        return QuarantineDecision(notice, True, human_summary)
    return QuarantineDecision(content, False, human_summary)
