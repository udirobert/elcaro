import type { ScanRequest, ScanResponse, ScanError } from "./types";

export async function scanContent(
  request: ScanRequest
): Promise<ScanResponse | ScanError> {
  try {
    const response = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: "Scan failed", detail: data.detail || data.error };
    }

    return data as ScanResponse;
  } catch (err) {
    return {
      error: "Network error",
      detail:
        err instanceof Error ? err.message : "Could not reach the scanner",
    };
  }
}

export function isError(
  result: ScanResponse | ScanError
): result is ScanError {
  return "error" in result;
}

import type { VulnerabilityResult } from "./types";

export async function analyzeVulnerability(
  prompt: string
): Promise<VulnerabilityResult | ScanError> {
  try {
    const response = await fetch("/api/vulnerable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: "Analysis failed", detail: data.detail || data.error };
    }

    return data as VulnerabilityResult;
  } catch (err) {
    return {
      error: "Network error",
      detail: err instanceof Error ? err.message : "Could not reach the analyzer",
    };
  }
}

import type { SandboxResult } from "./types";

export async function runSandbox(
  prompt: string,
  runPatternAnalysis = true
): Promise<SandboxResult | ScanError> {
  try {
    const response = await fetch("/api/sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, run_pattern_analysis: runPatternAnalysis }),
    });
    const data = await response.json();
    if (!response.ok) {
      return { error: "Sandbox failed", detail: data.detail || data.error };
    }
    return data as SandboxResult;
  } catch (err) {
    return {
      error: "Network error",
      detail: err instanceof Error ? err.message : "Could not reach the sandbox",
    };
  }
}
