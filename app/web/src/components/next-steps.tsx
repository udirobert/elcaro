"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import type { RiskLevel, ScanResponse } from "@/lib/types";
import { encodeVerdict } from "@/lib/share";

const SPRING = { type: "spring", stiffness: 400, damping: 30 } as const;

interface NextStepsProps {
  result: ScanResponse;
  content: string;
}

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Fallback only — the quarantine decision and the notice text now come from
// the API (ScanResponse.quarantined / safe_content, computed once in
// core/quarantine.py). This threshold covers responses from older miners and
// stale localStorage history that predate the server-side fields.
const BLOCK_THRESHOLD = 0.5;

// Risk-conditioned guidance — answers "so what do I do?" in the user's terms,
// using the same thresholds the integration docs teach (≥0.5 block, ≥0.3 flag).
const DECISION: Record<RiskLevel, { headline: string; actions: string[] }> = {
  dangerous: {
    headline: "Block it — this content should not reach your agent.",
    actions: [
      "Quarantine it — the notice above is exactly what your agent receives instead",
      "Alert your team, with this scan as the evidence",
    ],
  },
  suspicious: {
    headline: "Flag it — worth a human look before your agent acts.",
    actions: [
      "Quarantine it if nobody can review it now (notice shown above)",
      "Have a reviewer check the findings below, then pass or block",
    ],
  },
  low: {
    headline: "Process it — but log this scan with the findings below.",
    actions: [
      "Let the content through, and keep this scan in your audit trail",
    ],
  },
  safe: {
    headline: "Process it — nothing to act on.",
    actions: [],
  },
};

export function NextSteps({ result, content }: NextStepsProps) {
  const quarantined =
    result.quarantined ?? result.risk_score >= BLOCK_THRESHOLD;
  const decision = DECISION[result.risk_level];
  const [copied, setCopied] = useState(false);
  const reduceMotion = useReducedMotion();

  async function handleShare() {
    // The verdict is encoded in the URL fragment — nothing is stored
    // server-side. The disclosure below tells the user the link carries
    // their pasted content.
    const fragment = encodeVerdict({
      content,
      content_type: result.content_type,
      response: result,
      shared_at: Date.now(),
    });
    const url = `${window.location.origin}/scan#v=${fragment}`;
    const text = `Elcaro verdict: ${result.risk_level} (risk ${result.risk_score.toFixed(2)}). See what the agent would receive:`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "Elcaro scan verdict", text, url });
      } else {
        await navigator.clipboard.writeText(`${text} ${url}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Share sheet dismissed — no-op
    }
  }

  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.32, duration: 0.35, ease: EASE_OUT }}
    >
      {/* What your agent would receive — the remedy, not just the alarm */}
      <div>
        <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest mb-2">
          What your agent would receive
        </p>
        {quarantined ? (
          <div className="relative rounded-xl bg-dangerous-bg border border-dangerous/20 p-4 font-mono text-xs leading-relaxed text-dangerous/90">
            {result.safe_content ??
              "Quarantined — the original content is withheld and replaced with a structured notice."}
            {/* The stamp — the site's signature moment, peaking where the
                stakes are real: the user's own content, caught live */}
            <motion.span
              className="absolute right-3 top-3 px-2.5 py-1 rounded-md border-2 text-[10px] font-black uppercase tracking-[0.18em] border-dangerous text-dangerous bg-dangerous-bg/90 pointer-events-none"
              initial={
                reduceMotion
                  ? { opacity: 0 }
                  : { opacity: 0, scale: 1.8, rotate: -14 }
              }
              animate={
                reduceMotion
                  ? { opacity: 1 }
                  : { opacity: 1, scale: 1, rotate: -7 }
              }
              transition={reduceMotion ? { duration: 0.2 } : SPRING}
            >
              Quarantined
            </motion.span>
          </div>
        ) : (
          <div className="rounded-xl bg-surface border border-border p-4 text-sm text-ink-muted leading-relaxed">
            Passes through unchanged — the score is below the 0.5 quarantine
            threshold. In production you&apos;d still log this scan.
          </div>
        )}
      </div>

      {/* Your move — the decision, in three verbs max */}
      <div>
        <p className="text-[11px] font-medium text-ink-faint uppercase tracking-widest mb-2">
          Your move
        </p>
        <p className="text-sm font-semibold text-ink leading-snug mb-2">
          {decision.headline}
        </p>
        <ul className="space-y-1.5">
          {decision.actions.map((action, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-sm text-ink-muted leading-relaxed"
            >
              <span className="text-safe font-semibold shrink-0 mt-0.5">→</span>
              {action}
            </li>
          ))}
        </ul>
      </div>

      {/* The path from alarm to protection — contextual, only when it matters */}
      <Link
        href="/integrate"
        className="group inline-flex items-center gap-2 text-sm font-semibold text-violet hover:text-violet/80 transition-colors"
      >
        Don&apos;t just detect this — block it in your agent
        <span className="transition-transform group-hover:translate-x-0.5">→</span>
      </Link>

      {/* Share — the verdict travels; the content travels with it (disclosed) */}
      <div className="pt-1 border-t border-border">
        <div className="flex items-center justify-between gap-4 flex-wrap pt-3">
          <p className="text-[11px] text-ink-faint leading-relaxed max-w-sm">
            Sharing encodes this scan in the link itself — nothing is stored on
            any server. The link contains the pasted content.
          </p>
          <button
            onClick={handleShare}
            className="inline-flex items-center gap-2 text-xs font-semibold px-3.5 py-2 rounded-lg border border-border text-ink-muted hover:text-ink hover:border-border-strong transition-colors shrink-0"
          >
            {copied ? "✓ Link copied" : "Share this verdict"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
