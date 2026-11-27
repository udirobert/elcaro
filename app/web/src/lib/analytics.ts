/**
 * Client-side analytics for the prompt audit (/evaluate/audit,
 * formerly /vulnerable).
 *
 * Tracks three events:
 *   - analysis.completed: user finished a scan (quick or sandbox)
 *   - analysis.shared: user clicked the share button
 *   - analysis.upgrade_click: user clicked "Scan your own content" or
 *     "Integrate Elcaro" after seeing results (conversion signal)
 *
 * Events are stored in localStorage and flushed to the server endpoint
 * /api/analytics on page unload or when the buffer fills (5 events).
 * Uses no third-party libraries — pure localStorage + fetch.
 */

export type FunnelEventType =
  | "landing.viewed"
  | "scan.viewed"
  | "scan.started"
  | "scan.verdict"
  | "scan.error"
  | "scan.shared"
  | "scan.copied"
  | "integrate.viewed"
  | "keys.viewed"
  | "key.minted";

type FunnelEvent = {
  type: FunnelEventType;
  [key: string]: string | number | boolean | null | undefined;
};

export type AnalyticsEvent =
  | { type: "analysis.completed"; mode: "quick" | "sandbox"; score: number; serv_available: boolean }
  | { type: "analysis.shared"; score: number; mode: "quick" | "sandbox" }
  | { type: "analysis.upgrade_click"; from_score: number; destination: "/scan" | "/integrate" | "/evaluate" }
  | FunnelEvent;

type StoredEvent = AnalyticsEvent & { _ts: number; _session?: string; _page?: string };

const STORAGE_KEY = "elcaro_analytics_v1";
const FLUSH_THRESHOLD = 5;
const EVENT_TTL_MS = 24 * 60 * 60 * 1000; // 24h

function getBuffer(): StoredEvent[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as StoredEvent[];
  } catch {
    return [];
  }
}

function setBuffer(events: StoredEvent[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  } catch {
    // localStorage full — clear buffer silently
    localStorage.removeItem(STORAGE_KEY);
  }
}

function prune(buffer: StoredEvent[]): StoredEvent[] {
  const now = Date.now();
  return buffer.filter((e) => now - e._ts < EVENT_TTL_MS);
}

let _flushTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleFlush(): void {
  if (_flushTimer) clearTimeout(_flushTimer);
  _flushTimer = setTimeout(() => flushBuffer(), 2000);
}

export async function flushBuffer(): Promise<void> {
  const buffer = prune(getBuffer());
  if (buffer.length === 0) return;

  setBuffer([]); // optimistic clear

  try {
    // Page-hide/unload flushes cannot rely on a fetch completing. sendBeacon
    // is purpose-built for that path; normal interactive flushes still use
    // fetch so non-2xx responses can restore the buffer.
    if (typeof navigator !== "undefined" && document.visibilityState === "hidden") {
      const beaconBody = new Blob([JSON.stringify({ events: buffer })], {
        type: "application/json",
      });
      if (navigator.sendBeacon("/api/analytics", beaconBody)) return;
    }
    const response = await fetch("/api/analytics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events: buffer }),
    });
    // Restore on failure by merging, not overwriting: events tracked while
    // this fetch was in flight sit in the live buffer, and a plain restore
    // would silently discard them.
    if (!response.ok) setBuffer([...buffer, ...getBuffer()]);
  } catch {
    // Server unreachable — keep events in buffer for next flush
    setBuffer([...buffer, ...getBuffer()]);
  }
}

const SESSION_STORAGE_KEY = "elcaro_analytics_session_v1";

/** Daily rotating pseudonymous session id. It is random client-side state,
 * not an account identifier; the server stores only its HMAC. */
function getSessionId(): string {
  try {
    const today = new Date().toISOString().slice(0, 10);
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as { day?: string; id?: string };
      if (parsed.day === today && typeof parsed.id === "string") return parsed.id;
    }
    const id = typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ day: today, id }));
    return id;
  } catch {
    return "unavailable";
  }
}

function track(event: AnalyticsEvent): void {
  const buffer = prune(getBuffer());
  // Attach timestamp/session/page internally (not part of the public type).
  // The server strips IP/UA entirely and stores only HMAC(session id).
  const enriched: StoredEvent = {
    ...event,
    _ts: Date.now(),
    _session: getSessionId(),
    _page: window.location.pathname,
  };
  buffer.push(enriched);
  setBuffer(buffer);

  if (buffer.length >= FLUSH_THRESHOLD) {
    void flushBuffer();
  } else {
    scheduleFlush();
  }
}

// Public API

export function trackAnalysisComplete(
  mode: "quick" | "sandbox",
  score: number,
  servAvailable: boolean,
): void {
  track({ type: "analysis.completed", mode, score, serv_available: servAvailable });
}

export function trackAnalysisShare(score: number, mode: "quick" | "sandbox"): void {
  track({ type: "analysis.shared", score, mode });
}

export function trackFunnel(
  type: FunnelEventType,
  props: Record<string, string | number | boolean | null | undefined> = {},
): void {
  track({ type, ...props } as FunnelEvent);
}

export function trackUpgradeClick(destination: "/scan" | "/integrate" | "/evaluate"): void {
  // Use sessionStorage to get the last seen score (set by the component)
  const lastScoreStr = sessionStorage.getItem("elcaro_last_score");
  const fromScore = lastScoreStr ? parseInt(lastScoreStr, 10) : 0;
  track({ type: "analysis.upgrade_click", from_score: fromScore, destination });
}

export function setLastScore(score: number): void {
  sessionStorage.setItem("elcaro_last_score", String(score));
}

// Flush on page hide/unload
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") void flushBuffer();
  });
  window.addEventListener("beforeunload", () => void flushBuffer());
}
