"""Elcaro client helpers — the §2.9 "change one base URL" adoption path.

``elcaro.OpenAI(...)`` and ``elcaro.Anthropic(...)`` are thin subclasses of
the official SDKs that preset the Gateway base URL and header scheme. The
SDK objects are the real thing — streaming, retries, types all work; only
the transport target and two headers differ.

Auth layout (§2.3):
- OpenAI-style: ``api_key=<elcaro key>`` (rides Authorization) +
  ``x-upstream-key: <provider key>``
- Anthropic-style: ``api_key=<provider key>`` (rides x-api-key) +
  ``x-elcaro-key: <elcaro key>``

The SDKs are optional dependencies — this module imports them lazily so
``import elcaro`` stays dependency-free (``untrusted`` and
``verify_receipt`` work anywhere).
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

DEFAULT_GATEWAY_URL = "http://localhost:8000"


def _gateway_url(base_url: str | None) -> str:
    return (base_url or os.environ.get("ELCARO_GATEWAY_URL") or DEFAULT_GATEWAY_URL).rstrip("/")


def untrusted(part: dict, *, content_type: str | None = None) -> dict:
    """Mark a message part as untrusted retrieved content (§2.4).

    Returns a copy with the ``elcaro`` marker merged in — works on a whole
    message or on one Anthropic/OpenAI content block. The Gateway scans the
    marked part regardless of role, then strips the marker before
    forwarding.

    >>> msg = untrusted({"role": "user", "content": fetched_text},
    ...                 content_type="email")
    """
    marker = {"untrusted": True}
    if content_type is not None:
        marker["content_type"] = content_type
    existing = part.get("elcaro")
    merged = {**existing, **marker} if isinstance(existing, dict) else marker
    return {**part, "elcaro": merged}


def verify_receipt(payload: str, signature_b64: str, public_key_hex: str) -> bool:
    """Verify an ``x-elcaro-receipt`` signature offline.

    ``payload`` is the canonical JSON string from the response's
    ``elcaro.receipt.payload``; ``signature_b64`` is the base64 signature
    (header or ``elcaro.receipt.signature``); ``public_key_hex`` comes from
    ``GET /pubkey``. Self-contained — no server-side imports.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(base64.b64decode(signature_b64).hex()), payload.encode())
        return True
    except (InvalidSignature, ValueError):
        return False


def _elcaro_mode_header(mode: str | None) -> dict[str, str]:
    return {"x-elcaro-mode": mode} if mode else {}


@lru_cache(maxsize=1)
def _openai_class():
    try:
        import openai
    except ImportError as exc:  # pragma: no cover — depends on env
        raise ImportError("elcaro.OpenAI needs the OpenAI SDK: pip install openai") from exc

    class OpenAI(openai.OpenAI):  # type: ignore[name-defined]
        """``openai.OpenAI`` pointed at the Elcaro Gateway.

        The Elcaro key takes the SDK's ``api_key`` slot (it becomes the
        Authorization bearer); the upstream provider key goes in
        ``x-upstream-key`` so the Gateway can forward it.
        """

        def __init__(
            self,
            *,
            elcaro_key: str,
            upstream_key: str,
            base_url: str | None = None,
            mode: str | None = None,
            **kwargs,
        ):
            default_headers = {
                "x-upstream-key": upstream_key,
                **_elcaro_mode_header(mode),
                **(kwargs.pop("default_headers", None) or {}),
            }
            super().__init__(
                api_key=elcaro_key,
                base_url=_gateway_url(base_url),
                default_headers=default_headers,
                **kwargs,
            )

    return OpenAI


@lru_cache(maxsize=1)
def _anthropic_class():
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover — depends on env
        raise ImportError(
            "elcaro.Anthropic needs the Anthropic SDK: pip install anthropic"
        ) from exc

    class Anthropic(anthropic.Anthropic):  # type: ignore[name-defined]
        """``anthropic.Anthropic`` pointed at the Elcaro Gateway.

        The Anthropic SDK puts ``api_key`` in ``x-api-key`` — exactly the
        upstream-key slot — so the Elcaro key rides ``x-elcaro-key``.
        """

        def __init__(
            self,
            *,
            elcaro_key: str,
            upstream_key: str,
            base_url: str | None = None,
            mode: str | None = None,
            **kwargs,
        ):
            default_headers = {
                "x-elcaro-key": elcaro_key,
                **_elcaro_mode_header(mode),
                **(kwargs.pop("default_headers", None) or {}),
            }
            super().__init__(
                api_key=upstream_key,
                base_url=_gateway_url(base_url),
                default_headers=default_headers,
                **kwargs,
            )

    return Anthropic


def OpenAI(**kwargs):  # noqa: N802 — mirrors the SDK class name (§2.9)
    return _openai_class()(**kwargs)


def Anthropic(**kwargs):  # noqa: N802
    return _anthropic_class()(**kwargs)
