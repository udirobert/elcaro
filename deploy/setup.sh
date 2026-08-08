#!/bin/bash
# Elcaro Miner — VPS deployment script
# Run on a fresh Ubuntu/Debian VPS with: bash deploy/setup.sh
#
# Prerequisites:
#   - Domain pointing to VPS IP (for Caddy HTTPS)
#   - SSH access as root or sudo user
#
# This script:
#   1. Creates a deploy user
#   2. Installs Python 3.12, Caddy, and git
#   3. Clones the repo
#   4. Sets up the virtualenv and installs deps
#   5. Installs the systemd service and Caddy config
#   6. Starts everything

set -euo pipefail

DOMAIN="${1:-api.elcaro.dev}"
REPO="https://github.com/udirobert/elcaro.git"
DEPLOY_DIR="/opt/elcaro"
DEPLOY_USER="deploy"

echo "=== Elcaro Miner Deployment ==="
echo "Domain: $DOMAIN"
echo ""

# ── System packages ────────────────────────────────────────────────────────────

echo "→ Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3-pip git curl

# ── Caddy ──────────────────────────────────────────────────────────────────────

if ! command -v caddy &> /dev/null; then
    echo "→ Installing Caddy..."
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
fi

# ── Deploy user ────────────────────────────────────────────────────────────────

if ! id "$DEPLOY_USER" &>/dev/null; then
    echo "→ Creating deploy user..."
    useradd -r -m -s /bin/bash "$DEPLOY_USER"
fi

# ── Clone / pull repo ──────────────────────────────────────────────────────────

if [ -d "$DEPLOY_DIR" ]; then
    echo "→ Pulling latest..."
    cd "$DEPLOY_DIR"
    git pull --ff-only
else
    echo "→ Cloning repo..."
    git clone "$REPO" "$DEPLOY_DIR"
fi

chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

# ── Python environment ─────────────────────────────────────────────────────────

echo "→ Setting up Python environment..."
cd "$DEPLOY_DIR"
sudo -u "$DEPLOY_USER" python3.12 -m venv .venv
sudo -u "$DEPLOY_USER" .venv/bin/pip install -e ".[miner]" --quiet

# ── Systemd service ────────────────────────────────────────────────────────────

echo "→ Installing systemd service..."
cp deploy/elcaro-miner.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable elcaro-miner
systemctl restart elcaro-miner

# Wait for it to start
sleep 2
if systemctl is-active --quiet elcaro-miner; then
    echo "✓ Miner service running"
else
    echo "✗ Miner service failed to start — check: journalctl -u elcaro-miner"
    exit 1
fi

# ── Caddy config ──────────────────────────────────────────────────────────────

echo "→ Configuring Caddy for $DOMAIN..."
# Replace domain in Caddyfile
sed "s/api.elcaro.dev/$DOMAIN/g" deploy/Caddyfile > /etc/caddy/Caddyfile
mkdir -p /var/log/caddy

systemctl restart caddy

sleep 3
if systemctl is-active --quiet caddy; then
    echo "✓ Caddy running — HTTPS will be provisioned automatically"
else
    echo "✗ Caddy failed — check: journalctl -u caddy"
    exit 1
fi

# ── Verify ─────────────────────────────────────────────────────────────────────

echo ""
echo "=== Deployment complete ==="
echo ""
echo "  Miner API:  https://$DOMAIN"
echo "  Health:     https://$DOMAIN/health"
echo "  Metrics:    https://$DOMAIN/metrics"
echo ""
echo "  Logs:       journalctl -u elcaro-miner -f"
echo "  Restart:    sudo systemctl restart elcaro-miner"
echo "  Update:     cd /opt/elcaro && git pull && sudo systemctl restart elcaro-miner"
echo ""
echo "  Next steps:"
echo "  1. Verify: curl https://$DOMAIN/health"
echo "  2. Set ELCARO_MINER_URL=https://$DOMAIN in Netlify environment variables"
echo "  3. Trigger a Netlify redeploy"
