"""Shared request/response schemas for Elcaro — the IPI detection miner.

These models are used by both the miner API (Track 1) and the app middleware
(Track 3) to ensure a consistent interface.

Design principle: every finding must be explainable, evidenced, and actionable.
Inspired by Ossprey's threat card model — we never just say "bad"; we say why,
show the evidence, map to a framework, and suggest what to do.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ── Content types ──────────────────────────────────────────────────────────────


class ContentType(StrEnum):
    """The type of content being scanned. Affects contextual risk weighting."""

    EMAIL = "email"
    SEARCH_RESULT = "search_result"
    CODE = "code"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    CHAT_MESSAGE = "chat_message"
    SYSTEM_PROMPT = "system_prompt"


# ── Technique taxonomy ─────────────────────────────────────────────────────────


class TechniqueClass(StrEnum):
    """IPI technique classes (A–G) from the detection taxonomy."""

    AUTHORITY = "authority_framing"  # A — system-voice / trusted-source spoofing
    DELIMITER = "delimiter_confusion"  # B — fake closing tags, turn spoofing
    TASK_REFRAME = "task_reframing"  # C — goal hijack, mandatory reframing
    OBFUSCATION = "obfuscation"  # D — encoding, zero-width, homoglyphs
    PLACEMENT = "placement_salience"  # E — hidden in alt text, metadata, etc.
    CONDITIONAL = "conditional_trigger"  # F — delayed triggers keyed to workflow
    SWARM_DIRECTIVE = "swarm_directive"  # G — agent-to-agent steering register


class RiskLevel(StrEnum):
    """Overall risk classification."""

    SAFE = "safe"
    LOW = "low"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"


class Severity(StrEnum):
    """Per-indicator severity (distinct from overall risk level).

    Maps to how dangerous this specific pattern is in isolation.
    """

    INFO = "info"  # Weak signal — notable but not actionable alone
    LOW = "low"  # Minor risk — contributes to score but unlikely malicious alone
    MEDIUM = "medium"  # Moderate risk — warrants review
    HIGH = "high"  # Strong indicator — likely malicious
    CRITICAL = "critical"  # Near-certain injection — immediate action required


# ── TTP mapping ────────────────────────────────────────────────────────────────


class TTPReference(BaseModel):
    """Tactic/Technique/Procedure reference for a finding.

    Maps Elcaro findings to the MITRE ATLAS framework (AI-specific TTPs)
    and our own Elcaro taxonomy for patterns ATLAS doesn't cover.
    """

    framework: str = Field(
        ...,
        description="Reference framework: 'mitre_atlas' or 'elcaro'",
    )
    technique_id: str = Field(
        ...,
        description="Technique identifier (e.g. 'AML.T0051' for ATLAS, 'ELC-A01' for Elcaro)",
    )
    technique_name: str = Field(
        ...,
        description="Human-readable technique name",
    )
    tactic: str = Field(
        ...,
        description="The tactic this technique supports (e.g. 'Initial Access', 'Exfiltration')",
    )


# ── Detection results ──────────────────────────────────────────────────────────


class EvidenceContext(BaseModel):
    """The evidence behind a detection — the actual content that triggered it.

    Shows the matched text with surrounding context so a human reviewer
    can see exactly what was flagged without reading the full document.
    """

    matched_text: str = Field(
        ...,
        description="The exact text that triggered the pattern match",
    )
    context_before: str = Field(
        default="",
        description="Up to 100 chars of content before the match for context",
    )
    context_after: str = Field(
        default="",
        description="Up to 100 chars of content after the match for context",
    )
    char_offset: int = Field(
        default=0,
        description="Character offset of the match from the start of the content",
    )


class DetectionIndicator(BaseModel):
    """A single finding from a detector — the threat card.

    Modelled after Ossprey's threat card: severity, evidence, TTPs,
    explanation, and remediation. Every finding must be explainable
    and actionable.
    """

    technique_class: TechniqueClass
    technique_name: str = Field(
        ..., description="Specific pattern identifier (e.g. 'authority:system_voice_marker')"
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="How dangerous this specific indicator is in isolation",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="How confident the detector is (0–1)"
    )
    evidence: EvidenceContext = Field(
        ...,
        description="The matched text with surrounding context",
    )
    location: str = Field(
        ..., description="Where in the content the match was found (body, metadata, tail, etc.)"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of why this is suspicious"
    )
    remediation: str = Field(
        default="Review and remove the flagged content before processing.",
        description="Recommended action to address this finding",
    )
    ttps: list[TTPReference] = Field(
        default_factory=list,
        description="MITRE ATLAS or Elcaro TTP mappings for this finding",
    )

    # Backwards compatibility: expose matched_text at top level
    @property
    def matched_text(self) -> str:
        """Convenience accessor for the matched text."""
        return self.evidence.matched_text


# ── API request/response ──────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    """Request to scan content for prompt injection."""

    content: str = Field(..., description="The text content to scan for injection")
    content_type: ContentType = Field(
        default=ContentType.DOCUMENT,
        description="Type of content being scanned (affects contextual weighting)",
    )
    deep_analysis: bool = Field(
        default=False,
        description="If true, run LLM second pass for ambiguous (gray-zone) results",
    )
    serv_enabled: bool = Field(
        default=False,
        description=(
            "Optional progressive-enhancement toggle: when true AND the server is "
            "configured with SERV_API_KEY + SERV_ENABLED=1, the engine uses SERV "
            "Reasoning as the second-pass judge for borderline cases. Default off; "
            "the free fast path is unaffected (no network call, no key required)."
        ),
    )
    context: str | dict[str, Any] | None = Field(
        default=None,
        description="Optional context about the consuming agent or task. Accepts a "
        "string or an object: Telegraph's auto-routed /engine/v1/ask merges its "
        "`context` object into the request body, so a dict must not be rejected. "
        "Informational only — it does not affect detection.",
    )
    jev_enabled: bool = Field(
        default=False,
        description=(
            "Optional comparison toggle: when true AND the server is configured "
            "with JEV_API_KEY + JEV_ENABLED=1, borderline (gray-zone) scans also "
            "get a shadow verdict from TypeSafe's Jev model for side-by-side "
            "comparison. Jev never adjusts risk_score or risk_level — the rule "
            "engine's decision is unaffected either way. Default off; no network "
            "call, no key required."
        ),
    )
    laya_enabled: bool = Field(
        default=False,
        description=(
            "Optional comparison toggle: when true AND the server is configured "
            "with a Runware key + LAYA_ENABLED=1, borderline (gray-zone) scans "
            "also get a shadow verdict from Convai's Laya decision model (via "
            "Runware) for side-by-side comparison. Like Jev, Laya never adjusts "
            "risk_score or risk_level. Default off; no network call, no key "
            "required."
        ),
    )


class ScanResponse(BaseModel):
    """Response from the IPI detection scan.

    Structured to support both quick programmatic decisions (risk_score + risk_level)
    and deep human review (indicators with evidence, TTPs, and remediation).
    """

    risk_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall injection risk score (0=safe, 1=dangerous)"
    )
    risk_level: RiskLevel = Field(..., description="Categorical risk level")
    flagged_techniques: list[TechniqueClass] = Field(
        default_factory=list,
        description="Technique classes that triggered detection",
    )
    indicators: list[DetectionIndicator] = Field(
        default_factory=list,
        description="Detailed threat cards for each finding",
    )
    summary: str = Field(
        default="",
        description=(
            "Prose verdict: leads with 'Verdict: ...', then band, score and "
            "techniques. Never quotes matched content."
        ),
    )
    content_type: ContentType = Field(..., description="The content type that was scanned")
    deep_analysis_used: bool = Field(
        default=False,
        description="Whether the LLM second pass was invoked",
    )
    latency_ms: int | None = Field(
        default=None,
        description="Processing latency in milliseconds",
    )
    human_summary: str = Field(
        default="",
        description=(
            "One or two plain-language sentences the consuming agent can quote "
            "verbatim to its user — the relay contract (docs/ux-audit.md, "
            "principle 6). Written for someone who didn't run the scan."
        ),
    )
    safe_content: str = Field(
        default="",
        description=(
            "The content as the consuming agent should receive it: the original "
            "content when below the quarantine threshold, or the quarantine "
            "notice replacing it (see core/quarantine.py)."
        ),
    )
    quarantined: bool = Field(
        default=False,
        description="Whether risk_score met or exceeded the quarantine threshold (0.5)",
    )
    normalizations_applied: list[str] = Field(
        default_factory=list,
        description=(
            "Evasion-normalization steps applied before detection "
            "(core/normalize.py): e.g. zero_width_strip, confusable_fold, "
            "token_desplit, rot13_decode, hex_decode, base64_decode. Empty "
            "means the content was scanned as-is. Detection ran on the "
            "normalized text; safe_content still references the original."
        ),
    )
    # ── SERV Reasoning observability ─────────────────────────────────────────
    # Mirrors the deep_analysis_used contract: these fields tell the caller
    # exactly what the optional SERV path did (or didn't do) so dashboards
    # can distinguish "no SERV configured" from "SERV configured but
    # failed" from "SERV configured and contributed to the verdict".
    serv_available: bool = Field(
        default=False,
        description=(
            "True when the miner is configured with SERV_API_KEY and "
            "SERV_ENABLED=1 — the SERV second pass is ready to run."
        ),
    )
    serv_attempted: bool = Field(
        default=False,
        description=(
            "True when the engine attempted to call SERV for this scan "
            "(gray-zone AND serv_enabled / deep_analysis). False when the "
            "request stayed on the free rule-only fast path."
        ),
    )
    serv_used: bool = Field(
        default=False,
        description=(
            "True when the SERV call succeeded and contributed to the "
            "verdict (TTP refinement, remediation, safe_content). False "
            "when SERV was unavailable, in cooldown, timed out, returned a "
            "credit-exhaustion error, or was not requested. On failure the "
            "rule-based score stands unchanged."
        ),
    )
    serv_rule_score_before: float | None = Field(
        default=None,
        description=(
            "The raw SERV LLM score before the 50/50 blend with the rule "
            "score. Present only when serv_used=True. Lets the caller show "
            "the delta: rule score vs SERV score vs final blended score — "
            "the signal that proves SERV added value."
        ),
    )
    # Cost transparency for SERV-enhanced scans. Present only when serv_used=True.
    # All values are in USDC (USD-pegged stablecoin). None means the scan
    # did not use SERV or the cost could not be estimated.
    serv_cost: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Cost estimate for the SERV second pass, present only when "
            "serv_used=True. Keys: input_tokens, output_tokens, "
            "input_cost_usdc, output_cost_usdc, total_usdc. Values are "
            "approximations based on character counts — real token counts "
            "are available from the provider if the response includes them."
        ),
    )
    # ── Jev (TypeSafe) comparison observability ──────────────────────────────
    # A pure shadow pass: these fields report what Jev saw on the same
    # borderline content, purely for side-by-side comparison. Unlike the
    # serv_* fields above, Jev's verdict never contributes to risk_score /
    # risk_level / safe_content — the rule engine stays sole authority.
    jev_available: bool = Field(
        default=False,
        description=(
            "True when the miner is configured with JEV_API_KEY and "
            "JEV_ENABLED=1 — the Jev comparison pass is ready to run."
        ),
    )
    jev_attempted: bool = Field(
        default=False,
        description=(
            "True when the engine attempted to call Jev for this scan "
            "(gray-zone AND jev_enabled). False when the request stayed on "
            "the rule-only fast path or fell outside the gray zone."
        ),
    )
    jev_used: bool = Field(
        default=False,
        description=(
            "True when the Jev call succeeded and jev_comparison is "
            "populated. False when Jev was unavailable, in cooldown, timed "
            "out, or returned an error — jev_comparison is None in that case."
        ),
    )
    jev_comparison: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Side-by-side comparison of the rule engine's verdict and Jev's "
            "calibrated confidence on the same content, present only when "
            "jev_used=True. Keys: rule_score, rule_level, jev_score, "
            "jev_level, jev_confidence, probabilities (map<level, prob>), "
            "agrees_with_rules, input_tokens, output_tokens, cost_usd "
            "(console-observed pricing, not a published rate — see "
            "core/jev_reasoner.py). Informational only — never fed back into "
            "the quarantine decision."
        ),
    )
    # ── Laya (Convai via Runware) comparison observability ────────────────────
    # A second shadow pass, identical contract to Jev: reports what Laya saw on
    # the same borderline content, purely for comparison. Never contributes to
    # risk_score / risk_level / safe_content.
    laya_available: bool = Field(
        default=False,
        description=(
            "True when the miner is configured with a Runware key and "
            "LAYA_ENABLED=1 — the Laya comparison pass is ready to run."
        ),
    )
    laya_attempted: bool = Field(
        default=False,
        description=(
            "True when the engine attempted to call Laya for this scan "
            "(gray-zone AND laya_enabled). False when the request stayed on "
            "the rule-only fast path or fell outside the gray zone."
        ),
    )
    laya_used: bool = Field(
        default=False,
        description=(
            "True when the Laya call succeeded and laya_comparison is "
            "populated. False when Laya was unavailable, in cooldown, timed "
            "out, or returned an error — laya_comparison is None in that case."
        ),
    )
    laya_comparison: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Side-by-side comparison of the rule engine's verdict and Laya's "
            "injection probability on the same content, present only when "
            "laya_used=True. Keys: rule_score, rule_level, laya_score "
            "(P(injection), 0-1), laya_level, laya_confidence (|2p-1|), "
            "probabilities (map<true|false, prob>), agrees_with_rules, "
            "input_tokens, output_tokens, cost_usd (free until 2026-10-12, "
            "then launch-note pricing — see core/laya_reasoner.py). "
            "Informational only — never fed back into the quarantine decision."
        ),
    )
    scanned_at: int | None = Field(
        default=None,
        description="Unix timestamp of the scan. Set by the miner API; part of the signed payload.",
    )
    signature: str | None = Field(
        default=None,
        description=(
            "Ed25519 signature (hex) over the canonical verdict payload — present "
            "when the miner has ELCARO_SIGNING_KEY configured (core/signing.py). "
            "Verify against GET /pubkey or POST /verify. Absent means unsigned, "
            "not invalid."
        ),
    )
    key_id: str | None = Field(
        default=None,
        description="Short fingerprint of the signing key, so verifiers know which key signed.",
    )
