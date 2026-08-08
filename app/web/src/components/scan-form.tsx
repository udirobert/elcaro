"use client";

import { useState } from "react";
import type { ContentType, ScanResponse } from "@/lib/types";
import { scanContent, isError } from "@/lib/api";
import { CONTENT_TYPES, EXAMPLES } from "@/lib/constants";
import { ThinkingOrb } from "./thinking-orb";
import { ScanResult } from "./scan-result";

export function ScanForm() {
  const [content, setContent] = useState("");
  const [contentType, setContentType] = useState<ContentType>("email");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleScan() {
    if (!content.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    const response = await scanContent({ content, content_type: contentType });

    if (isError(response)) {
      setError(response.detail || response.error);
    } else {
      setResult(response);
    }

    setLoading(false);
  }

  function loadExample(index: number) {
    const example = EXAMPLES[index];
    setContent(example.content);
    setContentType(example.content_type);
    setResult(null);
    setError(null);
  }

  return (
    <div className="space-y-6">
      {/* Input area */}
      <div className="space-y-4">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste content to scan for prompt injection..."
          className="w-full h-40 p-4 rounded-xl bg-card border border-card-border text-foreground placeholder:text-muted font-mono text-sm resize-y focus:outline-none focus:border-foreground/30 transition-colors"
        />

        <div className="flex flex-col sm:flex-row gap-3">
          {/* Content type selector */}
          <select
            value={contentType}
            onChange={(e) => setContentType(e.target.value as ContentType)}
            className="px-4 py-2.5 rounded-lg bg-card border border-card-border text-foreground text-sm focus:outline-none focus:border-foreground/30"
          >
            {CONTENT_TYPES.map((ct) => (
              <option key={ct.value} value={ct.value}>
                {ct.label}
              </option>
            ))}
          </select>

          {/* Scan button */}
          <button
            onClick={handleScan}
            disabled={loading || !content.trim()}
            className="px-6 py-2.5 rounded-lg bg-foreground text-background font-semibold text-sm hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            {loading ? "Scanning..." : "Scan"}
          </button>
        </div>
      </div>

      {/* Example buttons */}
      <div className="space-y-2">
        <p className="text-xs text-muted uppercase tracking-wider font-semibold">
          Try an example
        </p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example, i) => (
            <button
              key={i}
              onClick={() => loadExample(i)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                example.is_injection
                  ? "border-dangerous/30 text-dangerous/80 hover:bg-dangerous/10"
                  : "border-safe/30 text-safe/80 hover:bg-safe/10"
              }`}
            >
              {example.is_injection ? "⚠ " : "✓ "}
              {example.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && <ThinkingOrb />}

      {/* Error state */}
      {error && (
        <div className="border border-dangerous/30 bg-dangerous/5 rounded-xl p-4">
          <p className="text-sm text-dangerous">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && <ScanResult result={result} />}
    </div>
  );
}
