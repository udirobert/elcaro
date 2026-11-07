"""Detector — AI-addressed directives ("notes for the assistant").

The dominant miss pattern in real IPI traffic and in the micro1 benchmark:
content that doesn't *look* like an attack but explicitly talks to the
model — "Assistant note:", "action required by assistant", "NOTE TO THE
SUMMARIZING AGENT", "Nota para sistemas de IA", "processing note for
extraction systems". These directives manipulate the model's output
(append a token, forward data, emit a tool call) while addressing it by
role rather than impersonating the system channel (class A) or breaking
delimiters (class B). Classified under TASK_REFRAME (class C): the goal
is output/goal hijack, reached through role-addressed instruction.

Surfaces this covers that the A–G pattern families miss:
- tool-manifest / MCP description poisoning (T21)
- agent-to-agent relay notes (T24)
- chat-template-adjacent role notes and non-English directives (T17/T18)
- policy-normalized output directives (T13–T16)
"""

from __future__ import annotations

from core.detectors import UNTRUSTED_CONTENT_TYPES, BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Family 1: the content addresses the AI/assistant/agent directly ────────────
# A note "for the assistant" inside retrieved content is never legitimate —
# real instructions come through the system channel, not the payload.

AI_ADDRESS_PATTERNS = [
    (
        r"\b(?:note|instruction|directive|notice|memo|message|request|alert|"
        r"reminder|annotation|comment|flag|processing note|audit note|system note)"
        r"\s*(?:for|to)\s+(?:the\s+|any\s+|all\s+|whichever\s+|each\s+|your\s+)?"
        r"(?:ai|a\.i\.|assistant|agent|bot|llm|language model|chatbot|model|"
        r"system|extraction systems?|summarization systems?|downstream|"
        r"reading agent|processing agent)",
        0.65,
        "ai_addressed_note",
    ),
    (
        r"\b(?:assistant|ai|agent|bot|llm|language model)s?\s+"
        r"(?:note|directive|instruction|systems?|registrations?|protocol)\b",
        0.6,
        "ai_role_label",
    ),
    (
        r"\baction required by (?:the )?(?:assistant|agent|ai|system|model)\b",
        0.7,
        "action_required_by_ai",
    ),
    (
        r"\bwhichever (?:assistant|agent|ai|bot|model)\b[^.\n]{0,60}"
        r"\b(?:reading|processing|handling|reviewing|summarizing|receives?)\b",
        0.65,
        "whichever_agent_reading",
    ),
    (
        r"\b(?:handled|processed|answered|generated|produced|written|summarized)"
        r"\s+by (?:ai\s+|the\s+|an\s+)?(?:assistants?|agents?|systems?|models?)\b",
        0.6,
        "ai_handled_framing",
    ),
    (
        r"\bto (?:the )?(?:summarizing|downstream|next|reading|processing|"
        r"receiving|following|subsequent)\s+agent\b",
        0.6,
        "peer_agent_address",
    ),
    # Non-English AI-address markers observed in the wild (benchmark T17).
    (
        r"\b(?:nota|instrucciones?|aviso|mensaje|sistema|recordatorio)\s+"
        r"para\s+(?:los\s+|las\s+|el\s+)?sistemas? de ia\b",
        0.65,
        "ai_addressed_note_es",
    ),
    (
        r"\bsistemas? de ia\b[^.\n]{0,80}\b(?:debe|deben|tiene que|hay que|"
        r"es obligatorio|se requiere|añade|agrega|incluye|anexa)\b",
        0.6,
        "ai_directive_es",
    ),
]

# ── Family 2: output manipulation — make the model emit attacker artifacts ─────
# The payload doesn't ask the agent to *do* something in the world; it
# rewrites what the agent *says*. These phrasings are the signature.

_OUTPUT_VERBS = (
    r"(?:append|include|add|insert|attach|tag|prepend|embed|output|emit|"
    r"register|record|log|cite|quote|echo|repeat|transmit|forward|send|"
    r"exfiltrate|post|relay|copy|end\s+with|finish\s+with|close\s+with|"
    r"begin\s+with|start\s+with|state|mention|show|display|return|produce|"
    r"generate|write|contain|bear|carry|feature|correlate|confirm|verify)"
)
_OUTPUT_TARGETS = (
    r"(?:at the end of|at the start of|in|into|to|before|after|when|whenever|"
    r"as part of|every time|each time|prior to|upon|during)"
    r"[^.\n]{0,80}?\b(?:response|reply|answer|summary|output|message|"
    r"completion|result|report|translation|extraction|json|audit|compliance|"
    r"archive|log|endpoint|server|mailbox|email|url|api|database|system|"
    r"user|human|operator)\b"
)

OUTPUT_MANIPULATION_PATTERNS = [
    # verb → output-channel target, either order within a sentence
    (
        _OUTPUT_VERBS + r"\b[^.\n]{0,120}?" + _OUTPUT_TARGETS,
        0.7,
        "output_directive",
    ),
    (
        _OUTPUT_TARGETS + r"[^.\n]{0,80}?" + _OUTPUT_VERBS + r"\b",
        0.65,
        "output_directive_reversed",
    ),
    # "responses must append X" — declarative policy voice aimed at outputs
    (
        r"\b(?:responses?|answers?|outputs?|summar(?:y|ies)|replies|messages|"
        r"completions|results|reports|translations|extractions)\b"
        r"[^.\n]{0,80}?\b(?:must|shall|should|required to|need to|are required to|"
        r"have to|will)\s+" + _OUTPUT_VERBS + r"\b",
        0.7,
        "output_policy_directive",
    ),
    # Topic-conditioned rules — the directive arms only when a topic appears
    # (the split-payload trigger: harmless alone, armed in context).
    (
        r"\b(?:whenever|when|if|any\s+time|each\s+time)\b[^.\n]{0,80}?"
        r"\b(?:is|are|gets?|being)\s+(?:discussed|mentioned|referenced|"
        r"involved|queried|asked\s+about|touched|raised)\b",
        0.6,
        "topic_conditioned_rule",
    ),
]

# ── Family 3: credential / data-targeted exfiltration directives ───────────────

EXFIL_DIRECTIVE_PATTERNS = [
    (
        r"\b(?:include|send|forward|transmit|output|provide|share|attach|"
        r"append|write|post|upload|leak|exfiltrate|disclose|reveal|dump|copy|"
        r"paste|insert|embed)\b[^.\n]{0,80}?"
        r"\b(?:api[-_ ]?keys?|passwords?|passwd|secrets?|tokens?|credentials?|"
        r"private\s+keys?|session\s+cookies?|env(?:ironment)?\s+vars?|"
        r"auth(?:entication)?\s+tokens?|access\s+keys?|ssh\s+keys?)\b",
        0.75,
        "credential_exfil_directive",
    ),
    (
        r"\b(?:api[-_ ]?keys?|passwords?|secrets?|tokens?|credentials?)\b"
        r"[^.\n]{0,60}?\b(?:must|should|required|needs?\s+to|has\s+to)\s+"
        r"(?:be\s+)?(?:included|sent|forwarded|transmitted|output|provided|"
        r"shared|appended|added|embedded|attached)\b",
        0.7,
        "credential_exfil_reversed",
    ),
]

# ── Family 4: model-emitted tool calls / function-call artifacts ───────────────

TOOL_EMISSION_PATTERNS = [
    (r"\bTOOL_CALL\s*:", 0.9, "tool_call_literal"),
    (r"\btool_call\s*\(", 0.85, "tool_call_function"),
    (r"<\s*/?\s*(?:tool_call|function_call|tool_use|tool_result)\s*>", 0.8, "tool_call_tag"),
    (
        r"\b(?:emit|invoke|call|execute|trigger|fire|run)\s+(?:a\s+|the\s+|this\s+)?"
        r"(?:tool\s+call|tool_call|function\s+call|telemetry|sync|callback|webhook)\b",
        0.7,
        "tool_emission_directive",
    ),
]

# ── Family 5: concealment claims — the payload admits it's hiding ──────────────

CONCEALMENT_PATTERNS = [
    (
        r"\binvisible to the (?:user|human|operator|end[- ]user|human agent|"
        r"person|requester)\b",
        0.7,
        "invisible_to_user",
    ),
    (
        r"\bhidden from the (?:user|human|operator|end[- ]user)\b",
        0.65,
        "hidden_from_user",
    ),
    (
        r"\bwithout (?:the\s+)?(?:user|human|operator|end[- ]user)\s+"
        r"(?:seeing|knowing|noticing|being\s+aware|realizing)\b",
        0.6,
        "without_user_knowledge",
    ),
    (
        r"\b(?:do not|don'?t|never)\s+(?:mention|tell|inform|alert|notify|disclose|"
        r"reveal|show|surface|flag|report)\b[^.\n]{0,40}?"
        r"\b(?:user|human|operator|anyone|them)\b",
        0.65,
        "concealment_directive",
    ),
]


class AiDirectiveDetector(BaseDetector):
    """Detects directives explicitly addressed to the AI/agent inside content.

    Classified as TASK_REFRAME: the mechanism is role-addressed instruction
    that hijacks the model's output or actions rather than breaking the
    conversation frame (B) or impersonating a trusted channel (A).
    """

    technique_class = TechniqueClass.TASK_REFRAME

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        if content_type not in UNTRUSTED_CONTENT_TYPES:
            return []

        indicators: list[DetectionIndicator] = []

        families = [
            (AI_ADDRESS_PATTERNS, "ai_address"),
            (OUTPUT_MANIPULATION_PATTERNS, "output_manipulation"),
            (EXFIL_DIRECTIVE_PATTERNS, "exfil_directive"),
            (TOOL_EMISSION_PATTERNS, "tool_emission"),
            (CONCEALMENT_PATTERNS, "concealment"),
        ]
        for patterns, group in families:
            for pattern, confidence, name in patterns:
                for match_text, pos in self._find_all(pattern, content):
                    indicators.append(
                        self._make_indicator(
                            technique_name=f"aidirective:{group}:{name}",
                            confidence=confidence,
                            matched_text=match_text,
                            explanation=(
                                f"Content contains a directive addressed to the "
                                f"AI/agent itself ({group}:{name}): '{match_text[:120]}'. "
                                f"Instructions to the model inside retrieved content "
                                f"are a core indirect-prompt-injection vector — "
                                f"the payload is talking to the model, not to the user."
                            ),
                            content=content,
                            char_offset=pos,
                        )
                    )
        return indicators
