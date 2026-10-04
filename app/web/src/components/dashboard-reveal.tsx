"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Progressive disclosure for the forensic dashboards. The page leads with a
// readable findings summary; the ~5,500px evidence artifact stays behind an
// explicit "open" so the page doesn't bury judges in tables. Same-origin, so
// the iframe auto-sizes to its content — expanding <details> accordions
// inside the dashboard re-measure via ResizeObserver.

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

  if (!open) {
    return (
      <div className="rounded-xl border border-border bg-surface px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <p className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
            Evidence dashboard · generated deterministically
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
      <div className="flex items-center justify-between gap-4">
        <button
          onClick={() => setOpen(false)}
          className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors"
        >
          ↑ Collapse the evidence
        </button>
        <a
          href={src}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-ink-muted hover:text-ink transition-colors underline-offset-2 hover:underline"
        >
          open full dashboard ↗
        </a>
      </div>
      <iframe
        ref={iframeRef}
        src={src}
        title={title}
        onLoad={handleLoad}
        style={{ height }}
        className="w-full rounded-xl border border-border bg-[#0b0e14]"
      />
    </div>
  );
}
