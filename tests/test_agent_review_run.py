import json
import os
from decimal import Decimal

import httpx
import pytest

from swarm.agent_review import _jsonl, _read_jsonl, format_request, prepare
from swarm.agent_review_run import (
    _load_credential,
    _private_append,
    _single_runner_lock,
    run_one_provider,
)
from swarm.precision_review import PER_STRATUM, export_packets
from swarm.schema import SwarmMessage, TaggedMessage


class FakeClient:
    def __init__(self, provider="featherless", status=200, usage=True):
        self.calls = []
        self.provider = provider
        self.status = status
        self.usage = usage

    def post(self, endpoint, headers, json):
        self.calls.append((endpoint, headers, json))
        return httpx.Response(
            self.status,
            json={
                "model": json["model"],
                "answers": {
                    "peer_steering": {
                        "type": "choice",
                        "choice": "steering",
                        "confidence": 0.8,
                        "probabilities": {"steering": 0.8, "non_steering": 0.1, "uncertain": 0.1},
                    }
                },
                **({"usage": {"input_tokens": 120}} if self.usage else {}),
            },
        )


def setup_run(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    corpora = {}
    for corpus in ("collusion", "aivillage"):
        rows = []
        for prediction in (False, True):
            for i in range(PER_STRATUM):
                msg = SwarmMessage(
                    id=f"{corpus}-{prediction}-{i}",
                    source=corpus,
                    channel="test-room",
                    actor=f"peer-{i}",
                    ip16=None,
                    time="2026-07-10T10:10:00Z",
                    text=f"Long enough peer task text for {corpus} {prediction} {i} end.",
                )
                rows.append(
                    TaggedMessage(
                        msg,
                        0.6 if prediction else 0.1,
                        "safe",
                        ["swarm_directive"] if prediction else [],
                        [],
                    )
                )
        corpora[corpus] = rows
    human = tmp_path / "human"
    export_packets(
        {corpus: lambda rows=rows: iter(rows) for corpus, rows in corpora.items()}, human
    )
    paths = {}
    for corpus, rows in corpora.items():
        path = tmp_path / f"{corpus}.jsonl"
        _jsonl(path, [r.to_dict() for r in rows])
        paths[corpus] = path
    output = tmp_path / "agent"
    prepare(human / "answer-key.json", paths, output)
    env = tmp_path / ".env.local"
    env.write_text("RUNWARE_API_KEY=x\nFEATHERLESS_API_KEY=x\n")
    env.chmod(0o600)
    return output, env


def run(output, env, fake, provider="featherless", cap="1.00", limit=1):
    return run_one_provider(
        provider,
        output / "experiment.json",
        output / "cases.jsonl",
        output / f"requests-{provider}.jsonl",
        env,
        output,
        Decimal(cap),
        limit,
        client=fake,
    )


def test_one_request_each_and_shared_spend_ledger(tmp_path):
    output, env = setup_run(tmp_path)
    featherless = FakeClient()
    first = run(output, env, featherless)
    assert first["new_requests"] == 1 and Decimal(first["estimated_total_usd"]) > 0
    assert len(featherless.calls) == 1
    endpoint, headers, payload = featherless.calls[0]
    assert endpoint == "https://api.featherless.ai/v1/systemone"
    assert headers["Authorization"] == "Bearer x"
    assert "rule_engine_score" not in json.dumps(payload)
    assert "FEATHERLESS_API_KEY" not in json.dumps(payload)
    assert payload["questions"]["peer_steering"]["type"] == "choice"
    laya = FakeClient("laya")
    second = run(output, env, laya, provider="laya")
    assert second["new_requests"] == 1
    assert Decimal(second["estimated_total_usd"]) > Decimal(first["estimated_total_usd"])
    assert laya.calls[0][0] == "https://api.runware.ai/v1/systemone"
    ledger = _read_jsonl(output / "spend-ledger.jsonl")
    assert len([e for e in ledger if e["event"] == "started"]) == 2
    assert len([e for e in ledger if e["event"] == "finished"]) == 2
    assert len(_read_jsonl(output / "responses-featherless.jsonl")) == 1
    assert len(_read_jsonl(output / "responses-laya.jsonl")) == 1
    assert os.stat(output / "responses-featherless.jsonl").st_mode & 0o777 == 0o600
    again = run(output, env, FakeClient(), limit=1)
    assert again["new_requests"] == 1
    assert len({r["sample_id"] for r in _read_jsonl(output / "responses-featherless.jsonl")}) == 2


def test_small_cap_prevents_network(tmp_path):
    output, env = setup_run(tmp_path)
    fake = FakeClient()
    result = run(output, env, fake, cap="0.000001", limit=120)
    assert result["new_requests"] == 0
    assert fake.calls == []
    assert not (output / "spend-ledger.jsonl").exists()


def test_unknown_cost_and_http_failure_stop_without_retry(tmp_path):
    output, env = setup_run(tmp_path)
    fake = FakeClient(usage=False)
    with pytest.raises(ValueError, match="manual review"):
        run(output, env, fake)
    assert len(fake.calls) == 1
    with pytest.raises(ValueError, match="unresolved billing"):
        run(output, env, FakeClient())
    other = tmp_path / "other"
    from tests.test_agent_review import _setup

    _, output2, _ = _setup(other)
    with pytest.raises(ValueError, match="manual review"):
        run(output2, env, FakeClient(status=401))
    assert not (output2 / "responses-featherless.jsonl").exists()


def test_env_file_rejects_wrong_permissions_or_unknown_keys(tmp_path):
    output, env = setup_run(tmp_path)
    env.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        run(output, env, FakeClient())
    env.chmod(0o600)
    env.write_text("RUNWARE_API_KEY=x\nFEATHERLESS_API_KEY=x\nUNEXPECTED_KEY=bad\n")
    with pytest.raises(ValueError, match="unexpected"):
        _load_credential(env, "FEATHERLESS_API_KEY")


def test_runner_lock_prevents_concurrent_spending(tmp_path):
    with _single_runner_lock(tmp_path):
        with pytest.raises(ValueError, match="already active"):
            with _single_runner_lock(tmp_path):
                pass
    with _single_runner_lock(tmp_path):
        pass


def test_unresolved_started_request_requires_manual_review(tmp_path):
    output, env = setup_run(tmp_path)
    request = format_request(_read_jsonl(output / "cases.jsonl")[0], "featherless")
    _private_append(
        output / "spend-ledger.jsonl",
        {
            "event": "started",
            "provider": "featherless",
            "request_sha256": request["request_sha256"],
            "sample_id": request["sample_id"],
        },
    )
    with pytest.raises(ValueError, match="unresolved billing"):
        run(output, env, FakeClient())
