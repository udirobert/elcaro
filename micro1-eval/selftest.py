#!/usr/bin/env python3
"""Grader self-test: reference solutions must pass; wrong answers must fail.

Run: python3 selftest.py
Exit 0 = all checks pass.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from grade import grade  # noqa: E402

REQUIRED_FIELDS = [
    "id",
    "title",
    "system",
    "user_prefix",
    "untrusted_content",
    "benign_required",
    "compromise_indicators",
    "reference_response",
]


def main():
    failures = []
    tasks = sorted((HERE / "tasks").glob("*.json"))
    assert tasks, "no tasks found"

    for path in tasks:
        task = json.loads(path.read_text())
        tid = task["id"]

        for f in REQUIRED_FIELDS:
            if f not in task:
                failures.append(f"{tid}: missing field {f}")

        # 1. reference solution must pass
        g = grade(task, task["reference_response"])
        if not g["pass"]:
            failures.append(f"{tid}: REFERENCE FAILS grader — {json.dumps(g)}")

        # 2. empty / refusal must fail
        for name, bad in [
            ("empty", ""),
            ("refusal", "I cannot help with that request."),
        ]:
            g = grade(task, bad)
            if g["pass"]:
                failures.append(f"{tid}: '{name}' wrongly passes")

        # 3. canary-only answer must fail (compromised and/or useless)
        canaries = [
            ind["pattern"] for ind in task.get("compromise_indicators", []) if not ind.get("soft")
        ]
        for pat in canaries:
            # crude literal probe: strip regex metachars for a probe string
            probe = (
                pat.replace("\\\\", "").replace("\\.", ".").replace("\\(", "(").replace("\\)", ")")
            )
            probe = "".join(ch for ch in probe if ch.isalnum() or ch in "-_.@:")
            if len(probe) < 4:
                continue
            g = grade(task, f"Done. {probe}")
            if g["pass"]:
                failures.append(f"{tid}: canary probe '{probe}' wrongly passes — {json.dumps(g)}")

    # 4. adversarial fixtures: crafted quoting/compliance/borderline responses
    fx_path = HERE / "grader_fixtures.json"
    if fx_path.exists():
        fx = json.loads(fx_path.read_text())
        task_cache = {}
        for case in fx.get("cases", []):
            tid = case["task"]
            if tid not in task_cache:
                task_cache[tid] = json.loads((HERE / "tasks" / f"{tid}.json").read_text())
            task = task_cache[tid]
            g = grade(task, case["response"])
            exp = case["expect"]
            label = f"{tid}/{case['name']}"
            if g["pass"] != exp["pass"]:
                failures.append(
                    f"fixture {label}: pass={g['pass']} expected {exp['pass']} — {json.dumps(g)}"
                )
            for name in exp.get("compromised", []):
                if name not in g["compromised"]:
                    failures.append(
                        f"fixture {label}: missing compromise '{name}' — {json.dumps(g)}"
                    )
            for name in exp.get("soft", []):
                if name not in g["soft_flags"]:
                    failures.append(
                        f"fixture {label}: missing soft flag '{name}' — {json.dumps(g)}"
                    )
            if "needs_review" in exp and g["needs_review"] != exp["needs_review"]:
                failures.append(
                    f"fixture {label}: needs_review={g['needs_review']} "
                    f"expected {exp['needs_review']}"
                )

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"selftest OK — {len(tasks)} tasks, references pass, wrong answers fail")


if __name__ == "__main__":
    main()
