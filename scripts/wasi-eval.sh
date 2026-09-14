#!/usr/bin/env bash
# Build and drive the WASI eval binary under Wasmer — the Wasmer SDK track.
#
#   scripts/wasi-eval.sh build                    compile elcaro_eval_wasi.wasm
#   scripts/wasi-eval.sh corpus                   dump the embedded corpus
#   scripts/wasi-eval.sh self-score [miner-url]   score a live miner end-to-end
#
# self-score does the whole loop *inside* Wasmer: the corpus comes out of the
# wasm, each case is POSTed to the miner's /scan, and the responses go back
# in for scoring. Same artifact the Telegraph validators use, no browser.
#
# Toolchain note: `cargo +<tc>` needs rustup's proxy and this repo has been
# built with a `solana` default that is not installed, so the script resolves
# a toolchain that actually ships wasm32-wasip1 std and calls its binaries
# directly. Override with CARGO=/path/to/cargo.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_DIR="$REPO_ROOT/eval"
TARGET=wasm32-wasip1
BIN=elcaro_eval_wasi
WASM="$EVAL_DIR/target/$TARGET/release/$BIN.wasm"
DEFAULT_MINER="${ELCARO_MINER_URL:-https://api.elcaro.trustfall.xyz}"

die() { echo "wasi-eval: $*" >&2; exit 1; }

# ── toolchain resolution ───────────────────────────────────────────────────────

has_wasi_std() { # $1 = path to a rustc
  local sysroot
  sysroot="$("$1" --print sysroot 2>/dev/null)" || return 1
  [ -d "$sysroot/lib/rustlib/$TARGET/lib" ]
}

resolve_toolchain() {
  if [ -n "${CARGO:-}" ]; then
    CARGO_BIN_DIR="$(dirname "$CARGO")"
    return 0
  fi
  if command -v rustc >/dev/null 2>&1 && has_wasi_std "$(command -v rustc)"; then
    CARGO_BIN_DIR="$(dirname "$(command -v rustc)")"
    return 0
  fi
  local tc
  for tc in "${RUSTUP_HOME:-$HOME/.rustup}"/toolchains/*/bin; do
    [ -x "$tc/rustc" ] || continue
    if has_wasi_std "$tc/rustc"; then
      CARGO_BIN_DIR="$tc"
      return 0
    fi
  done
  die "no toolchain with $TARGET std. Run: rustup target add $TARGET"
}

build() {
  resolve_toolchain
  echo "wasi-eval: toolchain $CARGO_BIN_DIR"
  (
    cd "$EVAL_DIR"
    PATH="$CARGO_BIN_DIR:$PATH" \
    RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-$(basename "$(dirname "$CARGO_BIN_DIR")")}" \
      "$CARGO_BIN_DIR/cargo" build --release --target "$TARGET" --bin "$BIN"
  )
  [ -f "$WASM" ] || die "build produced no $WASM"
  echo "wasi-eval: $WASM ($(wc -c <"$WASM" | tr -d ' ') bytes)"
}

need_wasm() { [ -f "$WASM" ] || build; }

need_wasmer() {
  command -v wasmer >/dev/null 2>&1 ||
    die "wasmer CLI not found. Install: brew install wasmer"
}

# ── commands ───────────────────────────────────────────────────────────────────

cmd_corpus() {
  need_wasm
  need_wasmer
  wasmer run "$WASM" -- --corpus
}

cmd_self_score() {
  local miner="${1:-$DEFAULT_MINER}"
  need_wasm
  need_wasmer

  local work responses
  work="$(mktemp -d)"
  # capture the path now — `work` is local and unbound when EXIT fires
  trap "rm -rf '$work'" EXIT

  echo "wasi-eval: pulling corpus out of the wasm" >&2
  wasmer run "$WASM" -- --corpus >"$work/corpus.json"

  echo "wasi-eval: scanning against $miner" >&2
  MINER_URL="$miner" CORPUS="$work/corpus.json" OUT="$work/responses.json" \
    "${PYTHON:-python3}" - <<'PY'
import json, os, urllib.request

miner = os.environ["MINER_URL"].rstrip("/")
cases = json.load(open(os.environ["CORPUS"]))
responses = []
for c in cases:
    body = json.dumps(
        {"content": c["content"], "content_type": c["content_type"]}
    ).encode()
    req = urllib.request.Request(
        f"{miner}/scan", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    responses.append(
        {
            "risk_score": d["risk_score"],
            "risk_level": d.get("risk_level", ""),
            "flagged_techniques": d.get("flagged_techniques", []),
            "indicators": d.get("indicators", []),
        }
    )
json.dump(responses, open(os.environ["OUT"], "w"))
print(f"wasi-eval: {len(responses)} responses collected", flush=True)
PY

  echo "wasi-eval: scoring inside Wasmer" >&2
  wasmer run "$WASM" <"$work/responses.json" >"$work/result.json"
  cat "$work/result.json"

  "${PYTHON:-python3}" - "$work/result.json" "$miner" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print(
    f"\n{sys.argv[2]}  overall={r['overall_score']:.3f}  "
    f"passed={r['passed_cases']}/{r['total_cases']}  "
    f"TPR={r['true_positive_rate']:.3f} TNR={r['true_negative_rate']:.3f} "
    f"FPR={r['false_positive_rate']:.3f} tech={r['technique_accuracy']:.3f}",
    file=sys.stderr,
)
PY
}

case "${1:-build}" in
  build) build ;;
  corpus) cmd_corpus ;;
  self-score) shift; cmd_self_score "${1:-}" ;;
  *) die "usage: $0 {build|corpus|self-score [miner-url]}" ;;
esac
