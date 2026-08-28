// Verdict correction — the "this verdict was wrong" surface (docs/ux-audit.md,
// R4). A detector that over-flags loses trust faster than one that misses,
// and a correction loop is how it stays calibrated. The miner stays stateless,
// so a report is filed as a GitHub issue from the verdict-report template and
// ingested into the eval corpus by scripts/ingest_verdict_reports.py.
//
// Privacy: the report carries the scanned content only because the user chose
// to report it — the same disclosure posture as the share feature. The content
// hash lets the ingest pipeline dedup without re-storing content.

import type { ScanResponse } from "./types";

const REPO = "udirobert/elcaro";
const ISSUE_TEMPLATE = "verdict-report.md";

export type ReportLabel = "missed" | "over-flagged";

export interface VerdictReport {
  title: string;
  body: string;
  url: string;
}

async function sha256Hex(text: string): Promise<string> {
  // crypto.subtle requires a secure context (https or localhost). If it's
  // unavailable, fall back to a marker — the hash is for dedup, not security.
  if (typeof crypto === "undefined" || !crypto.subtle) return "unavailable";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function buildVerdictReport(
  result: ScanResponse,
  content: string,
  label: ReportLabel
): Promise<VerdictReport> {
  const hash = await sha256Hex(content);
  const techniques = result.flagged_techniques.join(", ") || "none";
  const labelWord = label === "missed" ? "missed" : "over-flagged";

  const body = [
    `**Label:** ${labelWord}`,
    `**Content type:** ${result.content_type}`,
    `**Risk score:** ${result.risk_score.toFixed(2)}`,
    `**Risk level:** ${result.risk_level}`,
    `**Flagged techniques:** ${techniques}`,
    `**Content SHA-256:** ${hash}`,
    "",
    "## Content",
    content,
    "",
    "## Notes",
    "<!-- What happened? What should the verdict have been? -->",
  ].join("\n");

  const title = `Verdict report: ${labelWord} — ${result.content_type}, score ${result.risk_score.toFixed(2)}`;
  const url = `https://github.com/${REPO}/issues/new?template=${ISSUE_TEMPLATE}&title=${encodeURIComponent(title)}`;

  return { title, body, url };
}
