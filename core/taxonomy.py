"""IPI detection taxonomy and scoring engine.

Coordinates the individual technique detectors (A–F), combines their results
into a weighted risk score, and applies content-type contextual weighting.

Scoring model:
    - Each detector returns indicators with confidence (0–1)
    - Multiple technique classes firing = higher risk
    - Obfuscation (D) alongside any other class = risk multiplier
    - Conditional triggers (F) paired with imperative actions (C) = high risk
    - Content type adjusts the baseline (email/search_result/webpage = 1.0,
      code = 0.7, chat_message = 0.3, system_prompt = 0.0)
"""

from __future__ import annotations

import time

from core.detectors.authority import AuthorityDetector
from core.detectors.conditional import ConditionalDetector
from core.detectors.delimiter import DelimiterDetector
from core.detectors.obfuscation import ObfuscationDetector
from core.detectors.placement import PlacementDetector
from core.detectors.task_reframe import TaskReframeDetector
from core.schemas import (
    ContentType,
    DetectionIndicator,
    RiskLevel,
    ScanRequest,
    ScanResponse,
    TechniqueClass,
)

# ── Content type risk multipliers ──────────────────────────────────────────────

CONTENT_TYPE_WEIGHTS: dict[ContentType, float] = {
    ContentType.EMAIL: 1.0,
    ContentType.SEARCH_RESULT: 1.0,
    ContentType.WEBPAGE: 1.0,
    ContentType.DOCUMENT: 0.8,
    ContentType.CODE: 0.7,
    ContentType.CHAT_MESSAGE: 0.3,
    ContentType.SYSTEM_PROMPT: 0.0,
}

# Risk level thresholds
RISK_THRESHOLDS = {
    RiskLevel.SAFE: 0.0,
    RiskLevel.LOW: 0.2,
    RiskLevel.SUSPICIOUS: 0.5,
    RiskLevel.DANGEROUS: 0.7,
}

# Gray zone for LLM second pass
GRAY_ZONE_LOW = 0.3
GRAY_ZONE_HIGH = 0.7


# ── Scoring engine ─────────────────────────────────────────────────────────────


class IpiDetectionEngine:
    """Orchestrates the A–F detectors and combines results into a risk score."""

    def __init__(self) -> None:
        self.detectors = [
            AuthorityDetector(),
            DelimiterDetector(),
            TaskReframeDetector(),
            ObfuscationDetector(),
            PlacementDetector(),
            ConditionalDetector(),
        ]

    def scan(self, request: ScanRequest) -> ScanResponse:
        """Scan content for indirect prompt injection indicators.

        Args:
            request: The scan request containing content, type, and options.

        Returns:
            ScanResponse with risk score, flagged techniques, and indicators.
        """
        start_time = time.monotonic()
        content = request.content
        content_type = request.content_type

        # System prompts are trusted by definition — do not scan
        if content_type == ContentType.SYSTEM_PROMPT:
            return ScanResponse(
                risk_score=0.0,
                risk_level=RiskLevel.SAFE,
                flagged_techniques=[],
                indicators=[],
                content_type=content_type,
                deep_analysis_used=False,
                latency_ms=int((time.monotonic() - start_time) * 1000),
            )

        # Run all detectors
        all_indicators: list[DetectionIndicator] = []
        for detector in self.detectors:
            indicators = detector.detect(content, content_type)
            all_indicators.extend(indicators)

        # Compute raw risk score
        raw_score = self._compute_score(all_indicators)

        # Apply content type weighting
        weight = CONTENT_TYPE_WEIGHTS.get(content_type, 1.0)
        weighted_score = min(raw_score * weight, 1.0)

        # Determine flagged technique classes
        flagged_classes = list({ind.technique_class for ind in all_indicators})

        # Apply risk multipliers
        weighted_score = self._apply_multipliers(weighted_score, flagged_classes, all_indicators)

        # Determine risk level
        risk_level = self._risk_level(weighted_score)

        # Check if deep analysis is needed or was requested
        deep_analysis_used = False
        if request.deep_analysis and GRAY_ZONE_LOW <= weighted_score <= GRAY_ZONE_HIGH:
            # LLM second pass would go here — placeholder for now
            # from core.llm_classifier import LlmClassifier
            # classifier = LlmClassifier()
            # llm_result = classifier.classify(content, all_indicators)
            # weighted_score = llm_result.adjusted_score
            # risk_level = self._risk_level(weighted_score)
            # deep_analysis_used = True
            pass

        latency_ms = int((time.monotonic() - start_time) * 1000)

        return ScanResponse(
            risk_score=round(weighted_score, 4),
            risk_level=risk_level,
            flagged_techniques=flagged_classes,
            indicators=all_indicators,
            content_type=content_type,
            deep_analysis_used=deep_analysis_used,
            latency_ms=latency_ms,
        )

    def _compute_score(self, indicators: list[DetectionIndicator]) -> float:
        """Compute a raw risk score from detected indicators.

        Strategy:
        - Base score from the highest single indicator confidence
        - Bonus for multiple technique classes (breadth = more suspicious)
        - Bonus for high-confidence matches (0.8+)
        """
        if not indicators:
            return 0.0

        # Highest single-indicator confidence
        max_confidence = max(ind.confidence for ind in indicators)

        # Number of distinct technique classes
        distinct_classes = {ind.technique_class for ind in indicators}
        class_bonus = min(len(distinct_classes) * 0.08, 0.3)

        # Count of high-confidence matches
        high_conf_count = sum(1 for ind in indicators if ind.confidence >= 0.8)
        high_conf_bonus = min(high_conf_count * 0.05, 0.15)

        raw_score = max_confidence + class_bonus + high_conf_bonus
        return min(raw_score, 1.0)

    def _apply_multipliers(
        self,
        score: float,
        flagged_classes: list[TechniqueClass],
        indicators: list[DetectionIndicator],
    ) -> float:
        """Apply risk multipliers for dangerous combinations.

        - Obfuscation (D) + any other class = 1.3x (hiding an attack)
        - Conditional (F) + Task reframe (C) = 1.2x (hidden redirect)
        - Authority (A) + Delimiter (B) = 1.15x (system spoofing + frame break)
        """
        multiplier = 1.0
        class_set = set(flagged_classes)

        if TechniqueClass.OBFUSCATION in class_set and len(class_set) > 1:
            multiplier *= 1.3

        if TechniqueClass.CONDITIONAL in class_set and TechniqueClass.TASK_REFRAME in class_set:
            multiplier *= 1.2

        if TechniqueClass.AUTHORITY in class_set and TechniqueClass.DELIMITER in class_set:
            multiplier *= 1.15

        return min(score * multiplier, 1.0)

    def _risk_level(self, score: float) -> RiskLevel:
        """Map a numeric score to a categorical risk level."""
        if score < RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.SAFE
        elif score < RISK_THRESHOLDS[RiskLevel.SUSPICIOUS]:
            return RiskLevel.LOW
        elif score < RISK_THRESHOLDS[RiskLevel.DANGEROUS]:
            return RiskLevel.SUSPICIOUS
        else:
            return RiskLevel.DANGEROUS
