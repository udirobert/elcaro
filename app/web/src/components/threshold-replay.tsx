"use client";

import Link from "next/link";
import { getHistory, QUARANTINE_THRESHOLD } from "@/lib/history";

// Threshold replay (docs/ux-audit.md, R7) — turns the "0.5 blocks / 0.3 flags"
// doctrine into something the user can *feel*, by re-scoring their own session
// history at candidate thresholds. The score never changes; only whether the
// quarantine decision flips. Pure client-side — reads localStorage, nothing
// leaves the browser.

const FLAG_AT = 0.3;
const NEVER_PASS_AT = 0.7;

export function ThresholdReplay() {
  const history = getHistory();
  // Not enough local signal to replay yet — teach the doctrine instead of
  // vanishing (this card now sits high on /integrate, not at the bottom).
  if (history.length < 3) {
    return (
      <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
        <p className="text-sm font-semibold text-ink">Replay the threshold on your scans</p>
        <p className="text-xs text-ink-muted leading-relaxed">
          Run a few scans and this card replays your own session history at
          candidate thresholds — you see exactly what a{" "}
          <span className="font-mono text-ink">{FLAG_AT.toFixed(1)}</span> flag
          vs a <span className="font-mono text-ink">{QUARANTINE_THRESHOLD.toFixed(1)}</span>{" "}
          block would have changed. The score never moves; only the quarantine
          decision does. Nothing is stored server-side.
        </p>
        <Link
          href="/scan"
          className="inline-flex items-center gap-1 text-xs font-semibold text-violet underline underline-offset-2 hover:text-violet/80 transition-colors"
        >
          Open the scan playground →
        </Link>
      </div>
    );
  }

  // At FLAG_AT, how many currently-passing scans (score in [0.3, 0.5)) would
  // flip to quarantined?
  const newlyFlagged = history.filter(
    (h) => h.risk_score >= FLAG_AT && h.risk_score < QUARANTINE_THRESHOLD
  ).length;

  // At NEVER_PASS_AT, how many currently-quarantined scans (score in [0.5, 0.7))
  // would pass instead?
  const wouldSlipThrough = history.filter(
    (h) => h.risk_score >= QUARANTINE_THRESHOLD && h.risk_score < NEVER_PASS_AT
  ).length;

  return (
    <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
      <p className="text-sm font-semibold text-ink">Replay the threshold on your scans</p>
      <p className="text-xs text-ink-muted leading-relaxed">
        From your last {history.length} scan{history.length === 1 ? "" : "s"} (this browser only):
      </p>
      <ul className="space-y-1 text-xs text-ink-muted leading-relaxed">
        <li>
          <span className="font-mono text-ink">{FLAG_AT.toFixed(1)}</span> block threshold →{" "}
          <span className="text-suspicious font-semibold">{newlyFlagged}</span> more would be
          quarantined (currently passing, score {FLAG_AT.toFixed(1)}–{QUARANTINE_THRESHOLD.toFixed(1)}).
        </li>
        <li>
          <span className="font-mono text-ink">{NEVER_PASS_AT.toFixed(1)}</span> block threshold →{" "}
          <span className="text-dangerous font-semibold">{wouldSlipThrough}</span> currently
          quarantined scan{wouldSlipThrough === 1 ? "" : "s"} would pass instead (score{" "}
          {QUARANTINE_THRESHOLD.toFixed(1)}–{NEVER_PASS_AT.toFixed(1)}).
        </li>
      </ul>
      <p className="text-[11px] text-ink-faint leading-relaxed pt-1">
        The risk score is fixed — only the quarantine decision moves. Nothing is
        stored server-side; this replays your local history.
      </p>
    </div>
  );
}
