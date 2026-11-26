"""Durable scan rate limiting for the public miner edge.

The free scan path is cheap but not free: anonymous callers can otherwise fan
unbounded traffic through a public miner and, worse, trick it into invoking
paid second-opinion rails. This module implements fixed-window limits keyed by
an HMAC of the caller IP. Postgres is used when a DSN is configured so limits
survive restarts and multiple workers; in-memory mode is explicitly a local
development fallback.

Rate limiting is opt-in via environment so the test suite and local miners do
not unexpectedly throttle themselves. Production enables it in
deploy/ecosystem.config.cjs.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS scan_rate_windows (
    bucket      text NOT NULL,
    window_start bigint NOT NULL,
    count       int NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (bucket, window_start)
)
"""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0
    limit: int = 0
    remaining: int = 0
    reason: str = ""


class InMemoryScanRateLimiter:
    """Single-process fixed-window limiter — local/dev fallback only."""

    def __init__(
        self, *, per_minute: int, per_day: int, pepper: str, namespace: str = "scan"
    ) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self.namespace = namespace
        self._pepper = pepper.encode()
        self._windows: dict[tuple[str, int], int] = {}

    def _ip_key(self, ip: str) -> str:
        return hmac.new(self._pepper, ip.encode(), hashlib.sha256).hexdigest()[:32]

    def _increment(self, bucket: str, window_start: int) -> int:
        key = (bucket, window_start)
        value = self._windows.get(key, 0) + 1
        self._windows[key] = value
        # Bound memory: windows are immutable after expiry, so old entries can
        # be dropped lazily whenever a caller arrives.
        now = int(time.time())
        for k in list(self._windows):
            _, start = k
            if start < now - 2 * 86400:
                del self._windows[k]
        return value

    def _increment_pair(self, ip_key: str, minute_start: int, day_start: int) -> tuple[int, int]:
        return (
            self._increment(f"{self.namespace}:minute:{ip_key}", minute_start),
            self._increment(f"{self.namespace}:day:{ip_key}", day_start),
        )

    def _decision(self, minute_count: int, day_count: int, now: int) -> RateLimitDecision:
        if minute_count > self.per_minute:
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=60 - (now % 60),
                limit=self.per_minute,
                remaining=0,
                reason="minute",
            )
        if day_count > self.per_day:
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=86400 - (now % 86400),
                limit=self.per_day,
                remaining=0,
                reason="day",
            )
        return RateLimitDecision(
            allowed=True,
            limit=self.per_day,
            remaining=max(0, self.per_day - day_count),
        )

    def check(self, ip: str) -> RateLimitDecision:
        now = int(time.time())
        ip_key = self._ip_key(ip)
        minute_start = now - (now % 60)
        day_start = now - (now % 86400)
        minute_count, day_count = self._increment_pair(ip_key, minute_start, day_start)
        return self._decision(minute_count, day_count, now)


class PostgresScanRateLimiter(InMemoryScanRateLimiter):
    """Neon/Postgres-backed fixed-window limiter.

    Construction fails loud when the configured DSN is unusable: a deployment
    that asked for durable cost protection should not silently revert to no
    protection. Runtime failures fail closed for premium traffic handled by the
    caller; ordinary scans are still limited as far as the database can tell.
    """

    def __init__(
        self,
        dsn: str,
        *,
        per_minute: int,
        per_day: int,
        pepper: str,
        namespace: str = "scan",
        pool=None,
    ) -> None:
        super().__init__(per_minute=per_minute, per_day=per_day, pepper=pepper, namespace=namespace)
        if pool is None:
            try:
                from psycopg_pool import ConnectionPool
            except ImportError as e:
                raise RuntimeError(
                    "PostgresScanRateLimiter requires psycopg[pool] — "
                    "install with: pip install 'elcaro[miner]'"
                ) from e
            pool = ConnectionPool(
                dsn,
                min_size=1,
                max_size=2,
                open=True,
                check=ConnectionPool.check_connection,
                max_idle=240,
            )
        self._pool = pool
        with self._pool.connection() as conn:  # boot validation — fails loud
            conn.execute("SELECT 1")
            conn.execute(_DDL)

    def _increment(self, bucket: str, window_start: int) -> int:
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO scan_rate_windows (bucket, window_start, count)
                VALUES (%s, %s, 1)
                ON CONFLICT (bucket, window_start)
                DO UPDATE SET count = scan_rate_windows.count + 1,
                              updated_at = now()
                RETURNING count
                """,
                (bucket, window_start),
            ).fetchone()
        return int(row[0])

    def _increment_pair(self, ip_key: str, minute_start: int, day_start: int) -> tuple[int, int]:
        # Both windows are upserted in one round trip. Rate limiting sits in
        # front of a sub-2ms scan engine, so per-request Neon latency matters.
        minute_bucket = f"{self.namespace}:minute:{ip_key}"
        day_bucket = f"{self.namespace}:day:{ip_key}"
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                WITH minute_window AS (
                    INSERT INTO scan_rate_windows (bucket, window_start, count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (bucket, window_start)
                    DO UPDATE SET count = scan_rate_windows.count + 1,
                                  updated_at = now()
                    RETURNING count
                ), day_window AS (
                    INSERT INTO scan_rate_windows (bucket, window_start, count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (bucket, window_start)
                    DO UPDATE SET count = scan_rate_windows.count + 1,
                                  updated_at = now()
                    RETURNING count
                )
                SELECT minute_window.count, day_window.count
                FROM minute_window, day_window
                """,
                (minute_bucket, minute_start, day_bucket, day_start),
            ).fetchone()
        return int(row[0]), int(row[1])


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _build_limiter(
    *,
    per_minute: int,
    per_day: int,
    pepper: str,
    dsn: str | None,
    namespace: str,
):
    if dsn:
        return PostgresScanRateLimiter(
            dsn,
            per_minute=per_minute,
            per_day=per_day,
            pepper=pepper,
            namespace=namespace,
        )
    log.warning(
        "scan rate limiting is enabled without a DSN for %s — using single-process memory",
        namespace,
    )
    return InMemoryScanRateLimiter(
        per_minute=per_minute,
        per_day=per_day,
        pepper=pepper,
        namespace=namespace,
    )


def _rate_limit_pepper() -> str:
    return (
        os.environ.get("ELCARO_RATE_LIMIT_SALT")
        or os.environ.get("ELCARO_SIGNING_KEY")
        or os.environ.get("ELCARO_SCAN_RATE_LIMIT_DSN")
        or os.environ.get("ELCARO_METERING_DSN")
        or os.environ.get("ELCARO_CANARY_DSN")
        or "elcaro-dev-rate-limit"
    )


def _rate_limit_dsn() -> str | None:
    return (
        os.environ.get("ELCARO_SCAN_RATE_LIMIT_DSN")
        or os.environ.get("ELCARO_METERING_DSN")
        or os.environ.get("ELCARO_CANARY_DSN")
    )


def scan_rate_limiters_from_env():
    """Build (ordinary-scan, premium-scan) limiters; either may be None.

    Env:
      ELCARO_SCAN_RATE_LIMIT_PER_DAY           — 0/absent disables ordinary quota
      ELCARO_SCAN_RATE_LIMIT_PER_MINUTE        — ordinary burst guard, default 6
      ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_DAY   — 0/absent disables premium quota
      ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_MINUTE — premium burst guard, default 1
      ELCARO_SCAN_RATE_LIMIT_DSN               — preferred Postgres DSN
      ELCARO_METERING_DSN / ELCARO_CANARY_DSN  — fallback DSNs already deployed
      ELCARO_RATE_LIMIT_SALT                   — HMAC pepper for stored IP keys
    """
    pepper = _rate_limit_pepper()
    dsn = _rate_limit_dsn()

    scan_day = _int_env("ELCARO_SCAN_RATE_LIMIT_PER_DAY", 0)
    scan = None
    if scan_day > 0:
        scan = _build_limiter(
            per_minute=_int_env("ELCARO_SCAN_RATE_LIMIT_PER_MINUTE", 6),
            per_day=scan_day,
            pepper=pepper,
            dsn=dsn,
            namespace="scan",
        )

    premium_day = _int_env("ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_DAY", 0)
    premium = None
    if premium_day > 0:
        premium = _build_limiter(
            per_minute=_int_env("ELCARO_PREMIUM_SCAN_RATE_LIMIT_PER_MINUTE", 1),
            per_day=premium_day,
            pepper=pepper,
            dsn=dsn,
            namespace="premium_scan",
        )
    return scan, premium


def direct_scan_rate_limiter_from_env():
    """Build the higher-volume direct-ingress limiter, or None.

    Direct miner ingress is a mixed bag: legitimate Telegraph devnode traffic
    and callers bypassing the web app look similar because the protocol does
    not authenticate the devnode to the miner. It therefore gets a separate
    resource-protection quota instead of the strict browser conversion quota.
    Premium second-opinion rails remain tightly capped for everyone.
    """
    per_day = _int_env("ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_DAY", 0)
    if per_day <= 0:
        return None
    return _build_limiter(
        per_minute=_int_env("ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_MINUTE", 30),
        per_day=per_day,
        pepper=_rate_limit_pepper(),
        dsn=_rate_limit_dsn(),
        namespace="direct_scan",
    )


def rate_limiter_from_env():
    """Backward-compatible ordinary-scan limiter factory."""
    return scan_rate_limiters_from_env()[0]
