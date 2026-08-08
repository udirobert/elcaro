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
