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

The upload artifact is **`miner/telegraph.yaml`**. `miner/config.yaml` is the
internal capability reference, not the submission.

Schema reference: <https://docs.telegraphprotocol.com> → `miners/yaml-config.md`.

### How Telegraph actually calls a miner

Telegraph is a **passthrough proxy**, not an envelope protocol. `base_url` +
`endpoints[].external_path` are forwarded the caller's body verbatim, and the
miner's raw output is returned as `result`. So the flat `/scan` contract is what
gets registered — there is no `{intent, params}` wrapper to implement.

- Auto-routed: `POST /engine/v1/ask {query, context}` — an LLM router classifies
  the query to an Intent, picks a miner, and builds the body. `input_schema` is
  documentation that guides it; the node does **not** enforce it.
- Direct: `POST /engine/v1/ask/{id} {method, endpoint, payload}` — `payload`
  becomes the request body.

### Pre-registration checks (registration is on-chain and cannot be edited)

1. [ ] **`id` must be globally unused** — requests route on it; a clash is rejected.
     `8848` was free when checked. Re-verify:
     ```bash
     curl -s https://devnode.telegraphprotocol.com/api/miners \
       | python3 -c "import json,sys;print(sorted(int(m['id']) for m in json.load(sys.stdin) if str(m['id']).isdigit()))"
     ```
2. [ ] **Intents must be canonical** or `registerMiner` **reverts**. Declared:
     `CONTENT_MODERATION` + `TEXT_CLASSIFICATION`, both verified canonical.
     There is no `INJECTION_DETECTION` intent on the network. Re-verify:
     ```bash
     curl -s https://devnode.telegraphprotocol.com/engine/v1/intents
     ```
3. [ ] **`min_price_usdc` is immutable** after registration — changing it means
     deregister + re-register. Currently `0.01`.
4. [ ] Set your contact in `miner/config.yaml` → `miner.contact` (it becomes public)

### Register

5. [ ] Validate + register at <https://integrate.telegraphprotocol.com>. Paste the
     YAML; it sandbox-tests every declared endpoint against the live upstream,
     reports pass/fail per endpoint, then pins and registers for you.
6. [ ] Sign the registration on **Base Sepolia** with the wallet that will hold
     the slug — only that wallet can ever update it
7. [ ] Copy the registry contract into `miner/config.yaml` → `registration.registry_contract`
8. [ ] Log the submission + CID in `SUBMISSIONS.md`

Optional manual pin (the console pins for you): `PINATA_JWT=... python deploy/pin-config.py miner/telegraph.yaml`

### After registering

- **7-day grace period**: no leaderboard position and no score yet.
- **Routing is 70/20/10** by rank within an Intent, so being ranked first in
  `CONTENT_MODERATION` (currently **0 other miners**) captures the majority of
  that intent's routed traffic.

## Daily operations

See `deploy/README.md` (pm2 logs/restart/update, metrics).
