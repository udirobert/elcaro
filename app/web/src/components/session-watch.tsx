"use client";

import { useSyncExternalStore } from "react";
import { motion } from "framer-motion";
import type { HistoryEntry } from "@/lib/history";
import { getHistory, clearHistory } from "@/lib/history";
import type { RiskLevel } from "@/lib/types";

// Session watch (docs/ux-audit.md, R10) — a calm-mode supervision view built
// from the same localStorage history as the scan page. The miner stays
// stateless, so this is a *session* watch: it sees what you scanned in this
// browser. For team-wide supervision, wire the middleware's logs to your own
// observability stack (the operator stores; Elcaro never does).

const RISK_DOT: Record<RiskLevel, string> = {
  safe: "bg-safe",
  low: "bg-low",
  suspicious: "bg-suspicious",
  dangerous: "bg-dangerous",
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

function subscribeNoop() {
  return () => {};
}
const EMPTY: HistoryEntry[] = [];
function getServerSnapshot() {
  return EMPTY;
}

export function SessionWatch() {
  const history = useSyncExternalStore(subscribeNoop, getHistory, getServerSnapshot);

  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-8 text-center">
        <p className="text-sm text-ink-muted leading-relaxed">
          No scans in this session yet. Run a scan on the{" "}
          <a href="/scan" className="text-violet font-semibold underline underline-offset-2 hover:text-violet/80">
            scan page
          </a>{" "}
          and the watch view will populate here.
        </p>
      </div>
    );
  }

  const quarantined = history.filter((h) => h.risk_score >= 0.5);
  const quarantineRate = quarantined.length / history.length;
  const techniques = new Map<string, number>();
  for (const h of history) {
    for (const t of h.response.flagged_techniques || []) {
      techniques.set(t, (techniques.get(t) || 0) + 1);
    }
  }
  const scores = history.map((h) => h.risk_score).sort((a, b) => a - b);
  const median = scores.length ? scores[Math.floor(scores.length / 2)] : 0;

  // Calm when safe, loud when not (principle 4): the panel's accent shifts
  // with the session's worst verdict.
  const hasQuarantine = quarantined.length > 0;

  return (
    <div className="space-y-6">
      {/* Stat band */}
      <div
        className={`rounded-xl border p-5 grid grid-cols-2 sm:grid-cols-4 gap-4 ${
          hasQuarantine
            ? "border-dangerous/20 bg-dangerous-bg/30"
            : "border-safe/20 bg-safe-bg/30"
        }`}
      >
        <Stat label="Scans" value={history.length} />
        <Stat label="Quarantined" value={quarantined.length} accent={hasQuarantine ? "dangerous" : undefined} />
        <Stat label="Quarantine rate" value={`${(quarantineRate * 100).toFixed(0)}%`} />
        <Stat label="Median score" value={median.toFixed(2)} />
      </div>

      {/* Technique breakdown */}
      {techniques.size > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest">
            Techniques detected this session
          </p>
          <div className="flex flex-wrap gap-2">
            {[...techniques.entries()]
              .sort((a, b) => b[1] - a[1])
              .map(([technique, count]) => (
                <span
                  key={technique}
                  className="text-xs font-mono px-2.5 py-1 rounded-full bg-canvas border border-border text-ink-muted"
                >
                  {technique} · {count}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Timeline — denser than scan-history, watch-shaped */}
      <div className="space-y-2">
        <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest">
          Session timeline
        </p>
        <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
          {history.map((entry) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, ease: EASE_OUT }}
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface transition-colors"
            >
              <div className={`w-2 h-2 rounded-full shrink-0 ${RISK_DOT[entry.risk_level]}`} />
              <span className="text-xs text-ink-muted truncate flex-1 font-mono">
                {entry.content.slice(0, 50)}
                {entry.content.length > 50 ? "..." : ""}
              </span>
              <span className="text-xs text-ink-faint font-mono shrink-0">
                {entry.risk_score.toFixed(2)}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* The stateless constraint, stated honestly */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-xs text-ink-faint leading-relaxed">
          This is a session watch — it reads your browser&apos;s localStorage, nothing
          is stored server-side. For team-wide supervision, have the Elcaro
          middleware log quarantined verdicts to your own observability stack;
          Elcaro itself stays stateless.
        </p>
      </div>

      <button
        onClick={clearHistory}
        className="text-xs text-ink-faint hover:text-dangerous transition-colors"
      >
        Clear session history
      </button>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: "dangerous";
}) {
  return (
    <div>
      <p className="text-[10px] font-medium text-ink-faint uppercase tracking-widest">{label}</p>
      <p
        className={`text-2xl font-black tracking-tight ${
          accent === "dangerous" ? "text-dangerous" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
