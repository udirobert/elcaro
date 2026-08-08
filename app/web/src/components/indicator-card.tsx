"use client";

import { useState } from "react";
import type { DetectionIndicator } from "@/lib/types";

interface IndicatorCardProps {
  indicator: DetectionIndicator;
}

export function IndicatorCard({ indicator }: IndicatorCardProps) {
  const [expanded, setExpanded] = useState(false);
  const confidencePercent = Math.round(indicator.confidence * 100);

  return (
    <div
      className="border border-card-border rounded-lg bg-card p-4 cursor-pointer hover:border-foreground/20 transition-colors"
      onClick={() => setExpanded(!expanded)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") setExpanded(!expanded);
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">{expanded ? "▾" : "▸"}</span>
          <span className="text-sm font-mono text-foreground">
            {indicator.technique_name}
          </span>
        </div>
        <span className="text-xs font-mono text-muted">
          {confidencePercent}% confidence
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-3 pl-6 space-y-2">
          {/* Matched text */}
          <div className="p-2 rounded bg-background border border-card-border">
            <p className="text-xs text-muted mb-1">Matched text:</p>
            <p className="text-sm font-mono text-foreground break-all">
              &ldquo;{indicator.matched_text}&rdquo;
            </p>
          </div>

          {/* Explanation */}
          <p className="text-sm text-muted leading-relaxed">
            {indicator.explanation}
          </p>

          {/* Location */}
          <p className="text-xs text-muted">
            Location: <span className="font-mono">{indicator.location}</span>
          </p>
        </div>
      )}
    </div>
  );
}
