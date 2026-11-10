"""Settings access for the elcaro Hermes plugin.

Thin wrapper over ctx.get_config so guard/tools read the same keys the
manifest's config_schema declares. ctx is captured at register() time; a
plain dict can be injected for tests.

``type: secret`` settings never surface through get_config — Hermes keeps
them in .env — so they resolve through agent.secret_scope, which is
profile-scoped and fails closed under gateway multiplexing.
"""

from __future__ import annotations

import os
from typing import Any

_ctx: Any = None
_test_settings: dict[str, Any] | None = None


def bind(ctx: Any) -> None:
    """Capture the plugin context at registration."""
    global _ctx
    _ctx = ctx


def bind_test(settings: dict[str, Any]) -> None:
    """Inject settings without a Hermes ctx (unit tests)."""
    global _test_settings
    _test_settings = settings


def get(key: str, default: Any = None) -> Any:
    if _test_settings is not None and key in _test_settings:
        return _test_settings[key]
    if _ctx is not None:
        try:
            return _ctx.get_config(key, default=default)
        except Exception:
            return default
    return default


def get_str(key: str, default: str = "") -> str:
    v = get(key, default)
    return v if isinstance(v, str) else default


def get_secret(key: str, env_name: str, default: str = "") -> str:
    """Resolve a ``type: secret`` setting by its ``env:`` name.

    ctx.get_config never returns secret values — Hermes stores them in the
    profile's .env — so reads go through agent.secret_scope.get_secret,
    which honors the active profile scope (and raises rather than leak
    another profile's value under multiplexing). Outside Hermes, test
    settings or the process env supply the value.
    """
    if _test_settings is not None and key in _test_settings:
        v = _test_settings[key]
        return v if isinstance(v, str) else default
    try:
        from agent.secret_scope import get_secret_str

        return get_secret_str(env_name, default)
    except ImportError:
        return os.environ.get(env_name, default)


def get_float(key: str, default: float) -> float:
    try:
        return float(get(key, default))
    except (TypeError, ValueError):
        return default


def get_int(key: str, default: int) -> int:
    try:
        return int(get(key, default))
    except (TypeError, ValueError):
        return default


def get_list(key: str, default: list | None = None) -> list:
    v = get(key, default or [])
    return list(v) if isinstance(v, (list, tuple)) else (default or [])
