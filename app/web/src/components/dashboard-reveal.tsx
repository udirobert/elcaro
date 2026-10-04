"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Progressive disclosure for the forensic dashboards. The page leads with a
// readable findings summary; the evidence artifact opens as a "dossier
// window" — a fixed-height frame whose inner document scroll-snaps through
// five numbered chapters with reveal-on-scroll animation (all pure CSS
// inside the artifact; it ships under a no-JS CSP). Chapter chips jump
// straight to a section, and an expand toggle switches to full-height
// inline mode for readers who want the whole document at once.

const CHAPTERS: [id: string, label: string][] = [
  ["incidence", "01 · incidence"],
  ["propagation", "02 · shared artifacts"],
  ["artifacts", "03 · earliest seen"],
  ["influencers", "04 · later actors"],
  ["integrity", "05 · integrity"],
];

const DOSSIER_HEIGHT = "min(78vh, 840px)";

export function DashboardReveal({
  src,
  title,
  blurb,
}: {
  src: string;
  title: string;
  blurb: string;
}) {
  const [open, setOpen] = useState(false);
  const [full, setFull] = useState(false);
  const [height, setHeight] = useState(1600);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const measure = useCallback(() => {
    const doc = iframeRef.current?.contentDocument;
    if (doc?.documentElement) {
      setHeight(doc.documentElement.scrollHeight);
    }
  }, []);

  const handleLoad = useCallback(() => {
    measure();
    const doc = iframeRef.current?.contentDocument;
    if (doc?.documentElement) {
      observerRef.current?.disconnect();
      const ro = new ResizeObserver(measure);
      ro.observe(doc.documentElement);
      observerRef.current = ro;
    }
  }, [measure]);

  useEffect(() => () => observerRef.current?.disconnect(), []);
  useEffect(() => {
    if (full) measure();
  }, [full, measure]);

  // Chapter jump: scroll the iframe's inner document in dossier mode; in
  // full-height mode the inner doc can't scroll, so scroll the outer page
  // to the element's position instead.
  const jumpTo = useCallback(
    (id: string) => {
      const frame = iframeRef.current;
      const el = frame?.contentDocument?.getElementById(id);
      if (!frame || !el) return;
      if (full) {
        const innerTop =
          el.getBoundingClientRect().top + (frame.contentWindow?.scrollY ?? 0);
        const frameTop = frame.getBoundingClientRect().top + window.scrollY;
        window.scrollTo({ top: frameTop + innerTop - 90, behavior: "smooth" });
      } else {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    },
    [full],
  );

  if (!open) {
    return (
      <div className="rounded-xl border border-border bg-surface px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            Evidence dossier · generated deterministically · five chapters
          </p>
          <p className="text-sm text-ink-muted mt-1.5 max-w-lg leading-relaxed">
            {blurb}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setOpen(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ink text-canvas text-sm font-semibold hover:bg-ink/90 active:opacity-90 transition-colors"
          >
            Open the evidence
            <span>↓</span>
          </button>
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors underline-offset-2 hover:underline"
          >
            full view ↗
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button
          onClick={() => setOpen(false)}
          className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors shrink-0"
        >
          ↑ Collapse
        </button>
        <div className="flex flex-wrap gap-1.5">
          {CHAPTERS.map(([id, label]) => (
            <button
              key={id}
              onClick={() => jumpTo(id)}
              className="px-2.5 py-1 rounded-md border border-border bg-surface font-mono text-[10px] uppercase tracking-wider text-ink-muted hover:text-ink hover:border-ink/30 transition-colors"
            >
              {label}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-4 shrink-0">
          <button
            onClick={() => setFull((f) => !f)}
            className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors"
          >
            {full ? "⤡ dossier view" : "⤢ expand full"}
          </button>
          <a
            href={src}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors underline-offset-2 hover:underline"
          >
            open full ↗
          </a>
        </div>
      </div>
      <iframe
        ref={iframeRef}
        src={src}
        title={title}
        onLoad={handleLoad}
        style={{ height: full ? height : DOSSIER_HEIGHT }}
        className="w-full rounded-xl border border-border bg-[#0b0e14] transition-[height] duration-300"
      />
    </div>
  );
}
