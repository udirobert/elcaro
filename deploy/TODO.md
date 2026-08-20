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

## Step 3 — Register the miner on Telegraph

The upload artifact is **`miner/telegraph.yaml`** (Telegraph's own config format).
`miner/config.yaml` is the internal capability reference, not the submission.

1. [ ] Fill in the two console-dependent fields in `miner/telegraph.yaml`:
     - `id` — assigned by the Developer Console (confirm global vs per-account)
     - `protocol` — pick the value matching a direct HTTPS JSON API
2. [ ] Set your contact in `miner/config.yaml` → `miner.contact`
3. [ ] Pin the Telegraph config to IPFS:
     ```bash
     PINATA_JWT=... python deploy/pin-config.py miner/telegraph.yaml
     ```
4. [ ] Paste the returned CID into `miner/config.yaml` → `registration.ipfs_hash`, then commit
5. [ ] At <https://integrate.telegraphprotocol.com> → **Register Now / Connect API**:
     - [ ] Upload `miner/telegraph.yaml` (or paste `ipfs://<CID>`)
     - [ ] Endpoint URL: `https://api.elcaro.trustfall.xyz/query`
     - [ ] Intents: `INJECTION_DETECTION`, `CONTENT_SAFETY_SCAN`
     - [ ] Sign + register on **Base Sepolia** with your wallet
6. [ ] Copy the registry contract from the dashboard into `miner/config.yaml` → `registration.registry_contract`
7. [ ] Log the submission + CID in `SUBMISSIONS.md`

## Daily operations

See `deploy/README.md` (pm2 logs/restart/update, metrics).
