"use client";

import React from "react";
import { motion } from "framer-motion";
import type { DetectionIndicator } from "@/lib/types";

interface InlineHighlightProps {
  content: string;
  indicators: DetectionIndicator[];
}

export function InlineHighlight({ content, indicators }: InlineHighlightProps) {
  // Build a list of ranges to highlight
  const highlights: { start: number; end: number; className: string }[] = [];

  for (const ind of indicators) {
    const matchIdx = content.indexOf(ind.matched_text);
    if (matchIdx >= 0) {
      highlights.push({
        start: matchIdx,
        end: matchIdx + ind.matched_text.length,
        className:
          ind.confidence >= 0.7
            ? "highlight-dangerous"
            : "highlight-suspicious",
      });
    }
  }

  // Sort by start position and merge overlaps
  highlights.sort((a, b) => a.start - b.start);

  // Render content with highlighted spans
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
    // Text before this highlight
    if (h.start > lastEnd) {
      segments.push(
        <span key={`text-${i}`}>{content.slice(lastEnd, h.start)}</span>
      );
    }

    // Highlighted text
    segments.push(
      <motion.span
        key={`hl-${i}`}
        className={h.className}
        initial={{ opacity: 0, backgroundColor: "transparent" }}
        animate={{ opacity: 1 }}
        transition={{ delay: i * 0.15, duration: 0.3 }}
      >
        {content.slice(h.start, h.end)}
      </motion.span>
    );

    lastEnd = h.end;
  });

  // Remaining text
  if (lastEnd < content.length) {
    segments.push(<span key="text-end">{content.slice(lastEnd)}</span>);
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
