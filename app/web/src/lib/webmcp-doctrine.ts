import type { RiskLevel, ScanResponse } from "./types";
import { QUARANTINE_THRESHOLD } from "./history";

// Same numbers as app/mcp_server.py and /integrate.
export const BLOCK_THRESHOLD = QUARANTINE_THRESHOLD;
export const FLAG_THRESHOLD = 0.3;
export const NEVER_PASS_THRESHOLD = 0.7;

const DECISIONS: Record<
  RiskLevel,
  { action: string; headline: string; recommended_steps: string[] }
> = {
  dangerous: {
    action: "block",
    headline: "Block it — this content should not reach your agent.",
    recommended_steps: [
      "Process safe_content (the quarantine notice) instead of the original content",
      "Tell your user the content was blocked, and why — quote the verdict's human_summary field verbatim",
      "Alert your team, with this verdict as the evidence",
    ],
  },
  suspicious: {
    action: "review",
    headline: "Flag it — worth a human look before your agent acts.",
    recommended_steps: [
      "If no human can review it now, process safe_content instead of the original",
      "Have a reviewer check the indicators, then pass or block",
    ],
  },
  low: {
    action: "process_with_log",
    headline: "Process it — but log this verdict with the findings.",
    recommended_steps: [
      "Let the content through, and keep this verdict in your audit trail",
    ],
  },
  safe: {
    action: "process",
    headline: "Process it — nothing to act on.",
    recommended_steps: [],
  },
};

export function explainVerdict(result: ScanResponse) {
  const quarantined =
    result.quarantined ?? result.risk_score >= BLOCK_THRESHOLD;
  const decision = DECISIONS[result.risk_level];
  return {
    action: decision.action,
    headline: decision.headline,
    recommended_steps: decision.recommended_steps,
    risk_level: result.risk_level,
    risk_score: result.risk_score,
    quarantined,
    human_summary: result.human_summary ?? result.summary,
    doctrine: {
      block_at: BLOCK_THRESHOLD,
      flag_at: FLAG_THRESHOLD,
      never_pass_at: NEVER_PASS_THRESHOLD,
    },
    ui: "The human watching this tab already sees this verdict on /scan.",
  };
}
