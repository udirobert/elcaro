import type { ScanRequest, ScanResponse, ScanError, FetchUrlResponse, FetchUrlError } from "./types";

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

// ── URL fetching (/scan "Fetch page content") ────────────────────────────────

export async function fetchUrlAvailable(): Promise<boolean> {
  try {
    const res = await fetch("/api/fetch-url");
    if (!res.ok) return false;
    const data = await res.json();
    return Boolean(data.available);
  } catch {
    return false;
  }
}

export async function fetchUrlContent(
  url: string
): Promise<FetchUrlResponse | FetchUrlError> {
  try {
    const response = await fetch("/api/fetch-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await response.json();
    if (!response.ok) {
      return { error: data.error || "Failed to fetch that URL" };
    }
    return data as FetchUrlResponse;
  } catch (err) {
    return {
      error: err instanceof Error ? err.message : "Could not reach the fetch service",
    };
  }
}

export function isFetchUrlError(
  result: FetchUrlResponse | FetchUrlError
): result is FetchUrlError {
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

export interface MinerConfig {
  serv_available: boolean;
  jev_available: boolean;
  version: string;
}

export async function fetchMinerConfig(): Promise<MinerConfig> {
  try {
    const res = await fetch("/api/config");
    if (!res.ok) return { serv_available: false, jev_available: false, version: "unknown" };
    return res.json() as Promise<MinerConfig>;
  } catch {
    return { serv_available: false, jev_available: false, version: "unknown" };
  }
}
