/**
 * @elcaro/sdk — thin clients for the Elcaro Gateway.
 *
 * The whole integration is a base-URL swap plus two headers. These
 * wrappers exist so callers don't hand-roll the header names:
 *
 *   const openai = new ElcaroOpenAI({ elcaroKey, upstreamKey });
 *   // identical surface to `new OpenAI(...)` — chat.completions, streams…
 *
 * Auth (gateway §2.3): `x-elcaro-key` carries the Elcaro key (or
 * `Authorization` when the upstream key arrives via `x-upstream-key`),
 * `x-upstream-key` carries the provider's real API key, untouched.
 */

export const ELCARO_GATEWAY_URL = "https://gateway.elcaro.trustfall.xyz";

export interface ElcaroClientOptions {
  /** The customer's Elcaro key (`elk_…`). Env: ELCARO_API_KEY. */
  elcaroKey?: string;
  /** The provider's real API key — forwarded upstream, never logged. */
  upstreamKey?: string;
  /** Default: https://gateway.elcaro.trustfall.xyz */
  baseURL?: string;
  /** Extra headers merged into every request (after ours). */
  headers?: Record<string, string>;
}

export function resolveElcaroKey(elcaroKey?: string): string {
  const key = elcaroKey ?? process.env.ELCARO_API_KEY;
  if (!key) {
    throw new Error(
      "Elcaro key required — pass elcaroKey or set ELCARO_API_KEY. " +
        "Get one at https://elcaro.trustfall.xyz/integrate",
    );
  }
  return key;
}

export function elcaroHeaders(opts: ElcaroClientOptions): Record<string, string> {
  const headers: Record<string, string> = {
    "x-elcaro-key": resolveElcaroKey(opts.elcaroKey),
  };
  if (opts.upstreamKey) headers["x-upstream-key"] = opts.upstreamKey;
  return { ...headers, ...opts.headers };
}

/**
 * Mark a message index as untrusted → `x-elcaro-untrusted` header value
 * (§2.4). Scanned even when the role wouldn't be (e.g. a user turn
 * carrying pasted retrieval content).
 */
export function untrustedHeader(...messageIndexes: number[]): string {
  return `msg:${messageIndexes.join(",")}`;
}

/**
 * Mark an OpenAI-style content part as untrusted — the gateway scans it
 * and strips the marker before forwarding (§2.4).
 *
 *   messages: [{ role: "user", content: [
 *     { type: "text", text: "Summarize this:" },
 *     untrusted(retrievedDoc),
 *   ]}]
 */
export function untrusted(text: string): Record<string, unknown> {
  return { type: "text", text, elcaro: { untrusted: true } };
}

/** §2.7 response metadata, parsed from any Headers-like object. */
export interface ElcaroVerdict {
  verdict?: "clean" | "suspicious" | "dangerous";
  action?: "none" | "warned" | "quarantined" | "blocked" | "bypassed";
  scanned?: number;
  /** base64 Ed25519 signature — verifiable at POST {baseURL}/verify */
  receipt?: string;
  costUsdc?: string;
  /** Autopsy URL when action ≠ none */
  incident?: string;
}

export function verdictFromHeaders(headers: Headers): ElcaroVerdict {
  const get = (n: string) => headers.get(n) ?? undefined;
  const scanned = get("x-elcaro-scanned");
  return {
    verdict: get("x-elcaro-verdict") as ElcaroVerdict["verdict"],
    action: get("x-elcaro-action") as ElcaroVerdict["action"],
    scanned: scanned === undefined ? undefined : Number(scanned),
    receipt: get("x-elcaro-receipt"),
    costUsdc: get("x-elcaro-cost-usdc"),
    incident: get("x-elcaro-incident"),
  };
}
