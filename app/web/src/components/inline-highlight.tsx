"use client";

import React from "react";
import { motion } from "framer-motion";
import type { DetectionIndicator } from "@/lib/types";

interface InlineHighlightProps {
  content: string;
  indicators: DetectionIndicator[];
}

export function InlineHighlight({ content, indicators }: InlineHighlightProps) {
  // Build highlight ranges from evidence
  const highlights: { start: number; end: number; severity: string }[] = [];

  for (const ind of indicators) {
    const matchText = ind.evidence.matched_text;
    // Use char_offset if available, otherwise find in content
    let start = ind.evidence.char_offset;
    if (start === 0 && content.indexOf(matchText) > 0) {
      start = content.indexOf(matchText);
    }
    if (start >= 0 && matchText) {
      highlights.push({
        start,
        end: start + matchText.length,
        severity: ind.severity,
      });
    }
  }

  // Sort and deduplicate overlapping ranges
  highlights.sort((a, b) => a.start - b.start);

  if (highlights.length === 0) {
    return (
      <div className="p-5 rounded-xl bg-safe-bg border border-safe/20 font-mono text-sm leading-relaxed whitespace-pre-wrap">
        {content}
      </div>
    );
  }

  const segments: React.ReactNode[] = [];
  let lastEnd = 0;

  highlights.forEach((h, i) => {
    if (h.start > lastEnd) {
      segments.push(
        <span key={`text-${i}`} className="text-ink-muted">
          {content.slice(lastEnd, h.start)}
        </span>
      );
    }

    const isHighSeverity = h.severity === "high" || h.severity === "critical";
    segments.push(
      <motion.span
        key={`hl-${i}`}
        className={isHighSeverity ? "highlight-dangerous" : "highlight-suspicious"}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: i * 0.12, duration: 0.3 }}
      >
        {content.slice(h.start, h.end)}
      </motion.span>
    );

    lastEnd = h.end;
  });

  if (lastEnd < content.length) {
    segments.push(
      <span key="text-end" className="text-ink-muted">
        {content.slice(lastEnd)}
      </span>
    );
  }

  return (
    <motion.div
      className="p-5 rounded-xl bg-surface border border-border font-mono text-sm leading-relaxed whitespace-pre-wrap"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {segments}
    </motion.div>
  );
}
