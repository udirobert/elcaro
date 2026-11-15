import { NextResponse } from "next/server";

// Proxy for the miner's public /metrics — aggregate stats only, no PII.
// Keeps the miner URL server-side (same pattern as /api/scan).
const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

// x402 paid-lane state, merged into the metrics payload. Without a
// facilitator the lane still cryptographically verifies each payment but
// nothing settles on-chain — that is a DEGRADED mode and must not read as
// settled success on any public metrics surface. Mirrored from
// /api/x402/scan's payTo()/settleViaFacilitator() config reads.
function x402State() {
  const facilitator = Boolean(process.env.X402_FACILITATOR_URL?.trim());
  const payTo = Boolean(
    process.env.X402_PAYTO?.trim() || process.env.TELEGRAPH_X402_KEY?.trim()
  );
  return {
    paid_lane: payTo ? ("enabled" as const) : ("disabled" as const),
    settlement: facilitator
      ? ("onchain" as const)
      : ("degraded_local_verify" as const),
    facilitator_configured: facilitator,
  };
}

export async function GET() {
  try {
    const minerResponse = await fetch(`${MINER_URL}/metrics`, {
      cache: "no-store",
    });

    if (!minerResponse.ok) {
      return NextResponse.json(
        { error: "Metrics unavailable" },
        { status: 503 }
      );
    }

    return NextResponse.json({
      ...(await minerResponse.json()),
      x402: x402State(),
    });
  } catch {
    // The proof strip hides itself on failure — no need to be loud.
    return NextResponse.json(
      { error: "Metrics unavailable" },
      { status: 503 }
    );
  }
}
