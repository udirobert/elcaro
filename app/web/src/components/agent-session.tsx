"use client";

import { motion } from "framer-motion";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export type AgentBeat = 1 | 2 | 3 | "done";

const STEPS: { n: 1 | 2 | 3; label: string }[] = [
  { n: 1, label: "Load" },
  { n: 2, label: "Scan" },
  { n: 3, label: "Say what you almost did" },
];

export function agentBeat(args: {
  hasContent: boolean;
  scanning: boolean;
  hasResult: boolean;
  hasContrast: boolean;
}): AgentBeat {
  if (args.hasContrast) return "done";
  if (args.hasResult) return 3;
  if (args.scanning || args.hasContent) return 2;
  return 1;
}

export function AgentSessionRail({ beat }: { beat: AgentBeat }) {
  const current = beat === "done" ? 3 : beat;

  return (
    <ol className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
      <li className="text-ink-muted font-medium">Together</li>
      {STEPS.map((step, i) => {
        const active = step.n === current && beat !== "done";
        const done = beat === "done" || step.n < current;
        return (
          <li key={step.n} className="flex items-baseline gap-3">
            {i > 0 && (
              <span className="text-ink-faint" aria-hidden>
                →
              </span>
            )}
            <span
              className={
                active
                  ? "text-ink font-semibold"
                  : done
                    ? "text-ink-muted"
                    : "text-ink-faint"
              }
            >
              <span className="font-mono text-[10px] mr-1">{step.n}</span>
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function WaitingForIntent() {
  return (
    <motion.p
      className="text-sm text-ink-muted leading-relaxed"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT }}
    >
      Your agent’s turn — it should say what it was about to do with this,
      so you can see that next to the hidden instruction.
    </motion.p>
  );
}
