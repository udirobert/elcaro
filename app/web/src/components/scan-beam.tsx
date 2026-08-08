"use client";

import { motion } from "framer-motion";

export function ScanBeam() {
  return (
    <motion.div
      className="absolute inset-0 pointer-events-none rounded-2xl overflow-hidden z-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Gradient sweep — moves top to bottom */}
      <motion.div
        className="absolute inset-x-0 h-[2px]"
        style={{
          background:
            "linear-gradient(90deg, transparent, #7C3AED, #F97066, #7C3AED, transparent)",
        }}
        initial={{ top: "0%" }}
        animate={{ top: "100%" }}
        transition={{
          duration: 1.2,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />

      {/* Subtle glow following the beam */}
      <motion.div
        className="absolute inset-x-0 h-8 opacity-20 blur-md"
        style={{
          background:
            "linear-gradient(90deg, transparent, #7C3AED40, #F9706640, #7C3AED40, transparent)",
        }}
        initial={{ top: "-4%" }}
        animate={{ top: "100%" }}
        transition={{
          duration: 1.2,
          ease: "easeInOut",
          repeat: Infinity,
        }}
      />
    </motion.div>
  );
}
