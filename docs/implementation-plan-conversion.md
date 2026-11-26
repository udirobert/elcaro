# Elcaro — Implementation Plan: Conversion, UX, and Monetization

Derived from the 2026-11-26 product/UX and monetization audits, revised after
verification against gateway, scan, extension, and metering reality. Ordered by
priority (P0 first), not by original leverage guess. Each workstream has scope,
files touched, and a measurable done-when test.

## Verified live state (2026-11-26/27) — the constraints this plan must respect

| Fact | Evidence | Consequence |
|---|---|---|
| ~~Gateway has never served a successful production request~~ **PROVEN 2026-11-26** | W5 smoke test: 200 + receipt + verify green | Keyed traffic is no longer a gate for WS4 |
| `/api/x402/scan` paid scan lane is live and settling onchain | status: `paid: true, payToConfigured: true, settlement: onchain` | The 429 upsell should point here — not at the unproven gateway pay-per-call lane |
| Free scan can invoke SERV-backed analysis | miner `/config`: `serv_available: true`; scan form/API pass `serv_enabled` | Direct cost exposure on the free path; rate limiting is P0, not week 2 |
| ~~Extension bridge payer key is malformed~~ **FIXED 2026-11-26** | `payerAddress` now resolves | — |
| ~~Extension bridge accepts ANY chrome-extension origin~~ **CLOSED 2026-11-26** | `allowAnyExtension: false`, fake origin → 403 | Reopen per WS0b instructions when dev resumes |
| Miner API is directly reachable, bypassing the web proxy | `api.elcaro.trustfall.xyz` serves `/scan` without the Netlify edge | Rate limiting only at Netlify is insufficient |
| Phase 1 was Outcome C | `lexsi-eval/RESULTS-phase1.md` | No uplift claims; the benchmark is not a willingness-to-pay unlock |

---

## P0 — Safety and proof (before any further traffic push)

### WS0a — Finish the OpenServ launch verification · ✅ DONE 2026-11-26

Tracked in `docs/openserv-dolphin-launch.md` W5 — all green:

- Keyed call (`elk_39QwAm0B…`) returned **HTTP 200** with
  `x-elcaro-verdict: dangerous`, `x-elcaro-action: quarantined`, signed
  receipt; upstream completion narrated the quarantine (injection never
  reached the model).
- `POST /verify` → `{"valid":true,"key_id":"3383cee92fdbdf2f"}`.
- `/metrics` per-key row populated; `verify-live.sh` 27/27.
- Homepage/nav/keys deploy checks all pass.
- Note: the smoke-test payload in the launch doc was corrected — SERV
  requires a system message and `tool` messages must answer `tool_calls`.
- Remaining in that doc: owner actions only (like/repost, quote-tweet).

### WS0b — Close the extension bridge holes · ✅ DONE 2026-11-26

- `TELEGRAPH_X402_KEY` replaced in the production context with the valid
  Keychain key — `payerAddress` now resolves to
  `0x3aB5CDE666c356B043111AAFDA16aC258E19868F`.
- The extension is not installed in any browser on the owner's machine, so no
  id exists to pin: chose the deliberate close,
  `TELEGRAPH_BRIDGE_ALLOW_ANY_EXTENSION=0`. Probe of a fake
  `chrome-extension://` origin now returns 403 FORBIDDEN_ORIGIN; site/Gmail
  origins unaffected. The direct miner rail remains available for dev.
- Status endpoint gained `allowAnyExtension` so the closed state is
  observable without probing (commit `a90f784`).
- **To reopen for dev:** load the extension, copy its id from
  chrome://extensions, `netlify env:set TELEGRAPH_BRIDGE_EXTENSION_IDS <id>
  --context production`, redeploy.
- **Ops lesson recorded:** Netlify cancels builds for docs-only/empty commits
  (`base = "app/web"`), so env-only changes need a real content change or
  manual deploy to ride on — the canceled 19:42/19:49 deploys are why the
  first env fix silently did nothing.
- **Key hygiene note:** the Netlify CLI echoes the value in `env:set`
  confirmation output — treat any key set through it as exposed in terminal
  scrollback. The payer key is testnet-only; rotate before it ever holds
  real value.

### WS0c — Defend the free scan path · 2–3 days

**Problem:** no rate limiting anywhere on `/scan`; the scan UI and API pass
`serv_enabled`, and the production miner has SERV available — strangers can
spend real money through the free path. The miner API is directly reachable,
so a Netlify-only limiter is trivially bypassed.

**Changes:**

1. Rate limit at the miner/API layer (`miner/api.py`), not only the Netlify
   proxy. Per-IP token bucket (e.g. 30/day burst-tolerant) backed by a durable
   store (Neon or Redis) — in-memory does not survive processes or scale-out.
2. Price or disable the SERV deep-analysis pass for anonymous free scans
   (`serv_enabled` requires a key, or is capped separately at a much lower
   quota).
3. On limit, return a friendly 429 that upsells the **already-live** paid scan
   lane: "$0.01 per scan, no signup — x402" pointing at `/api/x402/scan`, or
   "wait N minutes". The limit itself is the monetization trigger.
4. Abuse logging: repeat offenders by IP hash into the metrics rollup.

**Done when:** direct miner-API calls (bypassing the web app) are limited;
429 body/headers carry the x402 hint; load test shows graceful degradation;
SERV-enabled anonymous scans are impossible or tightly capped.

### WS0d — Durable funnel instrumentation · 1 day

**Problem:** a small analytics system exists (`app/web/src/lib/analytics.ts`,
`/api/analytics`) but is audit-scoped, writes JSONL to local disk (ephemeral on
serverless), and records raw IPs. It cannot measure the conversion redesign.

**Changes:**

1. Replace/extend the sink with durable storage (Neon table or a
   privacy-preserving external tool).
2. Hash or drop IPs.
3. Events: landing → scan start → verdict → share/copy → integrate page →
   key mint. Add these BEFORE deploying WS1/WS2 so the redesign is measurable.

**Done when:** events persist across deploys; a dashboard/query can answer
"what fraction of landing visitors reach a verdict" for a given week.

---

## P1 — Conversion batch

### WS1 — Fix the front door · mostly done, finish and deploy · ~0.5–1 day

Largely implemented in the working tree: scan is the primary CTA, developer
gateway is secondary, jargon moved below the fold (`app/web/src/app/page.tsx`).
Remaining requirements:

1. Preserve the OpenServ promise: keep the winner badge above the fold and the
   word "gateway" in the hero or immediate supporting line (e.g. "Use it free
   in the browser, or drop it in as a gateway for your agent"). The tweet's
   promise and the landing page must match.
2. Deep-link scan examples (`/scan?example=…`) so "landing → verdict" is truly
   ≤2 clicks.
3. Deploy as one batch WITH WS2 so funnel comparison is clean.

**Done when:** first-time visitor reaches a verdict in ≤2 clicks; funnel
events fire at each step; no jargon above the fold in screenshot review.

### WS2 — Simplify the scan form · 1–2 days

**Problem:** `scan-form.tsx` (~892 lines) exposes SERV/Jev/Laya/JEV-VL toggles
inline in the main action row; several are no-ops on the free path.

**Changes:**

1. Collapse comparison rails behind an "Advanced: second opinions" disclosure,
   collapsed by default, labeled honestly ("calibration / comparison — does not
   change the verdict").
2. Mobile audit at 375px; fix stacking.
3. Microcopy to ≥12px; check `text-ink-faint` contrast against AA.

**Done when:** default path shows one input, one button, one verdict; toggles
hidden unless expanded; Lighthouse a11y ≥ 95 on `/scan`.

---

## P1/P2 — Measurement, then money

### WS3 — Attribution + revenue visibility · 3–5 days (NOT 1–2; precedes payment arming)

**Problem:** paid usage is weakly attributable (x402 gateway usage is encoded
as `key_id = "x402:{payer}"` — a surrogate, not a schema). `/api/x402/scan`
emits no usage events at all. No revenue view.

The original plan claimed "Auto-DDL already handles the migration" — **false**.
`metering/neon.py` uses `CREATE TABLE IF NOT EXISTS` only; there is no
`ALTER TABLE` path, and `_EVENT_COLUMNS` is a 1:1 projection of the frozen
`UsageEvent` dataclass, so every layer needs a coordinated change.

**Changes:**

1. Explicit Neon migration: `ALTER TABLE usage_events ADD COLUMN payer_address
   text` (+ `payment_network`, `payment_tx_hash`, `settlement_status`).
2. Extend `UsageEvent` in `core/usage.py` with the same fields; update
   `_EVENT_COLUMNS`; update all emitters.
3. Instrument BOTH lanes: gateway x402 (`_x402_gate` verify/settle path) and
   `/api/x402/scan` (which currently emits nothing).
4. Distinguish `verified_local` from `settled` — revenue rollups count settled
   only; settlement failures surface as their own metric.
5. `/api/revenue` rollup: paid calls, USDC collected, by day; payer-level
   detail is operator-only (auth-gated), public aggregates only.
6. Funnel events from WS0d join to revenue where keys are involved.

**Done when:** a paid scan is traceable end-to-end in the DB: tx hash → payer
→ usage event → settled rollup row; settlement failure produces a visible
metric, not a silent gap.

### WS4 — Price and arm the paid lanes · 4–7 days (NOT 2–3)

**Problem:** the original plan conflated two different surfaces:

- `/api/x402/scan` — paid scan, already live/onchain. Needs validation only.
- Gateway x402 pay-per-call — an **LLM proxy** using a server-held upstream
  credential. A fixed $0.002/request price is exploitable: callers route
  arbitrary large LLM traffic through Elcaro's SERV key and Elcaro subsidizes
  the inference cost.

Also: `ELCARO_GATEWAY_PRICE_USDC` is not a margin knob — when > 0 it IS the
x402 offer amount (`gateway/app.py:332-346`). There is currently no markup
mechanism at all.

**Changes, in order:**

1. Validate the scan lane end-to-end on testnet: 402 → pay → scan → verdict,
   settlement confirmed, attribution row written (depends on WS3 schema).
2. Decide what gateway pay-per-call actually sells:
   - **scan-only pricing** (charge for Elcaro's scan, caller supplies their own
     upstream key — no subsidy possible), or
   - **bundled inference** (requires ALL of: max input/output token or body
     caps, model allowlist or forced cheap model, per-payer rate limits, and a
     unit-economics calculation showing upstream cost + scan cost + margin).
3. Implement the chosen model. `X402_PAYTO` + upstream key in production
   `.env`; scripted 402 → pay → serve test on Base Sepolia first.
4. Network decision (Sepolia vs mainnet) made deliberately, documented on
   `/integrate` with real numbers replacing the "~$0.002/scan" estimate in
   `pricing-tiers.tsx`.
5. If CDP facilitator is wanted, implement the JWT auth path noted missing in
   `netlify.toml`.

**Done when:** scripted end-to-end test on the chosen network: 402 challenge →
payment → scanned signed response → settled attribution row; per-payer caps
proven by exceeding them in the test; documented price covers measured
upstream cost with margin.

---

## P2 — Distribution surface

### WS5 — Gmail extension · 1–2 days cleanup + open investigation + external CWS review

**Problem:** the original plan said "pin routing to miner 8848 by default" —
**technically and economically flawed**. The direct `ask/8848` rail is a dev
fallback that does not count as Telegraph miner volume and is not the payment
path; pinning to it sacrifices both. "Never charge for a non-verdict — refund
or retry" is not implementable after x402 exact payment settles; prevention is
the only real lever.

**Changes:**

1. Depends on WS0b (bridge must be fixed/pinned first).
2. Measure how often auto-routing produces non-verdicts (log rail + verdict
   boolean per scan; the normalize layer already distinguishes verdict from
   signal).
3. Investigate whether the ask text/schema/intent can keep routed traffic on
   Elcaro's miner; only then decide whether direct-8848 routing is worth the
   volume sacrifice. Record the decision with data.
4. Ship real icon set (16/32/48/128), `aria-live="polite"` + focus trap on the
   overlay, drop unused permissions.
5. CWS listing (privacy policy, permission justifications) and submit — review
   time is external and not part of the estimate.

**Done when:** stranger installs from CWS, scans a Gmail message, gets
SAFE/CAUTION/BLOCK with proper icon; every charged scan corresponds to a
verdict or the scan was never charged because routing was prevented upstream
of payment.

---

## P3 — Identity, billing, and research credibility (do not bundle)

The original WS7 bundled three independent things and hinged them on a
category error: "publish the Phase 1 benchmark — the willingness-to-pay
unlock." There is no unpublished win: Phase 1 was **Outcome C** (attacks 15→5
but passes 65→52, beyond tolerance). These are three separate workstreams:

### WS6a — Research: Phase 2 benchmark · research project, own timeline

Implement the three hypothesized fixes from `RESULTS-phase1.md` (skip
`serv_prompt_guard` on Elcaro-handled parts, segment-level quarantine, rewrite
the warn prefix) and evaluate on a NEW held-out set — H is in-sample for these
changes. This is the only path to a legitimate uplift claim.

### WS6b — Credibility: publish Phase 1 honestly · 1–2 days

Write up Outcome C as-is: the attack reduction, the pass cost, the mechanism
analysis. This demonstrates rigor and is valuable content — but it is not a
marketing win and must not be framed as one. Link from `/evaluate/benchmark`.

### WS6c — Identity & prepaid billing · 2–4 weeks, gated on WS3/WS4 usage data

1. Optional verified email attach to keys (magic link); anonymous keys keep
   working. Recovery = re-issue to verified email. Note: storing emails is a
   privacy commitment — update the privacy story before collecting them.
2. Prepaid credit packs via x402: credit balance table + decrement in
   `get_key`; reuse the verify/settle path.
3. Stripe only after usage evidence justifies it. Do not build speculatively.

---

## Sequencing

| Priority | Work | Gate |
|---|---|---|
| P0 (now) | WS0a launch verification, WS0b bridge holes, WS0c free-path defense, WS0d instrumentation | none — start immediately |
| P1 | WS1 + WS2 conversion batch, deployed together | WS0d (so the change is measurable) |
| P1/P2 | WS3 attribution schema + migrations | none, but precedes WS4 |
| P2 | WS4 price + arm paid lanes | WS0a (proven keyed traffic) AND WS3 (attribution) |
| P2 | WS5 extension | WS0b |
| P3 | WS6a/b/c | WS6c gated on WS3/WS4 usage data; WS6a/b independent |

## Explicitly out of scope for now

- Stripe / card billing (wait for usage evidence).
- Org/team accounts (needs identity first).
- "Protected by Elcaro" badge program.
- New detection classes (engine is not the constraint).
- Uplift marketing of any kind until WS6a produces it on fresh held-out data.
