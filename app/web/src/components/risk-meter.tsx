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
      className="flex items-baseline gap-4 flex-wrap"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Score — the hero number */}
      <motion.span
        className="text-5xl sm:text-6xl font-black tracking-tight"
        style={{ color }}
        initial={{ scale: 0.7, opacity: 0, filter: "blur(8px)" }}
        animate={{ scale: 1, opacity: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.span>{displayScore}</motion.span>
      </motion.span>

      {/* Level label */}
      <motion.span
        className={`text-xs font-bold uppercase tracking-widest px-2.5 py-1 rounded-md ${LEVEL_BG[level]}`}
        style={{ color }}
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.25, duration: 0.3 }}
      >
        {level}
      </motion.span>

      {/* Bar */}
      <div className="flex-1 max-w-48 h-1 rounded-full bg-border overflow-hidden self-center">
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
        {latencyMs}ms
      </motion.span>
    </motion.div>
  );
}
