"""Neon-backed C2 storage — UsageSink + KeyStore over Postgres.

Dev C's half of contract C2 (``core/usage.py``, §7.1): Dev B's Gateway
emits :class:`UsageEvent`s and resolves caller keys through ``get_key``;
this module stores them durably and serves hashed-key lookups.

Design, mirroring ``core/canary.py``:

- Construction fails loud: bad DSN / unreachable DB raises at boot
  (SELECT 1 + auto-DDL) — a misconfigured metering dependency should
  never silently degrade to unbilled traffic.
- ``emit`` fails soft: a mid-flight outage logs and drops the event —
  metering must never take paid traffic down (contract requirement).
- ``get`` fails CLOSED: lookup errors propagate — an unknown key state
  must fail the request, never forward it (contract requirement).

``core.usage``/``core.policy`` are lazy-imported: they land with Dev B's
branch, and this module is already correct against their Protocols.
``psycopg[pool]`` is lazy-imported — install via ``elcaro[miner]``.

Env: ``ELCARO_METERING_DSN``, falling back to ``ELCARO_CANARY_DSN``
(same Neon project pattern as canary).
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from collections.abc import Callable
from datetime import date
from typing import Any

log = logging.getLogger(__name__)

KEY_PREFIX_LEN = 12  # "elk_" + 8 chars shown in the key-management UI

# ── Schema (auto-DDL at construction, same posture as canary) ────────────────
#
# api_keys     — hashed caller keys + per-key KeyConfig fields (§7.1 C2).
#                The raw key is never stored; sha256(raw) is the lookup.
# usage_events — append-only event log, one row per metered request.
#                key_id is intentionally NOT a FK: x402 pay-per-call
#                events carry ephemeral ids with no api_keys row.
# usage_daily  — rollup written by rollup_day(); feeds /metrics and the
#                key-management page without scanning the event log.

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        key_id              text PRIMARY KEY,
        key_hash            text NOT NULL UNIQUE,
        key_prefix          text NOT NULL,
        label               text NOT NULL DEFAULT '',
        mode                text NOT NULL DEFAULT 'quarantine',
        upstream            text NOT NULL DEFAULT 'serv',
        scan_user_messages  boolean NOT NULL DEFAULT false,
        deep_analysis       boolean NOT NULL DEFAULT false,
        serv_shadow_hint    text,
        retention_opt_in    boolean NOT NULL DEFAULT false,
        fail_open           boolean NOT NULL DEFAULT false,
        created_at          timestamptz NOT NULL DEFAULT now(),
        revoked_at          timestamptz
    )
    """,
    "CREATE INDEX IF NOT EXISTS api_keys_hash_idx ON api_keys(key_hash)",
    """
    CREATE TABLE IF NOT EXISTS usage_events (
        id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        key_id                text NOT NULL,
        ts                    timestamptz NOT NULL,
        route                 text NOT NULL,
        provider              text NOT NULL,
        upstream              text NOT NULL,
        parts_scanned         int NOT NULL,
        action                text NOT NULL,
        overall               text NOT NULL,
        latency_ms_elcaro     double precision NOT NULL,
        latency_ms_upstream   double precision NOT NULL,
        serv_input_tokens     int,
        serv_output_tokens    int,
        charge_usdc           numeric(14,6) NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS usage_events_key_ts_idx ON usage_events(key_id, ts)",
    "CREATE INDEX IF NOT EXISTS usage_events_ts_idx ON usage_events(ts)",
    """
    CREATE TABLE IF NOT EXISTS usage_daily (
        key_id                    text NOT NULL,
        day                       date NOT NULL,
        route                     text NOT NULL,
        action                    text NOT NULL,
        requests                  int NOT NULL,
        parts_scanned             int NOT NULL,
        serv_input_tokens         bigint NOT NULL DEFAULT 0,
        serv_output_tokens        bigint NOT NULL DEFAULT 0,
        charge_usdc               numeric(14,6) NOT NULL DEFAULT 0,
        latency_ms_elcaro_total   double precision NOT NULL DEFAULT 0,
        latency_ms_upstream_total double precision NOT NULL DEFAULT 0,
        PRIMARY KEY (key_id, day, route, action)
    )
    """,
)

# UsageEvent field names → usage_events columns, 1:1 (contract C2).
_EVENT_COLUMNS = (
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
)


def hash_key(raw_key: str) -> str:
    """Storage form of a caller key: sha256 hex. Raw keys never persist."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _default_key_config(fields: dict[str, Any]) -> Any:
    """Row fields → ``core.usage.KeyConfig`` (lazy — lands with Dev B's
    branch). ``mode`` is stored as its string value."""
    from core.policy import Mode
    from core.usage import KeyConfig

    return KeyConfig(mode=Mode(fields.pop("mode")), **fields)


class NeonMetering:
    """UsageSink + KeyStore over one pooled Neon connection.

    Satisfies both C2 protocols structurally — the Gateway installs it via
    :func:`install_from_env`, which calls ``set_usage_sink``/``set_key_store``.
    """

    def __init__(
        self,
        dsn: str,
        *,
        pool=None,
        config_factory: Callable[[dict], Any] | None = None,
    ) -> None:
        if pool is None:
            try:
                from psycopg_pool import ConnectionPool
            except ImportError as e:
                raise RuntimeError(
                    "NeonMetering requires psycopg[pool] — "
                    "install with: pip install 'elcaro[miner]'"
                ) from e
            pool = ConnectionPool(dsn, min_size=1, max_size=4, open=True)
        self._pool = pool
        self._config_factory = config_factory or _default_key_config
        with self._pool.connection() as conn:  # boot validation — fails loud
            conn.execute("SELECT 1")
            for stmt in _DDL:
                conn.execute(stmt)

    def _conn(self):
        return self._pool.connection()

    # ── UsageSink ──────────────────────────────────────────────────────────

    def emit(self, event: Any) -> None:
        """Append one UsageEvent. Never raises — the caller's request path
        is paid traffic; a metering outage degrades visibility only."""
        try:
            cols = ", ".join(_EVENT_COLUMNS)
            ph = ", ".join(["%s"] * len(_EVENT_COLUMNS))
            with self._conn() as conn:
                conn.execute(
                    # cols/ph derive from the _EVENT_COLUMNS constant only —
                    # user input reaches the query solely via bound params.
                    f"INSERT INTO usage_events ({cols}) VALUES ({ph})",  # noqa: S608
                    tuple(getattr(event, c) for c in _EVENT_COLUMNS),
                )
        except Exception:
            log.exception("usage event dropped — metering outage, request unaffected")

    # ── KeyStore ───────────────────────────────────────────────────────────

    def get(self, raw_key: str) -> Any | None:
        """Raw key → KeyConfig, or None for unknown/revoked keys.

        Lookup errors PROPAGATE — the gateway fails the request closed."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT key_id, mode, upstream, scan_user_messages, deep_analysis,"
                " serv_shadow_hint, retention_opt_in, fail_open"
                " FROM api_keys WHERE key_hash = %s AND revoked_at IS NULL",
                (hash_key(raw_key),),
            ).fetchone()
        if row is None:
            return None
        cols = (
            "key_id",
            "mode",
            "upstream",
            "scan_user_messages",
            "deep_analysis",
            "serv_shadow_hint",
            "retention_opt_in",
            "fail_open",
        )
        return self._config_factory(dict(zip(cols, row, strict=True)))

    # ── Key issuance & management (web key page) ───────────────────────────

    def issue_key(self, *, label: str = "", **flags: Any) -> tuple[str, str]:
        """Mint ``elk_…`` + config → (raw_key, key_id). The raw key is shown
        once to the caller; only its sha256 hash persists."""
        raw = "elk_" + secrets.token_urlsafe(24)
        key_id = "elkid_" + secrets.token_hex(8)
        fields = {
            "mode": "quarantine",
            "upstream": "serv",
            "scan_user_messages": False,
            "deep_analysis": False,
            "serv_shadow_hint": None,
            "retention_opt_in": False,
            "fail_open": False,
            **flags,
        }
        mode = fields["mode"]
        if hasattr(mode, "value"):  # Mode enum → its string value
            mode = mode.value
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO api_keys (key_id, key_hash, key_prefix, label, mode,"
                " upstream, scan_user_messages, deep_analysis, serv_shadow_hint,"
                " retention_opt_in, fail_open)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    key_id,
                    hash_key(raw),
                    raw[:KEY_PREFIX_LEN],
                    label,
                    mode,
                    fields["upstream"],
                    fields["scan_user_messages"],
                    fields["deep_analysis"],
                    fields["serv_shadow_hint"],
                    fields["retention_opt_in"],
                    fields["fail_open"],
                ),
            )
        return raw, key_id

    def revoke_key(self, key_id: str) -> bool:
        """Soft-revoke — historical usage rows stay attributable."""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE api_keys SET revoked_at = now() WHERE key_id = %s AND revoked_at IS NULL",
                (key_id,),
            )
            return cur.rowcount > 0

    def list_keys(self) -> list[dict]:
        """Key-management page rows: never hashes, never raw keys."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key_id, key_prefix, label, mode, upstream, deep_analysis,"
                " created_at, revoked_at FROM api_keys ORDER BY created_at DESC"
            ).fetchall()
        cols = (
            "key_id",
            "key_prefix",
            "label",
            "mode",
            "upstream",
            "deep_analysis",
            "created_at",
            "revoked_at",
        )
        return [dict(zip(cols, r, strict=True)) for r in rows]

    # ── Rollups & reporting ────────────────────────────────────────────────

    def rollup_day(self, day: date) -> int:
        """Aggregate one day's events into usage_daily. Idempotent — safe
        to re-run for backfill or catch-up. Returns groups written."""
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO usage_daily
                    (key_id, day, route, action, requests, parts_scanned,
                     serv_input_tokens, serv_output_tokens, charge_usdc,
                     latency_ms_elcaro_total, latency_ms_upstream_total)
                SELECT key_id, %s, route, action, count(*), sum(parts_scanned),
                       coalesce(sum(serv_input_tokens), 0),
                       coalesce(sum(serv_output_tokens), 0),
                       sum(charge_usdc), sum(latency_ms_elcaro),
                       sum(latency_ms_upstream)
                FROM usage_events
                WHERE ts >= %s AND ts < %s + interval '1 day'
                GROUP BY key_id, route, action
                ON CONFLICT (key_id, day, route, action) DO UPDATE SET
                    requests                  = EXCLUDED.requests,
                    parts_scanned             = EXCLUDED.parts_scanned,
                    serv_input_tokens         = EXCLUDED.serv_input_tokens,
                    serv_output_tokens        = EXCLUDED.serv_output_tokens,
                    charge_usdc               = EXCLUDED.charge_usdc,
                    latency_ms_elcaro_total   = EXCLUDED.latency_ms_elcaro_total,
                    latency_ms_upstream_total = EXCLUDED.latency_ms_upstream_total
                """,
                (day, day, day),
            )
            return cur.rowcount

    def key_usage(self, key_id: str, *, days: int = 30) -> dict:
        """Per-key totals for the management page, from usage_daily."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT coalesce(sum(requests), 0), coalesce(sum(parts_scanned), 0),"
                " coalesce(sum(serv_input_tokens), 0),"
                " coalesce(sum(serv_output_tokens), 0),"
                " coalesce(sum(charge_usdc), 0)"
                " FROM usage_daily"
                " WHERE key_id = %s AND day >= current_date - %s",
                (key_id, days),
            ).fetchone()
        reqs, parts, si, so, charge = row
        return {
            "key_id": key_id,
            "days": days,
            "requests": reqs,
            "parts_scanned": parts,
            "serv_input_tokens": si,
            "serv_output_tokens": so,
            "charge_usdc": charge,
        }

    def public_metrics(self, *, days: int = 30) -> dict:
        """Aggregated, non-identifying numbers for public /metrics."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT coalesce(sum(requests), 0), coalesce(sum(parts_scanned), 0),"
                " count(DISTINCT key_id)"
                " FROM usage_daily WHERE day >= current_date - %s",
                (days,),
            ).fetchone()
            actions = conn.execute(
                "SELECT action, sum(requests) FROM usage_daily"
                " WHERE day >= current_date - %s GROUP BY action",
                (days,),
            ).fetchall()
        reqs, parts, keys = row
        return {
            "days": days,
            "requests": reqs,
            "parts_scanned": parts,
            "active_keys": keys,
            "by_action": {a: n for a, n in actions},
        }

    # ── Install ────────────────────────────────────────────────────────────

    def install(self) -> NeonMetering:
        """Register as the process-wide usage sink + key store (C2)."""
        from core.usage import set_key_store, set_usage_sink

        set_usage_sink(self)
        set_key_store(self)
        return self


def from_env(*, pool=None, config_factory=None) -> NeonMetering | None:
    """``ELCARO_METERING_DSN`` (else ``ELCARO_CANARY_DSN``) → NeonMetering;
    no DSN → None (callers keep the in-memory/stdout stubs)."""
    dsn = os.environ.get("ELCARO_METERING_DSN") or os.environ.get("ELCARO_CANARY_DSN")
    if not dsn:
        return None
    return NeonMetering(dsn, pool=pool, config_factory=config_factory)


def install_from_env(*, pool=None, config_factory=None) -> NeonMetering | None:
    """from_env + install(). None when unconfigured — gateway keeps stubs."""
    m = from_env(pool=pool, config_factory=config_factory)
    return m.install() if m else None
