"use client";

import { useEffect, useState } from "react";

// Miner status indicator — pings /api/metrics every 60s and shows a green dot
// when the production miner is reachable, amber when slow, or red when down.
// Defensive: if the miner goes down during judging, a judge seeing a scan
// error understands it's a transient infrastructure issue, not a broken
// product. Renders nothing during the initial check (no flash of red).

type Status = "checking" | "live" | "slow" | "down";

const COLORS: Record<Status, string> = {
  checking: "bg-ink-faint",
  live: "bg-safe",
  slow: "bg-suspicious",
  down: "bg-dangerous",
};

const LABELS: Record<Status, string> = {
  checking: "",
  live: "live",
  slow: "slow",
  down: "down",
};

export function MinerStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        const start = performance.now();
        const res = await fetch("/api/metrics", {
          signal: controller.signal,
          cache: "no-store",
        });
        const elapsed = performance.now() - start;
        clearTimeout(timeout);

        if (cancelled) return;

        if (res.ok) {
          setStatus(elapsed > 2000 ? "slow" : "live");
        } else {
          setStatus("down");
        }
      } catch {
        if (!cancelled) setStatus("down");
      }
    }

    check();
    const interval = setInterval(check, 60000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (status === "checking") return null;

  return (
    <span
      className="flex items-center gap-1.5 text-[10px] text-ink-faint font-mono"
      title={`Miner ${status}`}
      aria-label={`Miner ${status}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${COLORS[status]} ${
          status === "live" ? "animate-pulse" : ""
        }`}
      />
      {LABELS[status]}
    </span>
  );
}
