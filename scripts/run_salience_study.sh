#!/usr/bin/env sh
# Warn-mode salience study (R11) — one command for the full decision-rule run.
#
# Requires ELCARO_LLM_API_KEY in the environment (see .env.example). Runs the
# experiment against N models x R repeats — the decision rule in
# docs/warn-salience-experiment.md calls for >= 3 models x >= 3 runs each
# (>= 27 completions per position). Results land in eval/results/ as JSON,
# one file per model.
#
# Usage:
#   ELCARO_LLM_API_KEY=... ./scripts/run_salience_study.sh
#   MODELS="gpt-4o-mini" REPEATS=3 ELCARO_LLM_API_KEY=... ./scripts/run_salience_study.sh

set -eu

: "${ELCARO_LLM_API_KEY:?Set ELCARO_LLM_API_KEY (see .env.example)}"
MODELS="${MODELS:-gpt-4o-mini gpt-4.1-mini gpt-4.1-nano}"
REPEATS="${REPEATS:-3}"
OUT_DIR="eval/results"

mkdir -p "$OUT_DIR"

for model in $MODELS; do
  echo "=== $model ($REPEATS repeats, 9 cases each) ==="
  ELCARO_LLM_MODEL="$model" python scripts/warn_salience_experiment.py --run \
    --repeat "$REPEATS" > "$OUT_DIR/salience-$model.json"
  grep -E '^(prefix|suffix|sandwich)' "$OUT_DIR/salience-$model.json" 2>/dev/null || true
done

echo
echo "Raw results: $OUT_DIR/salience-<model>.json"
echo "Decision rule: docs/warn-salience-experiment.md — act if the median"
echo "followed-rate differs by position by >= 25 percentage points."
