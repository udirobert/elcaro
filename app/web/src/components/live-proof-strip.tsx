"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

// Live proof strip — real aggregate stats from the miner's /metrics.
// Hides itself entirely when the metrics endpoint is slow or unreachable:
// social proof that can't be faked, and no fake numbers when it's down.
export function LiveProofStrip() {
  const [stats, setStats] = useState<{
    scans: number;
    medianMs: number;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);

    fetch("/api/metrics", { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const scans = data?.total_scans;
        const median = data?.latency_ms?.p50;
        if (typeof scans === "number" && scans > 0) {
          setStats({
            scans,
            medianMs: typeof median === "number" ? median : 0,
          });
        }
      })
      .catch(() => {})
      .finally(() => clearTimeout(timeout));

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      controller.abort();
    };
  }, []);

  if (!stats) return null;

  return (
    <motion.p
      className="text-xs text-ink-faint font-mono pt-3"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.4 }}
    >
      {stats.scans.toLocaleString()} scans served live · median{" "}
      {stats.medianMs > 0 ? `${stats.medianMs}ms` : "<1ms"}
    </motion.p>
  );
}
