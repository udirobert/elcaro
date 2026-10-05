import { NextResponse } from "next/server";

// Proxy for the miner's public canary resolver — same pattern as /api/metrics.
// Keeps the miner URL server-side; the resolver itself returns only
// issuance metadata (hash, score, techniques — never scanned content).
const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  try {
    const minerResponse = await fetch(`${MINER_URL}/canary/${token}`, {
      cache: "no-store",
    });
    const body = await minerResponse.json().catch(() => null);
    if (!minerResponse.ok) {
      return NextResponse.json(
        body ?? { error: "Canary resolution unavailable" },
        { status: minerResponse.status }
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json(
      { error: "Canary resolution unavailable" },
      { status: 503 }
    );
  }
}
