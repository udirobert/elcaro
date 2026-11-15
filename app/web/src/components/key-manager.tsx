"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

/**
 * Self-service Elcaro key management (contract C2 surface).
 *
 * Keys are bearer tokens: the raw key is shown once at mint, stored only
 * in this browser's localStorage, and is itself the auth for reading or
 * revoking it. Losing it = mint a new one. Nothing here is a login.
 */

interface StoredKey {
  keyId: string;
  raw: string;
  label: string;
  createdAt: string;
}

interface KeyStatus {
  mode: string;
  upstream: string;
  deep_analysis: boolean;
  usage_30d: { requests: number; partsScanned: number; chargeUsdc: string } | null;
}

const LS_KEY = "elcaro_keys_v1";

// localStorage via useSyncExternalStore: the server snapshot is "[]" so
// hydration stays clean, and persist() emits to re-render same-tab writes.
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

function getSnapshot() {
  return localStorage.getItem(LS_KEY) ?? "[]";
}

function getServerSnapshot() {
  return "[]";
}

function persistKeys(next: StoredKey[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(next));
  listeners.forEach((cb) => cb());
}

export function KeyManager() {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const keys: StoredKey[] = useMemo(() => {
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }, [raw]);

  const [status, setStatus] = useState<Record<string, KeyStatus | "gone">>({});
  const [label, setLabel] = useState("");
  const [minted, setMinted] = useState<{ raw: string; keyId: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importKey, setImportKey] = useState("");

  useEffect(() => {
    // All setStatus calls happen after awaits — nothing synchronous here.
    for (const k of keys) {
      if (status[k.keyId]) continue;
      void (async () => {
        try {
          const res = await fetch(`/api/keys?key=${encodeURIComponent(k.raw)}`);
          if (res.ok) {
            const info = await res.json();
            setStatus((s) => ({ ...s, [k.keyId]: info }));
          } else {
            setStatus((s) => ({ ...s, [k.keyId]: "gone" }));
          }
        } catch {
          setStatus((s) => ({ ...s, [k.keyId]: "gone" }));
        }
      })();
    }
  }, [keys, status]);

  async function mint() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        setError(e.error ?? `Mint failed (${res.status})`);
        return;
      }
      const { key, key_id } = await res.json();
      setMinted({ raw: key, keyId: key_id });
      persistKeys([
        { keyId: key_id, raw: key, label, createdAt: new Date().toISOString() },
        ...keys,
      ]);
      setLabel("");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(k: StoredKey) {
    const res = await fetch(`/api/keys?key=${encodeURIComponent(k.raw)}`, {
      method: "DELETE",
    });
    if (res.ok) {
      persistKeys(keys.filter((x) => x.keyId !== k.keyId));
      setStatus((s) => {
        const n = { ...s };
        delete n[k.keyId];
        return n;
      });
    } else {
      setError(`Revoke failed (${res.status})`);
    }
  }

  function trackExisting() {
    const trimmed = importKey.trim();
    if (!trimmed.startsWith("elk_")) {
      setError("Expected a key starting with elk_");
      return;
    }
    if (!keys.some((k) => k.raw === trimmed)) {
      persistKeys([
        {
          keyId: `elkid_${trimmed.slice(4, 12)}`,
          raw: trimmed,
          label: "(imported)",
          createdAt: new Date().toISOString(),
        },
        ...keys,
      ]);
    }
    setImportKey("");
  }

  return (
    <div className="space-y-8">
      {/* Mint */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
        <div className="space-y-1">
          <h2 className="text-sm font-semibold text-ink">Mint a key</h2>
          <p className="text-xs text-ink-muted leading-relaxed">
            Keys are bearer tokens — the raw key is shown once, below, and
            stored only in this browser. Only its hash reaches our database.
          </p>
        </div>
        <div className="flex gap-2">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Label (optional — e.g. staging bot)"
            className="flex-1 rounded-lg border border-border bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-violet"
          />
          <button
            onClick={mint}
            disabled={busy}
            className="rounded-lg bg-ink text-canvas px-4 py-2 text-sm font-semibold hover:bg-ink/90 disabled:opacity-50 transition-colors"
          >
            {busy ? "Minting…" : "Mint key"}
          </button>
        </div>
        {error && <p className="text-xs text-dangerous">{error}</p>}

        {minted && (
          <div className="rounded-lg border border-safe/40 bg-safe-bg p-4 space-y-2">
            <p className="text-xs font-semibold text-safe">
              Key minted — copy it now. It will not be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 font-mono text-xs text-ink break-all select-all">
                {minted.raw}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(minted.raw)}
                className="shrink-0 rounded border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink transition-colors"
              >
                Copy
              </button>
            </div>
            <button
              onClick={() => setMinted(null)}
              className="text-xs text-ink-faint hover:text-ink transition-colors underline underline-offset-2"
            >
              I saved it — dismiss
            </button>
          </div>
        )}
      </div>

      {/* Your keys */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-ink">Your keys</h2>
        {keys.length === 0 && (
          <p className="text-xs text-ink-faint">
            None in this browser yet — mint one above, or track an existing
            key below.
          </p>
        )}
        <div className="space-y-3">
          {keys.map((k) => {
            const s = status[k.keyId];
            return (
              <div
                key={k.keyId}
                className="rounded-xl border border-border bg-surface p-4 space-y-2"
              >
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <code className="font-mono text-xs text-ink">
                    {k.raw.slice(0, 12)}…
                  </code>
                  <div className="flex items-center gap-3">
                    {k.label && (
                      <span className="text-xs text-ink-muted">{k.label}</span>
                    )}
                    <button
                      onClick={() => revoke(k)}
                      className="text-xs text-dangerous hover:underline underline-offset-2"
                    >
                      Revoke
                    </button>
                  </div>
                </div>
                {!s && <p className="text-xs text-ink-faint">Loading…</p>}
                {s === "gone" && (
                  <p className="text-xs text-dangerous">Revoked or unknown</p>
                )}
                {s && s !== "gone" && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-faint font-mono">
                    <span>mode: {s.mode}</span>
                    <span>upstream: {s.upstream}</span>
                    {s.deep_analysis && <span>serv judge</span>}
                    {s.usage_30d && (
                      <span>
                        30d: {s.usage_30d.requests} req · {s.usage_30d.partsScanned}{" "}
                        parts · ${s.usage_30d.chargeUsdc}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Track an existing key */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-3">
        <h2 className="text-sm font-semibold text-ink">Track an existing key</h2>
        <p className="text-xs text-ink-muted leading-relaxed">
          Minted elsewhere? Paste the raw key to see its config and usage
          here. It stays in this browser only.
        </p>
        <div className="flex gap-2">
          <input
            value={importKey}
            onChange={(e) => setImportKey(e.target.value)}
            placeholder="elk_…"
            className="flex-1 rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-violet"
          />
          <button
            onClick={trackExisting}
            className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-ink hover:bg-surface transition-colors"
          >
            Track
          </button>
        </div>
      </div>
    </div>
  );
}
