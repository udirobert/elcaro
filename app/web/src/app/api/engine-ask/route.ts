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
 * Cost control: every successful ask spends $0.01 of the payer wallet's USDC,
 * so this endpoint is gated by
 *   - an origin allowlist (the extension and this site),
 *   - an optional shared token (TELEGRAPH_BRIDGE_TOKEN),
 *   - a per-instance daily ask cap (TELEGRAPH_BRIDGE_DAILY_CAP).
 * The in-memory counter is per-Lambda-instance on Netlify; treat it as a
 * backstop, not a hard ceiling.
 */

export const runtime = "nodejs"; // EIP-712 signing needs Node crypto

const ENGINE_ASK = "https://devnode.telegraphprotocol.com/engine/v1/ask";
const CHAIN_ID = 84532; // Base Sepolia, from the live challenge
const DEFAULT_ASSET = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"; // USDC
const DEFAULT_PAY_TO = "0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"; // Diamond
const DEFAULT_AMOUNT = "10000"; // $0.01 in 6-decimal USDC
const MAX_QUERY_CHARS = 120_000;

const ALLOWED_ORIGINS = new Set([
  "https://elcaro.trustfall.xyz",
  "https://mail.google.com",
  "chrome-extension://", // prefix match for the unpacked extension
]);

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

function gate(req: NextRequest): NextResponse | null {
  const cap = Number(process.env.TELEGRAPH_BRIDGE_DAILY_CAP ?? "40");
  const today = new Date().toISOString().slice(0, 10);
  if (dailyAsks.day !== today) {
    dailyAsks.day = today;
    dailyAsks.count = 0;
  }
  if (Number.isFinite(cap) && cap > 0 && dailyAsks.count >= cap) {
    return NextResponse.json(
      { error: "bridge daily ask cap reached", code: "CAP_REACHED" },
      { status: 429 },
    );
  }

  const token = process.env.TELEGRAPH_BRIDGE_TOKEN;
  if (token && req.headers.get("x-bridge-token") !== token) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }

  const origin = req.headers.get("origin") ?? "";
  if (origin) {
    const ok =
      ALLOWED_ORIGINS.has(origin) ||
      origin.startsWith("chrome-extension://");
    if (!ok) return NextResponse.json({ error: "forbidden origin" }, { status: 403 });
  }
  return null;
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
  const headers = new Headers();
  headers.set("content-type", resp.headers.get("content-type") ?? "application/json");
  for (const h of ["x-payment-settle-response", "payment-response"]) {
    const v = resp.headers.get(h);
    if (v) headers.set(h, v);
  }
  return new NextResponse(text, { status: resp.status, headers });
}

export async function POST(req: NextRequest) {
  const blocked = gate(req);
  if (blocked) return blocked;

  let body: { query?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }
  const query = body.query;
  if (typeof query !== "string" || !query.trim()) {
    return NextResponse.json(
      { error: "body must be { query: string }" },
      { status: 400 },
    );
  }
  if (query.length > MAX_QUERY_CHARS) {
    return NextResponse.json({ error: "query too large" }, { status: 413 });
  }

  const init: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  };

  let resp = await fetch(ENGINE_ASK, init);
  if (resp.status !== 402) {
    return relay(resp); // routed straight through, or a non-402 failure
  }

  const key = process.env.TELEGRAPH_X402_KEY;
  if (!key) {
    return NextResponse.json(
      {
        error:
          "upstream requires payment and no payer wallet is configured (TELEGRAPH_X402_KEY)",
        code: "PAYER_NOT_CONFIGURED",
      },
      { status: 502 },
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
    return NextResponse.json(
      { error: "unreadable 402 challenge from upstream" },
      { status: 502 },
    );
  }
  const accept = accepts.find(
    (a) => a.scheme === "exact" && a.network === `eip155:${CHAIN_ID}`,
  );
  if (!accept) {
    return NextResponse.json(
      { error: "no eip155 exact payment option in the 402 challenge" },
      { status: 502 },
    );
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

  resp = await fetch(ENGINE_ASK, {
    ...init,
    headers: {
      ...(init.headers as Record<string, string>),
      "PAYMENT-SIGNATURE": Buffer.from(JSON.stringify(payload)).toString("base64"),
    },
  });

  if (resp.ok) dailyAsks.count += 1;
  return relay(resp);
}
