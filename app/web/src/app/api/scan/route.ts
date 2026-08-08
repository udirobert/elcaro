import { NextResponse } from "next/server";

const MINER_URL = process.env.ELCARO_MINER_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    const minerResponse = await fetch(`${MINER_URL}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: body.content,
        content_type: body.content_type || "document",
        deep_analysis: body.deep_analysis || false,
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
    // Fail open — return safe response if miner is unreachable
    console.error("Elcaro miner unreachable:", err);
    return NextResponse.json(
      {
        error: "Scanner unavailable",
        detail: "The detection engine is currently unreachable. Please try again.",
      },
      { status: 503 }
    );
  }
}
