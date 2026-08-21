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
    """IPI technique classes (A–F) from the detection taxonomy."""

    AUTHORITY = "authority_framing"  # A — system-voice / trusted-source spoofing
    DELIMITER = "delimiter_confusion"  # B — fake closing tags, turn spoofing
    TASK_REFRAME = "task_reframing"  # C — goal hijack, mandatory reframing
    OBFUSCATION = "obfuscation"  # D — encoding, zero-width, homoglyphs
    PLACEMENT = "placement_salience"  # E — hidden in alt text, metadata, etc.
    CONDITIONAL = "conditional_trigger"  # F — delayed triggers keyed to workflow


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
    context: str | dict[str, Any] | None = Field(
        default=None,
        description="Optional context about the consuming agent or task. Accepts a "
        "string or an object: Telegraph's auto-routed /engine/v1/ask merges its "
        "`context` object into the request body, so a dict must not be rejected. "
        "Informational only — it does not affect detection.",
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
        description="One-sentence human-readable summary of the scan result",
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
