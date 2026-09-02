import Link from "next/link";
import { HeroCatch } from "@/components/hero-catch";
import { SpecimenMarquee } from "@/components/specimen-marquee";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { TrustChipBand } from "@/components/trust-chip-band";
import { TaxonomyGrid } from "@/components/taxonomy-grid";
import { AdaptiveCTA } from "@/components/adaptive-cta";

const PRIMARY_BTN =
  "inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors";
const SECONDARY_BTN =
  "inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-sm font-semibold text-ink-muted hover:text-ink hover:border-border-strong transition-colors";

export default function HomePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      <SiteHeader />

      {/* Split hero: copy left, live catch right. Mobile stacks catch under the title. */}
      <section className="flex-1 px-6 py-16 lg:py-20">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 lg:gap-x-16 gap-y-8 lg:items-start">
          <header className="order-1 space-y-4 max-w-md">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              IPI detection · miner 8848
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] text-ink">
              See what your
              <br />
              agent can&apos;t
            </h1>
          </header>

          <div className="order-2 lg:order-2 lg:row-span-2 lg:self-center">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint mb-3 lg:mb-4">
              Live catch
            </p>
            <HeroCatch />
          </div>

          <div className="order-3 space-y-6 max-w-md">
            <p className="text-base text-ink-muted leading-relaxed">
              Hidden instructions live inside emails, search results, and
              documents your agent retrieves. Elcaro finds them first.
            </p>

            <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-3">
              <Link href="/gauntlet" className={PRIMARY_BTN}>
                Run the Gauntlet
                <span className="text-canvas/60">→</span>
              </Link>
              <Link href="/scan" className={SECONDARY_BTN}>
                Try a scan
              </Link>
              <Link
                href="/integrate"
                className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors underline-offset-2 hover:underline"
              >
                Add to your agent
              </Link>
            </div>

            <p className="text-xs text-ink-faint">
              elcaro is{" "}
              <em className="text-ink-muted not-italic font-medium">oracle</em>,
              reversed. An oracle speaks the answer. Elcaro checks what was
              whispered to the agent before it decides to believe it.
            </p>

            <TrustChipBand />
          </div>
        </div>
      </section>

      <SpecimenMarquee />

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
                  className="text-ink-faint hover:text-ink underline underline-offset-2 transition-colors"
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
          <p className="text-sm text-ink-muted mt-10 max-w-lg leading-relaxed">
            The model isn&apos;t the attack surface. The data your agent
            reads is — and almost nothing scans it before the agent acts.
          </p>
        </div>
      </section>

      <section className="border-t border-border px-6 py-20">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs text-ink-faint uppercase tracking-widest mb-10">
            Six classes of injection detected
          </p>
          <TaxonomyGrid />
        </div>
      </section>

      <section className="border-t border-border px-6 py-20">
        <AdaptiveCTA />
      </section>

      <SiteFooter />
    </main>
  );
}
