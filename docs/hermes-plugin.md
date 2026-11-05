# Hermes Agent Plugin Hackathon — "Elcaro rides every tool result"

Competition entry doc. Positioning + build plan, in the `paybox-ch1.md` style.
Record of participation lives in [hackathons.md](hackathons.md).

**Event:** Hermes Agent Plugin Hackathon (Nous Research) · 7 days
**Deadline:** Tue **Nov 11 2026, 5:00 PM EST** · internal target: video + PR by **Sun Nov 9**
**Prizes:** $20,000 pool — 1st $10k + neon sign + merch + $1k creds · 2nd $5k · 3rd $2.5k · 4th $1.5k · 5th $1k · runners-up ×5 (merch + $250 creds)
**Entry:** (1) PR adding the plugin to the catalog, (2) demo video on X tagging @NousResearch (≤90 s, must show the plugin working), (3) form: https://form.typeform.com/to/FwJLvOln — form can go in as soon as the PR is open; catalog checks run when a maintainer starts them, reviews every few days.

## Why elcaro wins this one (the mandate)

> PayBox scoped what agents may **spend**; elcaro scoped what they may
> **believe**. Hermes made that same bet one layer higher: their agent
> reads the web, files, and tool output — and its built-in defenses are
> *install-time* and *author-time*, not runtime.

Judged on **usefulness · reliability · polish · creativity**, with a stated
bias: "plugins that do more than a prompt or a skill could." Elcaro is
exactly that — a deterministic, sub-10 ms scanning engine wired into the
agent's own hook points, producing verdicts + a signed quarantine trail no
prompt wrapping could produce.

Precise hook placement (verified against the plugin developer guide +
the Event Hooks reference, 2026-11-05):

Tool-call order: `tool_request` middleware → approvals → `tool_execution`
middleware → `post_tool_call` → **`transform_tool_result`** → conversation.

| Hook | Fires | Elcaro's role |
|---|---|---|
| `transform_tool_result` | after any tool returns, **before the result is appended to conversation** — `(tool_name, args, result, task_id, **kwargs) -> str \| None`; first `str` replaces what the model sees, for every tool | **primary enforcement**: scan `result` → quarantined → return the signed `safe_content` quarantine notice in place of the poisoned result; suspicious-under-threshold → append `[ELCARO GUARD]` advisory; log the signed verdict to the threat log. The injection never reaches the model |
| `pre_tool_call` | before execution; may return `{"action":"block"}` or `{"action":"approve"}` | *args-carried* payloads — the model pasting fetched content into `write_file`/`terminal` args; scan serialized args on a configurable tool set, conservative thresholds |
| `pre_llm_call` | once per turn, before the tool-calling loop | **backstop + anti-retry**: inject `[ELCARO GUARD]` context summarizing new quarantine events so the agent doesn't re-fetch or work around withheld content; hard block reserved for critical |
| `post_tool_call` | after any tool returns | observer only (returns ignored) — not needed; `transform_tool_result` carries a superset of its payload |

**Why this beats the earlier `post_tool_call → pre_llm_call` sketch:**
`pre_llm_call` fires once per turn *before* the tool loop starts — a tool
result poisoned mid-turn would already have gone to the model before the
next `pre_llm_call` could act. `transform_tool_result` sits between tool
dispatch and conversation append, so quarantined content is rewritten in
place, within the turn it arrived. `transform_terminal_output` is the
terminal-specific variant (fires earlier, before output limits + secret
redaction) if terminal needs its own path. `tool_execution` middleware
(`next_call` wrap) is the fallback if result-rewriting proves brittle on
some surface.

## The competitive field (scouted with Tavily, 2026-11-05)

- **Marketplace just launched with this hackathon: ~976 plugins** (Official
  ~20, Certified 9, Community the rest). Bar-setters: **OMH bridge** (5.1k★),
  **phone-harness** (4.3k★), **sem-weave** (3.4k★). All combine
  tools + hooks + Desktop surface — that combo is the winning shape.
- **Security niche is occupied but has a precise hole:**
  - **OpenGuardrails** — real prior art: blog integration on Hermes's
    `before_tool_call`. Its thesis is *outbound* provenance ("the same bytes
    typed by the user is a normal install; synthesized from a web page is
    injection"). It guards what **leaves** the agent.
  - **hermes-security-audit** (catalog) — static code scanning
    (gitleaks/semgrep/OSV). Not runtime content defense.
  - **Hermes Forge** (MCP market) — tool-calling *reliability* guardrails
    (malformed outputs). Different niche.
  - **Hermes built-ins** — Tirith (command-approval warnings), install-time
    plugin scanning, skills scan-time quarantine (Cowork-inspired).
  - **The hole is acknowledged by Hermes itself:** issue
    [#8884](https://github.com/NousResearch/hermes-agent/issues/8884) — prompt
    injection via unscanned skill DESCRIPTION.md; root cause in
    `skills_guard.scan_file`. CVE writeups (9 in 4 days) highlight
    file-read-without-deny-list. Runtime **inbound content** defense is the
    gap. Elcaro fills it: *OpenGuardrails guards what leaves; elcaro guards
    what enters.*
- **Pitch line:** "Hermes agents browse the web and read files. Elcaro rides
  every tool result and stops prompt injection before it reaches the model."

## Elcaro-specific advantages already in the repo

- **Core is done and proven**: `core/` detectors, quarantine, sandbox,
  signing, taxonomy — no torch, fastapi only, 10 ms verdicts, live product
  with real paid scans. Class G (`swarm_directive`) shipped for the swarm
  hackathon — detector work is recent muscle.
- **Plugin packaging motion exists twice**: `paybox-plugin/` (MCP bundle,
  2 tools: `elcaro_scan` paid + `elcaro_quick_scan` free) and the Kiro
  `.kiro` PostToolUse guard hook (`askAgent` on web fetches → `[ELCARO
  GUARD]` inline). Reuse the naming and the dogfooding story.
- **Demo proof-art**: the Gauntlet adversarial benchmark + gauntlet page
  (6 scenarios) — replay a small corpus through the hook for the video.

## Build plan (Nov 6–9)

Standalone repo form (third-party product plugins ship as standalone repos,
not core PRs — verified in the developer guide + catalog rules). New
directory: `hermes-plugin/`, vendored engine under `elcaro_engine/`
(`vendor.sh` copies `core/` + rewrites `from core.` imports — core stays
source of truth).

1. `plugin.yaml` (manifest v2) — name `elcaro`,
   `provides_tools: [elcaro_scan, elcaro_quick_scan, elcaro_explain]`,
   `provides_hooks: [transform_tool_result, pre_tool_call, pre_llm_call]`,
   `config_schema` for sensitivity/enforcement/skip-tools, deps via
   `pyproject.toml`: `pydantic`, `cryptography` (signed verdicts), `httpx`
   (only for env-gated second passes) — oldest-compatible floors + upper
   bounds per catalog dep policy
2. `__init__.py` → `register(ctx)` — hooks + tools + bundled skill; engine
   init is lazy (first scan), keeping `hermes plugins doctor` socket-block
   clean and registration fast
3. Enforcement: `transform_tool_result` (scan result → replace with
   `safe_content` when quarantined, `[ELCARO GUARD]` advisory when
   suspicious) + `pre_tool_call` for args-carried payloads +
   `pre_llm_call` backstop summary
4. **Hermes-shaped tuning (the real engineering):** sensitivity presets per
   surface (web-fetch vs file-read vs shell-output), user-initiated-content
   allowlists so YOLO mode isn't nagged on every fetch the *user* typed
5. Signed JSONL threat log under `plugin_data_dir("elcaro")` →
   `elcaro_explain` reads it back; Desktop threat-log pane is the polish
   axis (strict SDK surface — no eval, SDK/react imports only)
6. Catalog constraints: declared tools/hooks must match `register()`
   exactly (mismatch = security decline); `hermes plugins validate` clean;
   no self-updaters, no core patching; 40-char SHA pin on the entry PR
7. Demo: agent fetches a seeded injection page → result swapped for the
   quarantine notice in-conversation, threat log shows signed verdict →
   benign fetch passes untouched. ≤90 s.
8. Video on X + PR + form by Sunday Nov 9 (two days of slack before the
   deadline).

**Scaffold status (Nov 5):** `hermes-plugin/` built and smoke-tested
against the installed hermes-agent (PyPI 0.19.0, scratch `HERMES_HOME`):
plugin loads `enabled: True, error: None` — 3 tools, 3 hooks, bundled
skill all registered. Verified through the **real dispatch path**
(`model_tools.handle_function_call`, no LLM needed): a poisoned
`read_file` returns the quarantine notice in place of file contents
(0.92 dangerous, canary ref stamped); a poisoned `write_file` args
payload is blocked by `pre_tool_call` and the file is never written;
benign reads/writes/terminal pass untouched. Tuning pass found and
fixed a load-bearing detail — every Hermes tool returns a
`json.dumps` envelope, so the guard now unwraps the envelope and
scans the real text (escaped newlines would have blunted detection);
error envelopes and structural confirmations are skipped. FP corpus
(git log, ls, package.json, READMEs w/ "instructions" phrasing,
source code, pytest, tracebacks, env, security docs *about*
injection): 0 false positives at balanced sensitivity. Unit tests in
`tests/test_hermes_plugin.py` (9 tests). Note: 0.19.0 predates
`plugins validate`/catalog checks — run those against a
marketplace-era build or let catalog CI do it.

**Surfaces shipped (Nov 5, second pass — closing the bar-setter gap):**
tools + hooks + **Desktop pane + backend API + commands** — the winning
combo the top plugins (OMH 5.1k, phone-harness 4.3k) all share.
`dashboard/plugin_api.py` (`/api/plugins/elcaro/verdicts|stats`) feeds
`desktop/plugin.js`: a threat-log pane (risk-colored verdict rows,
live-updates via `plugin.elcaro.verdict.logged` events broadcast on every
scan) + a status-bar quarantine chip. `/elcaro` slash command and
`hermes elcaro log|status` CLI subcommand read the same signed log.
Verified loading against the installed build: `enabled: True,
error: None`, commands registered.

## Risks (honest)

- False positives on Hermes's own tool-output conventions → tune against
  real Hermes sessions early, not at the end
- `transform_tool_result` sees the result Hermes gives it — if some tool
  returns non-`str` payloads, guard must no-op on non-str rather than
  crash (fail-open is the hook system's default anyway: a raising
  callback is logged and skipped)
- Doctor blocking sockets at registration means any hosted-lane call must be
  lazy; local-first core is the primary path, hosted lane optional

## Links

- Plugin developer guide: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- Catalog submission: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission
- Hooks reference: https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
- Security model (Tirith, skills scan): https://hermes-agent.nousresearch.com/docs/user-guide/security
- Marketplace: https://hermes-agent.nousresearch.com/marketplace
- Known gap: https://github.com/NousResearch/hermes-agent/issues/8884
- OpenGuardrails prior art: https://openguardrails.com/blog/guarding-a-hermes-agent-with-openguardrails
- Announcement: https://x.com/NousResearch/status/2118094256438936062
