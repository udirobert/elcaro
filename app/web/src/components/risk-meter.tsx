"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useState } from "react";
import type { RiskLevel } from "@/lib/types";

interface RiskMeterProps {
  score: number;
  level: RiskLevel;
  latencyMs: number;
}

const LEVEL_COLORS: Record<RiskLevel, string> = {
  safe: "#1A8A7A",
  low: "#2563EB",
  suspicious: "#D4860A",
  dangerous: "#E5533D",
};

const LEVEL_BG: Record<RiskLevel, string> = {
  safe: "bg-safe-bg",
  low: "bg-low-bg",
  suspicious: "bg-suspicious-bg",
  dangerous: "bg-dangerous-bg",
};

// What the level means for the caller, folded into the same badge as the
// level itself rather than a second "verdict" block repeating it below.
const LEVEL_ACTION: Record<RiskLevel, string> = {
  safe: "safe to process",
  low: "likely safe",
  suspicious: "review recommended",
  dangerous: "quarantined",
};

export function RiskMeter({ score, level, latencyMs }: RiskMeterProps) {
  const motionScore = useMotionValue(0);
  const displayScore = useTransform(motionScore, (v) => v.toFixed(2));
  const [showLatency, setShowLatency] = useState(false);

  useEffect(() => {
    const controls = animate(motionScore, score, {
      duration: 0.7,
      ease: [0.16, 1, 0.3, 1],
    });

    // Stagger the latency reveal
    const timeout = setTimeout(() => setShowLatency(true), 600);
    return () => {
      controls.stop();
      clearTimeout(timeout);
    };
  }, [score, motionScore]);

  const color = LEVEL_COLORS[level];

  return (
    <motion.div
      className="flex items-baseline gap-3 flex-wrap"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Score — the hero number */}
      <motion.span
        className="text-4xl sm:text-5xl font-black tracking-tight"
        style={{ color }}
        initial={{ scale: 0.7, opacity: 0, filter: "blur(8px)" }}
        animate={{ scale: 1, opacity: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.span>{displayScore}</motion.span>
      </motion.span>

      {/* Level + verdict — one badge, not two */}
      <motion.span
        className={`text-xs font-bold px-2.5 py-1 rounded-md ${LEVEL_BG[level]}`}
        style={{ color }}
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.25, duration: 0.3 }}
      >
        <span className="uppercase tracking-widest">{level}</span>
        <span className="opacity-60 font-medium"> · {LEVEL_ACTION[level]}</span>
      </motion.span>

      {/* Bar */}
      <div className="flex-1 min-w-16 max-w-40 h-1 rounded-full bg-border overflow-hidden self-center">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: "0%" }}
          animate={{ width: `${Math.min(score * 100, 100)}%` }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        />
      </div>

      {/* Latency — fades in after the score lands */}
      <motion.span
        className="text-[11px] text-ink-faint font-mono self-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: showLatency ? 1 : 0 }}
        transition={{ duration: 0.3 }}
      >
        {latencyMs > 0 ? `${latencyMs}ms` : "<1ms"}
      </motion.span>
    </motion.div>
  );
}
