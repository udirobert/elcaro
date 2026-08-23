import Link from "next/link";
import { HeroCatch } from "@/components/hero-catch";
import { SpecimenMarquee } from "@/components/specimen-marquee";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { TrustChipBand } from "@/components/trust-chip-band";
import { TaxonomyGrid } from "@/components/taxonomy-grid";
import { AdaptiveCTA } from "@/components/adaptive-cta";

export default function HomePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Header — shared chrome, consistent wayfinding */}
      <SiteHeader />

      {/* Spacious, editorial hero — the product demonstrated, not described */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <div className="max-w-xl text-center space-y-8 w-full">
          {/* Headline — large, bold, minimal */}
          <h1 className="text-5xl sm:text-6xl font-black tracking-tight leading-[1.08]">
            See what your
            <br />
            <span className="bg-gradient-to-r from-violet to-coral bg-clip-text text-transparent">
              agent can&apos;t
            </span>
          </h1>

          {/* One sentence — that's all */}
          <p className="text-lg text-ink-muted leading-relaxed max-w-md mx-auto">
            Hidden instructions live inside emails, search results, and documents
            your agent retrieves. Elcaro finds them first.
          </p>

          {/* Live catch — the demo is the hero */}
          <HeroCatch />

          {/* CTAs — Gauntlet first: proof before participation */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/gauntlet"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-violet to-coral text-canvas text-sm font-semibold hover:scale-[1.02] active:scale-[0.98] transition-transform"
            >
              Run the Gauntlet
              <span className="text-canvas/60">→</span>
            </Link>
            <Link
              href="/scan"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:scale-[1.02] active:scale-[0.98] transition-transform"
            >
              Try a scan
              <span className="text-ink-faint">→</span>
            </Link>
            <Link
              href="/integrate"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-sm font-semibold text-ink-muted hover:text-ink hover:border-border-strong transition-colors"
            >
              Add to your agent
            </Link>
          </div>

          {/* The name, explained — quiet, not a gimmick */}
          <p className="text-xs text-ink-faint pt-2">
            elcaro is{" "}
            <em className="text-ink-muted not-italic font-medium">oracle</em>,
            reversed. An oracle speaks the answer. Elcaro checks what was
            whispered to the agent before it decides to believe it.
          </p>

          {/* Trust-chip band — proof that earns its space, verifiable on demand */}
          <TrustChipBand />
        </div>
      </section>

      {/* Specimen marquee — the threats, ambient */}
      <SpecimenMarquee />

      {/* Why now — the problem, with receipts */}
      <section className="px-6 py-16 bg-surface">
        <div className="max-w-2xl mx-auto">
          <div className="grid sm:grid-cols-2 gap-8">
            <div>
              <p className="text-sm font-semibold text-ink mb-1.5">
                EchoLeak — zero clicks required
              </p>
              <p className="text-sm text-ink-muted leading-relaxed">
                A single crafted email made Microsoft 365 Copilot exfiltrate
                internal data with no user interaction.{" "}
                <a
                  href="https://nvd.nist.gov/vuln/detail/CVE-2025-32711"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ink-faint hover:text-violet underline underline-offset-2 transition-colors"
                >
                  CVE-2025-32711
                </a>
              </p>
            </div>
            <div>
              <p className="text-sm font-semibold text-ink mb-1.5">
                90+ organizations, one year
              </p>
              <p className="text-sm text-ink-muted leading-relaxed">
                CrowdStrike&apos;s 2026 threat report recorded prompt injection
                incidents across 90+ organizations in 2025 — &quot;prompts are
                the new malware.&quot;
              </p>
            </div>
          </div>
          <p className="text-sm text-ink-muted text-center mt-10 max-w-lg mx-auto leading-relaxed">
            The model isn&apos;t the attack surface. The data your agent
            reads is — and almost nothing scans it before the agent acts.
          </p>
        </div>
      </section>

      {/* The technique taxonomy — compact grid, expand on interest */}
      <section className="border-t border-border px-6 py-20">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs text-ink-faint uppercase tracking-widest mb-10 text-center">
            Six classes of injection detected
          </p>
          <TaxonomyGrid />
        </div>
      </section>

      {/* Closing CTA — adapts to the visitor's journey */}
      <section className="border-t border-border px-6 py-20">
        <AdaptiveCTA />
      </section>

      {/* Footer — shared chrome */}
      <SiteFooter />
    </main>
  );
}
