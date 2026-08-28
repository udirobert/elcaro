// Reviewer mode — persists the disclosure preference of a returning reviewer.
//
// The UI listens to what the user does: clicking "Expand all" repeatedly is a
// signal that the collapsed default wastes their time. After a threshold of
// expand-all clicks, reviewer mode engages and findings default to expanded —
// with a one-tap revert, because adaptation that can't be undone is a trap
// (docs/ux-audit.md, principle 3: adapt openly).

const MODE_KEY = "elcaro_reviewer_mode";
const COUNT_KEY = "elcaro_expand_all_count";
const ANNOUNCED_KEY = "elcaro_reviewer_announced";
const TRIGGER_COUNT = 2;

function readBool(key: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(key) === "true";
  } catch {
    return false;
  }
}

function writeBool(key: string, value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, value ? "true" : "false");
  } catch {
    // localStorage unavailable — non-critical, the preference just won't persist
  }
}

export function getReviewerMode(): boolean {
  return readBool(MODE_KEY);
}

export function setReviewerMode(enabled: boolean): void {
  writeBool(MODE_KEY, enabled);
  if (!enabled) writeCount(0);
}

/**
 * Record an expand-all click. Returns whether reviewer mode just engaged
 * (so the caller can announce it once) — the first time the count crosses
 * the trigger.
 */
export function recordExpandAll(): { enabled: boolean; firstTime: boolean } {
  const already = getReviewerMode();
  const count = readCount() + 1;
  writeCount(count);
  if (!already && count >= TRIGGER_COUNT) {
    writeBool(MODE_KEY, true);
    return { enabled: true, firstTime: true };
  }
  return { enabled: already, firstTime: false };
}

export function isReviewerAnnouncementAcknowledged(): boolean {
  return readBool(ANNOUNCED_KEY);
}

export function acknowledgeReviewerAnnouncement(): void {
  writeBool(ANNOUNCED_KEY, true);
}

function readCount(): number {
  if (typeof window === "undefined") return 0;
  try {
    return Number(localStorage.getItem(COUNT_KEY) || 0);
  } catch {
    return 0;
  }
}

function writeCount(n: number): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(COUNT_KEY, String(n));
  } catch {
    // non-critical
  }
}
