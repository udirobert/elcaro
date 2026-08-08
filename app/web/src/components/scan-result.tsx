"use client";

import { motion } from "framer-motion";
import type { ScanResponse } from "@/lib/types";
import { TECHNIQUE_LABELS } from "@/lib/constants";
import { RiskMeter } from "./risk-meter";
import { InlineHighlight } from "./inline-highlight";
import { IndicatorAnnotation } from "./indicator-annotation";

interface ScanResultProps {
  result: ScanResponse;
  content: string;
}

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function ScanResult({ result, content }: ScanResultProps) {
  const isQuarantined = result.risk_score >= 0.5;
  const isSafe = result.risk_level === "safe";

  return (
    <div className="space-y-8">
      {/* Risk meter */}
      <RiskMeter
        score={result.risk_score}
        level={result.risk_level}
        latencyMs={result.latency_ms}
      />

      {/* Summary */}
      {result.summary && (
        <motion.p
          className="text-sm text-ink-muted leading-relaxed"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.3, ease: EASE_OUT }}
        >
          {result.summary}
        </motion.p>
      )}

      {/* Evidence — inline highlighting */}
      {result.indicators.length > 0 && (
        <motion.div
          className="space-y-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.35, ease: EASE_OUT }}
        >
          <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest">
            Evidence
          </p>
          <InlineHighlight content={content} indicators={result.indicators} />
        </motion.div>
      )}

      {/* Indicators — threat cards */}
      {result.indicators.length > 0 && (
        <motion.div
          className="space-y-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.35, ease: EASE_OUT }}
        >
          <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest">
            Findings · {result.indicators.length}
          </p>
          <div className="space-y-3">
            {result.indicators.map((indicator, i) => (
              <IndicatorAnnotation
                key={`${indicator.technique_name}-${i}`}
                indicator={indicator}
                index={i}
              />
            ))}
          </div>
        </motion.div>
      )}

      {/* Verdict */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.3, ease: EASE_OUT }}
        className={`inline-flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
          isSafe
            ? "bg-safe-bg"
            : isQuarantined
              ? "bg-dangerous-bg"
              : "bg-suspicious-bg"
        }`}
      >
        {/* Status icon with animation */}
        <motion.span
          className="text-xl"
          initial={{ scale: 0, rotate: -90 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: 0.7, type: "spring", stiffness: 300, damping: 20 }}
        >
          {isSafe ? "✓" : isQuarantined ? "◉" : "◬"}
        </motion.span>
        <div>
          <p
            className={`text-sm font-semibold ${
              isSafe
                ? "text-safe"
                : isQuarantined
                  ? "text-dangerous"
                  : "text-suspicious"
            }`}
          >
            {isSafe
              ? "Safe to process"
              : isQuarantined
                ? "Quarantined"
                : "Review recommended"}
          </p>
          <p className="text-xs text-ink-muted">
            {isSafe
              ? "No injection patterns found"
              : `${result.flagged_techniques.map((t) => TECHNIQUE_LABELS[t] || t).join(", ")} detected`}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
