import type { ContentType, RiskLevel, ScanResponse } from "./types";

export interface HistoryEntry {
  id: string;
  timestamp: number;
  content: string;
  content_type: ContentType;
  risk_score: number;
  risk_level: RiskLevel;
  summary: string;
  response: ScanResponse;
}

export const STORAGE_KEY = "elcaro_scan_history";
const MAX_ENTRIES = 50;

// The quarantine doctrine (docs/ux-audit.md): a verdict at or above this score
// is quarantined. Shared so every surface computes "quarantined" identically.
// COUPLED CONSTANT: core/quarantine.py (DEFAULT_RISK_THRESHOLD) must stay in
// sync — the server computes the actual quarantine decision from that line.
export const QUARANTINE_THRESHOLD = 0.5;

// Cached by raw string so repeated calls (e.g. useSyncExternalStore's
// getSnapshot, which must return a stable reference when nothing changed)
// don't re-parse and hand back a new array/object graph every call — that
// makes React treat the store as perpetually changing and throw an
// infinite-loop error.
let cachedRaw: string | null = null;
let cachedHistory: HistoryEntry[] = [];

export function getHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === cachedRaw) return cachedHistory;
  cachedRaw = raw;
  try {
    cachedHistory = raw ? JSON.parse(raw) : [];
  } catch {
    cachedHistory = [];
  }
  return cachedHistory;
}

export function addToHistory(
  content: string,
  content_type: ContentType,
  response: ScanResponse
): HistoryEntry {
  const entry: HistoryEntry = {
    id: crypto.randomUUID(),
    timestamp: Date.now(),
    content,
    content_type,
    risk_score: response.risk_score,
    risk_level: response.risk_level,
    summary: response.summary,
    response,
  };

  const history = getHistory();
  history.unshift(entry);

  // Keep only the most recent entries
  const trimmed = history.slice(0, MAX_ENTRIES);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // localStorage full — evict oldest half
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(trimmed.slice(0, MAX_ENTRIES / 2))
    );
  }

  return entry;
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

// Count how many of the last N scans were SERV-refined. Used by the
// session-level SERV badge so users see their investment accumulating.
export function countServRefined(lastN: number = 10): number {
  if (typeof window === "undefined") return 0;
  const history = getHistory();
  return history.slice(0, lastN).filter((e) => e.response.serv_used).length;
}
