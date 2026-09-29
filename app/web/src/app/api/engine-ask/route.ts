import { NextRequest, NextResponse } from "next/server";
import { privateKeyToAccount } from "viem/accounts";
import { toHex } from "viem";
import { randomBytes } from "crypto";

/**
 * Engine-ask bridge — the extension's path to COUNTED Telegraph traffic.
 *
 * POST /api/engine-ask  { "query": "<natural-language ask>" }
 *
 * Forwards to the auto-routed engine rail (POST /engine/v1/ask), which is the
 * only rail that counts as miner volume, and answers the x402 402 challenge
 * server-side so the extension needs no wallet:
 *
 *   1. POST upstream without payment → 402 + base64 challenge in the
 *      `payment-required` header.
 *   2. Take the `exact` eip155 option (Base Sepolia USDC) and sign an EIP-3009
 *      TransferWithAuthorization (EIP-712) for the exact amount. Gasless — the
 *      facilitator submits the transfer on-chain.
 *   3. Retry once with the signed payload base64-encoded in `PAYMENT-SIGNATURE`.
 *
 * Client shape follows telegraph-examples `src/lib/x402.ts` (x402 v2, "exact"
 * scheme). Verified against the live devnode challenge on 29 Sep 2026: the
 * signed envelope passes upstream validation ("payment required" = unfunded
 * wallet, vs "Invalid payment" for a malformed one).
 *
 * GET /api/engine-ask → operator status (payer configured? cap left? is the
 * extension origin pinned?). Read-only, leaks no secrets, `no-store`.
 *
 * Cost control. Every successful ask spends $0.01 of the payer wallet's USDC,
 * so this endpoint is gated by, in order:
 *   - origin allowlist (the web app, `mail.google.com`, and the extension's
 *     pinned `chrome-extension://<id>` — see `originAllowed`),
 *   - an optional shared token (TELEGRAPH_BRIDGE_TOKEN),
 *   - a per-instance daily ask cap (TELEGRAPH_BRIDGE_DAILY_CAP).
 * The in-memory counter is per-Lambda-instance on Netlify; treat it as a
 * backstop, not a hard ceiling.
 *
 * Every failure path returns `{ error, code }` with a stable `code`, because
 * the extension renders copy off the code (see app/extension/gmail-scan/
 * background.js) and we do not want infra strings leaking into the overlay.
 */

export const runtime = "nodejs"; // EIP-712 signing needs Node crypto

const ENGINE_ASK = "https://devnode.telegraphprotocol.com/engine/v1/ask";
const CHAIN_ID = 84532; // Base Sepolia, from the live challenge
const DEFAULT_ASSET = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"; // USDC
const DEFAULT_PAY_TO = "0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"; // Diamond
const DEFAULT_AMOUNT = "10000"; // $0.01 in 6-decimal USDC
const MAX_QUERY_CHARS = 120_000;
const UPSTREAM_TIMEOUT_MS = 30_000; // stays above the extension's 20s client timeout

const SITE_ORIGINS = new Set([
  "https://elcaro.trustfall.xyz",
  "https://www.elcaro.trustfall.xyz",
]);
const GMAIL_ORIGINS = new Set(["https://mail.google.com"]);
const EXTENSION_SCHEME = "chrome-extension://";

const EIP3009_TYPES = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
  ],
} as const;

// Per-instance daily spend backstop (see module docstring).
const dailyAsks = { day: "", count: 0 };

function capToday(): number {
  const raw = Number(process.env.TELEGRAPH_BRIDGE_DAILY_CAP ?? "40");
  return Number.isFinite(raw) && raw > 0 ? raw : 0;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Roll the in-memory counter over at UTC midnight, then return remaining. */
function asksRemaining(): number | null {
  const day = today();
  if (dailyAsks.day !== day) {
    dailyAsks.day = day;
    dailyAsks.count = 0;
  }
  const cap = capToday();
  return cap ? Math.max(0, cap - dailyAsks.count) : null;
}

/** The extension ids we trust, from TELEGRAPH_BRIDGE_EXTENSION_IDS. */
function pinnedExtensionIds(): string[] {
  return (process.env.TELEGRAPH_BRIDGE_EXTENSION_IDS ?? "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

function extensionIdOf(origin: string): string {
  return origin
    .slice(EXTENSION_SCHEME.length)
    .replace(/\/+$/, "")
    .toLowerCase();
}

/**
 * Origin policy.
 *
 * Extension origins carry a per-install id, so "any chrome-extension://" is a
 * standing invitation to anyone who can install *an* extension. When
 * TELEGRAPH_BRIDGE_EXTENSION_IDS names the published id(s), only those pass.
 * Unset means the unpacked-dev convenience (accept any id) still holds, but
 * GET /api/engine-ask reports `extensionPinned: false` so the gap is visible;
 * TELEGRAPH_BRIDGE_ALLOW_ANY_EXTENSION=0 hard-closes it without an id list.
 */
function originAllowed(origin: string): boolean {
  if (!origin) return process.env.TELEGRAPH_BRIDGE_ALLOW_NO_ORIGIN === "1";
  if (SITE_ORIGINS.has(origin) || GMAIL_ORIGINS.has(origin)) return true;
  if (!origin.startsWith(EXTENSION_SCHEME)) return false;
  const pinned = pinnedExtensionIds();
  if (pinned.length) return pinned.includes(extensionIdOf(origin));
  return process.env.TELEGRAPH_BRIDGE_ALLOW_ANY_EXTENSION !== "0";
}

/** Origin + token gate. Runs before the cap so a stranger can't burn it. */
function gateIdentity(req: NextRequest): NextResponse | null {
  const origin = req.headers.get("origin") ?? "";
  if (!originAllowed(origin)) {
    return fail(403, "FORBIDDEN_ORIGIN", "origin is not allowed to use this bridge");
  }
  const token = process.env.TELEGRAPH_BRIDGE_TOKEN;
  if (token && req.headers.get("x-bridge-token") !== token) {
    return fail(403, "FORBIDDEN_TOKEN", "missing or incorrect bridge token");
  }
  return null;
}

function fail(
  status: number,
  code: string,
  error: string,
  extra?: Record<string, unknown>,
): NextResponse {
  return NextResponse.json(
    { error, code, ...extra },
    { status, headers: { "cache-control": "no-store" } },
  );
}

interface Accept {
  scheme: string;
  network: string;
  asset?: string;
  amount?: string;
  payTo?: string;
  maxTimeoutSeconds?: number;
  extra?: { name?: string; version?: string };
}

async function relay(resp: Response): Promise<NextResponse> {
  const text = await resp.text();
  const headers = new Headers({ "cache-control": "no-store" });
  headers.set("content-type", resp.headers.get("content-type") ?? "application/json");
  for (const h of ["x-payment-settle-response", "payment-response"]) {
    const v = resp.headers.get(h);
    if (v) headers.set(h, v);
  }
  return new NextResponse(text, { status: resp.status, headers });
}

/** Operator status. No secrets: booleans and counters only. */
export async function GET(req: NextRequest) {
  const blocked = gateIdentity(req);
  if (blocked) return blocked;

  const remaining = asksRemaining();
  return NextResponse.json(
    {
      ok: true,
      service: "elcaro-telegraph-bridge",
      payerConfigured: Boolean(process.env.TELEGRAPH_X402_KEY),
      tokenRequired: Boolean(process.env.TELEGRAPH_BRIDGE_TOKEN),
      extensionPinned: pinnedExtensionIds().length > 0,
      dailyCap: capToday() || null,
      asksUsed: dailyAsks.count,
      asksRemaining: remaining,
      costPerAskUsd: 0.01,
      upstream: ENGINE_ASK,
    },
    { headers: { "cache-control": "no-store" } },
  );
}

export async function POST(req: NextRequest) {
  const blocked = gateIdentity(req);
  if (blocked) return blocked;

  if (asksRemaining() === 0) {
    return fail(429, "CAP_REACHED", "this bridge instance has used its daily ask cap");
  }

  let body: { query?: unknown };
  try {
    body = await req.json();
  } catch {
    return fail(400, "INVALID_JSON", "request body is not valid JSON");
  }
  const query = body.query;
  if (typeof query !== "string" || !query.trim()) {
    return fail(400, "BAD_REQUEST", "body must be { query: string }");
  }
  if (query.length > MAX_QUERY_CHARS) {
    return fail(413, "QUERY_TOO_LARGE", "query exceeds the bridge size limit");
  }

  const init: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
  };

  let resp: Response;
  try {
    resp = await fetch(ENGINE_ASK, init);
  } catch (e) {
    const aborted = e instanceof Error && e.name === "TimeoutError";
    return fail(
      504,
      aborted ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNREACHABLE",
      aborted
        ? "the Telegraph engine did not answer in time"
        : "the Telegraph engine could not be reached",
    );
  }

  if (resp.status !== 402) {
    return relay(resp); // routed straight through, or a non-402 failure
  }

  const key = process.env.TELEGRAPH_X402_KEY;
  if (!key) {
    return fail(
      502,
      "PAYER_NOT_CONFIGURED",
      "upstream requires payment and no payer wallet is configured",
    );
  }

  const challengeB64 = resp.headers.get("payment-required");
  let accepts: Accept[];
  try {
    const challenge = JSON.parse(
      Buffer.from(challengeB64 ?? "", "base64").toString("utf8"),
    );
    accepts = challenge.accepts ?? [];
  } catch {
    return fail(502, "CHALLENGE_UNREADABLE", "could not read the 402 challenge from upstream");
  }
  const accept = accepts.find(
    (a) => a.scheme === "exact" && a.network === `eip155:${CHAIN_ID}`,
  );
  if (!accept) {
    return fail(502, "NO_PAYMENT_OPTION", "the 402 challenge offered no supported payment option");
  }

  const account = privateKeyToAccount(key as `0x${string}`);
  const now = Math.floor(Date.now() / 1000);
  const authorization = {
    from: account.address,
    to: (accept.payTo ?? DEFAULT_PAY_TO) as `0x${string}`,
    value: BigInt(accept.amount ?? DEFAULT_AMOUNT),
    validAfter: BigInt(now - 30),
    validBefore: BigInt(now + Math.max(accept.maxTimeoutSeconds ?? 60, 300)),
    nonce: toHex(randomBytes(32)) as `0x${string}`,
  };

  const signature = await account.signTypedData({
    domain: {
      name: accept.extra?.name ?? "USDC",
      version: accept.extra?.version ?? "2",
      chainId: CHAIN_ID,
      verifyingContract: (accept.asset ?? DEFAULT_ASSET) as `0x${string}`,
    },
    types: EIP3009_TYPES,
    primaryType: "TransferWithAuthorization",
    message: {
      from: authorization.from,
      to: authorization.to,
      value: authorization.value,
      validAfter: authorization.validAfter,
      validBefore: authorization.validBefore,
      nonce: authorization.nonce,
    },
  });

  const payload = {
    x402Version: 2,
    scheme: "exact",
    network: accept.network,
    accepted: accept,
    payload: {
      signature,
      authorization: {
        from: authorization.from,
        to: authorization.to,
        value: authorization.value.toString(),
        validAfter: authorization.validAfter.toString(),
        validBefore: authorization.validBefore.toString(),
        nonce: authorization.nonce,
      },
    },
    extensions: {},
  };

  try {
    resp = await fetch(ENGINE_ASK, {
      ...init,
      headers: {
        ...(init.headers as Record<string, string>),
        "PAYMENT-SIGNATURE": Buffer.from(JSON.stringify(payload)).toString("base64"),
      },
    });
  } catch (e) {
    const aborted = e instanceof Error && e.name === "TimeoutError";
    return fail(
      504,
      aborted ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNREACHABLE",
      aborted
        ? "the Telegraph engine did not settle in time"
        : "the Telegraph engine could not be reached for settlement",
    );
  }

  // A second 402 means the envelope was well-formed but the payer could not
  // settle — almost always an unfunded/empty testnet wallet. Surface that as
  // one operator problem instead of shipping the challenge to the overlay.
  if (resp.status === 402) {
    const detail = (await resp.text().catch(() => "")).slice(0, 500);
    return fail(502, "PAYMENT_REJECTED", "the payer wallet could not settle the ask", {
      upstream: detail,
    });
  }

  // Only a settled ask spends money, so only a settled ask burns the cap.
  if (resp.ok) dailyAsks.count += 1;
  return relay(resp);
}
