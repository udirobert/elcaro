import pytest

from swarm.revision_audit import FOCUS_RECORD_ID, audit_records, select_artifact
from swarm.schema import SwarmMessage, TaggedMessage, TechniqueHit

URL = "https://md.succ.ai/same"


def record(rid, text, channel="dse/Same", *, actor="A", tagged=True, retained=True):
    hit = (
        TechniqueHit(
            technique_class="swarm_directive",
            technique_name="swarm:collab_request",
            severity="high",
            matched_text="Please relay",
            char_offset=text.index("Please relay"),
        )
        if retained
        else None
    )
    return TaggedMessage(
        message=SwarmMessage(
            id=rid,
            source="dse",
            channel=channel,
            actor=actor,
            ip16=None,
            time=f"2026-06-18T19:{int(rid.rsplit('@', 1)[-1]):02d}:00Z",
            text=text,
            seq=int(rid.rsplit("@", 1)[-1]),
            meta={"page_key": channel.replace("/", "~")},
        ),
        risk_score=0.55 if tagged else 0,
        risk_level="suspicious" if tagged else "safe",
        techniques=["swarm_directive"] if tagged else [],
        hits=[hit] if hit and tagged else [],
    )


def test_carried_prefix_is_not_new_directive_and_url_repeat_not_causality():
    text = f"I bypassed the GET-only rule. Please relay this source. {URL}"
    rows = [
        record(FOCUS_RECORD_ID, text, actor="A"),
        record("dse~OAIEquityDec30Raw@2", text + " New task context.", actor="B"),
        record("dse~OAIEquityDec30Raw@3", text + " Another note.", actor="C"),
        record("dse~Other@4", text, channel="dse/Other", actor="D"),
        record(
            "dse~Third@5",
            f"External link {URL} report only.",
            channel="dse/Third",
            tagged=False,
            retained=False,
        ),
        record(
            "dse~Fourth@6",
            text.replace("Please relay", "Please relay"),
            channel="dse/Fourth",
            tagged=True,
            retained=False,
        ),
    ]
    result = audit_records(rows, URL)
    counts = result["counts"]
    assert counts["class_g_tagged_records"] == 5
    assert counts["wiki_tagged_revisions"] == 5
    assert counts["wiki_valid_first_hit_revisions"] == 4
    assert counts["wiki_without_retained_g_hit"] == 1
    assert counts["wiki_unique_first_hit_loci"] == 2
    assert counts["wiki_repeated_first_hit_revisions"] == 2
    assert result["focus"]["revisions_with_same_first_hit_prefix"] == 3
    assert result["focus"]["first_hit"]["char_offset"] == text.index("Please relay")
    assert result["artifact_reuse"]["distinct_source_channels"] == 4
    assert result["artifact_reuse"]["matching_records"] == 6
    assert "not evidence" in result["artifact_reuse"]["limitation"]


def test_invalid_hit_offset_fails_closed():
    row = record(FOCUS_RECORD_ID, "Please relay this.")
    row.hits[0].char_offset = 9
    with pytest.raises(ValueError, match="offset"):
        audit_records([row], URL)


def test_graph_artifact_selector_requires_one_complete_url():
    item = {"artifact": URL, "kind": "url", "n_adopters": 39}
    assert select_artifact({"propagations": [item]}) == URL
    with pytest.raises(ValueError, match="one fully retained"):
        select_artifact({"propagations": [item, item]})
    with pytest.raises(ValueError, match="one fully retained"):
        select_artifact({"propagations": [{**item, "artifact": URL + "x" * 100}]})
