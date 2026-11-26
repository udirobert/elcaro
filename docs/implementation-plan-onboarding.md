# Implementation plan — onboarding inversion

> **Date:** 2026-11-26 · **Trigger:** first public response to the Dolphin
> quote-tweet: improve onboarding · **Status:** draft, nothing started
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

## Principles

1. **Value before commitment, strictly ordered.** Nobody is asked to create,
   install, decide, or pay anything before they have seen a verdict.
2. **Every step in the docs must be runnable.** A command that fails is worse
   than no command. Each step is tested exactly as written, in a clean shell.
3. **Decisions deferred, not removed.** Upstream choice, payment, and keys
   all still exist — they appear at the moment the user has a reason to care.
4. **No new claims.** This plan rearranges true things; it does not add any.

## Workstreams

### OB1 — No-key-first rewrite of `/integrate` · ~1 day

**Problem:** the page leads with key minting. The no-key curl is the product's
best first minute and it's missing.

**Changes:**

1. New first section: **"30 seconds, nothing to create"** — the verified
   no-key scan curl, pre-filled with the authority-spoofing injection example
   (the same specimen the scan-form examples and the launch video use), so
   the first output a new user sees is `DANGEROUS` on input that *looks*
   innocent. Include the expected output inline so success is recognizable.
2. Progressive disclosure after that: "want this inside your agent's retrieval
   path?" → key minting (OB3) → gateway drop-in. Each step framed as optional
   deepening, not prerequisite.
3. The free-scan curl must state its own limits honestly in one line
   (rate-limited, shared quota — per WS0c) so heavy users understand why keys
   exist. This converts the limit into the upsell, same model as the 429.
4. Remove or demote any instruction that cannot be run as written (see OB2).

**Files:** `app/web/src/app/integrate/page.tsx`, possibly extracting a
`try-it` component shared with the homepage scan section.

**Done when:** in a clean shell, copy-pasting the first command produces a
`DANGEROUS` verdict in under 30 seconds with no account, key, install, or
editing of the command. Timed on a cold machine/browser profile.

### OB2 — Resolve the npm ghost · 0.5–1 day, decision first

**Problem:** `@elcaro/sdk` is a 404 landmine. Two honest resolutions:

- **Option A — publish.** `sdk/js` is `0.1.0`, tests pass 11/11, builds clean
  (verified during the launch work). Publishing is mostly npm logistics
  (scope access, CI or manual first publish, provenance). Then the SDK
  snippets become runnable, and `/integrate` can offer npm OR curl.
- **Option B — scrub.** Remove/rewrite every reference so nobody is sent to
  the 404; keep the SDK as repo-local or git-installable only.

**Recommendation: A** — the package already passes its tests, the audience is
npm-native, and the quote-tweet is sending traffic now. If scope/permissions
block publishing this week, fall back to B immediately rather than leaving
the landmine in place.

**Done when:** `npm i @elcaro/sdk` succeeds on a clean machine AND the
installed package's quickstart produces a verdict — or (B) no reachable doc,
page, or README mentions the package name.

### OB3 — Zero-decision key minting · 0.5–1 day

**Problem:** minting a key forces the upstream choice before the user has
any basis for it.

**Changes:**

1. Default upstream pre-selected (SERV — cheapest, and the OpenServ audience
   already holds keys), choice moved behind "advanced".
2. One-line plain-language consequence text: "this is which AI your scanned
   traffic is forwarded to — you can mint more keys later."
3. Post-mint screen becomes a *continuation*, not a dead end: shows the key
   once (as today) plus the exact next command with the key already
   interpolated — copy one line, run it, see a signed verdict. This is the
   moment the integration path and the no-key path converge.

**Files:** `app/web/src/app/keys/page.tsx` + key-mint components.

**Done when:** minting requires zero choices (one click), and the post-mint
screen contains a copy-paste command that — run as-is — returns a verdict
with receipt headers. Verified in a clean browser profile.

### OB4 — The full-path stranger test · 0.5 day, no code unless it fails

**Problem:** every previous estimate of onboarding quality was written by
people who already hold keys. The feedback that triggered this plan came
from a stranger.

**Changes:** scripted clean-room test — fresh browser profile, fresh shell,
no keychain, no env: land on `/` from the tweet → scan in browser → follow
to `/integrate` → run the no-key curl → mint key → run the keyed gateway
call → verify the receipt at `/verify`. Time each step; log every hesitation
point, jargon wall, or dead end. Anything that fails becomes a bug in OB1–OB3
scope; anything merely confusing becomes copy work in the same pass.

**Done when:** median time-to-first-verdict ≤ 60 seconds, time-to-first
*keyed, receipted* call ≤ 5 minutes, zero steps requiring knowledge the test
subject doesn't have. Results recorded in this doc.

### OB5 — Close the loop publicly · 15 minutes, owner action

After OB1–OB3 deploy and OB4 verifies: reply to the person who gave the
feedback — what changed, with the no-key curl inline so anyone can confirm
in seconds. A visible fixed-it loop is worth more than the fix.

**Done when:** the reply is posted.

## Sequencing and dependencies

| Order | Work | Depends on |
|---|---|---|
| 1 | OB1 no-key-first `/integrate` | nothing — highest leverage, start now |
| 2 | OB2 npm decision + execution | owner decision on publish access |
| 3 | OB3 zero-decision minting | nothing, parallel with OB1/OB2 |
| 4 | OB4 stranger test | OB1+OB3 deployed; OB2 if publish chosen |
| 5 | OB5 close the loop | OB4 green |

Total: ~2–3 days of work, mostly frontend/copy, no new infrastructure.
Nothing here blocks or is blocked by WS5 (extension) or the WS4 tail — a
parallel agent can take this whole plan independently.

## Explicitly out of scope

- Redesigning x402 onboarding for humans — it's the agent payment rail;
  the human evaluation path is the free scan, full stop.
- Account/email identity systems (WS6c) — key minting stays lightweight and
  anonymous; the fix is ordering, not identity.
- Homepage changes beyond possibly sharing the try-it component — the
  scan-first landing already converts; this plan is the layer beneath it.
