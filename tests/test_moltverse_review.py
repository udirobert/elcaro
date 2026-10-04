import csv
import json
from pathlib import Path

import pytest

from swarm.moltverse_review import GUIDANCE, PER_STRATUM, export, prepare_adjudication, score
from swarm.precision_review import COLUMNS
from swarm.schema import SwarmMessage, TaggedMessage


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    tagged = tmp_path / "tagged.jsonl"
    with tagged.open("w") as file:
        for flag in (True, False):
            for n in range(PER_STRATUM):
                text = f"MoltVerse unique case {flag} {n}, how do agents coordinate these notes?"
                message = SwarmMessage(
                    id=f"moltverse:{flag}:{n}",
                    source="moltverse",
                    channel="https://moltbook.example/post/1",
                    actor=f"u/handle{n}",
                    ip16=None,
                    time="2026-02-01T01:00:00+00:00",
                    text=text,
                )
                row = TaggedMessage(
                    message, 0.55 if flag else 0.0, "low", ["swarm_directive"] if flag else [], []
                )
                file.write(json.dumps(row.to_dict()) + "\n")
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "provenance": {
                    "source_dataset": "christian-hoang-04/moltverse",
                    "posts_source_sha256": "p",
                    "comments_source_sha256": "c",
                }
            }
        )
    )
    return tagged, summary


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def update(path: Path, changed):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(changed)


def test_blind_frozen_packet(tmp_path):
    tagged, summary = fixture(tmp_path)
    dest = tmp_path / "out"
    key = export(tagged, summary, dest)
    assert len(key["entries"]) == 2 * PER_STRATUM
    assert key["unique_text_by_prediction"] == {"match": PER_STRATUM, "non_match": PER_STRATUM}
    assert all("prediction" in e and "body_sha256" in e for e in key["entries"])
    for letter in "ab":
        contents = rows(dest / f"reviewer-{letter}.csv")
        assert len(contents) == 80
        assert all(set(r) == set(COLUMNS) and not r["label"] for r in contents)
        assert all("prediction" not in r and "risk_score" not in r for r in contents)
    assert [r["sample_id"] for r in rows(dest / "reviewer-a.csv")] != [
        r["sample_id"] for r in rows(dest / "reviewer-b.csv")
    ]
    assert "self-asserted" in GUIDANCE and "not maliciousness" in GUIDANCE
    with pytest.raises(FileExistsError):
        export(tagged, summary, dest)


def test_unlabeled_and_disputed_packets_cannot_score(tmp_path):
    tagged, summary = fixture(tmp_path)
    out = tmp_path / "out"
    key = export(tagged, summary, out)
    a, b = out / "reviewer-a.csv", out / "reviewer-b.csv"
    with pytest.raises(ValueError, match="Incomplete"):
        score(out / "answer-key.json", a, b, None)
    look = {e["sample_id"]: e for e in key["entries"]}
    for path in (a, b):
        items = rows(path)
        for item in items:
            item["label"] = (
                "steering" if look[item["sample_id"]]["prediction"] == "match" else "non_steering"
            )
        update(path, items)
    base = score(out / "answer-key.json", a, b, None)
    assert base["reviewed"] == 80 and base["results"]["steering_among_matches"]["fraction"] == 1.0
    assert base["results"]["steering_among_non_matches"]["fraction"] == 0.0
    changed = rows(b)
    changed[0]["label"] = "uncertain"
    update(b, changed)
    with pytest.raises(ValueError, match="adjudication"):
        score(out / "answer-key.json", a, b, None)
    adjud = out / "adjudication.csv"
    assert prepare_adjudication(out / "answer-key.json", a, b, adjud) == 1
    pending = rows(adjud)
    assert len(pending) == 1 and pending[0]["label"] == ""
    pending[0]["label"] = "non_steering"
    update(adjud, pending)
    completed = score(out / "answer-key.json", a, b, adjud)
    assert completed["disagreed_or_uncertain"] == 1
    assert "not verified agent identity" in completed["interpretation"].lower()


def test_context_tampering_or_source_change_fails(tmp_path):
    tagged, summary = fixture(tmp_path)
    out = tmp_path / "out"
    export(tagged, summary, out)
    a = out / "reviewer-a.csv"
    b = out / "reviewer-b.csv"
    changed = rows(a)
    changed[0]["label"] = "steering"
    changed[0]["text"] = "changed"
    update(a, changed)
    with pytest.raises(ValueError, match="edited"):
        score(out / "answer-key.json", a, b, None)
    assert not (out / "score.json").exists()
    bad = tmp_path / "wrong.json"
    bad.write_text(json.dumps({"provenance": {"source_dataset": "other"}}))
    with pytest.raises(ValueError, match="source summary"):
        export(tagged, bad, tmp_path / "other")
