#!/bin/bash
# Elcaro Miner — VPS deployment script
# Run on the VPS as linuxuser: bash deploy/setup.sh
#
# This VPS uses: nginx (reverse proxy) + PM2 (process manager) + Cloudflare (HTTPS)
#
# This script:
#   1. Sets up the Python virtualenv
#   2. Installs the nginx config
#   3. Starts the miner via PM2
#
# Prerequisites:
#   - Repo cloned to /home/linuxuser/elcaro
#   - Python 3.12, nginx, and PM2 already installed
#   - Cloudflare DNS configured for your domain → VPS IP (proxy enabled, port 8847)

set -euo pipefail

DEPLOY_DIR="/home/linuxuser/elcaro"
DOMAIN="${1:-api.elcaro.trustfall.xyz}"
NGINX_PORT="8847"
APP_PORT="8848"

echo "=== Elcaro Miner Deployment ==="
echo "Domain:     $DOMAIN"
echo "Nginx port: $NGINX_PORT (Cloudflare connects here)"
echo "App port:   $APP_PORT (uvicorn binds here)"
echo ""

cd "$DEPLOY_DIR"

# ── Python environment ─────────────────────────────────────────────────────────

echo "→ Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi
.venv/bin/pip install -e ".[miner]" --quiet
echo "✓ Python deps installed"

# ── Verify the engine works ────────────────────────────────────────────────────

echo "→ Running quick smoke test..."
.venv/bin/python -m pytest tests/ -q --no-header 2>/dev/null && echo "✓ Tests pass" || echo "⚠ Tests failed (continuing anyway)"

# ── nginx config ───────────────────────────────────────────────────────────────

echo "→ Installing nginx config..."
NGINX_CONF="/etc/nginx/sites-available/elcaro"

# Replace domain in config
sed "s/api.elcaro.trustfall.xyz/$DOMAIN/g" deploy/nginx.conf | sudo tee "$NGINX_CONF" > /dev/null

# Enable site
if [ ! -L "/etc/nginx/sites-enabled/elcaro" ]; then
    sudo ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/elcaro
fi

# Test and reload
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo "✓ nginx configured and reloaded"
else
    echo "✗ nginx config test failed — check: sudo nginx -t"
    exit 1
fi

# ── PM2 ────────────────────────────────────────────────────────────────────────

echo "→ Starting miner via PM2..."

# Stop existing instance if running
pm2 delete elcaro-miner 2>/dev/null || true

# Start fresh
pm2 start deploy/ecosystem.config.cjs
pm2 save

# Wait and verify
sleep 2
if pm2 show elcaro-miner | grep -q "online"; then
    echo "✓ Miner running on port $APP_PORT"
else
    echo "✗ Miner failed to start — check: pm2 logs elcaro-miner"
    exit 1
fi

# ── Verify ─────────────────────────────────────────────────────────────────────

echo ""
echo "→ Testing endpoint..."
RESPONSE=$(curl -s http://127.0.0.1:$APP_PORT/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo "✓ Health check passed: $RESPONSE"
else
    echo "✗ Health check failed: $RESPONSE"
    exit 1
fi

echo ""
echo "=== Deployment complete ==="
echo ""
echo "  Local:    http://127.0.0.1:$APP_PORT"
echo "  Nginx:    http://$(hostname -I | awk '{print $1}'):$NGINX_PORT"
echo "  Public:   https://$DOMAIN (via Cloudflare)"
echo ""
echo "  Health:   curl https://$DOMAIN/health"
echo "  Metrics:  curl https://$DOMAIN/metrics"
echo "  Scan:     curl -X POST https://$DOMAIN/scan -H 'Content-Type: application/json' -d '{\"content\": \"SYSTEM: test\", \"content_type\": \"email\"}'"
echo ""
echo "  Logs:     pm2 logs elcaro-miner"
echo "  Restart:  pm2 restart elcaro-miner"
echo "  Update:   cd $DEPLOY_DIR && git pull && .venv/bin/pip install -e '.[miner]' -q && pm2 restart elcaro-miner"
echo ""
echo "  Next steps:"
echo "  1. Ensure Cloudflare DNS A record for $DOMAIN → $(hostname -I | awk '{print $1}') (proxied, port $NGINX_PORT)"
echo "  2. Set ELCARO_MINER_URL=https://$DOMAIN in Netlify environment variables"
echo "  3. Trigger a Netlify redeploy"
