# Deployment

> Host-specific detail (IP, SSH alias, exact paths, neighbouring services) lives
> in `docs/ops.md`, which is gitignored. This file stays generic on purpose.

## Architecture

The miner runs on a **Coolify-managed VPS**. Coolify's `coolify-proxy` container
(Traefik v3.6) is the only process bound to public :80/:443 and terminates TLS
for every domain on the host via Let's Encrypt. Host-level nginx is **not** part
of the serving path — the `nginx.service` unit is in a `failed` state and nothing
on the host binds :80/:443.

```
┌──────────┐        ┌──────────────────────────────────────────────┐
│  Browser │───────▶│  VPS                                         │
└──────────┘ HTTPS  │  ┌────────────────────────────────────────┐  │
             :443   │  │ coolify-proxy (Traefik v3.6)           │  │
                    │  │  • owns :80 / :443                     │  │
                    │  │  • Let's Encrypt HTTP-01 (acme.json)   │  │
                    │  │  • file provider: /traefik/dynamic/    │  │
                    │  └───────────────┬────────────────────────┘  │
                    │                  │ host.docker.internal      │
                    │                  │ :8848                     │
                    │                  ▼                           │
                    │        uvicorn (PM2: elcaro-miner)           │
                    │        binds 0.0.0.0:8848                    │
                    │        ufw: 8848 open to Docker bridges only  │
                    └──────────────────────────────────────────────┘
```

DNS is a plain A-record at the registrar pointing straight at the VPS. No CDN
proxy is involved, and none is needed: Traefik terminates TLS at the origin.

## Frontend (Netlify)

`netlify.toml` at the repo root is the source of truth for this — base
directory `app/web`, build command `npm run build`, publish `app/web/.next`,
via `@netlify/plugin-nextjs`.

1. Connect the GitHub repo to Netlify (New site from Git)
2. It reads `netlify.toml` automatically — no manual build settings needed
3. Site settings → Environment variables → add
   `ELCARO_MINER_URL` = `https://api.elcaro.trustfall.xyz`
4. Site settings → Domain management → add custom domain: `elcaro.trustfall.xyz`

**Live since Aug 21, 2026:** the site serves at
[elcaro.trustfall.xyz](https://elcaro.trustfall.xyz) via a CNAME to
`elcaro.netlify.app` (registrar DNS at GoDaddy) with an automatically
provisioned Let's Encrypt certificate. Full suite `deploy/verify-live.sh`
passes 21/21 including the frontend proxy checks.

## Miner API (VPS)

> ⚠️ **This is a shared host.** It runs many unrelated projects (dozens of
> containers and PM2 processes). Do **not** install a host-level nginx/certbot on
> it, and do **not** touch other projects' files in the Traefik dynamic config
> directory — Traefik reads that whole directory, and every other domain's
> routing lives there. See `docs/ops.md`.

### Exposing the miner (the established pattern on this host)

Three pieces, mirroring how the other host-run apps on the box are wired:

1. **Bind the app so Traefik can reach it.** uvicorn must listen on `0.0.0.0`,
   not `127.0.0.1` — Traefik runs in a container and cannot reach host loopback;
   it connects via `host.docker.internal`. Set in `ecosystem.config.cjs`.

2. **Keep it private with ufw.** The port is bound broadly but firewalled to the
   Docker bridge networks, so it is unreachable from the internet:

   ```bash
   sudo ufw allow from 10.0.0.0/8 to any port 8848 proto tcp \
     comment "elcaro-miner from Docker/Traefik"
   ```

3. **Add a Traefik route.** Install `deploy/traefik-elcaro.yaml` into Coolify's
   Traefik dynamic directory as `elcaro.yaml` (root:root 0644). Traefik runs with
   `--providers.file.watch=true`, so it is picked up live — no proxy restart, no
   impact on other projects. Exact path and command: `docs/ops.md`.

Traefik then requests the Let's Encrypt cert automatically over HTTP-01 and
stores it in the shared `acme.json`.

### Exposing the Gateway (Phase 2)

`gateway.elcaro.trustfall.xyz` mirrors the miner pattern on port **8849** —
the `elcaro-gateway` PM2 app in `ecosystem.config.cjs` already binds
`0.0.0.0:8849` (uvicorn `gateway.app:app`). To bring it live:

1. **DNS**: A record `gateway.elcaro.trustfall.xyz` → VPS public IP.
2. **ufw**:

   ```bash
   sudo ufw allow from 10.0.0.0/8 to any port 8849 proto tcp \
     comment "elcaro-gateway from Docker/Traefik"
   ```

3. **Traefik**: install `deploy/traefik-elcaro-gateway.yaml` into the dynamic
   dir as `elcaro-gateway.yaml` — a *new* file, alongside `elcaro.yaml`,
   touching nothing else.
4. **Env**: the gateway reads `ELCARO_SIGNING_KEY`, `ELCARO_METERING_DSN`,
   `ELCARO_GATEWAY_PRICE_USDC` and `ELCARO_UPSTREAM_<NAME>_URL` from the same
   `~/elcaro/.env` the ecosystem file already loads.
5. **Boot**: `pm2 startOrRestart deploy/ecosystem.config.cjs && pm2 save`,
   then `GATEWAY_URL=https://gateway.elcaro.trustfall.xyz bash deploy/verify-live.sh`
   — the gateway checks assert `/health` and that keyless/bogus-key chat
   requests fail closed (401).

Note: until Dev B's `gateway/` package merges, the `elcaro-gateway` PM2 app
has no code to run — it crash-loops briefly then idles (max_restarts=10);
`pm2 delete elcaro-gateway` silences it if deployed early.

### Prerequisites

Python 3.12 and PM2 are already installed on the VPS.

### Deploy the app itself

```bash
cd ~/elcaro && git pull
pm2 start deploy/ecosystem.config.cjs && pm2 save
```

`pm2 save` matters: without it a reboot restores the old bind address.

### Environment variables

`deploy/ecosystem.config.cjs` loads `~/elcaro/.env` itself (plain
`KEY=value` lines, `export` prefixes and quotes tolerated) and merges it
into the app's env, so the file on the VPS is the single place secrets
live — gitignored, mode `600`. The committed `env` block wins on a key
conflict: it declares the deployment contract (e.g. `SERV_ENABLED=1`),
`.env` carries secrets (`SERV_API_KEY`, `ELCARO_SIGNING_KEY`,
`ELCARO_CANARY_DSN`, …) plus any var the block does not set.

Two pm2 gotchas this file is written around:

- `pm2 restart elcaro-miner` reuses the env frozen in pm2's dump and does
  **not** re-evaluate the ecosystem file. To apply env/config changes use
  `pm2 startOrRestart deploy/ecosystem.config.cjs` — `update.sh` does.
- After any `startOrRestart`, `pm2 save` so `pm2 resurrect` restores the
  new env, not the stale dump.

### SERV in production (Phase 0.1)

The miner advertises a SERV Reasoning second pass; it is armed by config,
not by code changes:

1. Put `SERV_API_KEY=<openserv key>` in `~/elcaro/.env` (console.openserv.ai;
   `SERV_ENABLED`/`SERV_MODEL` are already committed in the ecosystem file).
2. `pm2 startOrRestart deploy/ecosystem.config.cjs && pm2 save`
3. `BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh`
   — the SERV checks assert `serv_available: true` on `/config` and a live
   `serv_used` verdict on a gray-zone `?serv=1` scan. They fail loudly on a
   silent rules fallback.

### Update an existing deployment

```bash
bash deploy/update.sh
```

One command: records a rollback anchor, pulls, reinstalls deps, runs the test
suite (a failure aborts **before** the restart, so a bad commit never reaches
production), restarts, and smoke-checks `/health`. Rollback is printed at the
top of every run: `git checkout <anchor> && pm2 restart elcaro-miner`.

### Ports

| Port | Bound to | Exposure |
|---|---|---|
| 443 | `coolify-proxy` (Traefik) | Public — terminates TLS for all domains |
| 80 | `coolify-proxy` (Traefik) | Public — ACME HTTP-01 + redirect to 443 |
| 8848 | uvicorn (`0.0.0.0`) | Private — ufw restricts to Docker bridges |

### Do not use these on this host

| File | Why |
|---|---|
| `nginx.conf` | Assumes a CDN proxy → origin port 8847. Host nginx is not running and Traefik owns 443. Kept only for a future non-Coolify host. |
| `setup.sh` (nginx steps) | Installs a host nginx vhost; inert here at best, conflicting at worst. |

### Verify a deployment

`deploy/verify-live.sh` runs an 18-check smoke suite against a live miner
(health, metadata, dangerous/clean/system_prompt payloads, `/v1/infer` alias,
validation errors, metrics) plus frontend proxy checks:

```bash
# Miner only (frontend not yet deployed):
BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh

# Full end-to-end once Netlify has ELCARO_MINER_URL set:
bash deploy/verify-live.sh
```

### Daily operations

```bash
# View logs
pm2 logs elcaro-miner

# Restart
pm2 restart elcaro-miner

# Update code + restart (test-gated, with rollback anchor)
bash deploy/update.sh

# Check metrics
curl http://127.0.0.1:8848/metrics

# Status
pm2 show elcaro-miner
```

### Files

| File | Purpose |
|---|---|
| `ecosystem.config.cjs` | PM2 process config — binds `0.0.0.0:8848`, restart policy, memory limit |
| `traefik-elcaro.yaml` | **Live ingress.** Install into Coolify's Traefik dynamic dir as `elcaro.yaml` |
| `update.sh` | **Update path.** Test-gated deploy with rollback anchor and health smoke check |
| `verify-live.sh` | Post-deploy smoke suite (18 checks, miner + frontend proxy) |
| `pin-config.py` | Pins `miner/config.yaml` to IPFS via Pinata, returns the CID — not used for `miner/telegraph.yaml`, which is self-hosted instead (see `SUBMISSIONS.md`) |
| `nginx.conf` | Legacy CDN-proxy model — **not used on this host** |

Uptime monitoring: `.github/workflows/uptime.yml` polls the miner `/health` and
the frontend every 15 minutes and fails the workflow on 2 consecutive misses
(GitHub emails workflow-failure notifications to repo watchers).

Frontend build config lives at the repo root: `netlify.toml`.

Operational runbook, rollback steps, and host specifics: `docs/ops.md` (local only).
