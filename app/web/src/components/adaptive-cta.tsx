"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { hasRunGauntlet } from "@/lib/journey";
import { getHistory } from "@/lib/history";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Journey-aware closing CTA — reads what the visitor has actually done (ran
// the Gauntlet? scanned their own content?) and suggests the next logical
// step instead of repeating a fixed funnel. Uses the same SSR-safe
// useSyncExternalStore pattern as ScanForm: the server snapshot is always
// "fresh" (no localStorage), so hydration matches, and the client snapshot
// reads the real journey state on mount.

type JourneyState = "fresh" | "gauntlet" | "scanned";

function subscribeNoop() {
  return () => {};
}

function getClientSnapshot(): JourneyState {
  const ranGauntlet = hasRunGauntlet();
  const hasScanned = getHistory().length > 0;
  if (ranGauntlet) return "gauntlet";
  if (hasScanned) return "scanned";
  return "fresh";
}

function getServerSnapshot(): JourneyState {
  return "fresh";
}

const COPY: Record<
  JourneyState,
  { headline: string; subtext: string; primary: { label: string; href: string }; secondary: { label: string; href: string } }
> = {
  fresh: {
    headline: "Your agent is reading",
    subtext:
      "See what it can\u2019t \u2014 then make sure nothing whispers to it unscanned.",
    primary: { label: "Run the Gauntlet", href: "/gauntlet" },
    secondary: { label: "Scan something", href: "/scan" },
  },
  gauntlet: {
    headline: "Now try your own content",
    subtext:
      "The Gauntlet proved the engine. Paste what your agent actually retrieves.",
    primary: { label: "Scan your own content", href: "/scan" },
    secondary: { label: "Add to your agent", href: "/integrate" },
  },
  scanned: {
    headline: "Ready to protect your agent?",
    subtext:
      "You\u2019ve seen the verdicts. Now put Elcaro in your retrieval pipeline.",
    primary: { label: "Add to your agent", href: "/integrate" },
    secondary: { label: "Run the Gauntlet", href: "/gauntlet" },
  },
};

export function AdaptiveCTA() {
  const journey = useSyncExternalStore(
    subscribeNoop,
    getClientSnapshot,
    getServerSnapshot
  );
  const reduceMotion = useReducedMotion();
  const copy = COPY[journey];

  return (
    <motion.div
      key={journey}
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: EASE_OUT }}
      className="max-w-2xl mx-auto space-y-6"
    >
      <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-ink">
        {copy.headline}
        {journey === "fresh" && (
          <>
            <br />
            right now.
          </>
        )}
      </h2>
      <p className="text-sm text-ink-muted leading-relaxed max-w-md">
        {copy.subtext}
      </p>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <Link
          href={copy.primary.href}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors"
        >
          {copy.primary.label}
          <span className="text-canvas/60">→</span>
        </Link>
        <Link
          href={copy.secondary.href}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-sm font-semibold text-ink-muted hover:text-ink hover:border-border-strong transition-colors"
        >
          {copy.secondary.label}
        </Link>
      </div>
    </motion.div>
  );
}
