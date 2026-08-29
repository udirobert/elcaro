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

export function getHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
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
