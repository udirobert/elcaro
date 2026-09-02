"use client";

import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

// One vertical pass while the scan is in flight. Transform-only (the moving
// layer is full height, so y: "100%" is the parent, not the 2px rule).
// Ink, not a brand gradient — danger colour is reserved for the verdict.
export function ScanBeam() {
  const reduceMotion = useReducedMotion();
  if (reduceMotion) return null;

  return (
    <motion.div
      className="absolute inset-0 pointer-events-none rounded-2xl overflow-hidden z-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      <motion.div
        className="absolute inset-x-0 h-full"
        initial={{ y: "-100%" }}
        animate={{ y: "100%" }}
        transition={{ duration: 0.85, ease: EASE }}
      >
        <div className="absolute bottom-0 inset-x-0 h-[2px] bg-ink" />
        <div className="absolute bottom-0 inset-x-0 h-8 bg-ink/10" />
      </motion.div>
    </motion.div>
  );
}
