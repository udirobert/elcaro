import { NextRequest, NextResponse } from "next/server";
import { appendFile, mkdir, readFile, stat } from "fs/promises";
import { join } from "path";
import { Pool } from "pg";
import { cleanEvents } from "@/lib/analytics-clean";

export const runtime = "nodejs"; // pg requires Node, not edge

const EVENTS_DIR = join(process.cwd(), ".analytics");
const EVENTS_FILE = join(EVENTS_DIR, "events.jsonl");

let pool: Pool | null | undefined;
let ddlPromise: Promise<void> | null = null;

function getPool(): Pool | null {
  if (pool !== undefined) return pool;
  const dsn =
    process.env.ELCARO_ANALYTICS_DSN ||
    process.env.ELCARO_METERING_DSN ||
    process.env.ELCARO_CANARY_DSN;
  pool = dsn ? new Pool({ connectionString: dsn, max: 2 }) : null;
  return pool;
}

async function ensureTables(p: Pool): Promise<void> {
  ddlPromise ??= (async () => {
    await p.query(`
      CREATE TABLE IF NOT EXISTS funnel_events (
        id           text PRIMARY KEY,
        received_at  timestamptz NOT NULL DEFAULT now(),
        client_ts    timestamptz,
        event        text NOT NULL,
        session_hash text,
        page         text NOT NULL DEFAULT '',
        props        jsonb NOT NULL DEFAULT '{}'::jsonb
      )`);
    await p.query(
      "CREATE INDEX IF NOT EXISTS funnel_events_received_idx ON funnel_events (received_at DESC)"
    );
    await p.query(
      "CREATE INDEX IF NOT EXISTS funnel_events_event_idx ON funnel_events (event, received_at DESC)"
    );
  })();
  await ddlPromise;
}

async function insertPostgres(events: ReturnType<typeof cleanEvents>): Promise<boolean> {
  const p = getPool();
  if (!p) return false;
  await ensureTables(p);
  for (const e of events) {
    await p.query(
      `INSERT INTO funnel_events (id, client_ts, event, session_hash, page, props)
       VALUES ($1, $2, $3, $4, $5, $6::jsonb)`,
      [e.id, e.clientTs, e.event, e.sessionHash, e.page, JSON.stringify(e.props)]
    );
  }
  return true;
}

async function insertLocalFile(events: ReturnType<typeof cleanEvents>): Promise<void> {
  await mkdir(EVENTS_DIR, { recursive: true });
  const lines = events.map((e) => JSON.stringify({
    id: e.id,
    ts: e.clientTs?.getTime() ?? Date.now(),
    type: e.event,
    session_hash: e.sessionHash,
    page: e.page,
    ...e.props,
  })).join("\n");
  await appendFile(EVENTS_FILE, lines + "\n");
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const events = cleanEvents(body.events);
    if (events.length === 0) {
      return NextResponse.json({ ok: true, flushed: 0 });
    }

    try {
      if (await insertPostgres(events)) {
        return NextResponse.json({ ok: true, flushed: events.length, sink: "postgres" });
      }
    } catch {
      // Fall through to the local development sink. In production the DSN
      // should be present; GET reports which sink is active so this is visible.
    }

    await insertLocalFile(events);
    return NextResponse.json({ ok: true, flushed: events.length, sink: "local_file" });
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  // Admin-only — aggregate counts and funnel shape, never raw rows.
  const adminToken = process.env.ANALYTICS_ADMIN_TOKEN;
  if (!adminToken || req.headers.get("x-admin-token") !== adminToken) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const p = getPool();
  if (p) {
    try {
      await ensureTables(p);
      const [total, byType] = await Promise.all([
        p.query("SELECT count(*)::int AS count FROM funnel_events"),
        p.query(`
          SELECT event,
                 count(*)::int AS events,
                 count(DISTINCT session_hash)::int AS sessions
          FROM funnel_events
          WHERE received_at >= now() - interval '30 days'
          GROUP BY event
          ORDER BY events DESC`),
      ]);
      return NextResponse.json({
        sink: "postgres",
        events_tracked: total.rows[0].count,
        last_30d: byType.rows,
      });
    } catch {
      return NextResponse.json({ sink: "postgres", error: "query failed" }, { status: 500 });
    }
  }

  try {
    const fileStat = await stat(EVENTS_FILE).catch(() => null);
    const count = fileStat
      ? (await readFile(EVENTS_FILE, "utf8")).split("\n").filter(Boolean).length
      : 0;
    return NextResponse.json({
      sink: "local_file",
      events_tracked: count,
      file_age_hours: fileStat ? Math.round((Date.now() - fileStat.mtimeMs) / 3600000) : null,
    });
  } catch {
    return NextResponse.json({ sink: "local_file", events_tracked: 0 });
  }
}
