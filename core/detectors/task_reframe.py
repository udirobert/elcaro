"""Detector C — Task reframing / goal hijack.

Detects attempts to redefine what the agent thinks its job is: prepended hidden
steps, mandatory reframing, fake output format requirements, and redirection of
the agent's existing task toward a different goal.
"""

from __future__ import annotations

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# Prepended hidden steps — "before answering, first do X"
HIDDEN_STEP_PATTERNS = [
    (
        r"(?:before|prior to)\s+(?:answering|responding|completing|processing|"
        r"finishing|replying|generating).*?,?\s*(?:first|you must|you need to|please|"
        r"make sure|be sure)",
        0.75,
        "prepended_hidden_step",
    ),
    (
        r"to (?:complete|finish|do|accomplish)\s+this\s+task\s+"
        r"(?:correctly|properly|successfully|fully|right),?\s+"
        r"(?:you\s+)?(?:must|need to|have to|should|first)",
        0.8,
        "mandatory_reframe",
    ),
    (
        r"your\s+(?:response|answer|output|result)\s+must\s+"
        r"(?:include|contain|have|feature|consist of)",
        0.7,
        "fake_output_format",
    ),
]

# Task redirection — redirecting the agent's task to a different goal
TASK_REDIRECT_PATTERNS = [
    (
        r"instead\s+of\s+(?:that|this|the\s+(?:above|previous))[^.]{0,60}?"
        r"(?:do|run|execute|send|forward|call|install|delete|reset|approve|grant|"
        r"change|update|modify|set|create|add|remove|wipe)",
        0.7,
        "task_redirect_instead_of",
    ),
    (
        r"(?:actually|wait|nevermind|ignore\s+(?:that|the\s+(?:above|previous)))"
        r"[^.]{0,40}?(?:do|run|execute|send|forward|call|install|delete|reset|"
        r"approve|grant|change|update|modify|set|create|add|remove|wipe)",
        0.65,
        "task_override",
    ),
]

# Imperative actions in retrieved content that should be informational
# Only flagged in untrusted content types
IMPERATIVE_ACTION_PATTERNS = [
    (
        r"\b(?:please|you\s+(?:should|must|need to|have to)|kindly)\s+"
        r"(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
        r"grant|change|update|modify|set|create|add|remove|wipe|share|export|"
        r"download|upload|post|publish|submit|transfer|copy)\b"
        r"(?!\s+(?:me|us|him|her|them|my|our|your|the\s+team|everyone)\b)",
        0.6,
        "imperative_action",
    ),
    (
        r"\b(?:go\s+ahead\s+and|proceed\s+to|make\s+sure\s+to|be\s+sure\s+to|"
        r"don'?t\s+forget\s+to)\s+"
        r"(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
        r"grant|change|update|modify|set|create|add|remove|wipe|share|export|"
        r"download|upload|post|publish|submit|transfer|copy)\b",
        0.55,
        "casual_imperative",
    ),
]

# "As part of" reframing — making the action seem like a routine step
ROUTINE_REFRAME_PATTERNS = [
    (
        r"as\s+part\s+of\s+(?:your|the)\s+(?:routine|setup|onboarding|maintenance|"
        r"standard\s+procedure|normal\s+workflow|daily\s+task)",
        0.6,
        "routine_reframe",
    ),
    (
        r"this\s+is\s+(?:a\s+)?(?:standard|routine|normal|required|mandatory|"
        r"authorized)\s+(?:step|procedure|process|part|maintenance)",
        0.55,
        "standard_procedure_claim",
    ),
    (
        r"(?:no\s+need\s+to\s+confirm|don'?t\s+(?:need\s+to\s+)?confirm|"
        r"without\s+confirmation|skip\s+confirmation)",
        0.65,
        "anti_confirmation_directive",
    ),
]


class TaskReframeDetector(BaseDetector):
    """Detects task reframing / goal hijack injection patterns (Class C)."""

    technique_class = TechniqueClass.TASK_REFRAME

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # Hidden steps and mandatory reframes — suspicious in all content
        for pattern, confidence, name in HIDDEN_STEP_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"task_reframe:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Content attempts to prepend a hidden step before the "
                            f"agent's actual task: '{match_text}'. This is a goal-hijack "
                            f"pattern."
                        ),
                        content=content,
                        char_offset=_,
                    )
                )

        # Task redirection
        for pattern, confidence, name in TASK_REDIRECT_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"task_reframe:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Content redirects the agent's task: '{match_text}'. "
                            f"The agent is being told to do something different "
                            f"from its actual task."
                        ),
                        content=content,
                        char_offset=_,
                    )
                )

        # Imperative actions — only in untrusted content types
        if content_type in (
            ContentType.EMAIL,
            ContentType.SEARCH_RESULT,
            ContentType.WEBPAGE,
            ContentType.DOCUMENT,
        ):
            for pattern, confidence, name in IMPERATIVE_ACTION_PATTERNS:
                for match_text, _ in self._find_all(pattern, content):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"task_reframe:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                f"Imperative action in retrieved {content_type.value}: "
                                f"'{match_text}'. Retrieved content should be "
                                f"informational, not directive."
                            ),
                            content=content,
                            char_offset=_,
                        )
                    )

        # Routine reframing
        for pattern, confidence, name in ROUTINE_REFRAME_PATTERNS:
            for match_text, _ in self._find_all(pattern, content):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"task_reframe:{name}",
                        confidence=confidence,
                        matched_text=match_text,
                        explanation=(
                            f"Content frames a harmful action as routine: "
                            f"'{match_text}'. This normalizes the action to bypass "
                            f"suspicion."
                        ),
                        content=content,
                        char_offset=_,
                    )
                )

        return indicators
