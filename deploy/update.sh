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
#   5. pm2 startOrRestart — re-reads deploy/ecosystem.config.cjs, so env/config
#      changes in the file take effect (a plain `pm2 restart` would keep the
#      env frozen in pm2's dump)
#   6. Smoke-check /health
#
# Rollback if anything goes wrong after a successful update:
#   git checkout <anchor hash printed below> && pm2 restart elcaro-miner

set -euo pipefail

DEPLOY_DIR="/home/linuxuser/elcaro"
cd "$DEPLOY_DIR"

echo "=== Elcaro Miner Update ==="

# 1. Rollback anchor — the commit currently deployed. Carried through the
#    hand-off below so a re-exec still reports the real anchor.
PREV_COMMIT="${ELCARO_ROLLBACK_ANCHOR:-$(git rev-parse --short HEAD)}"
echo "→ Rollback anchor: $PREV_COMMIT (git checkout $PREV_COMMIT && pm2 restart elcaro-miner)"

# 2. Pull
echo "→ Pulling latest code..."
git pull --ff-only

# 2b. `git pull` can rewrite this very file while bash is reading it. The
#     interpreter keeps its byte offset into a file whose contents just
#     shifted, so it resumes in the middle of the new script instead of the
#     old one — observed as the script exiting 7 with the post-restart health
#     check and everything after it silently skipped. Hand off to the pulled
#     copy instead of pretending to keep running the old one.
if [ "${ELCARO_UPDATE_FRESH:-0}" != "1" ] \
    && [ -n "$(git diff --name-only "$PREV_COMMIT" HEAD -- deploy/update.sh || true)" ]; then
    echo "→ This script changed in the pulled commit — re-executing the new one"
    cp deploy/update.sh /tmp/elcaro-update-fresh.sh
    ELCARO_UPDATE_FRESH=1 ELCARO_ROLLBACK_ANCHOR="$PREV_COMMIT" exec bash /tmp/elcaro-update-fresh.sh
fi

# Nothing to do if already current
if [ "$(git rev-parse --short HEAD)" = "$PREV_COMMIT" ]; then
    echo "✓ Already up to date ($PREV_COMMIT) — nothing to do."
    exit 0
fi

# 3. Dependencies
echo "→ Installing dependencies..."
.venv/bin/pip install -e ".[miner,gateway]" --quiet

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

# 5. Restart — startOrRestart re-evaluates the ecosystem file (env included);
#    a bare `pm2 restart elcaro-miner` would keep the env from pm2's dump.
echo "→ Restarting elcaro-miner..."
pm2 startOrRestart deploy/ecosystem.config.cjs

# 6. Smoke check — the process must come back healthy. Retry, and swallow
#    curl's own failure: a bare `RESPONSE=$(curl ...)` under `set -e` aborts
#    the script when the port is not yet bound (curl exit 7), which skipped
#    this assertion and everything after it — including the quota read-back
#    below. That is how a restart could "succeed" while both checks stayed
#    unrun.
RESPONSE=""
for attempt in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    RESPONSE=$(curl -s --max-time 5 http://127.0.0.1:8848/health || true)
    if echo "$RESPONSE" | grep -q "healthy"; then
        echo "✓ Health check passed (attempt $attempt)"
        break
    fi
done
if ! echo "$RESPONSE" | grep -q "healthy"; then
    echo "✗ Health check FAILED after restart: ${RESPONSE:-<no response from :8848>}"
    echo "→ Roll back now: git checkout $PREV_COMMIT && pm2 restart elcaro-miner"
    exit 1
fi

echo ""
echo "=== Update complete: $PREV_COMMIT → $(git rev-parse --short HEAD) ==="

# 7. Quota arming is part of the contract, and it is the one thing a restart can
#    silently undo: `pm2 restart` reuses the env frozen in pm2's dump, so limits
#    added to the ecosystem file stay dead until a startOrRestart. The free-scan
#    quota once ran idle in production for exactly that reason. Read it back
#    from the process itself rather than trusting the file.
QUOTA=$(curl -s -D - -o /dev/null --max-time 10 -X POST http://127.0.0.1:8848/scan \
    -H "Content-Type: application/json" \
    -d '{"content": "deploy probe", "content_type": "email"}' 2>/dev/null \
    | awk 'tolower($1)=="x-ratelimit-limit:" {print $2}' | tr -d '\r') || QUOTA=""
if [ -n "$QUOTA" ]; then
    echo "✓ Anonymous scan quota armed (x-ratelimit-limit: $QUOTA)"
else
    echo "⚠ No x-ratelimit-limit header — the free-scan limiter is NOT armed."
    echo "  The process is running without ELCARO_*_RATE_LIMIT_*, which means its"
    echo "  env predates ecosystem.config.cjs. Re-run 'pm2 startOrRestart"
    echo "  deploy/ecosystem.config.cjs', then assert it: bash deploy/verify-live.sh"
fi
echo "Full verification: BASE_URL=https://api.elcaro.trustfall.xyz SKIP_FRONTEND=1 bash deploy/verify-live.sh"
