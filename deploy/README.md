# Deployment

## Architecture

```
┌─────────────┐         ┌──────────────────┐
│   Netlify   │ ──────▶ │      VPS         │
│  (Next.js)  │  proxy  │  (Python miner)  │
│  app/web/   │         │  miner/api.py    │
└─────────────┘         └──────────────────┘
```

## Frontend (Netlify)

The GitHub repo is connected directly to Netlify. Every push to `main` triggers
a deploy automatically.

**Required setup (one-time in Netlify dashboard):**
1. Site settings → Build → Base directory: `app/web`
2. Site settings → Environment variables → Add:
   - `ELCARO_MINER_URL` = `https://your-domain.com` (your VPS URL)

## Miner API (VPS)

### Quick deploy

SSH into your VPS as root and run:

```bash
curl -fsSL https://raw.githubusercontent.com/udirobert/elcaro/main/deploy/setup.sh | bash -s your-domain.com
```

Or clone and run manually:

```bash
git clone https://github.com/udirobert/elcaro.git /opt/elcaro
cd /opt/elcaro
bash deploy/setup.sh your-domain.com
```

### What the script does

1. Installs Python 3.12, Caddy, git
2. Creates a `deploy` user (non-root, hardened)
3. Clones the repo to `/opt/elcaro`
4. Creates a virtualenv and installs dependencies
5. Installs and starts the systemd service
6. Configures Caddy as reverse proxy with automatic HTTPS

### Manual management

```bash
# View logs
journalctl -u elcaro-miner -f

# Restart after a code change
cd /opt/elcaro && git pull && sudo systemctl restart elcaro-miner

# Check status
systemctl status elcaro-miner
curl https://your-domain.com/health
curl https://your-domain.com/metrics
```

### Files

| File | Purpose |
|---|---|
| `elcaro-miner.service` | systemd unit — runs uvicorn, auto-restarts, security-hardened |
| `Caddyfile` | Reverse proxy config — automatic HTTPS, security headers, logging |
| `setup.sh` | One-shot deployment script for a fresh VPS |

### Requirements

- Ubuntu 22.04+ or Debian 12+
- Domain with DNS A record pointing to the VPS IP
- Ports 80 and 443 open (for Caddy/HTTPS)
- ~256MB RAM minimum
