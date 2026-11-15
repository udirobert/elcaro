#!/usr/bin/env python3
"""Does the benchmark measure what Gateway customers get?

For each in-sample task (tasks/ only; the held-out set never leaves this
machine before the freeze), send the exact marked request the gateway arms
build to the live Gateway and compare its per-part verdicts (the `elcaro`
body object) with the benchmark's in-process core.policy.apply_policy:
same parts, same content hash, same risk score, same action, same
quarantine decision. Technique *order* is not compared (main's engine may
predate the determinism fix); the technique *set* is.

Usage (from lexsi-eval/):
  ELCARO_GATEWAY_KEY=... SERV_API_KEY=... uv run --project .. python check_gateway_parity.py
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_eval as r  # noqa: E402

GATEWAY = os.environ.get("ELCARO_GATEWAY_URL", "https://gateway.elcaro.trustfall.xyz")
MODES = {"gateway_warn": "warn", "gateway_quarantine": "quarantine"}
try:
    import certifi

    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL = None


def call_gateway(messages, mode, key, upstream_key, retries=2):
    body = json.dumps(
        {"model": "gpt-5.4-mini", "messages": messages, "max_completion_tokens": 16}
    ).encode()
    req = urllib.request.Request(  # noqa: S310 — fixed https Gateway URL
        f"{GATEWAY}/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-elcaro-key": key,
            "x-upstream-key": upstream_key,
            "x-elcaro-mode": mode,
        },
        method="POST",
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180, context=_SSL) as resp:  # noqa: S310
                return json.loads(resp.read()), resp.headers  # case-insensitive
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def _summ(result):
    return [
        {
            "path": v.path,
            "content_sha256": v.content_sha256,
            "risk_score": round(v.scan.risk_score, 6),
            "action": v.action,
            "quarantined": v.scan.quarantined,
            "techniques": sorted(t.value for t in v.scan.flagged_techniques),
        }
        for v in result.parts
    ]


def remote_parts(body):
    return [
        {
            "path": p["path"],
            "content_sha256": p["content_sha256"],
            "risk_score": round(p["risk_score"], 6),
            "action": p["action"],
            "quarantined": p["quarantined"],
            "techniques": sorted(p["flagged_techniques"]),
        }
        for p in body["elcaro"]["parts"]
    ]


def main():
    key = os.environ.get("ELCARO_GATEWAY_KEY")
    upstream = os.environ.get("SERV_API_KEY")
    if not (key and upstream):
        sys.exit("set ELCARO_GATEWAY_KEY and SERV_API_KEY")
    rows, mismatches = [], 0
    for path in sorted(r.TASKS_DIR.glob("*.json")):  # in-sample only, by design
        task = r.load_task(path)
        for presentation, mode in MODES.items():
            local = _summ_for(task, presentation)
            try:
                body, headers = call_gateway(r.gateway_request_messages(task), mode, key, upstream)
                remote = remote_parts(body)
                ok = local == remote
                note = "" if ok else json.dumps({"local": local, "gateway": remote})[:400]
            except urllib.error.HTTPError as e:
                ok, note, headers = False, f"HTTP {e.code}: {e.read()[:200]!r}", {}
            mismatches += not ok
            rows.append(
                {
                    "task": task["id"],
                    "mode": mode,
                    "match": ok,
                    "gateway_action": headers.get("x-elcaro-action"),
                    "parts": len(local),
                    "local_actions": [p["action"] for p in local],
                    "local_scores": [p["risk_score"] for p in local],
                    "note": note,
                }
            )
            print(
                f"  {task['id']} {mode:10s} match={ok} parts={len(local)} "
                f"gateway={headers.get('x-elcaro-action')} local={[p['action'] for p in local]}"
            )
    out = HERE / "gateway-parity.json"
    out.write_text(
        json.dumps({"gateway": GATEWAY, "checked": len(rows), "rows": rows}, indent=2) + "\n"
    )
    print(f"{len(rows) - mismatches}/{len(rows)} task×mode pairs match → {out.name}")
    sys.exit(1 if mismatches else 0)


def _summ_for(task, presentation):
    engine = r._elcaro_engine()  # also puts the repo root on sys.path for core/
    from core.policy import Mode, Provider, apply_policy

    result = apply_policy(
        r.gateway_request_messages(task),
        Provider.OPENAI,
        Mode(MODES[presentation]),
        engine=engine,
    )
    return _summ(result)


if __name__ == "__main__":
    main()
