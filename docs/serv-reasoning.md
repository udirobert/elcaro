# SERV Reasoning Integration Guide

> Date: 2026-09-15 · Status: implemented · aligned with
> [SERV day-one recommendations](https://docs.openserv.ai/serv-reasoning/day-one)

## What is SERV?

SERV (OpenServ) is a hosted reasoning API that exposes OpenAI-compatible
chat completions behind a bearer-token. Elcaro uses it as an **optional
second-pass judge** for borderline IPI classification — cases where the
rule engine's score lands in the gray zone (0.3–0.7) and a purely
deterministic verdict isn't reliable.

## Architecture

```
Content → Rule engine → score
                        │
             ┌──────────┴──────────┐
             │  score in [0.3, 0.7]?│
             └──────────┬──────────┘
                   yes / no
                    │
                    ▼
          SERV Reasoning (if enabled)
                    │
                    ▼
          Blend: 0.5 × rule + 0.5 × SERV
                    │
                    ▼
          Final score (capped by rule floor: max(final, 0.5 × rule))
```

Rules always keep veto power. SERV can refine upward or downward but
cannot zero out a strong rule signal. On any failure (timeout, auth error,
malformed JSON, credit exhaustion) the rule-based score stands unchanged.

## Configuration

Set these environment variables on your miner deployment:

```bash
SERV_ENABLED=1
SERV_API_KEY=<your-serv-key>
SERV_BASE_URL=https://inference-api.openserv.ai/v1
SERV_MODEL=gpt-5.4-mini       # cheapest model in the SERV catalog
SERV_TIMEOUT=8                 # seconds — generous for LLM latency
```

Without `SERV_ENABLED=1` AND `SERV_API_KEY`, the reasoner is not built and
the engine stays purely rule-based. Zero network calls, zero impact on the
free <10 ms fast path.

Sign up at https://console.openserv.ai/ — new accounts get a $5 starter
credit.

## Pricing (for operators)

| Path | Cost | Latency | When it runs |
|---|---|---|---|
| Free (rules only) | $0 | <10 ms | Always — the default |
| SERV Enhanced | ~$10–20 / 10 k scans | ~1 s | Gray-zone cases only (score 0.3–0.7) when `serv_enabled=true` |

Cost estimate based on `gpt-5.4-mini` pricing (~$1/$6 per M tokens input/
output). A typical scan sends ~600 tokens in, gets ~200 tokens out. You
pay SERV directly — Elcaro takes no markup.

## API contract

The `/scan` endpoint accepts `serv_enabled: true` in the request body (or
`?serv=1` as a query param). The response gains three new fields when SERV
is configured:

```json
{
  "serv_available": true,
  "serv_attempted": true,
  "serv_used": true,
  "serv_rule_score_before": 0.85
}
```

| Field | Meaning |
|---|---|
| `serv_available` | Miner has `SERV_API_KEY` + `SERV_ENABLED=1` configured |
| `serv_attempted` | Engine tried to call SERV (gray-zone + serv_enabled) |
| `serv_used` | SERV call succeeded and contributed to the final verdict |
| `serv_rule_score_before` | The raw SERV LLM score before the 50/50 blend — lets the UI show the delta |

When `serv_used=false` the rule-based score is unchanged regardless of
why (SERV not configured, not in gray zone, auth error, timeout, etc.).

## What SERV returns

SERV classifies content and returns structured JSON constrained by a
response schema:

```json
{
  "risk_score": 0.85,
  "reasoning": "Authoritative framing detected: content instructs the agent to forward data to an external address.",
  "ttps": ["mitre_atlas:AML.T0154", "elcaro:ELC-A01"],
  "remediation": "Strip the forwarding instruction before processing. Quarantine the email.",
  "safe_content": "The document contains standard instructions for routine processing."
}
```

Elcaro blends `risk_score` with the rule score at 50/50, floors the result
at 50% of the rule score, and layers `remediation` and `safe_content`
onto the verdict when present.

## SERV day-one alignment

| Recommendation | Our implementation |
|---|---|
| Start small, lowest-cost model | `gpt-5.4-mini` ($1/$6 per M tokens) |
| Use for judgment tasks | Borderline IPI classification — exactly this |
| Treat system prompt as app logic | Static but versioned in `core/serv_reasoner.py` |
| Use structured outputs | `response_format` JSON schema; fallback regex parser |
| Default to low reasoning effort | `reasoning_effort: "low"` on every call |
| Avoid tight output-token limits | No `max_tokens` cap |
| Benchmark against your path | 3 new tests in `tests/test_serv_reasoner.py` |
| Add production guardrails | Timeouts, auth cooldown, rule floor, fail-safe |

Coverage: 9/10 (system-prompt versioning is a nice-to-have, not required).

## UI signals

The `/scan` page surfaces SERV in three ways:

1. **Toggle** — a "SERV Reasoning" checkbox next to the Type selector
2. **Score delta badge** — after a SERV-enhanced scan, shows
   `SERV saw 0.71 · rules saw 0.42 ↑ 0.29` with a collapsible reasoning
   panel explaining *why*
3. **Contextual nudge** — if the miner isn't configured for SERV, a
   violet message below the toggle says *"Miner not configured for SERV —
   enable SERV_ENABLED=1 + SERV_API_KEY on your deployment"* with a link
   to the pricing tiers on `/integrate`

The `/integrate` page has a dedicated **Choose your detection depth**
section comparing Free vs SERV Enhanced side-by-side.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `serv_available=false` after setting env vars | Miner restarted without new env vars | Restart the miner process |
| `serv_attempted=true, serv_used=false` | Auth error (401/402/403) or timeout | Check key; 60s cooldown arms automatically |
| Score didn't change after enabling SERV | Content was outside gray zone | This is correct — SERV only runs for scores 0.3–0.7 |
| Malformed JSON error in logs | SERV returned non-JSON | Rare; falls back to rule score automatically |
