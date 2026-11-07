#!/usr/bin/env python3
"""Curate the IPI task corpus with Lexsi-Labs/CuratorKIT.

Feeds tasks/*.json through CuratorKIT's ingest -> dedup -> hygiene
pipeline and writes a provenance-manifested export (manifest.json,
rejected.jsonl, dataset_card.md, lexsi_provenance.json, checksums.txt)
that doubles as the Hugging Face dataset card source.

Two deliberate config choices, both load-bearing for adversarial data:

- ``clean=False``: the default TextCleaner strips HTML-tag-shaped text,
  which silently destroys tag-based injection payloads (CuratorKIT
  itself warns about this). Normalisation/whitespace transforms would
  likewise corrupt obfuscation-dependent attacks, so byte-exact
  preservation wins over cosmetic cleaning.
- ``secrets_gate=True``: rejects samples containing real credentials.
  Note this flags our base64-encoded injection payloads too — a
  documented false-positive class for adversarial corpora (see
  docs/hackathons.md and the write-up).

Requires:  lexsi-eval/.venv  (pip install "curatorkit[connectors]")

Usage:
  .venv/bin/python curate_tasks.py [--output-dir curated-tasks]
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from curatorkit import Curator, CuratorConfig  # noqa: E402

TASKS_DIR = HERE / "tasks"


def task_to_record(path: Path) -> dict:
    """Map a task file onto CuratorKIT's instruction/input/output slots.

    Unmapped columns are preserved in sample.metadata automatically.
    """
    t = json.loads(path.read_text())
    return {
        "instruction": t["user_prefix"],
        "input": t["untrusted_content"],
        "output": t.get("reference_response", ""),
        "task_id": t["id"],
        "title": t["title"],
        "domain": t["domain"],
        "content_type": t["content_type"],
        "source": t["source"],
        "system": t["system"],
        "user_suffix": t["user_suffix"],
        "benign_required": json.dumps(t.get("benign_required", [])),
        "benign_groups": json.dumps(t.get("benign_groups", [])),
        "compromise_indicators": json.dumps(t.get("compromise_indicators", [])),
        "expected_failure": t.get("expected_failure", ""),
        "notes": t.get("notes", ""),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=str(HERE / "curated-tasks"))
    ap.add_argument("--work-file", default=None, help="intermediate JSONL path (default: tempfile)")
    args = ap.parse_args()

    if args.work_file:
        work = Path(args.work_file)
        work.parent.mkdir(parents=True, exist_ok=True)
    else:
        import tempfile

        fd, tmp = tempfile.mkstemp(suffix=".jsonl", prefix="ipi_tasks_")
        os.close(fd)
        work = Path(tmp)
    with work.open("w") as f:
        for p in sorted(TASKS_DIR.glob("T*.json")):
            f.write(json.dumps(task_to_record(p)) + "\n")

    result = Curator(
        CuratorConfig(
            dataset=str(work),
            clean=False,
            dedup="minhash",
            secrets_gate=True,
            export_formats=["corpus", "alpaca"],
            output_dir=args.output_dir,
            name="ipi-eval-tasks",
        )
    ).run()
    result.print_summary()


if __name__ == "__main__":
    main()
