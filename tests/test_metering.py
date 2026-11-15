"""C2 storage tests — metering/neon.py against a fake psycopg pool.

Mirrors tests/test_canary.py's _FakePool pattern: no live Postgres, SQL
and params recorded for assertion. ``config_factory`` injects a stub so
tests don't need core.usage (Dev B's branch); production uses the real
lazy default.
"""

import hashlib
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from metering.neon import KEY_PREFIX_LEN, NeonMetering, from_env, hash_key


class _FakeResult:
    def __init__(self, rows, rowcount=0):
        self._rows = rows
        self.rowcount = rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, pool):
        self._pool = pool

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if self._pool.fail:
            raise RuntimeError("db down")
        self._pool.queries.append((sql, params))
        rows = self._pool.next_rows.pop(0) if self._pool.next_rows else []
        return _FakeResult(rows, rowcount=len(rows) or self._pool.rowcount)


class _FakePool:
    """Stand-in for psycopg_pool.ConnectionPool — records (sql, params)."""

    def __init__(self, next_rows=None, fail=False, rowcount=1):
        self.queries = []
        self.next_rows = list(next_rows or [])
        self.fail = fail
        self.rowcount = rowcount

    def connection(self):
        return _FakeConn(self)


def _factory(fields):
    """Test stand-in for core.usage.KeyConfig — records fields verbatim."""
    return SimpleNamespace(**fields)


def _make(next_rows=None, fail=False, rowcount=1):
    pool = _FakePool(fail=fail, rowcount=rowcount)
    m = NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    pool.next_rows.extend(next_rows or [])  # staged post-construction — DDL would eat them
    return m, pool


# ── Construction ────────────────────────────────────────────────────────────


def test_constructs_and_validates():
    _, pool = _make()
    sql = [q for q, _ in pool.queries]
    assert sql[0] == "SELECT 1"
    joined = " ".join(sql)
    for table in ("api_keys", "usage_events", "usage_daily"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in joined


def test_construct_fails_loud():
    with pytest.raises(RuntimeError, match="db down"):
        _make(fail=True)


# ── Key issuance ────────────────────────────────────────────────────────────


def test_issue_key_format_and_hash():
    m, pool = _make()
    raw, key_id = m.issue_key(label="bench", mode="warn", deep_analysis=True)
    assert raw.startswith("elk_") and key_id.startswith("elkid_")
    insert = [q for q in pool.queries if "INSERT INTO api_keys" in q[0]][0]
    params = insert[1]
    assert params[0] == key_id
    assert params[1] == hashlib.sha256(raw.encode()).hexdigest()
    assert params[2] == raw[:KEY_PREFIX_LEN]  # display prefix only — never the key
    assert params[3] == "bench" and params[4] == "warn" and params[7] is True
    # raw key itself must never appear in stored params
    assert raw not in params


def test_issue_key_defaults_quarantine():
    m, pool = _make()
    m.issue_key()
    insert = [q for q in pool.queries if "INSERT INTO api_keys" in q[0]][0]
    assert insert[1][4] == "quarantine" and insert[1][5] == "serv"


def test_key_ids_unique():
    m, _ = _make()
    _, a = m.issue_key()
    _, b = m.issue_key()
    assert a != b


# ── get(): fail-closed lookup ───────────────────────────────────────────────


def test_get_returns_config():
    row = ("elkid_1", "quarantine", "serv", False, True, "shadow-x", False, False)
    m, _ = _make(next_rows=[[row]])
    cfg = m.get("elk_abc")
    assert cfg.key_id == "elkid_1"
    assert cfg.mode == "quarantine"
    assert cfg.deep_analysis is True
    assert cfg.serv_shadow_hint == "shadow-x"


def test_get_looks_up_by_hash():
    m, pool = _make(next_rows=[[]])
    m.get("elk_secret")
    lookup = [q for q in pool.queries if "FROM api_keys" in q[0]][0]
    assert lookup[1] == (hash_key("elk_secret"),)
    assert "revoked_at IS NULL" in lookup[0]


def test_get_unknown_returns_none():
    m, _ = _make(next_rows=[[]])
    assert m.get("elk_unknown") is None


def test_get_db_error_propagates():
    """Fail closed: a broken key store must not forward requests."""
    pool = _FakePool()
    m = NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    pool.fail = True
    with pytest.raises(RuntimeError, match="db down"):
        m.get("elk_any")


# ── emit(): fail-soft sink ──────────────────────────────────────────────────


def _event(**kw):
    base = dict(
        key_id="elkid_1",
        ts=datetime(2026, 11, 15, tzinfo=UTC),
        route="/v1/chat/completions",
        provider="openai",
        upstream="serv",
        parts_scanned=3,
        action="quarantined",
        overall="high",
        latency_ms_elcaro=12.4,
        latency_ms_upstream=380.0,
        serv_input_tokens=None,
        serv_output_tokens=None,
        charge_usdc=Decimal("0.010000"),
    )
    return SimpleNamespace(**{**base, **kw})


def test_emit_inserts_all_event_fields():
    m, pool = _make()
    m.emit(_event())
    insert = [q for q in pool.queries if "INSERT INTO usage_events" in q[0]][0]
    sql, params = insert
    for col in (
        "key_id",
        "ts",
        "route",
        "provider",
        "upstream",
        "parts_scanned",
        "action",
        "overall",
        "latency_ms_elcaro",
        "latency_ms_upstream",
        "serv_input_tokens",
        "serv_output_tokens",
        "charge_usdc",
    ):
        assert col in sql
    assert params[0] == "elkid_1" and params[5] == 3 and params[12] == Decimal("0.010000")


def test_emit_never_raises():
    pool = _FakePool()
    m = NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    pool.fail = True
    m.emit(_event())  # drops silently — paid traffic unaffected


# ── revoke / list / rollups ─────────────────────────────────────────────────


def test_revoke_soft():
    m, pool = _make()
    assert m.revoke_key("elkid_1") is True
    upd = [q for q in pool.queries if "UPDATE api_keys" in q[0]][0]
    assert "revoked_at = now()" in upd[0] and upd[1] == ("elkid_1",)


def test_revoke_already_revoked():
    m, _ = _make(rowcount=0)
    assert m.revoke_key("elkid_1") is False


def test_list_keys_never_exposes_secrets():
    row = ("elkid_1", "elk_AbCdEf12", "bench", "quarantine", "serv", True, "ts", None)
    m, pool = _make(next_rows=[[row]])
    keys = m.list_keys()
    assert keys[0]["key_prefix"] == "elk_AbCdEf12"
    assert "key_hash" not in keys[0]
    assert "key_hash" not in pool.queries[-1][0]


def test_rollup_day_upserts():
    m, pool = _make(rowcount=42)
    n = m.rollup_day(date(2026, 11, 15))
    assert n == 42
    sql, params = [q for q in pool.queries if "INSERT INTO usage_daily" in q[0]][0]
    assert "ON CONFLICT (key_id, day, route, action)" in sql
    assert params == (date(2026, 11, 15), date(2026, 11, 15), date(2026, 11, 15))


def test_key_usage_aggregates():
    m, _ = _make(next_rows=[[(120, 480, 5000, 3000, Decimal("1.200000"))]])
    u = m.key_usage("elkid_1", days=7)
    assert u["requests"] == 120 and u["charge_usdc"] == Decimal("1.200000")
    assert u["days"] == 7


def test_public_metrics_no_identifiers():
    m, pool = _make(next_rows=[[(500, 2000, 17)], [("quarantined", 30), ("blocked", 5)]])
    met = m.public_metrics(days=30)
    assert met == {
        "days": 30,
        "requests": 500,
        "parts_scanned": 2000,
        "active_keys": 17,
        "by_action": {"quarantined": 30, "blocked": 5},
    }
    sql = " ".join(q for q, _ in pool.queries)
    assert "GROUP BY action" in sql


# ── env wiring ──────────────────────────────────────────────────────────────


def test_from_env_no_dsn(monkeypatch):
    monkeypatch.delenv("ELCARO_METERING_DSN", raising=False)
    monkeypatch.delenv("ELCARO_CANARY_DSN", raising=False)
    assert from_env() is None


def test_from_env_dsn(monkeypatch):
    monkeypatch.setenv("ELCARO_METERING_DSN", "postgresql://m")
    m = from_env(pool=_FakePool(), config_factory=_factory)
    assert isinstance(m, NeonMetering)


def test_from_env_falls_back_to_canary_dsn(monkeypatch):
    monkeypatch.delenv("ELCARO_METERING_DSN", raising=False)
    monkeypatch.setenv("ELCARO_CANARY_DSN", "postgresql://c")
    assert isinstance(from_env(pool=_FakePool(), config_factory=_factory), NeonMetering)


def test_install_registers_both_protocols():
    """install() wires set_usage_sink + set_key_store — stubbed core.usage."""
    calls = []
    stub = SimpleNamespace(
        set_usage_sink=lambda s: calls.append(("sink", s)),
        set_key_store=lambda s: calls.append(("store", s)),
    )
    sys.modules.setdefault("core.usage", stub)
    try:
        m, _ = _make()
        assert m.install() is m
        assert calls == [("sink", m), ("store", m)]
    finally:
        sys.modules.pop("core.usage", None)
