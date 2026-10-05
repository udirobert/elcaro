"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

interface CanaryEvent {
  token: string;
  recognized: boolean;
  kind?: string;
  issued_at?: number;
  content_sha256?: string;
  risk_score?: number;
  risk_level?: string;
  techniques?: string[];
  content_type?: string;
}

const KIND_LABELS: Record<string, string> = {
  scan: "a quarantine notice served by /scan",
  specimen_serve: "a fetch of the specimen kit",
};

/** Paste a Ref: elc-... token found in the wild → resolve it against the
 * issuing miner via /api/canary. Recognized = the notice is genuine and
 * this is the scan that minted it; unrecognized = forged, foreign, or
 * minted before a restart (informational, not proof either way). */
export function CanaryResolver() {
  const [token, setToken] = useState("");
  const [result, setResult] = useState<CanaryEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function resolve(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const t = token.trim();
    if (!t) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch(`/api/canary/${encodeURIComponent(t)}`);
      const body = await res.json().catch(() => null);
      if (res.status === 422) {
        setError("That doesn't look like a canary token — the format is elc-<hex>-<6 hex>.");
      } else if (!res.ok || !body) {
        setError(body?.error ?? body?.detail ?? "Resolution unavailable right now.");
      } else {
        setResult(body);
      }
    } catch {
      setError("Couldn't reach the resolver — try again shortly.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={resolve} className="flex gap-3">
        <input
          type="text"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="elc-6ac30b20-8b7b0f"
          spellCheck={false}
          className="flex-1 rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-violet/30"
        />
        <button
          type="submit"
          disabled={loading || !token.trim()}
          className="rounded-lg bg-ink text-canvas px-5 py-2 text-sm font-semibold hover:bg-ink/90 transition-colors disabled:opacity-50"
        >
          {loading ? "Resolving…" : "Resolve"}
        </button>
      </form>

      <AnimatePresence mode="wait">
        {error && (
          <motion.p
            key="err"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
            className="text-sm text-dangerous"
          >
            {error}
          </motion.p>
        )}

        {result && (
          <motion.div
            key={result.token}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
            className={`rounded-xl border px-5 py-4 space-y-3 ${
              result.recognized
                ? "border-safe/30 bg-safe/5"
                : "border-warning/30 bg-warning/5"
            }`}
          >
            {result.recognized ? (
              <>
                <p className="text-sm font-semibold text-ink">
                  Genuine — this token was minted by{" "}
                  {KIND_LABELS[result.kind ?? ""] ?? "this miner"}
                  {result.issued_at && (
                    <>
                      {" "}
                      on{" "}
                      <span className="font-mono">
                        {new Date(result.issued_at * 1000).toISOString()}
                      </span>
                    </>
                  )}
                  .
                </p>
                {result.risk_score != null && (
                  <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div>
                      <dt className="text-ink-faint uppercase tracking-widest text-[10px]">
                        Original score
                      </dt>
                      <dd className="font-mono text-ink">{result.risk_score}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-faint uppercase tracking-widest text-[10px]">
                        Level
                      </dt>
                      <dd className="font-mono text-ink">{result.risk_level}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-faint uppercase tracking-widest text-[10px]">
                        Content type
                      </dt>
                      <dd className="font-mono text-ink">{result.content_type}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-faint uppercase tracking-widest text-[10px]">
                        Techniques
                      </dt>
                      <dd className="font-mono text-ink">
                        {result.techniques?.join(", ") || "—"}
                      </dd>
                    </div>
                  </dl>
                )}
                <p className="text-[11px] text-ink-faint leading-relaxed">
                  The notice that carried this token was a real Elcaro
                  quarantine — the content it replaced scored{" "}
                  {result.risk_score} ({result.risk_level}) at mint time. Its
                  SHA-256 is on record; the content itself is never stored.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-ink">
                  Not recognized — this miner didn&apos;t mint {result.token}.
                </p>
                <p className="text-xs text-ink-muted leading-relaxed">
                  A well-formed token can still be unresolvable: minted by
                  another Elcaro deployment, minted on a miner without a
                  durable registry, or copied into a forged notice. The
                  signature on a verdict — not in-band text — is the trust
                  signal.
                </p>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
