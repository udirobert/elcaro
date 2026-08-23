// Journey state — tracks the visitor's exploration for adaptive CTAs.
// The homepage closing CTA reads this to suggest the next logical step
// based on what the visitor has actually done, not a fixed funnel.

const GAUNTLET_KEY = "elcaro_gauntlet_run";

export function hasRunGauntlet(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(GAUNTLET_KEY) === "true";
  } catch {
    return false;
  }
}

export function markGauntletRun(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(GAUNTLET_KEY, "true");
  } catch {
    // localStorage unavailable — non-critical, the CTA just stays at default
  }
}
