"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { scanContent, isError } from "@/lib/api";
import type { ScanResponse } from "@/lib/types";
import { PAYBOX_SCENARIOS, type PayboxScenario } from "@/lib/paybox-gauntlet";
import { QUARANTINE_THRESHOLD } from "@/lib/history";
import { InlineHighlight } from "./inline-highlight";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const LEVEL_COLORS: Record<string, string> = {
  safe: "#1A8A7A",
  low: "#2563EB",
  suspicious: "#D4860A",
  dangerous: "#E5533D",
};

// Volley pacing — same feel as /evaluate/gauntlet: each verdict lands
// before the next scenario fires, so a recording reads as a montage.
const STAGGER_MS = 350;

type Phase = "idle" | "running" | "done" | "error";

interface Entry {
  id: string;
  isInjection: boolean;
  response: ScanResponse;
}

function stopped(e: Entry): boolean {
  return e.isInjection && e.response.risk_score >= QUARANTINE_THRESHOLD;
}

function passed(e: Entry): boolean {
  return !e.isInjection && e.response.risk_score < QUARANTINE_THRESHOLD;
}

export function PayboxGauntlet() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [runningIndex, setRunningIndex] = useState(-1);

  const entryFor = (id: string) => entries.find((e) => e.id === id);

  const stopCount = entries.filter(stopped).length;
  const falsePositives = entries.filter(
    (e) => e.isInjection === false && e.response.risk_score >= QUARANTINE_THRESHOLD
  ).length;
  const protectedUsd = PAYBOX_SCENARIOS.filter(
    (s) => s.isInjection && entryFor(s.id) && stopped(entryFor(s.id)!)
  ).reduce((sum, s) => sum + (s.stakeUsd ?? 0), 0);
  const attacks = PAYBOX_SCENARIOS.filter((s) => s.isInjection).length;

  async function runAll() {
    setPhase("running");
    setEntries([]);
    const collected: Entry[] = [];
    for (let i = 0; i < PAYBOX_SCENARIOS.length; i++) {
      const s = PAYBOX_SCENARIOS[i];
      setRunningIndex(i);
      const response = await scanContent({
        content: s.content,
        content_type: s.content_type,
      });
      if (isError(response)) {
        setPhase("error");
        setRunningIndex(-1);
        return;
      }
      collected.push({ id: s.id, isInjection: s.isInjection, response });
      setEntries([...collected]);
      if (i < PAYBOX_SCENARIOS.length - 1) {
        await new Promise((r) => setTimeout(r, STAGGER_MS));
      }
    }
    setRunningIndex(-1);
    setPhase("done");
  }

  return (
    <div className="space-y-8">
      {/* Hero — the mandate gap in two lines */}
      <div className="page-enter space-y-3">
        <p className="text-[11px] font-mono uppercase tracking-widest text-violet">
          MoonPay Hackathons · Chapter 1
        </p>
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
          The PayBox Gauntlet
        </h1>
        <p className="text-base text-ink-muted leading-relaxed max-w-2xl">
          PayBox scopes what an agent may <span className="text-ink font-semibold">spend</span>.
          Elcaro scopes what it may <span className="text-ink font-semibold">believe</span>.
          Six scenarios — one per rubric category — where a single injected
          paragraph steers a real PayBox tool toward the vault. One click
          fires them all at the live engine.
        </p>
        <p className="text-xs text-ink-faint font-mono">
          Paid lane: POST /api/x402/scan — x402 &quot;exact&quot;, Base + Base Sepolia.
          This page runs the same verdict on the free path.
        </p>
      </div>

      {/* Scoreboard */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px rounded-2xl border border-border bg-border overflow-hidden">
        {[
          { label: "attacks stopped", value: `${stopCount}/${attacks}` },
          {
            label: "protected",
            value: protectedUsd > 0 ? `$${protectedUsd.toLocaleString()}` : "—",
          },
          { label: "false positives", value: `${falsePositives}` },
          {
            label: "paid calls via vault",
            value: entries.length > 0 ? `${entries.length}` : "0",
          },
        ].map((stat) => (
          <div key={stat.label} className="bg-surface px-4 py-3">
            <div className="text-xl font-black tracking-tight tabular-nums">
              {stat.value}
            </div>
            <div className="text-[10px] uppercase tracking-widest text-ink-faint">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Run control */}
      <div className="flex items-center gap-4 flex-wrap">
        {phase !== "running" ? (
          <motion.button
            onClick={runAll}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 transition-colors"
            whileTap={{ opacity: 0.9 }}
          >
            {phase === "done" ? "Run the gauntlet again" : "Run the gauntlet"}
            <span>→</span>
          </motion.button>
        ) : (
          <div className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold">
            <motion.span
              className="w-3 h-3 rounded-full border-2 border-canvas/40 border-t-canvas"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.6, repeat: Infinity, ease: "linear" }}
            />
            Scenario {runningIndex + 1}/{PAYBOX_SCENARIOS.length}
          </div>
        )}
        {phase === "error" && (
          <p className="text-sm text-dangerous">
            The scanner is unreachable right now — try again in a moment.
          </p>
        )}
        {phase === "done" && (
          <p className="text-xs text-ink-faint font-mono">
            every gate = a paid call through a PayBox wallet — safety that
            compounds into marketplace volume
          </p>
        )}
      </div>

      {/* Scenario cards */}
      <div className="space-y-4">
        {PAYBOX_SCENARIOS.map((s, i) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            entry={entryFor(s.id)}
            isRunning={runningIndex === i}
          />
        ))}
      </div>
    </div>
  );
}

function ScenarioCard({
  scenario: s,
  entry,
  isRunning,
}: {
  scenario: PayboxScenario;
  entry?: Entry;
  isRunning: boolean;
}) {
  const stoppedAttack = entry ? stopped(entry) : false;
  const cleanPass = entry ? passed(entry) : false;
  const color = entry
    ? LEVEL_COLORS[entry.response.risk_level] ?? "#A3A3A0"
    : "#A3A3A0";

  return (
    <motion.section
      layout
      transition={{ ease: EASE_OUT, duration: 0.3 }}
      className="rounded-2xl border border-border bg-surface overflow-hidden"
      style={{ opacity: entry || isRunning ? 1 : 0.7 }}
    >
      {/* Header — category, stakes, the tool on the line */}
      <div className="px-5 py-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-border">
        <span className="text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded bg-canvas border border-border text-ink-muted">
          {s.category}
        </span>
        <h2 className="text-base font-bold tracking-tight">{s.title}</h2>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-violet/10 text-violet border border-violet/20">
            {s.gatedTool}
          </span>
          <span className="text-[10px] font-mono text-ink-faint">
            {s.stakeLabel}
          </span>
          {entry && (
            <span
              className="text-xs font-black px-2 py-1 rounded"
              style={{ color }}
            >
              {stoppedAttack ? "STOP" : cleanPass ? "GO" : entry.response.risk_level.toUpperCase()}
            </span>
          )}
          {isRunning && (
            <motion.span
              className="text-xs text-ink-faint font-mono"
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1.1, repeat: Infinity }}
            >
              scanning…
            </motion.span>
          )}
        </div>
      </div>

      <div className="px-5 py-4 grid gap-4 md:grid-cols-2">
        {/* Left — the setup + the content the agent retrieved */}
        <div className="space-y-3 min-w-0">
          <p className="text-sm text-ink-muted leading-relaxed">
            <span className="text-ink font-medium">Task:</span> {s.setup}
          </p>
          <div className="rounded-xl bg-canvas border border-border p-4 max-h-56 overflow-y-auto">
            {entry ? (
              <InlineHighlight
                content={s.content}
                indicators={entry.response.indicators}
              />
            ) : (
              <pre className="text-xs font-mono text-ink-faint whitespace-pre-wrap leading-relaxed">
                {s.content}
              </pre>
            )}
          </div>
        </div>

        {/* Right — counterfactual vs what the gate did */}
        <div className="space-y-3 min-w-0">
          <div className="rounded-xl border border-dangerous/25 bg-dangerous/5 px-4 py-3">
            <p className="text-[10px] uppercase tracking-widest text-dangerous font-mono mb-1">
              without the gate
            </p>
            <p className="text-sm text-ink-muted leading-relaxed">
              {s.counterfactual}
            </p>
          </div>
          <AnimatePresence>
            {entry && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ease: EASE_OUT, duration: 0.3 }}
                className="rounded-xl border border-border bg-canvas px-4 py-3"
              >
                <p className="text-[10px] uppercase tracking-widest font-mono mb-1" style={{ color }}>
                  with elcaro — {entry.response.risk_level} ·{" "}
                  {entry.response.risk_score.toFixed(2)}
                  {entry.response.latency_ms != null &&
                    ` · ${entry.response.latency_ms}ms`}
                </p>
                <p className="text-sm text-ink leading-relaxed">
                  {stoppedAttack
                    ? `${s.gatedTool} never fired — ${s.stakeLabel} stayed in the vault, and the grant can be tightened before the next read.`
                    : cleanPass
                      ? `${s.gatedTool} proceeds — a gate that blocks everything protects nothing.`
                      : entry.response.summary}
                </p>
                {entry.response.canary_hits != null &&
                  entry.response.canary_hits.length > 0 && (
                    <p className="mt-2 text-[11px] font-mono text-violet">
                      canary hit — exfil provenance resolvable via /canary
                    </p>
                  )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.section>
  );
}
