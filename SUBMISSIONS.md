# Submission Log — Telegraph Hackathon Season I

> H1 overall close: **Sun 07 Sep 2026 23:59 UTC**.
> Track 1 miner-ID + YAML form: **Wed 02 Sep 2026 11:59:59 UTC**.
> Track 3 (Apps & Agents) is open now — must consume live Telegraph miners.
> X / engagement posts: extended to **2 Sep 2026**.
> Log every submission, iteration, and result here.
>
> The Kiro "Ready, Spec, Ship" hackathon (deadline Aug 23, 2026) is tracked
> separately in [docs/hackathons.md](docs/hackathons.md).

## Key dates

| Date | Event |
|------|-------|
| Aug 17, 2026 | H1 opens — Track 1 (Miners) & Track 2 (Scripts) |
| Aug 31 / Sep 1 | Track 3 (Apps & Agents) is the live build window |
| **Wed 02 Sep 2026 11:59:59 UTC** | **Track 1 form: miner ID(s) + YAML** · X/engagement posts extended to this date |
| **Sun 07 Sep 2026 23:59 UTC** | **H1 submissions close** · evaluation begins |
| TBA | Winners announced |

## Track 1 — Miner (IPI Detection)

| # | Date | What | Miner ID | Intent | Status | Notes |
|---|------|------|----------|--------|--------|-------|
| 1 | 2026-08-20 | Registered on Base Sepolia | `8848` | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` | ❌ Rejected | `registrationId 136` — YAML hash mismatch. Console's IPFS pin re-serialised the file before hashing. See iteration log. |
| 2 | 2026-08-20 | Re-registered, self-hosted YAML | `8848` | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` | ✅ Active | `registrationId 145`, tx [`0x79a908a6...`](https://sepolia.basescan.org/tx/0x79a908a6ac0b45dad82048e25cb148dc3daf8a841510fbef31b4ad5c006f9d3f). Confirmed `activation_status: active` via `devnode.telegraphprotocol.com/api/miners/145`. |
| 3 | 2026-09-01 | YAML: endpoint `intents` + `params.body` so engine routing can select `/scan` | `8848` | same | ⏳ Needs deploy + `updateMiner` then form submit | Catalog listed Elcaro for `CONTENT_MODERATION` but `/scan` declared no `intents`, so auto-routed asks could not select it. Direct 402 calls do not count as miner volume. |

## Track 2 — Eval Script (Adversarial IPI Test Suite)

| # | Date | What | Status | Notes |
|---|------|------|--------|-------|
| 1 | 2026-08-29 | WASM eval script: score miners against IPI corpus | ✅ Done | Rust → `wasm32-unknown-unknown`, 26-case corpus (18 adversarial positives across all six classes + 8 clean negatives), pointer/length host ABI, standalone browser demo (`eval/wasm-demo/`). Verified in-browser against the live miner: **0.672** overall (24/26, TPR 0.889, TNR 1.0, FPR 0.0). |

## Track 3 — App (Agent Content Screener)

Official bar: users & activity, usage, creativity, **must use Telegraph miners**, posts showcasing the project.

| # | Date | What | Status | Notes |
|---|------|------|--------|-------|
| 1 | 2026-08-29 | Middleware demo: agent pre-filters retrieved content | ✅ Product | `app/middleware.py` + [/integrate](https://elcaro.trustfall.xyz/integrate). Direct `POST /scan` — fine as a product, **does not** by itself satisfy “must use Telegraph miners”. |
| 2 | 2026-09-01 | Live Telegraph catalog on /integrate | ⏳ Ship with frontend | `GET /api/telegraph/miners` reads `devnode…/api/miners?intent=CONTENT_MODERATION`. Counted volume still needs auto-routed `/engine/v1/ask` after YAML `updateMiner`. |

## Iteration log

(Record design decisions, test results, and mutations here as we build.)

### 2026-08-20 — Track 1 miner: live HTTPS, then two registration attempts

**Live endpoint.** `https://api.elcaro.trustfall.xyz` fronted by the VPS's
Coolify-managed Traefik (not a host nginx, and not a Cloudflare proxy — DNS is
a plain A record). 18/18 smoke checks pass; `/scan` returns in ~15ms.

**Registration attempt 1 — rejected.** Registered `id 8848` /
`registrationId 136` against a YAML pinned via integrate.telegraphprotocol.com's
own "Import & Upload" wizard. The node rejected it:

> YAML hash mismatch: registered `81a0e5fb...`, fetched `937a0b68...` — the
> document at the registered URL is not the one committed on chain. This will
> NOT be retried.

Cause: the console's wizard **parses and re-serialises** an uploaded YAML
before pinning to IPFS (strips comments, reflows some `description` fields).
Same data, different bytes, different SHA-256. The hash computed from the
*uploaded* file never matches what the node fetches from the *pinned* file.

Confirmed no fix-in-place was possible: `updateMiner` only works on an
*active* registration, and this one was `rejected` (Telegraph support,
Discord, confirmed directly). Separately, the registering wallet was a
passkey-based Base Account with no exportable private key and mobile-only
browser access — `cast --browser` and basescan's "Write Contract" tab both
require an injected browser-extension wallet (MetaMask/etc.), which a Base
Account isn't reachable through. Both would have been dead ends even if
`updateMiner` had been usable.

**Registration attempt 2 — active.** Fix: stopped relying on any third party
to host the YAML. Added `GET /telegraph.yaml` to the miner itself, serving the
exact repo file's raw bytes with no templating/serialisation step — guarded by
a byte-identity test (`tests/test_api.py`) so this class of bug fails CI
instead of failing on-chain. Plain HTTPS is an explicitly supported
registration hosting option, not a workaround (`docs.telegraphprotocol.com` →
`miners/miner-registration.md`, Step 2).

Registered fresh (`id 8848` reused — the rejected registration doesn't reserve
it; confirmed free again before reuse) with `registrationId 145`, a new fee
wallet (deliberately separate from the fourcast miner's wallet), against
`https://api.elcaro.trustfall.xyz/telegraph.yaml` and its live hash
`0x213b88c6...`. Confirmed `activation_status: active`, appears in the public
`/api/miners` catalog with the correct schema, and `/scan` still verified
end-to-end post-registration.

**Takeaway for next registration or update:** always hash the URL the node
will fetch (`curl -s <url> | sha256sum`), never a local file, and don't trust
a console's "we'll pin it for you" step to preserve bytes unless verified.

### 2026-08-29 — Track 2 eval script: WASM build, ABI bug caught by browser test

**Build.** `eval/` compiled clean to `wasm32-unknown-unknown` (156K artifact,
zero warnings, 6/6 native tests). Exports verified programmatically:
`elcaro_alloc`, `elcaro_dealloc`, `evaluate_ptr`, `get_test_cases_ptr`,
`test_case_count` — the pointer/length ABI the validator runtime needs.

**Bug caught by smoke-testing the actual artifact.** A Node round-trip of the
pointer ABI panicked inside the allocator on the first `elcaro_dealloc`.
Root cause: output buffers were handed to the host as `Vec<u8>` memory, but a
`Vec`'s *capacity* can exceed its *length*, while the dealloc contract passes
length as capacity — `Vec::from_raw_parts(ptr, 0, len)` with mismatched
capacity is UB and tripped the allocator's checks. Native tests never caught
it because they only exercised allocations where capacity happened to match.
Fix: both sides of the ABI now use raw `alloc`/`dealloc` with exact-size
`(len, 1)` layouts, so the contract holds unconditionally.

**Live self-score via the browser demo.** `eval/wasm-demo/` runs the module
entirely client-side: pulls the corpus out of the WASM, sends each of the 26
cases to the miner's `/scan` from the page, and scores the responses in WASM.
Against the production miner (`api.elcaro.trustfall.xyz`):

- overall **0.672** — 24/26 cases, TPR 0.889, TNR 1.000, FPR 0.000,
  technique accuracy 0.667
- both misses are obfuscation-class detections (D004 translation indirection,
  D005 token splitting) — a known engine gap, now measurable by anyone from
  a static HTML page

**Takeaway:** never ship a WASM ABI on native tests alone — instantiate the
real artifact and round-trip it. The capacity/length mismatch would have
scored zero silently in a validator.

### 2026-09-01 — Track 1 form deadline is Sep 2; engine routing was a no-op

**Judging rule (Ahmed Ali, Telegraph).** Direct calls — raw HTTPS to the
miner, or `POST /engine/v1/ask/8848` with or without x402 — are not counted
toward miner request volume. Auto-routed `POST /engine/v1/ask` is. An agent
that uses the direct path still counts as an application.

**YAML gap.** `/scan` had a description and top-level `supported_intents`,
but no per-endpoint `intents:` or `params`. The official YAML guide says
routing selects an endpoint by intent, so an endpoint with no `intents`
list is never called. Confirmed on the live catalog: Elcaro is the only
`CONTENT_MODERATION` miner, and `/scan` listed path/method/description
only. Counted engine traffic could not land.

**Fix (repo, not yet live).** `miner/telegraph.yaml` now declares
`intents: [CONTENT_MODERATION, TEXT_CLASSIFICATION]` and `params.body`
(`content` required). Deploying that file without `updateMiner()` will
hash-mismatch and reject the miner. Sequence: deploy →
`scripts/print_update_miner.sh` → `updateMiner` from the registering
wallet → submit miner id `8848` + the live YAML on the Track 1 form
before Wed 02 Sep 2026 11:59:59 UTC.
