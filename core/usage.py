"""C2 — usage events and key lookup (contract per docs/roadmap-gateway.md §7.1).

The Gateway emits one :class:`UsageEvent` per request and resolves caller
keys through :func:`get_key`. Both are interfaces with swappable
implementations, so Dev B ships working defaults while Dev C lands the Neon
sinks and hashed key store behind the same signatures:

    emit_usage(event)      Dev B: stdout/no-op sink now; Dev C: Neon sink +
                           daily rollups later (Phase 3.2).
    get_key(raw_key)       Dev B: in-memory stub now; Dev C: hashed key
                           lookup over the key-management store (Phase 3.2).

Both are deliberately tolerant of the producer side: ``emit_usage`` never
raises into the request path — a metering outage must not take paid traffic
down. ``get_key`` failures DO propagate: unknown or broken key state fails
the request closed, never open.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from core.policy import Mode

log = logging.getLogger(__name__)


# ── Usage events ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UsageEvent:
    """One metered Gateway request (contract C2 — fields fixed for both lanes).

    ``charge_usdc`` is Elcaro's own charge for the call; the upstream's cost
    is billed by the provider directly. ``serv_*_tokens`` come from the
    upstream ``usage`` field when present — never from the 4-chars-per-token
    estimate (Phase 3.2 replaces that heuristic).
    """

    key_id: str
    ts: datetime
    route: str  # e.g. "/v1/chat/completions"
    provider: str  # "openai" | "anthropic"
    upstream: str  # upstream allowlist entry the key resolved to, e.g. "serv"
    parts_scanned: int
    action: str  # none | warned | quarantined | blocked | bypassed
    overall: str  # worst RiskLevel value across scanned parts
    latency_ms_elcaro: float  # our overhead: auth + scan + policy
    latency_ms_upstream: float  # upstream round trip
    serv_input_tokens: int | None = None
    serv_output_tokens: int | None = None
    charge_usdc: Decimal = Decimal("0")


class UsageSink(Protocol):
    """Anything that can accept a UsageEvent — Neon writer, stdout, test spy."""

    def emit(self, event: UsageEvent) -> None: ...


class NullUsageSink:
    """Default: drop events. Safe until Dev C's Neon sink lands."""

    def emit(self, event: UsageEvent) -> None:
        pass


class StdoutUsageSink:
    """Dev/local sink: one JSON line per event. ``Decimal``/``datetime``
    serialize to strings — the Neon schema decides real types."""

    def __init__(self, stream=None):
        self._stream = stream or sys.stdout

    def emit(self, event: UsageEvent) -> None:
        self._stream.write(json.dumps(asdict(event), default=str, separators=(",", ":")) + "\n")
        self._stream.flush()


_sink: UsageSink = NullUsageSink()


def set_usage_sink(sink: UsageSink) -> None:
    """Install the process-wide sink — Dev C's Neon writer, or a test spy."""
    global _sink
    _sink = sink


def emit_usage(event: UsageEvent) -> None:
    """Emit one usage event. Never raises into the request path — a metering
    outage degrades visibility, not paid traffic."""
    try:
        _sink.emit(event)
    except Exception:  # noqa: BLE001 — metering must not fail requests
        log.warning("usage sink dropped an event", exc_info=True)


# ── Key lookup ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class KeyConfig:
    """Per-key Gateway configuration (contract C2).

    ``upstream`` names an entry in the Gateway's upstream allowlist (§2.3) —
    never a raw URL, so keys cannot point the proxy at arbitrary hosts.
    ``fail_open`` selects the availability posture when the scan path itself
    errors (§5 risk table): True forwards unscanned with
    ``x-elcaro-action: bypassed``; False fails the request.
    """

    key_id: str
    mode: Mode = Mode.QUARANTINE  # §2.5 default
    upstream: str = "serv"
    scan_user_messages: bool = False
    deep_analysis: bool = False  # "Gateway + SERV judge" tier (§3.1)
    serv_shadow_hint: str | None = None  # opt-in serv_shadow_agent hint (§2.6)
    retention_opt_in: bool = False  # store payloads for incident review (§2.8)
    fail_open: bool = False


class KeyStore(Protocol):
    """Raw API key → KeyConfig, or None for unknown keys. Dev C implements
    this over hashed storage; lookup errors propagate (fail closed)."""

    def get(self, raw_key: str) -> KeyConfig | None: ...


class InMemoryKeyStore:
    """Dev/test stub: literal raw-key map. Dev C replaces it with the Neon
    store keyed by hash — the gateway only ever calls ``get``."""

    def __init__(self, keys: dict[str, KeyConfig] | None = None):
        self._keys = dict(keys or {})

    def add(self, raw_key: str, config: KeyConfig) -> None:
        self._keys[raw_key] = config

    def get(self, raw_key: str) -> KeyConfig | None:
        return self._keys.get(raw_key)


_store: KeyStore = InMemoryKeyStore()


def set_key_store(store: KeyStore) -> None:
    """Install the process-wide key store — Dev C's Neon lookup, or a stub."""
    global _store
    _store = store


def get_key(raw_key: str) -> KeyConfig | None:
    """Resolve an ``x-elcaro-key`` to its config, or None when unknown."""
    return _store.get(raw_key)


__all__ = [
    "InMemoryKeyStore",
    "KeyConfig",
    "KeyStore",
    "NullUsageSink",
    "StdoutUsageSink",
    "UsageEvent",
    "UsageSink",
    "emit_usage",
    "get_key",
    "set_key_store",
    "set_usage_sink",
]
