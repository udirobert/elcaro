"""Calibrate JEV-27B-VL's injection probabilities against the labelled corpus.

JEV-27B-VL (AutoTrust, via Novita) is a comparison rail only — Elcaro never
lets it control the verdict — but we still want to know how good the signal
is before promoting it in the UI or the Discord post. Novita's constrained
``decide`` output stops the model inventing an option; it does not prevent
errors in judgment, so check calibration on your own data before trusting a
probability anywhere consequential.

This script sends every case in ``eval/corpus.json`` to the live JEV-27B-VL
model as the same single Noul question the engine uses, then reports, against
the corpus labels:

  - accuracy / TPR / TNR / FPR at a 0.5 threshold
  - a threshold sweep (0.3 … 0.7) so you can see where JEV-VL separates best
  - Brier score (mean squared error of the probability) — the calibration
    number that matters for a probabilistic signal
  - mean latency and total input tokens (the only billed unit on this API)

It writes nothing and changes no state. Requires a real key — there is no
offline mode, because the whole point is measuring the real model.

Usage:
    JEV_VL_ENABLED=1 NOVITA_API_KEY=... python scripts/jev_vl_calibration.py
    # or JEV_VL_API_KEY=...; optional JEV_VL_MODEL / JEV_VL_BASE_URL overrides

Exit code is non-zero if JEV-VL is not configured or every call failed, so
it can gate a "JEV-VL is calibrated" claim in CI or a release check.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from core.jev_vl_reasoner import JevVlReasoner

CORPUS = Path(__file__).resolve().parent.parent / "eval" / "corpus.json"


def main() -> int:
    reasoner = JevVlReasoner.from_env()
    if reasoner is None:
        print(
            "JEV-VL is not configured. Set JEV_VL_ENABLED=1 and NOVITA_API_KEY "
            "(or JEV_VL_API_KEY), then re-run.",
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
        rows.append((c["id"], is_injection, result.jev_vl_score, result.input_tokens, latency_ms))
        print(
            f"  {c['id']:<6} label={'INJ ' if is_injection else 'clean'} "
            f"P(inj)={result.jev_vl_score:.3f} {latency_ms:6.1f}ms"
        )

    if not rows:
        print("\nEvery JEV-VL call failed — nothing to calibrate.", file=sys.stderr)
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
        print(
            f"Total input tokens: {total}  "
            "(the only billed unit; cost depends on JEV_VL_INPUT_PRICE_PER_M)"
        )

    print("\nthreshold  accuracy  TPR     TNR     FPR")
    for th in (0.3, 0.4, 0.5, 0.6, 0.7):
        acc, tpr, tnr, fpr = rate_at(th)
        print(f"  {th:.2f}      {acc:.3f}     {tpr:.3f}   {tnr:.3f}   {fpr:.3f}")

    print(
        "\nReminder: JEV-VL is a comparison rail only — these numbers decide "
        "whether to surface it, never whether to trust it over the rules."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
