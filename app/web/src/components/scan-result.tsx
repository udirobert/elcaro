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

export function ScanResult({ result, content }: ScanResultProps) {
  const isQuarantined = result.risk_score >= 0.5;

  return (
    <div className="space-y-10">
      {/* Risk meter — the headline number */}
      <RiskMeter score={result.risk_score} level={result.risk_level} latencyMs={result.latency_ms} />

      {/* Summary — one sentence, human-readable */}
      {result.summary && (
        <motion.p
          className="text-base text-ink-muted leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {result.summary}
        </motion.p>
      )}

      {/* The content with inline highlights */}
      {result.indicators.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-ink-faint uppercase tracking-widest">
            Evidence
          </p>
          <InlineHighlight content={content} indicators={result.indicators} />
        </div>
      )}

      {/* Indicator annotations — threat cards */}
      {result.indicators.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs font-medium text-ink-faint uppercase tracking-widest">
            Findings ({result.indicators.length})
          </p>
          <div className="space-y-4">
            {result.indicators.map((indicator, i) => (
              <IndicatorAnnotation
                key={`${indicator.technique_name}-${i}`}
                indicator={indicator}
                index={i}
              />
            ))}
          </div>
        </div>
      )}

      {/* Verdict */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, duration: 0.3 }}
        className={`inline-flex items-center gap-3 px-4 py-3 rounded-xl ${
          isQuarantined ? "bg-dangerous-bg" : "bg-safe-bg"
        }`}
      >
        <span className="text-2xl">{isQuarantined ? "◉" : "◎"}</span>
        <div>
          <p
            className={`text-sm font-semibold ${
              isQuarantined ? "text-dangerous" : "text-safe"
            }`}
          >
            {isQuarantined ? "Quarantined" : "Safe to process"}
          </p>
          <p className="text-xs text-ink-muted">
            {isQuarantined
              ? `${result.flagged_techniques.map((t) => TECHNIQUE_LABELS[t] || t).join(", ")} detected`
              : "No injection patterns found"}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
