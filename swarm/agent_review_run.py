from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

from swarm.agent_review import (
    PROVIDER_MODELS,
    QUESTION,
    _answer,
    _canonical,
    _hash,
    _read_jsonl,
    format_request,
)

ENDPOINTS = {
    "laya": ("https://api.runware.ai/v1/systemone", "RUNWARE_API_KEY", Decimal("0.02")),
    "featherless": (
        "https://api.featherless.ai/v1/systemone",
        "FEATHERLESS_API_KEY",
        Decimal("0.28"),
    ),
}
TOKEN_OVERHEAD_RESERVE = 8192


def _load_credential(path: Path, name: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Credential file must be a regular file")
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("Credential file must be owned by this user and mode 0600")
    values = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (
            separator != "="
            or key not in {"RUNWARE_API_KEY", "FEATHERLESS_API_KEY"}
            or key in values
        ):
            raise ValueError("Credential file has an unexpected or duplicated variable")
        values[key] = value
    if not values.get(name):
        raise ValueError(f"{name} was not supplied in the credential file")
    return values[name]


def _private_append(path: Path, row: dict) -> None:
    if path.exists() and (path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600):
        raise ValueError("Review journal file must be owner-only")
    descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
        file.flush()
        os.fsync(file.fileno())


@contextmanager
def _single_runner_lock(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "runner.lock"
    if path.is_symlink() or (path.exists() and stat.S_IMODE(path.stat().st_mode) != 0o600):
        raise ValueError("Runner lock file must be owner-only")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another provider runner is already active") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def run_one_provider(
    provider: str,
    experiment_path: Path,
    cases_path: Path,
    requests_path: Path,
    credential_file: Path,
    output_dir: Path,
    max_total_usd: Decimal,
    max_new_requests: int,
    client: httpx.Client | None = None,
) -> dict:
    if provider not in ENDPOINTS:
        raise ValueError("Only the configured Runware and Featherless rails are supported")
    if max_total_usd <= 0 or max_new_requests < 1 or max_new_requests > 120:
        raise ValueError("A positive spend cap and 1–120 new requests are required")
    manifest = json.loads(experiment_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("question_sha256") != _hash(
        _canonical(QUESTION)
    ):
        raise ValueError("Frozen experiment question changed")
    if manifest.get("model_ids", {}).get(provider) != PROVIDER_MODELS[provider]:
        raise ValueError("Frozen provider model changed")
    cases = _read_jsonl(cases_path)
    if (
        len(cases) != manifest["prepared_count"]
        or _hash(_canonical(cases)) != manifest["cases_sha256"]
    ):
        raise ValueError("Frozen cases changed")
    requests = _read_jsonl(requests_path)
    if requests != [format_request(case, provider) for case in cases]:
        raise ValueError("Frozen provider requests changed")
    endpoint, variable, rate_per_million = ENDPOINTS[provider]
    credential = _load_credential(credential_file, variable)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = output_dir / "spend-ledger.jsonl"
    reply_path = output_dir / f"responses-{provider}.jsonl"
    entries = _read_jsonl(ledger) if ledger.exists() else []
    started = {(r["provider"], r["request_sha256"]) for r in entries if r["event"] == "started"}
    finished = {(r["provider"], r["request_sha256"]) for r in entries if r["event"] == "finished"}
    if started != finished:
        raise ValueError(
            "An earlier provider request has an unresolved billing outcome; stop for manual review"
        )
    total = sum(
        (Decimal(r["estimated_usd"]) for r in entries if r["event"] == "finished"), Decimal("0")
    )
    if total >= max_total_usd:
        raise ValueError("The approved spend cap has been reached")
    if reply_path.exists():
        response_ids = {row["sample_id"] for row in _read_jsonl(reply_path)}
    else:
        response_ids = set()
    sent = 0
    owned_client = client is None
    if client is None:
        client = httpx.Client(timeout=15, follow_redirects=False, trust_env=False)
    try:
        for request in requests:
            if sent >= max_new_requests:
                break
            identity = (provider, request["request_sha256"])
            if identity in finished or request["sample_id"] in response_ids:
                continue
            payload = request["body"]
            estimated_tokens = len(_canonical(payload)) + TOKEN_OVERHEAD_RESERVE
            reserved = Decimal(estimated_tokens) * rate_per_million / Decimal(1_000_000)
            if total + reserved > max_total_usd:
                break
            _private_append(
                ledger,
                {
                    "event": "started",
                    "provider": provider,
                    "sample_id": request["sample_id"],
                    "request_sha256": request["request_sha256"],
                    "reserved_usd": str(reserved),
                },
            )
            sent += 1
            try:
                response = client.post(
                    endpoint, headers={"Authorization": f"Bearer {credential}"}, json=payload
                )
                data = response.json() if response.status_code == 200 else None
                usage = data.get("usage") if isinstance(data, dict) else None
                count = usage.get("input_tokens") if isinstance(usage, dict) else None
                if (
                    response.status_code != 200
                    or isinstance(count, bool)
                    or not isinstance(count, int)
                    or count < 0
                ):
                    _private_append(
                        ledger,
                        {
                            "event": "manual_review",
                            "provider": provider,
                            "sample_id": request["sample_id"],
                            "request_sha256": request["request_sha256"],
                            "http_status": response.status_code,
                        },
                    )
                    raise ValueError(
                        "Provider response did not include a valid success and "
                        "input token count; billing status requires manual review"
                    )
                estimated_cost = Decimal(count) * rate_per_million / Decimal(1_000_000)
                _private_append(
                    reply_path,
                    {
                        "sample_id": request["sample_id"],
                        "request_sha256": request["request_sha256"],
                        "response": data,
                    },
                )
                _private_append(
                    ledger,
                    {
                        "event": "finished",
                        "provider": provider,
                        "sample_id": request["sample_id"],
                        "request_sha256": request["request_sha256"],
                        "estimated_usd": str(estimated_cost),
                        "input_tokens": count,
                    },
                )
                total += estimated_cost
                _, issue = _answer(data, PROVIDER_MODELS[provider])
                if issue or total >= max_total_usd or estimated_cost > reserved:
                    break
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                _private_append(
                    ledger,
                    {
                        "event": "manual_review",
                        "provider": provider,
                        "sample_id": request["sample_id"],
                        "request_sha256": request["request_sha256"],
                        "error_type": type(exc).__name__,
                    },
                )
                raise ValueError(
                    "Provider request outcome uncertain; stop for manual review"
                ) from None
    finally:
        if owned_client:
            client.close()
    return {
        "provider": provider,
        "new_requests": sent,
        "estimated_total_usd": str(total),
        "limit_usd": str(max_total_usd),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Opt-in typed-review provider runner with a spend gate"
    )
    parser.add_argument("--provider", required=True, choices=tuple(ENDPOINTS))
    parser.add_argument(
        "--experiment", type=Path, default=Path("data/swarm/agent-review-v1/experiment.json")
    )
    parser.add_argument(
        "--cases", type=Path, default=Path("data/swarm/agent-review-v1/cases.jsonl")
    )
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env.local"))
    parser.add_argument("--out", type=Path, default=Path("data/swarm/agent-review-v1"))
    parser.add_argument("--max-total-usd", type=str, required=True)
    parser.add_argument("--max-new-requests", type=int, required=True)
    args = parser.parse_args()
    try:
        cap = Decimal(args.max_total_usd)
    except InvalidOperation as exc:
        raise SystemExit("Invalid USD spend limit") from exc
    with _single_runner_lock(args.out):
        result = run_one_provider(
            args.provider,
            args.experiment,
            args.cases,
            args.requests,
            args.env_file,
            args.out,
            cap,
            args.max_new_requests,
        )
    print(
        f"{result['provider']}: {result['new_requests']} new calls; estimated "
        f"cumulative USD {result['estimated_total_usd']}; limit USD "
        f"{result['limit_usd']}"
    )


if __name__ == "__main__":
    main()
