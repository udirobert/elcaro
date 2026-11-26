# Implementation plan — onboarding inversion

> **Date:** 2026-11-26 · **Trigger:** first public response to the Dolphin
> quote-tweet: improve onboarding · **Status:** OB1 core shipped (`f604023`),
> then corrected the same day by a review pass — see
> [Verification log](#verification-log--2026-11-26-review-pass-after-f604023).
> OB1, OB3, OB6 and OB7 are shipped and verified live — OB7's cause was a stale
> pm2 env, not missing code. What remains is **OB4/OB5** (the stranger test and
> the public reply) and the deferred OB2 npm decision.
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

### OB6 — Make a key do something on the surface the stranger just used · **shipped and verified live**

**Problem (V4):** the ladder's second rung was empty. `elk_` was accepted only
by the gateway, which additionally demands the caller's own upstream
credential, so minting a key bought nothing a first-time user could execute
without editing a command.

**Shipped:** `/scan` and `/v1/infer` now honour `x-elcaro-key`.

- Keys resolve through the same Neon store the gateway uses
  (`metering.from_env()`, `ELCARO_METERING_DSN` or `ELCARO_CANARY_DSN`). Only
  the *key store* is installed on the miner — the usage sink stays with the
  gateway, so scan traffic is metered once, where it is charged. Note the cost
  of that: `NeonMetering` validates eagerly, so the miner process now holds a
  small pool (`min_size=1 · max_size=4`) and runs the key DDL at boot. An
  unreachable store degrades to `503 key_service_unavailable`, never to a
  silent anonymous downgrade.
- A keyed call spends `ELCARO_KEYED_SCAN_RATE_LIMIT_*` (committed:
  `120/min · 5000/day`, vs `30/min · 300/day` anonymous) from its own window,
  keyed by `key_id` — never the raw secret.
- A `200` echoes `X-RateLimit-Limit` / `X-RateLimit-Remaining`, so "your own
  quota" is one `curl -i` away. A `429` returns `keyed_scan_rate_limited`
  with no x402 upsell — a keyed caller already has an account.
- Unknown key → `401 unknown_key`; no DSN configured →
  `503 key_service_unavailable`; no keyed quota configured (dev/offline) →
  falls through to the anonymous bucket, **never** to unlimited access.
- `rate_limited_keyed_scans` added to `/metrics`.

**Post-deploy verification — run 2026-11-26 against production, all green:**

1. Keyed scan (a key minted at `/keys`, then revoked): `200` with
   `x-ratelimit-limit: 5000` and `remaining` counting down `4999 → 4998`
   across `/scan` and `/v1/infer`. The done-when is met: same curl as the
   first-run call, one extra header, own quota.
2. `elk_bogus_key_check` → `401 unknown_key`.
3. Anonymous scan → `200`, no `X-RateLimit-*` (the free boundary is unchanged).
4. Deploy path: `deploy/update.sh` on the VPS, rollback anchor `35c60c2`,
   tests gated the restart and passed, `/health` healthy after
   `pm2 startOrRestart`.

**Still deliberately unsaid on `/integrate`:** the keyed quota is not
advertised, and when it is, it should read "your own quota, visible on every
response" rather than repeating `5000/day` — a number ops can change should not
become a page claim (V2's lesson). The post-mint command itself is OB3.

### OB3 — Zero-decision key minting · **shipped and verified live**

**Problem:** minting exposed the upstream choice before the user had seen a
verdict, and the post-mint screen dead-ended at "copy it now".

**Shipped (`key-manager.tsx`, `/integrate` path 00):**

1. The upstream `<select>` moved behind a collapsed **"Advanced — which
   provider this key routes to"** disclosure. The mint row is now label +
   button; SERV stays selected and untouched.
2. The provider explanation lives inside that disclosure, where it is wanted:
   it only describes gateway routing, and says the scan API takes the key
   alone.
3. The post-mint screen is a continuation, not a dead end: the key, then the
   *same* curl with `-H "x-elcaro-key: …"` already interpolated (copy button
   included) and the specimen that returns `dangerous`. Nothing to edit.
4. `/integrate` path 00 now names the header and the consequence — own quota,
   `X-RateLimit-*` on the response — and says the gateway on path 01
   additionally wants your own provider credential.
5. No limit number is published anywhere: the quota is observable on every
   response instead of frozen into copy (V2's lesson).

**Verified 2026-11-26, after the OB6 miner deploy:** a key minted at `/keys`,
the post-mint command pasted unedited → `dangerous` / risk 1.00 with
`x-ratelimit-limit: 5000`, `remaining: 4999`. Key revoked afterwards; the same
command then returns `401 unknown_key`.

**Not verified:** a human typing it in a fresh browser profile — that is OB4.

### OB7 — Turn the scan rate limiter back on · **fixed and verified live**

**Root cause (not what the plan guessed).** The limiter was never broken:
`ELCARO_DIRECT_SCAN_RATE_LIMIT_*` was committed in `deploy/ecosystem.config.cjs`
and the code was correct. The running process was started with
`pm2 restart elcaro-miner`, which **reuses the env frozen in pm2's dump** and
never re-reads the ecosystem file — the exact gotcha `deploy/README.md:179`
warns about. So the process had no limit env, `direct_scan_rate_limiter_from_env()`
returned `None`, and an unauthenticated endpoint ran unlimited while the config
file said `30/min · 300/day`. Limiter init was *not* failing open, and the DSN
was not the problem.

**Fixed:** the OB6 deploy used `deploy/update.sh`, whose
`pm2 startOrRestart` re-reads the file. Measured after it:

- 31st scan in a window → `429` with `retry-after`, `x-ratelimit-limit: 30`,
  `x-ratelimit-remaining: 0` and the x402 upsell body
- `/metrics` `rate_limited_scans` incremented (`0 → 10` across a burst)
- buckets are per caller IP (Traefik's right-most `X-Forwarded-For`), so one
  host's burst cannot throttle anyone else

**Guards so it cannot go quiet again** — the real defect was that nothing
noticed:

1. `X-RateLimit-Limit` / `-Remaining` now ride **every** scan response, keyed
   or anonymous, so an idle limiter shows up as missing headers on a `200`
   instead of as a wall that never arrives.
2. `deploy/verify-live.sh` check `8b` bursts until it sees a `429`, then
   asserts the header and `Retry-After`. It fails when a deployment is running
   a stale env. `SKIP_QUOTA_CHECK=1` for local runs, where limits are off.
3. `deploy/update.sh` reads the quota back from the restarted process and
   prints either `✓ Anonymous scan quota armed (x-ratelimit-limit: N)` or a
   warning naming the stale-dump cause.

**Found while fixing it — the deploy script was lying too.** `update.sh` ends
with a post-restart health check, and that check had not been running: `RESPONSE=$(curl …)`
under `set -euo pipefail` aborts the script when the port is not yet bound
(curl exit 7), so every deploy exited 7 *after* restarting the miner, skipping
the health assertion, the summary line and anything added after them. The root
cause was nastier: `git pull` rewrites `deploy/update.sh` while bash is reading
it, and the interpreter keeps its byte offset into content that just shifted.
Fixed in three passes — retry the health probe and swallow curl's own failure;
then (having learned the hand-off itself lived in the rewritten file) re-exec
from an immutable `/tmp` copy before touching git, and hand off to the pulled
version with the pre-deploy commit carried as `ELCARO_ROLLBACK_ANCHOR`. First
clean run: `anchor 135bf06 → b6ed1e4`, `✓ Health check passed (attempt 3)`,
`✓ Anonymous scan quota armed (x-ratelimit-limit: 300)`, exit 0. The mechanism
was tested in a scratch repo (a v1 script pulling a v2 script) before it
touched production.

**Done when (met):** the documented quota is observable — `X-RateLimit-*` on a
`200`, `429` + `Retry-After` past the cap — and `verify-live.sh` asserts it.
Verified: **27 passed, 0 failed**, including the three new quota assertions.

**Deliberate non-change:** `/integrate` still does not quote a number. "Each
response tells you what's left" is true whatever ops sets the limit to; `30/min`
is not (V2's lesson, applied twice).

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
| 2 | OB6 keyed `/scan` | nothing | **shipped + verified live 2026-11-26** |
| 3 | OB3 zero-decision minting | OB6 ✅ live | **shipped + verified live 2026-11-26** |
| 4 | OB7 limiter actually on | stale pm2 env, cleared by the OB6 deploy | **fixed + guarded 2026-11-26** |
| 5 | OB2 npm decision | owner (publish scope) | not urgent — no reachable reference |
| 6 | **OB4 stranger test** | OB1+OB3+OB6 deployed | **next** — gates OB5 |
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
