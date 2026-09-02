"use client";

import { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { scanContent, isError } from "@/lib/api";
import type { ScanResponse } from "@/lib/types";
import { GAUNTLET_PAYLOADS } from "@/lib/gauntlet";
import { markGauntletRun } from "@/lib/journey";
import { QUARANTINE_THRESHOLD } from "@/lib/history";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;
const SPRING = { type: "spring", stiffness: 400, damping: 30 } as const;

type Phase = "idle" | "running" | "done" | "error";

// Volley pacing — each verdict lands before the next payload fires.
const STAGGER_MS = 200;

const LEVEL_COLORS: Record<string, string> = {
  safe: "#1A8A7A",
  low: "#2563EB",
  suspicious: "#D4860A",
  dangerous: "#E5533D",
};

interface GauntletEntry {
  id: string;
  isInjection: boolean;
  response: ScanResponse;
}

export function GauntletRunner() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [entries, setEntries] = useState<GauntletEntry[]>([]);
  const [runningIndex, setRunningIndex] = useState(-1);
  const [copied, setCopied] = useState(false);

  const injections = GAUNTLET_PAYLOADS.filter((p) => p.isInjection);
  const cleans = GAUNTLET_PAYLOADS.filter((p) => !p.isInjection);

  const caught = entries.filter(
    (e) => e.isInjection && e.response.risk_score >= QUARANTINE_THRESHOLD
  ).length;
  const falsePositives = entries.filter(
    (e) => !e.isInjection && e.response.risk_score >= QUARANTINE_THRESHOLD
  ).length;
  const latencies = entries
    .map((e) => e.response.latency_ms ?? 0)
    .filter((n) => n > 0)
    .sort((a, b) => a - b);
  const medianMs = latencies.length
    ? latencies[Math.floor(latencies.length / 2)]
    : 0;

  async function runGauntlet() {
    setPhase("running");
    setEntries([]);
    const collected: GauntletEntry[] = [];

    for (let i = 0; i < GAUNTLET_PAYLOADS.length; i++) {
      const payload = GAUNTLET_PAYLOADS[i];
      setRunningIndex(i);

      const response = await scanContent({
        content: payload.content,
        content_type: payload.content_type,
      });

      if (isError(response)) {
        setPhase("error");
        setRunningIndex(-1);
        return;
      }

      collected.push({
        id: payload.id,
        isInjection: payload.isInjection,
        response,
      });
      setEntries([...collected]);

      if (i < GAUNTLET_PAYLOADS.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, STAGGER_MS));
      }
    }

    setRunningIndex(-1);
    setPhase("done");
    // Mark the journey so the homepage closing CTA adapts to suggest scanning
    // the visitor's own content next, rather than re-pitching the Gauntlet.
    markGauntletRun();
  }

  function verdictText(): string {
    return (
      `Elcaro caught ${caught}/${injections.length} classes of indirect prompt injection` +
      (falsePositives === 0
        ? " with zero false positives"
        : ` (${falsePositives} clean item${
            falsePositives === 1 ? "" : "s"
          } flagged)`) +
      ` — median ${
        medianMs > 0 ? `${medianMs}ms` : "sub-millisecond"
      } latency. Can your agent's defenses?`
    );
  }

  async function handleShare() {
    const url = `${window.location.origin}/gauntlet`;
    const text = `${verdictText()} ${url}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "The Elcaro Gauntlet", text, url });
      } else {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Share sheet dismissed — no-op
    }
  }

  return (
    <div className="space-y-8">
      {/* Intro */}
      <div className="space-y-3">
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
          The Gauntlet
        </h1>
        <p className="text-base text-ink-muted leading-relaxed max-w-xl">
          Eight payloads — one per class of indirect prompt injection, plus two
          clean controls — fired at the live engine. No pasting, no setup: one
          click, and you watch every verdict land.
        </p>
      </div>

      {/* Run control */}
      <div className="flex items-center gap-4 flex-wrap">
        {phase !== "running" ? (
          <motion.button
            onClick={runGauntlet}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors"
            whileTap={{ opacity: 0.9 }}
          >
            {phase === "done" ? "Run the Gauntlet again" : "Run the Gauntlet"}
            <span>→</span>
          </motion.button>
        ) : (
          <div className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold">
            <motion.span
              className="w-3 h-3 rounded-full border-2 border-canvas/40 border-t-canvas"
              animate={{ rotate: 360 }}
              transition={{ duration: 0.6, repeat: Infinity, ease: "linear" }}
            />
            Firing payload {runningIndex + 1}/{GAUNTLET_PAYLOADS.length}
          </div>
        )}

        {phase === "error" && (
          <p className="text-sm text-dangerous">
            The scanner is unreachable right now — try again in a moment.
          </p>
        )}
      </div>

      {/* Specimen stage — the payload on trial, presented large */}
      <SpecimenStage entries={entries} phase={phase} runningIndex={runningIndex} />

      {/* Ledger — the at-a-glance verdict summary */}
      <div className="rounded-2xl border border-border bg-surface divide-y divide-border overflow-hidden">
        {GAUNTLET_PAYLOADS.map((payload, i) => {
          const entry = entries.find((e) => e.id === payload.id);
          const isRunning = runningIndex === i;
          const correct = entry
            ? entry.isInjection
              ? entry.response.risk_score >= QUARANTINE_THRESHOLD
              : entry.response.risk_score < QUARANTINE_THRESHOLD
            : false;

          return (
            <div
              key={payload.id}
              className="flex items-center gap-3 px-4 py-3"
              style={{ opacity: entry || isRunning ? 1 : 0.55 }}
            >
              {/* Letter */}
              <span
                className="text-lg font-black w-6 shrink-0 text-center"
                style={{
                  color: entry
                    ? LEVEL_COLORS[entry.response.risk_level] ?? "#A3A3A0"
                    : "#A3A3A0",
                }}
              >
                {payload.letter}
              </span>

              {/* Label + note */}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-ink">
                  {payload.label}
                </span>
                <span className="hidden sm:inline text-xs text-ink-faint ml-2">
                  — {payload.note}
                </span>
                <span className="hidden sm:inline-block text-[10px] font-mono text-ink-faint ml-2 px-1.5 py-0.5 rounded bg-canvas border border-border">
                  {payload.content_type.replace("_", " ")}
                </span>
              </div>

              {/* Verdict */}
              <div className="flex items-center gap-2.5 shrink-0">
                {isRunning && (
                  <motion.span
                    className="text-xs text-ink-faint font-mono"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                  >
                    scanning…
                  </motion.span>
                )}
                {entry && (
                  <>
                    <span
                      className="text-xs font-mono"
                      style={{
                        color: LEVEL_COLORS[entry.response.risk_level],
                      }}
                    >
                      {entry.response.risk_score.toFixed(2)}{" "}
                      {entry.response.risk_level}
                    </span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: correct ? "#1A8A7A" : "#E5533D" }}
                    >
                      {correct ? "✓" : "✗"}
                    </span>
                  </>
                )}
                {!entry && !isRunning && (
                  <span className="text-xs text-ink-faint font-mono">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Honesty footnote — the Gauntlet's credibility is the point */}
      <p className="text-xs text-ink-faint leading-relaxed max-w-xl">
        Payloads are drawn from the engine&apos;s public test suite and run
        against the live production miner — if a detection misses, the
        scorecard shows it.
      </p>

      {/* Scorecard — designed to be the screenshot */}
      <AnimatePresence>
        {phase === "done" && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, ease: EASE_OUT }}
            className="rounded-2xl border border-border bg-surface px-6 py-10 text-center space-y-6"
          >
            <p className="text-xs text-ink-faint uppercase tracking-widest">
              Gauntlet scorecard
            </p>

            <div className="flex items-baseline justify-center gap-8 sm:gap-14 flex-wrap">
              <div>
                <p className="text-4xl sm:text-5xl font-black tracking-tight text-ink">
                  {caught}
                  <span className="text-2xl text-ink-faint">
                    /{injections.length}
                  </span>
                </p>
                <p className="text-xs text-ink-faint mt-1.5">
                  injections caught
                </p>
              </div>
              <div>
                <p className="text-4xl sm:text-5xl font-black tracking-tight text-ink">
                  {falsePositives}
                  <span className="text-2xl text-ink-faint">
                    /{cleans.length}
                  </span>
                </p>
                <p className="text-xs text-ink-faint mt-1.5">clean flagged</p>
              </div>
              <div>
                <p className="text-4xl sm:text-5xl font-black tracking-tight text-ink">
                  {medianMs > 0 ? (
                    <>
                      {medianMs}
                      <span className="text-2xl text-ink-faint">ms</span>
                    </>
                  ) : (
                    "<1ms"
                  )}
                </p>
                <p className="text-xs text-ink-faint mt-1.5">median latency</p>
              </div>
            </div>

            <p className="text-sm text-ink-muted max-w-md mx-auto leading-relaxed">
              &ldquo;{verdictText()}&rdquo;
            </p>

            <div className="flex items-center justify-center gap-3 flex-wrap">
              <button
                onClick={handleShare}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors"
              >
                {copied ? "✓ Copied" : "Share this result"}
              </button>
              <Link
                href="/scan"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border text-sm font-semibold text-ink-muted hover:text-ink hover:border-border-strong transition-colors"
              >
                Scan your own content
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Specimen stage ─────────────────────────────────────────────────────────────
//
// The payload on trial, presented large: a dimensional card that enters with a
// tilt, gets struck through and stamped QUARANTINED when caught (the UI
// performs the arrest), and recedes into a ghost stack as the next specimen
// comes forward. All framer-motion + CSS perspective — no WebGL, no new deps.

function SpecimenStage({
  entries,
  phase,
  runningIndex,
}: {
  entries: GauntletEntry[];
  phase: Phase;
  runningIndex: number;
}) {
  const reduceMotion = useReducedMotion();

  // The front card: the payload being fired, or the most recent verdict.
  const displayIndex =
    phase === "idle" ? 0 : runningIndex >= 0 ? runningIndex : entries.length - 1;
  const front =
    displayIndex >= 0 && displayIndex < GAUNTLET_PAYLOADS.length
      ? GAUNTLET_PAYLOADS[displayIndex]
      : null;
  const frontEntry = front
    ? entries.find((e) => e.id === front.id) ?? null
    : null;
  const isFrontRunning = phase === "running" && runningIndex === displayIndex;

  // Ghost stack: up to three completed specimens receding behind the front card.
  const ghostIds = new Set(
    entries.slice(0, Math.max(displayIndex, 0)).map((e) => e.id).slice(-3)
  );
  const ghosts = entries.filter((e) => ghostIds.has(e.id));

  const verdict: "caught" | "missed" | "clean" | "false-positive" | null =
    frontEntry
      ? frontEntry.isInjection
        ? frontEntry.response.risk_score >= QUARANTINE_THRESHOLD
          ? "caught"
          : "missed"
        : frontEntry.response.risk_score < QUARANTINE_THRESHOLD
          ? "clean"
          : "false-positive"
      : null;

  const STAMP_STYLES: Record<string, string> = {
    caught: "border-dangerous text-dangerous bg-dangerous-bg/90",
    missed: "border-suspicious text-suspicious bg-suspicious-bg/90",
    clean: "border-safe text-safe bg-safe-bg/90",
    "false-positive": "border-suspicious text-suspicious bg-suspicious-bg/90",
  };
  const STAMP_LABELS: Record<string, string> = {
    caught: "Quarantined",
    missed: "Missed",
    clean: "Clean",
    "false-positive": "Flagged",
  };

  return (
    <div
      className="relative h-64 sm:h-72"
      style={{ perspective: 1200 }}
      aria-live="polite"
    >
      {/* Ghost stack — completed specimens receding behind */}
      {ghosts.map((ghost, i) => {
        const depth = ghosts.length - i;
        return (
          <div
            key={ghost.id}
            className="absolute inset-0 rounded-2xl border border-border bg-surface"
            style={{
              transform: `translateY(${depth * 10}px) scale(${1 - depth * 0.04})`,
              opacity: Math.max(0.15, 0.45 - depth * 0.1),
            }}
          />
        );
      })}

      {/* Front specimen card */}
      <AnimatePresence mode="wait">
        {front && (
          <motion.div
            key={front.id}
            className="absolute inset-0 rounded-2xl border border-border bg-surface p-6 sm:p-8 flex flex-col overflow-hidden"
            style={{ transformPerspective: 1200 }}
            initial={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, rotateX: 14, y: 48, scale: 0.96 }
            }
            animate={
              reduceMotion
                ? { opacity: phase === "idle" ? 0.75 : 1 }
                : {
                    opacity: phase === "idle" ? 0.75 : 1,
                    rotateX: 0,
                    y: 0,
                    scale: 1,
                  }
            }
            exit={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, y: -24, scale: 0.97 }
            }
            transition={
              reduceMotion
                ? { duration: 0.15 }
                : { duration: 0.45, ease: EASE_OUT }
            }
          >
            {/* Specimen header */}
            <div className="flex items-center justify-between mb-4 shrink-0">
              <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                Specimen {front.letter} — {front.label}
              </p>
              <span className="text-[10px] font-mono text-ink-faint uppercase tracking-wide">
                {front.content_type.replace(/_/g, " ")}
              </span>
            </div>

            {/* The payload — struck through when caught */}
            <div className="flex-1 flex items-center min-h-0">
              <p
                className={`font-mono text-sm sm:text-base leading-relaxed whitespace-pre-wrap max-w-2xl ${
                  verdict === "caught"
                    ? "text-ink-muted line-through decoration-dangerous/60 decoration-2"
                    : "text-ink-muted"
                }`}
              >
                {front.content}
              </p>
            </div>

            {/* Scanning pulse while the payload is in flight */}
            {isFrontRunning && (
              <motion.div
                className="absolute inset-0 rounded-2xl border-2 border-ink/30 pointer-events-none"
                animate={{ opacity: [0.25, 0.7, 0.25] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              />
            )}

            {/* The stamp — the arrest, performed */}
            {verdict && (
              <motion.div
                className="absolute inset-0 flex items-center justify-center pointer-events-none"
                initial={
                  reduceMotion
                    ? { opacity: 0 }
                    : { opacity: 0, scale: 2, rotate: -16 }
                }
                animate={
                  reduceMotion
                    ? { opacity: 1 }
                    : { opacity: 1, scale: 1, rotate: -8 }
                }
                transition={reduceMotion ? { duration: 0.2 } : SPRING}
              >
                <span
                  className={`px-5 py-2 rounded-lg border-2 text-sm font-black uppercase tracking-[0.2em] ${STAMP_STYLES[verdict]}`}
                >
                  {STAMP_LABELS[verdict]}
                </span>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
