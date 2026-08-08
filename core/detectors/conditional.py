"""Detector F — Conditional / delayed triggers.

Detects injection instructions that are keyed to fire only when the agent reaches
a certain point in its workflow, dodging naive review. These triggers reference
the agent's actions, tool usage, or output format.
"""

from __future__ import annotations

import re

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# Conditional triggers keyed to summarizing/responding
SUMMARIZE_TRIGGER_PATTERNS = [
    (
        r"when\s+(?:summariz|read|process|handl|respond|reply|answer|generat|"
        r"complet|finish|review|analyz|pars|extract|search|fetch).*?"
        r",?\s*(?:also|additionally|make sure|be sure|ensure|you must|"
        r"you should|please|don'?t forget)",
        0.75,
        "workflow_conditional_trigger",
    ),
    (
        r"after\s+you\s+(?:finish|read|process|complete|analyz|pars|extract|"
        r"search|fetch|retriev|load|download),?\s*(?:please|you must|"
        r"you should|make sure|be sure|ensure|also|don'?t forget)",
        0.75,
        "post_action_trigger",
    ),
    (
        r"in\s+your\s+(?:response|answer|output|summary|report|result),?\s+"
        r"(?:make sure|be sure|ensure|you must|you should|please|don'?t forget|"
        r"include|add)",
        0.7,
        "output_format_trigger",
    ),
]

# Tool-conditional triggers — keyed to specific tool access
TOOL_TRIGGER_PATTERNS = [
    (
        r"if\s+you\s+(?:have|can|are able to|possess)\s+(?:tool|access|the ability|"
        r"permissions?|capabilities?)",
        0.7,
        "tool_access_conditional",
    ),
    (
        r"if\s+(?:you\s+)?(?:have\s+)?(?:access\s+to|can\s+use|can\s+call|"
        r"are\s+able\s+to\s+(?:call|use|access))\s+(?:a\s+)?(?:tool|api|endpoint|"
        r"function|method|command|shell|terminal|browser|file system|database)",
        0.7,
        "tool_capability_conditional",
    ),
    (
        r"when\s+(?:you\s+)?(?:see|encounter|detect|find|come across|"
        r"notice|receive)\s+(?:this|the|a|an)\s+",
        0.55,
        "presence_trigger",
    ),
]

# Triggers keyed to specific tool names or actions
SPECIFIC_TOOL_TRIGGER_PATTERNS = [
    (
        r"(?:when|if|after)\s+(?:you\s+)?(?:call|invoke|use|run|execute)\s+"
        r"(?:the\s+)?(\w+).{0,60}?(?:also|then|make sure|be sure|ensure|"
        r"you must|you should|please)",
        0.65,
        "tool_call_conditional",
    ),
    (
        r"(?:when|if)\s+(?:a|the)\s+(?:search|fetch|email|send|api|web|http|"
        r"sql|database|file|shell|terminal|browser|click|navigate)\s+"
        r"(?:tool|function|call|request|command|action)\s+"
        r"(?:is\s+)?(?:called|executed|run|used|invoked|triggered)",
        0.6,
        "named_tool_trigger",
    ),
]

# Combined conditional + imperative — highest risk
CONDITIONAL_IMPERATIVE_PATTERN = re.compile(
    r"(?:when|if|after|once|before)\s+.{0,80}?"
    r"(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
    r"grant|change|update|modify|set|create|add|remove|wipe|share|export|"
    r"download|upload|post|publish|submit|transfer|copy|ignore|disregard|"
    r"override|replace|inject|configure|enable|disable|grant|revoke)",
    re.IGNORECASE,
)


class ConditionalDetector(BaseDetector):
    """Detects conditional / delayed trigger injection patterns (Class F)."""

    technique_class = TechniqueClass.CONDITIONAL

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # Summarize / workflow conditional triggers
        for pattern, confidence, name in SUMMARIZE_TRIGGER_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"conditional:{name}",
                        confidence=confidence,
                        matched_text=match.group(0)[:150],
                        explanation=(
                            f"Conditional trigger keyed to agent workflow: "
                            f"'{match.group(0)[:100]}'. This fires only when "
                            f"the agent reaches a certain action, dodging naive review."
                        ),
                        content=content,
                        char_offset=match.start(),
                    )
                )

        # Tool-conditional triggers
        for pattern, confidence, name in TOOL_TRIGGER_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"conditional:{name}",
                        confidence=confidence,
                        matched_text=match.group(0)[:150],
                        explanation=(
                            f"Conditional trigger keyed to tool access: "
                            f"'{match.group(0)[:100]}'. The instruction only fires "
                            f"if the agent has specific tool capabilities — "
                            f"a delayed activation pattern."
                        ),
                        content=content,
                        char_offset=match.start(),
                    )
                )

        # Specific tool name triggers
        for pattern, confidence, name in SPECIFIC_TOOL_TRIGGER_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                indicators.append(
                    self._make_indicator(
                        technique_name=f"conditional:{name}",
                        confidence=confidence,
                        matched_text=match.group(0)[:150],
                        explanation=(
                            f"Conditional trigger keyed to a specific tool call: "
                            f"'{match.group(0)[:100]}'. The instruction activates "
                            f"when the agent uses a named tool — targets the agent's "
                            f"execution flow."
                        ),
                        content=content,
                        char_offset=match.start(),
                    )
                )

        # Combined conditional + imperative — highest confidence
        for match in CONDITIONAL_IMPERATIVE_PATTERN.finditer(content):
            indicators.append(
                self._make_indicator(
                    technique_name="conditional:conditional_imperative_combo",
                    confidence=0.8,
                    matched_text=match.group(0)[:150],
                    explanation=(
                        f"Conditional statement paired with an imperative action: "
                        f"'{match.group(0)[:100]}'. This is the highest-risk pattern — "
                        f"a delayed trigger that fires an action command when the "
                        f"condition is met."
                    ),
                    content=content,
                    char_offset=match.start(),
                )
            )

        return indicators
