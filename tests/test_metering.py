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

from core.usage import UsageEvent
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
        if self._pool.fail_times > 0:
            self._pool.fail_times -= 1
            raise self._pool.fail_exc
        if self._pool.fail:
            raise RuntimeError("db down")
        self._pool.queries.append((sql, params))
        rows = self._pool.next_rows.pop(0) if self._pool.next_rows else []
        return _FakeResult(rows, rowcount=len(rows) or self._pool.rowcount)


class _FakePool:
    """Stand-in for psycopg_pool.ConnectionPool — records (sql, params).

    ``fail_times`` raises ``fail_exc`` on the next N execute() calls
    (staged post-construction, like next_rows); ``acquisitions`` counts
    pool.connection() checkouts for retry assertions."""

    def __init__(self, next_rows=None, fail=False, rowcount=1):
        self.queries = []
        self.next_rows = list(next_rows or [])
        self.fail = fail
        self.rowcount = rowcount
        self.fail_times = 0
        self.fail_exc = RuntimeError("db down")
        self.acquisitions = 0

    def connection(self):
        self.acquisitions += 1
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
        event_id="ev-test",
        payer_address=None,
        payment_network=None,
        payment_tx_hash=None,
        settlement_status="none",
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


# ── Idle-reconnect retry (Neon autosuspend) ─────────────────────────────────
#
# Neon suspends idle compute (~5 min) and kills pooled connections with
# AdminShutdown — an OperationalError subclass. Read/idempotent paths retry
# once on a fresh connection; emit (INSERT — ambiguous-commit double-bill
# risk) and issue_key (caller retries) deliberately do not.


def _op_error():
    import psycopg

    return psycopg.OperationalError("terminating connection due to administrator command")


def test_get_retries_once_on_operational_error():
    row = ("elkid_1", "quarantine", "serv", False, True, "shadow-x", False, False)
    m, pool = _make(next_rows=[[row]])
    pool.fail_times, pool.fail_exc = 1, _op_error()
    before = pool.acquisitions
    cfg = m.get("elk_abc")
    assert cfg.key_id == "elkid_1"
    assert pool.acquisitions - before == 2  # dead conn + fresh conn


def test_get_propagates_when_both_attempts_fail():
    """Fail closed still holds — a second failure must propagate."""
    m, pool = _make()
    pool.fail_times, pool.fail_exc = 2, _op_error()
    before = pool.acquisitions
    with pytest.raises(Exception, match="terminating connection"):
        m.get("elk_any")
    assert pool.acquisitions - before == 2  # retried once, then gave up


def test_list_keys_retries_once():
    row = ("elkid_1", "elk_AbCdEf12", "bench", "quarantine", "serv", True, "ts", None)
    m, pool = _make(next_rows=[[row]])
    pool.fail_times, pool.fail_exc = 1, _op_error()
    keys = m.list_keys()
    assert keys[0]["key_id"] == "elkid_1"


def test_revoke_key_retries_once():
    m, pool = _make()
    pool.fail_times, pool.fail_exc = 1, _op_error()
    assert m.revoke_key("elkid_1") is True


def test_emit_never_retries_and_never_raises():
    """INSERT retry could double-bill after an ambiguous commit — one try."""
    m, pool = _make()
    pool.fail_times, pool.fail_exc = 5, _op_error()
    before = pool.acquisitions
    m.emit(_event())
    assert pool.acquisitions - before == 1


def test_issue_key_never_retries():
    """Caller-visible error — the user can retry; no silent re-INSERT."""
    m, pool = _make()
    pool.fail_times, pool.fail_exc = 5, _op_error()
    before = pool.acquisitions
    with pytest.raises(Exception, match="terminating connection"):
        m.issue_key()
    assert pool.acquisitions - before == 1


def test_default_pool_health_check_and_idle_recycling(monkeypatch):
    """Default ConnectionPool must check connections on checkout and close
    them before Neon's ~5min autosuspend kills them."""
    import psycopg_pool

    captured = {}

    class _RecPool:
        check_connection = staticmethod(lambda conn: None)

        def __init__(self, dsn, **kw):
            captured.update(kw)
            captured["dsn"] = dsn
            self._fake = _FakePool()

        def connection(self):
            return self._fake.connection()

    monkeypatch.setattr(psycopg_pool, "ConnectionPool", _RecPool)
    NeonMetering("postgresql://x", config_factory=_factory)
    assert captured["check"] is _RecPool.check_connection
    assert captured["max_idle"] == 240
    assert captured["min_size"] == 1 and captured["max_size"] == 4
    assert captured["open"] is True


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


def test_install_registers_both_protocols(monkeypatch):
    """install() wires set_usage_sink + set_key_store — stubbed core.usage.

    The stub must REPLACE the real module: core/usage.py exists now, and
    tests that ran earlier already imported it — setdefault() would no-op
    and install() would register into the real globals."""
    calls = []
    stub = SimpleNamespace(
        set_usage_sink=lambda s: calls.append(("sink", s)),
        set_key_store=lambda s: calls.append(("store", s)),
    )
    monkeypatch.setitem(sys.modules, "core.usage", stub)
    m, _ = _make()
    assert m.install() is m
    assert calls == [("sink", m), ("store", m)]


# ── WS3 attribution schema ──────────────────────────────────────────────────


class _FakeConnTracking:
    """Records every executed statement so tests can assert on SQL."""

    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql.strip().split()[0].upper(), sql, params))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakePoolTracking:
    def __init__(self):
        self.conn = _FakeConnTracking()

    def connection(self):
        return self.conn


def test_ddl_includes_attribution_migration():
    """WS3: the explicit migration is part of DDL — unlike CREATE TABLE IF NOT
    EXISTS, ALTER ... IF NOT EXISTS applies to existing tables."""
    pool = _FakePoolTracking()
    NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    alters = [sql for op, sql, _ in pool.conn.executed if op == "ALTER"]
    joined = " ".join(alters)
    for col in (
        "event_id",
        "payer_address",
        "payment_network",
        "payment_tx_hash",
        "settlement_status",
    ):
        assert col in joined, f"missing migration for {col}"


def test_insert_writes_attribution_columns():
    pool = _FakePoolTracking()
    m = NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    ev = UsageEvent(
        key_id="x402:0xabc",
        ts=datetime(2026, 11, 15, tzinfo=UTC),
        route="/v1/chat/completions",
        provider="openai",
        upstream="serv",
        parts_scanned=1,
        action="none",
        overall="low",
        latency_ms_elcaro=1.0,
        latency_ms_upstream=2.0,
        payer_address="0xabc",
        payment_network="eip155:84532",
        settlement_status="pending",
    )
    m.emit(ev)
    inserts = [(sql, params) for op, sql, params in pool.conn.executed if op == "INSERT"]
    assert len(inserts) == 1
    sql, params = inserts[0]
    assert "payer_address" in sql
    # positional params follow _EVENT_COLUMNS order — locate values by index
    from metering.neon import _EVENT_COLUMNS

    values = dict(zip(_EVENT_COLUMNS, params, strict=True))
    assert values["payer_address"] == "0xabc"
    assert values["payment_network"] == "eip155:84532"
    assert values["settlement_status"] == "pending"
    assert values["event_id"] == ev.event_id


def test_update_settlement_rewrites_pending_row():
    pool = _FakePoolTracking()
    m = NeonMetering("postgresql://x", pool=pool, config_factory=_factory)
    m.record_settlement("ev-1", tx_hash="0xtx", status="settled")
    updates = [(sql, params) for op, sql, params in pool.conn.executed if op == "UPDATE"]
    assert len(updates) == 1
    sql, params = updates[0]
    assert "payment_tx_hash" in sql and "settlement_status" in sql
    assert "event_id" in sql  # keyed by event correlation id, not payer
    assert params == ("0xtx", "settled", "ev-1")


def test_record_settlement_requires_registration():
    """Without a registered metering sink, record_settlement is a safe no-op."""
    import core.usage as cu

    old = cu._sink
    try:
        cu._sink = cu.NullUsageSink()
        cu.record_settlement("ev-x", tx_hash="0x", status="settled")  # must not raise
    finally:
        cu._sink = old
