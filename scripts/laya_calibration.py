"""Calibrate Laya's injection probabilities against Elcaro's labelled corpus.

Convai/Runware's launch note is explicit: constrained output stops the model
inventing an option but "doesn't prevent errors in judgment … check
calibration on your own data before letting a probability control any
consequential action." Elcaro never lets Laya control the verdict (it's a
comparison rail only), but we still want to know how good the signal is before
promoting it in the UI or the Discord post.

This script sends every case in ``eval/corpus.json`` to the live Laya model as
the same Noul question the engine uses, then reports, against the corpus
labels:

  - accuracy / TPR / TNR / FPR at a 0.5 threshold
  - a threshold sweep (0.3 … 0.7) so you can see where Laya separates best
  - Brier score (mean squared error of the probability) — the calibration
    number that matters for a probabilistic signal
  - mean latency and total input tokens (cost during/after the free window)

It writes nothing and changes no state. Requires a real key — there is no
offline mode, because the whole point is measuring the real model.

Usage:
    LAYA_ENABLED=1 RUNWARE_API_KEY=... python scripts/laya_calibration.py
    # or LAYA_API_KEY=...; optional LAYA_MODEL / LAYA_BASE_URL overrides

Exit code is non-zero if Laya is not configured or every call failed, so it
can gate a "Laya is calibrated" claim in CI or a release check.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from core.laya_reasoner import LayaReasoner

CORPUS = Path(__file__).resolve().parent.parent / "eval" / "corpus.json"


def main() -> int:
    reasoner = LayaReasoner.from_env()
    if reasoner is None:
        print(
            "Laya is not configured. Set LAYA_ENABLED=1 and RUNWARE_API_KEY "
            "(or LAYA_API_KEY), then re-run.",
            file=sys.stderr,
        )
        return 2

    cases = json.loads(CORPUS.read_text())
    rows: list[tuple[str, bool, float, int | None, float]] = []
    failures = 0

    for c in cases:
        content = c["content"]
        content_type = c["content_type"]
        is_injection = bool(c["is_injection"])
        t0 = time.monotonic()
        result = reasoner.classify(content, content_type, [], rule_score=0.5)
        latency_ms = (time.monotonic() - t0) * 1000
        if not result.ok:
            failures += 1
            print(f"  {c['id']:<6} FAILED (no answer)")
            continue
        rows.append((c["id"], is_injection, result.laya_score, result.input_tokens, latency_ms))
        print(
            f"  {c['id']:<6} label={'INJ ' if is_injection else 'clean'} "
            f"P(inj)={result.laya_score:.3f} {latency_ms:6.1f}ms"
        )

    if not rows:
        print("\nEvery Laya call failed — nothing to calibrate.", file=sys.stderr)
        return 1

    pos = [r for r in rows if r[1]]
    neg = [r for r in rows if not r[1]]

    def rate_at(threshold: float) -> tuple[float, float, float, float]:
        tp = sum(1 for r in pos if r[2] >= threshold)
        tn = sum(1 for r in neg if r[2] < threshold)
        acc = (tp + tn) / len(rows)
        tpr = tp / len(pos) if pos else float("nan")
        tnr = tn / len(neg) if neg else float("nan")
        fpr = 1.0 - tnr if neg else float("nan")
        return acc, tpr, tnr, fpr

    # Brier score: mean (p - label)^2. Lower is better; 0.25 is a coin flip.
    brier = sum((r[2] - (1.0 if r[1] else 0.0)) ** 2 for r in rows) / len(rows)
    tokens = [r[3] for r in rows if isinstance(r[3], int)]
    mean_latency = sum(r[4] for r in rows) / len(rows)

    print(
        f"\nScored {len(rows)}/{len(cases)} cases ({failures} failed), "
        f"{len(pos)} injection / {len(neg)} clean."
    )
    print(f"Brier score: {brier:.4f}  (0 = perfect, 0.25 = uninformative)")
    print(f"Mean latency: {mean_latency:.1f} ms")
    if tokens:
        total = sum(tokens)
        print(f"Total input tokens: {total}  (~${total * 0.02 / 1_000_000:.6f} at $0.02/MTok)")

    print("\nthreshold  accuracy  TPR     TNR     FPR")
    for th in (0.3, 0.4, 0.5, 0.6, 0.7):
        acc, tpr, tnr, fpr = rate_at(th)
        print(f"  {th:.2f}      {acc:.3f}     {tpr:.3f}   {tnr:.3f}   {fpr:.3f}")

    print(
        "\nReminder: Laya is a comparison rail only — these numbers decide "
        "whether to surface it, never whether to trust it over the rules."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
