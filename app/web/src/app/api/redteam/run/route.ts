import { NextResponse } from "next/server";

const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

// Streams the miner's self-red-team run through as Server-Sent Events.
// The upstream body is piped straight through — each `data:` line is one
// journal record from the searcher (scan / trophy / run_end).
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const upstream = new URL(`${MINER_URL}/redteam/run`);
  const budget = url.searchParams.get("budget");
  const seed = url.searchParams.get("seed");
  if (budget) upstream.searchParams.set("budget", budget);
  if (seed) upstream.searchParams.set("seed", seed);

  let minerResponse: Response;
  try {
    minerResponse = await fetch(upstream, {
      headers: { Accept: "text/event-stream" },
    });
  } catch (err) {
    console.error("Elcaro miner unreachable:", err);
    return NextResponse.json(
      {
        error: "Scanner unavailable",
        detail: "The detection engine is currently unreachable. Please try again.",
      },
      { status: 503 }
    );
  }

  if (!minerResponse.ok || !minerResponse.body) {
    const detail = await minerResponse.text().catch(() => "");
    return NextResponse.json(
      { error: "Miner error", detail },
      { status: minerResponse.status || 502 }
    );
  }

  return new Response(minerResponse.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
