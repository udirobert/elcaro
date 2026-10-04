"use client";

import { useEffect, useMemo, useState } from "react";

interface HuntReceipt {
  record_id?: string;
  source?: string;
  channel?: string;
  actor?: string;
  time?: string;
  original_time?: string;
  matched_text?: string;
  char_offset?: number | null;
}

interface HuntSegment {
  hour_utc: string;
  records: number;
  distinct_actor_labels: number;
  receipts: HuntReceipt[];
}

interface HuntCandidate {
  id: string;
  kind: string;
  source: string;
  channel: string;
  artifact: string;
  assertion: string;
  status: string;
  discovery: HuntSegment[];
  holdout: HuntSegment[];
  replicated_holdout_hours: number;
  copied_discovery_text_records_excluded: number;
  eligible_discovery_records_in_channel: number;
  eligible_holdout_records_in_channel: number;
  legs: Record<string, string>;
  refused_inference: string;
}

interface HuntIndex {
  schema_version: number;
  corpus: string;
  method: Record<string, unknown>;
  accounting: Record<string, number>;
  discovery_days: string[];
  holdout_days: string[];
  candidate_count: number;
  replicated_observation_count: number;
  candidates: HuntCandidate[];
  pages: { src: string; candidate_count: number }[];
}

interface HuntPage {
  candidates: HuntCandidate[];
}

const STATUS_WORDING: Record<string, string> = {
  replicated_observation: "observations repeated in holdout, not confirmed coordination",
  unreplicated_candidate: "unreplicated candidate — no qualifying holdout hour",
};

function statusWording(status: string): string {
  return STATUS_WORDING[status] ?? status;
}

function statusTone(status: string): string {
  if (status === "replicated_observation")
    return "border-emerald-600/40 bg-emerald-50 text-emerald-800";
  return "border-suspicious/40 bg-suspicious-bg text-suspicious";
}

function Field({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="min-w-0 text-sm">
      <div className="text-ink-faint break-words">{label}</div>
      <div className="font-mono text-ink min-w-0 break-words">
        {typeof value === "string" ? value : JSON.stringify(value)}
      </div>
    </div>
  );
}

function Segment({ label, segment }: { label: string; segment: HuntSegment }) {
  return (
    <div className="space-y-1">
      <p className="font-mono text-[11px] text-ink break-all">
        {label} · {segment.hour_utc} — {segment.distinct_actor_labels} actor
        labels, {segment.records} {segment.records === 1 ? "record" : "records"}
      </p>
      <ul className="space-y-1.5">
        {segment.receipts.map((r, i) => (
          <li
            key={`${String(r.record_id)}-${i}`}
            className="rounded-md border border-border bg-canvas px-2 py-1.5 space-y-0.5 min-w-0"
          >
            <p className="font-mono text-[11px] text-ink break-all">
              {String(r.record_id ?? "")}
              {typeof r.char_offset === "number" && (
                <span className="text-ink-faint"> @ offset {r.char_offset}</span>
              )}
            </p>
            <p className="text-[11px] text-ink-faint break-words">
              {String(r.actor ?? "")}
              {r.source ? ` · ${String(r.source)}` : ""}
              {r.channel ? ` · ${String(r.channel)}` : ""}
              {r.original_time ? ` · recorded ${String(r.original_time)}` : ""}
              {r.time ? ` · UTC ${String(r.time)}` : ""}
            </p>
            {r.matched_text ? (
              <code className="block rounded bg-ink/[0.05] px-2 py-1 font-mono text-[11px] text-ink break-all whitespace-pre-wrap">
                {String(r.matched_text)}
              </code>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CandidateRow({ c }: { c: HuntCandidate }) {
  return (
    <li className="rounded-lg border border-border bg-surface px-3 py-2 space-y-2 min-w-0">
      <p className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${statusTone(c.status)}`}
        >
          {c.status}
        </span>
        <span className="font-mono text-[11px] text-ink-faint">
          {c.source} · {c.channel}
        </span>
      </p>
      <code className="block rounded bg-ink/[0.05] px-2 py-1 font-mono text-[11px] text-ink break-all whitespace-pre-wrap">
        {c.artifact}
      </code>
      <p className="text-xs text-ink-faint leading-relaxed break-words">
        {statusWording(c.status)} — {c.discovery.length} discovery{" "}
        {c.discovery.length === 1 ? "hour" : "hours"} ·{" "}
        {c.replicated_holdout_hours} replicated holdout{" "}
        {c.replicated_holdout_hours === 1 ? "hour" : "hours"} ·{" "}
        {c.copied_discovery_text_records_excluded} copied full-text{" "}
        {c.copied_discovery_text_records_excluded === 1 ? "record" : "records"}{" "}
        excluded
      </p>
      <details className="group">
        <summary className="cursor-pointer text-xs font-semibold text-violet hover:text-violet/80 transition-colors">
          Exact rules and receipts
        </summary>
        <div className="mt-2 space-y-2 min-w-0">
          <p className="text-xs text-ink-muted leading-relaxed break-words">
            {c.assertion}
          </p>
          <ul className="space-y-1">
            {Object.entries(c.legs ?? {}).map(([k, v]) => (
              <li key={k} className="text-xs text-ink-faint break-words">
                <span className="font-mono uppercase text-[10px] tracking-wider">
                  {k}
                </span>{" "}
                — {v}
              </li>
            ))}
          </ul>
          <p className="text-xs text-ink-faint italic leading-relaxed break-words">
            {c.refused_inference}
          </p>
          {c.discovery.map((s) => (
            <Segment key={`d-${s.hour_utc}`} label="Discovery" segment={s} />
          ))}
          {c.holdout.map((s) => (
            <Segment key={`h-${s.hour_utc}`} label="Holdout" segment={s} />
          ))}
        </div>
      </details>
    </li>
  );
}

export function HuntCandidates({ corpus }: { corpus: string }) {
  const [index, setIndex] = useState<HuntIndex | null>(null);
  const [pages, setPages] = useState<HuntCandidate[][]>([]);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [loadingPage, setLoadingPage] = useState(false);
  const loading = !index && !indexError;
  const pagePattern = useMemo(
    () => new RegExp(`^/swarm/hunt-${corpus}-\\d{4,}\\.json$`),
    [corpus],
  );

  const fetchPage = (n: number) => {
    const entry = index?.pages[n];
    if (!entry || !pagePattern.test(entry.src)) return;
    setLoadingPage(true);
    fetch(entry.src, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HuntPage>;
      })
      .then((page) => {
        setPages((prev) => {
          if (prev.length !== n) return prev;
          return [...prev, page.candidates ?? []];
        });
        setPageError(null);
      })
      .catch((e: unknown) => {
        setPageError(
          `Page ${n + 1} of ${index.pages.length} failed to load (${e instanceof Error ? e.message : "fetch failed"}).`,
        );
      })
      .finally(() => setLoadingPage(false));
  };

  useEffect(() => {
    if (index || indexError) return;
    let cancelled = false;
    let loaded: HuntIndex | null = null;
    fetch(`/swarm/hunt-${corpus}.json`, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HuntIndex>;
      })
      .then((d) => {
        loaded = d;
        const first = d.pages?.[0];
        if (!first || !pagePattern.test(first.src)) return null;
        return fetch(first.src, { cache: "no-store" }).then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json() as Promise<HuntPage>;
        });
      })
      .then((page) => {
        if (cancelled || !loaded) return;
        setIndex(loaded);
        if (page) setPages([page.candidates ?? []]);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (loaded) {
          setIndex(loaded);
          setPageError(
            `Page 1 failed to load (${e instanceof Error ? e.message : "fetch failed"}).`,
          );
        } else {
          setIndexError(
            `The hunt snapshot for this corpus has not been generated yet (${e instanceof Error ? e.message : "fetch failed"}).`,
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [corpus, index, indexError, pagePattern]);

  const candidates = pages.flat();
  const total = index?.candidate_count ?? 0;
  const remaining = total - candidates.length;

  return (
    <div className="space-y-4 min-w-0">
      {loading && (
        <p className="text-sm text-ink-muted" role="status">
          Loading the hunt snapshot…
        </p>
      )}
      {indexError && (
        <div className="space-y-2" role="alert">
          <p className="text-sm text-ink-muted break-words">{indexError}</p>
          <button
            type="button"
            onClick={() => setIndexError(null)}
            className="text-sm font-semibold text-violet hover:text-violet/80 underline underline-offset-2 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {index && (
        <>
          <div className="space-y-1">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Method and disclaimers
            </p>
            <p className="rounded-lg border border-suspicious/40 bg-suspicious-bg px-3 py-2 text-sm text-ink leading-relaxed break-words">
              Exploratory screening over the supplied normalized records —
              <strong> not</strong> a significance test, a confirmed
              coordination finding, or a causal claim. The holdout split is
              unlabeled: it is not a benign negative control.
            </p>
            <ul className="space-y-1 pt-1">
              {Object.entries(index.method ?? {}).map(([k, v]) => (
                <li key={k} className="text-xs text-ink-faint break-words">
                  <span className="font-mono uppercase text-[10px] tracking-wider">
                    {k}
                  </span>{" "}
                  — {String(v)}
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-1">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Split and counts
            </p>
            <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
              <Field
                label="discovery days (sha256 day hash, bucket 0)"
                value={index.discovery_days.length}
              />
              <Field
                label="holdout days (bucket 1)"
                value={index.holdout_days.length}
              />
              <Field label="candidates" value={index.candidate_count} />
              <Field
                label="observations repeated in holdout, not confirmed coordination"
                value={index.replicated_observation_count}
              />
            </div>
            <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2 pt-1">
              {Object.entries(index.accounting ?? {}).map(([k, v]) => (
                <Field key={k} label={k} value={v} />
              ))}
            </div>
          </div>

          <div className="space-y-2 min-w-0">
            <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
              Candidates — stable discovery order · {candidates.length} of{" "}
              {total} loaded
            </p>
            {total === 0 && (
              <p className="text-sm text-ink-muted">
                No candidates in this snapshot.
              </p>
            )}
            <ul className="space-y-2">
              {candidates.map((c) => (
                <CandidateRow key={c.id} c={c} />
              ))}
            </ul>
            {loadingPage && (
              <p className="text-sm text-ink-muted" role="status">
                Loading the next page…
              </p>
            )}
            {pageError && (
              <div className="space-y-1" role="alert">
                <p className="text-sm text-ink-muted break-words">{pageError}</p>
                <button
                  type="button"
                  disabled={loadingPage}
                  onClick={() => fetchPage(pages.length)}
                  className="text-sm font-semibold text-violet hover:text-violet/80 underline underline-offset-2 transition-colors disabled:opacity-50"
                >
                  Retry this page
                </button>
              </div>
            )}
            {!pageError && remaining > 0 && (
              <button
                type="button"
                disabled={loadingPage}
                onClick={() => fetchPage(pages.length)}
                className="text-sm font-semibold text-violet hover:text-violet/80 underline underline-offset-2 transition-colors disabled:opacity-50"
              >
                Show {Math.min(12, remaining)} more
              </button>
            )}
            <p className="text-xs text-ink-faint leading-relaxed break-words">
              <a
                href={`/swarm/hunt-${corpus}.json`}
                download
                className="underline underline-offset-2 hover:text-ink transition-colors"
              >
                Download the hunt index (same origin)
              </a>
              {" — "}
              the full report stays local:
              <code> python3 -m swarm hunt </code> writes
              <code> hunt.json</code> +<code> hunt-journal.jsonl</code> in the
              corpus out/ directory.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
