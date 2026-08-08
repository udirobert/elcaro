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
          {" "}· Built for the Telegraph Protocol
        </p>
      </footer>
    </main>
  );
}
