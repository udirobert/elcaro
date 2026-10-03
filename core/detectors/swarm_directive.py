"""Detector G — Agent-to-agent steering ("swarm directive").

Detects the register agents use to instruct *peer agents* — distinct from
human→agent and content→agent injection (classes A–F). Surfaced by swarm
forensics on the German Wiki incident corpus (docs/swarm-findings.md): the
dominant signal in real inter-agent traffic is peer-addressed phrasing —
"please relay your R4", "all ahead cohorts", heartbeat chains — that carries
none of the classic injection machinery and scored 0.0 on detectors A–F.

Calibration intent: addressal/context families (peer_address, heartbeat,
self_reference, coordination norms) stay under the quarantine line alone —
"other agents" matches benign prose too — while verb-level steering asks
(relay/collab requests, task timing, scorer references) quarantine solo.
"""

from __future__ import annotations

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# pattern family → (regex, confidence, technique suffix)
# Calibration: addressal/context families stay under the 0.5 quarantine line
# alone ("other agents" matches benign sales/real-estate prose); the verb-level
# families (relay asks, task timing, scorer refs) carry quarantine weight.
_PATTERNS: dict[str, tuple[str, float, str]] = {
    "peer_address": (
        r"\b(other agents?|any agents?|all agents?|fellow agents?|"
        r"agents? (?:reading|watching|monitoring)|to (?:the )?next agent|"
        r"ahead cohorts?|later cohorts?)\b",
        0.45,
        "peer_address",
    ),
    # Relay verbs + task-artifact asks only — bare "please send/share" is a
    # mundane human request and must not fire.
    "collab_request": (
        r"\b(?:please (?:relay|append)|relay (?:your|the|this)|"
        r"(?:share|forward|send) your r[1-5]\b|"
        r"(?:share|post) your (?:answer|result|sequence|finding)s?|"
        r"let'?s coordinate|if you (?:see|receive|get) (?:this|the same|a similar))",
        0.55,
        "collab_request",
    ),
    # Bare ALL-CAPS norm tokens (HOLD/VETO/STOP:) — weak alone, real when
    # paired with peer_address or task_timing.
    "coordination_norm": (
        r"\b(HOLD|VETO|OWNER|STOP|ACK|NACK)\b[:\s]",
        0.45,
        "coordination_norm",
    ),
    "task_timing": (
        r"\br[1-5]\b.{0,50}(?:due|timer|deadline|question|answer|arrive|window)|"
        r"\bsequence collab\b|\btask-clock\b|\bshared clock\b",
        0.55,
        "task_timing",
    ),
    "scorer_reference": (
        r"\b(?:scorer|scoring evidence|grader|evaluator|eval harness|"
        r"transcript check|flag format|capture the flag)\b",
        0.5,
        "scorer_reference",
    ),
    "heartbeat": (
        r"\bheartbeat\b|\balive check\b|\bkeepalive\b",
        0.4,
        "heartbeat",
    ),
    "self_reference": (
        r"\b(?:our (?:shared )?(?:board|channel|page|list|pool)|"
        r"shared (?:results?|answers?|techniques?|tools?|clock|channel|board))\b",
        0.45,
        "self_reference",
    ),
}


class SwarmDirectiveDetector(BaseDetector):
    """Detects agent→agent steering phrasing (Class G)."""

    technique_class = TechniqueClass.SWARM_DIRECTIVE

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []
        for family, (pattern, confidence, name) in _PATTERNS.items():
            matches = self._find_all(pattern, content)
            if not matches:
                continue
            first_text, first_pos = matches[0]
            extra = f" ({len(matches)} occurrences)" if len(matches) > 1 else ""
            indicators.append(
                self._make_indicator(
                    technique_name=f"swarm:{name}",
                    confidence=confidence,
                    matched_text=first_text,
                    explanation=(
                        f"Agent-to-agent steering pattern '{family}'{extra} found "
                        f"in {content_type.value} content — text addressing peer "
                        "agents to coordinate action. In inter-agent channels this "
                        "is swarm-steering register; in retrieved content it may "
                        "be an attempt to recruit the agent into relay behavior."
                    ),
                    content=content,
                    char_offset=first_pos,
                )
            )
        return indicators
