"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import type { DetectionIndicator, Severity } from "@/lib/types";
import { TECHNIQUE_LABELS } from "@/lib/constants";

interface IndicatorAnnotationProps {
  indicator: DetectionIndicator;
  index: number;
}

const SEVERITY_COLORS: Record<Severity, string> = {
  info: "#6B6B68",
  low: "#2563EB",
  medium: "#D4860A",
  high: "#E5533D",
  critical: "#991B1B",
};

const SEVERITY_BG: Record<Severity, string> = {
  info: "bg-[#f4f4f2]",
  low: "bg-low-bg",
  medium: "bg-suspicious-bg",
  high: "bg-dangerous-bg",
  critical: "bg-dangerous-bg",
};

export function IndicatorAnnotation({
  indicator,
  index,
}: IndicatorAnnotationProps) {
  const [expanded, setExpanded] = useState(false);
  const techniqueLabel =
    TECHNIQUE_LABELS[indicator.technique_class] || indicator.technique_class;
  const confidencePercent = Math.round(indicator.confidence * 100);
  const accentColor = SEVERITY_COLORS[indicator.severity];

  return (
    <motion.div
      className="group cursor-pointer"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        delay: index * 0.1,
        duration: 0.35,
        ease: [0.16, 1, 0.3, 1],
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-4">
        {/* Severity accent line */}
        <div
          className="w-1 shrink-0 rounded-full mt-0.5 transition-all duration-300"
          style={{
            height: expanded ? "100%" : "2rem",
            minHeight: "2rem",
            backgroundColor: accentColor,
          }}
        />

        <div className="space-y-2 min-w-0 flex-1">
          {/* Header row */}
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${SEVERITY_BG[indicator.severity]}`}
              style={{ color: accentColor }}
            >
              {indicator.severity}
            </span>
            <span className="text-sm font-semibold text-ink">
              {techniqueLabel}
            </span>
            <span className="text-xs text-ink-faint font-mono">
              {confidencePercent}%
            </span>
            <span className="text-xs text-ink-faint ml-auto">
              {expanded ? "▾" : "▸"}
            </span>
          </div>

          {/* Explanation — always visible */}
          <p className="text-sm text-ink-muted leading-relaxed">
            {indicator.explanation}
          </p>

          {/* Expanded: evidence + TTPs + remediation */}
          {expanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              transition={{ duration: 0.25 }}
              className="space-y-3 pt-2"
            >
              {/* Evidence */}
              <div className="rounded-lg bg-canvas border border-border p-3 font-mono text-xs leading-relaxed">
                <span className="text-ink-faint">{indicator.evidence.context_before}</span>
                <span
                  className="font-semibold px-0.5 rounded"
                  style={{ backgroundColor: `${accentColor}20`, color: accentColor }}
                >
                  {indicator.evidence.matched_text}
                </span>
                <span className="text-ink-faint">{indicator.evidence.context_after}</span>
              </div>

              {/* TTPs */}
              {indicator.ttps.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {indicator.ttps.map((ttp) => (
                    <span
                      key={`${ttp.framework}-${ttp.technique_id}`}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-canvas border border-border text-ink-muted"
                    >
                      {ttp.technique_id} · {ttp.tactic}
                    </span>
                  ))}
                </div>
              )}

              {/* Remediation */}
              <div className="flex items-start gap-2 pt-1">
                <span className="text-xs text-safe font-semibold shrink-0">→</span>
                <p className="text-xs text-ink-muted leading-relaxed">
                  {indicator.remediation}
                </p>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
