import { createHmac, randomUUID } from "crypto";

const MAX_EVENTS_PER_FLUSH = 20;

const ALLOWED_EVENTS = new Set([
  // Original audit events
  "analysis.completed",
  "analysis.shared",
  "analysis.upgrade_click",
  // Conversion funnel
  "landing.viewed",
  "scan.viewed",
  "scan.started",
  "scan.verdict",
  "scan.error",
  "scan.shared",
  "scan.copied",
  "integrate.viewed",
  "keys.viewed",
  "key.minted",
]);

// Never accept fields that could carry user content or bearer material. The
// scan funnel needs metadata only; content itself must never become analytics.
const FORBIDDEN_PROP_KEYS = new Set([
  "content",
  "text",
  "prompt",
  "token",
  "key",
  "raw",
  "signature",
  "url",
  "email",
]);

interface AnalyticsEventInput {
  type?: unknown;
  _ts?: unknown;
  _session?: unknown;
  _page?: unknown;
  [key: string]: unknown;
}

function sessionHash(session: unknown): string | null {
  if (typeof session !== "string" || session.length < 8 || session.length > 128) return null;
  const salt = process.env.ELCARO_ANALYTICS_SALT || "elcaro-analytics-dev";
  return createHmac("sha256", salt).update(session).digest("hex");
}

function cleanPage(page: unknown): string {
  if (typeof page !== "string" || !page.startsWith("/") || page.length > 120) return "";
  // Strip query/fragment defensively — funnel analysis needs paths only.
  return page.split(/[?#]/, 1)[0];
}

function cleanProps(event: AnalyticsEventInput): Record<string, string | number | boolean | null> {
  const props: Record<string, string | number | boolean | null> = {};
  for (const [key, value] of Object.entries(event)) {
    if (key === "type" || key.startsWith("_") || FORBIDDEN_PROP_KEYS.has(key)) continue;
    if (!/^[a-z][a-z0-9_]{0,39}$/.test(key)) continue;
    if (typeof value === "string") {
      props[key] = value.slice(0, 160);
    } else if (typeof value === "number" && Number.isFinite(value)) {
      props[key] = value;
    } else if (typeof value === "boolean" || value === null) {
      props[key] = value;
    }
    if (Object.keys(props).length >= 30) break;
  }
  return props;
}

export function cleanEvents(raw: unknown) {
  if (!Array.isArray(raw)) return [];
  return raw.slice(0, MAX_EVENTS_PER_FLUSH).flatMap((item) => {
    const event = item as AnalyticsEventInput;
    if (typeof event?.type !== "string" || !ALLOWED_EVENTS.has(event.type)) return [];
    const ts = typeof event._ts === "number" && Number.isFinite(event._ts)
      ? new Date(event._ts)
      : null;
    if (ts && (Number.isNaN(ts.getTime()) || Math.abs(Date.now() - ts.getTime()) > 48 * 3600_000)) {
      return [];
    }
    return [{
      id: randomUUID(),
      clientTs: ts,
      event: event.type,
      sessionHash: sessionHash(event._session),
      page: cleanPage(event._page),
      props: cleanProps(event),
    }];
  });
}
