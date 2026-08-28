"use client";

import { useState, useSyncExternalStore } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ScanResponse } from "@/lib/types";
import { RiskMeter } from "./risk-meter";
import { InlineHighlight } from "./inline-highlight";
import { IndicatorAnnotation } from "./indicator-annotation";
import { NextSteps } from "./next-steps";
import { getReviewerMode, recordExpandAll, setReviewerMode } from "@/lib/reviewer";

interface ScanResultProps {
  result: ScanResponse;
  content: string;
}

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Reviewer mode is client-only (localStorage). The server snapshot is always
// false so SSR and the first client render agree; the client re-syncs after
// hydration — same accepted pattern as the first-visit onboarding in ScanForm.
function subscribeNoop() {
  return () => {};
}
function getReviewerModeSnapshot(): boolean {
  return getReviewerMode();
}
function getReviewerModeServerSnapshot(): boolean {
  return false;
}

export function ScanResult({ result, content }: ScanResultProps) {
  const isSafe = result.risk_level === "safe";
  const hasFindings = result.indicators.length > 0;

  const reviewerMode = useSyncExternalStore(
    subscribeNoop,
    getReviewerModeSnapshot,
    getReviewerModeServerSnapshot
  );

  // Override holds the user's explicit expand/collapse actions. When null,
  // the default is reviewer-mode-driven (expanded for reviewers, collapsed
  // otherwise) — derived, not set-in-effect, so no hydration drift.
  const [override, setOverride] = useState<Set<number> | null>(null);
  const [showAnnouncement, setShowAnnouncement] = useState(false);
  const allIndexSet = new Set(result.indicators.map((_, i) => i));
  const expandedIds =
    override ?? (reviewerMode && hasFindings ? allIndexSet : new Set<number>());
  const allExpanded = hasFindings && expandedIds.size === result.indicators.length;

  function toggleExpanded(index: number) {
    setOverride((prev) => {
      const base = prev ?? expandedIds;
      const next = new Set(base);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function handleExpandAll() {
    const { firstTime } = recordExpandAll();
    if (firstTime) setShowAnnouncement(true);
    setOverride(allExpanded ? new Set<number>() : allIndexSet);
  }

  return (
    <div className="space-y-5">
      {/* Reviewer-mode announcement — shown once when the preference engages
          from repeated expand-all use. Adaptation, explained (principle 3). */}
      <AnimatePresence>
        {showAnnouncement && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="rounded-lg border border-violet/20 bg-violet/5 px-3 py-2 flex items-center justify-between gap-3 flex-wrap">
              <p className="text-xs text-ink-muted leading-relaxed">
                <span className="font-semibold text-ink">Reviewer mode on</span> — findings will
                default to expanded for you. Reverting clears the preference.
              </p>
              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => setShowAnnouncement(false)}
                  className="text-xs text-ink-faint hover:text-ink transition-colors"
                >
                  Got it
                </button>
                <button
                  onClick={() => {
                    setReviewerMode(false);
                    setShowAnnouncement(false);
                    setOverride(new Set<number>());
                  }}
                  className="text-xs font-semibold text-violet hover:text-violet/80 transition-colors"
                >
                  Revert
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Risk meter — score, level, verdict, and latency in one row */}
      <RiskMeter
        score={result.risk_score}
        level={result.risk_level}
        latencyMs={result.latency_ms}
      />

      {/* Summary — the one sentence explanation, skipped when there's
          nothing more specific to say than the risk level already shows */}
      {result.summary && !isSafe && (
        <motion.p
          className="text-sm text-ink-muted leading-relaxed"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.3, ease: EASE_OUT }}
        >
          {result.summary}
        </motion.p>
      )}

      {/* Evidence — only shown for the safe case, where "we checked and found
          nothing" is the useful signal. When there ARE findings, each one
          already carries its own evidence snippet on expand below, so
          repeating the full pasted content here would just duplicate the
          textarea the user is already looking at. */}
      {isSafe && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.35, ease: EASE_OUT }}
        >
          <InlineHighlight content={content} indicators={result.indicators} />
        </motion.div>
      )}

      {/* Findings — threat cards, collapsed by default; each expands to its
          own evidence, TTPs, and remediation */}
      {hasFindings && (
        <motion.div
          className="space-y-2"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.35, ease: EASE_OUT }}
        >
          <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest">
            Findings · {result.indicators.length}
          </p>
          <div
            className={`space-y-1 ${
              result.indicators.length > 4
                ? "max-h-80 overflow-y-auto pr-1"
                : ""
            }`}
          >
            {result.indicators.map((indicator, i) => (
              <IndicatorAnnotation
                key={`${indicator.technique_name}-${i}`}
                indicator={indicator}
                index={i}
                expanded={expandedIds.has(i)}
                onToggle={() => toggleExpanded(i)}
              />
            ))}
          </div>
          {/* Expand-all — for the reviewer with eight indicators. Repeated use
              engages reviewer mode (findings default to expanded). */}
          {result.indicators.length > 1 && (
            <button
              onClick={handleExpandAll}
              className="text-xs text-ink-faint hover:text-ink transition-colors"
            >
              {allExpanded ? "Collapse all" : "Expand all"}
            </button>
          )}
        </motion.div>
      )}

      {/* What to do about it — the remedy, the decision, and the path to
          automated protection. Answers "so what?" instead of stopping at
          the alarm. */}
      <NextSteps result={result} content={content} />
    </div>
  );
}
