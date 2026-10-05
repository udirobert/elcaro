"""Initialize the durable canary table (canary_events).

Reads ELCARO_CANARY_DSN from the environment and instantiates
PostgresCanaryRegistry — whose constructor runs SELECT 1 plus the
CREATE TABLE IF NOT EXISTS, so this doubles as a connectivity preflight
before deploying the miner with a DSN set.

Usage:
    ELCARO_CANARY_DSN=postgresql://... python scripts/init_canary_db.py
"""

from __future__ import annotations

import os
import sys

from core.canary import PostgresCanaryRegistry


def main() -> int:
    dsn = os.environ.get("ELCARO_CANARY_DSN")
    if not dsn:
        print("ELCARO_CANARY_DSN is not set — nothing to initialize.", file=sys.stderr)
        return 1
    registry = PostgresCanaryRegistry(dsn)
    print(f"canary_events ready — {len(registry)} existing tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
