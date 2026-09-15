"use client";

import { useState, useSyncExternalStore } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ScanResponse } from "@/lib/types";
import { RiskMeter } from "./risk-meter";
import { InlineHighlight } from "./inline-highlight";
import { IndicatorAnnotation } from "./indicator-annotation";
import { NextSteps } from "./next-steps";
import { getReviewerMode, recordExpandAll, setReviewerMode } from "@/lib/reviewer";
import { countServRefined, getHistory } from "@/lib/history";

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
        // Animate from SERV's raw score to the blended final score so users
        // see the needle move — the visual proof that SERV changed something.
        ruleScoreBefore={result.serv_rule_score_before ?? null}
      />

      {/* Session SERV counter — shows accumulated value after SERV has been
          used across multiple scans. Only appears when there's a meaningful
          history so it doesn't clutter a fresh session. */}
      {result.serv_used && (
        <SessionServCount />
      )}

      {/* SERV Reasoning attribution — visible only when SERV contributed.
          Shows the score delta so the user can see exactly what SERV added:
          "SERV saw 0.71, rules saw 0.42, final is 0.57" — this is the
          monetization signal. Off by default; free scans show nothing here.

          When serv_rule_score_before is present the badge is value-dense;
          when absent (older miner, edge case) it falls back to the generic
          message. */}
      {result.serv_used && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: EASE_OUT }}
          className="rounded-lg border border-violet/20 bg-violet/5 overflow-hidden"
        >
          <div className="flex items-center gap-2 px-3 py-2">
            <span className="font-mono text-xs font-bold text-violet shrink-0">
              SERV Reasoning
            </span>
            {typeof result.serv_rule_score_before === "number" ? (
              <ScoreDelta
                ruleScore={result.risk_score}
                servScore={result.serv_rule_score_before}
                cost={result.serv_cost ?? undefined}
              />
            ) : (
              <span className="text-xs text-ink-muted leading-relaxed">
                second-tier judge refined this verdict
              </span>
            )}
          </div>
          {/* Collapsible reasoning — the "why" behind SERV's score */}
          <ServReasoningPanel result={result} />
        </motion.div>
      )}
      {/* SERV configured but failed — only show when the call was attempted
          and returned confidence=0 (network / credit / parse error). Keeps
          the user informed that their toggle was honoured but the upstream
          couldn't contribute; rule verdict still stands. */}
      {result.serv_attempted && !result.serv_used && result.serv_available && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: EASE_OUT }}
          className="flex items-start gap-2 text-xs text-ink-faint bg-canvas border border-border rounded-lg px-3 py-2"
        >
          <span className="font-mono font-semibold shrink-0 mt-px">
            SERV fallback
          </span>
          <span className="text-ink-muted leading-relaxed">
            SERV was unavailable for this scan — rule-based verdict stands
          </span>
        </motion.div>
      )}

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

      {/* Normalization disclosure — when the engine had to strip evasion
          machinery (invisible chars, lookalikes, encodings) to read the
          content, say so. Transparency is part of the verdict. */}
      {result.normalizations_applied &&
        result.normalizations_applied.length > 0 && (
          <motion.p
            className="text-xs text-ink-muted leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35, duration: 0.3 }}
          >
            Normalized before scanning:{" "}
            {result.normalizations_applied
              .map(
                (n) =>
                  ({
                    zero_width_strip: "invisible characters removed",
                    confusable_fold: "lookalike characters folded to ASCII",
                    token_desplit: "split keywords rejoined",
                    rot13_decode: "ROT13 text decoded",
                    hex_decode: "hex blob decoded",
                    base64_decode: "base64 blob decoded",
                  })[n] ?? n
              )
              .join(" · ")}
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

// ── Sub-components ───────────────────────────────────────────────────────────

interface ScoreDeltaProps {
  ruleScore: number;
  servScore: number;
  cost?: { total_usdc: number } | null;
}

/**
 * Shows the SERV-vs-rules score delta as a concise value-prop line.
 * "SERV saw 0.71 · rules saw 0.42 · final 0.57" — the upsell signal.
 * Optionally shows the approximate SERV cost when available.
 */
function ScoreDelta({ ruleScore, servScore, cost }: ScoreDeltaProps) {
  const moved = servScore - ruleScore;
  const direction = moved > 0 ? "↑" : moved < 0 ? "↓" : "→";
  const moveColor =
    moved > 0.05
      ? "text-dangerous"
      : moved < -0.05
        ? "text-warning"
        : "text-ink-muted";

  return (
    <span className="text-xs text-ink-muted leading-relaxed flex items-center gap-1.5 flex-wrap">
      <span>SERV saw</span>
      <span className={`font-mono font-semibold ${moveColor}`}>{servScore.toFixed(2)}</span>
      <span>· rules saw</span>
      <span className="font-mono text-ink-faint">{ruleScore.toFixed(2)}</span>
      <span className={`${moveColor}`}>
        {direction} {Math.abs(moved).toFixed(2)}
      </span>
      {cost?.total_usdc != null && cost.total_usdc > 0 && (
        <span className="text-ink-faint font-mono text-[10px]">
          · ~${cost.total_usdc.toFixed(4)}
        </span>
      )}
    </span>
  );
}

/**
 * Collapsible panel showing SERV's reasoning when it contributed to the
 * verdict. Hidden by default so the badge stays compact; expanded on click
 * so the user can see *why* SERV changed the score — the second upsell.
 */
function ServReasoningPanel({ result }: { result: ScanResponse }) {
  const [expanded, setExpanded] = useState(false);

  // The reasoning is carried by the top indicator's remediation when SERV
  // refined it; otherwise we fall back to the scan summary.
  const topIndicator =
    result.indicators.length > 0
      ? result.indicators.reduce((a, b) =>
          a.severity.value > b.severity.value ||
          (a.severity.value === b.severity.value && a.confidence > b.confidence)
            ? a
            : b
        )
      : null;
  const reasoning = topIndicator?.explanation ?? result.summary ?? "";

  if (!reasoning) return null;

  return (
    <div className="border-t border-violet/10">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[11px] text-violet/70 hover:text-violet transition-colors"
        aria-expanded={expanded}
      >
        <span>Why SERV changed the score</span>
        <span className={`transform transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <p className="px-3 pb-2 text-xs text-ink-muted leading-relaxed">
              {reasoning}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Session SERV counter ──────────────────────────────────────────────────────
// Shows accumulated SERV value across the current session. Only appears when
// there's a meaningful count so fresh sessions stay clean.
function SessionServCount() {
  const refined = countServRefined(10);
  const total = getHistory().slice(0, 10).length;

  // Don't show if we haven't seen enough data yet
  if (total < 2 || refined === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT }}
      className="inline-flex items-center gap-2 text-[11px] text-violet font-medium bg-violet/5 border border-violet/15 rounded-full px-3 py-1"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-violet shrink-0" />
      SERV refined {refined} of {total} recent scans
    </motion.div>
  );
}
