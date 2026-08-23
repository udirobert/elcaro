"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import type { ScanResponse } from "@/lib/types";
import { RiskMeter } from "./risk-meter";
import { InlineHighlight } from "./inline-highlight";
import { IndicatorAnnotation } from "./indicator-annotation";
import { NextSteps } from "./next-steps";

interface ScanResultProps {
  result: ScanResponse;
  content: string;
}

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function ScanResult({ result, content }: ScanResultProps) {
  const isSafe = result.risk_level === "safe";
  const hasFindings = result.indicators.length > 0;

  // Expanded-finding state lives here (not per-card) so an expand-all
  // control can drive every card at once.
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  function toggleExpanded(index: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }

  const allExpanded =
    hasFindings && expandedIds.size === result.indicators.length;

  return (
    <div className="space-y-5">
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
          {/* Expand-all — for the reviewer with eight indicators */}
          {result.indicators.length > 1 && (
            <button
              onClick={() =>
                setExpandedIds(
                  allExpanded
                    ? new Set()
                    : new Set(result.indicators.map((_, i) => i))
                )
              }
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
