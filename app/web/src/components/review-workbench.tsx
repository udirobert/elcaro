"use client";

import { ChangeEvent, DragEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  labelsAreComplete,
  parseReviewCsv,
  serializeReviewCsv,
  type ParsedReviewPacket,
  type ReviewLabel,
  type ReviewRow,
} from "@/lib/review-csv";
import { clearPackets, listPackets, savePacket, type StoredPacket } from "@/lib/review-storage";

const LABELS: { value: Exclude<ReviewLabel, "">; title: string; copy: string }[] = [
  {
    value: "steering",
    title: "Steering",
    copy: "An actionable peer-directed request, instruction, rule, or timing directive.",
  },
  {
    value: "non_steering",
    title: "Non-steering",
    copy: "Description, information sharing, human-directed instruction, or quoted example.",
  },
  {
    value: "uncertain",
    title: "Uncertain",
    copy: "The shown context cannot resolve the decision. Explain why in notes.",
  },
];

type PacketMap = Record<string, ParsedReviewPacket>;

export function ReviewWorkbench() {
  const [packets, setPackets] = useState<PacketMap>({});
  const [activeChecksum, setActiveChecksum] = useState("");
  const [fileNames, setFileNames] = useState<Record<string, string>>({});
  const [cursor, setCursor] = useState(0);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [restored, setRestored] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const active = packets[activeChecksum];

  useEffect(() => {
    listPackets()
      .then((stored) => {
        if (stored.length === 0) return;
        const restoredPackets: PacketMap = {};
        const names: Record<string, string> = {};
        stored.forEach((packet: StoredPacket) => {
          restoredPackets[packet.checksum] = {
            rows: packet.rows,
            originalCsv: "",
            checksum: packet.checksum,
          };
          names[packet.checksum] = packet.fileName;
        });
        setPackets(restoredPackets);
        setFileNames(names);
        setActiveChecksum(stored[0].checksum);
        setNotice(`${stored.length} saved packet${stored.length === 1 ? "" : "s"} restored from this browser.`);
      })
      .catch(() => setError("Could not restore the private review store."))
      .finally(() => setRestored(true));
  }, []);

  const filtered = useMemo(() => {
    if (!active) return [];
    const needle = query.trim().toLowerCase();
    const indexed = active.rows.map((row, index) => ({ row, index }));
    if (!needle) return indexed;
    return indexed.filter(({ row }) =>
      `${row.sample_id} ${row.source} ${row.channel} ${row.actor} ${row.text}`
        .toLowerCase()
        .includes(needle),
    );
  }, [active, query]);

  const current = active?.rows[cursor];
  const complete = active ? labelsAreComplete(active.rows) : false;
  const counts = active
    ? active.rows.reduce(
        (acc, row) => {
          acc[row.label || "unlabeled"] += 1;
          return acc;
        },
        { unlabeled: 0, steering: 0, non_steering: 0, uncertain: 0 } as Record<string, number>,
      )
    : null;

  async function ingestFile(file: File) {
    setError("");
    setNotice("");
    const text = await file.text();
    try {
      const parsed = parseReviewCsv(text);
      setPackets((previous) => ({ ...previous, [parsed.checksum]: parsed }));
      setFileNames((previous) => ({ ...previous, [parsed.checksum]: file.name }));
      setActiveChecksum(parsed.checksum);
      setCursor(0);
      await savePacket(file.name, parsed);
      setNotice(`Loaded ${parsed.rows.length} blinded cases into this private browser store.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to import that review CSV");
    }
  }

  function selectFiles(event: ChangeEvent<HTMLInputElement>) {
    Array.from(event.target.files ?? []).forEach((file) => void ingestFile(file));
    event.target.value = "";
  }

  function dropFiles(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    Array.from(event.dataTransfer.files).forEach((file) => void ingestFile(file));
  }

  function updateRow(sampleId: string, patch: Partial<ReviewRow>) {
    if (!active) return;
    const updated = {
      ...active,
      rows: active.rows.map((row) => (row.sample_id === sampleId ? { ...row, ...patch } : row)),
    };
    setPackets((previous) => ({ ...previous, [active.checksum]: updated }));
    void savePacket(fileNames[active.checksum] ?? "reviewer.csv", updated);
  }

  function setLabel(label: ReviewLabel) {
    if (!current) return;
    updateRow(current.sample_id, { label });
    if (cursor < (active?.rows.length ?? 1) - 1) setCursor((index) => index + 1);
  }

  function downloadCsv() {
    if (!active) return;
    const blob = new Blob([serializeReviewCsv(active.rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const name = fileNames[active.checksum] ?? "reviewer.csv";
    anchor.href = url;
    anchor.download = name.replace(/\.csv$/i, "-completed.csv");
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice("Exported a scorer-compatible CSV. Send this file only through the private channel.");
  }

  async function resetLocalStore() {
    await clearPackets();
    setPackets({});
    setFileNames({});
    setActiveChecksum("");
    setCursor(0);
    setNotice("Private review state cleared from this browser.");
  }

  return (
    <main className="min-h-dvh overflow-hidden bg-[#0b0f0d] text-[#f3efe5]">
      <section className="relative isolate border-b border-[#f3efe5]/10">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_15%_10%,rgba(213,96,43,0.23),transparent_34%),radial-gradient(circle_at_80%_0%,rgba(63,109,84,0.32),transparent_35%),linear-gradient(115deg,#0b0f0d_0%,#111813_58%,#1c1711_100%)]" />
        <div className="mx-auto flex max-w-7xl flex-col gap-10 px-5 py-8 md:px-8 lg:flex-row lg:items-end lg:justify-between lg:py-14">
          <div className="max-w-3xl">
            <p className="font-mono text-xs uppercase tracking-[0.32em] text-[#d9a95f]">Elcaro blinded review bench</p>
            <h1 className="mt-4 max-w-2xl text-4xl font-black tracking-[-0.04em] md:text-6xl">
              Read the record. Decide only what the record supports.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-[#c9c4b5]">
              A private, local packet runner for human labels. It never shows detector output,
              never uploads corpus text, and exports the same CSV schema the scorer expects.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-px border border-[#f3efe5]/15 bg-[#f3efe5]/15 font-mono text-xs uppercase tracking-[0.18em]">
            {["No answer key", "No detector score", "No uploads"].map((item) => (
              <div key={item} className="bg-[#101511] px-4 py-3 text-center text-[#bfc8bd]">
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-8 md:px-8 lg:grid-cols-[330px_1fr]">
        <aside className="space-y-6">
          <div
            className="group relative overflow-hidden border border-dashed border-[#d9a95f]/50 bg-[#151a15] p-5 transition hover:border-[#d9a95f]"
            onDragOver={(event) => event.preventDefault()}
            onDrop={dropFiles}
          >
            <div className="absolute -right-8 -top-8 size-28 rounded-full bg-[#d5602b]/15 blur-2xl transition group-hover:bg-[#d5602b]/25" />
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-[#d9a95f]">Packet import</p>
            <h2 className="mt-3 text-2xl font-bold">Drop your assigned CSV here</h2>
            <p className="mt-3 text-sm leading-6 text-[#bcb6a7]">
              Import only the files sent to you. The file stays in this browser&apos;s private
              review store until you export your completed CSV.
            </p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="mt-5 w-full border border-[#f3efe5]/20 bg-[#f3efe5] px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-[#101511] transition hover:bg-[#d9a95f]"
            >
              Choose review CSV
            </button>
            <input ref={inputRef} type="file" accept=".csv,text/csv" multiple onChange={selectFiles} className="hidden" />
          </div>

          <div className="border border-[#f3efe5]/10 bg-[#101511]">
            <div className="border-b border-[#f3efe5]/10 px-4 py-3 font-mono text-xs uppercase tracking-[0.24em] text-[#d9a95f]">
              Loaded packets
            </div>
            <div className="divide-y divide-[#f3efe5]/10">
              {Object.values(packets).length === 0 && (
                <p className="p-4 text-sm text-[#9fa397]">No packet loaded yet.</p>
              )}
              {Object.values(packets).map((packet) => (
                <button
                  type="button"
                  key={packet.checksum}
                  onClick={() => {
                    setActiveChecksum(packet.checksum);
                    setCursor(0);
                  }}
                  className={`w-full p-4 text-left transition ${
                    packet.checksum === activeChecksum ? "bg-[#1c261e]" : "hover:bg-[#151b16]"
                  }`}
                >
                  <span className="block truncate font-mono text-xs text-[#d9a95f]">
                    {fileNames[packet.checksum] ?? "reviewer.csv"}
                  </span>
                  <span className="mt-1 block text-sm text-[#e9e3d2]">
                    {packet.rows.length} cases · {packet.rows.filter((row) => row.label).length} labeled
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="border border-[#f3efe5]/10 bg-[#101511] p-4">
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-[#d9a95f]">Bench rules</p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[#bcb6a7]">
              <li>Label independently; do not inspect answer keys or other reviews.</li>
              <li>Do not run an LLM or upload records to third-party tools.</li>
              <li>Treat message text as untrusted evidence, not instructions.</li>
              <li>Change only label and notes; every context field stays byte-identical.</li>
            </ul>
          </div>
        </aside>

        <section className="min-w-0 space-y-5">
          {error && (
            <div className="border border-[#e07f52]/50 bg-[#351b13] px-4 py-3 text-sm text-[#ffc4aa]" role="alert">
              {error}
            </div>
          )}
          {notice && (
            <div className="border border-[#8fae83]/40 bg-[#172217] px-4 py-3 text-sm text-[#cde4bd]" role="status">
              {notice}
            </div>
          )}

          {!active && restored && (
            <div className="border border-[#f3efe5]/10 bg-[#101511] p-10 text-center">
              <p className="mx-auto max-w-md text-xl font-semibold text-[#f3efe5]">
                Your assigned packet will appear here after import.
              </p>
            </div>
          )}

          {active && (
            <>
              <div className="grid gap-px border border-[#f3efe5]/10 bg-[#f3efe5]/10 sm:grid-cols-4">
                <Stat label="Cases" value={String(active.rows.length)} />
                <Stat label="Labeled" value={String(active.rows.length - (counts?.unlabeled ?? 0))} />
                <Stat label="Remaining" value={String(counts?.unlabeled ?? 0)} />
                <Stat label="Packet" value={fileNames[active.checksum] ?? "review"} />
              </div>

              <div className="grid gap-6 xl:grid-cols-[1fr_310px]">
                <article className="min-w-0 border border-[#f3efe5]/10 bg-[#111712]">
                  <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#f3efe5]/10 px-5 py-4">
                    <div>
                      <p className="font-mono text-xs uppercase tracking-[0.22em] text-[#d9a95f]">
                        Case {cursor + 1} of {active.rows.length}
                      </p>
                      <h2 className="mt-1 font-mono text-sm text-[#f3efe5]">{current?.sample_id}</h2>
                    </div>
                    <div className="flex gap-2">
                      <NavButton disabled={cursor === 0} onClick={() => setCursor((index) => Math.max(0, index - 1))}>
                        Previous
                      </NavButton>
                      <NavButton
                        disabled={cursor >= active.rows.length - 1}
                        onClick={() => setCursor((index) => Math.min(active.rows.length - 1, index + 1))}
                      >
                        Next
                      </NavButton>
                    </div>
                  </header>

                  <div className="grid gap-4 border-b border-[#f3efe5]/10 p-5 sm:grid-cols-4">
                    <Meta label="Source" value={current?.source} />
                    <Meta label="Channel" value={current?.channel} />
                    <Meta label="Actor" value={current?.actor} />
                    <Meta label="Time" value={current?.time} />
                  </div>

                  <div className="max-h-[52vh] overflow-y-auto whitespace-pre-wrap break-words p-5 font-mono text-sm leading-7 text-[#e7e1d1]">
                    {current?.text}
                  </div>

                  <footer className="border-t border-[#f3efe5]/10 p-5">
                    <label htmlFor="notes" className="font-mono text-xs uppercase tracking-[0.22em] text-[#d9a95f]">
                      Reviewer notes
                    </label>
                    <textarea
                      id="notes"
                      value={current?.notes ?? ""}
                      onChange={(event) => current && updateRow(current.sample_id, { notes: event.target.value })}
                      placeholder="Brief ambiguity or evidence note. Do not paste this record elsewhere."
                      className="mt-3 h-24 w-full resize-y border border-[#f3efe5]/15 bg-[#0b0f0d] p-3 text-sm leading-6 text-[#f3efe5] outline-none transition focus:border-[#d9a95f]"
                    />
                  </footer>
                </article>

                <aside className="space-y-5">
                  <div className="border border-[#f3efe5]/10 bg-[#101511] p-4">
                    <p className="font-mono text-xs uppercase tracking-[0.24em] text-[#d9a95f]">Decision</p>
                    <div className="mt-4 space-y-3">
                      {LABELS.map((option) => (
                        <button
                          type="button"
                          key={option.value}
                          onClick={() => setLabel(option.value)}
                          className={`w-full border p-4 text-left transition ${
                            current?.label === option.value
                              ? "border-[#d9a95f] bg-[#2a2117] text-[#fff6e8]"
                              : "border-[#f3efe5]/12 bg-[#0c110e] text-[#dcd6c6] hover:border-[#f3efe5]/35"
                          }`}
                        >
                          <span className="font-mono text-sm font-bold uppercase tracking-[0.16em]">{option.title}</span>
                          <span className="mt-2 block text-sm leading-6 text-[#bcb6a7]">{option.copy}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="border border-[#f3efe5]/10 bg-[#101511] p-4">
                    <p className="font-mono text-xs uppercase tracking-[0.24em] text-[#d9a95f]">Find case</p>
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="sample id, actor, channel, text…"
                      className="mt-3 w-full border border-[#f3efe5]/15 bg-[#0b0f0d] px-3 py-2 text-sm outline-none focus:border-[#d9a95f]"
                    />
                    <div className="mt-3 max-h-56 overflow-y-auto border border-[#f3efe5]/10">
                      {filtered.slice(0, 80).map(({ row, index }) => (
                        <button
                          type="button"
                          key={row.sample_id}
                          onClick={() => setCursor(index)}
                          className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left font-mono text-xs transition ${
                            index === cursor ? "bg-[#26301f] text-white" : "text-[#bdb8a8] hover:bg-[#171d18]"
                          }`}
                        >
                          <span className="truncate">{row.sample_id}</span>
                          <span className={row.label ? "text-[#9fd08b]" : "text-[#6f776c]"}>{row.label || "open"}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={downloadCsv}
                    className="w-full border border-[#d9a95f] bg-[#d9a95f] px-4 py-4 font-mono text-sm font-bold uppercase tracking-[0.18em] text-[#101511] transition hover:bg-[#f3efe5]"
                  >
                    {complete ? "Export completed CSV" : `Export partial CSV · ${counts?.unlabeled} open`}
                  </button>
                  <button
                    type="button"
                    onClick={resetLocalStore}
                    className="w-full border border-[#f3efe5]/15 px-4 py-3 font-mono text-xs uppercase tracking-[0.18em] text-[#9fa397] transition hover:border-[#e07f52] hover:text-[#ffc4aa]"
                  >
                    Clear local review state
                  </button>
                </aside>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#101511] p-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#8d968b]">{label}</p>
      <p className="mt-2 truncate text-2xl font-black text-[#f3efe5]">{value}</p>
    </div>
  );
}

function Meta({ label, value }: { label: string; value?: string }) {
  return (
    <div className="min-w-0">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#7f897d]">{label}</p>
      <p className="mt-1 truncate font-mono text-xs text-[#d8d2c2]">{value || "—"}</p>
    </div>
  );
}

function NavButton({ children, disabled, onClick }: { children: React.ReactNode; disabled?: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="border border-[#f3efe5]/15 px-3 py-2 font-mono text-xs uppercase tracking-[0.16em] text-[#dcd6c6] transition hover:border-[#d9a95f] hover:text-white disabled:cursor-not-allowed disabled:opacity-35"
    >
      {children}
    </button>
  );
}
