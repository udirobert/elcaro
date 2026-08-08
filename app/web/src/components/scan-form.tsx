"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ContentType, ScanResponse } from "@/lib/types";
import { scanContent, isError } from "@/lib/api";
import { CONTENT_TYPES, EXAMPLES } from "@/lib/constants";
import { addToHistory } from "@/lib/history";
import { ScanResult } from "./scan-result";
import { ScanBeam } from "./scan-beam";
import { ScanHistory } from "./scan-history";

export function ScanForm() {
  const [content, setContent] = useState("");
  const [contentType, setContentType] = useState<ContentType>("email");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleScan() {
    if (!content.trim()) return;

    setScanning(true);
    setResult(null);
    setError(null);

    const response = await scanContent({ content, content_type: contentType });

    if (isError(response)) {
      setError(response.detail || response.error);
    } else {
      setResult(response);
      addToHistory(content, contentType, response);
      setHistoryRefresh((n) => n + 1);
    }

    setScanning(false);
  }

  function loadExample(index: number) {
    const example = EXAMPLES[index];
    setResult(null);
    setError(null);

    // Type the content in character by character
    setContent("");
    setContentType(example.content_type);

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
    setError(null);
  }

  return (
    <div className="space-y-8">
      {/* The content area — the main stage */}
      <div className="relative">
        {/* Scanning beam overlay */}
        <AnimatePresence>{scanning && <ScanBeam />}</AnimatePresence>

        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste content here..."
          className="w-full min-h-[200px] p-6 rounded-2xl bg-surface border border-border text-ink font-mono text-sm leading-relaxed resize-y focus:outline-none focus:border-violet transition-colors placeholder:text-ink-faint"
          style={{ fontVariantLigatures: "none" }}
        />

        {/* Content type — subtle, inline */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2">
          <select
            value={contentType}
            onChange={(e) => setContentType(e.target.value as ContentType)}
            className="text-xs font-medium text-ink-muted bg-canvas border border-border rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-violet cursor-pointer"
          >
            {CONTENT_TYPES.map((ct) => (
              <option key={ct.value} value={ct.value}>
                {ct.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Actions row */}
      <div className="flex items-center justify-between gap-4">
        {/* Examples — small, understated */}
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map((example, i) => (
            <button
              key={i}
              onClick={() => loadExample(i)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all hover:scale-105 active:scale-95 ${
                example.is_injection
                  ? "text-dangerous bg-dangerous-bg hover:text-dangerous"
                  : "text-safe bg-safe-bg hover:text-safe"
              }`}
            >
              {example.label}
            </button>
          ))}
        </div>

        {/* Scan button */}
        <motion.button
          onClick={handleScan}
          disabled={scanning || !content.trim()}
          className="px-5 py-2.5 rounded-xl bg-ink text-canvas font-semibold text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          animate={
            !scanning && content.trim()
              ? { scale: [1, 1.02, 1] }
              : { scale: 1 }
          }
          transition={{
            repeat: !scanning && content.trim() ? Infinity : 0,
            duration: 3,
            ease: "easeInOut",
          }}
        >
          {scanning ? "Scanning..." : "Scan"}
        </motion.button>
      </div>

      {/* Scan history */}
      <ScanHistory onSelect={loadFromHistory} refreshKey={historyRefresh} />

      {/* Loading state — visible below the textarea during scan */}
      <AnimatePresence>
        {scanning && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-3 py-4"
          >
            <div className="relative w-5 h-5">
              <div className="absolute inset-0 rounded-full border-2 border-border" />
              <div className="absolute inset-0 rounded-full border-2 border-violet border-t-transparent animate-spin" />
            </div>
            <span className="text-sm text-ink-muted">
              Analysing content for injection patterns...
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="text-sm text-dangerous"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Results — the content transforms */}
      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <ScanResult result={result} content={content} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
