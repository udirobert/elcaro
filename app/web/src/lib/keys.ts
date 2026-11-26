/**
 * Elcaro Gateway key management — mints, reads, and revokes keys in the
 * same Neon tables metering/neon.py owns (api_keys / usage_daily).
 *
 * THE SCHEMA BELOW IS A MIRROR — keep it in sync with metering/neon.py's
 * _DDL. The Python side is the source of truth; both create idempotently
 * so either side can land first.
 *
 * Key model (contract C2, §7.1): the raw key is shown to the caller once;
 * only sha256(raw) + a short display prefix persist. Possession of the raw
 * key is the auth for read/revoke — keys are bearer tokens.
 */

import { createHash, randomBytes, randomUUID } from "crypto";
import { Pool } from "pg";

const KEY_PREFIX_LEN = 12; // "elk_" + 8 chars — matches metering/neon.py

/**
 * Upstreams a gateway key may route to. Must stay in sync with the gateway's
 * allowlist (gateway/upstream.py) — a key pointing at an unknown upstream
 * fails closed at request time.
 */
export const KEY_UPSTREAMS = ["serv", "openai", "anthropic"] as const;
export type KeyUpstream = (typeof KEY_UPSTREAMS)[number];

export function isKeyUpstream(value: unknown): value is KeyUpstream {
  return (
    typeof value === "string" &&
    (KEY_UPSTREAMS as readonly string[]).includes(value)
  );
}

let pool: Pool | null | undefined;
let ddlPromise: Promise<void> | null = null;

function getPool(): Pool | null {
  if (pool !== undefined) return pool;
  // ELCARO_METERING_DSN wins; the canary DSN points at the same Neon
  // project and keeps key self-service working pre-gateway-deploy.
  const dsn = process.env.ELCARO_METERING_DSN || process.env.ELCARO_CANARY_DSN;
  pool = dsn ? new Pool({ connectionString: dsn, max: 2 }) : null;
  return pool;
}

export function meteringConfigured(): boolean {
  return getPool() !== null;
}

async function ensureTables(p: Pool): Promise<void> {
  ddlPromise ??= p.query(`
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
    )`).then(() => undefined);
  await ddlPromise;
}

export function hashKey(raw: string): string {
  return createHash("sha256").update(raw, "utf8").digest("hex");
}

export interface MintedKey {
  rawKey: string;
  keyId: string;
  prefix: string;
}

/** Mint an elk_* key with the contract-C2 default config. `upstream` is the
 * provider the key routes to (SERV by default) and must match the credential
 * the caller passes as the upstream key. Returns the raw key exactly once —
 * it is never stored. Null when the DB is down. */
export async function issueKey(
  label = "",
  upstream: KeyUpstream = "serv"
): Promise<MintedKey | null> {
  const p = getPool();
  if (!p) return null;
  try {
    await ensureTables(p);
    const raw = `elk_${randomBytes(24).toString("base64url")}`;
    const keyId = `elkid_${randomUUID().replaceAll("-", "").slice(0, 16)}`;
    await p.query(
      `INSERT INTO api_keys (key_id, key_hash, key_prefix, label, upstream)
       VALUES ($1, $2, $3, $4, $5)`,
      [keyId, hashKey(raw), raw.slice(0, KEY_PREFIX_LEN), label, upstream]
    );
    return { rawKey: raw, keyId, prefix: raw.slice(0, KEY_PREFIX_LEN) };
  } catch {
    return null;
  }
}

export interface KeyInfo {
  keyId: string;
  prefix: string;
  label: string;
  mode: string;
  upstream: string;
  deepAnalysis: boolean;
  createdAt: string;
  usage30d: {
    requests: number;
    partsScanned: number;
    chargeUsdc: string;
  } | null;
}

/** Raw key → its config + 30d rollup, or null for unknown/revoked keys.
 * Possession of the raw key is the only auth. */
export async function keyInfo(rawKey: string): Promise<KeyInfo | null> {
  const p = getPool();
  if (!p) return null;
  try {
    await ensureTables(p);
    const { rows } = await p.query(
      `SELECT key_id, key_prefix, label, mode, upstream, deep_analysis, created_at
       FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL`,
      [hashKey(rawKey)]
    );
    if (rows.length === 0) return null;
    const r = rows[0];
    let usage: KeyInfo["usage30d"] = null;
    try {
      const u = await p.query(
        `SELECT coalesce(sum(requests),0)::int AS requests,
                coalesce(sum(parts_scanned),0)::int AS parts,
                coalesce(sum(charge_usdc),0)::text AS charge
         FROM usage_daily
         WHERE key_id = $1 AND day >= current_date - 30`,
        [r.key_id]
      );
      usage = {
        requests: u.rows[0].requests,
        partsScanned: u.rows[0].parts,
        chargeUsdc: u.rows[0].charge,
      };
    } catch {
      // usage_daily may not exist before the gateway's first rollup —
      // usage reads as zero, not an error.
    }
    return {
      keyId: r.key_id,
      prefix: r.key_prefix,
      label: r.label,
      mode: r.mode,
      upstream: r.upstream,
      deepAnalysis: r.deep_analysis,
      createdAt: new Date(r.created_at).toISOString(),
      usage30d: usage,
    };
  } catch {
    return null;
  }
}

/** Revoke by raw key (owner proves possession). True when a live key died. */
export async function revokeKey(rawKey: string): Promise<boolean | null> {
  const p = getPool();
  if (!p) return null;
  try {
    await ensureTables(p);
    const res = await p.query(
      `UPDATE api_keys SET revoked_at = now()
       WHERE key_hash = $1 AND revoked_at IS NULL`,
      [hashKey(rawKey)]
    );
    return (res.rowCount ?? 0) > 0;
  } catch {
    return null;
  }
}
