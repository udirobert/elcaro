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

## Frontend (Cloudflare Pages)

The frontend is on **Cloudflare Pages**, not Netlify.

1. Project → Build → Root directory: `app/web`
2. Custom domain: `elcaro.trustfall.xyz`
3. Environment variable: `ELCARO_MINER_URL` = `https://api.elcaro.trustfall.xyz`

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

### Prerequisites

Python 3.12 and PM2 are already installed on the VPS.

### Deploy the app itself

```bash
cd ~/elcaro && git pull
pm2 start deploy/ecosystem.config.cjs && pm2 save
```

`pm2 save` matters: without it a reboot restores the old bind address.

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
# Miner only (frontend not yet published):
BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh

# Full end-to-end once Cloudflare Pages has ELCARO_MINER_URL set:
bash deploy/verify-live.sh
```

### Daily operations

```bash
# View logs
pm2 logs elcaro-miner

# Restart
pm2 restart elcaro-miner

# Update code + restart
cd ~/elcaro && git pull && .venv/bin/pip install -e ".[miner]" -q && pm2 restart elcaro-miner

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
| `verify-live.sh` | Post-deploy smoke suite (18 checks, miner + frontend proxy) |
| `pin-config.py` | Pins `miner/config.yaml` to IPFS via Pinata, returns the CID |
| `nginx.conf` | Legacy CDN-proxy model — **not used on this host** |
| `setup.sh` | Legacy one-shot deploy — nginx steps **not used on this host** |

Operational runbook, rollback steps, and host specifics: `docs/ops.md` (local only).
