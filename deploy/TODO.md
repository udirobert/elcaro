# Deployment TODO — go live + register on Telegraph

> Goal: get the Elcaro miner **live and registered on the Telegraph Protocol**
> before Track 1 & 2 close **Sep 7, 2026**. Registration happens at
> <https://integrate.telegraphprotocol.com> (web3 wallet required — do the final
> "Register Now → Connect API" step yourself in the browser).

## Step 1 — Live HTTPS endpoint ✅ DONE (Aug 20, 2026)

`https://api.elcaro.trustfall.xyz/health` returns HTTP 200 with a valid Let's
Encrypt cert (valid to Nov 18 2026). `/scan` verified end-to-end:
`risk_score 1.0`, `latency_ms 14`. Full suite: **18/18 passed**.

The original CDN-proxy / host-nginx plan did **not** apply to this host. What was
actually true:

- The VPS is **Coolify-managed**; `coolify-proxy` (Traefik v3.6) owns :80/:443.
- Host nginx is **not running** (`nginx.service` = `failed`), so every vhost in
  `/etc/nginx/sites-enabled/` was inert — including the old elcaro one on :8847.
  That is why the port was refused, and why probing the origin directly hit an
  invalid cert.
- A host-level certbot/nginx on :443 would have **failed to bind** and risked the
  shared ingress for every other project on the host. That plan was dropped.
- DNS was already correct: `api.elcaro` A → the VPS, exactly like the other
  working services on the box. No DNS change was needed.

What changed (all additive, all reversible, nothing shared touched):

- [x] `deploy/ecosystem.config.cjs` — uvicorn rebound `127.0.0.1` → `0.0.0.0`
      so the Traefik container can reach it via `host.docker.internal`
- [x] `ufw allow from 10.0.0.0/8 to any port 8848 proto tcp` — reachable from the
      Docker bridges only, never the public internet
- [x] New Traefik dynamic route from `deploy/traefik-elcaro.yaml` — picked up
      live via file-watch; cert issued over HTTP-01
- [x] `pm2 save` so the new bind survives a reboot
- [x] Confirmed neighbouring services on the shared host unaffected

Rollback steps and host specifics: `docs/ops.md` (local only, gitignored).

## Step 2 — Frontend (Cloudflare Pages)

> The frontend target is **Cloudflare Pages**. Note that
> `elcaro.trustfall.xyz` does **not** resolve yet — a subdomain still has to be
> created and attached to the Pages project.

- [ ] Create `elcaro.trustfall.xyz` at the registrar → CNAME to the Pages project
- [ ] Add it as a custom domain on the Cloudflare Pages project
- [ ] Set `ELCARO_MINER_URL=https://api.elcaro.trustfall.xyz` in Pages env vars
- [ ] Full E2E: `bash deploy/verify-live.sh`

## Step 3 — Register the miner on Telegraph ✅ DONE (Aug 20, 2026)

**Registered and active.** `registrationId: 145`, on-chain tx
[`0x79a908a6...c006f9d3f`](https://sepolia.basescan.org/tx/0x79a908a6ac0b45dad82048e25cb148dc3daf8a841510fbef31b4ad5c006f9d3f),
confirmed via `devnode.telegraphprotocol.com/api/miners/145`:
`"activation_status":"active"`, `"rejection_reason":null`. Appears in the public
catalog (`/api/miners`) with the correct schema, endpoint, and intents.

The upload artifact is **`miner/telegraph.yaml`**, but it is registered by URL,
**not** by uploading through the console. `miner/config.yaml` is the internal
capability reference, not the submission.

### The first attempt failed — here's why, for next time

A first registration (`id 8848`, `registrationId 136`) was rejected on-chain.
The node's own error: *"YAML hash mismatch: registered 81a0e5fb...,
fetched 937a0b68... — the document at the registered URL is not the one
committed on chain. This will NOT be retried."*

Root cause: **integrate.telegraphprotocol.com's "Import & Upload" step
re-serialises an uploaded YAML before pinning it to IPFS** — strips comments,
reflows some fields. The re-serialised bytes are semantically identical but
hash differently, so a hash computed from the local file never matches what the
node fetches from the pinned URL.

There is no `updateMiner` path for a `rejected` (never-activated) registration
— Telegraph support confirmed only an active registration can be updated; a
rejected one needs a fresh `registerMiner` call. Separately, the registering
wallet was a passkey-based Base Account with no exportable key and mobile-only
access, so `cast --browser` and basescan's Write Contract tab (both need an
injected browser-extension wallet) weren't usable to fix it even if update had
been possible.

**Fix:** self-host the exact file over plain HTTPS instead of letting the
console pin it — HTTPS is an explicitly supported hosting option, equal footing
with IPFS (`docs.telegraphprotocol.com` → `miners/miner-registration.md`,
Step 2). `GET /telegraph.yaml` on the miner now serves the repo file's raw
bytes with no templating step, guarded by a byte-identity test in
`tests/test_api.py` so this class of bug fails CI instead of failing on-chain.

**The lesson for any future update:** always compute the registration hash
from the URL the node will actually fetch, never from a local file —
```bash
curl -s https://api.elcaro.trustfall.xyz/telegraph.yaml | sha256sum
```
— and never let a third-party console "pin for you" without confirming the
pinned bytes hash identically to what you uploaded.

### Registered values

| Field | Value |
|---|---|
| YAML URL | `https://api.elcaro.trustfall.xyz/telegraph.yaml` |
| YAML Hash | `0x213b88c646efd4d39bddaa16b3adb93402dff3ba9cd8215affa73c8f1e5adb8e` |
| Miner `id` | `8848` |
| `registrationId` | `145` |
| Intents | `CONTENT_MODERATION`, `TEXT_CLASSIFICATION` |
| Floor price | `0.01` USDC |
| Fee/registering wallet | `0x1e17B4FB12B29045b29475f74E536Db97Ddc5D40` (fresh — separate from the fourcast miner's wallet, deliberately) |

- [ ] Set your contact in `miner/config.yaml` → `miner.contact` (it becomes public) — still outstanding, not required for the registration itself
- [ ] Copy the registry contract into `miner/config.yaml` → `registration.registry_contract` = `0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8`

### After registering

- **7-day grace period**: no leaderboard position and no score yet — runs until
  ~Aug 27, 2026.
- **Routing is 70/20/10** by rank within an Intent. `CONTENT_MODERATION` had
  **0 other miners** at registration time, so Elcaro should default to rank 1
  once scoring starts.

## Daily operations

See `deploy/README.md` (pm2 logs/restart/update, metrics).
