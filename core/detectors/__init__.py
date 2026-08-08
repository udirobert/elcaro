"""Base detector class for all IPI technique detectors."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from core.schemas import (
    ContentType,
    DetectionIndicator,
    EvidenceContext,
    Severity,
    TechniqueClass,
    TTPReference,
)

# ── TTP mappings ───────────────────────────────────────────────────────────────
# Map technique classes to their MITRE ATLAS and Elcaro TTP references.
# MITRE ATLAS: https://atlas.mitre.org/techniques/
# These are the standard references for AI/ML attack techniques.

_TTPS: dict[TechniqueClass, list[TTPReference]] = {
    TechniqueClass.AUTHORITY: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051",
            technique_name="LLM Prompt Injection: Indirect",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-A01",
            technique_name="Authority/Role Impersonation",
            tactic="Privilege Escalation",
        ),
    ],
    TechniqueClass.DELIMITER: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051",
            technique_name="LLM Prompt Injection: Indirect",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-B01",
            technique_name="Context Boundary Escape",
            tactic="Defense Evasion",
        ),
    ],
    TechniqueClass.TASK_REFRAME: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051",
            technique_name="LLM Prompt Injection: Indirect",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-C01",
            technique_name="Task Goal Hijack",
            tactic="Execution",
        ),
    ],
    TechniqueClass.OBFUSCATION: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051.001",
            technique_name="LLM Prompt Injection: Indirect via Encoding",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-D01",
            technique_name="Filter Evasion via Encoding",
            tactic="Defense Evasion",
        ),
    ],
    TechniqueClass.PLACEMENT: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051",
            technique_name="LLM Prompt Injection: Indirect",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-E01",
            technique_name="Salience Manipulation",
            tactic="Defense Evasion",
        ),
    ],
    TechniqueClass.CONDITIONAL: [
        TTPReference(
            framework="mitre_atlas",
            technique_id="AML.T0051",
            technique_name="LLM Prompt Injection: Indirect",
            tactic="Initial Access",
        ),
        TTPReference(
            framework="elcaro",
            technique_id="ELC-F01",
            technique_name="Conditional/Delayed Trigger",
            tactic="Execution",
        ),
    ],
}

# ── Severity mapping ───────────────────────────────────────────────────────────
# Confidence → severity. Higher confidence = higher severity.


def _confidence_to_severity(confidence: float) -> Severity:
    """Map a confidence score to a severity level."""
    if confidence >= 0.85:
        return Severity.CRITICAL
    elif confidence >= 0.7:
        return Severity.HIGH
    elif confidence >= 0.55:
        return Severity.MEDIUM
    elif confidence >= 0.4:
        return Severity.LOW
    else:
        return Severity.INFO


# ── Remediation templates ──────────────────────────────────────────────────────

_REMEDIATION: dict[TechniqueClass, str] = {
    TechniqueClass.AUTHORITY: (
        "Strip or quarantine content claiming system/admin authority. "
        "Verify the source is actually privileged before allowing the agent to act on it."
    ),
    TechniqueClass.DELIMITER: (
        "Remove fabricated delimiters and role markers. "
        "Do not allow retrieved content to redefine conversation boundaries."
    ),
    TechniqueClass.TASK_REFRAME: (
        "Reject content that attempts to prepend, redirect, or redefine the agent's task. "
        "The agent's goal should only come from trusted instructions."
    ),
    TechniqueClass.OBFUSCATION: (
        "Decode and inspect obfuscated content before processing. "
        "Block content that hides instructions behind encoding or character substitution."
    ),
    TechniqueClass.PLACEMENT: (
        "Inspect low-visibility fields (metadata, alt text, comments) for imperatives. "
        "Do not privilege content at document edges over content in the body."
    ),
    TechniqueClass.CONDITIONAL: (
        "Block content containing conditional triggers keyed to agent workflow. "
        "Retrieved content should not dictate when or how the agent acts."
    ),
}


# ── Base class ─────────────────────────────────────────────────────────────────


class BaseDetector(ABC):
    """Abstract base for IPI technique detectors.

    Each detector scans content for patterns matching one technique class
    (A–F) and returns a list of DetectionIndicators for any matches found.
    """

    technique_class: TechniqueClass

    @abstractmethod
    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        """Scan content and return any detected indicators."""
        ...

    def _make_indicator(
        self,
        technique_name: str,
        confidence: float,
        matched_text: str,
        explanation: str,
        location: str = "body",
        *,
        content: str = "",
        char_offset: int = 0,
    ) -> DetectionIndicator:
        """Construct an enriched DetectionIndicator (threat card).

        Args:
            technique_name: Specific pattern ID (e.g. 'authority:system_voice_marker')
            confidence: Detection confidence (0–1)
            matched_text: The text that triggered the match
            explanation: Human-readable explanation
            location: Where in the content (body, metadata, tail, etc.)
            content: The full content string (for extracting surrounding context)
            char_offset: Character offset of the match in the content
        """
        # Build evidence with surrounding context
        context_before = ""
        context_after = ""
        if content and char_offset >= 0:
            ctx_start = max(0, char_offset - 100)
            ctx_end = min(len(content), char_offset + len(matched_text) + 100)
            context_before = content[ctx_start:char_offset]
            match_end = char_offset + len(matched_text)
            context_after = content[match_end:ctx_end]

        evidence = EvidenceContext(
            matched_text=matched_text[:200],
            context_before=context_before[-100:],
            context_after=context_after[:100],
            char_offset=char_offset,
        )

        return DetectionIndicator(
            technique_class=self.technique_class,
            technique_name=technique_name,
            severity=_confidence_to_severity(confidence),
            confidence=confidence,
            evidence=evidence,
            location=location,
            explanation=explanation,
            remediation=_REMEDIATION.get(
                self.technique_class, "Review and remove the flagged content."
            ),
            ttps=_TTPS.get(self.technique_class, []),
        )

    @staticmethod
    def _find_all(
        pattern: str,
        content: str,
        flags: int = re.IGNORECASE,
    ) -> list[tuple[str, int]]:
        """Find all matches of a regex pattern in content.

        Returns list of (matched_text, start_index) tuples.
        """
        matches = []
        for m in re.finditer(pattern, content, flags):
            matches.append((m.group(0), m.start()))
        return matches
