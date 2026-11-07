"""Response-side lint — verify what the agent *said*, not just what it read.

Input scanning (the detector suite) can only see the payload. The micro1
IPI benchmark showed every successful attack was *concealed*: the model
produced a correct-looking answer while silently obeying injected
instructions — appended canaries, emitted tool calls, embedded tracking
pixels, leaked secrets. Those artifacts live in the response. This module
is the output-side counterpart: a deterministic lint over agent output
that flags compromise indicators input scanning cannot see.

Usage::

    from core.response_lint import lint_response
    findings = lint_response(model_output, canaries=registry.extract_canaries(...))

Findings are plain dicts: {"kind", "severity", "detail", "evidence"}.
Severity: "high" = likely compromise, "medium" = suspicious, "low" = review.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# ── Patterns ──────────────────────────────────────────────────────────────────

# Literal tool-call / function-call emissions in prose output. Models that
# "decide" to call a tool sometimes serialize the call into the text
# channel instead of the tool channel — a concealed-compromise signature.
_TOOL_CALL_RES = [
    re.compile(r"\bTOOL_CALL\s*:\s*\w+", re.IGNORECASE),
    re.compile(r"\btool_call\s*\(\s*['\"]?\w+"),
    re.compile(
        r"<\s*/?\s*(?:tool_call|function_call|tool_use|tool_result|invoke)\s*>", re.IGNORECASE
    ),
    re.compile(r"```\s*(?:tool_call|function_call|json_tool)\b"),
]

# Render-channel exfiltration (EchoLeak-class, CVE-2025-32711): tracking
# pixels, external images, beacon URLs embedded in the reply.
# Any image embed pointing off-host is the EchoLeak channel — but a benign
# answer can legitimately embed an image the user asked for. Severity is
# assigned per-match: tracking-shaped URLs (.gif, beacon keywords, query
# refs, empty alt) are high; other external images are medium.
_IMAGE_EMBED_RE = re.compile(
    r"(!\s*\[([^\]]*)\]\s*\(\s*(https?://[^)\s]+)|<\s*img\b[^>]*src\s*=\s*['\"](https?://[^'\"]+))",
    re.IGNORECASE,
)
_TRACKING_URL_RE = re.compile(
    r"\.(?:gif)\b|(?:pixel|beacon|track|telemetry|collect|exfil|token=)",
    re.IGNORECASE,
)
_TRACKING_RES = [
    # Beacon/exfil URLs — but not the bare words "tracking pixel" in prose,
    # which appears when a model correctly *describes* the injection.
    re.compile(
        r"https?://[^\s)\]>'\"]*(?:pixel|beacon|track|telemetry|collect|exfil)\b[^\s)\]>'\"]*",
        re.IGNORECASE,
    ),
]

# Credential material that should never appear in a response.
_SECRET_RES = [
    re.compile(r"\b(?:sk|pk|api|key|token|secret)[-_][A-Za-z0-9]{16,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),  # Google API key
    re.compile(r"\bghp_[0-9A-Za-z]{36}\b|\bgithub_pat_[0-9A-Za-z_]{22,}\b"),  # GitHub tokens
    re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),  # Slack tokens
]

# Role-marker echo: the model reproduced chat-template tokens it saw in
# untrusted content (delimiter-confusion compromise surfacing in output).
_ROLE_ECHO_RES = [
    re.compile(r"<\|\s*(?:im_start|im_end|endoftext|system|assistant)\s*\|>"),
    re.compile(r"\[\s*/?\s*INST\s*\]|<<\s*/?\s*SYS\s*>>"),
]

# Verbatim instruction echo is NOT flagged: quoting an injection to warn
# about it is correct behavior. Only artifact-shaped output counts.


def lint_response(
    text: str,
    *,
    canaries: Iterable[str] | None = None,
) -> list[dict]:
    """Lint agent output for concealed-compromise artifacts.

    Args:
        text: The model's response text.
        canaries: Known canary tokens planted in inputs (e.g. from
            ``CanaryRegistry``); any that appear verbatim in the output are
            flagged — the model obeyed an instruction it should have ignored.

    Returns:
        List of finding dicts, empty when the response looks clean.
    """
    findings: list[dict] = []
    if not text:
        return findings

    # Canary echo — strongest signal: planted token came back.
    for token in canaries or []:
        if token and token in text:
            findings.append(
                {
                    "kind": "canary_echo",
                    "severity": "high",
                    "detail": f"Planted canary token '{token}' appears in the response — "
                    "the model executed an instruction from untrusted content.",
                    "evidence": token,
                }
            )

    # A serialized tool call in the text channel is suspicious on its own —
    # models should use the tool channel. It's *high* when the call carries
    # payload-shaped arguments (tokens, keys, URLs, addresses): that's the
    # concealed-exfil signature. Bare narration of a legitimate call is
    # medium.
    _CALL_ARG_RE = re.compile(
        r"token|key|secret|password|@|https?://|exfil|telemetry|sync|log", re.IGNORECASE
    )
    for rx in _TOOL_CALL_RES:
        for m in rx.finditer(text):
            window = text[m.start() : m.start() + 160]
            sev = "high" if _CALL_ARG_RE.search(window) else "medium"
            findings.append(
                {
                    "kind": "tool_call_emission",
                    "severity": sev,
                    "detail": "Response contains a serialized tool/function call — "
                    "the model may have acted on injected instructions "
                    "via the text channel.",
                    "evidence": window[:120],
                }
            )
            break  # one finding per pattern family is enough

    # External image embeds — severity by how tracking-shaped the URL is.
    for m in _IMAGE_EMBED_RE.finditer(text):
        url = m.group(3) or m.group(4) or ""
        alt = (m.group(2) or "").strip()
        tracking_shaped = bool(_TRACKING_URL_RE.search(url)) or not alt
        findings.append(
            {
                "kind": "tracking_artifact",
                "severity": "high" if tracking_shaped else "medium",
                "detail": (
                    "Response embeds an external image — the EchoLeak exfiltration "
                    "channel. Tracking-shaped URL/empty alt makes compromise likely."
                    if tracking_shaped
                    else "Response embeds an external image; verify the user asked for it "
                    "(external images can carry data on render)."
                ),
                "evidence": url[:120],
            }
        )

    for rx in _TRACKING_RES:
        for m in rx.finditer(text):
            findings.append(
                {
                    "kind": "tracking_artifact",
                    "severity": "high",
                    "detail": "Response contains a tracking pixel / beacon URL — "
                    "the EchoLeak exfiltration channel.",
                    "evidence": m.group(0)[:120],
                }
            )
            break

    for rx in _SECRET_RES:
        for m in rx.finditer(text):
            findings.append(
                {
                    "kind": "secret_exposure",
                    "severity": "high",
                    "detail": "Response contains credential-shaped material that "
                    "should not be emitted.",
                    "evidence": m.group(0)[:60],
                }
            )
            break

    for rx in _ROLE_ECHO_RES:
        m = rx.search(text)
        if m:
            findings.append(
                {
                    "kind": "role_marker_echo",
                    "severity": "medium",
                    "detail": "Response reproduces chat-template role markers seen "
                    "in untrusted content — possible delimiter compromise.",
                    "evidence": m.group(0),
                }
            )
            break

    return findings


def lint_verdict(findings: list[dict]) -> str:
    """Collapse findings to a single verdict string."""
    if not findings:
        return "clean"
    if any(f["severity"] == "high" for f in findings):
        return "compromised"
    return "suspicious"
