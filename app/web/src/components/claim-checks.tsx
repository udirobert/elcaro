"use client";

import { useEffect, useState } from "react";

interface ClaimReceipt {
  record_id?: string;
  actor?: string;
  source?: string;
  time?: string;
  matched_text?: string;
  char_offset?: number | null;
  page_key?: string;
  page_name?: string;
  [key: string]: unknown;
}

interface AdopterReceipt {
  msg_id?: string;
  actor?: string;
  time?: string;
  [key: string]: unknown;
}

interface PropagationEvidence {
  artifact?: string;
  origin?: ClaimReceipt;
  adopters?: number;
  retained_adopter_receipts?: AdopterReceipt[];
}

interface RateGroup {
  matches: number;
  eligible_records: number;
  rate: number | null;
  receipts?: ClaimReceipt[];
}

interface ClaimReference {
  method: string;
  selection: string;
  analysis_set: RateGroup;
  reference_set: RateGroup;
  limitation: string;
}

interface ClaimEntry {
  id: string;
  assertion: string;
  status: string;
  check: string;
  observed: Record<string, unknown>;
  evidence: Array<Record<string, unknown>>;
  limitations: string;
  reference?: ClaimReference | null;
}

interface ClaimLedger {
  schema_version: number;
  corpus: string;
  accounting: Record<string, unknown>;
  claims: ClaimEntry[];
  refusals: ClaimEntry[];
}

const CORPORA: [id: string, label: string][] = [
  ["collusion", "Corpus I — Wiki"],
  ["aivillage", "Corpus II — AI Village"],
];

type View = "check" | "journal" | "accounting";

const VIEWS: [id: View, label: string][] = [
  ["check", "Observation check"],
  ["journal", "Refusal journal"],
  ["accounting", "Input accounting"],
];

const STATUS_WORDING: Record<string, string> = {
  supported: "supported observation — not certified truth",
  insufficient_evidence: "insufficient evidence — inference refused",
  contradicted: "contradicted — retained references failed to resolve",
  not_applicable: "not applicable to this corpus",
};

function statusWording(status: string): string {
  return STATUS_WORDING[status] ?? status;
}

function statusTone(status: string): string {
  if (status === "supported")
    return "border-emerald-600/40 bg-emerald-50 text-emerald-800";
  if (status === "contradicted")
    return "border-red-600/40 bg-red-50 text-red-800";
  return "border-suspicious/40 bg-suspicious-bg text-suspicious";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function ObservedValue({ value }: { value: unknown }) {
  if (isRecord(value)) {
    return (
      <span className="break-words">
        {Object.entries(value)
          .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
          .join(" · ")}
      </span>
    );
  }
  if (Array.isArray(value)) {
    return <span className="break-words">{JSON.stringify(value)}</span>;
  }
  return <span className="break-words">{typeof value === "string" ? value : JSON.stringify(value)}</span>;
}

function Field({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="min-w-0 text-sm">
      <div className="text-ink-faint break-words">{label}</div>
      <div className="font-mono text-ink min-w-0">
        <ObservedValue value={value} />
      </div>
    </div>
  );
}

function RateRow({ label, group }: { label: string; group?: RateGroup }) {
  if (!group) return null;
  return (
    <tr className="border-t border-border">
      <th className="py-1.5 pr-4 text-left font-semibold text-ink-muted">
        {label}
      </th>
      <td className="py-1.5 pr-4 font-mono">{group.matches}</td>
      <td className="py-1.5 pr-4 font-mono">{group.eligible_records}</td>
      <td className="py-1.5 font-mono">
        {group.rate === null || group.rate === undefined
          ? "unavailable — 0 eligible"
          : group.rate.toFixed(4)}
      </td>
    </tr>
  );
}

function Receipt({ r }: { r: ClaimReceipt }) {
  return (
    <li className="rounded-lg border border-border bg-canvas px-3 py-2 space-y-1 min-w-0">
      <p className="font-mono text-[11px] text-ink break-all">
        {String(r.record_id ?? "")}
        {typeof r.char_offset === "number" && (
          <span className="text-ink-faint"> @ offset {r.char_offset}</span>
        )}
      </p>
      <p className="text-[11px] text-ink-faint break-words">
        {String(r.actor ?? "")}
        {r.source ? ` · ${String(r.source)}` : ""}
        {r.time ? ` · ${String(r.time)}` : ""}
        {r.page_key ? ` · page ${String(r.page_key)}` : ""}
      </p>
      {r.matched_text ? (
        <code className="block rounded bg-ink/[0.05] px-2 py-1 font-mono text-[11px] text-ink break-all whitespace-pre-wrap">
          {String(r.matched_text)}
        </code>
      ) : null}
    </li>
  );
}

function isPropagationEvidence(e: Record<string, unknown>): boolean {
  return "artifact" in e || "origin" in e;
}

function PropagationEvidenceItem({ e }: { e: PropagationEvidence }) {
  const adopters = (e.retained_adopter_receipts ?? []).map((a) => ({
    record_id: a.msg_id,
    actor: a.actor,
    time: a.time,
  }));
  return (
    <li className="rounded-lg border border-border bg-canvas px-3 py-2 space-y-2 min-w-0">
      <p className="font-mono text-[11px] text-ink break-all">
        {String(e.artifact ?? "")}
      </p>
      <p className="text-[11px] text-ink-faint">
        {typeof e.adopters === "number" ? `${e.adopters} adopters` : ""}
      </p>
      {e.origin && (
        <ul className="space-y-2">
          <Receipt r={e.origin} />
        </ul>
      )}
      {adopters.length > 0 && (
        <ul className="space-y-2">
          {adopters.map((a, i) => (
            <Receipt key={`${String(a.record_id)}-${i}`} r={a} />
          ))}
        </ul>
      )}
    </li>
  );
}

function EvidenceList({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <ul className="space-y-2">
      {items.map((e, i) =>
        isPropagationEvidence(e) ? (
          <PropagationEvidenceItem key={i} e={e as PropagationEvidence} />
        ) : (
          <Receipt key={`${String(e.record_id)}-${i}`} r={e as ClaimReceipt} />
        ),
      )}
    </ul>
  );
}

export function ClaimChecks({
  claimId,
  initialCorpus = "collusion",
}: {
  claimId: string;
  initialCorpus?: string;
}) {
  const [corpus, setCorpus] = useState(initialCorpus);
  const [view, setView] = useState<View>("check");
  const [cache, setCache] = useState<Record<string, ClaimLedger>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const error = errors[corpus] ?? null;
  const loading = !cache[corpus] && !error;

  useEffect(() => {
    if (cache[corpus] || errors[corpus]) return;
    let cancelled = false;
    fetch(`/swarm/claims-${corpus}.json`, { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ClaimLedger>;
      })
      .then((data) => {
        if (cancelled) return;
        setCache((c) => ({ ...c, [corpus]: data }));
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setErrors((prev) => ({
          ...prev,
          [corpus]: `The claim snapshot for this corpus is not available yet (${e instanceof Error ? e.message : "fetch failed"}).`,
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [corpus, cache, errors]);

  const ledger = cache[corpus];
  const entry = ledger?.claims.find((c) => c.id === claimId);

  return (
    <div className="space-y-4 min-w-0">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex flex-wrap gap-1.5">
          {CORPORA.map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={corpus === id}
              onClick={() => setCorpus(id)}
              className={`px-2.5 py-1 rounded-md border font-mono text-[10px] uppercase tracking-wider transition-colors ${
                corpus === id
                  ? "border-ink/40 bg-ink text-canvas"
                  : "border-border bg-surface text-ink-muted hover:text-ink hover:border-ink/30"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {VIEWS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={view === id}
              onClick={() => setView(id)}
              className={`px-2.5 py-1 rounded-md border font-mono text-[10px] uppercase tracking-wider transition-colors ${
                view === id
                  ? "border-violet/50 bg-violet/10 text-violet"
                  : "border-border bg-surface text-ink-muted hover:text-ink hover:border-ink/30"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <p className="text-sm text-ink-muted" role="status">
          Loading the claim snapshot…
        </p>
      )}
      {error && (
        <div className="space-y-2" role="alert">
          <p className="text-sm text-ink-muted break-words">{error}</p>
          <button
            type="button"
            onClick={() => {
              setErrors((e) => {
                const next = { ...e };
                delete next[corpus];
                return next;
              });
            }}
            className="text-sm font-semibold text-violet hover:text-violet/80 underline underline-offset-2 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {ledger && view === "check" && (
        <div className="space-y-4 min-w-0">
          {!entry && (
            <p className="text-sm text-ink-muted">
              No ledger entry with id <code>{claimId}</code> exists in this
              corpus snapshot.
            </p>
          )}
          {entry && (
            <>
              <div className="space-y-1">
                <p className="text-sm text-ink leading-relaxed break-words">
                  <span className="font-semibold">Assertion:</span>{" "}
                  {entry.assertion}
                </p>
                <span
                  className={`inline-block rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${statusTone(entry.status)}`}
                >
                  {entry.status}
                </span>
                <p className="text-xs text-ink-faint italic break-words">
                  {statusWording(entry.status)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                  Exact check
                </p>
                <p className="text-sm text-ink-muted leading-relaxed break-words">
                  {entry.check}
                </p>
              </div>
              {Object.keys(entry.observed ?? {}).length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                    Observed data
                  </p>
                  <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                    {Object.entries(entry.observed).map(([k, v]) => (
                      <Field key={k} label={k} value={v} />
                    ))}
                  </div>
                </div>
              )}
              {entry.reference && (
                <div className="space-y-1 min-w-0">
                  <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                    Unlabeled analysis / reference split
                  </p>
                  <div className="overflow-x-auto">
                    <table className="text-sm">
                      <thead>
                        <tr className="text-left text-ink-faint">
                          <th className="pr-4 font-normal">set</th>
                          <th className="pr-4 font-normal">matches</th>
                          <th className="pr-4 font-normal">eligible</th>
                          <th className="font-normal">rate</th>
                        </tr>
                      </thead>
                      <tbody>
                        <RateRow
                          label="analysis"
                          group={entry.reference.analysis_set}
                        />
                        <RateRow
                          label="reference"
                          group={entry.reference.reference_set}
                        />
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-ink-faint leading-relaxed break-words">
                    {entry.reference.method} — {entry.reference.selection}
                  </p>
                  <p className="text-xs text-ink-faint leading-relaxed break-words">
                    {entry.reference.limitation}
                  </p>
                </div>
              )}
              <div className="space-y-1">
                <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                  Limitations
                </p>
                <p className="text-sm text-ink-muted leading-relaxed break-words">
                  {entry.limitations}
                </p>
              </div>
              {(entry.evidence ?? []).length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                    Receipts — record ids, offsets, matched text
                  </p>
                  <EvidenceList items={entry.evidence} />
                </div>
              )}
            </>
          )}
        </div>
      )}

      {ledger && view === "journal" && (
        <div className="space-y-3 min-w-0">
          <p className="text-xs text-ink-faint leading-relaxed">
            Every inference the ledger refused to support, kept on record
            with the reason. {(ledger.refusals ?? []).length}{" "}
            {(ledger.refusals ?? []).length === 1 ? "entry" : "entries"} in
            this snapshot.
          </p>
          <ul className="space-y-2">
            {(ledger.refusals ?? []).map((j) => (
              <li
                key={j.id}
                className="rounded-lg border border-border bg-canvas px-3 py-2 space-y-1 min-w-0"
              >
                <p className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[11px] text-ink break-all">
                    {j.id}
                  </span>
                  <span
                    className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${statusTone(j.status)}`}
                  >
                    {j.status}
                  </span>
                </p>
                <p className="text-sm text-ink-muted leading-relaxed break-words">
                  {j.assertion}
                </p>
                <p className="text-xs text-ink-faint leading-relaxed break-words">
                  Why refused: {j.check}
                </p>
                <p className="text-xs text-ink-faint leading-relaxed break-words">
                  {j.limitations}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {ledger && view === "accounting" && (
        <div className="space-y-3 min-w-0">
          <p className="rounded-lg border border-suspicious/40 bg-suspicious-bg px-3 py-2 text-sm text-ink leading-relaxed break-words">
            These counts describe the{" "}
            <strong>normalized supplied records only</strong> — they are not
            a measure of incident capture coverage, raw parse rejects,
            deduplicated input rows, or unseen activity.
          </p>
          <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
            {Object.entries(ledger.accounting)
              .filter(([k]) => k !== "scope")
              .map(([k, v]) => (
                <Field key={k} label={k} value={v} />
              ))}
          </div>
          {"scope" in ledger.accounting && (
            <p className="text-xs text-ink-faint leading-relaxed break-words">
              {String(ledger.accounting.scope)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
