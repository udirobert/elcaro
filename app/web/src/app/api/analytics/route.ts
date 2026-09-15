import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { appendFile, mkdir, readFile, stat } from "fs/promises";
import { join } from "path";

const EVENTS_DIR = join(process.cwd(), ".analytics");
const EVENTS_FILE = join(EVENTS_DIR, "events.jsonl");

interface AnalyticsEvent {
  type: string;
  _ts?: number;
  [key: string]: unknown;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const events: AnalyticsEvent[] = Array.isArray(body.events) ? body.events : [];

    if (events.length === 0) {
      return NextResponse.json({ ok: true, flushed: 0 });
    }

    await mkdir(EVENTS_DIR, { recursive: true });

    const lines = events.map((e) => {
      const { _ts, ...rest } = e;
      return JSON.stringify({
        id: randomUUID(),
        ts: _ts ?? Date.now(),
        ...rest,
        ua: req.headers.get("user-agent")?.slice(0, 200) ?? "",
        ip: (req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip") ?? "").split(",")[0].trim(),
      });
    }).join("\n");

    await appendFile(EVENTS_FILE, lines + "\n");

    return NextResponse.json({ ok: true, flushed: events.length });
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  // Admin-only — returns event count (no PII)
  const adminToken = process.env.ANALYTICS_ADMIN_TOKEN;
  if (!adminToken || req.headers.get("x-admin-token") !== adminToken) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  try {
    const fileStat = await stat(EVENTS_FILE).catch(() => null);
    const count = fileStat
      ? (await readFile(EVENTS_FILE, "utf8")).split("\n").filter(Boolean).length
      : 0;
    return NextResponse.json({
      events_tracked: count,
      file_age_hours: fileStat ? Math.round((Date.now() - fileStat.mtimeMs) / 3600000) : null,
    });
  } catch {
    return NextResponse.json({ events_tracked: 0 });
  }
}
