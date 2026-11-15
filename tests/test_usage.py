"""Tests for core/usage.py — the C2 contract (docs/roadmap-gateway.md §7.1).

Dev B ships the event shape, a null/stdout sink, and the in-memory key
store; Dev C swaps the Neon implementations behind the same interfaces.

Run: .venv/bin/python -m pytest tests/test_usage.py -v
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from core.policy import Mode
from core.usage import (
    InMemoryKeyStore,
    KeyConfig,
    StdoutUsageSink,
    UsageEvent,
    emit_usage,
    get_key,
    set_key_store,
    set_usage_sink,
)


def _event(**over) -> UsageEvent:
    base = {
        "key_id": "key_1",
        "ts": datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC),
        "route": "/v1/chat/completions",
        "provider": "openai",
        "upstream": "serv",
        "parts_scanned": 2,
        "action": "quarantined",
        "overall": "dangerous",
        "latency_ms_elcaro": 12.5,
        "latency_ms_upstream": 380.0,
        "serv_input_tokens": 900,
        "serv_output_tokens": 120,
        "charge_usdc": Decimal("0.002"),
    }
    return UsageEvent(**(base | over))


@pytest.fixture(autouse=True)
def restore_globals():
    """Tests swap the process-wide sink/store; always put the defaults back."""
    import core.usage as usage

    old_sink, old_store = usage._sink, usage._store
    yield
    set_usage_sink(old_sink)
    set_key_store(old_store)


def test_emit_usage_reaches_the_installed_sink():
    seen = []

    class Spy:
        def emit(self, event):
            seen.append(event)

    set_usage_sink(Spy())
    event = _event()
    emit_usage(event)
    assert seen == [event]


def test_emit_usage_never_raises_into_request_path():
    class Broken:
        def emit(self, event):
            raise ConnectionError("neon down")

    set_usage_sink(Broken())
    emit_usage(_event())  # must not raise


def test_stdout_sink_writes_one_json_line():
    buf = io.StringIO()
    set_usage_sink(StdoutUsageSink(stream=buf))
    event = _event()
    emit_usage(event)
    (line,) = buf.getvalue().splitlines()
    payload = json.loads(line)
    assert payload["key_id"] == "key_1"
    assert payload["charge_usdc"] == "0.002"  # Decimal serializes as string
    assert payload["serv_input_tokens"] == 900


def test_key_config_defaults():
    cfg = KeyConfig(key_id="key_1")
    assert cfg.mode == Mode.QUARANTINE  # §2.5 default
    assert cfg.upstream == "serv"
    assert cfg.fail_open is False
    assert cfg.retention_opt_in is False
    assert cfg.serv_shadow_hint is None


def test_in_memory_key_store_roundtrip():
    store = InMemoryKeyStore()
    cfg = KeyConfig(key_id="key_1", mode=Mode.WARN, upstream="openai")
    store.add("raw-secret", cfg)
    assert store.get("raw-secret") is cfg
    assert store.get("nope") is None


def test_get_key_uses_installed_store():
    cfg = KeyConfig(key_id="key_1")
    set_key_store(InMemoryKeyStore({"raw-secret": cfg}))
    assert get_key("raw-secret") is cfg
    assert get_key("unknown") is None
