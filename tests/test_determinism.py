"""Regression test: scan output must be deterministic across PYTHONHASHSEEDs.

flagged_techniques was built with ``list({...})`` on a str enum, so its order
depended on hash randomization — leaking into human_summary and quarantine
text for identical input. This test scans a fixed multi-technique payload in
subprocesses under several hash seeds and asserts identical output.

Run: python -m pytest tests/test_determinism.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = REPO_ROOT / "lexsi-eval" / "tasks" / "T10.json"

SCAN_SCRIPT = """\
import json
import sys

sys.path.insert(0, {root!r})
from core import ContentType, IpiDetectionEngine, ScanRequest

task = json.load(open({task!r}))
engine = IpiDetectionEngine(classifier=None)
result = engine.scan(
    ScanRequest(content=task["untrusted_content"], content_type=ContentType.EMAIL)
)
print(
    json.dumps(
        {{
            "flagged_techniques": [t.value for t in result.flagged_techniques],
            "human_summary": result.human_summary,
            "risk_score": result.risk_score,
        }}
    )
)
"""


def _scan(seed: str) -> dict:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    out = subprocess.run(
        [sys.executable, "-c", SCAN_SCRIPT.format(root=str(REPO_ROOT), task=str(TASK_PATH))],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(out.stdout)


def test_scan_output_is_deterministic_across_hash_seeds():
    results = {seed: _scan(seed) for seed in ("0", "1", "2", "3")}
    baseline = results["0"]
    assert len(baseline["flagged_techniques"]) > 1, (
        "test needs a multi-technique payload to catch ordering bugs"
    )
    for seed, result in results.items():
        assert result == baseline, f"PYTHONHASHSEED={seed} diverged: {result}"
