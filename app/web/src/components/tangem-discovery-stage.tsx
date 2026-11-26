"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

// Public, credential-free metadata only. Direct browser GET, user-triggered —
// no proxy, no mount-time or scan-time requests, no QR, no tools/list.
const METADATA_URL =
  "https://mcp.tangem.org/.well-known/oauth-protected-resource/mcp";
const EXPECTED_RESOURCE_NAME = "Tangem MCP";
const EXPECTED_RESOURCE = "https://mcp.tangem.org/mcp";
const EXPECTED_AUTH_SERVER = "https://authentication.tangem.org";

type Phase = "idle" | "pending" | "success" | "failed";

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

// Line-art handset scene — drawn, not photographic: a terminal, a public
// endpoint, a matte card behind a stop mark. Motion is illustrative only;
// every claim lives in the labels, so reduced motion loses nothing.
function Scene({
  phase,
  reduceMotion,
}: {
  phase: Phase;
  reduceMotion: boolean;
}) {
  const pending = phase === "pending";
  const success = phase === "success";
  const failed = phase === "failed";

  const enter = reduceMotion ? { duration: 0 } : { type: "spring" as const, stiffness: 120, damping: 18 };
  const draw = reduceMotion
    ? { duration: 0 }
    : { duration: 0.9, ease: "easeInOut" as const };

  return (
    <svg
      viewBox="0 0 640 300"
      role="img"
      aria-label="Diagram: an agent terminal can reach Tangem's public metadata endpoint, but a stop mark sits before the physical card."
      className="w-full max-w-[640px]"
    >
      {/* agent terminal */}
      <g>
        <rect x="24" y="120" width="96" height="60" rx="8" fill="none" stroke="var(--color-ink)" strokeOpacity="0.5" strokeWidth="2" />
        <rect x="34" y="132" width="44" height="4" rx="2" fill="var(--color-ink)" fillOpacity="0.35" />
        <rect x="34" y="142" width="60" height="4" rx="2" fill="var(--color-ink)" fillOpacity="0.2" />
        <rect x="34" y="152" width="30" height="4" rx="2" fill="var(--color-ink)" fillOpacity="0.35" />
        <text x="72" y="200" textAnchor="middle" fontSize="11" fill="var(--color-ink-muted)" fontFamily="var(--font-mono)">
          your agent
        </text>
      </g>

      {/* outbound path: terminal → public endpoint (drawn only on request) */}
      <motion.path
        d="M 120 140 L 470 80"
        fill="none"
        stroke="var(--color-teal)"
        strokeWidth="2"
        strokeDasharray="5 5"
        initial={{ pathLength: 0 }}
        animate={
          pending || success ? { pathLength: 1 } : { pathLength: failed ? 0.35 : 0 }
        }
        transition={draw}
      />
      {/* one outbound pulse while the request is in flight */}
      {pending && (
        <motion.circle
          r="5"
          fill="var(--color-teal)"
          initial={{ cx: 120, cy: 140, opacity: 1 }}
          animate={{ cx: 470, cy: 80, opacity: 0.15 }}
          transition={
            reduceMotion
              ? { duration: 0 }
              : { duration: 0.9, ease: "easeInOut" as const }
          }
        />
      )}
      {/* return path, success only */}
      {success && (
        <motion.path
          d="M 470 80 L 120 152"
          fill="none"
          stroke="var(--color-teal)"
          strokeWidth="2.5"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.7, ease: "easeOut", delay: 0.3 }}
        />
      )}

      {/* public endpoint */}
      <g>
        <circle
          cx="470"
          cy="80"
          r="14"
          fill="none"
          stroke={success ? "var(--color-teal)" : failed ? "var(--color-dangerous)" : "var(--color-ink)"}
          strokeOpacity={success ? 1 : 0.45}
          strokeWidth="2.5"
        />
        <circle cx="470" cy="80" r="4" fill={success ? "var(--color-teal)" : "var(--color-ink)"} fillOpacity={success ? 1 : 0.35} />
        <text x="470" y="58" textAnchor="middle" fontSize="11" fill="var(--color-ink-muted)" fontFamily="var(--font-mono)">
          public metadata
        </text>
      </g>

      {/* dashed path endpoint → card, broken at the stop mark */}
      <line x1="480" y1="92" x2="498" y2="106" stroke="var(--color-ink)" strokeOpacity="0.3" strokeWidth="2" strokeDasharray="4 6" />
      <line x1="524" y1="128" x2="540" y2="140" stroke="var(--color-ink)" strokeOpacity="0.3" strokeWidth="2" strokeDasharray="4 6" />
      {/* STOP — illustration only: no tap, no sign, no approval */}
      <g transform="translate(511,117)">
        <polygon
          points="0,-14 10,-10 14,0 10,10 0,14 -10,10 -14,0 -10,-10"
          fill="var(--color-dangerous-bg)"
          stroke="var(--color-dangerous)"
          strokeWidth="2"
        />
        <text y="4" textAnchor="middle" fontSize="9" fontWeight="800" fill="var(--color-dangerous)">
          STOP
        </text>
      </g>

      {/* the physical card — matte black, typographic, contour engraving.
          Static placement lives on the outer <g>; framer's animated transform
          on the inner <g> no longer fights it, so the card can't clip. */}
      <g transform="translate(486,216) rotate(-6) scale(1.8)">
        <motion.g
          initial={reduceMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={enter}
        >
          <rect x="-60" y="-38" width="120" height="76" rx="10" fill="#111" stroke="#000" strokeWidth="1" />
          {/* contour engraving */}
          <path d="M -52 -28 q 30 14 104 6" fill="none" stroke="#333" strokeWidth="1" />
          <path d="M -52 -18 q 34 16 104 8" fill="none" stroke="#2a2a2a" strokeWidth="1" />
          <path d="M -52 20 q 40 12 104 2" fill="none" stroke="#2a2a2a" strokeWidth="1" />
          {/* contactless arcs */}
          <path d="M -40 -6 a 8 8 0 0 1 0 12" fill="none" stroke="#555" strokeWidth="1.5" />
          <path d="M -34 -12 a 15 15 0 0 1 0 24" fill="none" stroke="#444" strokeWidth="1.5" />
          <path d="M -28 -18 a 22 22 0 0 1 0 36" fill="none" stroke="#333" strokeWidth="1.5" />
          <text x="18" y="2" textAnchor="middle" fontSize="15" fontWeight="800" fill="#e8e8e8" letterSpacing="3" fontFamily="var(--font-satoshi), system-ui">
            TANGEM
          </text>
          <text x="18" y="18" textAnchor="middle" fontSize="8" fill="#666" letterSpacing="1">
            YOUR CARD. YOUR KEYS.
          </text>
        </motion.g>
      </g>

      {/* stacked response tags — fixed labels, shown only after validation.
          Raw document fields are never rendered. */}
      {success && (
        <motion.g
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.35, delay: 0.5 }}
        >
          {["Tangem MCP", "mcp.tangem.org/mcp", "Authorization: authentication.tangem.org"].map(
            (label, i) => (
              <g key={label} transform={`translate(24, ${216 + i * 26})`}>
                <rect x="0" y="0" rx="6" width={label.length * 7.2 + 20} height="20" fill="var(--color-safe-bg)" stroke="var(--color-teal)" strokeOpacity="0.5" />
                <text x="10" y="14" fontSize="11" fontWeight="600" fill="var(--color-safe)" fontFamily="var(--font-mono)">
                  {label}
                </text>
              </g>
            )
          )}
        </motion.g>
      )}
    </svg>
  );
}

export function TangemDiscoveryStage({
  onInspect,
}: {
  onInspect: () => void;
}) {
  const reduceMotion = useReducedMotion() ?? false;
  const [phase, setPhase] = useState<Phase>("idle");

  async function discover() {
    if (phase === "pending") return;
    setPhase("pending");
    const ok = await fetchTangemMetadata();
    setPhase(ok ? "success" : "failed");
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduceMotion ? { duration: 0 } : { duration: 0.3 }}
      className="space-y-5"
    >
      <div className="space-y-1.5">
        <p className="text-[10px] uppercase tracking-wide text-ink-faint">
          Field test 01 · Tangem MCP
        </p>
        <h2 className="text-[28px] sm:text-[40px] font-black tracking-tight leading-none">
          Tangem keeps signing in your hands.
        </h2>
        <p className="text-sm text-ink leading-relaxed max-w-xl">
          You asked for a market summary, not a swap. If the report steers the
          agent, it could propose a trade you never requested. Elcaro checks
          that report; only the cardholder decides what to sign.
        </p>
      </div>

      <Scene phase={phase} reduceMotion={reduceMotion} />

      <div className="space-y-1" aria-live="polite">
        {phase === "success" && (
          <>
            <p className="text-sm font-semibold text-safe">
              Public metadata received.
            </p>
            <p className="text-xs text-ink-muted leading-relaxed">
              Wallet not paired · no signature requested. Listing actual tools
              needs the paired terminal — signing stays with the cardholder.
            </p>
            <p className="text-sm text-ink font-medium">Next: inspect the note.</p>
          </>
        )}
        {phase === "failed" && (
          <p className="text-sm font-semibold text-dangerous">
            Unavailable · wallet not connected.
          </p>
        )}
        {phase === "idle" && (
          <p className="text-xs text-ink-muted leading-relaxed">
            Press Discover to fetch Tangem’s public metadata directly from
            this browser — no account, no pairing, nothing signed.
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={discover}
          disabled={phase === "pending"}
          className="rounded-lg bg-ink text-canvas text-sm font-semibold px-6 py-3 hover:bg-ink/90 transition-colors disabled:opacity-50"
        >
          {phase === "pending"
            ? "Contacting…"
            : phase === "failed"
              ? "Retry discovery"
              : phase === "success"
                ? "Refresh metadata"
                : "Discover Tangem MCP"}
        </button>
        <button
          onClick={onInspect}
          className="text-teal text-sm font-medium hover:text-teal/80 transition-colors"
        >
          Inspect the market note
        </button>
      </div>
    </motion.div>
  );
}
