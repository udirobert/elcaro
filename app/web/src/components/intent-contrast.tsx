"use client";

import { motion } from "framer-motion";
import type { IntentContrast } from "@/lib/webmcp-doctrine";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

interface IntentContrastPanelProps {
  contrast: IntentContrast;
}

function Column({
  step,
  label,
  body,
  tone,
  delay,
}: {
  step: string;
  label: string;
  body: string;
  tone: "ink" | "danger" | "safe";
  delay: number;
}) {
  const box =
    tone === "danger"
      ? "border-dangerous/25 bg-dangerous-bg"
      : tone === "safe"
        ? "border-safe/25 bg-safe-bg"
        : "border-border bg-surface";
  const labelColor =
    tone === "danger"
      ? "text-dangerous"
      : tone === "safe"
        ? "text-safe"
        : "text-ink-faint";

  return (
    <motion.div
      className={`rounded-xl border px-4 py-3 space-y-2 min-w-0 ${box}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: EASE_OUT }}
    >
      <p
        className={`text-[10px] font-bold uppercase tracking-widest ${labelColor}`}
      >
        <span className="font-mono mr-1.5 opacity-70">{step}</span>
        {label}
      </p>
      <p className="text-sm text-ink leading-relaxed">{body}</p>
    </motion.div>
  );
}

export function IntentContrastPanel({ contrast }: IntentContrastPanelProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted leading-relaxed">
        What almost happened.
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        <Column
          step="1"
          label="About to"
          body={contrast.intended_action}
          tone="ink"
          delay={0}
        />
        <Column
          step="2"
          label="The document asked"
          body={contrast.injection_asked_for}
          tone="danger"
          delay={0.08}
        />
        <Column
          step="3"
          label="Do this instead"
          body={
            contrast.quarantined
              ? contrast.quote_to_user
              : contrast.remediation
          }
          tone="safe"
          delay={0.16}
        />
      </div>
    </div>
  );
}
