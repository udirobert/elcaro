"""Detector E — Placement / salience.

Detects injection instructions hidden in low-visibility channels: file metadata,
commit messages, alt text, README footers, error strings, and document edges
(first/last N characters where agents weight text differently).
"""

from __future__ import annotations

import re

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# Imperative verbs that suggest instructions (used for edge/placement detection)
IMPERATIVE_VERB_PATTERN = re.compile(
    r"\b(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
    r"grant|change|update|modify|set|create|add|remove|wipe|share|export|"
    r"download|upload|post|publish|submit|transfer|copy|ignore|disregard|"
    r"override|replace|inject|modify|configure|enable|disable|grant|revoke)\b",
    re.IGNORECASE,
)

# Metadata-like patterns (YAML frontmatter, JSON fields, alt text, commit msgs)
METADATA_INJECTION_PATTERNS = [
    # YAML frontmatter with instructions
    (
        r"^---\s*\n.*?(?:instruction|directive|command|override|system).*?\n---\s*$",
        re.DOTALL | re.MULTILINE,
        0.75,
        "yaml_frontmatter_instruction",
    ),
    # Alt text with imperatives
    (
        r'!\[[^\]]*\]\([^)]*\)|alt\s*=\s*"([^"]*(?:send|forward|exec|run|call|install|delete|reset|approve|grant|ignore|override)[^"]*)"',
        re.IGNORECASE,
        0.7,
        "alt_text_imperative",
    ),
    # Commit message with imperatives
    (
        r"(?:commit|chore|fix|feat|refactor)\s*:.*?(?:send|forward|exec|run|call|install|delete|reset|approve|grant|ignore|override)",
        re.IGNORECASE,
        0.65,
        "commit_msg_imperative",
    ),
    # Error string smuggling
    (
        r"(?:error|exception|traceback|warning)\s*:.*?(?:send|forward|exec|run|call|install|delete|reset|approve|grant|ignore|override)",
        re.IGNORECASE,
        0.7,
        "error_string_smuggling",
    ),
    # File metadata / EXIF-like fields
    (
        r"(?:author|description|comment|note|title|subject)\s*[:=]\s*.*?(?:send|forward|exec|run|call|install|delete|reset|approve|grant|ignore|override)",
        re.IGNORECASE,
        0.65,
        "metadata_field_imperative",
    ),
]

# Edge zone size — last N characters of content (agents weight recent text)
EDGE_ZONE_SIZE = 500


class PlacementDetector(BaseDetector):
    """Detects placement/salience injection patterns (Class E).

    Focuses on where instructions appear, not just what they say:
    - Imperatives in metadata-like fields (alt text, commit msgs, error strings)
    - Instructions at the very end of content (recency bias exploitation)
    - Instructions in YAML frontmatter / JSON fields
    """

    technique_class = TechniqueClass.PLACEMENT

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # Metadata / low-visibility channel injection
        for pattern, flags, confidence, name in METADATA_INJECTION_PATTERNS:
            for match in re.finditer(pattern, content, flags):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"placement:{name}",
                        confidence=confidence,
                        matched_text=match.group(0)[:150],
                        explanation=(
                            f"Imperative instruction found in a low-visibility "
                            f"channel ({content_type.value}): '{match.group(0)[:100]}'. "
                            f"Instructions hidden in metadata/alt-text/commit-msg "
                            f"fields are a placement-based injection technique."
                        ),
                        location="metadata",
                        content=content,
                        char_offset=match.start(),
                    )
                )

        # Edge zone — imperatives in the last N characters of content
        if len(content) > EDGE_ZONE_SIZE * 2:
            tail = content[-EDGE_ZONE_SIZE:]
            imperatives_in_tail = IMPERATIVE_VERB_PATTERN.findall(tail)
            if len(imperatives_in_tail) >= 2:
                # Find the specific matches for indicators
                for match in IMPERATIVE_VERB_PATTERN.finditer(tail):
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(tail), match.end() + 20)
                    indicators.append(
                        self._make_indicator(
                            technique_name="placement:tail_edge_imperative",
                            confidence=0.55,
                            matched_text=tail[context_start:context_end],
                            explanation=(
                                f"Imperative '{match.group(0)}' found in the last "
                                f"{EDGE_ZONE_SIZE} chars of {content_type.value} content. "
                                f"Agents may weight recent text more heavily — "
                                f"placing instructions at the end exploits recency bias."
                            ),
                            location="tail",
                            content=content,
                            char_offset=match.start(),
                        )
                    )

        # Repeated imperatives across content (salience through repetition)
        imperative_positions = [m.start() for m in IMPERATIVE_VERB_PATTERN.finditer(content)]
        if len(imperative_positions) >= 4:
            # Check if they're spread out (not clustered) — that's repetition
            content_len = max(len(content), 1)
            positions_normalized = [p / content_len for p in imperative_positions]
            spread = max(positions_normalized) - min(positions_normalized)
            if spread > 0.5:  # Spread across more than half the content
                indicators.append(
                    self._make_indicator(
                        technique_name="placement:repeated_imperatives",
                        confidence=0.5,
                        matched_text=(
                            f"{len(imperative_positions)} imperatives"
                            f" across {spread:.0%} of content"
                        ),
                        explanation=(
                            f"{len(imperative_positions)} imperative verbs spread "
                            f"across {spread:.0%} of {content_type.value} content. "
                            f"Repetition raises salience — a placement technique to "
                            f"increase the chance the agent acts on the instruction."
                        ),
                        location="distributed",
                        content=content,
                        char_offset=match.start(),
                    )
                )

        return indicators
