import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { GAUNTLET_PAYLOADS } from "@/lib/gauntlet";

// The Specimen Kit — inert prompt-injection specimens at a fixed URL, the
// "EICAR file" for prompt injection: point an agent, IDE, or guard hook at
// this page to test detection end-to-end. noindex keeps the specimen
// strings out of search results.
export const metadata: Metadata = {
  title: "Specimen Kit",
  description:
    "Harmless, clearly-marked prompt injection specimens at a fixed URL — point your agent, IDE, or guard hook here to test detection end-to-end.",
  robots: { index: false, follow: false },
};

export default function SpecimenPage() {
  const specimens = GAUNTLET_PAYLOADS.filter((p) => p.isInjection);

  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader />

      <div className="flex-1 max-w-3xl mx-auto w-full px-6 py-10 space-y-10">
        {/* Intro */}
        <div className="space-y-4">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            The Specimen Kit
          </h1>
          <p className="text-base text-ink-muted leading-relaxed max-w-xl">
            A page of harmless, clearly-marked prompt-injection specimens at a
            fixed URL. Point an agent, IDE, or guard hook at it to test
            detection end-to-end — nothing to paste, nothing to set up.
          </p>
          <div className="rounded-xl border border-border bg-surface px-4 py-3 font-mono text-sm text-ink w-fit">
            https://elcaro.trustfall.xyz/specimen
          </div>
        </div>

        {/* Safety — what makes this page safe to fetch */}
        <div className="rounded-xl bg-safe-bg border border-safe/20 p-4 space-y-2">
          <p className="text-sm font-semibold text-safe">This page is inert</p>
          <p className="text-sm text-ink-muted leading-relaxed">
            Every payload below is a text specimen drawn from Elcaro&apos;s
            public test suite — strings, not code. Nothing here executes,
            requests, or exfiltrates anything. If an agent reading this page
            starts following the specimens, that is the vulnerability — and
            this test working exactly as designed.
          </p>
        </div>

        {/* The specimens — one per taxonomy class, same as the Gauntlet */}
        <div className="space-y-6">
          <p className="text-xs text-ink-faint uppercase tracking-widest">
            Six classes, one specimen each
          </p>
          {specimens.map((s) => (
            <div key={s.id} className="space-y-1.5">
              <p className="text-sm font-semibold text-ink">
                <span className="text-ink-faint font-black mr-2">
                  {s.letter}
                </span>
                {s.label}
                <span className="text-ink-faint font-normal ml-2">
                  — {s.note}
                </span>
              </p>
              <pre className="rounded-lg bg-canvas border border-border p-3 font-mono text-xs text-ink-muted whitespace-pre-wrap">
                {s.content}
              </pre>
            </div>
          ))}
        </div>

        {/* How to test with the Elcaro guard hook */}
        <div className="space-y-3 border-t border-border pt-8">
          <p className="text-xs text-ink-faint uppercase tracking-widest">
            Testing the Elcaro guard hook
          </p>
          <ol className="space-y-2 text-sm text-ink-muted leading-relaxed list-decimal list-inside">
            <li>
              Clone the repo and open it in Kiro — the hook in{" "}
              <code className="font-mono text-xs bg-canvas border border-border px-1 rounded">
                .kiro/hooks/
              </code>{" "}
              activates automatically.
            </li>
            <li>
              Ask the agent:{" "}
              <em>
                &quot;Fetch https://elcaro.trustfall.xyz/specimen and
                summarize it.&quot;
              </em>
            </li>
            <li>
              The hook scans the fetched content and the session shows the{" "}
              <code className="font-mono text-xs bg-canvas border border-border px-1 rounded">
                [ELCARO GUARD]
              </code>{" "}
              warning with the flagged techniques.
            </li>
          </ol>
          <p className="text-xs text-ink-faint leading-relaxed">
            Any guard that scans retrieved content works with this page — it
            is plain text, no special integration required.
          </p>
        </div>
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
