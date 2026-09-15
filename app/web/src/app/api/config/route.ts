import { NextResponse } from "next/server";

const MINER_URL = process.env.MINER_URL ?? "http://127.0.0.1:8848";

export async function GET() {
  try {
    const res = await fetch(`${MINER_URL}/config`);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { serv_available: false, version: "unknown" },
      { status: 502 }
    );
  }
}
