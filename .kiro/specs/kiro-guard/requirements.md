# Kiro Guard — Elcaro Protects the Kiro Agent: Requirements

## Overview

Dogfooding with a thesis: **the agent that built the injection firewall is
itself protected by it.** A Kiro hook scans content the agent retrieves
(web fetches) through Elcaro before it can influence the agent's reasoning.

This is the flagship Kiro-native primitive for the Kiro hackathon submission
(Kiro Usage: 20 pts of the rubric) and the centerpiece of the demo video —
a hook visibly firing in the Kiro IDE, catching an injected instruction
mid-session. No other entry can tell this story: their products don't guard
agents.

Built during the competition window (deadline Aug 23, 2026 23:59 UTC).

## Functional requirements

### FR-1 Guard hook (`.kiro/hooks/elcaro-guard.json`)

- FR-1.1 A hook MUST fire after every web-category tool call (`PostToolUse`,
  matcher `web`) and submit the tool result to Elcaro's `/scan` endpoint
- FR-1.2 The hook action MUST be a shell command (deterministic, no LLM
  credits, fast — the scan is single-digit milliseconds server-side)
- FR-1.3 The hook configuration MUST be committed at
  `.kiro/hooks/elcaro-guard.json` so any clone of the repo gets a working
  guard with zero setup
- FR-1.4 The hook timeout MUST be low (10s) so a slow network cannot stall
  the agent loop for the default 60s

### FR-2 Scanner script (`scripts/kiro-scan-hook.py`)

- FR-2.1 The script MUST use Python stdlib only (`json`, `sys`, `urllib`) —
  it runs in Kiro's hook execution context where the project venv is not
  guaranteed
- FR-2.2 The script MUST read the hook event JSON from STDIN and extract the
  tool result text
- FR-2.3 The script MUST POST the text to `ELCARO_MINER_URL` (default:
  the live API `https://api.elcaro.trustfall.xyz`) with
  `content_type: "webpage"`
- FR-2.4 The script MUST handle missing/malformed payload fields gracefully
  (empty scan, exit 0) — never crash the hook

### FR-3 Verdict behavior

- FR-3.1 On `risk_score >= 0.5` the script MUST exit non-zero and print a
  warning to STDERR containing: the risk score, the flagged techniques, and
  an explicit instruction to the agent not to follow instructions embedded
  in the retrieved content (Kiro delivers STDERR to the agent on hook
  failure)
- FR-3.2 On a safe verdict the script MUST exit 0 with no output — silent
  pass, to avoid polluting the agent's context on every web fetch
- FR-3.3 On miner unreachability or timeout the script MUST exit 0 silently
  — **fail-open**: the guard is a warning layer; the middleware is the
  enforcement layer, and a dead miner must not brick the dev loop

### FR-4 Payload discovery

- FR-4.1 Because the exact `PostToolUse` result field names are not fully
  documented, the first implementation step MUST capture one real event
  payload (log STDIN to a temp file) and the extraction logic MUST be
  finalised against that ground truth

### FR-5 `.kiroignore`

- FR-5.1 A `.kiroignore` MUST exclude secrets and host-specific files from
  agent context: `.env.local`, `docs/ops.md`, `.venv/`, `node_modules/`

### FR-6 Verification

- FR-6.1 A fixture-based test MUST demonstrate: injection payload → non-zero
  exit + STDERR warning; clean payload → exit 0 silent; unreachable miner →
  exit 0 silent
- FR-6.2 An end-to-end manual check MUST confirm the hook fires in the Kiro
  IDE on a web fetch of a page containing a known injection string
