/**
 * x402 scan-lane usage attribution (WS3). The gateway writes usage_events
 * from Python; the paid scan lane (/api/x402/scan) lives here in TypeScript
 * and writes the same table directly. metering/neon.py is the schema source
 * of truth — the ALTERs below are the same idempotent statements so either
 * side can win the deploy race.
 *
 * Never throws: a metering outage degrades visibility, not paid traffic
 * (same posture as the Python sink).
 */

import { Pool } from "pg";

let pool: Pool | null | undefined;
let ddlPromise: Promise<void> | null = null;

function getPool(): Pool | null {
  if (pool !== undefined) return pool;
  const dsn = process.env.ELCARO_METERING_DSN || process.env.ELCARO_CANARY_DSN;
  pool = dsn ? new Pool({ connectionString: dsn, max: 2 }) : null;
  return pool;
}

async function ensureColumns(p: Pool): Promise<void> {
  ddlPromise ??= (async () => {
    for (const stmt of [
      "ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS event_id text",
      "ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS payer_address text",
      "ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS payment_network text",
      "ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS payment_tx_hash text",
      "ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS settlement_status text NOT NULL DEFAULT 'none'",
    ]) {
      await p.query(stmt);
    }
  })();
  await ddlPromise;
}

export interface ScanUsageRow {
  eventId: string;
  keyId: string;
  payer: string;
  network: string;
  amountAtomic: string;
  txHash: string | null;
  settlementStatus: "settled" | "failed" | "verified_local";
  riskLevel: string;
  latencyMsMiner: number;
  latencyMsTotal: number;
}

export async function insertScanUsage(row: ScanUsageRow): Promise<void> {
  try {
    const p = getPool();
    if (!p) return; // dev without a DSN — visibility degrades, scan unaffected
    await ensureColumns(p);
    await p.query(
      `INSERT INTO usage_events
         (key_id, ts, route, provider, upstream, parts_scanned, action, overall,
          latency_ms_elcaro, latency_ms_upstream, charge_usdc,
          event_id, payer_address, payment_network, payment_tx_hash, settlement_status)
       VALUES ($1, now(), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)`,
      [
        row.keyId,
        "/api/x402/scan",
        "scan",
        "miner",
        1,
        "none", // scan lane reports risk; no policy action is applied
        row.riskLevel,
        Math.max(0, Math.round((row.latencyMsTotal - row.latencyMsMiner) * 100) / 100),
        Math.round(row.latencyMsMiner * 100) / 100,
        Number(row.amountAtomic) / 1_000_000,
        row.eventId,
        row.payer,
        row.network,
        row.txHash,
        row.settlementStatus,
      ],
    );
  } catch (err) {
    console.warn("scan usage event dropped — metering outage, request unaffected", err);
  }
}
