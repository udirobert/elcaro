# Submission Log — Telegraph Hackathon Season I

> Track 1 & 2 open Aug 17, 2026. Track 3 opens after T1/T2 close (~Aug 31).
> Log every submission, iteration, and result here.
>
> The Kiro "Ready, Spec, Ship" hackathon (deadline Aug 23, 2026) is tracked
> separately in [docs/hackathons.md](docs/hackathons.md).

## Key dates

| Date | Event |
|------|-------|
| Aug 17, 2026 12:00 UTC | Track 1 (Miners) & Track 2 (Scripts) open |
| Aug 31, 2026 | Track 3 (Apps) opens |
| Sep 7, 2026 | Track 1 & 2 close; evaluation begins |
| TBA | Winners announced |

## Track 1 — Miner (IPI Detection)

| # | Date | What | Miner ID | Intent | Status | Notes |
|---|------|------|----------|--------|--------|-------|
| 1 | 2026-08-20 | Registered on Base Sepolia | `8848` | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` | ❌ Rejected | `registrationId 136` — YAML hash mismatch. Console's IPFS pin re-serialised the file before hashing. See iteration log. |
| 2 | 2026-08-20 | Re-registered, self-hosted YAML | `8848` | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` | ✅ Active | `registrationId 145`, tx [`0x79a908a6...`](https://sepolia.basescan.org/tx/0x79a908a6ac0b45dad82048e25cb148dc3daf8a841510fbef31b4ad5c006f9d3f). Confirmed `activation_status: active` via `devnode.telegraphprotocol.com/api/miners/145`. |

## Track 2 — Eval Script (Adversarial IPI Test Suite)

| # | Date | What | Status | Notes |
|---|------|------|--------|-------|
| — | — | WASM eval script: score miners against IPI corpus | TODO | Rust → wasm32-unknown-unknown |

## Track 3 — App (Agent Content Screener)

| # | Date | What | Status | Notes |
|---|------|------|--------|-------|
| — | 2026-08-29 | Middleware demo: agent pre-filters retrieved content | ✅ Done | `app/middleware.py` + interactive walkthrough on [/integrate](https://elcaro.trustfall.xyz/integrate); replace/block/warn quarantine modes, signed verdicts, session-watch supervision |

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
