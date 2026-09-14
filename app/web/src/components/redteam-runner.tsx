"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { QUARANTINE_THRESHOLD } from "@/lib/history";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;
const FEED_LIMIT = 120;

const LEVEL_COLORS: Record<string, string> = {
  safe: "#3D8B5F",
  low: "#7A8C2E",
  suspicious: "#D4860A",
  dangerous: "#E5533D",
};

// One line per record streamed from GET /api/redteam/run — the journal
// contract in redteam/journal.py.
interface RunRecord {
  kind: "run_start" | "run_end" | "scan" | "trophy" | "execution" | string;
  ts?: number;
  gen?: number;
  id?: string;
  seed_id?: string;
  ops?: string[];
  content_type?: string;
  content?: string;
  risk_score?: number;
  risk_level?: string;
  quarantined?: boolean;
  flagged_techniques?: string[];
  canary_intact?: boolean;
  bypass?: boolean;
  scans?: number;
  trophies?: number;
}

function trophyKey(r: RunRecord): string {
  return `${r.seed_id}|${(r.ops ?? []).join("/")}|${r.content_type}`;
}

function OpChip({ op }: { op: string }) {
  return (
    <span className="px-1.5 py-0.5 rounded bg-ink/[0.06] text-ink-muted font-mono text-[10px] leading-none whitespace-nowrap">
      {op}
    </span>
  );
}

function ScoreChip({ score, bypass }: { score: number; bypass?: boolean }) {
  const caught = score >= QUARANTINE_THRESHOLD;
  return (
    <span
      className="px-2 py-0.5 rounded-md font-mono text-xs font-bold tabular-nums"
      style={{
        color: caught ? LEVEL_COLORS.dangerous : LEVEL_COLORS.safe,
        backgroundColor: caught ? "#E5533D14" : "#3D8B5F14",
      }}
    >
      {score.toFixed(2)}
      {bypass ? " BYPASS" : ""}
    </span>
  );
}

export function RedteamRunner() {
  const reduced = useReducedMotion();
  const [phase, setPhase] = useState<"idle" | "running" | "done" | "error">("idle");
  const [mode, setMode] = useState<"vulnerable" | "hardened">("vulnerable");
  const [execute, setExecute] = useState(false);
  const [oracle, setOracle] = useState<string | null>(null);
  const [feed, setFeed] = useState<RunRecord[]>([]);
  const [trophies, setTrophies] = useState<Map<string, RunRecord>>(new Map());
  const [executions, setExecutions] = useState<RunRecord[]>([]);
  const [stats, setStats] = useState({ scans: 0, budget: 0 });
  const [expanded, setExpanded] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => esRef.current?.close(), []);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ block: "nearest" });
  }, [feed]);

  function run() {
    esRef.current?.close();
    setFeed([]);
    setTrophies(new Map());
    setExecutions([]);
    setStats({ scans: 0, budget: 0 });
    setExpanded(null);
    setOracle(null);
    setPhase("running");

    const params = new URLSearchParams({ budget: "150" });
    if (mode === "vulnerable") params.set("baseline", "vulnerable");
    if (execute) params.set("execute", "true");
    const es = new EventSource(`/api/redteam/run?${params}`);
    esRef.current = es;

    es.onmessage = (evt) => {
      let rec: RunRecord;
      try {
        rec = JSON.parse(evt.data);
      } catch {
        return;
      }
      if (rec.kind === "run_start") {
        const r = rec as { budget?: number; oracle?: string };
        setStats((s) => ({ ...s, budget: r.budget ?? 0 }));
        setOracle(r.oracle ?? null);
        return;
      }
      if (rec.kind === "run_end") {
        setPhase("done");
        es.close();
        return;
      }
      if (rec.kind === "execution") {
        setExecutions((e) => [...e, rec]);
        return;
      }
      if (rec.kind === "scan" || rec.kind === "trophy") {
        setStats((s) => ({ ...s, scans: s.scans + 1 }));
        setFeed((f) => [...f.slice(-(FEED_LIMIT - 1)), rec]);
        if (rec.kind === "trophy") {
          setTrophies((t) => {
            const next = new Map(t);
            next.set(trophyKey(rec), rec);
            return next;
          });
        }
      }
    };

    es.onerror = () => {
      es.close();
      setPhase((p) => (p === "running" ? "error" : p));
    };
  }

  const trophyList = [...trophies.values()];
  const lowest = feed.reduce(
    (m, r) => (r.risk_score !== undefined && r.risk_score < m ? r.risk_score : m),
    1
  );

  return (
    <div className="space-y-8">
      {/* Intro */}
      <div className="page-enter space-y-3">
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
          The red team
        </h1>
        <p className="text-base text-ink-muted leading-relaxed max-w-xl">
          Elcaro attacks itself. An evolutionary searcher mutates the shipped
          attack corpus — obfuscation, encoding, delimiter and type tricks —
          and fires every candidate at the live engine. Anything that scores
          under the quarantine line with its payload intact lands in the
          trophy case.
        </p>
      </div>

      {/* Run control */}
      <div className="space-y-3">
        {/* Target selector — the before/after arc: the same searcher hits
            either the pre-hardening engine semantics or the live one */}
        <div className="inline-flex rounded-xl border border-border overflow-hidden text-sm">
          {(
            [
              { key: "vulnerable", label: "Vulnerable baseline" },
              { key: "hardened", label: "Hardened engine" },
            ] as const
          ).map((m) => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              disabled={phase === "running"}
              className={`px-4 py-2 font-semibold transition-colors ${
                mode === m.key
                  ? "bg-ink text-canvas"
                  : "bg-surface text-ink-muted hover:text-ink"
              } disabled:opacity-50`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          {phase !== "running" ? (
            <motion.button
              onClick={run}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors"
              whileTap={{ opacity: 0.9 }}
            >
              {phase === "done" ? "Attack again" : "Attack the engine"}
              <span>→</span>
            </motion.button>
          ) : (
            <div className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold">
              <motion.span
                className="w-3 h-3 rounded-full border-2 border-canvas/40 border-t-canvas"
                animate={{ rotate: 360 }}
                transition={{ duration: 0.6, repeat: Infinity, ease: "linear" }}
              />
              Searching — {stats.scans}
              {stats.budget ? `/${stats.budget}` : ""} candidates
            </div>
          )}

          <label className="inline-flex items-center gap-2 text-xs text-ink-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={execute}
              onChange={(e) => setExecute(e.target.checked)}
              disabled={phase === "running"}
              className="accent-ink"
            />
            test agent compliance on bypasses
          </label>

          {oracle && (
            <span className="text-xs text-ink-muted">
              target:{" "}
              {oracle === "BaselineOracle"
                ? "pre-hardening engine (before today's fixes)"
                : "live hardened engine"}
            </span>
          )}

          {phase === "error" && (
            <p className="text-sm text-dangerous">
              The scanner is unreachable right now — try again in a moment.
            </p>
          )}
        </div>
      </div>

      {/* Stats strip */}
      {feed.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Candidates scanned", value: String(stats.scans) },
            {
              label: "Bypasses found",
              value: String(trophyList.length),
              accent: trophyList.length > 0,
            },
            {
              label: "Lowest score seen",
              value: feed.length ? lowest.toFixed(2) : "—",
            },
          ].map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-border bg-surface px-4 py-3"
            >
              <div
                className="text-2xl font-black tabular-nums"
                style={s.accent ? { color: LEVEL_COLORS.dangerous } : undefined}
              >
                {s.value}
              </div>
              <div className="text-xs text-ink-muted mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Trophy case */}
      <AnimatePresence>
        {trophyList.length > 0 && (
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE_OUT }}
            className="rounded-2xl border border-dangerous/30 bg-surface overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h2 className="text-sm font-bold text-dangerous">
                Trophy case — confirmed bypasses
              </h2>
              <span className="text-xs text-ink-muted">
                score &lt; {QUARANTINE_THRESHOLD}, payload intact
              </span>
            </div>
            <div className="divide-y divide-border">
              {trophyList.map((t) => {
                const key = trophyKey(t);
                const open = expanded === key;
                return (
                  <button
                    key={key}
                    onClick={() => setExpanded(open ? null : key)}
                    className="w-full text-left px-4 py-3 hover:bg-ink/[0.02] transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-wrap">
                      <ScoreChip score={t.risk_score ?? 0} bypass />
                      <span className="text-xs font-mono text-ink-muted">
                        {t.seed_id} · {t.content_type}
                      </span>
                      <span className="flex gap-1 flex-wrap">
                        {(t.ops ?? []).map((op, i) => (
                          <OpChip key={`${op}-${i}`} op={op} />
                        ))}
                      </span>
                    </div>
                    {open && t.content && (
                      <pre className="mt-3 p-3 rounded-lg bg-ink/[0.04] text-xs text-ink-muted font-mono whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                        {t.content}
                      </pre>
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Executions — Tier-2: did an agent actually comply? */}
      <AnimatePresence>
        {executions.length > 0 && (
          <motion.div
            initial={reduced ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: EASE_OUT }}
            className="rounded-2xl border border-border bg-surface overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-bold">Agent compliance check</h2>
            </div>
            <div className="divide-y divide-border">
              {executions.map((e) => {
                const complied = (e as { complied?: boolean }).complied;
                const detail = (e as { detail?: string }).detail;
                const excerpt = (e as { response_excerpt?: string })
                  .response_excerpt;
                return (
                  <div key={e.id ?? e.ts} className="px-4 py-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      {complied ? (
                        <span className="px-2 py-0.5 rounded-md text-xs font-black text-canvas" style={{ backgroundColor: LEVEL_COLORS.dangerous }}>
                          AGENT COMPLIED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-md bg-ink/[0.06] text-ink-muted text-xs font-semibold">
                          {detail === "llm_unconfigured" ? "no LLM configured" : "no compliance"}
                        </span>
                      )}
                      <span className="font-mono text-xs text-ink-muted">
                        {e.seed_id}
                      </span>
                      <span className="flex gap-1 flex-wrap">
                        {(e.ops ?? []).map((op, i) => (
                          <OpChip key={`${op}-${i}`} op={op} />
                        ))}
                      </span>
                    </div>
                    {excerpt && (
                      <p className="mt-2 text-xs text-ink-muted italic leading-relaxed line-clamp-3">
                        “{excerpt}”
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Live feed */}
      {feed.length > 0 && (
        <div className="rounded-2xl border border-border bg-surface overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <h2 className="text-sm font-bold">Candidate stream</h2>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-border">
            {[...feed].reverse().map((r) => (
              <div
                key={r.id}
                className="flex items-center gap-3 px-4 py-2 text-xs"
              >
                <ScoreChip score={r.risk_score ?? 0} bypass={r.bypass} />
                <span className="font-mono text-ink-muted shrink-0">
                  {r.seed_id}
                </span>
                <span className="flex gap-1 flex-wrap min-w-0">
                  {(r.ops ?? []).map((op, i) => (
                    <OpChip key={`${op}-${i}`} op={op} />
                  ))}
                </span>
                <span className="ml-auto text-ink-muted/60 shrink-0">
                  {r.content_type}
                </span>
              </div>
            ))}
            <div ref={feedEndRef} />
          </div>
        </div>
      )}

      {/* Closing line */}
      {phase === "done" && (
        <p className="text-sm text-ink-muted leading-relaxed max-w-xl">
          {trophyList.length === 0
            ? "No bypasses this run — every mutation was caught. The structural evasion classes (encoding, homoglyphs, token splitting, type arbitrage) are closed by the normalization layer; what survives is semantic indirection."
            : `${trophyList.length} bypass${
                trophyList.length === 1 ? "" : "es"
              } against the ${
                oracle === "BaselineOracle" ? "pre-hardening" : "live"
              } engine. Flip to “Hardened engine” and run again — the same
              searcher, the fixes live.`}
        </p>
      )}
    </div>
  );
}
