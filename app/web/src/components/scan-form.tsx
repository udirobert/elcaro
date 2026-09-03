"use client";

import { useState, useRef, useCallback, useEffect, useSyncExternalStore } from "react";
import { motion, AnimatePresence, useAnimation } from "framer-motion";
import type { ContentType, ScanResponse } from "@/lib/types";
import { scanContent, isError } from "@/lib/api";
import { CONTENT_TYPES, EXAMPLES } from "@/lib/constants";
import { addToHistory, getHistory } from "@/lib/history";
import { decodeVerdict } from "@/lib/share";
import { useWebMcpScan } from "@/lib/use-webmcp-scan";
import { buildIntentContrast, type IntentContrast } from "@/lib/webmcp-doctrine";
import { ScanResult } from "./scan-result";
import { IntentContrastPanel } from "./intent-contrast";
import {
  AgentSessionRail,
  WaitingForIntent,
  agentBeat,
} from "./agent-session";
import { ScanBeam } from "./scan-beam";
import { ScanHistory } from "./scan-history";
import { WebMcpDebug } from "./webmcp-debug";

// Motion tokens — consistent across the app
const SPRING = { type: "spring", stiffness: 400, damping: 30 } as const;
const EASE_OUT = [0.16, 1, 0.3, 1] as const;

// Rotating status lines while a scan runs — one per detector concern, so the
// wait reads as the six detector classes working (which is literally true).
const SCAN_STATUSES = [
  "Checking for forged authority…",
  "Watching context boundaries…",
  "Decoding obfuscation…",
  "Reading the document edges…",
];

// Content-type whisper — the pasted shape suggests the provenance, which
// sets risk weighting (one of the five integration rules on /integrate).
function detectContentType(
  content: string
): { type: ContentType; label: string } | null {
  if (/^\s*(from|to|subject|cc):/im.test(content)) {
    return { type: "email", label: "Email" };
  }
  if (
    /^\s*(def |class |import |from \w+ import|function |const |let |var |#!\/)/m.test(
      content
    )
  ) {
    return { type: "code", label: "Code" };
  }
  return null;
}

// A one-shot read of localStorage's initial state, exposed via
// useSyncExternalStore so React handles the SSR/hydration mismatch (server
// has no localStorage, so it renders the false/never-changes snapshot) without
// a setState-in-effect. There's nothing to actually subscribe to — history
// length is only re-checked when ScanForm's own state changes trigger a
// re-render, so subscribe is a no-op.
function subscribeNoop() {
  return () => {};
}
function getIsFirstVisitSnapshot() {
  return getHistory().length === 0;
}
function getIsFirstVisitServerSnapshot() {
  return false;
}

// The shared-verdict URL fragment, as an external store. getSnapshot parses
// and decodes once per React query; the server snapshot is always null so
// hydration is safe. subscribe listens for hashchange (covers back/forward
// navigation into a shared link).
function subscribeHash(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}
function getHashVerdict() {
  const hash = window.location.hash;
  return hash.startsWith("#v=") ? decodeVerdict(hash.slice(3)) : null;
}
function getHashVerdictServer() {
  return null;
}

export function ScanForm() {
  const [content, setContent] = useState("");
  const [contentType, setContentType] = useState<ContentType>("email");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [dismissedOnboarding, setDismissedOnboarding] = useState(false);
  const [scanStatusIndex, setScanStatusIndex] = useState(0);
  const [intentContrast, setIntentContrast] = useState<IntentContrast | null>(
    null
  );
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const shakeControls = useAnimation();
  const resultRef = useRef<ScanResponse | null>(null);
  const scanningRef = useRef(false);

  // Keep the mutable ref in sync with the state value. The synchronous writes in
  // event handlers are for tool call chains; this effect covers shared-verdict
  // hydration and any other state transitions.
  useEffect(() => {
    resultRef.current = result;
  });

  // Was there any scan history at mount? Read via useSyncExternalStore so the
  // SSR pass (no localStorage) and the hydrated client pass agree on a stable
  // value without a setState-in-effect. Combined with `dismissedOnboarding`
  // below so it disappears immediately on first interaction, not just once
  // localStorage is next read.
  const hadHistoryOnMount = useSyncExternalStore(
    subscribeNoop,
    getIsFirstVisitSnapshot,
    getIsFirstVisitServerSnapshot
  );
  const isFirstVisit = hadHistoryOnMount && !dismissedOnboarding;

  // Shared verdict — when the URL carries #v=<encoded>, render that scan
  // instead of an empty form. The fragment is an external store: read via
  // useSyncExternalStore (server snapshot is null, so hydration is safe),
  // adopted by adjusting state during render (the React-sanctioned pattern —
  // no setState inside an effect), and the fragment is then dropped from the
  // address bar so a refresh starts clean.
  const sharedVerdict = useSyncExternalStore(
    subscribeHash,
    getHashVerdict,
    getHashVerdictServer
  );
  const [adoptedVerdict, setAdoptedVerdict] = useState(sharedVerdict);
  if (sharedVerdict !== adoptedVerdict) {
    setAdoptedVerdict(sharedVerdict);
    if (sharedVerdict) {
      setContent(sharedVerdict.content);
      setContentType(sharedVerdict.content_type);
      setResult(sharedVerdict.response);
      setIntentContrast(null);
      setError(null);
      setDismissedOnboarding(true);
    }
  }

  // Side effect only — no setState. Runs after the verdict is adopted.
  useEffect(() => {
    if (adoptedVerdict && window.location.hash.startsWith("#v=")) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, [adoptedVerdict]);

  const triggerShake = useCallback(async () => {
    await shakeControls.start({
      x: [0, -6, 5, -4, 3, -1, 0],
      transition: { duration: 0.4, ease: "easeInOut" },
    });
  }, [shakeControls]);

  async function runScanWith(nextContent: string, nextType: ContentType) {
    if (!nextContent.trim()) {
      return { error: "Scan failed", detail: "content is empty" };
    }
    if (scanningRef.current) {
      return { error: "Scan failed", detail: "a scan is already running" };
    }

    scanningRef.current = true;
    setDismissedOnboarding(true);
    setContent(nextContent);
    setContentType(nextType);
    setScanning(true);
    setScanStatusIndex(0);
    setResult(null);
    resultRef.current = null;
    setIntentContrast(null);
    setError(null);

    try {
      const response = await scanContent({
        content: nextContent,
        content_type: nextType,
      });

      if (isError(response)) {
        setError(response.detail || response.error);
        triggerShake();
      } else {
        setResult(response);
        resultRef.current = response;
        addToHistory(nextContent, nextType, response);
        setHistoryRefresh((n) => n + 1);
      }

      return response;
    } finally {
      scanningRef.current = false;
      setScanning(false);
    }
  }

  async function handleScan() {
    await runScanWith(content, contentType);
  }

  function applySpecimen(id: string) {
    const example = EXAMPLES.find((ex) => ex.id === id);
    if (!example) {
      return {
        ok: false as const,
        error: `Unknown specimen id ${JSON.stringify(id)}. Call list_specimens.`,
      };
    }
    setDismissedOnboarding(true);
    setResult(null);
    resultRef.current = null;
    setIntentContrast(null);
    setError(null);
    setContent(example.content);
    setContentType(example.content_type);
    return { ok: true as const, label: example.label };
  }

  const webmcpLive = useWebMcpScan({
    scan: runScanWith,
    loadSpecimen: applySpecimen,
    lastVerdict: () => resultRef.current,
    contrastIntent: (intendedAction) => {
      const last = resultRef.current;
      if (!last) {
        return {
          ok: false as const,
          error:
            "No verdict on this page yet. Call scan_content first, with the human watching.",
        };
      }
      const contrast = buildIntentContrast(last, intendedAction);
      setIntentContrast(contrast);
      return { ok: true as const, contrast };
    },
  });

  function loadExample(index: number) {
    const example = EXAMPLES[index];
    setDismissedOnboarding(true);
    setResult(null);
    resultRef.current = null;
    setIntentContrast(null);
    setError(null);
    setContent("");
    setContentType(example.content_type);

    // Type in character by character — gives a sense of the content arriving
    let i = 0;
    const chars = example.content;
    const interval = setInterval(() => {
      if (i < chars.length) {
        setContent(chars.slice(0, i + 1));
        i++;
      } else {
        clearInterval(interval);
      }
    }, 8);
  }

  function loadFromHistory(entry: import("@/lib/history").HistoryEntry) {
    setContent(entry.content);
    setContentType(entry.content_type);
    setResult(entry.response);
    resultRef.current = entry.response;
    setIntentContrast(null);
    setError(null);
  }

  const hasContent = content.trim().length > 0;

  // Rotating scan status — cycles the detector-concern lines while scanning.
  // The index is reset where scanning starts (handleScan), not here, so no
  // setState fires synchronously inside the effect.
  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(() => setScanStatusIndex((i) => i + 1), 700);
    return () => clearInterval(interval);
  }, [scanning]);

  const suggestion = hasContent ? detectContentType(content) : null;
  const beat = agentBeat({
    hasContent,
    scanning,
    hasResult: Boolean(result),
    hasContrast: Boolean(intentContrast),
  });

  return (
    <div className="space-y-6">
      <div className="page-enter space-y-2">
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
          Scan
        </h1>
        <p className="text-base text-ink-muted leading-relaxed max-w-xl">
          Paste what your agent retrieved. Hidden instructions get caught
          before it acts.
        </p>
      </div>

      {webmcpLive ? (
        <>
          <AgentSessionRail beat={beat} />
          <WebMcpDebug live={webmcpLive} />
        </>
      ) : (
        !hasContent &&
        !result && (
          <p className="text-xs text-ink-faint font-mono">
            Armed — waiting for retrieved content
          </p>
        )
      )}

      {/* First-visit onboarding — explains what to do, disappears after first use */}
      <AnimatePresence>
        {isFirstVisit && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
            className="overflow-hidden"
          >
            <div className="rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink-muted leading-relaxed">
              Not sure what to try?{" "}
              <span className="text-ink">Click an example below</span>
              {" "}— one is a hidden instruction, one is clean.
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* The content area */}
      <motion.div className="relative" animate={shakeControls}>
        {/* Scanning beam overlay */}
        <AnimatePresence>{scanning && <ScanBeam />}</AnimatePresence>

        <textarea
          ref={textareaRef}
          name="content"
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            if (e.target.value.trim()) setDismissedOnboarding(true);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.metaKey && hasContent && !scanning) {
              e.preventDefault();
              handleScan();
            }
          }}
          placeholder="Paste content here — an email, search result, or document your agent would read..."
          className={`w-full min-h-[200px] p-6 rounded-2xl bg-surface border text-ink font-mono text-sm leading-relaxed resize-y focus:outline-none focus:border-ink/40 focus:ring-1 focus:ring-ink/10 transition-colors duration-200 placeholder:text-ink-faint ${
            !hasContent && !scanning && !result
              ? "border-ink/15"
              : "border-border"
          }`}
          style={{ fontVariantLigatures: "none" }}
          aria-label="Content to scan for prompt injection"
        />

        {/* Keyboard shortcut hint — appears when content is present */}
        <AnimatePresence>
          {hasContent && !scanning && !result && (
            <motion.span
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="absolute bottom-4 left-6 text-[10px] text-ink-faint font-mono"
            >
              ⌘ Enter to scan
            </motion.span>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Content-type whisper — suggests provenance from the pasted shape */}
      {suggestion && suggestion.type !== contentType && (
        <motion.button
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={() => setContentType(suggestion.type)}
          className="text-xs text-violet font-medium hover:text-violet/80 transition-colors"
        >
          {suggestion.label} detected — scan as{" "}
          {suggestion.label.toLowerCase()}?
        </motion.button>
      )}

      {/* Actions row — examples (left), content-type + scan (right) */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        {/* Examples */}
        <div className="flex flex-col gap-1.5">
          <AnimatePresence>
            {isFirstVisit && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[10px] text-ink-faint uppercase tracking-wide"
              >
                Try an example
              </motion.span>
            )}
          </AnimatePresence>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((example, i) => (
              <motion.button
                key={i}
                onClick={() => loadExample(i)}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                  example.is_injection
                    ? "text-dangerous/70 bg-dangerous-bg hover:text-dangerous"
                    : "text-safe/70 bg-safe-bg hover:text-safe"
                }`}
                whileTap={{ scale: 0.92 }}
                transition={SPRING}
              >
                {example.label}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Content type + scan — grouped on the right */}
        <div className="flex items-center gap-3">
          {/* Content type — labeled, visible, not floating */}
          <label className="flex items-center gap-1.5 text-xs text-ink-faint">
            <span className="font-medium">Type</span>
            <select
              name="content_type"
              value={contentType}
              onChange={(e) => setContentType(e.target.value as ContentType)}
              className="text-xs font-medium text-ink-muted bg-canvas border border-border rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-ink/40 cursor-pointer transition-colors"
              aria-label="Content type"
            >
              {CONTENT_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>
                  {ct.label}
                </option>
              ))}
            </select>
          </label>

          {/* Scan button */}
          <motion.button
            onClick={handleScan}
            disabled={scanning || !hasContent}
            className="relative px-5 py-2.5 rounded-xl bg-ink text-canvas font-semibold text-sm overflow-hidden disabled:opacity-30 disabled:cursor-not-allowed"
            whileTap={hasContent && !scanning ? { opacity: 0.9 } : {}}
            transition={{ duration: 0.15 }}
          >
            {/* Button content — morphs between states */}
            <AnimatePresence mode="wait">
              {scanning ? (
                <motion.span
                  key="scanning"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.15 }}
                  className="flex items-center gap-2"
                >
                  <motion.span
                    className="w-3 h-3 rounded-full border-2 border-canvas/40 border-t-canvas"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.6, repeat: Infinity, ease: "linear" }}
                  />
                  {SCAN_STATUSES[scanStatusIndex % SCAN_STATUSES.length]}
                </motion.span>
              ) : (
                <motion.span
                  key="idle"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.15 }}
                >
                  Scan
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </div>
      </div>

      {/* Scan history */}
      <ScanHistory onSelect={loadFromHistory} refreshKey={historyRefresh} />

      {/* Error — with shake on the textarea */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
            className="flex items-start gap-2 text-sm text-dangerous"
          >
            <span className="shrink-0 mt-0.5">×</span>
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.45, ease: EASE_OUT }}
          >
            {intentContrast && (
              <div className="mb-5">
                <IntentContrastPanel contrast={intentContrast} />
              </div>
            )}
            {webmcpLive && result && !intentContrast && (
              <div className="mb-5">
                <WaitingForIntent />
              </div>
            )}
            <ScanResult result={result} content={content} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
