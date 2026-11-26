"use client";

import { useState } from "react";
import { useReducedMotion } from "framer-motion";
import { TangemStageArt, type StagePhase } from "./tangem-stage-art";
import { TangemCaseFigure } from "./tangem-case-figure";
import type { WorkshopCase } from "@/lib/tangem-casebook";
import styles from "./tangem-stage.module.css";

// Public, credential-free metadata only. Direct browser GET, user-triggered —
// no proxy, no mount-time or scan-time requests, no QR, no tools/list.
const METADATA_URL =
  "https://mcp.tangem.org/.well-known/oauth-protected-resource/mcp";
const EXPECTED_RESOURCE_NAME = "Tangem MCP";
const EXPECTED_RESOURCE = "https://mcp.tangem.org/mcp";
const EXPECTED_AUTH_SERVER = "https://authentication.tangem.org";

async function fetchTangemMetadata(): Promise<boolean> {
  try {
    const res = await fetch(METADATA_URL, {
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return false;
    const body: unknown = await res.json();
    if (typeof body !== "object" || body === null) return false;
    const doc = body as Record<string, unknown>;
    return (
      doc.resource_name === EXPECTED_RESOURCE_NAME &&
      doc.resource === EXPECTED_RESOURCE &&
      Array.isArray(doc.authorization_servers) &&
      doc.authorization_servers.includes(EXPECTED_AUTH_SERVER)
    );
  } catch {
    return false;
  }
}

export function TangemDiscoveryStage({
  caseDef,
  onInspect,
}: {
  caseDef: WorkshopCase;
  onInspect: () => void;
}) {
  const reduceMotion = useReducedMotion() ?? false;
  const [phase, setPhase] = useState<StagePhase>("idle");

  async function discover() {
    if (phase === "pending") return;
    setPhase("pending");
    const ok = await fetchTangemMetadata();
    setPhase(ok ? "success" : "failed");
  }

  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-[0.2em] text-ink-faint">
          Casebook &nbsp;·&nbsp; Tangem × Elcaro &nbsp;·&nbsp; Signing stays
          with the cardholder
        </p>
        <h2 className="text-[28px] sm:text-[40px] font-black tracking-tight leading-none">
          {caseDef.headline}
        </h2>
        <p className="text-sm text-ink-muted leading-relaxed">
          You asked — {caseDef.intent}
        </p>
      </div>

      {/* Specimen figure + the readings the audience should hold
          before any scan — visible ahead of Inspect. */}
      <TangemCaseFigure figure={caseDef.figure} tell={caseDef.tell} />
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            Source says
          </p>
          <p className="text-sm text-ink leading-relaxed">{caseDef.fact}</p>
          <p className="text-xs text-ink-faint leading-relaxed">
            {caseDef.source}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            If the agent obeys
          </p>
          <p className="text-sm text-ink-muted leading-relaxed">
            {caseDef.stakes}
          </p>
        </div>
      </div>

      {/* Tangem public endpoint — a separate, optional control. The card
          still-life belongs to this strip, not to the specimen. */}
      <div className="rounded-xl border border-border px-4 py-4 space-y-3">
        <p className="text-[10px] uppercase tracking-wide text-ink-faint">
          Tangem public endpoint · optional
        </p>
        <div className={styles.plate}>
          <TangemStageArt phase={phase} reduceMotion={reduceMotion} />
        </div>
        <div aria-live="polite" className="space-y-1">
          {phase === "success" && (
            <>
              <p className="text-sm font-semibold text-safe">
                Public metadata received.
              </p>
              {/* proof of the real fetch — fixed validated constants,
                  rendered only on success; never raw document fields */}
              <div className="font-mono text-xs text-ink-muted space-y-0.5">
                <p>↳ {EXPECTED_RESOURCE.replace("https://", "")}</p>
                <p>↳ {EXPECTED_AUTH_SERVER.replace("https://", "")}</p>
              </div>
              <p className="text-xs text-ink-muted leading-relaxed">
                Wallet not paired · no signature requested. Listing actual
                tools needs the paired terminal — signing stays with the
                cardholder.
              </p>
            </>
          )}
          {phase === "failed" && (
            <p className="text-sm font-semibold text-dangerous">
              Unavailable · wallet not connected.
            </p>
          )}
          {phase === "idle" && (
            <p className="text-xs text-ink-muted leading-relaxed">
              Public side only: this browser can read Tangem’s public
              protected-resource metadata. The signer stays behind the card.
            </p>
          )}
        </div>
        <button
          onClick={discover}
          disabled={phase === "pending"}
          className="rounded-lg border border-ink/25 text-ink text-xs font-semibold px-4 py-2 hover:bg-ink/5 transition-colors disabled:opacity-50"
        >
          {phase === "pending"
            ? "Contacting…"
            : phase === "failed"
              ? "Retry discovery"
              : phase === "success"
                ? "Refresh metadata"
                : "Discover Tangem MCP"}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onInspect}
          className="rounded-lg bg-ink text-canvas text-sm font-semibold px-6 py-3 hover:bg-ink/90 transition-colors"
        >
          {caseDef.inspectLabel}
        </button>
      </div>
    </div>
  );
}
