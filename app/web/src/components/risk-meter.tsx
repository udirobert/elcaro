"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect } from "react";
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

export function RiskMeter({ score, level, latencyMs }: RiskMeterProps) {
  const motionScore = useMotionValue(0);
  const displayScore = useTransform(motionScore, (v) => v.toFixed(2));

  useEffect(() => {
    const controls = animate(motionScore, score, {
      duration: 0.8,
      ease: [0.16, 1, 0.3, 1],
    });
    return controls.stop;
  }, [score, motionScore]);

  const color = LEVEL_COLORS[level];

  return (
    <div className="flex items-baseline gap-4">
      {/* Animated score */}
      <motion.span
        className="text-6xl font-black tracking-tight font-[var(--font-display)]"
        style={{ color }}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <motion.span>{displayScore}</motion.span>
      </motion.span>

      {/* Level + latency */}
      <div className="space-y-1">
        <motion.span
          className="text-sm font-semibold uppercase tracking-wider"
          style={{ color }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          {level}
        </motion.span>
        <motion.p
          className="text-xs text-ink-faint font-mono"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          {latencyMs}ms
        </motion.p>
      </div>

      {/* Visual bar — grows from left */}
      <div className="flex-1 max-w-64 h-1.5 rounded-full bg-border overflow-hidden ml-4">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: "0%" }}
          animate={{ width: `${Math.min(score * 100, 100)}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        />
      </div>
    </div>
  );
}
