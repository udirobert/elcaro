"use client";

import { useEffect, useState } from "react";

type Miner = {
  id?: string;
  slug?: string;
  name?: string;
  activation_status?: string;
  endpoints?: { path?: string; method?: string }[];
};

type Catalog = {
  intent: string;
  source: string;
  miners: Miner[];
  error?: string;
};

export function TelegraphRail() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/telegraph/miners?intent=CONTENT_MODERATION", {
      cache: "no-store",
    })
      .then((r) => r.json())
      .then((data: Catalog) => {
        if (!cancelled) setCatalog(data);
      })
      .catch(() => {
        if (!cancelled) setCatalog({ intent: "", source: "", miners: [], error: "unreachable" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!catalog) {
    return (
      <p className="text-xs text-ink-faint font-mono">
        Loading live Telegraph catalog…
      </p>
    );
  }

  if (catalog.error || catalog.miners.length === 0) {
    return (
      <p className="text-xs text-ink-faint">
        Telegraph catalog unreachable right now. The miner is still registered
        as id 8848 — check{" "}
        <a
          href="https://devnode.telegraphprotocol.com/api/miners?intent=CONTENT_MODERATION"
          className="underline underline-offset-2"
          target="_blank"
          rel="noopener noreferrer"
        >
          /api/miners?intent=CONTENT_MODERATION
        </a>
        .
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5 space-y-3">
      <p className="text-sm font-semibold text-ink">
        Live Telegraph miners · CONTENT_MODERATION
      </p>
      <p className="text-xs text-ink-muted leading-relaxed">
        Fetched from the protocol node, not hardcoded. Track 3 judging requires
        applications to use Telegraph miners. Auto-routed{" "}
        <code className="font-mono bg-canvas border border-border px-1 rounded">
          POST /engine/v1/ask
        </code>{" "}
        is the rail that also counts as miner volume.
      </p>
      <ul className="space-y-2">
        {catalog.miners.map((m) => (
          <li
            key={m.id || m.slug}
            className="flex items-baseline justify-between gap-4 text-sm"
          >
            <span className="text-ink font-medium">
              {m.name || m.slug}
              <span className="ml-2 font-mono text-xs text-ink-faint">
                id {m.id}
              </span>
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-safe">
              {m.activation_status || "listed"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
