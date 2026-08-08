"""Shared request/response schemas for Elcaro — the IPI detection miner.

These models are used by both the miner API (Track 1) and the app middleware
(Track 3) to ensure a consistent interface.
"""

from __future__ import annotations

from enum import StrEnum

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


# ── Detection results ──────────────────────────────────────────────────────────


class DetectionIndicator(BaseModel):
    """A single pattern match from a detector."""

    technique_class: TechniqueClass
    technique_name: str = Field(
        ..., description="Human-readable name of the specific pattern detected"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="How confident the detector is (0–1)"
    )
    matched_text: str = Field(..., description="The text snippet that triggered the match")
    location: str = Field(
        ..., description="Where in the content the match was found (body, metadata, etc.)"
    )
    explanation: str = Field(..., description="Why this is suspicious")


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
    context: str | None = Field(
        default=None,
        description="Optional context about the consuming agent or task",
    )


class ScanResponse(BaseModel):
    """Response from the IPI detection scan."""

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
        description="Detailed list of detection indicators",
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
