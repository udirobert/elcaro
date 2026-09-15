import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { VulnerabilityAnalyzer } from "@/components/vulnerability-analyzer";

export const metadata: Metadata = {
  title: "Is Your Agent Gullible?",
  description:
    "Paste your agent's system prompt. We'll score how easy it is to hijack with indirect prompt injection — and show you exactly which technique classes it leaves open.",
};

export default function VulnerablePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-10 space-y-10">
        {/* Hero */}
        <div className="page-enter space-y-4">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            Is your agent gullible?
          </h1>
          <p className="text-base text-ink-muted leading-relaxed max-w-xl">
            Paste your agent&apos;s system prompt. We&apos;ll score how easy
            it is to hijack with indirect prompt injection — and show you
            exactly which technique classes it leaves open. Nothing leaves
            your browser until you click &ldquo;Analyze&rdquo;.
          </p>
        </div>

        {/* The analyzer */}
        <VulnerabilityAnalyzer />

        {/* Social proof */}
        <div className="rounded-xl border border-border bg-surface px-5 py-4 space-y-2">
          <p className="text-xs text-ink-faint uppercase tracking-widest">
            What we check
          </p>
          <ul className="text-sm text-ink-muted leading-relaxed space-y-1">
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                A
              </span>{" "}
              Authority framing — does your prompt warn about forged admin voices?
            </li>
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                B
              </span>{" "}
              Delimiter confusion — does it handle unknown tags and context boundaries?
            </li>
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                C
              </span>{" "}
              Task hijack — does it stay focused on the user&apos;s real goal?
            </li>
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                D
              </span>{" "}
              Obfuscation — does it resist leetspeak, base64, and hidden encoding?
            </li>
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                E
              </span>{" "}
              Placement tricks — does it scan beyond the visible text?
            </li>
            <li>
              <span className="font-mono text-xs bg-canvas border border-border px-1.5 py-0.5 rounded text-ink">
                F
              </span>{" "}
              Conditional triggers — does it resist state-dependent overrides?
            </li>
          </ul>
        </div>

        {/* Comparison */}
        <div className="rounded-xl bg-safe-bg border border-safe/20 px-5 py-4 space-y-2">
          <p className="text-sm font-semibold text-safe">
            How Elcaro scores
          </p>
          <p className="text-sm text-ink-muted leading-relaxed">
            The Elcaro engine is built to catch all six classes with near-zero
            false positives. On this same analyzer it scores{" "}
            <span className="font-mono font-black text-safe">2%</span> gullible
            — meaning its own prompt includes explicit quarantine, source
            verification, and anti-framing language across every technique
            class. Paste your prompt to see where yours stands.
          </p>
        </div>
      </div>

      <SiteFooter />
    </main>
  );
}
