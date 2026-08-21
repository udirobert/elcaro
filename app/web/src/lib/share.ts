import type { ContentType, ScanResponse } from "./types";

// Shareable verdicts — encoded in the URL fragment (#v=...) so nothing is
// stored server-side. The miner is stateless (an on-chain requirement) and
// scans never touch a database: the content lives only in the link the user
// chooses to share. See docs/growth-loops.md for the privacy rationale.

export interface SharedVerdict {
  content: string;
  content_type: ContentType;
  response: ScanResponse;
  shared_at: number;
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000; // avoid stack overflow on large payloads
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function base64UrlToBytes(encoded: string): Uint8Array {
  const b64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function encodeVerdict(verdict: SharedVerdict): string {
  const json = JSON.stringify(verdict);
  return bytesToBase64Url(new TextEncoder().encode(json));
}

export function decodeVerdict(fragment: string): SharedVerdict | null {
  try {
    const json = new TextDecoder().decode(base64UrlToBytes(fragment));
    const parsed = JSON.parse(json) as SharedVerdict;
    if (
      typeof parsed?.content === "string" &&
      typeof parsed?.content_type === "string" &&
      parsed?.response &&
      typeof parsed.response.risk_score === "number" &&
      typeof parsed.response.risk_level === "string"
    ) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}
