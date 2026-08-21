import { NextResponse } from "next/server";

// Proxy for the miner's public /metrics — aggregate stats only, no PII.
// Keeps the miner URL server-side (same pattern as /api/scan).
const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

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

    return NextResponse.json(await minerResponse.json());
  } catch {
    // The proof strip hides itself on failure — no need to be loud.
    return NextResponse.json(
      { error: "Metrics unavailable" },
      { status: 503 }
    );
  }
}
