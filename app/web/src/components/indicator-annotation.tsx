"use client";

import { motion } from "framer-motion";
import type { DetectionIndicator } from "@/lib/types";
import { TECHNIQUE_LABELS } from "@/lib/constants";

interface IndicatorAnnotationProps {
  indicator: DetectionIndicator;
  index: number;
}

export function IndicatorAnnotation({
  indicator,
  index,
}: IndicatorAnnotationProps) {
  const techniqueLabel =
    TECHNIQUE_LABELS[indicator.technique_class] || indicator.technique_class;
  const confidencePercent = Math.round(indicator.confidence * 100);

  return (
    <motion.div
      className="flex items-start gap-4 group"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        delay: index * 0.1,
        duration: 0.35,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      {/* Left accent line */}
      <div
        className="w-0.5 shrink-0 rounded-full mt-1"
        style={{
          height: "100%",
          minHeight: "2rem",
          backgroundColor:
            indicator.confidence >= 0.7 ? "#E5533D" : "#D4860A",
        }}
      />

      {/* Content */}
      <div className="space-y-1 min-w-0">
        {/* Technique + confidence */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-ink">
            {techniqueLabel}
          </span>
          <span className="text-xs text-ink-faint font-mono">
            {confidencePercent}%
          </span>
        </div>

        {/* Explanation — the human-readable story */}
        <p className="text-sm text-ink-muted leading-relaxed">
          {indicator.explanation}
        </p>
      </div>
    </motion.div>
  );
}
