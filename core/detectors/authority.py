"""Detector A — Authority / role framing.

Detects injected text that attempts to impersonate a higher-priority instruction
source: system-voice spoofing, trusted-source impersonation, policy-update
framing.

Reference: Greshake et al. (2023), OWASP LLM01.
"""

from __future__ import annotations

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# System-voice markers that should never appear in retrieved content
SYSTEM_VOICE_PATTERNS = [
    (r"\b(SYSTEM|ADMIN|INSTRUCTION|OVERRIDE)\s*[:\]]", 0.9, "system_voice_marker"),
    (r"<\s*system[-_]?(?:note|message|instruction|prompt)\s*>", 0.95, "system_tag"),
    (r"\[(?:SYSTEM|ADMIN|INSTRUCTION|OVERRIDE)\]", 0.85, "bracketed_authority"),
]

# Trusted-source impersonation
TRUSTED_SOURCE_PATTERNS = [
    (
        r"(?:Note|Instruction|Directive|Notice|Memo)\s+(?:from|by|—)\s+"
        r"(?:the\s+)?(?:data owner|maintainer|admin(?:istrator)?|security team|"
        r"system admin|devops|platform team)",
        0.85,
        "trusted_source_impersonation",
    ),
    (
        r"(?:Per|As per|According to)\s+(?:the\s+)?(?:security team|admin|maintainer)",
        0.75,
        "authority_claim",
    ),
    (
        r"(?:updated?|new|revised)\s+policy\s+(?:supersedes?|replaces?|overrides?)",
        0.8,
        "policy_override",
    ),
    (
        r"this (?:note|instruction|directive)\s+(?:is|was)\s+"
        r"(?:pre-?authorized|approved|authorized)",
        0.7,
        "fake_authorization",
    ),
]

# Imperative authority commands in retrieved content
AUTHORITY_IMPERATIVE_PATTERNS = [
    (
        r"(?:you (?:must|need to|are required to|are authorized to|should|have to))\s+"
        r"(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|grant|change|update|modify|set|create|add|remove|wipe)",
        0.7,
        "authority_directive",
    ),
    (
        r"(?:do not|don'?t|never)\s+(?:confirm|ask|verify|check with|wait for)",
        0.65,
        "anti_confirmation",
    ),
    (
        r"(?:standing|permanent|ongoing)\s+(?:instruction|directive|request|rule)",
        0.6,
        "standing_instruction",
    ),
]


class AuthorityDetector(BaseDetector):
    """Detects authority/role framing injection patterns (Class A)."""

    technique_class = TechniqueClass.AUTHORITY

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # System-voice markers are high-confidence in any retrieved content
        for pattern, confidence, name in SYSTEM_VOICE_PATTERNS:
            for match_text, _pos in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"authority:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"System-voice marker '{match_text}' found in "
                            f"{content_type.value} content. Retrieved content "
                            f"cannot contain legitimate system instructions."
                        ),
                        content=content,
                        char_offset=_pos,
                    )
                )

        # Trusted-source impersonation
        for pattern, confidence, name in TRUSTED_SOURCE_PATTERNS:
            for match_text, _pos in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"authority:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Content claims authority from a trusted source "
                            f"('{match_text}'), which is a common injection pattern "
                            f"in retrieved {content_type.value} content."
                        ),
                        content=content,
                        char_offset=_pos,
                    )
                )

        # Authority imperatives — only flag in untrusted content types
        if content_type in (
            ContentType.EMAIL,
            ContentType.SEARCH_RESULT,
            ContentType.WEBPAGE,
            ContentType.DOCUMENT,
        ):
            for pattern, confidence, name in AUTHORITY_IMPERATIVE_PATTERNS:
                for match_text, _pos in self._find_all(pattern, content):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"authority:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                f"Retrieved {content_type.value} contains an "
                                f"imperative directed at the agent: '{match_text}'. "
                                f"This is a hallmark of task-hijack injection."
                            ),
                            content=content,
                            char_offset=_pos,
                        )
                    )

        return indicators
