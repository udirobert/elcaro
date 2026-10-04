import hashlib
import json
from pathlib import Path

import pytest

from swarm.claims import build_claim_ledger
from swarm.report import write_findings
from swarm.schema import Finding, SwarmMessage, TaggedMessage, TechniqueHit

CORPUS = "testcorpus"
LONG = "The quick brown fox jumps over the lazy dog again."


def make_tagged(
    rid: str,
    text: str = LONG,
    *,
    actor: str = "AgentA",
    source: str = "dse",
    time: str = "2026-06-16T10:00:00Z",
    techniques: list[str] | None = None,
    hits: list[TechniqueHit] | None = None,
    meta: dict | None = None,
) -> TaggedMessage:
    return TaggedMessage(
        message=SwarmMessage(
            id=rid,
            source=source,
            channel="chan",
            actor=actor,
            ip16=None,
            time=time,
            text=text,
            meta=meta or {},
        ),
        risk_score=0.0,
        risk_level="safe",
        techniques=techniques or [],
        hits=hits or [],
    )


def claim(ledger: dict, cid: str) -> dict:
    return next(c for c in ledger["claims"] if c["id"] == cid)


def expected_bucket(actor: str) -> int:
    return hashlib.sha256(actor.encode()).digest()[0] % 2


def test_steering_counts_class_once_per_record_even_duplicate_technique():
    tagged = [make_tagged("r1", techniques=["swarm_directive", "swarm_directive"])]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "steering")
    assert c["status"] == "supported"
    assert c["observed"]["matches"] == 1
    assert c["observed"]["technique_counts"]["swarm_directive"] == 1


def test_steering_excludes_short_records_for_class_g():
    tagged = [make_tagged("r1", text="short", techniques=["swarm_directive"])]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "steering")
    assert c["observed"]["matches"] == 0
    assert c["status"] == "insufficient_evidence"
    assert ledger["accounting"]["skipped_short_records"] == 1


def test_zero_denominator_reference_rate_is_null():
    tagged = [make_tagged("r1", text="")]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    ref = claim(ledger, "steering")["reference"]
    assert ref["analysis_set"]["eligible_records"] == 0
    assert ref["analysis_set"]["rate"] is None
    assert ref["reference_set"]["rate"] is None


def test_actor_disjoint_partition_invariant_to_reorder():
    tagged = [make_tagged(f"r{i}", actor=f"Agent{i}", source=f"src{i % 3}") for i in range(12)]
    a = build_claim_ledger(tagged, {}, [], CORPUS)
    b = build_claim_ledger(list(reversed(tagged)), {}, [], CORPUS)
    ra = claim(a, "steering")["reference"]
    rb = claim(b, "steering")["reference"]
    assert ra["analysis_set"]["eligible_records"] == rb["analysis_set"]["eligible_records"]
    assert ra["reference_set"]["eligible_records"] == rb["reference_set"]["eligible_records"]
    assert ra["analysis_set"]["matches"] == rb["analysis_set"]["matches"]
    assert ra["reference_set"]["matches"] == rb["reference_set"]["matches"]


def test_partition_matches_expected_sha256_buckets():
    tagged = [make_tagged(f"r{i}", actor=f"Agent{i}") for i in range(8)]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    ref = claim(ledger, "steering")["reference"]
    want0 = sum(expected_bucket(f"Agent{i}") == 0 for i in range(8))
    want1 = 8 - want0
    assert ref["analysis_set"]["eligible_records"] == want0
    assert ref["reference_set"]["eligible_records"] == want1


def test_same_actor_across_sources_stays_in_one_bucket():
    tagged = [
        make_tagged("r1", actor="SharedAgent", source="dse"),
        make_tagged("r2", actor="SharedAgent", source="cross-site"),
        make_tagged("r3", actor="SharedAgent", source="fractal"),
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    ref = claim(ledger, "steering")["reference"]
    bucket = expected_bucket("SharedAgent")
    sets = [ref["analysis_set"], ref["reference_set"]]
    assert sets[bucket]["eligible_records"] == 3
    assert sets[1 - bucket]["eligible_records"] == 0


def test_reference_sets_not_called_benign():
    tagged = [make_tagged(f"r{i}", actor=f"A{i}") for i in range(6)]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    ref = claim(ledger, "steering")["reference"]
    assert set(ref) == {
        "method",
        "selection",
        "analysis_set",
        "reference_set",
        "limitation",
    }
    assert "benign" not in ref["method"]
    assert "benign" not in ref["selection"]


def test_scorer_full_text_match_after_40000_and_accounting_truncated():
    text = "x" * 40_100 + " the scorer logged it"
    tagged = [make_tagged("r1", text=text)]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "evaluation-vocabulary")
    assert c["status"] == "supported"
    assert c["observed"]["matches"] == 1
    assert ledger["accounting"]["scan_truncated_records"] == 1


def test_evaluation_awareness_always_insufficient():
    tagged = [make_tagged("r1", text="the scorer logged my transcript and grade")]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "evaluation-awareness")
    assert c["status"] == "insufficient_evidence"
    assert claim(ledger, "evaluation-vocabulary")["status"] == "supported"


def test_accounting_missing_time_empty_and_duplicate_ids():
    tagged = [
        make_tagged("r1", time="not-a-time"),
        make_tagged("r1", text=""),
        make_tagged("r2"),
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    a = ledger["accounting"]
    assert a["normalized_records"] == 3
    assert a["unique_record_ids"] == 2
    assert a["duplicate_record_ids"] == 1
    assert a["empty_text_records"] == 1
    assert a["missing_or_unparseable_time_records"] == 1


def test_persistence_not_applicable_without_pages():
    ledger = build_claim_ledger([make_tagged("r1")], {}, [], CORPUS)
    assert claim(ledger, "persistence")["status"] == "not_applicable"


def test_zzz_page_repeated_revisions_counted_once():
    meta = {"page_key": "dse~ZZZPage", "page_name": "ZZZPage"}
    tagged = [
        make_tagged("r1", meta=dict(meta)),
        make_tagged("r2", meta=dict(meta)),
        make_tagged("r3", meta={"page_key": "dse~Other", "page_name": "Other"}),
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "persistence")
    assert c["observed"]["zzz_named_pages"] == 1
    assert c["observed"]["eligible_pages"] == 2
    assert c["status"] == "supported"


def test_zz_prefix_matches_and_single_z_excluded():
    tagged = [
        make_tagged("r1", meta={"page_key": "a~ZZ", "page_name": "ZZPage"}),
        make_tagged("r2", meta={"page_key": "a~ZZZ", "page_name": "ZZZPage"}),
        make_tagged("r3", meta={"page_key": "a~Z", "page_name": "Zone"}),
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "persistence")
    assert c["observed"]["zzz_named_pages"] == 2
    assert c["status"] == "supported"


def test_recreations_separate_inventory():
    tagged = [
        make_tagged(
            "r1",
            meta={"page_key": "dse~Re", "page_name": "Rebuilt", "n_recreations": 2},
        )
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    c = claim(ledger, "persistence")
    assert c["observed"]["recreated_pages"] == 1
    assert c["observed"]["zzz_named_pages"] == 0
    assert c["status"] == "supported"


def test_ratio_and_malicious_specificity_always_insufficient():
    meta = {"page_key": "dse~ZZZ", "page_name": "ZZZPage", "n_recreations": 3}
    tagged = [
        make_tagged(f"r{i}", techniques=["swarm_directive"], meta=dict(meta)) for i in range(10)
    ]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    assert claim(ledger, "steering-specificity")["status"] == "insufficient_evidence"
    assert claim(ledger, "persistence-ratio")["status"] == "insufficient_evidence"


def _graph_with_prop(origin: dict, adopters: list[dict]) -> dict:
    return {
        "propagated_artifacts": 1,
        "propagations": [
            {
                "kind": "url",
                "artifact": "https://example.test/tool",
                "origin_msg": origin["msg_id"],
                "origin_actor": origin["actor"],
                "origin_time": origin["time"],
                "n_adopters": len(adopters),
                "n_posts": len(adopters),
                "adopters": adopters,
            }
        ],
    }


def test_propagation_nonexistent_reference_contradicted():
    tagged = [make_tagged("r1")]
    graph = _graph_with_prop(
        {"msg_id": "ghost", "actor": "AgentA", "time": "2026-06-16T10:00:00Z"}, []
    )
    ledger = build_claim_ledger(tagged, graph, [], CORPUS)
    c = claim(ledger, "propagation")
    assert c["status"] == "contradicted"
    assert c["observed"]["invalid_references"] == 1


def test_propagation_duplicate_id_contradicted():
    tagged = [make_tagged("r1", actor="AgentA"), make_tagged("r1", actor="AgentB")]
    graph = _graph_with_prop(
        {"msg_id": "r1", "actor": "AgentA", "time": "2026-06-16T10:00:00Z"}, []
    )
    ledger = build_claim_ledger(tagged, graph, [], CORPUS)
    assert claim(ledger, "propagation")["status"] == "contradicted"


@pytest.mark.parametrize(
    "field,value",
    [("actor", "WrongActor"), ("time", "2026-01-01T00:00:00Z")],
)
def test_propagation_mismatched_actor_or_time_contradicted(field, value):
    tagged = [make_tagged("r1", actor="AgentA", time="2026-06-16T10:00:00Z")]
    origin = {"msg_id": "r1", "actor": "AgentA", "time": "2026-06-16T10:00:00Z"}
    origin[field] = value
    ledger = build_claim_ledger(tagged, _graph_with_prop(origin, []), [], CORPUS)
    assert claim(ledger, "propagation")["status"] == "contradicted"


def test_propagation_invalid_reference_is_not_silently_validated():
    tagged = [
        make_tagged("r1", actor="AgentA", time="2026-06-16T10:00:00Z"),
        make_tagged("r2", actor="AgentB", time="2026-06-16T11:00:00Z"),
    ]
    graph = _graph_with_prop(
        {"msg_id": "r1", "actor": "AgentA", "time": "2026-06-16T10:00:00Z"},
        [{"msg_id": "r2", "actor": "AgentB", "time": "2026-06-16T11:00:00Z"}],
    )
    graph["propagations"].append(
        {
            "kind": "url",
            "artifact": "https://example.test/other",
            "origin_msg": "ghost",
            "origin_actor": "Nobody",
            "origin_time": "2026-06-16T12:00:00Z",
            "n_adopters": 0,
            "n_posts": 0,
            "adopters": [],
        }
    )
    ledger = build_claim_ledger(tagged, graph, [], CORPUS)
    c = claim(ledger, "propagation")
    assert c["status"] == "contradicted"
    assert c["observed"]["invalid_references"] == 1
    assert len(c["evidence"]) == 1


def test_propagation_valid_references_supported_causality_insufficient():
    tagged = [
        make_tagged("r1", actor="AgentA", time="2026-06-16T10:00:00Z"),
        make_tagged("r2", actor="AgentB", time="2026-06-16T11:00:00Z"),
    ]
    graph = _graph_with_prop(
        {"msg_id": "r1", "actor": "AgentA", "time": "2026-06-16T10:00:00Z"},
        [{"msg_id": "r2", "actor": "AgentB", "time": "2026-06-16T11:00:00Z"}],
    )
    ledger = build_claim_ledger(tagged, graph, [], CORPUS)
    c = claim(ledger, "propagation")
    assert c["status"] == "supported"
    assert c["observed"]["invalid_references"] == 0
    assert claim(ledger, "propagation-causality")["status"] == "insufficient_evidence"


def _report_inputs():
    scan = {
        "messages": 1,
        "scanned": 1,
        "flagged_ge_0.5": 0,
        "risk_levels": {},
        "technique_counts": {},
    }
    graph = {
        "coedit_edges": 0,
        "copy_edges": 0,
        "propagated_artifacts": 0,
        "propagations": [],
        "top_influencers": [],
    }
    istats = {"save_events": 0, "delete_events": 0, "revert_events": 0, "probe_events": 0}
    findings = [
        Finding(
            kind="deletion_evasion",
            title="t",
            detail="d",
            severity="info",
            stats={"zzz_named_pages": 1, "recreated_pages": 0},
        )
    ]
    return scan, graph, findings, istats


def test_journal_integration_records_all_statuses(tmp_path: Path):
    tagged = [make_tagged("r1", techniques=["swarm_directive"])]
    ledger = build_claim_ledger(tagged, {}, [], CORPUS)
    scan, graph, findings, istats = _report_inputs()
    paths = write_findings(
        tmp_path, scan, graph, findings, istats, corpus=CORPUS, claim_ledger=ledger
    )
    try:
        assert "claims" in paths and "journal" in paths
        report = json.loads(paths["json"].read_text())
        assert report["claim_ledger"]["corpus"] == CORPUS

        journal_lines = [json.loads(line) for line in paths["journal"].read_text().splitlines()]
        assert len(journal_lines) == len(ledger["claims"])
        assert {e["status"] for e in journal_lines} == {e["status"] for e in ledger["claims"]}

        claims_doc = json.loads(paths["claims"].read_text())
        assert claims_doc["accounting"]["normalized_records"] == 1
        assert "refusals" in claims_doc
        assert all(e["status"] != "supported" for e in claims_doc["refusals"])

        md = paths["md"].read_text()
        assert "## Claim checks" in md and "## Input accounting" in md

        deployed = paths.get("deployed_claims")
        if deployed is not None:
            assert deployed.name == f"claims-{CORPUS}.json"
            assert json.loads(deployed.read_text())["corpus"] == CORPUS
    finally:
        for key in ("deployed_claims", "deployed_dashboard"):
            deployed = paths.get(key)
            if deployed is not None and deployed.exists():
                deployed.unlink()


def test_write_findings_without_ledger_backwards_compatible(tmp_path: Path):
    scan, graph, findings, istats = _report_inputs()
    paths = write_findings(tmp_path, scan, graph, findings, istats, corpus=CORPUS)
    try:
        report = json.loads(paths["json"].read_text())
        assert "claim_ledger" not in report
        assert "claims" not in paths and "journal" not in paths
        assert not (tmp_path / "claims.json").exists()
        assert not (tmp_path / "journal.jsonl").exists()
    finally:
        deployed = paths.get("deployed_dashboard")
        if deployed is not None and deployed.exists():
            deployed.unlink()
