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
- **Leaves a signed trail.** Every verdict lands in a JSONL threat log
  (Ed25519-signed when a key is configured) under the plugin data dir —
  queryable with `elcaro_explain`, reviewable by a human later.

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
