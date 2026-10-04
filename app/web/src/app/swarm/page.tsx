import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site-chrome";
import { DashboardReveal } from "@/components/dashboard-reveal";
import { FindingsBrief } from "@/components/findings-brief";

// Elcaro Swarm — forensic findings on real agent-swarms. The page leads with
// the story and a readable findings brief; the generated dashboards
// (`python3 -m swarm all`, single-file, evidence-cited) sit behind
// DashboardReveal so the evidence is one click away without burying the
// reader in tables.
export const metadata: Metadata = {
  title: "Elcaro Swarm — forensic findings",
  description:
    "Evidence-cited forensic analysis of real agent swarms: provenance graphs tracing shared artifacts to their earliest observed sources, and integrity auditing over the German Wiki incident and AI Village corpora.",
};

const STATS: [string, string][] = [
  ["209,890", "messages analyzed"],
  ["31,195", "flags ≥0.5 risk"],
  ["15,005", "swarm directives"],
  ["13,927", "propagated artifacts"],
  ["59", "evasion pages"],
  ["2", "incident corpora"],
];

const GH = "https://github.com/udirobert/elcaro";
const linkCls =
  "text-violet font-semibold underline underline-offset-2 hover:text-violet/80 transition-colors";

export default function SwarmPage() {
  return (
    <main className="min-h-dvh flex flex-col">
      {/* Shared chrome */}
      <SiteHeader active="swarm" />

      <div className="flex-1 w-full px-6 py-10 space-y-14">
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
              a provenance graph tracing every shared artifact from its
              earliest observed source through its adopters, an integrity auditor for
              evasion and impersonation, and a deterministic detection
              engine over inter-agent messages — every claim cited to a
              corpus id and character offset.
            </p>
            <p>
              Then we ran it on a second, independently documented incident —
              the German Wiki collusion dump. The largest single tag class
              was agent-to-agent steering phrasing — a steering register not
              explicitly modeled by the original detector taxonomy. That
              finding shipped as{" "}
              <a href={`${GH}/blob/main/docs/technique-reference.md`} className={linkCls}>
                class G
              </a>
              , a seventh detector — and on the AI Village corpus it
              wasn&apos;t tuned on, it immediately surfaced as the #2
              signal.
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

        {/* Findings in brief — readable before any evidence is opened */}
        <div className="max-w-5xl mx-auto space-y-5">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            Findings in brief — the evidence is one click down
          </p>
          <FindingsBrief />
        </div>

        {/* Corpus I — evidence behind a reveal */}
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="space-y-1">
            <h2 className="text-2xl font-black tracking-tight">
              Corpus I — the German Wiki incident
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
              The collusion.wiki dump: 26,405 deduplicated messages of agents
              colluding on timed eval tasks. Shared bypass artifacts recur
              across agents — earliest observed sources identified inside.
            </p>
          </div>
          <DashboardReveal
            src="/swarm/dashboard.html"
            title="Elcaro Swarm findings dashboard — German Wiki incident corpus"
            blurb="Five chapters in one dossier — technique incidence, propagation radials that draw themselves as you scroll, the earliest-source table, top influencers, and the integrity findings. Leaf through, or jump to a chapter."
          />
        </div>

        {/* Corpus II — evidence behind a reveal */}
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="space-y-1">
            <h2 className="text-2xl font-black tracking-tight">
              Corpus II — the AI Village transcripts
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
              The hackathon-provided export (aidigestorg/ai-village): 183,485
              messages across 16 rooms, 31 named agents. Same pipeline,
              unchanged code — and the agents use evaluation and logging
              vocabulary.
            </p>
          </div>
          <DashboardReveal
            src="/swarm/dashboard-aivillage.html"
            title="Elcaro Swarm findings dashboard — AI Village transcript corpus"
            blurb="The same five-chapter dossier on an untuned corpus — swarm_directive surfaces as the #2 signal, and the propagation reel shows status diffusing agent→agent with named origins."
          />
        </div>

        {/* Reproduce & evidence — the close judges can act on */}
        <div className="max-w-5xl mx-auto">
          <div className="rounded-xl border border-border bg-surface px-6 py-5 space-y-4">
            <div className="space-y-1">
              <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                Reproduce & verify
              </p>
              <h2 className="text-xl font-black tracking-tight">
                Deterministic, evidence-cited, no LLM in the loop
              </h2>
              <p className="text-sm text-ink-muted leading-relaxed max-w-2xl">
                Both dashboards are generated artifacts — ~2ms per message,
                every claim cited to a corpus id and character offset. The
                pipeline is four stages and one command:
              </p>
            </div>
            <div className="rounded-lg bg-ink/[0.04] border border-border px-4 py-3 font-mono text-sm text-ink overflow-x-auto">
              <span className="text-ink-faint"># corpus:</span>{" "}
              https://collusion.wiki/explorer/download{" "}
              <span className="text-ink-faint">→ data/swarm/</span>
              <br />
              python3 -m swarm all{" "}
              <span className="text-ink-faint">
                # ingest → scan → graph → integrity → findings
              </span>
            </div>
            <p className="text-sm text-ink-muted leading-relaxed">
              <a href={`${GH}/blob/main/docs/swarm-findings.md`} className={linkCls}>
                Full findings write-up
              </a>{" "}
              ·{" "}
              <a href={`${GH}/tree/main/swarm`} className={linkCls}>
                swarm/ source
              </a>{" "}
              ·{" "}
              <a href={`${GH}/blob/main/docs/technique-reference.md`} className={linkCls}>
                Class G technique reference
              </a>{" "}
              ·{" "}
              <a href={`${GH}/blob/main/docs/swarm-submission.md`} className={linkCls}>
                Hackathon submission
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Shared chrome */}
      <SiteFooter />
    </main>
  );
}
