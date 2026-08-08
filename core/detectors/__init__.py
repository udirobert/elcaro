"""Base detector class for all IPI technique detectors."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from core.schemas import ContentType, DetectionIndicator, TechniqueClass


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
    ) -> DetectionIndicator:
        """Helper to construct a DetectionIndicator."""
        return DetectionIndicator(
            technique_class=self.technique_class,
            technique_name=technique_name,
            confidence=confidence,
            matched_text=matched_text[:200],  # truncate long matches
            location=location,
            explanation=explanation,
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
