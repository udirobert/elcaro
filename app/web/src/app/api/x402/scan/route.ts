import { NextRequest, NextResponse } from "next/server";
import { getAddress, recoverTypedDataAddress } from "viem";
import { privateKeyToAccount } from "viem/accounts";

/**
 * x402-paid scan — the PayBox marketplace lane for Elcaro.
 *
 * POST /api/x402/scan is the same verdict as /api/scan, but behind an HTTP
 * 402 payment challenge so an agent can pay per-request from a PayBox wallet
 * grant (`use_service` gateway mode, or `pay_x402` + retry).
 *
 * Protocol (x402 v2, "exact" scheme — the same envelope the Telegraph
 * devnode speaks, which engine-ask already answers as a payer):
 *
 *   1. Any request without a payment header → 402 + base64 challenge in
 *      `PAYMENT-REQUIRED` (and the same JSON in the body for v1 parsers).
 *      Two accepts are offered: Base mainnet USDC and Base Sepolia USDC —
 *      PayBox picks whichever rail the granted wallet supports.
 *   2. The client signs an EIP-3009 TransferWithAuthorization (EIP-712)
 *      and retries with `PAYMENT-SIGNATURE` (v2) or `X-PAYMENT` (v1).
 *   3. We recover the signer locally (recoverTypedDataAddress — no RPC,
 *      sub-ms), check the authorization against the offer WE issued
 *      (never the client-echoed `accepted` block), then proxy the scan.
 *
 * Settlement. With X402_FACILITATOR_URL set we hand the signed payload to a
 * facilitator (/verify then /settle) so the transfer lands on-chain.
 * Without one the authorization is verified cryptographically but not
 * settled — reported honestly as `payment.settlement: "verified_local"`.
 * For a $0.01-per-scan resource that is a deliberate trade-off: a signed
 * authorization IS the payment instrument; settlement can batch later.
 *
 * The free path (/scan on the miner, /api/scan here) is untouched — this
 * lane is additive, gated by the client choosing to pay.
 */

export const runtime = "nodejs"; // viem crypto needs Node, not edge

const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

// USDC EIP-3009 domains, keyed by x402 network id. `extra.name`/`version`
// are what the payer signs over — they must match the token's EIP-712
// domain exactly or recovered signers won't match `from`.
const NETWORKS: Record<
  string,
  { chainId: number; asset: `0x${string}`; extra: { name: string; version: string } }
> = {
  "eip155:8453": {
    chainId: 8453, // Base mainnet
    asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    extra: { name: "USD Coin", version: "2" },
  },
  "eip155:84532": {
    chainId: 84532, // Base Sepolia
    asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    extra: { name: "USDC", version: "2" },
  },
};

const DEFAULT_AMOUNT = "10000"; // $0.01, 6-decimal USDC — mirrors engine-ask
const MAX_TIMEOUT_SECONDS = 300;
const CLOCK_SKEW_S = 60;
const MINER_TIMEOUT_MS = 15_000;

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

interface Accept {
  scheme: "exact";
  network: string;
  asset: string;
  amount: string;
  payTo: string;
  maxTimeoutSeconds: number;
  extra: { name: string; version: string };
}

interface Authorization {
  from: string;
  to: string;
  value: string;
  validAfter: string;
  validBefore: string;
  nonce: string;
}

interface PaymentPayload {
  x402Version?: number;
  scheme?: string;
  network?: string;
  accepted?: Accept; // v2 echo — validated, never trusted for the domain
  payload?: { signature?: string; authorization?: Authorization };
}

/**
 * Where scan payments land. X402_PAYTO is the operator's receiving address.
 * Fallback derives the address from TELEGRAPH_X402_KEY (the bridge payer
 * wallet) so a demo deployment can pay itself end-to-end on Sepolia.
 */
let payToCache: `0x${string}` | null | undefined;
function payTo(): `0x${string}` | null {
  if (payToCache !== undefined) return payToCache;
  const explicit = process.env.X402_PAYTO?.trim();
  if (explicit) {
    try {
      payToCache = getAddress(explicit as `0x${string}`);
      return payToCache;
    } catch {
      payToCache = null;
      return null;
    }
  }
  const key = process.env.TELEGRAPH_X402_KEY?.trim();
  if (key) {
    try {
      payToCache = privateKeyToAccount(key as `0x${string}`).address;
      return payToCache;
    } catch {
      payToCache = null;
    }
  } else {
    payToCache = null;
  }
  return payToCache;
}

function offers(): Accept[] {
  const to = payTo();
  if (!to) return [];
  const amount = process.env.X402_SCAN_AMOUNT?.trim() || DEFAULT_AMOUNT;
  return Object.entries(NETWORKS).map(([network, n]) => ({
    scheme: "exact",
    network,
    asset: n.asset,
    amount,
    payTo: to,
    maxTimeoutSeconds: MAX_TIMEOUT_SECONDS,
    extra: n.extra,
  }));
}

function resourceBlock(req: NextRequest) {
  const url = new URL(req.url);
  return {
    url: `${url.origin}${url.pathname}`,
    description:
      "Elcaro indirect-prompt-injection scan — GO/STOP verdict with matched spans, " +
      "flagged techniques, quarantine notice, canary ref, signed proof.",
    mimeType: "application/json",
  };
}

/** The 402 challenge: header (v2) + body (v1 parsers read bodies). */
function challenge(req: NextRequest, error?: string): NextResponse {
  const body = {
    x402Version: 2,
    error: error ?? "payment required",
    resource: resourceBlock(req),
    accepts: offers(),
  };
  const headers = new Headers({ "cache-control": "no-store" });
  headers.set("content-type", "application/json");
  headers.set("payment-required", Buffer.from(JSON.stringify(body)).toString("base64"));
  return NextResponse.json(body, { status: 402, headers });
}

// ── Nonce replay guard (per-instance, like the engine-ask daily cap) ──────
const seenNonces = new Map<string, number>();
function nonceSeen(from: string, nonce: string): boolean {
  const now = Date.now();
  for (const [k, t] of seenNonces) if (now - t > 10 * 60_000) seenNonces.delete(k);
  const key = `${from.toLowerCase()}:${nonce.toLowerCase()}`;
  if (seenNonces.has(key)) return true;
  seenNonces.set(key, now);
  return false;
}

function decodePayment(req: NextRequest): PaymentPayload | null {
  const raw = req.headers.get("payment-signature") ?? req.headers.get("x-payment");
  if (!raw) return null;
  try {
    return JSON.parse(Buffer.from(raw, "base64").toString("utf8"));
  } catch {
    return null;
  }
}

/**
 * Verify the signed authorization against OUR offer. Returns the matched
 * offer on success, or a reason string on failure.
 */
async function verifyPayment(
  payment: PaymentPayload,
): Promise<{ accept: Accept; payer: `0x${string}` } | { reason: string }> {
  const sig = payment.payload?.signature;
  const auth = payment.payload?.authorization;
  if (!sig || !auth) return { reason: "malformed payment payload" };
  if (payment.scheme && payment.scheme !== "exact") return { reason: "unsupported scheme" };

  // v2 echoes `accepted`; v1 only carries network. Match to our offer.
  const want = payment.accepted?.network ?? payment.network;
  const accept = offers().find((a) => a.network === want);
  if (!accept) return { reason: "no matching payment option for network" };

  // The authorization must target the offer we issued.
  try {
    if (getAddress(auth.to as `0x${string}`) !== getAddress(accept.payTo as `0x${string}`))
      return { reason: "authorization pays a different recipient" };
  } catch {
    return { reason: "bad recipient address in authorization" };
  }
  if (BigInt(auth.value) < BigInt(accept.amount))
    return { reason: "authorization underpays the required amount" };

  const now = Math.floor(Date.now() / 1000);
  if (now < Number(auth.validAfter) - CLOCK_SKEW_S)
    return { reason: "authorization not yet valid" };
  if (now > Number(auth.validBefore))
    return { reason: "authorization expired" };

  if (nonceSeen(auth.from, auth.nonce))
    return { reason: "authorization nonce already spent" };

  // Recover the signer over the domain WE declared for this network.
  const net = NETWORKS[accept.network];
  let payer: `0x${string}`;
  try {
    payer = await recoverTypedDataAddress({
      domain: {
        name: net.extra.name,
        version: net.extra.version,
        chainId: net.chainId,
        verifyingContract: net.asset,
      },
      types: EIP3009_TYPES,
      primaryType: "TransferWithAuthorization",
      message: {
        from: auth.from as `0x${string}`,
        to: auth.to as `0x${string}`,
        value: BigInt(auth.value),
        validAfter: BigInt(auth.validAfter),
        validBefore: BigInt(auth.validBefore),
        nonce: auth.nonce as `0x${string}`,
      },
      signature: sig as `0x${string}`,
    });
  } catch {
    return { reason: "payment signature did not verify" };
  }
  if (getAddress(payer) !== getAddress(auth.from as `0x${string}`))
    return { reason: "payment signature does not match payer" };

  return { accept, payer };
}

/** Optional: hand the verified payload to a facilitator to settle on-chain. */
async function settleViaFacilitator(
  payment: PaymentPayload,
  accept: Accept,
): Promise<{ settled: boolean; txHash?: string; detail?: string }> {
  const base = process.env.X402_FACILITATOR_URL?.trim();
  if (!base) return { settled: false, detail: "verified_local" };
  const reqBody = { x402Version: 2, paymentPayload: payment, paymentRequirements: accept };
  try {
    const v = await fetch(`${base.replace(/\/+$/, "")}/verify`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(reqBody),
      signal: AbortSignal.timeout(10_000),
    });
    const vj = await v.json().catch(() => ({}));
    if (!v.ok || vj.isValid === false)
      return { settled: false, detail: `facilitator rejected: ${vj.invalidReason ?? v.status}` };
    const s = await fetch(`${base.replace(/\/+$/, "")}/settle`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(reqBody),
      signal: AbortSignal.timeout(20_000),
    });
    const sj = await s.json().catch(() => ({}));
    if (!s.ok || sj.success === false)
      return { settled: false, detail: "facilitator could not settle" };
    return { settled: true, txHash: sj.transaction ?? sj.txHash };
  } catch {
    return { settled: false, detail: "facilitator unreachable" };
  }
}

/**
 * GET is the unpaid probe path — PayBox's use_service hits the URL first to
 * read the 402, so an unauthenticated GET must ALWAYS answer 402, whatever
 * the Accept header says. Operator status lives behind ?status=1.
 */
export async function GET(req: NextRequest) {
  if (new URL(req.url).searchParams.get("status") === "1") {
    return NextResponse.json(
      {
        ok: true,
        service: "elcaro-x402-scan",
        paid: true,
        payToConfigured: Boolean(payTo()),
        payTo: payTo(),
        networks: Object.keys(NETWORKS),
        amountAtomic: process.env.X402_SCAN_AMOUNT?.trim() || DEFAULT_AMOUNT,
        facilitator: Boolean(process.env.X402_FACILITATOR_URL?.trim()),
      },
      { headers: { "cache-control": "no-store" } },
    );
  }
  const payment = decodePayment(req);
  if (!payment) return challenge(req);
  const verdict = await verifyPayment(payment);
  if ("reason" in verdict) return challenge(req, verdict.reason);
  return NextResponse.json(
    { error: "paid scan requires POST with a JSON body", code: "METHOD_REQUIRES_POST" },
    { status: 405 },
  );
}

export async function POST(req: NextRequest) {
  if (!payTo()) {
    return NextResponse.json(
      { error: "paid lane not configured", code: "PAYTO_NOT_CONFIGURED" },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }

  const payment = decodePayment(req);
  if (!payment) return challenge(req);

  // Validate the body BEFORE touching the payment — a malformed request
  // must not burn a paid authorization's nonce.
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "request body is not valid JSON", code: "INVALID_JSON" },
      { status: 400 },
    );
  }
  if (typeof body.content !== "string" || !body.content) {
    return NextResponse.json(
      { error: "body must include content: string", code: "BAD_REQUEST" },
      { status: 400 },
    );
  }

  const verdict = await verifyPayment(payment);
  if ("reason" in verdict) return challenge(req, verdict.reason);

  let minerResponse: Response;
  try {
    minerResponse = await fetch(`${MINER_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: body.content,
        content_type: body.content_type || "document",
        deep_analysis: body.deep_analysis || false,
        serv_enabled: body.serv_enabled || false,
      }),
      signal: AbortSignal.timeout(MINER_TIMEOUT_MS),
    });
  } catch (e) {
    const aborted = e instanceof Error && e.name === "TimeoutError";
    return NextResponse.json(
      {
        error: aborted ? "the scan engine did not answer in time" : "the scan engine is unreachable",
        code: aborted ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNREACHABLE",
      },
      { status: 504 },
    );
  }

  const scanJson = await minerResponse.json().catch(() => null);
  if (!minerResponse.ok || scanJson == null) {
    return NextResponse.json(
      { error: "miner error", code: "MINER_ERROR" },
      { status: minerResponse.status || 502 },
    );
  }

  // Verified before we serve — settle (best-effort) after, per x402's
  // verify→serve→settle order. A facilitator miss doesn't claw the verdict.
  const settlement = await settleViaFacilitator(payment, verdict.accept);

  const receipt = {
    success: true,
    network: verdict.accept.network,
    payer: verdict.payer,
    amount: verdict.accept.amount,
    asset: verdict.accept.asset,
    transaction: settlement.txHash ?? null,
    settlement: settlement.settled ? "onchain" : (settlement.detail ?? "verified_local"),
  };

  const headers = new Headers({ "cache-control": "no-store" });
  headers.set("payment-response", Buffer.from(JSON.stringify(receipt)).toString("base64"));

  return NextResponse.json({ ...scanJson, payment: receipt }, { headers });
}
