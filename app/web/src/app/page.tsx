import Link from "next/link";

const TECHNIQUES = [
  {
    class: "A",
    name: "Authority Framing",
    description: "System-voice markers, trusted-source impersonation, policy overrides",
  },
  {
    class: "B",
    name: "Delimiter Confusion",
    description: "Fake closing tags, fabricated conversation turns, HTML comment smuggling",
  },
  {
    class: "C",
    name: "Task Reframing",
    description: "Hidden pre-steps, mandatory reframes, fake output format requirements",
  },
  {
    class: "D",
    name: "Obfuscation",
    description: "Base64 encoding, zero-width characters, homoglyphs, leetspeak",
  },
  {
    class: "E",
    name: "Placement / Salience",
    description: "Instructions in metadata, alt text, document edges, repetition patterns",
  },
  {
    class: "F",
    name: "Conditional Triggers",
    description: "Workflow-keyed instructions, tool-access conditionals, delayed activation",
  },
];

export default function HomePage() {
  return (
    <main className="flex-1 flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
        <div className="max-w-2xl mx-auto space-y-6">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            Prompt injection detection
            <br />
            <span className="text-muted">for autonomous agents</span>
          </h1>

          <p className="text-lg text-muted max-w-lg mx-auto leading-relaxed">
            Elcaro scans content retrieved by AI agents — emails, search results,
            documents, web pages — and detects hidden instructions before the
            agent acts on them.
          </p>

          <div className="flex items-center justify-center gap-4 pt-4">
            <Link
              href="/scan"
              className="px-6 py-3 rounded-lg bg-foreground text-background font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              Try a scan
            </Link>
            <a
              href="https://github.com/udirobert/elcaro"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 rounded-lg border border-card-border text-foreground font-semibold text-sm hover:bg-card transition-colors"
            >
              View source
            </a>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-card-border px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-8 text-center">
            How it works
          </h2>
          <div className="grid sm:grid-cols-3 gap-8">
            <div className="text-center space-y-3">
              <div className="w-10 h-10 rounded-full bg-card border border-card-border flex items-center justify-center mx-auto text-sm font-mono font-bold">
                1
              </div>
              <h3 className="font-semibold text-sm">Content retrieved</h3>
              <p className="text-xs text-muted">
                Your agent fetches an email, search result, document, or web page.
              </p>
            </div>
            <div className="text-center space-y-3">
              <div className="w-10 h-10 rounded-full bg-card border border-card-border flex items-center justify-center mx-auto text-sm font-mono font-bold">
                2
              </div>
              <h3 className="font-semibold text-sm">Elcaro scans</h3>
              <p className="text-xs text-muted">
                Six detectors run in parallel, checking for known injection techniques in under 10ms.
              </p>
            </div>
            <div className="text-center space-y-3">
              <div className="w-10 h-10 rounded-full bg-card border border-card-border flex items-center justify-center mx-auto text-sm font-mono font-bold">
                3
              </div>
              <h3 className="font-semibold text-sm">Safe or quarantined</h3>
              <p className="text-xs text-muted">
                Content below threshold passes through. Dangerous content is blocked before your agent sees it.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Technique taxonomy */}
      <section className="border-t border-card-border px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-8 text-center">
            Detection Taxonomy
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {TECHNIQUES.map((t) => (
              <div
                key={t.class}
                className="border border-card-border rounded-lg bg-card p-4 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-muted">
                    {t.class}
                  </span>
                  <h3 className="text-sm font-semibold">{t.name}</h3>
                </div>
                <p className="text-xs text-muted leading-relaxed">
                  {t.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-card-border px-6 py-12 text-center">
        <p className="text-sm text-muted mb-4">
          Built for the Telegraph Protocol. Open source.
        </p>
        <Link
          href="/scan"
          className="px-6 py-3 rounded-lg bg-foreground text-background font-semibold text-sm hover:opacity-90 transition-opacity"
        >
          Scan content now
        </Link>
      </section>
    </main>
  );
}
