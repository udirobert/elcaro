"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { ScanResponse } from "@/lib/types";
import {
  WORKSHOP_CASES,
  type WorkshopCase,
} from "@/lib/tangem-casebook";
import { TangemDiscoveryStage } from "./tangem-discovery-stage";
import styles from "./tangem-stage.module.css";

type VerdictState = "none" | "held" | "allowed" | "review" | "failed";

function verdictState(
  verdict: ScanResponse | null,
  error: string | null
): VerdictState {
  if (error) return "failed";
  if (!verdict) return "none";
  if (verdict.quarantined === true) return "held";
  if (verdict.quarantined === false && verdict.risk_level === "safe") {
    return "allowed";
  }
  return "review";
}

const HEADLINE: Record<VerdictState, string> = {
  none: "Who gave the instruction?",
  held: "Source quarantined.",
  allowed: "Allowed by scan.",
  review: "Verdict needs review.",
  failed: "Scan did not complete.",
};

const STEP: Record<VerdictState, (clean: boolean, tell: string) => string> = {
  none: (clean, tell) =>
    clean
      ? "2 of 3 · Scan the clean version — same check, without the extra instruction."
      : `1 of 3 · Scan the marked version — did the user ask for ${tell}, or did the document?`,
  held: () =>
    "2 of 3 · Compare the clean version — only the planted line changes.",
  allowed: () =>
    "3 of 3 · Where Tangem MCP fits — the paired terminal asks tools/list; this page never connects a wallet.",
  review: () => "Ambiguous result — the demo stops here rather than forward.",
  failed: () => "The scan did not return — nothing was forwarded.",
};

const LIVE_TEXT: Record<VerdictState, string> = {
  none: "No verdict yet.",
  held: "Verdict: the whole document is quarantined.",
  allowed: "Verdict: scanned clean and allowed.",
  review: "Verdict: ambiguous — needs review.",
  failed: "The scan did not complete.",
};

// Faithful preview of the submitted note — entire content, newlines and JSON
// braces preserved. The canary substring is highlighted only by exact match;
// nothing about the scan is fabricated here.
function NotePreview({
  note,
  tell,
}: {
  note: string;
  tell: string;
}) {
  const idx = note.indexOf(tell);
  if (idx === -1) {
    return (
      <p className="font-mono text-xs sm:text-sm text-[#2a2417] leading-relaxed whitespace-pre-wrap break-words">
        {note}
      </p>
    );
  }
  return (
    <p className="font-mono text-xs sm:text-sm text-[#2a2417] leading-relaxed whitespace-pre-wrap break-words">
      {note.slice(0, idx)}
      <mark className="font-black underline decoration-[#c53f2a] decoration-2 underline-offset-2 bg-transparent text-[#2a2417]">
        {tell}
      </mark>
      {note.slice(idx + tell.length)}
    </p>
  );
}

export function TangemCutaway({
  note,
  clean,
  scanning,
  verdict,
  error,
  caseDef,
  activeCaseId,
  onScan,
  onSwitch,
  onSelectCase,
}: {
  note: string;
  clean: boolean;
  scanning: boolean;
  verdict: ScanResponse | null;
  error: string | null;
  caseDef: WorkshopCase;
  activeCaseId: string;
  onScan: () => void;
  onSwitch: () => void;
  onSelectCase: (id: string) => void;
}) {
  // The opening vignette is the first screen for this specimen. It is closed
  // by Inspect (never scans) and can be re-opened after a real verdict via
  // "Replay scenario" — an explicit local toggle that never discards the
  // genuine result; closing the replay returns to it.
  const [showStory, setShowStory] = useState(true);
  const [replaying, setReplaying] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [canFullscreen, setCanFullscreen] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const evidenceTitleRef = useRef<HTMLHeadingElement>(null);

  const storyVisible =
    showStory && !scanning && !error && (!verdict || replaying);

  useEffect(() => {
    if (!storyVisible) {
      evidenceTitleRef.current?.focus();
    }
  }, [storyVisible]);

  useEffect(() => {
    setCanFullscreen(
      Boolean(document.fullscreenEnabled) &&
        typeof sectionRef.current?.requestFullscreen === "function"
    );
    const sync = () =>
      setFullscreen(document.fullscreenElement === sectionRef.current);
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  function inspect() {
    setShowStory(false);
    setReplaying(false);
  }

  function selectCase(id: string) {
    if (id === activeCaseId || scanning) return;
    // back to the story preview first — the parent then swaps the specimen
    setShowStory(true);
    setReplaying(false);
    onSelectCase(id);
  }

  function toggleFullscreen() {
    if (document.fullscreenElement === sectionRef.current) {
      Promise.resolve(document.exitFullscreen()).catch(() => {});
    } else {
      // a rejection just leaves the inline plate in place — still usable
      Promise.resolve(sectionRef.current?.requestFullscreen?.()).catch(
        () => {}
      );
    }
  }

  const state = verdictState(verdict, error);
  const held = state === "held";

  return (
    <section
      ref={sectionRef}
      aria-label="Workshop case walkthrough"
      className={`${styles.present} relative rounded-2xl border border-border bg-surface px-5 py-5 sm:px-7 sm:py-6 space-y-5 overflow-hidden`}
    >
      <div className={styles.presentInner ?? ""}>
        {/* Case chooser — mounted once for both story and evidence so the
            section never remounts (fullscreen survives the switch). */}
        <div
          role="group"
          aria-label="Workshop cases"
          className="flex flex-wrap items-center gap-2 pb-1"
        >
          {WORKSHOP_CASES.map((c, i) => (
            <button
              key={c.id}
              aria-pressed={activeCaseId === c.id}
              disabled={scanning}
              onClick={() => selectCase(c.id)}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors disabled:opacity-50 ${
                activeCaseId === c.id
                  ? "border-ink bg-ink text-canvas"
                  : "border-border bg-surface text-ink-muted hover:border-ink/40 hover:text-ink"
              }`}
            >
              {`0${i + 1} · ${c.label}`}
            </button>
          ))}
        </div>

        {storyVisible ? (
          <TangemDiscoveryStage caseDef={caseDef} onInspect={inspect} />
        ) : (
          <div className={`${styles.paper} px-5 py-5 sm:px-8 sm:py-6 space-y-5`}>
            {/* registration corners — instrument-plate framing */}
            <span aria-hidden className={`${styles.regCorner} ${styles.tl}`} />
            <span aria-hidden className={`${styles.regCorner} ${styles.tr}`} />
            <span aria-hidden className={`${styles.regCorner} ${styles.bl}`} />
            <span aria-hidden className={`${styles.regCorner} ${styles.br}`} />

            <div className="space-y-1.5">
              <p className="text-[10px] uppercase tracking-[0.2em] text-[#8a7a55]">
                02 / Evidence &nbsp;·&nbsp; Live test · harmless stand-in
              </p>
              <h2
                ref={evidenceTitleRef}
                tabIndex={-1}
                className="text-[28px] sm:text-[40px] font-black tracking-tight leading-none focus:outline-none text-[#2a2417]"
              >
                {HEADLINE[state]}
              </h2>
              <p className="text-xs text-[#6b5d40] leading-relaxed">
                {scanning
                  ? "Scanning the document — same real check as the terminal."
                  : STEP[state](clean, caseDef.tell)}
              </p>
              <p className="sr-only" role="status" aria-live="polite">
                {LIVE_TEXT[state]}
              </p>
            </div>

            {/* Specimen slip — the entire submitted document, verbatim; the
                opposing registration jaws close over it only on a real
                quarantine. */}
            <div className={styles.jawHost} data-verdict={state} style={{ position: "relative" }}>
              <div className={`${styles.slip} px-4 py-4`}>
                <NotePreview note={note} tell={caseDef.tell} />
                {/* Reserved footer band — the stamp lives here, in flow, so
                    it can never cover the specimen text. Rendered only for
                    an actual held/allowed response. */}
                <div className={styles.stampBand}>
                  {(state === "held" || state === "allowed") && (
                    <span aria-hidden className={styles.stamp}>
                      {held ? "QUARANTINED" : "SCANNED CLEAN"}
                    </span>
                  )}
                </div>
              </div>
              <span aria-hidden className={styles.jawTop} />
              <span aria-hidden className={styles.jawBottom} />
            </div>

            {/* Downstream lane — deliberately empty. The browser demo never
                sends anything onward; the paired terminal is the only path. */}
            <div className="rounded-lg border border-dashed border-[#b7a884] px-4 py-3 space-y-1">
              <p className="text-[10px] uppercase tracking-wide text-[#8a7a55]">
                Tangem wallet · Not paired
              </p>
              <p className="text-xs text-[#6b5d40] leading-relaxed">
                Paired terminal only: tools/list → descriptions → Elcaro scan.
                No tool is executed.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={onScan}
                disabled={scanning}
                className="rounded-lg bg-[#2a2417] text-[#fbf8f1] text-sm font-semibold px-5 py-2.5 hover:bg-[#3d3423] transition-colors disabled:opacity-50"
              >
                {scanning ? "Scanning…" : "Scan"}
              </button>
              <button
                onClick={onSwitch}
                disabled={scanning}
                className="text-[#0d9488] text-sm font-medium hover:text-[#14b8a6]/80 transition-colors disabled:opacity-50"
              >
                {clean ? "Load marked version" : caseDef.cleanLabel}
              </button>
              {(state === "held" || state === "allowed") && (
                <Link
                  href="/integrate#mcp-tool-results"
                  className="text-[#0d9488] text-sm font-medium hover:text-[#14b8a6]/80 transition-colors"
                >
                  Use this check in your agent →
                </Link>
              )}
              {verdict && (
                <button
                  onClick={() => {
                    setReplaying(true);
                    setShowStory(true);
                  }}
                  disabled={scanning}
                  className="text-[#8a7a55] text-xs font-medium hover:text-[#2a2417] transition-colors disabled:opacity-50"
                >
                  Replay scenario
                </button>
              )}
            </div>
          </div>
        )}
      </div>
      {canFullscreen && (
        <button
          onClick={toggleFullscreen}
          className="absolute top-3 right-3 text-[10px] uppercase tracking-wide text-ink-faint hover:text-ink transition-colors"
        >
          {fullscreen ? "Exit presentation" : "Present"}
        </button>
      )}
    </section>
  );
}
