#!/bin/bash
# Elcaro Miner — VPS update script
# Run on the VPS as linuxuser: bash deploy/update.sh
#
# Safe update path for the shared Coolify host (see deploy/README.md):
#   1. Record the current commit (rollback anchor)
#   2. git pull
#   3. pip install (locked extras)
#   4. Run the test suite — a failure ABORTS before the restart, so a bad
#      commit never reaches production
#   5. pm2 restart
#   6. Smoke-check /health
#
# Rollback if anything goes wrong after a successful update:
#   git checkout <anchor hash printed below> && pm2 restart elcaro-miner

set -euo pipefail

DEPLOY_DIR="/home/linuxuser/elcaro"
cd "$DEPLOY_DIR"

echo "=== Elcaro Miner Update ==="

# 1. Rollback anchor — the commit currently deployed
PREV_COMMIT=$(git rev-parse --short HEAD)
echo "→ Rollback anchor: $PREV_COMMIT (git checkout $PREV_COMMIT && pm2 restart elcaro-miner)"

# 2. Pull
echo "→ Pulling latest code..."
git pull --ff-only

# Nothing to do if already current
if [ "$(git rev-parse --short HEAD)" = "$PREV_COMMIT" ]; then
    echo "✓ Already up to date ($PREV_COMMIT) — nothing to do."
    exit 0
fi

# 3. Dependencies
echo "→ Installing dependencies..."
.venv/bin/pip install -e ".[miner]" --quiet

# 4. Tests gate the restart — abort BEFORE touching the running process
echo "→ Running test suite (must pass before restart)..."
if ! .venv/bin/python -m pytest tests/ -q --no-header > /tmp/elcaro-update-tests.log 2>&1; then
    echo "✗ Tests FAILED — aborting update. Running miner untouched."
    echo "  Test log: /tmp/elcaro-update-tests.log (tail below)"
    tail -20 /tmp/elcaro-update-tests.log
    echo "→ Repo is at the new commit but the process still runs old code."
    echo "  Fix forward, or roll back: git checkout $PREV_COMMIT"
    exit 1
fi
echo "✓ Tests pass ($(grep -oE '[0-9]+ passed' /tmp/elcaro-update-tests.log | tail -1))"

# 5. Restart
echo "→ Restarting elcaro-miner..."
pm2 restart elcaro-miner

# 6. Smoke check — the process must come back healthy
sleep 3
RESPONSE=$(curl -s --max-time 10 http://127.0.0.1:8848/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo "✓ Health check passed"
else
    echo "✗ Health check FAILED after restart: $RESPONSE"
    echo "→ Roll back now: git checkout $PREV_COMMIT && pm2 restart elcaro-miner"
    exit 1
fi

echo ""
echo "=== Update complete: $PREV_COMMIT → $(git rev-parse --short HEAD) ==="
echo "Full verification: BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh"
