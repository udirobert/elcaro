import csv
import json

import pytest

from swarm.precision_review import (
    COLUMNS,
    PER_STRATUM,
    export_packets,
    prepare_adjudication,
    score,
)
from swarm.schema import SwarmMessage, TaggedMessage


def row(corpus, label, index, *, text=None, rid=None):
    body = (
        text
        if text is not None
        else f"distinct {corpus} {label} review content number {index} for a peer"
    )
    message = SwarmMessage(
        id=rid or f"{corpus}-{label}-{index}",
        source=corpus,
        channel="review-room",
        actor=f"Agent-{index % 9}",
        ip16=None,
        time=f"2026-07-10T10:{index % 60:02d}:00Z",
        text=body,
    )
    return TaggedMessage(
        message,
        0.7 if label == "match" else 0.0,
        "low",
        ["swarm_directive"] if label == "match" else [],
        [],
    )


def corpus(name):
    return [row(name, label, i) for label in ("match", "non_match") for i in range(PER_STRATUM + 2)]


def factories(wiki=None, village=None):
    w = wiki if wiki is not None else corpus("collusion")
    v = village if village is not None else corpus("aivillage")
    return {"collusion": lambda: iter(w), "aivillage": lambda: iter(v)}


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def filled(out):
    entries = {
        e["sample_id"]: e for e in json.loads((out / "answer-key.json").read_text())["entries"]
    }
    for reviewer in "ab":
        file = out / f"reviewer-{reviewer}.csv"
        rows = read_rows(file)
        for item in rows:
            item["label"] = (
                "steering"
                if entries[item["sample_id"]]["prediction"] == "match"
                else "non_steering"
            )
        save_rows(file, rows)
    return entries


def test_blind_packet_size_and_fields(tmp_path):
    out = tmp_path / "review"
    key = export_packets(factories(), out)
    assert len(key["entries"]) == 4 * PER_STRATUM
    assert len({e["sample_id"] for e in key["entries"]}) == 4 * PER_STRATUM
    assert {e["prediction"] for e in key["entries"]} == {"match", "non_match"}
    assert key["census"]["collusion"]["eligible_records"] == 2 * (PER_STRATUM + 2)
    assert all(e["body_sha256"] and e["context_sha256"] for e in key["entries"])
    for reviewer in "ab":
        rows = read_rows(out / f"reviewer-{reviewer}.csv")
        assert len(rows) == 4 * PER_STRATUM
        assert all(set(r) == set(COLUMNS) and r["label"] == "" for r in rows)
        assert all(
            "risk_score" not in r and "prediction" not in r and "record_id" not in r for r in rows
        )
    assert [r["sample_id"] for r in read_rows(out / "reviewer-a.csv")] != [
        r["sample_id"] for r in read_rows(out / "reviewer-b.csv")
    ]
    assert "maliciousness" in (out / "review-guidance.txt").read_text()


def test_reordering_input_does_not_change_packet_or_key(tmp_path):
    w, v = corpus("collusion"), corpus("aivillage")
    a = tmp_path / "a"
    b = tmp_path / "b"
    export_packets(factories(w, v), a)
    export_packets(factories(list(reversed(w)), list(reversed(v))), b)
    for name in ("answer-key.json", "reviewer-a.csv", "reviewer-b.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_dedup_duplicate_id_and_formula_safety(tmp_path):
    w = [
        t
        for t in corpus("collusion")
        if t.message.id.startswith("collusion-non_match")
        or int(t.message.id.rsplit("-", 1)[1]) < PER_STRATUM
    ]
    w[0] = row("collusion", "match", 0, text="=2+2 please relay this answer to peers now")
    w += [row("collusion", "match", 888, text=w[0].message.text, rid="duplicate-body")]
    w += [
        row("collusion", "non_match", 333, rid="duplicate-record"),
        row("collusion", "non_match", 334, rid="duplicate-record"),
    ]
    out = tmp_path / "review"
    key = export_packets(factories(w), out)
    c = key["census"]["collusion"]
    assert c["duplicate_id_records_excluded"] == 2
    assert c["unique_review_texts"]["match"] == PER_STRATUM
    assert c["unique_review_texts"]["non_match"] == PER_STRATUM + 2
    assert all("duplicate-record" != e["record_id"] for e in key["entries"])
    assert any(r["text"].startswith("'=2+2") for r in read_rows(out / "reviewer-a.csv"))


def test_conflicting_predictions_for_same_review_text_fail_closed(tmp_path):
    w = corpus("collusion")
    w += [row("collusion", "non_match", 999, text=w[0].message.text)]
    with pytest.raises(ValueError, match="conflicting"):
        export_packets(factories(w), tmp_path / "review")


def test_insufficient_stratum_or_nonempty_out_fails(tmp_path):
    with pytest.raises(ValueError, match="Too few"):
        export_packets(factories(corpus("collusion")[:10]), tmp_path / "review")
    assert list((tmp_path / "review").iterdir()) == []
    (tmp_path / "review" / "existing.txt").write_text("preserve")
    with pytest.raises(FileExistsError):
        export_packets(factories(), tmp_path / "review")


def test_complete_agreement_scores_stratified_not_naive_accuracy(tmp_path):
    out = tmp_path / "review"
    export_packets(factories(), out)
    filled(out)
    result = score(out / "answer-key.json", out / "reviewer-a.csv", out / "reviewer-b.csv", None)
    assert result["reviewed"] == 4 * PER_STRATUM
    assert result["disagreed_or_uncertain"] == 0
    for corpus_name in ("collusion", "aivillage"):
        assert result["corpora"][corpus_name]["steering_among_matches"]["fraction"] == 1.0
        assert result["corpora"][corpus_name]["steering_among_non_matches"]["fraction"] == 0.0
        assert result["corpora"][corpus_name]["steering_among_matches"]["reviewed"] == PER_STRATUM
        assert result["corpora"][corpus_name]["steering_among_matches"]["wilson_95"][1] == 1.0
    assert "accuracy" not in result and "recall" not in result


def test_disputes_and_uncertainties_require_blinded_adjudication(tmp_path):
    out = tmp_path / "review"
    export_packets(factories(), out)
    filled(out)
    bfile = out / "reviewer-b.csv"
    rows = read_rows(bfile)
    sid1, sid2 = rows[0]["sample_id"], rows[1]["sample_id"]
    rows[0]["label"] = "uncertain"
    rows[1]["label"] = "uncertain"
    save_rows(bfile, rows)
    with pytest.raises(ValueError, match="2 cases require"):
        score(out / "answer-key.json", out / "reviewer-a.csv", bfile, None)
    pending = out / "adjudication.csv"
    assert (
        prepare_adjudication(out / "answer-key.json", out / "reviewer-a.csv", bfile, pending) == 2
    )
    pending_rows = read_rows(pending)
    assert {r["sample_id"] for r in pending_rows} == {sid1, sid2}
    assert all(r["label"] == "" and r["notes"] == "" for r in pending_rows)
    for r in pending_rows:
        r["label"] = "steering"
    save_rows(pending, pending_rows)
    result = score(out / "answer-key.json", out / "reviewer-a.csv", bfile, pending)
    assert result["disagreed_or_uncertain"] == 2
    pending_rows[0]["label"] = "uncertain"
    save_rows(pending, pending_rows)
    with pytest.raises(ValueError, match="Uncertain"):
        score(out / "answer-key.json", out / "reviewer-a.csv", bfile, pending)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unexpected", "context", "bad-label"])
def test_tampered_or_incomplete_reviews_fail(tmp_path, mutation):
    out = tmp_path / "review"
    export_packets(factories(), out)
    filled(out)
    a = out / "reviewer-a.csv"
    rows = read_rows(a)
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(rows[0].copy())
    elif mutation == "unexpected":
        rows[0]["sample_id"] = "unknown"
    elif mutation == "context":
        rows[0]["text"] = "changed reviewer input"
    else:
        rows[0]["label"] = "invalid"
    save_rows(a, rows)
    with pytest.raises(ValueError):
        score(out / "answer-key.json", a, out / "reviewer-b.csv", None)


def test_adjudication_cannot_contain_undisputed_samples(tmp_path):
    out = tmp_path / "review"
    export_packets(factories(), out)
    filled(out)
    adjudication = out / "adjudication.csv"
    rows = read_rows(out / "reviewer-a.csv")
    save_rows(adjudication, rows[:1])
    with pytest.raises(ValueError):
        score(out / "answer-key.json", out / "reviewer-a.csv", out / "reviewer-b.csv", adjudication)
