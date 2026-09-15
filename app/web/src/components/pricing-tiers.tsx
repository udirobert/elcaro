"use client";

import Link from "next/link";
import { motion } from "framer-motion";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Cost estimate for gpt-5.4-mini via SERV (the default model):
//   Input: ~$1 / 1M tokens · Output: ~$6 / 1M tokens
// A typical scan sends ~600 tokens in, gets back ~200 tokens out.
//   Per scan ≈ ($1×600 + $6×200) / 1M ≈ $0.0018 → ~$18 / 10 k scans.
// These are approximations — the actual per-call cost is returned in
// serv_cost.total_usdc on the ScanResponse so callers always know.
const ESTIMATED_COST_PER_10K = "$15–$25";
const ESTIMATED_PER_SCAN_USDC = "~$0.002";
const ESTIMATED_LATENCY_MS = "~1 s";
const FREE_LATENCY_MS = "<10 ms";

interface PricingTiersProps {
  // When true, the SERV card is pre-highlighted to draw the eye.
  // Used on the integrated /integrate page; false on a standalone pricing page.
  elevatedServ?: boolean;
}

export function PricingTiers({ elevatedServ = false }: PricingTiersProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <span className="text-xs font-mono text-ink-faint">00</span>
        <h2 className="text-lg font-bold text-ink">Choose your detection depth</h2>
      </div>
      <p className="text-sm text-ink-muted leading-relaxed max-w-xl">
        Every scan starts on the free rule-based path — no key, no cost, under
        10 ms. SERV Reasoning is an optional second pass that inspects
        borderline cases with LLM judgment. Enable it when you need higher
        confidence on ambiguous content.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Free tier */}
        <TierCard
          label="Free"
          price="$0"
          subtitle="Rule-based detection"
          highlight={false}
        >
          <FeatureRow label="Latency" value={FREE_LATENCY_MS} />
          <FeatureRow label="Scope" value="Deterministic rules" />
          <FeatureRow
            label="Gray-zone cases"
            value="Missed or guessed"
            muted
          />
          <FeatureRow label="TTP mapping" value="Rule-covered techniques" />
          <FeatureRow
            label="Remediation"
            value="Generic quarantine notice"
            muted
          />
          <FeatureRow
            label="Setup"
            value="None — works immediately"
          />
          <p className="mt-4 pt-4 border-t border-border text-[11px] text-ink-faint leading-relaxed">
            Great for high-volume, low-risk workloads. All agents get this
            path by default.
          </p>
        </TierCard>

        {/* SERV-Enhanced tier */}
        <TierCard
          label="SERV Enhanced"
          price={ESTIMATED_COST_PER_10K}
          subtitle={`~${ESTIMATED_PER_SCAN_USDC}/scan · paid to SERV`}
          highlight={elevatedServ}
        >
          <FeatureRow label="Latency" value={ESTIMATED_LATENCY_MS} />
          <FeatureRow label="Scope" value="Rules + LLM judgment" />
          <FeatureRow
            label="Gray-zone cases"
            value="SERV reviews & re-scores"
          />
          <FeatureRow
            label="TTP mapping"
            value="Enriched from SERV"
          />
          <FeatureRow
            label="Remediation"
            value="SERV-refined, agent-ready"
          />
          <FeatureRow label="Setup" value="Set SERV_API_KEY + SERV_ENABLED=1" />
          <p className="mt-4 pt-4 border-t border-border text-[11px] text-ink-faint leading-relaxed">
            Pays SERV directly (gpt-5.4-mini, the cheapest model in their
            catalog). No Elcaro markup — every scan returns
            <code className="font-mono bg-surface border border-border px-1 rounded text-xs mx-1">
              serv_cost.total_usdc
            </code>
            so you see the real cost per call. Typical: ~$0.002/scan.
          </p>
          <div className="mt-4">
            <Link
              href="https://docs.openserv.ai/serv-reasoning/day-one"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet hover:text-violet/80 transition-colors underline underline-offset-2"
            >
              View SERV day-one docs
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </TierCard>
      </div>

      {/* When SERV is configured but not yet enabled — a contextual nudge */}
      <p className="text-[11px] text-ink-faint leading-relaxed">
        Your deployment already supports SERV. To enable: set{" "}
        <code className="font-mono bg-surface border border-border px-1.5 py-0.5 rounded text-xs">
          SERV_ENABLED=1
        </code>{" "}
        and{" "}
        <code className="font-mono bg-surface border border-border px-1.5 py-0.5 rounded text-xs">
          SERV_API_KEY
        </code>
        {" "}on your miner, then toggle{" "}
        <span className="font-medium text-ink-muted">
          &ldquo;SERV Reasoning&rdquo;
        </span>{" "}
        on the /scan page.
      </p>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

interface TierCardProps {
  label: string;
  price: string;
  subtitle: string;
  highlight: boolean;
  children: React.ReactNode;
}

function TierCard({ label, price, subtitle, highlight, children }: TierCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT }}
      className={[
        "rounded-xl border p-5 space-y-3",
        highlight
          ? "border-violet/30 bg-violet/5"
          : "border-border bg-surface",
      ].join(" ")}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <p className="text-xs font-mono text-ink-faint uppercase tracking-wider">
            {label}
          </p>
          <p className="text-xs text-ink-muted mt-0.5">{subtitle}</p>
        </div>
        <p
          className={[
            "text-sm font-mono font-bold shrink-0",
            highlight ? "text-violet" : "text-ink",
          ].join(" ")}
        >
          {price}
          <span className="text-[10px] font-normal text-ink-faint ml-1">
            /10k scans
          </span>
        </p>
      </div>

      <div className="space-y-2 pt-1">
        {children}
      </div>
    </motion.div>
  );
}

interface FeatureRowProps {
  label: string;
  value: string;
  muted?: boolean;
}

function FeatureRow({ label, value, muted = false }: FeatureRowProps) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-xs">
      <span className={muted ? "text-ink-faint" : "text-ink-muted"}>{label}</span>
      <span
        className={[
          "font-medium shrink-0 text-right",
          muted ? "text-ink-faint" : "text-ink",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}
