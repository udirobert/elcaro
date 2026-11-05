# Incident Response — elcaro's next layer

Direction doc: the market moved from *detection* to *detection **and
response***. This is where elcaro goes next — as a hackathon
differentiator now, and as the product's identity afterward.

**Origin:** competitive re-scout Nov 5 (see `hermes-plugin.md` §
Competitive field). The Hermes plugin field converged on one shape —
every credible entry (sentry, injection-guard, CaMeL Guard, us)
*detects or gates*. None answers the question a user actually asks at
a quarantine: **"what was that thing trying to do?"**

**Market evidence:** HiddenLayer, Miggo, and Operant all launched
agentic *Detection & Response* products in 2026 — runtime guardrails
plus incident observability, because "one in eight AI breaches are
linked to agentic systems" and "most controls stop at prompts,
policies, or static permissions" while "execution-time behavior
remains largely unobserved." OWASP's 2026 Agentic Top-10 names the
attack shape everyone should be built for: **multi-tool kill chains**
(fetch → credential read → egress) and **memory persistence**.

## The thesis

> Everyone built a door. Elcaro builds the flight recorder *and* the
> crash investigation: detect → gate → reconstruct the kill chain →
> sign the evidence.

Detection tells you something was blocked. Response tells you what it
wanted, how far it got, and what to fix. That gap is the wedge — for
the hackathon (two mechanisms ahead of sentry: sequence detection +
forensic depth) and for the product (the only agent-security tool
that produces an *incident*, not just a verdict).

## The three primitives

### 1. Autopsy — what did the attack want?

On every quarantine, a second deterministic pass extracts the attack's
objective and targets:

- **Objective class:** exfiltration, persistence, steering, reward
  hack, privilege escalation — mapped from flagged technique classes
  plus what the payload *addresses* (credential paths, egress hosts,
  memory writes, instruction files).
- **Named targets:** the literal paths/hosts/tools the payload
  references (`~/.ssh/id_rsa` → `evil.example/x`) — extracted by
  regex inventory, no LLM, stays offline and sub-ms.
- **Kill-chain stage:** recon → steer → harvest → exfil → persist —
  the payload's position in the attack lifecycle.
- **Concealment:** which evasion it used (unicode, encoding,
  delimiter tricks, fragmentation).

Output lands in the threat-log entry (`extra.autopsy`), in
`elcaro_explain`, and in the pane row. Demo line: *"Sentry blocks
the door. Elcaro files the police report."*

### 2. Kill-chain detection — score the sequence, not just the content

OWASP's headline attack shape is `untrusted read → sensitive read →
egress` inside minutes. Every entry in the field scores content;
nobody scores the *call sequence*. A novel-phrasing injection that
never trips a detector still drives a recognizable behavior.

Implementation: a rolling per-session window in `policy.py` —
`(timestamp, tool_class)` deque where tool classes are
`untrusted_result | sensitive_read | egress | write | memory_write |
instruction_write`. Chain rules match ordered patterns within
`chain_window_seconds` (default 300):

- `untrusted_result → sensitive_read → egress` → **block** (the
  classic exfil chain)
- `untrusted_result → memory_write | instruction_write` → **block**
  (persistence attempt)
- `untrusted_result → outside_workspace_write` → escalate

This is detection that survives a zero-day phrasing — it follows the
*shape of the crime*, not the words. The pane shows "3-hop kill chain
intercepted" instead of three unrelated gated calls. Sentry's taint
gates individual actions during a window; this gates the *chain* — a
strictly richer model of the same idea.

### 3. Persistence gate — memory is an injection surface

Sentry's own PR admits the `memory` tool is ungated: a poisoned page
writes itself into standing memory and re-fires every future session.
The demo writes itself: *"the agent remembered the attack — forever —
until elcaro."*

- `memory` already in `scan_args_tools` — extend with a
  persistence-shaped check: memory writes carrying instruction-verb
  density or canary/decoy markers → block.
- On memory *reads*, entries containing prior injection markers
  (canary hit → propagation edge; decoy marker → quarantine) are
  flagged as re-firing payloads, not just content.
- Cron/scheduled-job writes carrying instruction payloads get the
  same treatment — persistence through time, not just storage.

## Phase 2+ (post-hackathon, product layer)

- **Fleet quorum** — opt-in payload-hash share via the existing
  `api_url` lane: quarantined anywhere → suspect everywhere. We own
  the network already (`miner/`, `telegraph/`); no plugin can clone
  a network effect in a weekend. The un-copyable moat.
- **Intent binding** — high-stakes actions (payments, sends,
  deletes) require a signed receipt linking them to the user's actual
  request. Closes the arc: PayBox scoped what agents may spend,
  elcaro scoped what they may believe — now what they may *do*, and
  proof of *why*.
- **Incident export** — one command bundles a quarantine + autopsy +
  chain + signatures into a signed incident file a human (or a SOC)
  can verify offline. Judges love artifacts; SOCs require them.
- **Paid autopsy lane** — `elcaro_autopsy` behind the existing x402
  scan lane: pay-per-incident-report is a productized version of the
  same primitive.

## Implementation plan (hackathon scope — ~1 day)

All inside `hermes-plugin/`; no new surfaces, no new disclosures.

| # | Change | Files | Effort |
|---|--------|-------|--------|
| 1 | `autopsy.py`: technique→objective map, target extraction (paths/hosts/tools), kill-chain stage, concealment list. Wired into `guard._scan_and_log` on quarantine → `extra.autopsy`; surfaced in `tools.elcaro_explain` + pane detail line. | new + guard/tools/pane | ~3 h |
| 2 | Kill-chain window: `_chain: dict[session] → deque[(ts, class)]` in `policy.py`; tool→class map; chain rules evaluated before single-call rules; chain hits log `surface:"policy"`, `policy_rule:"kill_chain"`. | policy.py | ~3 h |
| 3 | Persistence gate: memory/cron writes carrying instruction-shaped content or markers → block via chain rule + args-scan extension; memory read-backs with markers flagged. | guard.py, policy.py | ~2 h |
| 4 | Pane: autopsy line under quarantined rows (`wanted: exfil ~/.ssh → host`), kill-chain group header when a chain fires. | desktop/plugin.js | ~1 h |
| 5 | Tests: autopsy extraction on corpus, chain window fires on synthetic sequence, memory persistence block, monitor-mode parity. | tests/ | ~1 h |
| 6 | Docs: README bullet, `hermes-plugin.md` entry, catalog PR body + pin bump (`sha` → new commit), re-validate. | docs, catalog | ~30 m |

**Config additions:** `chain_window_seconds` (300),
`chain_rules_enabled` (true), `persistence_gate` (enforce/monitor/off —
defaults share `taint_policy` unless set).

**Demo beats this unlocks for the video:** honeypot catch (existing) →
pane shows *"wanted: exfil ~/.ssh/id_rsa → evil.example"* under the row
→ a 3-call sequence blocked as a named kill chain → "the agent
remembered the attack — forever — until elcaro" → `chain ✓` verify.
That is a *story of a catch*, not a feature tour — the Custodian
formula end to end.

## Naming / positioning

Keep the product language consistent: **elcaro is the incident system
for agents** — detection engine → enforcement kernel → incident
reports → fleet intelligence. In the catalog PR and video, one line:
*"Every other entry blocks the injection. Ours tells you what it was
trying to do."*
