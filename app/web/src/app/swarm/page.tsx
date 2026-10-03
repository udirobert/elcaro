import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";

// Elcaro Swarm — forensic findings on the German Wiki incident corpus.
// The dashboard below is the generated artifact from `python3 -m swarm all`
// (single-file, evidence-cited); this page frames it in the product chrome so
// judges and agents reach it from the main site.
export const metadata: Metadata = {
  title: "Elcaro Swarm — forensic findings",
  description:
    "Evidence-cited forensic analysis of a real agent swarm: provenance graphs, patient-zero tracing, and integrity auditing over the German Wiki incident corpus.",
};

const STATS: [string, string][] = [
  ["26,405", "messages analyzed"],
  ["6,319", "flags ≥0.5 risk"],
  ["5,658", "swarm directives"],
  ["7,535", "propagated artifacts"],
  ["59", "evasion pages"],
  ["499", "covert links"],
];

export default function SwarmPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="swarm" />

      <div className="flex-1 w-full px-6 py-10 space-y-8">
        {/* Intro */}
        <div className="page-enter max-w-5xl mx-auto space-y-4">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            Elcaro Swarm
          </h1>
          <p className="text-base text-ink-muted leading-relaxed max-w-2xl">
            Forensic analysis of a real agent swarm — the German Wiki incident
            corpus (collusion.wiki). Provenance graphs trace every shared
            artifact from patient-zero through its adopters; the integrity
            auditor surfaces deletion evasion, impersonation, and covert
            channels; the detection engine tags agent-to-agent steering that
            classic injection classes miss. Every claim cites a corpus id.
          </p>
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

        {/* The generated findings dashboard */}
        <div className="max-w-6xl mx-auto">
          <iframe
            src="/swarm/dashboard.html"
            title="Elcaro Swarm findings dashboard — German Wiki incident corpus"
            className="w-full rounded-xl border border-border bg-[#0b0e14] h-[1600px]"
          />
          <p className="text-xs text-ink-faint mt-3 leading-relaxed">
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

        {/* Second corpus: the hackathon-provided AI Village export */}
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="space-y-1">
            <h2 className="text-2xl font-black tracking-tight">
              Same pipeline, second corpus — AI Village
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
              The hackathon-provided transcript export (aidigestorg/ai-village):
              183,485 messages across 16 rooms, 31 named agents. The
              steering register generalizes — 24,876 flags, 9,347 directives
              — and propagations trace information diffusion with named
              origins.
            </p>
          </div>
          <iframe
            src="/swarm/dashboard-aivillage.html"
            title="Elcaro Swarm findings dashboard — AI Village transcript corpus"
            className="w-full rounded-xl border border-border bg-[#0b0e14] h-[1600px]"
          />
        </div>
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
