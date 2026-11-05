"""Canary tokens — per-issuance traceability marks for served content.

Same string ≠ copied is the unsolved problem in swarm forensics: when a
steering artifact shows up under N actor labels, shared text alone can't
tell propagation from independent typing. A per-copy token makes the edge
exact: if a quarantine notice minted at scan S later appears inside content
scanned at scan S', the token resolves S' → S deterministically.

The load-bearing surface is the quarantine notice itself — the one Elcaro
output designed for verbatim relay ("Tell your user: ..." is meant to be
quoted). Agents that carry the notice into shared channels, chat boards, or
downstream scans carry the token with it.

Two readings of a token found inside scanned content:
    - recognized  — this miner issued it: the notice is genuine, and the
      hit reports what the original scan saw (score, techniques, content
      hash — never the content itself; the miner stays stateless).
    - unrecognized but well-formed — either minted by another Elcaro
      deployment, minted before a restart, or forged. A forged quarantine
      notice is itself a deception signal (in-band text is spoofable — the
      verdict signature covers the JSON; the canary covers the relayed
      text), but "unrecognized" alone doesn't distinguish those cases, so
      the field is informational — it never changes the risk score.

Agloe-style caveat worth restating: a token only survives verbatim copying.
Agents that paraphrase the notice drop it — like every trap street, this
traces copies, not ideas.

Env:
    ELCARO_CANARY=0 disables entirely.
    ELCARO_CANARY_DSN=postgresql://... switches to the durable Postgres
        registry (Neon) — tokens survive restarts and resolve across
        deploys. The table is auto-created on first boot.
    Otherwise: in-memory bounded FIFO (default) — state resets on restart,
        tokens from before resolve as unrecognized.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from collections import OrderedDict
from typing import Any

log = logging.getLogger(__name__)

# elc-<unix-hex>-<6 rand hex>. The timestamp segment makes every token
# self-describing — a canary found in a dated external corpus is
# cross-checkable against issuance time without calling the miner.
TOKEN_RE = re.compile(r"elc-[0-9a-f]{6,10}-[0-9a-f]{6}\b")

DEFAULT_CAPACITY = 50_000


class CanaryRegistry:
    """Bounded in-memory token → issuance-event map.

    Records verdict metadata only (hash, score, techniques) — never the
    scanned content — keeping the miner's no-content-retention posture.
    FIFO eviction past capacity: oldest tokens resolve as unrecognized.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self.capacity = capacity
        self._events: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def mint(self, kind: str = "scan", **event: Any) -> str:
        """Issue a token and record the serving event it points back to.

        ``kind`` labels the serving surface — "scan" for quarantine
        notices, "specimen_serve" for stamped specimen fetches — so a
        resolved token says *what* was relayed, not just that it was.
        """
        token = f"elc-{int(time.time()):x}-{secrets.token_hex(3)}"
        event = {"issued_at": int(time.time()), "kind": kind, **event}
        self._events[token] = event
        self._events.move_to_end(token)
        while len(self._events) > self.capacity:
            self._events.popitem(last=False)
        return token

    def lookup(self, token: str) -> dict[str, Any] | None:
        """The issuance event for a token, or None if this miner didn't
        mint it (or it aged out of the FIFO window)."""
        return self._events.get(token)

    def __len__(self) -> int:
        return len(self._events)


def extract_canaries(text: str) -> list[str]:
    """All well-formed canary tokens in a text, first-seen order."""
    return list(dict.fromkeys(TOKEN_RE.findall(text)))


_CANARY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS canary_events (
    token     TEXT PRIMARY KEY,
    kind      TEXT NOT NULL DEFAULT 'scan',
    issued_at BIGINT NOT NULL,
    payload   JSONB NOT NULL DEFAULT '{}'::jsonb
)
"""


class PostgresCanaryRegistry:
    """Durable canary registry — Postgres-backed (Neon).

    Same contract as CanaryRegistry; the engine doesn't know which it
    holds. Two deliberate asymmetries, matching the project's security
    posture:

      - Construction fails loud: a bad DSN or unreachable database raises
        at boot (SELECT 1 + auto-DDL), because a misconfigured security
        dependency should never silently degrade.
      - Runtime operations fail soft: a mid-flight outage on mint/lookup
        logs and returns None — an unstamped scan or an unrecognized
        token beats a 500. Detection availability outranks provenance.

    Connections are pooled (psycopg_pool) so mint stays ~1ms once warm.
    """

    def __init__(self, dsn: str, *, pool=None) -> None:
        if pool is None:
            try:
                from psycopg_pool import ConnectionPool
            except ImportError as e:
                raise RuntimeError(
                    "PostgresCanaryRegistry requires psycopg[pool] — "
                    "install with: pip install 'elcaro[miner]'"
                ) from e
            pool = ConnectionPool(dsn, min_size=1, max_size=4, open=True)
        self._pool = pool
        with self._conn() as conn:  # boot-time validation — fails loud
            conn.execute("SELECT 1")
            conn.execute(_CANARY_TABLE_SQL)

    def _conn(self):
        return self._pool.connection()

    def mint(self, kind: str = "scan", **event: Any) -> str | None:
        """Issue a token; None when the database is unreachable."""
        token = f"elc-{int(time.time()):x}-{secrets.token_hex(3)}"
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO canary_events (token, kind, issued_at, payload) "
                    "VALUES (%s, %s, %s, %s::jsonb) ON CONFLICT (token) DO NOTHING",
                    (token, kind, int(time.time()), json.dumps(event)),
                )
        except Exception:
            log.exception("canary mint failed — scan proceeds unstamped")
            return None
        return token

    def lookup(self, token: str) -> dict[str, Any] | None:
        """The issuance event for a token, or None — same contract as the
        in-memory registry (unknown, aged-out, or DB unreachable)."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT kind, issued_at, payload FROM canary_events WHERE token = %s",
                    (token,),
                ).fetchone()
        except Exception:
            log.exception("canary lookup failed for %s", token)
            return None
        if row is None:
            return None
        kind, issued_at, payload = row
        return {"issued_at": issued_at, "kind": kind, **(payload or {})}

    def __len__(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT count(*) FROM canary_events").fetchone()[0]


def registry_from_env() -> CanaryRegistry | PostgresCanaryRegistry | None:
    """ELCARO_CANARY=0 disables; ELCARO_CANARY_DSN → durable Postgres;
    anything else → in-memory FIFO."""
    if os.environ.get("ELCARO_CANARY") == "0":
        return None
    dsn = os.environ.get("ELCARO_CANARY_DSN")
    if dsn:
        return PostgresCanaryRegistry(dsn)
    return CanaryRegistry()
