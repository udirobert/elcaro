import json

import pytest

from swarm.agent_review import (
    CHOICES,
    MAX_TEXT_CHARS,
    PROVIDER_MODELS,
    QUESTION,
    _answer,
    _canonical,
    _hash,
    _jsonl,
    _read_jsonl,
    format_request,
    prepare,
    validate_offline,
)
from swarm.precision_review import PER_STRATUM, export_packets
from swarm.schema import SwarmMessage, TaggedMessage


def _tagged(corpus, predicted, i, *, too_long=False):
    text = f"message in {corpus} stratum {predicted} case {i}; no untrusted instructions followed. "
    if too_long:
        text += "x" * (MAX_TEXT_CHARS + 1)
    return TaggedMessage(
        message=SwarmMessage(
            id=f"{corpus}-{predicted}-{i}",
            source=corpus,
            channel="room",
            actor=f"peer-{i}",
            ip16=None,
            time="2026-07-10T10:10:00Z",
            text=text,
        ),
        risk_score=0.7 if predicted else 0.1,
        risk_level="suspicious" if predicted else "safe",
        techniques=["swarm_directive"] if predicted else [],
        hits=[],
    )


def _setup(tmp_path):
    corpora = {
        corpus: [
            _tagged(corpus, predicted, i, too_long=i == 0)
            for predicted in (True, False)
            for i in range(PER_STRATUM)
        ]
        for corpus in ("collusion", "aivillage")
    }
    human = tmp_path / "human"
    export_packets(
        {corpus: lambda rows=rows: iter(rows) for corpus, rows in corpora.items()}, human
    )
    paths = {}
    for corpus, rows in corpora.items():
        path = tmp_path / f"{corpus}.jsonl"
        _jsonl(path, [t.to_dict() for t in rows])
        paths[corpus] = path
    out = tmp_path / "agent"
    manifest = prepare(human / "answer-key.json", paths, out)
    return human, out, manifest


def _response(request, choice="steering", model=None, probabilities=None):
    answer = {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities or {"steering": 0.8, "non_steering": 0.1, "uncertain": 0.1},
        "confidence": 0.8,
    }
    return {
        "sample_id": request["sample_id"],
        "request_sha256": request["request_sha256"],
        "response": {
            "model": model or request["body"]["model"],
            "answers": {"peer_steering": answer},
        },
    }


def test_frozen_sample_reuse_no_prediction_leak_or_network(tmp_path, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("No network in offline preparation")

    monkeypatch.setattr("httpx.post", fail_network)
    human, out, manifest = _setup(tmp_path)
    key = json.loads((human / "answer-key.json").read_text())
    assert manifest["sample_count"] == 4 * PER_STRATUM
    assert manifest["prepared_count"] == 4 * (PER_STRATUM - 1)
    assert manifest["excluded_count"] == 4
    assert {e["sample_id"] for e in key["entries"]} == {
        c["sample_id"] for c in _read_jsonl(out / "cases.jsonl")
    } | {c["sample_id"] for c in manifest["excluded"]}
    assert not (out / "score.json").exists()
    for provider in PROVIDER_MODELS:
        requests = _read_jsonl(out / f"requests-{provider}.jsonl")
        assert len(requests) == manifest["prepared_count"]
        for r in requests:
            assert r["endpoint_path"] == "/v1/systemone"
            assert r["body"]["model"] == PROVIDER_MODELS[provider]
            assert r["body"]["questions"] == QUESTION
            assert set(r["body"]) == {"model", "state", "questions"}
            assert len(r["body"]["state"]["message"]) <= MAX_TEXT_CHARS
            assert _hash(_canonical(r["body"])) == r["request_sha256"]
            assert "rule_engine_score" not in json.dumps(r) and "swarm_directive" not in json.dumps(
                r
            )
    assert {c["sample_id"] for c in _read_jsonl(out / "cases.jsonl")} == {
        r["sample_id"] for r in _read_jsonl(out / "requests-jev.jsonl")
    }


def test_adapters_use_identical_question_and_state(tmp_path):
    _, out, _ = _setup(tmp_path)
    prepared = _read_jsonl(out / "cases.jsonl")
    for case in prepared:
        requests = {p: format_request(case, p) for p in PROVIDER_MODELS}
        assert {r["body"]["state"]["message"] for r in requests.values()} == {
            case["state"]["message"]
        }
        assert all(r["body"]["questions"] == QUESTION for r in requests.values())
        assert all(
            set(r["body"]["questions"]["peer_steering"]["criteria"]) == CHOICES
            for r in requests.values()
        )
    with pytest.raises(ValueError, match="Unknown"):
        format_request(prepared[0], "unknown")


def test_validation_preserves_missing_errors_and_unbound_not_negative(tmp_path):
    _, out, manifest = _setup(tmp_path)
    requests = _read_jsonl(out / "requests-featherless.jsonl")
    responses = [
        _response(requests[0]),
        {
            "sample_id": requests[1]["sample_id"],
            "request_sha256": requests[1]["request_sha256"],
            "error": "provider unavailable",
        },
        _response(requests[2]),
    ]
    responses[2]["request_sha256"] = "changed"
    response_file = out / "responses.jsonl"
    _jsonl(response_file, responses)
    validated = validate_offline(
        out / "experiment.json",
        out / "cases.jsonl",
        "featherless",
        response_file,
        out / "validated.json",
    )
    assert validated["prepared_count"] == manifest["prepared_count"]
    assert validated["status_counts"] == {
        "answered": 1,
        "missing_response": manifest["prepared_count"] - 3,
        "provider_error": 1,
        "unbound_response": 1,
    }
    assert all("fraction" not in r and "precision" not in r for r in validated["results"])
    assert not any("provider unavailable" in json.dumps(r) for r in validated["results"])
    responses.append(_response(requests[0]))
    _jsonl(response_file, responses)
    with pytest.raises(ValueError, match="duplicate"):
        validate_offline(
            out / "experiment.json",
            out / "cases.jsonl",
            "featherless",
            response_file,
            out / "invalid.json",
        )
    assert not (out / "invalid.json").exists()


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"answers": {}}, "malformed_response"),
        ({"model": "other", "answers": {}}, "model_mismatch"),
        (
            {
                "model": "jev-1.13.0",
                "answers": {
                    "peer_steering": {
                        "type": "choice",
                        "choice": "steering",
                        "probabilities": {"steering": 0.8, "non_steering": 0.8, "uncertain": 0.1},
                    }
                },
            },
            "invalid_probabilities",
        ),
        (
            {
                "model": "jev-1.13.0",
                "answers": {
                    "peer_steering": {
                        "type": "choice",
                        "choice": "steering",
                        "probabilities": {"steering": 0.1, "non_steering": 0.8, "uncertain": 0.1},
                    }
                },
            },
            "invalid_choice_distribution",
        ),
        (
            {
                "model": "jev-1.13.0",
                "answers": {
                    "peer_steering": {
                        "type": "choice",
                        "choice": "steering",
                        "probabilities": {"steering": True, "non_steering": 0, "uncertain": 0},
                    }
                },
            },
            "invalid_probabilities",
        ),
    ],
)
def test_malformed_answers_fail_closed(payload, expected):
    _, issue = _answer(payload, "jev-1.13.0")
    assert issue == expected


def test_pinned_question_and_case_integrity_required(tmp_path):
    _, out, _ = _setup(tmp_path)
    index = out / "experiment.json"
    cases = out / "cases.jsonl"
    empty = out / "responses.jsonl"
    _jsonl(empty, [])
    manifest = json.loads(index.read_text())
    manifest["question_sha256"] = "changed"
    index.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="question"):
        validate_offline(index, cases, "jev", empty, out / "result.json")
    assert not (out / "result.json").exists()
    manifest["question_sha256"] = _hash(_canonical(QUESTION))
    index.write_text(json.dumps(manifest))
    rows = _read_jsonl(cases)
    rows[0]["state"]["message"] += " changed"
    _jsonl(cases, rows)
    with pytest.raises(ValueError, match="case set"):
        validate_offline(index, cases, "jev", empty, out / "result.json")


def test_request_and_state_have_no_human_csv_fields(tmp_path):
    _, out, _ = _setup(tmp_path)
    for request in _read_jsonl(out / "requests-laya.jsonl"):
        assert not any(
            key in request["body"]["state"]
            for key in ("label", "notes", "prediction", "body_sha256", "sample_id")
        )
        assert request["body"]["state"].keys() == {"message", "source", "channel", "actor", "time"}
