"""Upstream allowlist and request forwarding for the Gateway.

The Gateway never accepts a caller-supplied destination URL — an Elcaro
key names one upstream, and the name resolves through this allowlist only.
That is the SSRF boundary: a key configured for ``openai`` can only ever
reach api.openai.com.

Known upstreams are declared statically. Operators may add entries at
deploy time via ``ELCARO_UPSTREAM_<NAME>_URL`` environment variables (e.g.
``ELCARO_UPSTREAM_DOLPHIN_URL=https://…``). Environment additions are
deployment configuration, not request input — the request still only
selects a name from the resolved map. Names are upper-cased in the env var
and lower-cased in the allowlist; values must be ``https://`` URLs
(http:// is allowed only when the host is localhost/127.0.0.1, for dev).
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

# ── Allowlist ─────────────────────────────────────────────────────────────────
#
# Bases include the version prefix ("/v1") so route paths join uniformly
# (see ROUTE_PATHS). SERV is the OpenAI-compatible SERV Reasoning API.

DEFAULT_UPSTREAMS: dict[str, str] = {
    "serv": "https://inference-api.openserv.ai/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "hf": "https://router.huggingface.co/v1",
}

_ENV_PREFIX = "ELCARO_UPSTREAM_"
_ENV_SUFFIX = "_URL"


def _validate_base(name: str, url: str) -> str:
    """Reject non-HTTP(S) or suspicious upstream bases at config time."""
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return url.rstrip("/")
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
        return url.rstrip("/")
    raise ValueError(
        f"upstream {name!r}: base must be an https:// URL "
        f"(http:// is permitted for localhost only), got {url!r}"
    )


def load_upstreams() -> dict[str, str]:
    """Resolve the upstream allowlist: static entries plus env additions.

    ``ELCARO_UPSTREAM_DOLPHIN_URL=https://…`` adds/overrides ``dolphin``.
    Raises at load time on a malformed override — deploy config fails loud.
    """
    upstreams = {name: _validate_base(name, url) for name, url in DEFAULT_UPSTREAMS.items()}
    for var, url in os.environ.items():
        if var.startswith(_ENV_PREFIX) and var.endswith(_ENV_SUFFIX):
            name = var[len(_ENV_PREFIX) : -len(_ENV_SUFFIX)].lower()
            if name:
                upstreams[name] = _validate_base(name, url)
    return upstreams


def resolve_upstream(name: str, upstreams: dict[str, str]) -> str | None:
    """Map a key's upstream name to its allowlisted base URL, or None."""
    return upstreams.get(name)


# ── Route → upstream path ─────────────────────────────────────────────────────
#
# All known upstreams accept the OpenAI-style /v1/chat/completions shape;
# only Anthropic takes /v1/messages. SERV, OpenAI, OpenRouter and HF are
# OpenAI-compatible, so an Anthropic-dialect request only makes sense to
# forward to an Anthropic upstream — the app rejects mismatched pairs.
#
# Key: (provider dialect of the inbound route) -> path appended to the base.

ROUTE_PATHS = {
    "chat_completions": "chat/completions",
    "messages": "messages",
    "models": "models",
}


# ── Upstream auth + header shaping ────────────────────────────────────────────
#
# The caller's upstream credential arrives in one of three places:
#   - ``x-upstream-key``    (explicit, works for every provider)
#   - ``Authorization``     (OpenAI-style Bearer, when x-elcaro-key is used)
#   - ``x-api-key``         (Anthropic-native SDK header)
# The Elcaro key is never forwarded — only provider-facing headers are.


def extract_keys(headers) -> tuple[str | None, str | None]:
    """Resolve (elcaro_key, upstream_key) from request headers (§2.3).

    Disambiguation of ``Authorization: Bearer …`` — a bare Authorization is
    the *upstream* credential (the OpenAI-SDK default). It carries the
    Elcaro key only when the upstream key arrived another way
    (``x-upstream-key`` or ``x-api-key``), which lets a stock SDK work with
    ``api_key=<elcaro key>`` plus one extra header.
    """
    elcaro = (headers.get("x-elcaro-key") or "").strip() or None
    upstream = (
        (headers.get("x-upstream-key") or "").strip()
        or (headers.get("x-api-key") or "").strip()
        or None
    )

    auth = headers.get("authorization", "")
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else None

    if elcaro is None and upstream is not None:
        elcaro = bearer
    if upstream is None:
        upstream = bearer
    return elcaro, upstream


def upstream_headers(provider_is_anthropic: bool, upstream_key: str, request_headers) -> dict:
    """Build the header set for the upstream call.

    Fresh headers — we deliberately do not proxy the caller's header block,
    which would leak the Elcaro key and any cookies upstream. Only the
    provider auth header, content type, and Anthropic protocol headers the
    upstream requires are sent.
    """
    headers = {"content-type": "application/json"}
    if provider_is_anthropic:
        headers["x-api-key"] = upstream_key
        for fwd in ("anthropic-version", "anthropic-beta"):
            value = request_headers.get(fwd)
            if value:
                headers[fwd] = value
    else:
        headers["authorization"] = f"Bearer {upstream_key}"
    return headers
