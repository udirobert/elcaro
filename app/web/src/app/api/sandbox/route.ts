import { NextRequest, NextResponse } from "next/server";

const MINER_URL = process.env.MINER_URL ?? "http://127.0.0.1:8848";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${MINER_URL}/sandbox`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: "Miner unreachable", detail: "Could not reach the sandbox endpoint" },
      { status: 502 }
    );
  }
}
