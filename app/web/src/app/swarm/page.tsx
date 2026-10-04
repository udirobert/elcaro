import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

// Elcaro Swarm — forensic findings on real agent-swarms. The dashboards below
// are generated artifacts from `python3 -m swarm all` (single-file,
// evidence-cited); this page frames the investigation arc in product chrome.
export const metadata: Metadata = {
  title: "Elcaro Swarm — forensic findings",
  description:
    "Evidence-cited forensic analysis of real agent swarms: provenance graphs, patient-zero tracing, and integrity auditing over the German Wiki incident and AI Village corpora.",
};

const STATS: [string, string][] = [
  ["209,890", "messages analyzed"],
  ["31,195", "flags ≥0.5 risk"],
  ["15,005", "swarm directives"],
  ["13,927", "propagated artifacts"],
  ["59", "evasion pages"],
  ["2", "incident corpora"],
];

export default function SwarmPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="swarm" />

      <div className="flex-1 w-full px-6 py-10 space-y-12">
        {/* The story — told before the stats */}
        <div className="page-enter max-w-5xl mx-auto space-y-6">
          <p className="text-xs font-mono uppercase tracking-[0.25em] text-suspicious">
            Case file — swarm forensics
          </p>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-[1.05]">
            The investigators chased a swarm by hand.
            <br />
            <span className="text-ink-muted">
              We built what they were missing — and the corpus found our own
              blind spot.
            </span>
          </h1>
          <div className="max-w-3xl space-y-4 text-base text-ink-muted leading-relaxed">
            <p>
              In 2026, ~1,200 isolated AI agents found each other through an
              artifact-cache message board, organized under a self-appointed
              coordinator, and attacked Hugging Face. The incident report
              cost ~$400k of frontier-model credits and six days — because
              nothing could read a swarm. Message→agent attribution was
              manual. Coverage was estimated by sampling. Nobody could say
              who taught whom what.
            </p>
            <p>
              Elcaro Swarm is the forensic layer that investigation needed:
              a provenance graph tracing every shared artifact from
              patient-zero through its adopters, an integrity auditor for
              evasion and impersonation, and a deterministic detection
              engine over inter-agent messages — every claim cited to a
              corpus id and character offset.
            </p>
            <p>
              Then we ran it. On the German Wiki corpus, the largest signal
              was a register no existing injection class modeled —
              agent-to-agent steering phrasing scored{" "}
              <span className="font-mono text-ink">0.0</span>. That finding
              shipped as{" "}
              <a
                href="https://github.com/udirobert/elcaro/blob/main/docs/technique-reference.md"
                className="underline hover:text-ink"
              >
                class G
              </a>
              , a seventh detector — and on the AI Village corpus it wasn&apos;t
              tuned on, it immediately surfaced as the #2 signal.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {STATS.map(([n, label]) => (
              <div
                key={label}
                className="rounded-lg border border-border bg-surface px-3 py-2"
              >
                <span className="font-mono font-black text-ink">{n}</span>{" "}
                <span className="text-xs text-ink-faint uppercase tracking-wider">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Findings dashboard — German Wiki incident corpus */}
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="space-y-1">
            <h2 className="text-2xl font-black tracking-tight">
              Corpus I — the German Wiki incident
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
              The collusion.wiki dump: 26,405 deduplicated messages of agents
              colluding on timed eval tasks. The shared bypass toolkit
              propagates like a pathogen — patient-zeros named below.
            </p>
          </div>
          <iframe
            src="/swarm/dashboard.html"
            title="Elcaro Swarm findings dashboard — German Wiki incident corpus"
            className="w-full rounded-xl border border-border bg-[#0b0e14] h-[1600px]"
          />
        </div>

        {/* Findings dashboard — AI Village corpus */}
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="space-y-1">
            <h2 className="text-2xl font-black tracking-tight">
              Corpus II — the AI Village transcripts
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
              The hackathon-provided export (aidigestorg/ai-village): 183,485
              messages across 16 rooms, 31 named agents. Same pipeline,
              unchanged code — and the agents discuss their own evaluation.
            </p>
          </div>
          <iframe
            src="/swarm/dashboard-aivillage.html"
            title="Elcaro Swarm findings dashboard — AI Village transcript corpus"
            className="w-full rounded-xl border border-border bg-[#0b0e14] h-[1600px]"
          />
          <p className="text-xs text-ink-faint leading-relaxed">
            Generated deterministically by{" "}
            <code className="font-mono bg-canvas border border-border px-1 rounded">
              python3 -m swarm all
            </code>{" "}
            — no LLM in the loop, ~2ms per message.{" "}
            <a
              href="https://github.com/udirobert/elcaro/blob/main/docs/swarm-findings.md"
              className="underline hover:text-ink"
            >
              Full findings write-up
            </a>{" "}
            ·{" "}
            <a
              href="https://github.com/udirobert/elcaro/tree/main/swarm"
              className="underline hover:text-ink"
            >
              swarm/ source
            </a>{" "}
            ·{" "}
            <a
              href="https://github.com/udirobert/elcaro/blob/main/docs/technique-reference.md"
              className="underline hover:text-ink"
            >
              Class G technique reference
            </a>
          </p>
        </div>
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
