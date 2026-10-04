import audit from "../../public/swarm/revision-audit.json";

const linkCls =
  "text-violet font-semibold underline underline-offset-2 hover:text-violet/80 transition-colors";

const fmt = (n: number) => n.toLocaleString("en-US");

function Receipt({
  id,
  actor,
  time,
  channel,
}: {
  id: string;
  actor: string;
  time: string;
  channel: string;
}) {
  return (
    <div className="font-mono text-xs text-ink-muted leading-relaxed break-words">
      <span className="text-ink">{id}</span> · {actor} · {time} · {channel}
    </div>
  );
}

export function SwarmCaseWalkthrough() {
  const c = audit.counts;
  const reuse = audit.artifact_reuse;

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="space-y-1">
        <p className="text-[10px] font-mono uppercase tracking-widest text-suspicious">
          Self-audit — what the tag counts actually mean
        </p>
        <h2 className="text-2xl font-black tracking-tight">
          A revision carry-forward correction, in three steps
        </h2>
        <p className="text-sm text-ink-muted leading-relaxed max-w-3xl">
          Class G counts tagged records, not unique directives. On the Wiki
          corpus many records are revisions of shared pages, so one authored
          line can reappear as the first detector hit across many revisions.
          This audit —{" "}
          <code className="text-xs">python3 -m swarm.revision_audit --data data/swarm</code>{" "}
          — is a methodological correction to Elcaro&apos;s own outputs, not a
          newly discovered agent exploit. Actor labels are not proven readers
          or intent.
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-surface px-5 py-4 space-y-2">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            1 — First matched span
          </p>
          <p className="text-sm text-ink-muted leading-relaxed">
            Record{" "}
            <code className="text-xs text-ink break-all">{audit.focus.first.id}</code>{" "}
            first matches{" "}
            <span className="font-mono text-xs text-ink">
              “{audit.focus.first_hit.matched_text}”
            </span>{" "}
            at character offset {audit.focus.first_hit.char_offset} — posted by{" "}
            {audit.focus.first.actor} at {audit.focus.first.time}.
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface px-5 py-4 space-y-2">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            2 — Revision carry-forward
          </p>
          <p className="text-sm text-ink-muted leading-relaxed">
            The identical first-hit prefix persists through all{" "}
            {audit.focus.revisions_with_same_first_hit_prefix} revisions of
            the page, last seen in{" "}
            <code className="text-xs text-ink break-all">{audit.focus.last.id}</code>{" "}
            at {audit.focus.last.time} under actor label{" "}
            {audit.focus.last.actor}. Fifteen hits ≠ fifteen independently
            authored instructions.
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface px-5 py-4 space-y-2">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            3 — Cohort audit
          </p>
          <p className="text-sm text-ink-muted leading-relaxed">
            Of {fmt(c.class_g_tagged_records)} tagged records,{" "}
            {fmt(c.wiki_tagged_revisions)} are wiki revisions:{" "}
            {fmt(c.wiki_valid_first_hit_revisions)} retain a valid first Class
            G hit ({c.wiki_without_retained_g_hit} don&apos;t), grouping into{" "}
            {fmt(c.wiki_unique_first_hit_loci)} unique first-hit prefixes with{" "}
            {fmt(c.wiki_repeated_first_hit_revisions)} additional carried-over
            revisions.
          </p>
        </div>
      </div>

      <details className="rounded-xl border border-border bg-surface px-5 py-4 group">
        <summary className="cursor-pointer text-sm font-semibold text-ink select-none">
          Revision chain and artifact recurrence receipts
        </summary>
        <div className="mt-4 space-y-5">
          <div className="space-y-1.5">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Focus locus — all {audit.focus.example_revision_ids.length}{" "}
              revision IDs sharing the “{audit.focus.first_hit.matched_text}”
              prefix at offset {audit.focus.first_hit.char_offset}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {audit.focus.example_revision_ids.map((id) => (
                <span
                  key={id}
                  className="rounded bg-ink/[0.04] border border-border px-2 py-0.5 font-mono text-xs text-ink-muted"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Separate observation — exact {reuse.host} URL recurrence
            </p>
            <p className="text-sm text-ink-muted leading-relaxed">
              The exact <span className="font-mono text-xs text-ink">{reuse.host}</span>{" "}
              URL appears in {reuse.matching_records} revision records under{" "}
              {reuse.distinct_actor_labels} actor labels across{" "}
              {reuse.distinct_source_channels} source/channel pairs, earliest
              observed at {reuse.earliest_observed.time}. An observed
              appearance is not evidence that an actor read the earlier post
              or acted on its contents — not proven reading, adoption, or
              causal propagation.
            </p>
            <div className="space-y-1">
              {reuse.independent_channel_examples.map((r) => (
                <Receipt
                  key={r.id}
                  id={r.id}
                  actor={r.actor}
                  time={r.time}
                  channel={r.channel}
                />
              ))}
            </div>
          </div>
        </div>
      </details>

      <p className="text-sm text-ink-muted leading-relaxed">
        <a href="/swarm/revision-audit.json" className={linkCls}>
          Download the audit JSON
        </a>{" "}
        ·{" "}
        <a
          href="https://collusion.wiki/explorer/download"
          className={linkCls}
          rel="noopener noreferrer"
        >
          collusion.wiki corpus
        </a>{" "}
        — the original incident report already documents proxy tooling and
        evasion; this audit recounts our own tag outputs.
      </p>
    </div>
  );
}
