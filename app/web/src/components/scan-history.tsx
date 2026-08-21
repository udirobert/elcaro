"use client";

import { useState, useRef, useSyncExternalStore } from "react";
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

const EMPTY_HISTORY: HistoryEntry[] = [];
function getServerSnapshot(): HistoryEntry[] {
  return EMPTY_HISTORY;
}
function subscribeNoop() {
  return () => {};
}

export function ScanHistory({ onSelect, refreshKey }: ScanHistoryProps) {
  // getHistory() allocates a new array every call, which would break
  // useSyncExternalStore's requirement that the snapshot getter return an
  // Object.is-equal reference across calls until the store actually changes
  // (otherwise React assumes an infinite update loop and errors). The ref
  // below caches the last read; `cacheKey` — refreshKey from the parent (bumped
  // when a scan completes) combined with a local counter bumped on clear — is
  // the only thing allowed to invalidate it, so identity stays stable across
  // unrelated re-renders (e.g. `expanded` toggling) but updates exactly when
  // the underlying data does.
  const [clearCount, setClearCount] = useState(0);
  const cacheKey = `${refreshKey}:${clearCount}`;
  const cacheRef = useRef<{ key: string; data: HistoryEntry[] } | null>(null);

  const history = useSyncExternalStore(
    subscribeNoop,
    () => {
      if (!cacheRef.current || cacheRef.current.key !== cacheKey) {
        cacheRef.current = { key: cacheKey, data: getHistory() };
      }
      return cacheRef.current.data;
    },
    getServerSnapshot
  );
  const [expanded, setExpanded] = useState(false);

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
                setClearCount((n) => n + 1);
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
