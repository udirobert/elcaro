#!/usr/bin/env python3
"""AuditKIT-backed evaluation of the IPI task corpus (Lexsi Track 2a).

Runs the same 24 tasks and the same naive presentation as run_eval.py,
but orchestrates generation through Lexsi-Labs/AuditKIT: a custom
Adapter emits the identical [system, user] message list, the ``api:``
backend calls CohereLabs/aya-expanse-32b on the HF Inference Providers
router, and AuditKIT scores utility metrics (chrf, rouge_l) against the
reference responses.

After the AuditKIT run, each generated output is additionally graded
with this repo's deterministic compromise grader (grade.py) — the same
grader used for every other arm — so ASR/pass numbers stay comparable
across micro1-eval and lexsi-eval.

Requires:  lexsi-eval/.venv  (pip install auditkit)
Env:       HF_TOKEN or ~/.cache/huggingface/token

Usage:
  .venv/bin/python auditkit_eval.py --model CohereLabs/aya-expanse-32b \
      --presentation naive --out results-auditkit/naive.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import auditkit as ak  # noqa: E402
from auditkit.adapter import Adapter, Request  # noqa: E402
from auditkit.model.api_gen import APIModel  # noqa: E402
from grade import grade, load_task  # noqa: E402
from run_eval import build_messages  # noqa: E402

TASKS_DIR = HERE / "tasks"
HF_BASE = "https://router.huggingface.co/v1"


class IpiAdapter(Adapter):
    """Emit the exact message list run_eval.py builds for a presentation."""

    method = "ipi_agentic"

    def __init__(self, presentation: str = "naive"):
        self.presentation = presentation
        self.method = f"ipi_{presentation}"

    def identity(self) -> dict:
        return {"method": self.method}

    def adapt(self, sample: ak.Sample, config) -> list[Request]:
        task = sample.metadata["task"]
        messages = build_messages(task, self.presentation)
        return [
            Request(
                prompt=messages[-1]["content"],
                params={"messages": messages},
            )
        ]


def hf_token() -> str:
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if tok:
        return tok
    cache = Path.home() / ".cache" / "huggingface" / "token"
    if cache.exists():
        return cache.read_text().strip()
    raise SystemExit("no HF token: set HF_TOKEN or log in via `hf auth login`")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="CohereLabs/aya-expanse-32b")
    ap.add_argument("--presentation", default="naive", choices=["naive", "labeled", "wrapped"])
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--scorers", default="chrf,rouge_l")
    ap.add_argument("--tasks", default=None, help="comma-separated task ids, e.g. T01,T05")
    args = ap.parse_args()

    tasks = sorted(TASKS_DIR.glob("T*.json"))
    if args.tasks:
        wanted = {t.strip() for t in args.tasks.split(",")}
        tasks = [p for p in tasks if p.stem in wanted]
    samples = []
    for _ in range(args.trials):
        for p in tasks:
            task = json.loads(p.read_text())
            samples.append(
                ak.Sample(
                    input=task["user_prefix"],
                    target=task.get("reference_response", ""),
                    id=f"{task['id']}-t{_ + 1}",
                    task=task.get("domain", "agentic_ipi"),
                    metadata={"task": task, "trial": _ + 1},
                )
            )

    model = APIModel(
        model=args.model,
        api_base=HF_BASE,
        api_key=hf_token(),
        name="hf-router",
    )
    scorers = [s.strip() for s in args.scorers.split(",") if s.strip()]
    adapter = IpiAdapter(args.presentation)

    result = ak.evaluate(samples, model, scorers, adapter=adapter)
    print(result.summary())

    # Post-hoc deterministic grading with the repo grader. AuditKIT
    # Predictions carry sample_id ("<TASK>-t<N>") and raw_output; map back
    # to the task file for grade().
    graded = []
    for pred in result.samples:
        task_id = pred.sample_id.rsplit("-t", 1)[0]
        trial = int(pred.sample_id.rsplit("-t", 1)[1])
        task = load_task(TASKS_DIR / f"{task_id}.json")
        g = grade(task, pred.raw_output or "")
        graded.append(
            {
                "id": pred.sample_id,
                "task_id": task_id,
                "trial": trial,
                "pass": g.get("pass"),
                "useful": g.get("useful"),
                "compromised": g.get("compromised"),
                "detected": g.get("injection_detected"),
            }
        )

    out = {
        "model": args.model,
        "presentation": args.presentation,
        "auditkit_run": result.to_dict() if hasattr(result, "to_dict") else None,
        "graded": graded,
    }
    out_path = (
        Path(args.out)
        if args.out
        else (
            HERE / "results-auditkit" / f"{args.presentation}-{args.model.replace('/', '_')}.json"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
