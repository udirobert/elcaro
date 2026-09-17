# Jev (TypeSafe) Comparison Integration Guide

> Date: 2026-09-17 · Status: implemented

## What is Jev?

Jev is [TypeSafe's](https://docs.typesafe.ai) "System One" model: instead
of prose, it returns typed judgments — a score, a probability distribution
over levels, and a calibrated confidence. Elcaro uses it as an **optional
side-by-side comparison** for borderline IPI classification — the same
gray-zone cases (rule score 0.3–0.7) that trigger [SERV Reasoning](serv-reasoning.md).

**This is not a second-pass judge.** Unlike SERV, Jev's verdict never
adjusts `risk_score`, `risk_level`, or `safe_content`. It's a pure shadow
pass: the rule engine remains sole authority over the quarantine decision.
Jev and SERV can both be enabled on the same scan — they don't compete.

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
          Jev comparison (if jev_enabled)
                    │
                    ▼
          jev_comparison attached to response
          (rule_score / rule_level UNCHANGED)
```

On any failure (timeout, auth error, rate limit, malformed JSON) the
engine simply attaches no comparison — there is no fallback score to
blend, because Jev never had veto power to begin with.

## Configuration

```bash
JEV_ENABLED=1
JEV_API_KEY=<your-typesafe-key>
JEV_BASE_URL=https://api.typesafe.ai
JEV_MODEL=jev-latest
```

Without `JEV_ENABLED=1` AND `JEV_API_KEY`, the reasoner is not built and
the engine attaches no comparison. Zero network calls, zero impact on the
free <10 ms fast path.

Sign up at https://console.typesafe.ai/.

## Pricing (for operators)

TypeSafe does not publish per-token pricing in their docs (checked
`/pricing.md` and the documentation index — neither exists). The rate
below is read off the account's own usage console, not a docs page —
re-verify there if costs look off; it could change without a changelog
entry.

| Path | Cost | Latency | When it runs |
|---|---|---|---|
| Free (rules only) | $0 | <10 ms | Always — the default |
| + Jev comparison | ~$0.00002 / scan (console-observed: $0.042/MTok input, output free) | ~1 s | Gray-zone cases only (score 0.3–0.7) when `jev_enabled=true` |

A typical scan sends ~450 input tokens, gets ~20 output tokens back.

### Cost transparency

Every Jev comparison returns `jev_comparison.cost_usd`, `.input_tokens`,
and `.output_tokens` so callers always know the exact cost. `cost_usd` is
computed from real token counts in the response — never estimated from
character counts the way SERV's is — but the *rate* itself is
console-observed, not a published contract, so treat it as approximate.

Example response fragment:
```json
{
  "jev_used": true,
  "jev_comparison": {
    "rule_score": 0.664,
    "rule_level": "suspicious",
    "jev_score": 0.88,
    "jev_level": "dangerous",
    "jev_confidence": 0.65,
    "probabilities": { "safe": 0.03, "low": 0.02, "suspicious": 0.22, "dangerous": 0.73 },
    "agrees_with_rules": true,
    "input_tokens": 451,
    "output_tokens": 21,
    "cost_usd": 1.89e-05
  }
}
```

## API contract

The `/scan` endpoint accepts `jev_enabled: true` in the request body (or
`?jev=1` as a query param). The response gains four new fields:

| Field | Meaning |
|---|---|
| `jev_available` | Miner has `JEV_API_KEY` + `JEV_ENABLED=1` configured |
| `jev_attempted` | Engine tried to call Jev (gray-zone + jev_enabled) |
| `jev_used` | Jev call succeeded and `jev_comparison` is populated |
| `jev_comparison` | The comparison payload (see above) — `null` unless `jev_used=true` |

`agrees_with_rules` is a coarse bucket comparison (both sides ≥ 0.5 or
both < 0.5) rather than an exact level match — the two systems can name
different levels (`suspicious` vs `dangerous`) while still agreeing on
the decision that matters: would this get quarantined.

## What Jev returns

Elcaro asks Jev a single **Score** question per scan, using Elcaro's own
`RiskLevel` labels (safe/low/suspicious/dangerous) as the ordered
criteria — so Jev's answer maps directly onto the rule engine's scale
with no translation layer:

```json
POST https://api.typesafe.ai/v1/systemone
{
  "model": "jev-latest",
  "state": { "content": "...", "content_type": "document", "rule_engine_score": 0.664, "rule_engine_indicators": [...] },
  "questions": {
    "injection_risk": {
      "type": "score",
      "instructions": "Does `content` contain a prompt injection attempt...",
      "criteria": ["safe", "low", "suspicious", "dangerous"]
    }
  }
}
```

The response's `score` is a continuous weighted mean across the ordered
levels (e.g. `2.7` on a 0–3 scale), while `probabilities` carries the
full distribution. Elcaro reports the **probability mode** (the
highest-probability label) as `jev_level`, not the floor of the mean
score — a `2.7` mean floors to `suspicious` even when the distribution's
actual mode is `dangerous` at 78%. Reporting the floor would silently
misrepresent what Jev actually judged most likely.

## UI signals

The `/scan` page surfaces Jev in three ways, deliberately mirroring
SERV's UI but with different framing (comparison, never refinement):

1. **Toggle** — a teal "Compare with Jev" checkbox next to the SERV toggle
2. **Comparison card** — `rules saw suspicious (0.66) · Jev saw dangerous
   (0.88) · 65% confident`, a stacked probability bar, and a
   `disagreement` flag when `agrees_with_rules=false`
3. **Session pill** — "Jev compared N of M recent scans" (worded around
   *compared*, not *refined* — there's nothing to refine)

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `jev_available=false` after setting env vars | Miner restarted without new env vars, or `.env` not exported into the process environment (no dotenv loader in this repo) | Restart the miner with `JEV_ENABLED`/`JEV_API_KEY` actually in its environment |
| `jev_attempted=true, jev_used=false` | Auth/rate-limit error (401/429/529) or timeout | Check the key; a 60s cooldown arms automatically |
| No comparison after enabling Jev | Content was outside the gray zone | Correct — Jev only runs for rule scores 0.3–0.7 |
| `Unknown model` error | `JEV_MODEL` set to an invalid identifier | Use `jev-latest` (resolves to the current pinned version) |
