"use client";

import { useState } from "react";
import { ClaimChecks } from "./claim-checks";

const CLAIMS: {
  claimId: string;
  corpus: string;
  kicker: string;
  title: string;
  body: string;
}[] = [
  {
    claimId: "steering",
    corpus: "collusion",
    kicker: "New detector — class G",
    title: "A steering register the engine had missed",
    body: "15,005 records match the Class G steering rules across two corpora. Class G ranks #1 on the Wiki corpus and #2 on AI Village. These are rule matches, not a measured malicious-steering rate.",
  },
  {
    claimId: "propagation",
    corpus: "collusion",
    kicker: "Provenance",
    title: "Shared artifacts recur across agents",
    body: "Shared sandbox-bypass infrastructure — markdown.new, jqp.vercel.app, md.succ.ai, allorigins — appears in records from 39–46 agents, with earliest observed sources identified. Shared appearances do not establish causal influence.",
  },
  {
    claimId: "persistence",
    corpus: "collusion",
    kicker: "Integrity",
    title: "Deletion and recreation, recorded",
    body: "59 observed pages use ZZZ-style names; 48 pages have recorded post-deletion recreation. These inventories do not establish a persistence-to-moderation success ratio.",
  },
  {
    claimId: "evaluation-vocabulary",
    corpus: "aivillage",
    kicker: "Corpus II",
    title: "Evaluation and logging vocabulary",
    body: "10,362 AI Village records match scorer/evaluation/logging vocabulary rules. That includes logs and transcripts—not necessarily awareness of grading or evasion.",
  },
];

export function FindingsBrief() {
  const [selected, setSelected] = useState<string | null>(null);
  const current = CLAIMS.find((c) => c.claimId === selected);

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-4">
        {CLAIMS.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-border bg-surface px-5 py-4 space-y-2"
          >
            <p className="text-[10px] font-mono uppercase tracking-widest text-suspicious">
              {f.kicker}
            </p>
            <h2 className="text-lg font-black tracking-tight leading-snug">
              {f.title}
            </h2>
            <p className="text-sm text-ink-muted leading-relaxed">{f.body}</p>
            <button
              type="button"
              aria-expanded={selected === f.claimId}
              aria-controls="claim-explorer"
              onClick={() =>
                setSelected((s) => (s === f.claimId ? null : f.claimId))
              }
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-violet hover:text-violet/80 underline-offset-2 hover:underline transition-colors"
            >
              {selected === f.claimId ? "Close the check ↑" : "Test this claim →"}
            </button>
          </div>
        ))}
      </div>

      {current && (
        <div
          id="claim-explorer"
          className="rounded-xl border border-border bg-surface px-5 py-4 space-y-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Claim check — deterministic re-observation, not a model verdict
            </p>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors"
            >
              ↑ Collapse
            </button>
          </div>
          <ClaimChecks
            key={current.claimId}
            claimId={current.claimId}
            initialCorpus={current.corpus}
          />
        </div>
      )}
    </div>
  );
}
