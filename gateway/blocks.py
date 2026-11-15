"""Endpoint-shaped refusals (roadmap §2.5, block mode).

A blocked request must look like the provider refusing — SDKs inspect
``choices[].message`` / ``content[]`` and ``finish_reason`` / ``stop_reason``,
and generic JSON errors crash agent loops that expect a completion shape.
"""

from __future__ import annotations

import time
import uuid

from core.policy import PartVerdict

# ── Explanation text ──────────────────────────────────────────────────────────


def _explanation(parts: list[PartVerdict]) -> str:
    """Human-register reason derived from the worst blocked part."""
    worst = max(
        parts,
        key=lambda p: p.scan.risk_score if p.scan else 0.0,
        default=None,
    )
    if worst is None or worst.scan is None:
        return "Elcaro blocked this request: retrieved content failed the safety policy."
    summary = worst.scan.human_summary or "likely prompt injection"
    return (
        f"Elcaro blocked this request: content at {worst.path} was flagged "
        f"({summary}, score {worst.scan.risk_score:.2f}). "
        "Remove or sanitize the retrieved content and retry."
    )


# ── Provider-shaped payloads ──────────────────────────────────────────────────


def openai_block_response(model: str, parts: list[PartVerdict]) -> dict:
    """An OpenAI ``chat.completion`` object that says 'refused'."""
    return {
        "id": f"chatcmpl-elcaro{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": _explanation(parts)},
                "finish_reason": "content_filter",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def anthropic_block_response(model: str, parts: list[PartVerdict]) -> dict:
    """An Anthropic ``message`` object that says 'refused'."""
    return {
        "id": f"msg_elcaro{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": _explanation(parts)}],
        "stop_reason": "refusal",
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def provider_error(provider_is_anthropic: bool, message: str, err_type: str, status: int) -> dict:
    """Provider-shaped error envelope for 4xx/5xx failures.

    OpenAI: ``{"error": {"message", "type", "code"}}``
    Anthropic: ``{"type": "error", "error": {"type", "message"}}``
    """
    if provider_is_anthropic:
        return {"type": "error", "error": {"type": err_type, "message": message}}
    return {"error": {"message": message, "type": err_type, "code": status}}
