/**
 * Canary minting for the web tier — writes to the same canary_events table
 * the miner reads (ELCARO_CANARY_DSN, Neon). Specimen fetches stamp a
 * per-serve token so a verbatim relay of the specimen text inside a later
 * /scan resolves to this exact serving event via GET /canary/{token}.
 *
 * Same contract as core/canary.py: never store content (hash + metadata
 * only); fail soft — a DB outage yields an unstamped response, never a
 * failed page.
 */

import { createHash, randomBytes } from "crypto";
import { Pool } from "pg";

let pool: Pool | null | undefined;

function getPool(): Pool | null {
  if (pool !== undefined) return pool;
  const dsn = process.env.ELCARO_CANARY_DSN;
  pool = dsn ? new Pool({ connectionString: dsn, max: 2 }) : null;
  return pool;
}

export function contentSha256(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

/** Mint an elc-<unix-hex>-<rand> token into canary_events. Null when the
 * DSN is unset (canaries disabled) or the insert fails. */
export async function mintCanary(
  kind: string,
  payload: Record<string, unknown>
): Promise<string | null> {
  const p = getPool();
  if (!p) return null;
  const now = Math.floor(Date.now() / 1000);
  const token = `elc-${now.toString(16)}-${randomBytes(3).toString("hex")}`;
  try {
    await p.query(
      "INSERT INTO canary_events (token, kind, issued_at, payload) " +
        "VALUES ($1, $2, $3, $4::jsonb) ON CONFLICT (token) DO NOTHING",
      [token, kind, now, JSON.stringify(payload)]
    );
    return token;
  } catch {
    return null;
  }
}
