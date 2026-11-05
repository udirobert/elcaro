# elcaro — runtime prompt-injection defense for Hermes

Hermes agents browse the web, read files, and run commands. Everything
those tools return is untrusted — a fetched page or a file can carry
instructions written for the agent, not the user. Elcaro rides every tool
result and stops prompt injection **before it reaches the model**.

## What it does

- **Scans every tool result inline.** A `transform_tool_result` hook runs
  each result through elcaro's deterministic detector taxonomy (A–G:
  authority spoofing, delimiter escapes, task hijacking, obfuscation,
  hidden placement, conditional triggers, agent-to-agent steering) —
  sub-10 ms, fully local, no network.
- **Enforces in place.** Quarantined results are swapped for a signed
  `[CONTENT QUARANTINED BY ELCARO]` notice *before* they're appended to
  the conversation — the model never sees the poison. Suspicious content
  under the threshold gets a `[ELCARO GUARD]` advisory appended.
- **Covers the args lane.** `pre_tool_call` scans the arguments of
  configured tools (`write_file`, `terminal`) so a model pasting fetched
  content into a heredoc doesn't smuggle the payload past the result scan.
- **Backstops the turn.** `pre_llm_call` injects a one-line summary of new
  quarantines so the agent doesn't retry fetches or work around the guard.
- **Baits exfiltration with a decoy honeypot.** Drops `service-credentials.env`
  with an installation-unique `ELCARO-DECOY-*` marker in the plugin data dir.
  Any tool result or `write_file`/`terminal` args payload containing the bait
  marker triggers a deterministic `1.00 dangerous` quarantine (`decoy_exfiltration`).
- **Records a tamper-evident flight-recorder trail.** Every verdict lands in a
  hash-chained JSONL threat log (`prev_hash` → `entry_hash`, Ed25519-signed when
  a key is configured) with canary provenance edges (`type: "edge"`, rendered as
  `propagation ⚡` in the Desktop pane) and signed clean-scan receipts.
- **Gates actions, not just content.** A quarantine taints the session
  (`taint_ttl_seconds`, default 30 min). While tainted, the kernel evaluates
  each tool call as the action it really makes — `tool_call` unwraps to its
  target, `execute_code` is judged as the shell it runs, `process_manage` as
  the line it types — and refuses credential-path reads/writes and
  instruction-file writes (`SKILL.md`, `AGENTS.md`, `SOUL.md`, plugin configs),
  while network egress and outside-workspace writes escalate to Hermes's
  approval gate. A credential read + egress channel in one shell step is
  refused even in a clean session. Taint propagates into spawned subagents
  (`subagent_start`) so delegation can't launder it. `taint_policy`
  (`enforce` / `monitor` / `off`), `policy_allow_paths` and
  `policy_allow_hosts` tune the gate; every decision lands in the same signed
  log as a `policy` receipt (`gate-block` / `gate-approve` rows in the pane).

## Commands & Surfaces

| Surface | Use |
|---|---|
| `/elcaro` | Show recent verdicts & quarantine count in-session |
| `/elcaro calibrate` | Replay the seeded attack & benign corpus against yourself in-session |
| `/elcaro verify` | Recompute the SHA-256 `prev_hash → entry_hash` chain and verify tamper-evidence |
| `/elcaro <index>` | Explain a specific logged verdict |
| `hermes elcaro log \| status \| calibrate \| verify` | CLI access to the signed threat log |
| Desktop `threat log` pane + `◉` chip | Real-time verdict rows (`scanned`, `quarantined`, `args-block`, `HONEYPOT`, `propagation ⚡`), hash-chain tamper badge, honeypot status line, and a signed-receipts drawer via `/api/plugins/elcaro/{verdicts,receipts,edges,stats,verify,decoy}` |

## Tools

| Tool | Use |
|---|---|
| `elcaro_scan` | Full verdict + evidence trail — before payments, sends, sign-ins, writes |
| `elcaro_quick_scan` | Triage: score, level, quarantine flag |
| `elcaro_explain` | Plain-language explanation of a logged verdict |

## Settings

`sensitivity` (strict / balanced / permissive), `enforcement`
(replace / flag / off), `skip_tools`, `scan_args_tools`,
`advisory_threshold`, `quarantine_threshold`, optional hosted `api_url`,
and a `signing_key` for signed verdicts — all under the plugin's page in
the Desktop settings.

## Provenance

Detection engine: [elcaro](https://github.com/udirobert/elcaro) — the IPI
detection miner. The engine is vendored (`elcaro_engine/`, refreshed by
`vendor.sh`) so the plugin runs fully offline with three small deps:
`pydantic`, `cryptography`, `httpx`.
