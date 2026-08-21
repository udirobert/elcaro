# Kiro Guard — Elcaro Protects the Kiro Agent: Design

## Vision

Elcaro's product thesis is "scan what the agent reads before it acts."
This spec turns that thesis on our own tooling: the Kiro agent developing
Elcaro retrieves web content (docs, GitHub issues, package pages) that could
carry indirect prompt injection. The guard hook closes that loop — and in
doing so demonstrates Kiro's hook primitive with a use case unique to a
security product.

```
Kiro agent ──▶ web tool (fetch) ──▶ tool result ──▶ PostToolUse hook
                                                        │
                                          scripts/kiro-scan-hook.py
                                                        │
                                              POST /scan (Elcaro)
                                                        │
                              safe → exit 0 (silent)    │    injection → exit 1
                                                        │
                                              STDERR warning → agent
```

## Decision: PostToolUse, not PreToolUse

| Option | Verdict | Why |
|---|---|---|
| `PreToolUse` (web) | Rejected | PreToolUse sees the tool *input* — a URL, not the content. The injection vector is the retrieved body, which only exists after the tool runs. |
| `PostToolUse` (web) | **Chosen** | Sees the tool *result* — the actual text entering the agent's context. A non-zero exit delivers STDERR to the agent as a warning; the agent then treats the retrieved content as untrusted. |
| `UserPromptSubmit` | Rejected | The user's own prompt is the trusted channel (Elcaro weights `chat_message` lowest); scanning it adds latency without threat coverage. |

`PostToolUse` cannot un-execute the fetch — but that's fine: the content is
already blocked from *influencing* the agent by the warning, and the
middleware (the enforcement layer) remains the hard gate for production
agents. The hook is the advisory layer for the development loop.

## Decision: fail-open on infrastructure, fail-closed on detection

- **Detection (risk >= 0.5):** loud — non-zero exit, STDERR warning. The
  agent is explicitly told the content contains injection attempts.
- **Miner down / timeout:** silent exit 0. A monitoring layer that bricks
  the dev loop when its backend restarts gets disabled within a day — and
  this repo's own uptime monitoring (`.github/workflows/uptime.yml`) already
  watches the miner. Availability of the dev loop wins; enforcement belongs
  to the middleware, not the advisory hook.

## Decision: stdlib-only scanner script

The hook command runs in Kiro's execution context — the project `.venv` is
not guaranteed to exist or be on PATH. `json` + `sys` + `urllib.request`
from the standard library removes the entire dependency question. The scan
is a single small POST; `httpx` buys nothing here.

## Decision: default to the live API

`ELCARO_MINER_URL` defaults to `https://api.elcaro.trustfall.xyz` so the
hook works out-of-the-box in any clone (judges, contributors) with zero
setup — mirroring the product-first README philosophy. Local development
overrides the env var to `http://localhost:8848`.

## Payload extraction

The docs show `tool_name` and `tool_input` on STDIN for tool hooks; the
result field for `PostToolUse` is not exhaustively documented. Task 1
therefore captures one real event to a log before finalising extraction —
defensive field lookup (several candidate keys, deep search for the longest
string value) with a safe empty-scan fallback.

## Risks

| Risk | Mitigation |
|---|---|
| Result payload shape differs from docs | FR-4.1 discovery step; defensive extraction; never crash |
| Latency added to every web fetch (~0.5s RTT to VPS) | Single POST, 10s timeout, silent pass; acceptable for a security layer |
| Hook stderr wording itself phishes the agent | Warning text is fixed, factual, and instructs distrust of the *content*, not new actions |
