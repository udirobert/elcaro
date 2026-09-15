import { NextResponse } from "next/server";

const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Forward ?serv=1 (or =0) as a query param to the miner. Body's
    // serv_enabled wins if the caller didn't pass ?serv, so the UI
    // checkbox stays the canonical toggle.
    const url = new URL(request.url);
    const servQuery = url.searchParams.get("serv");
    const servFromQuery =
      servQuery === "1" || servQuery === "true" ? true
        : servQuery === "0" || servQuery === "false" ? false
          : undefined;

    const minerResponse = await fetch(`${MINER_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: body.content,
        content_type: body.content_type || "document",
        deep_analysis: body.deep_analysis || false,
        serv_enabled:
          servFromQuery !== undefined ? servFromQuery : (body.serv_enabled || false),
      }),
    });

    if (!minerResponse.ok) {
      const errorText = await minerResponse.text();
      return NextResponse.json(
        { error: "Miner error", detail: errorText },
        { status: minerResponse.status }
      );
    }

    const data = await minerResponse.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Elcaro miner unreachable:", err);
    return NextResponse.json(
      {
        error: "Scanner unavailable",
        detail:
          "The detection engine is currently unreachable. Please try again.",
      },
      { status: 503 }
    );
  }
}
