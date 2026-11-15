"""Elcaro client package — adopt the Gateway by changing one base URL.

    from elcaro import OpenAI, untrusted

    client = OpenAI(elcaro_key="elc-…", upstream_key="sk-…",
                    base_url="https://gateway.example.com")
    client.chat.completions.create(
        model="…",
        messages=[
            {"role": "system", "content": "…"},
            untrusted({"role": "tool", "tool_call_id": "…",
                       "content": fetched_text}),
        ],
    )

The SDK subclasses are resolved lazily (``pip install openai`` /
``anthropic`` only when used); ``untrusted`` and ``verify_receipt`` are
dependency-free.
"""

from __future__ import annotations

from elcaro.client import untrusted, verify_receipt

__version__ = "0.1.0"


def __getattr__(name: str):
    """Lazy SDK subclass resolution — importing elcaro must not require
    openai/anthropic to be installed."""
    if name in ("OpenAI", "Anthropic"):
        from elcaro import client

        return getattr(client, f"_{name.lower()}_class")()
    raise AttributeError(f"module 'elcaro' has no attribute {name!r}")


__all__ = ["Anthropic", "OpenAI", "untrusted", "verify_receipt"]
