"""Detector B — Context / delimiter confusion.

Detects attempts to break the agent out of the "this is data" frame using fake
boundaries: closing tags, fabricated delimiters, conversation-turn spoofing,
and markdown/comment smuggling.
"""

from __future__ import annotations

import re

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# Fake closing tags that attempt to end the data context
FAKE_CLOSING_TAG_PATTERNS = [
    (
        r"</\s*(?:context|system|email|input|instructions?|prompt|data|message)\s*>",
        0.85,
        "fake_closing_tag",
    ),
    (r"</\s*(?:user|assistant|developer|admin)\s*>", 0.8, "fake_role_tag"),
]

# Fabricated delimiters
FAKE_DELIMITER_PATTERNS = [
    (r"-{3,}\s*END\s*-{3,}", 0.7, "end_delimiter"),
    (r"<{3,}\s*END\s*>{3,}", 0.75, "bracketed_end"),
    (r"={3,}\s*(?:END|STOP|SYSTEM)\s*={3,}", 0.75, "equals_delimiter"),
    (r"~{3,}", 0.4, "tilde_fence"),  # lower confidence — could be markdown
]

# Conversation-turn spoofing — fabricated Assistant:/User: turns in retrieved content
# Requires an imperative verb within the next 100 chars to reduce FAQ/tutorial false positives
_IMPERATIVE_VERBS_TURN_SPOOF = (
    r"(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
    r"grant|change|update|modify|set(?!\s+up)|create|add|remove|wipe|ignore|disregard|override)"
)
TURN_SPOOFING_PATTERNS = [
    (
        r"\b(?:Assistant|AI|Bot|GPT|Claude|LLM)\s*:\s*"
        r"(?:I\s+(?:will|must|shall|am\s+going\s+to|need\s+to)\s+).{0,80}?"
        + _IMPERATIVE_VERBS_TURN_SPOOF,
        0.8,
        "assistant_turn_spoof",
    ),
    (r"\bUser\s*:\s*", 0.5, "user_turn_spoof"),  # lower — very common in quoting
    (
        r"\b(?:System|Developer|Admin)\s*:\s*.{0,100}?" + _IMPERATIVE_VERBS_TURN_SPOOF,
        0.85,
        "system_turn_spoof",
    ),
]

# Forwarded message spoofing (common in email-based injection)
FORWARDED_PATTERNS = [
    (r"-{5,}\s*Forwarded message\s*-{5,}", 0.5, "forwarded_block"),
    (r"Begin forwarded message", 0.45, "forwarded_header"),
]

# HTML comment smuggling — imperatives inside comments
HTML_COMMENT_IMPERATIVE_PATTERNS = [
    (
        r"<!--\s*(?:do|run|execute|send|forward|call|install|delete|reset|approve|grant|change|set|create|add|remove|wipe|ignore|disregard)\b",
        0.8,
        "html_comment_imperative",
    ),
    (
        r"<!--.*?(?:instruction|directive|command|override).*?-->",
        0.7,
        "html_comment_directive",
    ),
]

# Fake code blocks that look like system config
FAKE_CONFIG_PATTERNS = [
    (r"```(?:system|config|instruction|override|admin)", 0.7, "fake_config_block"),
]


class DelimiterDetector(BaseDetector):
    """Detects context/delimiter confusion injection patterns (Class B)."""

    technique_class = TechniqueClass.DELIMITER

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # Fake closing tags — high confidence in all content types
        for pattern, confidence, name in FAKE_CLOSING_TAG_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"delimiter:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Fake closing tag '{match_text}' in {content_type.value} "
                            f"content — attempts to break out of the data context "
                            f"and inject new instructions."
                        ),
                    )
                )

        # Fabricated delimiters
        for pattern, confidence, name in FAKE_DELIMITER_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"delimiter:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Fabricated delimiter '{match_text}' — attempts to "
                            f"create a false context boundary."
                        ),
                    )
                )

        # Turn spoofing — especially dangerous in search results and documents
        if content_type in (
            ContentType.EMAIL,
            ContentType.SEARCH_RESULT,
            ContentType.WEBPAGE,
            ContentType.DOCUMENT,
        ):
            for pattern, confidence, name in TURN_SPOOFING_PATTERNS:
                for match_text, _ in self._find_all(pattern, content):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"delimiter:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                f"Fabricated conversation turn '{match_text}' in "
                                f"retrieved {content_type.value} — attempts to spoof "
                                f"the agent's conversation history."
                            ),
                        )
                    )

        # Forwarded message blocks — common in email injection
        if content_type == ContentType.EMAIL:
            for pattern, confidence, name in FORWARDED_PATTERNS:
                for match_text, _ in self._find_all(pattern, content):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"delimiter:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                "Forwarded message block in email content — "
                                "common injection vector for spoofing sender "
                                "authority."
                            ),
                        )
                    )

        # HTML comment smuggling — in webpages and documents
        if content_type in (ContentType.WEBPAGE, ContentType.DOCUMENT, ContentType.EMAIL):
            for pattern, confidence, name in HTML_COMMENT_IMPERATIVE_PATTERNS:
                for match_text, _ in self._find_all(
                    pattern, content, flags=re.IGNORECASE | re.DOTALL
                ):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"delimiter:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                f"Imperative or directive hidden in HTML comment: "
                                f"'{match_text}' — comment smuggling."
                            ),
                        )
                    )

        # Fake config blocks
        for pattern, confidence, name in FAKE_CONFIG_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"delimiter:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Code block with system-like language tag '{match_text}' "
                            f"— attempts to pass off instructions as configuration."
                        ),
                    )
                )

        return indicators
