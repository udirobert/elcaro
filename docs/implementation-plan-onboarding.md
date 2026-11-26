# Implementation plan — onboarding inversion

> **Date:** 2026-11-26 · **Trigger:** first public response to the Dolphin
> quote-tweet: improve onboarding · **Status:** OB1 core shipped (`f604023`),
> then corrected the same day by a review pass — see
> [Verification log](#verification-log--2026-11-26-review-pass-after-f604023).
> OB3 is blocked on the new **OB6**; OB2 is no longer urgent; **OB7** is a new
> open ops item.
> **Related:** [implementation-plan-conversion.md](implementation-plan-conversion.md)
> (scan-first conversion batch — this plan applies the same insight one level
> deeper, to the integration surface)

## The diagnosis, with evidence

The conversion batch made the *marketing* surface scan-first. The
*integration* surface still assumes commitment before value. Every fact
below verified live 2026-11-26:

| Fact | Evidence | Consequence |
|---|---|---|
| Free scan needs NO key and answers in seconds | `curl POST api.elcaro.trustfall.xyz/scan` unauthenticated → **200 + verdict** | The best possible first-run experience already exists — and is absent from the onboarding path |
| `/integrate` opens with "mint an elk_ key at /keys" | `app/web/src/app/integrate/page.tsx:19` | Account creation demanded before any value — inverted vs. the Stripe-docs pattern (value in 30s, commitment later) |
| `npm i @elcaro/sdk` → **404** | `npm view @elcaro/sdk` errors; package.json is `0.1.0`, not private, simply never published | Anyone who guesses the package name hits a dead end at command one — dead ends cost more trust than missing features |
| Key minting forces the upstream decision (SERV/OpenAI/…) at minute zero | `/keys` flow | A decision only someone who already understands the architecture can make — exactly backwards for first run |
| x402 pay-per-call is zero-signup but not zero-friction | requires wallet + USDC | Right path for *agents*, wrong path for *humans evaluating* — do not present it as the easy option |
| The person who gave this feedback tried within minutes of the post | the reply itself | Closing the loop publicly when fixed is worth more than the fix — plan for it |

## Verification log — 2026-11-26, review pass after `f604023`

Measured against production from a clean shell and a clean browser profile,
after the OB1 core landed. Where the table above and production disagree, this
section wins.

| # | Check | Result |
|---|---|---|
| V1 | The exact curl on `/integrate`, specimen included | ✅ `200`, `risk_level: dangerous`, 4 techniques, **0.89 s** wall clock, no key, no editing |
| V2 | Shipped copy: "the free scan is rate-limited per IP" | ❌ **34 consecutive scans → 34× `200`**, no `X-RateLimit-*`, no `429`. `core/rate_limit.py:292-310` returns `None` unless `ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_DAY > 0`, and `deploy/ecosystem.config.cjs:73` sets `300` — so the limiter is inert or absent on `api.`. Open ops item: **OB7** |
| V3 | Shipped "What comes back" sample | ❌ three pretty-printed fields; the real body is **7 260 bytes on one line**. Corrected: verbatim prefix + field guide |
| V4 | Can a minted `elk_` key be used? | ❌ gateway `/v1/*` is the only consumer (`gateway/app.py:711-716`) and it *also* requires the caller's own upstream credential; miner `/scan` has no key auth (`miner/api.py:217-234`); the web proxy forwards no key; the gateway exposes no `/scan` route (`gateway/app.py:969-1071`). This is **OB6** |
| V5 | OB3 item 1, "default upstream to SERV" | ✅ already shipped — `key-manager.tsx:70` is `useState("serv")` |
| V6 | The plan's "verify the receipt at `/verify`" | ⚠️ `/verify` is **404** on the web app. Real surfaces: miner `POST /verify` (content + six response fields + signature) and gateway `POST /verify` (`{payload, signature}`, base64, gateway receipts only). Round trip tested → `{"valid":true,…}`; tampering one character → `{"valid":false,…}` |
| V7 | OB2, "anyone who guesses the package name hits a dead end" | ⚠️ overstated — no reachable reference exists: zero `@elcaro/sdk` strings under `app/web/src`, none in `public/llms.txt`, and `sdk/js/README.md` correctly says `git clone`. The 404 appears only in this plan, `docs/openserv-dolphin-launch.md:50`, `docs/roadmap-gateway.md:327` |
| V8 | `/integrate` section order | ❌ key-first: `00 Gateway` opened with `// Mint an elk_ key at /keys`. Corrected: no-key Direct API is now `00`, gateway `01` |

## Principles

1. **Value before commitment, strictly ordered.** Nobody is asked to create,
   install, decide, or pay anything before they have seen a verdict.
2. **Every step in the docs must be runnable.** A command that fails is worse
   than no command. Each step is tested exactly as written, in a clean shell.
3. **Decisions deferred, not removed.** Upstream choice, payment, and keys
   all still exist — they appear at the moment the user has a reason to care.
4. **No new claims.** This plan rearranges true things; it does not add any.
   The review pass is what enforces this: shipped copy is re-measured against
   production, not reread. V2 and V3 above were both written in good faith and
   both wrong.

## Workstreams

### OB1 — No-key-first rewrite of `/integrate` · ~1 day · **core shipped**

**Shipped in `f604023`:** the "Try it right now — nothing to create" section
opens the page with the verified no-key curl, the injection specimen, and an
honest note about what the endpoint is for.

**Corrections applied in the review pass (V1–V3, V8):**

1. The limit sentence asserted a per-IP limit production does not enforce.
   Reworded to what is true — unauthenticated, best-effort, shared — naming
   the abuse case instead of quoting an unenforced number. Re-enabling the
   limiter is OB7; the number goes back on the page only once it is real.
2. "What comes back" was pretty-printed and abbreviated, i.e. not the
   response. Replaced with a verbatim prefix of the real 7 KB body plus a
   field guide that names `human_summary` and `safe_content`.
3. "everything below, in order of commitment" was false — the next section was
   `00 Gateway`, whose first line asks for a key. The no-key Direct API is now
   `00`, the gateway `01` and titled "needs a key", and the hero leads with the
   unauthenticated call instead of the SDK swap.
4. Added the trust step the page was missing: every verdict is signed, and
   `GET /pubkey` returns the same `key_id` from a single zero-edit command.

**Still open:** none of the OB1 copy items. OB3's progressive disclosure
remains (the page is now ordered correctly, but the mint step still exposes the
upstream choice).

### OB2 — The npm ghost · 5 minutes, or 1 day if publishing

**Corrected on review (V7):** the landmine is not reachable from the product.
No `@elcaro/sdk` string exists under `app/web/src`, none in `public/llms.txt`,
and `sdk/js/README.md` already says `git clone`; the `/integrate` snippets
import the stock `openai` / `@anthropic-ai/sdk` clients. The 404 survives only
in internal docs, and two of those (`docs/openserv-dolphin-launch.md:50`,
`docs/roadmap-gateway.md:327`) record the fact accurately — they should not be
edited into claiming otherwise.

**So:** no emergency, and Option B is already true of every user-facing
surface. Option A (publish) stays open on its merits: if taken, add
`repository`/`homepage` and a `prepublishOnly` build first —
`sdk/js/package.json` ships `files: ["dist"]` with no prepublish hook, so a
stale `dist/` would publish silently.

**Done when:** either `npm i @elcaro/sdk` succeeds on a clean machine and the
installed quickstart returns a verdict, or the decision is recorded as
"deferred — not referenced anywhere a user can reach".

### OB6 — Make a key do something on the surface the stranger just used · 0.5–1 day

**Problem:** the ladder's second rung is empty (V4). `elk_` is accepted only
by the gateway, which additionally demands the caller's own upstream
credential, so minting a key currently buys nothing a first-time user can
execute without editing a command. **OB3's post-mint screen cannot be finished
before this exists.**

**Change (recommended):** accept `elk_` on `/scan` — on the miner directly, or
as a gateway `/scan` route in front of it. Consequences to implement:

1. Keyed scans draw from the key's own bucket instead of the shared anonymous
   one. `core/rate_limit.py` already keys windows by a hashed identity and a
   `namespace`, so this is a new namespace (`keyed_scan`), not new machinery.
2. The response keeps its `signature`/`key_id` — both are emitted today and
   the miner already exposes `POST /verify` (V6) — so receipts become
   attributable per key.
3. The post-mint command becomes the *same* curl as the first-run one plus
   `-H "x-elcaro-key: elk_…"`, with a reward that can be explained in a
   sentence: your own quota, your own receipts.

**Rejected alternative:** extend x402 scan-only pricing to keyed humans. Right
for agents, wrong here — it puts a wallet and USDC in a human's second step,
more friction than the form this plan exists to remove.

**Done when:** in a clean shell, the same specimen scanned anonymously and
with a freshly minted key differs only by one header, and the keyed call
reports its own quota rather than the shared bucket.

### OB3 — Zero-decision key minting · 0.5 day, **after OB6**

**Problem:** minting exposes the upstream choice (a `<select>` at
`key-manager.tsx:188-196`) before the user has seen a verdict, and the
post-mint screen dead-ends at "copy it now".

**Already done (V5):** upstream defaults to SERV (`key-manager.tsx:70`) — the
original item 1 needed no code.

**Changes:**

1. Move the upstream `<select>` behind an "advanced" disclosure, SERV
   pre-selected and unchanged by default.
2. One line of plain language: "this is which provider your gateway traffic is
   forwarded to — you can mint more keys later."
3. Post-mint screen becomes a continuation: the key, plus the scan curl with
   `-H "x-elcaro-key: <the key just minted>"` already interpolated. **Depends
   on OB6** — written before it, the command cannot succeed.
4. Say the gateway's own prerequisite at the point of mint: path 01 needs
   *your* OpenAI/Anthropic/SERV credential as well as the `elk_` key. Today
   that is only implied inside the code sample.

**Done when:** minting is one click with zero choices, and the post-mint
command — run as-is, nothing edited — returns a verdict drawing on the key's
quota. Verified in a clean browser profile.

### OB7 — Turn the scan rate limiter back on · 1 hour, ops

**Found on review (V2):** 34 rapid anonymous scans all returned `200` with no
`X-RateLimit-*` headers and no `429`. `direct_scan_rate_limiter_from_env()`
returns `None` when `ELCARO_DIRECT_SCAN_RATE_LIMIT_PER_DAY` is unset or `0`
(`core/rate_limit.py:292-310`), while `deploy/ecosystem.config.cjs:73` sets
`300` — so the process answering `api.` is either not the one that config
describes, or limiter init is failing open. Either way an unauthenticated
endpoint is currently unlimited, which is a cost and abuse exposure
independent of onboarding.

**Done when:** the documented `30/min · 300/day` direct quota is observable —
`X-RateLimit-Remaining` on a `200`, `429` + `Retry-After` past the cap — and
the `/integrate` limit line can quote a number again.

### OB4 — The full-path stranger test · 0.5 day, no code unless it fails

**Problem:** every previous estimate of onboarding quality was written by
people who already hold keys. The feedback that triggered this plan came
from a stranger.

**Changes:** scripted clean-room test — fresh browser profile, fresh shell,
no keychain, no env: land on `/` from the tweet → scan in browser → follow
to `/integrate` → run the no-key curl → check the verdict against
`GET /pubkey` → mint key → run the keyed scan from OB6 → confirm
`POST /verify` on the miner returns `valid: true` (V6 — there is no web
`/verify` page; do not script against one). Time each step; log every
hesitation point, jargon wall, or dead end. Anything that fails becomes a bug
in OB1/OB3/OB6 scope; anything merely confusing becomes copy work in the same
pass.

**Done when:** median time-to-first-verdict ≤ 60 seconds, time-to-first
*keyed, receipted, verified* call ≤ 5 minutes, zero steps requiring knowledge
the test subject doesn't have. Results recorded in this doc.

### OB5 — Close the loop publicly · 15 minutes, owner action

After OB1–OB3 deploy and OB4 verifies: reply to the person who gave the
feedback — what changed, with the no-key curl inline so anyone can confirm
in seconds. A visible fixed-it loop is worth more than the fix.

**Done when:** the reply is posted.

## Sequencing and dependencies

| Order | Work | Depends on | State |
|---|---|---|---|
| 1 | OB1 no-key-first `/integrate` | nothing — highest leverage | core shipped `f604023`; claims corrected 2026-11-26 |
| 2 | **OB6 keyed `/scan`** | nothing | **next** — unblocks OB3 |
| 3 | OB3 zero-decision minting | OB6 | upstream already defaults to SERV |
| 4 | OB7 limiter actually on | deploy/env check on `api.` | open ops item |
| 5 | OB2 npm decision | owner (publish scope) | not urgent — no reachable reference |
| 6 | OB4 stranger test | OB1+OB3+OB6 deployed | gates OB5 |
| 7 | OB5 close the loop | OB4 green | owner action |

Total: ~2–3 days, mostly frontend/copy plus one small backend route (OB6).
Nothing here blocks or is blocked by WS5 (extension) or the WS4 tail — a
parallel agent can take OB6 or OB7 independently of the `/integrate` copy.

## Explicitly out of scope

- Redesigning x402 onboarding for humans — it's the agent payment rail;
  the human evaluation path is the free scan, full stop.
- Account/email identity systems (WS6c) — key minting stays lightweight and
  anonymous; the fix is ordering, not identity.
- Homepage changes beyond possibly sharing the try-it component — the
  scan-first landing already converts; this plan is the layer beneath it.
