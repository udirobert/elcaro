"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { HistoryEntry } from "@/lib/history";
import { getHistory, clearHistory } from "@/lib/history";
import type { RiskLevel } from "@/lib/types";

interface ScanHistoryProps {
  onSelect: (entry: HistoryEntry) => void;
  refreshKey: number;
}

const RISK_DOT: Record<RiskLevel, string> = {
  safe: "bg-safe",
  low: "bg-low",
  suspicious: "bg-suspicious",
  dangerous: "bg-dangerous",
};

function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function ScanHistory({ onSelect, refreshKey }: ScanHistoryProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setHistory(getHistory());
  }, [refreshKey]);

  if (history.length === 0) return null;

  return (
    <div className="space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-xs font-medium text-ink-faint hover:text-ink-muted transition-colors"
      >
        <span>{expanded ? "▾" : "▸"}</span>
        <span>History ({history.length})</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
              {history.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => onSelect(entry)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface transition-colors text-left group"
                >
                  {/* Risk dot */}
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${RISK_DOT[entry.risk_level]}`}
                  />

                  {/* Content preview */}
                  <span className="text-xs text-ink-muted truncate flex-1 font-mono">
                    {entry.content.slice(0, 60)}
                    {entry.content.length > 60 ? "..." : ""}
                  </span>

                  {/* Score */}
                  <span className="text-xs text-ink-faint font-mono shrink-0">
                    {entry.risk_score.toFixed(2)}
                  </span>

                  {/* Time */}
                  <span className="text-[10px] text-ink-faint shrink-0">
                    {timeAgo(entry.timestamp)}
                  </span>
                </button>
              ))}
            </div>

            {/* Clear button */}
            <button
              onClick={() => {
                clearHistory();
                setHistory([]);
              }}
              className="mt-2 text-[10px] text-ink-faint hover:text-dangerous transition-colors"
            >
              Clear history
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
