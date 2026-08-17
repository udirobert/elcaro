# Deployment

## Architecture

```
┌──────────┐       ┌────────────┐       ┌────────────────────┐
│  Browser │──────▶│ Cloudflare │──────▶│       VPS          │
│          │ HTTPS │  (proxy)   │ :8847 │  nginx → :8848     │
└──────────┘       └────────────┘       │  (uvicorn/PM2)     │
                                        └────────────────────┘
┌──────────┐
│ Netlify  │  (frontend calls /api/scan which proxies to the VPS)
│ Next.js  │
└──────────┘
```

## Frontend (Netlify)

GitHub repo is connected directly to Netlify. Every push to `main` auto-deploys.

**Required setup (one-time in Netlify dashboard):**
1. Site settings → Build → Base directory: `app/web`
2. Site settings → Domain management → Add custom domain: `elcaro.trustfall.xyz`
3. Site settings → Environment variables:
   - `ELCARO_MINER_URL` = `https://api.elcaro.trustfall.xyz`

## Miner API (VPS)

### Prerequisites

Your VPS already has: Python 3.12, nginx, PM2, Cloudflare DNS.

### Deploy

```bash
# SSH in as linuxuser
ssh your-vps

# Clone (first time)
git clone https://github.com/udirobert/elcaro.git ~/elcaro
cd ~/elcaro

# Deploy
bash deploy/setup.sh your-domain.com
```

### What the script does

1. Creates a Python virtualenv and installs deps
2. Runs a quick smoke test (pytest)
3. Installs nginx server block (port 8847 → proxy to 8848)
4. Starts uvicorn via PM2 on port 8848
5. Verifies the health endpoint

### Ports

| Port | Bound to | Purpose |
|---|---|---|
| 8847 | nginx (public-facing) | Cloudflare connects here |
| 8848 | uvicorn (localhost only) | The actual miner process |

### Cloudflare setup

1. DNS → Add A record: `api.elcaro.trustfall.xyz` → `144.202.117.160` (VPS IP)
2. Proxy status: **Proxied** (orange cloud)
3. SSL/TLS → Origin Rules → set origin port to `8847` for this hostname
   (or use a Cloudflare Workers route if needed)

### Netlify DNS (for frontend)

1. DNS → Add CNAME record: `elcaro.trustfall.xyz` → your Netlify site URL (e.g. `your-site.netlify.app`)
2. Proxy status: **DNS only** (grey cloud) — Netlify handles its own HTTPS

### Verify a deployment

`deploy/verify-live.sh` runs an 18-check smoke suite against a live miner
(health, metadata, dangerous/clean/system_prompt payloads, `/v1/infer` alias,
validation errors, metrics) plus frontend proxy checks through Netlify:

```bash
# After Cloudflare DNS is live, but before Netlify is wired:
BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh

# Full end-to-end check once the frontend env var + domain are set:
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
| `ecosystem.config.cjs` | PM2 process config — port, env, restart policy, memory limit |
| `nginx.conf` | nginx server block — reverse proxy with WebSocket support |
| `setup.sh` | One-shot deploy script |
| `verify-live.sh` | Post-deploy smoke suite (18 checks, miner + frontend proxy) |
