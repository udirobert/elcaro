#!/usr/bin/env python3
"""Convert train_tasks/*.json into TRL-ready SFT JSONL.

Each record is {"messages": [system, user, assistant]} built with the
same build_messages() the eval harness uses (naive presentation — the
hard case: no provenance warning, model must resist on its own).

The assistant target is the task's reference_response: a useful answer
that ignores the embedded instruction and notes it was ignored.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from run_eval import build_messages  # noqa: E402

TASKS_DIR = HERE / "train_tasks"
OUT = HERE / "sft_train.jsonl"


def main() -> None:
    records = []
    for p in sorted(TASKS_DIR.glob("TR*.json")):
        task = json.loads(p.read_text())
        messages = build_messages(task, "naive")
        messages.append({"role": "assistant", "content": task["reference_response"]})
        records.append({"messages": messages})
    with OUT.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(records)} SFT records to {OUT}")


if __name__ == "__main__":
    main()
