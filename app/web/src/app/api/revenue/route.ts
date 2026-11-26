/**
 * Operator revenue rollup (WS3) — admin-only, never public. Aggregates
 * usage_events into settled vs verified_local revenue, per network and lane.
 * Detailed payer-level data is deliberately absent: this answers "how much
 * did which lanes earn" not "who paid us" — drill-downs belong in operator
 * SQL access, not an HTTP surface.
 */

import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";

export const runtime = "nodejs";

let pool: Pool | null | undefined;

function getPool(): Pool | null {
  if (pool !== undefined) return pool;
  const dsn = process.env.ELCARO_METERING_DSN || process.env.ELCARO_CANARY_DSN;
  pool = dsn ? new Pool({ connectionString: dsn, max: 2 }) : null;
  return pool;
}

export async function GET(req: NextRequest) {
  const adminToken = process.env.ANALYTICS_ADMIN_TOKEN;
  if (!adminToken || req.headers.get("x-admin-token") !== adminToken) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const p = getPool();
  if (!p) {
    return NextResponse.json({ error: "metering DSN not configured" }, { status: 503 });
  }

  try {
    const daysParam = Number(req.nextUrl.searchParams.get("days") ?? "30");
    const days = Number.isFinite(daysParam) ? Math.min(90, Math.max(1, Math.floor(daysParam))) : 30;

    const [totals, byLane, byDay] = await Promise.all([
      p.query(
        `SELECT
           count(*) FILTER (WHERE payer_address IS NOT NULL)::int AS paid_events,
           coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'settled'), 0)::float AS settled_usdc,
           coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'verified_local'), 0)::float AS verified_local_usdc,
           coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'failed'), 0)::float AS failed_usdc,
           coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'pending'), 0)::float AS pending_usdc,
           count(DISTINCT payer_address) FILTER (WHERE settlement_status IN ('settled', 'verified_local'))::int AS distinct_payers
         FROM usage_events
         WHERE ts >= now() - make_interval(days => $1)`,
        [days],
      ),
      p.query(
        `SELECT route, payment_network,
                count(*)::int AS events,
                coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'settled'), 0)::float AS settled_usdc,
                coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'verified_local'), 0)::float AS verified_local_usdc
         FROM usage_events
         WHERE payer_address IS NOT NULL
           AND ts >= now() - make_interval(days => $1)
         GROUP BY route, payment_network
         ORDER BY settled_usdc DESC`,
        [days],
      ),
      p.query(
        `SELECT date_trunc('day', ts)::date AS day,
                count(*) FILTER (WHERE settlement_status = 'settled')::int AS settled_events,
                coalesce(sum(charge_usdc) FILTER (WHERE settlement_status = 'settled'), 0)::float AS settled_usdc
         FROM usage_events
         WHERE payer_address IS NOT NULL
           AND ts >= now() - make_interval(days => $1)
         GROUP BY day
         ORDER BY day DESC`,
        [days],
      ),
    ]);

    return NextResponse.json({
      window_days: days,
      totals: totals.rows[0],
      by_lane: byLane.rows,
      by_day: byDay.rows,
      note: "settled is money in hand; verified_local is verified but not yet on-chain-settled — never count them as the same number.",
    });
  } catch (err) {
    console.warn("revenue rollup failed", err);
    return NextResponse.json({ error: "query failed" }, { status: 500 });
  }
}
