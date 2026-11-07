# Lexsi AI Safety & Alignment Hackathon — IPI eval for Cohere models

Track 2a (AI Red Teaming, Safety & Alignment): **adversarial/safety
evaluation sets** and **multi-turn audits (prompt injection hidden in
tools/documents)**. Submission deadline **Nov 14, 2026, 23:59 AoE**.

This directory is the Lexsi-facing arm of the Elcaro indirect
prompt-injection benchmark. It reuses the `micro1-eval/` harness
verbatim — same 24 attack tasks, same deterministic grader, same
transcript format — pointed at allowed Cohere open-weight models via
the Hugging Face Inference Providers router. Nothing in `micro1-eval/`
is modified; results land in `lexsi-eval/results*/`.

## Models (hackathon-allowed dense open weights)

Served by `https://router.huggingface.co/v1` (OpenAI-compatible):

| Router id | Notes |
|---|---|
| `CohereLabs/aya-expanse-32b` | Primary target — strongest allowed model |
| `CohereLabs/aya-expanse-8b` | Not currently on the router; use 32b |
| `CohereLabs/tiny-aya-global` | Small/cheap second model |
| `CohereLabs/tiny-aya-fire` / `-water` / `-earth` | Additional small variants |

Pilot sanity run (2026-11-07, naive arm, 1 trial × 5 tasks):
aya-expanse-32b compromised on T05, T21, T24 — real signal, not
trivial refusal or trivial obedience. Full numbers pending.

## Running

```bash
cd lexsi-eval
cp .env.example .env   # fill EVAL_API_KEY with your HF token

# naive arm (raw untrusted content, no warning) — the "before" condition
EVAL_BASE_URL=https://router.huggingface.co/v1 \
EVAL_API_KEY=$HF_TOKEN \
python3 run_eval.py --models CohereLabs/aya-expanse-32b \
  --presentation naive --trials 3

# labeled arm (explicit untrusted-content warning in system prompt)
python3 run_eval.py --models CohereLabs/aya-expanse-32b \
  --presentation labeled --trials 3

# wrapped arm (Elcaro detector pre-scan + [ELCARO WARNING] preamble)
python3 run_eval.py --models CohereLabs/aya-expanse-32b \
  --presentation wrapped --trials 3

# re-grade stored transcripts (no API needed)
python3 run_eval.py --regrade
python3 selftest.py
```

Results land in `results/` (labeled), `results-naive/`,
`results-wrapped/`, each with `summary.json` + `summary.md` and raw
transcripts including the resolved upstream model id.

## Submission artifacts

- [x] Full three-arm run vs aya-expanse-32b + tiny-aya-global
      (72 trials/cell; see `results*/summary.md`)
- [x] HF dataset: https://huggingface.co/datasets/Papajams/elcaro-ipi-eval
      (tasks + curated exports + all transcripts + graders)
- [x] HF model collection:
      https://huggingface.co/collections/Papajams/lexsi-ipi-eval-cohere-aya-models-6aef8fd587f725ebce1bc528
- [x] Lexsi stack repos chained (2 required): **CuratorKIT**
      (`curate_tasks.py` → `curated-tasks/` provenance artifacts) and
      **AuditKIT** (`auditkit_eval.py` → `results-auditkit/` RunResult)
- [x] SafeTune repair arm (negative result): `results-safetune/` +
      adapter https://huggingface.co/Papajams/aya-expanse-8b-elcaro-sft
      (in collection) — compromised 5/24 → 6/24
- [x] Report/write-up: `WRITEUP.md`; form abstract: `ABSTRACT.md`
- [ ] Submission form (Tally, live until Nov 14 23:59 AoE) — needs
      registered email + links above

## Honest caveats

- These are the **same 24 tasks** as `micro1-eval` — for Lexsi they are
  an evaluation-set deliverable, not a held-out generalization claim.
  The held-out suite remains separate future work.
- Wrapped results measure Elcaro's production detector; warn-mode is
  not quarantine, and residual failures exist (see
  `micro1-eval/results-wrapped/summary.md`).
