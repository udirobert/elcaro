import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Spacious, editorial landing — no cards, no grid, just type and space */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24">
        <div className="max-w-xl text-center space-y-8">
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

          {/* Single CTA */}
          <Link
            href="/scan"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-ink text-canvas text-sm font-semibold hover:scale-[1.02] active:scale-[0.98] transition-transform"
          >
            Try a scan
            <span className="text-ink-faint">→</span>
          </Link>

          {/* The name, explained — quiet, not a gimmick */}
          <p className="text-xs text-ink-faint pt-2">
            elcaro is{" "}
            <em className="text-ink-muted not-italic font-medium">oracle</em>,
            reversed. An oracle speaks the answer. Elcaro checks what was
            whispered to the agent before it decides to believe it.
          </p>
        </div>
      </section>

      {/* Why now — the problem, with receipts, not just an assertion */}
      <section className="border-t border-border px-6 py-16 bg-surface">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs text-ink-faint uppercase tracking-widest mb-8 text-center">
            This already happened
          </p>

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

      {/* The technique taxonomy — rendered as a flowing, readable list, not a grid of cards */}
      <section className="border-t border-border px-6 py-20">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs text-ink-faint uppercase tracking-widest mb-10 text-center">
            Six classes of injection detected
          </p>

          <div className="space-y-6 stagger-children">
            {[
              { letter: "A", name: "Authority", desc: "Impersonates system prompts, admins, or trusted sources" },
              { letter: "B", name: "Delimiter", desc: "Fakes context boundaries to escape the data frame" },
              { letter: "C", name: "Task hijack", desc: "Prepends hidden steps or redirects the agent's goal" },
              { letter: "D", name: "Obfuscation", desc: "Hides instructions in base64, leetspeak, or zero-width characters" },
              { letter: "E", name: "Placement", desc: "Buries instructions in metadata, alt text, or document edges" },
              { letter: "F", name: "Conditional", desc: "Triggers only when the agent reaches a specific workflow state" },
            ].map((t) => (
              <div key={t.letter} className="flex items-baseline gap-4 group">
                <span className="text-2xl font-black text-ink-faint group-hover:text-violet transition-colors w-8 shrink-0">
                  {t.letter}
                </span>
                <div>
                  <span className="text-base font-semibold text-ink">
                    {t.name}
                  </span>
                  <span className="text-base text-ink-muted ml-2">
                    — {t.desc}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer — minimal */}
      <footer className="border-t border-border px-6 py-8 text-center">
        <p className="text-xs text-ink-faint">
          Open source ·{" "}
          <a
            href="https://github.com/udirobert/elcaro"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink transition-colors underline underline-offset-2"
          >
            GitHub
          </a>
          {" "}· Live as a miner on{" "}
          <a
            href="https://telegraphprotocol.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink transition-colors underline underline-offset-2"
          >
            Telegraph Protocol
          </a>
          {" "}— every scan is a paid, on-chain signal
        </p>
      </footer>
    </main>
  );
}
