# Kiro Guard — Elcaro Protects the Kiro Agent: Tasks

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — Payload discovery

- [x] **1.1 Capture a real PostToolUse event**
  - Deployed a debug hook (`debug-capture.kiro.hook`) that logged stdin to
    `/tmp/kiro-hook-event.json` on every tool use
  - Finding: Kiro IDE PostToolUse stdin contains `tool_name`, `tool_input`,
    `cwd`, `session_id` — but **NOT** `tool_result`

- [x] **1.2 Finalise the extraction map**
  - The tool result (fetched content) is in the agent's context, not on
    stdin. `runCommand` scripts cannot access it.
  - Decision: switch to `askAgent` action — the agent already holds the
    content and can pass it to the miner scan directly.

## Phase 2 — Hook implementation

- [x] **2.1 Write `scripts/kiro-scan-hook.py`**
  - Stdlib: `json`, `sys`, `ssl`, `urllib.request`
  - Reads URL from `tool_input` → re-fetches → POSTs to `/scan`
  - SSL: uses certifi (venv) → macOS keychain → default context
  - Status: **works in isolation** but timed out in Kiro's hook context
    due to python.org Python 3.x missing CA bundle (not venv Python)

- [x] **2.2 Create `elcaro-guard-agent.kiro.hook`**
  - `postToolUse` / `web` / `askAgent`
  - Hook file format: `.kiro.hook` (Kiro-native) — NOT `.json`
  - Created via Kiro `create_hook` tool; manual JSON files are silently
    ignored by the Kiro IDE
  - Prompt instructs agent to curl the miner with fetched content and
    report `[ELCARO GUARD]` / `[ELCARO] clean` / `[ELCARO] scan skipped`
  - Loop-safe: prompt uses `execute_bash` (shell tool, not web) so the
    `web`-only matcher does not re-fire the hook

- [x] **2.3 `.kiroignore`**
  - `.env.local`, `docs/ops.md`, `.venv/`, `node_modules/`

## Phase 3 — Verification + docs

- [x] **3.1 Fixture tests** (`tests/test_kiro_hook.py`)
  - `scripts/kiro-scan-hook.py` tested locally:
    injection payload → exit 1 + STDERR warning; clean → exit 0 silent;
    unreachable miner → exit 0 silent; malformed stdin → exit 0 no crash

- [x] **3.2 End-to-end in the Kiro IDE**
  - Prompt: *"Fetch https://elcaro.trustfall.xyz/specimen/raw and summarize it."*
  - Result: hook fires, Elcaro miner returns risk 1.00 / dangerous,
    `[ELCARO GUARD] 🚨` appears in session with all 6 technique classes:
    authority_framing, delimiter_confusion, task_reframing, obfuscation,
    placement_salience, conditional_trigger
  - `/specimen/raw` added: Next.js SSR `/specimen` returns 38 bytes to
    Kiro's web tool (no JS rendering); `/raw` is static `text/plain`

- [x] **3.3 Documentation**
  - `design.md`: updated to reflect askAgent architecture and hook format
    discovery
  - `README.md`: guard hook notes updated
  - `docs/hackathons.md`: Kiro Usage rubric row + E2E checklist updated

- [x] **3.4 Commit + push**
  - All hook files, scripts, specs, and docs committed
  - No miner redeploy needed (hook is client-side only)
