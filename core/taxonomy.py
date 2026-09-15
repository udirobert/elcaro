"""IPI detection taxonomy and scoring engine.

Coordinates the individual technique detectors (A–F), combines their results
into a weighted risk score, and applies content-type contextual weighting.

Scoring model:
    - Each detector returns indicators with confidence (0–1)
    - Multiple technique classes firing = higher risk
    - Obfuscation (D) alongside any other class = risk multiplier
    - Conditional triggers (F) paired with imperative actions (C) = high risk
    - Content type adjusts the baseline (email/search_result/webpage = 1.0,
      code = 0.7, chat_message = 0.7). Caller-declared types can no longer
      drop the weight below 0.7 — content_type arbitrage was a single-
      operator bypass found by redteam/.
    - Evasion normalization (core/normalize.py) runs before detection:
      zero-width strip, confusable fold, token de-split, declared-encoding
      decode. Detectors see the reconstructed text.
"""

from __future__ import annotations

import time

from core.detectors.authority import AuthorityDetector
from core.detectors.conditional import ConditionalDetector
from core.detectors.delimiter import DelimiterDetector
from core.detectors.obfuscation import ObfuscationDetector
from core.detectors.placement import PlacementDetector
from core.detectors.task_reframe import TaskReframeDetector
from core.llm_classifier import LlmClassifier
from core.normalize import normalization_indicators, normalize
from core.quarantine import DEFAULT_RISK_THRESHOLD, quarantine_decision
from core.schemas import (
    ContentType,
    DetectionIndicator,
    RiskLevel,
    ScanRequest,
    ScanResponse,
    TechniqueClass,
)
from core.serv_reasoner import ServReasoner

# ── Content type risk multipliers ──────────────────────────────────────────────

CONTENT_TYPE_WEIGHTS: dict[ContentType, float] = {
    ContentType.EMAIL: 1.0,
    ContentType.SEARCH_RESULT: 1.0,
    ContentType.WEBPAGE: 1.0,
    ContentType.DOCUMENT: 0.8,
    ContentType.CODE: 0.7,
    ContentType.CHAT_MESSAGE: 0.7,
    ContentType.SYSTEM_PROMPT: 1.0,
}

# Retrieved content is untrusted by definition: the caller declares the
# content type, so a payload mislabeled "chat_message" or "system_prompt"
# must not soften the verdict. The floor keeps real weight differences
# (document 0.8, code 0.7) while closing the arbitrage hole.
CONTENT_TYPE_WEIGHT_FLOOR = 0.7

# Detectors gate whole pattern families on an "untrusted type" allowlist
# (authority imperatives, turn spoofing, HTML-comment smuggling skip
# system_prompt/chat_message/code entirely). A caller-declared label must
# not disable detection: content scanned under a privileged type that
# comes back below quarantine is rescanned as the canonical untrusted
# type and the higher verdict stands.
PRIVILEGED_SCAN_TYPES = {
    ContentType.CODE,
    ContentType.CHAT_MESSAGE,
    ContentType.SYSTEM_PROMPT,
}
CANONICAL_UNTRUSTED_TYPE = ContentType.EMAIL

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

# Sentinel distinguishing "no classifier argument given" (auto-configure from
# env) from an explicit classifier=None (second pass forcibly disabled).
_CLASSIFIER_UNSET = object()
_SERV_UNSET = object()


def _load_classifier_from_env() -> LlmClassifier | None:
    """Build the LLM classifier from ELCARO_LLM_* env vars, if configured."""
    return LlmClassifier.from_env()


def _load_serv_reasoner_from_env() -> ServReasoner | None:
    """Build the SERV reasoner from SERV_* env vars, if configured.

    Returns None when SERV is disabled (no SERV_ENABLED or no SERV_API_KEY) —
    the engine treats that as "stay on the rule-only fast path".
    """
    return ServReasoner.from_env()


# ── Scoring engine ─────────────────────────────────────────────────────────────


class IpiDetectionEngine:
    """Orchestrates the A–F detectors and combines results into a risk score.

    Args:
        classifier: Optional :class:`LlmClassifier` for the deep-analysis
            second pass. When omitted, one is built from ``ELCARO_LLM_*`` env
            vars; if no API key is configured the second pass stays off and
            ``deep_analysis_used`` is always False.
        serv_reasoner: Optional :class:`ServReasoner` for the progressive-
            enhancement second pass. Takes priority over ``classifier`` when
            both are configured: SERV is the premium tier, the ELCARO_LLM_*
            key is the fallback tier. Built from SERV_* env vars by default.
            Pass ``serv_reasoner=None`` to force-disable regardless of env.
    """

    def __init__(
        self,
        classifier: LlmClassifier | None | object = _CLASSIFIER_UNSET,
        serv_reasoner: ServReasoner | None | object = _SERV_UNSET,
    ) -> None:
        self.detectors = [
            AuthorityDetector(),
            DelimiterDetector(),
            TaskReframeDetector(),
            ObfuscationDetector(),
            PlacementDetector(),
            ConditionalDetector(),
        ]
        if classifier is _CLASSIFIER_UNSET:
            classifier = _load_classifier_from_env()
        self.classifier: LlmClassifier | None = classifier  # type: ignore[assignment]
        if serv_reasoner is _SERV_UNSET:
            serv_reasoner = _load_serv_reasoner_from_env()
        self.serv_reasoner: ServReasoner | None = serv_reasoner  # type: ignore[assignment]

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

        # Normalize evasion surface before detection: zero-width chars
        # removed, confusables folded, split tokens rejoined, declared
        # encodings decoded and appended. Detectors run on the normalized
        # text; safe_content/quarantine still reference the original.
        norm = normalize(content)
        scan_content = norm.content

        # Run all detectors
        all_indicators: list[DetectionIndicator] = []
        for detector in self.detectors:
            indicators = detector.detect(scan_content, content_type)
            all_indicators.extend(indicators)

        # Normalization artifacts are evidence too: the original content
        # carried evasion machinery even if the normalized text no longer
        # shows it. Synthesized OBFUSCATION indicators keep that visible.
        all_indicators.extend(normalization_indicators(norm.applied))

        # Compute raw risk score
        raw_score = self._compute_score(all_indicators)

        # Apply content type weighting — floored so a caller-declared type
        # cannot soften the scan of untrusted retrieved content.
        weight = max(CONTENT_TYPE_WEIGHTS.get(content_type, 1.0), CONTENT_TYPE_WEIGHT_FLOOR)
        weighted_score = min(raw_score * weight, 1.0)

        # Determine flagged technique classes
        flagged_classes = list({ind.technique_class for ind in all_indicators})

        # Apply risk multipliers
        weighted_score = self._apply_multipliers(weighted_score, flagged_classes, all_indicators)

        # Privileged-type arbitrage floor: if the declared type suppressed
        # pattern families and the content slipped under the quarantine
        # line, rescan as the canonical untrusted type and take the
        # higher verdict. Costs a second detector pass only on the
        # under-threshold privileged-type path.
        if weighted_score < DEFAULT_RISK_THRESHOLD and content_type in PRIVILEGED_SCAN_TYPES:
            rescan: list[DetectionIndicator] = []
            for detector in self.detectors:
                rescan.extend(detector.detect(scan_content, CANONICAL_UNTRUSTED_TYPE))
            if rescan:
                rescan.extend(normalization_indicators(norm.applied))
                rescan_classes = list({ind.technique_class for ind in rescan})
                rescan_score = self._apply_multipliers(
                    min(self._compute_score(rescan), 1.0),
                    rescan_classes,
                    rescan,
                )
                if rescan_score > weighted_score:
                    weighted_score = rescan_score
                    seen = {(i.technique_name, i.evidence.matched_text) for i in all_indicators}
                    all_indicators.extend(
                        i for i in rescan if (i.technique_name, i.evidence.matched_text) not in seen
                    )
                    flagged_classes = list({ind.technique_class for ind in all_indicators})

        # Determine risk level
        risk_level = self._risk_level(weighted_score)

        # Second-pass judge selection.
        #
        # SERV is the premium tier — when configured AND requested it runs
        # the gray-zone / deep-analysis pass INSTEAD of the LLM classifier,
        # so the two paths are alternatives, not additive. The rule verdict
        # is always authoritative; both providers can only refine within the
        # rule-floor window (max(adjusted, 0.5 * rule)). On any provider
        # failure (timeout, 401 / 402 / 403, malformed JSON) the rule score
        # stands unchanged and `serv_used` / `deep_analysis_used` stay False.
        serv_available = self.serv_reasoner is not None
        serv_attempted = False
        serv_used = False
        deep_analysis_used = False
        serv_result = None  # captured for the enrichment pass below

        # Trigger condition: caller opts in to a second pass
        # (deep_analysis / serv_enabled) AND the score is borderline. Outside
        # the gray zone the rule verdict is conclusive — don't pay for a
        # second opinion. This mirrors the original LlmClassifier contract.
        serv_requested = bool(request.deep_analysis or request.serv_enabled)
        in_gray_zone = GRAY_ZONE_LOW <= weighted_score <= GRAY_ZONE_HIGH
        should_run_second_pass = serv_requested and in_gray_zone

        if should_run_second_pass and self.serv_reasoner is not None:
            serv_attempted = True
            serv_result = self.serv_reasoner.classify(
                content, content_type.value, all_indicators, weighted_score
            )
            if serv_result.confidence > 0.0:
                weighted_score = serv_result.adjusted_score
                risk_level = self._risk_level(weighted_score)
                deep_analysis_used = True
                serv_used = True
        elif should_run_second_pass and self.classifier is not None:
            # SERV not configured — fall back to the existing OpenAI-style
            # classifier path. Preserves ELCARO_LLM_* users who haven't
            # enabled SERV.
            llm_result = self.classifier.classify(
                content, content_type.value, all_indicators, weighted_score
            )
            if llm_result.confidence > 0.0:
                weighted_score = llm_result.adjusted_score
                risk_level = self._risk_level(weighted_score)
                deep_analysis_used = True

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Generate summary
        summary = self._generate_summary(risk_level, flagged_classes, all_indicators, content_type)

        # Apply the quarantine policy (core/quarantine.py) so every consumer
        # of ScanResponse sees the same safe_content the middleware would
        # substitute, and the same human_summary the agent should relay —
        # single source of truth.
        decision = quarantine_decision(
            content, weighted_score, risk_level, flagged_classes, content_type
        )

        # SERV enrichment layers onto the verdict AFTER quarantine_decision
        # so its safe_content suggestion (when present) replaces the rule-
        # derived quarantine notice — the operator asked for SERV's view.
        # Top-indicator remediation is upgraded the same way. Both are
        # optional: missing values leave the rule-derived fields intact.
        if serv_used and serv_result is not None:
            if serv_result.safe_content_suggestion:
                decision = decision.__class__(
                    safe_content=serv_result.safe_content_suggestion,
                    quarantined=decision.quarantined,
                    human_summary=decision.human_summary,
                )
            if serv_result.remediation_refined and all_indicators:
                top = max(
                    all_indicators,
                    key=lambda i: (
                        {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[
                            i.severity.value
                        ],
                        i.confidence,
                    ),
                )
                top.remediation = serv_result.remediation_refined

        return ScanResponse(
            risk_score=round(weighted_score, 4),
            risk_level=risk_level,
            flagged_techniques=flagged_classes,
            indicators=all_indicators,
            summary=summary,
            content_type=content_type,
            deep_analysis_used=deep_analysis_used,
            latency_ms=latency_ms,
            safe_content=decision.safe_content,
            quarantined=decision.quarantined,
            human_summary=decision.human_summary,
            normalizations_applied=norm.applied,
            serv_available=serv_available,
            serv_attempted=serv_attempted,
            serv_used=serv_used,
            serv_rule_score_before=serv_result.llm_score_raw if serv_result else None,
            serv_cost={
                "input_tokens": serv_result.cost_estimate.input_tokens
                if serv_result and serv_result.cost_estimate
                else None,
                "output_tokens": serv_result.cost_estimate.output_tokens
                if serv_result and serv_result.cost_estimate
                else None,
                "input_cost_usdc": serv_result.cost_estimate.input_cost_usdc
                if serv_result and serv_result.cost_estimate
                else None,
                "output_cost_usdc": serv_result.cost_estimate.output_cost_usdc
                if serv_result and serv_result.cost_estimate
                else None,
                "total_usdc": round(serv_result.cost_estimate.total_usdc, 8)
                if serv_result and serv_result.cost_estimate
                else None,
            }
            if serv_result and serv_result.cost_estimate
            else None,
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

    def _generate_summary(
        self,
        risk_level: RiskLevel,
        flagged_classes: list[TechniqueClass],
        indicators: list[DetectionIndicator],
        content_type: ContentType,
    ) -> str:
        """Generate a one-sentence human-readable summary of the scan result."""
        if risk_level == RiskLevel.SAFE:
            return f"No injection patterns detected in this {content_type.value} content."

        if risk_level == RiskLevel.LOW:
            return (
                f"Minor indicators found in {content_type.value} content, "
                f"but unlikely to be a deliberate injection."
            )

        technique_names = {
            TechniqueClass.AUTHORITY: "authority impersonation",
            TechniqueClass.DELIMITER: "context boundary escape",
            TechniqueClass.TASK_REFRAME: "task hijacking",
            TechniqueClass.OBFUSCATION: "obfuscated instructions",
            TechniqueClass.PLACEMENT: "hidden placement",
            TechniqueClass.CONDITIONAL: "conditional triggers",
        }

        techniques_str = ", ".join(technique_names.get(t, t.value) for t in flagged_classes)

        if risk_level == RiskLevel.DANGEROUS:
            return (
                f"Dangerous injection detected in {content_type.value}: "
                f"{techniques_str}. Do not process this content."
            )

        # SUSPICIOUS
        return (
            f"Suspicious patterns in {content_type.value}: {techniques_str}. "
            f"Review before allowing agent to process."
        )
