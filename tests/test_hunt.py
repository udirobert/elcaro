import json
from pathlib import Path
from types import SimpleNamespace

from swarm.__main__ import cmd_hunt
from swarm.hunt import build_hunt
from swarm.report import write_hunt_artifacts
from swarm.schema import SwarmMessage, TaggedMessage

CORPUS = "testcorpus"
URL = "https://example.test/tool"
D0 = "2026-06-01"
D1 = "2026-06-02"
D0B = "2026-06-04"


def make_tagged(
    rid: str,
    text: str,
    *,
    actor: str,
    source: str = "dse",
    channel: str = "chan",
    time: str,
) -> TaggedMessage:
    return TaggedMessage(
        message=SwarmMessage(
            id=rid,
            source=source,
            channel=channel,
            actor=actor,
            ip16=None,
            time=time,
            text=text,
            meta={},
        ),
        risk_score=0.0,
        risk_level="safe",
        techniques=[],
        hits=[],
    )


def disc_row(rid, actor, url=URL, hour=10, text=None, **kw):
    return make_tagged(
        rid,
        text if text is not None else f"ctx {actor} {rid} {url}",
        actor=actor,
        time=f"{D0}T{hour:02d}:00:00Z",
        **kw,
    )


def holdout_row(rid, actor, url=URL, text=None, hour=9, **kw):
    return make_tagged(
        rid,
        text if text is not None else f"holdout {actor} {rid} {url}",
        actor=actor,
        time=f"{D1}T{hour:02d}:00:00Z",
        **kw,
    )


def base_discovery(url=URL):
    return [disc_row(f"d{i}", actor, url=url) for i, actor in enumerate("ABC")]


def test_three_actors_same_hour_discovers_unreplicated_candidate():
    hunt = build_hunt(lambda: iter(base_discovery()), CORPUS)
    assert hunt["candidate_count"] == 1
    c = hunt["candidates"][0]
    assert c["status"] == "unreplicated_candidate"
    assert c["artifact"] == URL
    assert c["replicated_holdout_hours"] == 0
    assert c["holdout"] == []
    assert len(c["discovery"]) == 1
    assert c["discovery"][0]["distinct_actor_labels"] == 3


def test_new_bodies_in_holdout_replicate_observation():
    tagged = base_discovery() + [holdout_row(f"h{i}", actor) for i, actor in enumerate("DEF")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    c = hunt["candidates"][0]
    assert c["status"] == "replicated_observation"
    assert c["replicated_holdout_hours"] == 1
    assert hunt["replicated_observation_count"] == 1
    assert c["holdout"][0]["distinct_actor_labels"] == 3


def test_copied_discovery_bodies_excluded_from_holdout():
    holdout = [
        holdout_row(f"h{i}", actor, text=f"ctx {actor} d{i} {URL}") for i, actor in enumerate("ABC")
    ]
    tagged = base_discovery() + holdout
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    c = hunt["candidates"][0]
    assert c["status"] == "unreplicated_candidate"
    assert c["copied_discovery_text_records_excluded"] == 3
    assert c["holdout"] == []


def test_holdout_only_url_is_not_a_candidate():
    tagged = [holdout_row(f"h{i}", actor) for i, actor in enumerate("DEF")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_same_url_different_channel_or_source_cannot_confirm():
    tagged = base_discovery()
    tagged += [holdout_row(f"h{i}", actor, channel="other") for i, actor in enumerate("DEF")]
    tagged += [holdout_row(f"g{i}", actor, source="cross") for i, actor in enumerate("GHI")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    c = hunt["candidates"][0]
    assert c["status"] == "unreplicated_candidate"
    assert c["replicated_holdout_hours"] == 0


def test_offset_aware_time_uses_utc_day_and_hour():
    tagged = [
        make_tagged(
            f"d{i}",
            f"ctx {actor} {URL}",
            actor=actor,
            time="2026-06-02T00:30:00+02:00",
        )
        for i, actor in enumerate("ABC")
    ]
    tagged.append(make_tagged("n1", f"naive ctx {URL}", actor="N", time="2026-06-02T05:00:00"))
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 1
    c = hunt["candidates"][0]
    assert c["discovery"][0]["hour_utc"] == "2026-06-01T22:00:00+00:00"
    assert "2026-06-01" in hunt["discovery_days"]
    assert hunt["accounting"]["naive_time_assumed_utc_records"] == 1


def test_invalid_time_empty_fields_short_text_excluded():
    tagged = [
        make_tagged("r1", f"ctx {URL}", actor="A", time="2026-06-01"),
        make_tagged("r2", f"ctx {URL}", actor="A", time="not-a-time"),
        make_tagged("r3", f"ctx {URL}", actor="", time=f"{D0}T10:00:00Z"),
        make_tagged("r4", f"ctx {URL}", actor="A", channel="", time=f"{D0}T10:00:00Z"),
        make_tagged("r5", "short", actor="A", time=f"{D0}T10:00:00Z"),
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    a = hunt["accounting"]
    assert a["supplied_records"] == 5
    assert a["eligible_records"] == 0
    assert hunt["candidate_count"] == 0


def test_duplicate_id_rows_all_excluded():
    tagged = [
        disc_row("dup", "A"),
        disc_row("dup", "B"),
        disc_row("ok1", "C"),
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    a = hunt["accounting"]
    assert a["duplicate_id_records_excluded"] == 2
    assert a["eligible_records"] == 1
    assert hunt["candidate_count"] == 0


def test_same_url_twice_in_one_record_counts_once():
    tagged = [
        make_tagged(f"d{i}", f"see {URL} and {URL} again", actor=actor, time=f"{D0}T10:00:00Z")
        for i, actor in enumerate("ABC")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    c = hunt["candidates"][0]
    assert c["discovery"][0]["records"] == 3
    assert len(c["discovery"][0]["receipts"]) == 3


def test_one_actor_three_posts_cannot_discover():
    tagged = [
        make_tagged(f"d{i}", f"ctx{i} {URL}", actor="Solo", time=f"{D0}T10:0{i}:00Z")
        for i in range(3)
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_two_actors_cannot_discover():
    tagged = [disc_row(f"d{i}", actor) for i, actor in enumerate("AB")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_three_actors_spread_across_two_hours_cannot_discover():
    tagged = [disc_row("d0", "A"), disc_row("d1", "B"), disc_row("d2", "C", hour=11)]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_url_identity_preserves_path_case_lowercases_netloc():
    tagged = [
        make_tagged(
            f"d{i}",
            f"ctx {actor} https://EXAMPLE.test/Path",
            actor=actor,
            time=f"{D0}T10:00:00Z",
        )
        for i, actor in enumerate("ABC")
    ]
    tagged += [
        holdout_row(f"h{i}", actor, url="https://example.test/path")
        for i, actor in enumerate("DEF")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 1
    c = hunt["candidates"][0]
    assert c["artifact"] == "https://example.test/Path"
    assert c["status"] == "unreplicated_candidate"


def test_userinfo_url_skipped():
    tagged = [
        make_tagged(
            f"d{i}",
            f"ctx {actor} https://user:pw@example.test/x",
            actor=actor,
            time=f"{D0}T10:00:00Z",
        )
        for i, actor in enumerate("ABC")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_url_over_4096_chars_skipped():
    long_url = "https://example.test/" + "a" * 4100
    tagged = [
        make_tagged(f"d{i}", f"ctx {actor} {long_url}", actor=actor, time=f"{D0}T10:00:00Z")
        for i, actor in enumerate("ABC")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0


def test_url_after_text_cap_excluded_and_truncated_counted():
    text = "x" * 40_100 + " " + URL
    tagged = [make_tagged("r1", text, actor="A", time=f"{D0}T10:00:00Z")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0
    assert hunt["accounting"]["text_cap_records"] == 1


def test_url_ending_at_truncated_boundary_excluded():
    text = "x" * 39975 + " https://example.test/tool-and-more-beyond-the-cap"
    tagged = [
        make_tagged(f"d{i}", text, actor=actor, time=f"{D0}T10:00:00Z")
        for i, actor in enumerate("ABC")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 0
    assert hunt["accounting"]["text_cap_records"] == 3


def test_url_ending_before_cap_followed_by_space_retained():
    text = "x" * 39970 + " " + URL + " tail"
    tagged = [
        make_tagged(f"d{i}", text, actor=actor, time=f"{D0}T10:00:00Z")
        for i, actor in enumerate("ABC")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert hunt["candidate_count"] == 1
    assert hunt["accounting"]["text_cap_records"] == 3


def test_different_query_or_fragment_cannot_confirm():
    tagged = base_discovery(url="https://example.test/p?A=1#Frag")
    tagged += [
        holdout_row(f"h{i}", actor, url="https://example.test/p?a=1#frag")
        for i, actor in enumerate("DEF")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    c = hunt["candidates"][0]
    assert c["artifact"] == "https://example.test/p?A=1#Frag"
    assert c["status"] == "unreplicated_candidate"


def test_input_reorder_produces_identical_output():
    tagged = base_discovery() + [holdout_row(f"h{i}", actor) for i, actor in enumerate("DEF")]
    a = build_hunt(lambda: iter(tagged), CORPUS)
    b = build_hunt(lambda: iter(list(reversed(tagged))), CORPUS)
    assert a == b


def test_receipts_capped_at_five_earliest_all_records_counted():
    tagged = [
        make_tagged(f"d{i}", f"ctx {actor} {URL}", actor=actor, time=f"{D0}T10:{10 + i:02d}:00Z")
        for i, actor in enumerate("ABCDEF")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    seg = hunt["candidates"][0]["discovery"][0]
    assert seg["records"] == 6
    assert len(seg["receipts"]) == 5
    assert [r["record_id"] for r in seg["receipts"]] == ["d0", "d1", "d2", "d3", "d4"]


def test_empty_input_stable_output():
    hunt = build_hunt(lambda: iter([]), CORPUS)
    assert hunt["candidate_count"] == 0
    assert hunt["replicated_observation_count"] == 0
    assert hunt["candidates"] == []
    assert hunt["discovery_days"] == []
    assert hunt["holdout_days"] == []
    assert all(v == 0 for v in hunt["accounting"].values())


def test_factory_replayed_three_times():
    calls = []

    def factory():
        calls.append(1)
        return iter(base_discovery())

    build_hunt(factory, CORPUS)
    assert len(calls) == 3


def test_discovery_and_holdout_days_disjoint_utc_split():
    tagged = base_discovery()
    tagged += [disc_row("e1", "E", hour=12)]
    tagged = [t for t in tagged]
    tagged += [make_tagged("f1", f"ctx F {URL}", actor="F", time=f"{D0B}T10:00:00Z")]
    tagged += [holdout_row("h1", "H")]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    assert sorted(hunt["discovery_days"]) == [D0, D0B]
    assert hunt["holdout_days"] == [D1]
    assert not set(hunt["discovery_days"]) & set(hunt["holdout_days"])


def _fixture_jsonl(tagged) -> list[str]:
    return [
        json.dumps(
            {
                **{
                    "id": t.message.id,
                    "source": t.message.source,
                    "channel": t.message.channel,
                    "actor": t.message.actor,
                    "ip16": None,
                    "time": t.message.time,
                    "text": t.message.text,
                    "seq": 0,
                    "deleted": False,
                    "meta": {},
                },
                "risk_score": 0.0,
                "risk_level": "safe",
                "techniques": [],
                "hits": [],
            }
        )
        for t in tagged
    ]


def test_write_hunt_artifacts_journal_includes_all_candidates(tmp_path: Path):
    tagged = base_discovery() + [holdout_row(f"h{i}", actor) for i, actor in enumerate("DEF")]
    tagged += [
        disc_row(f"x{i}", actor, url="https://other.test/y", hour=12)
        for i, actor in enumerate("XYZ")
    ]
    hunt = build_hunt(lambda: iter(tagged), CORPUS)
    paths = write_hunt_artifacts(tmp_path, hunt, CORPUS)
    try:
        doc = json.loads(paths["hunt"].read_text())
        assert doc["candidate_count"] == 2
        lines = [json.loads(x) for x in paths["hunt_journal"].read_text().splitlines()]
        assert len(lines) == len(hunt["candidates"])
        assert {x["status"] for x in lines} == {
            "replicated_observation",
            "unreplicated_candidate",
        }
        deployed = paths.get("deployed_hunt")
        if deployed is not None:
            assert deployed.name == f"hunt-{CORPUS}.json"
            raw = deployed.read_text()
            assert raw.endswith("\n")
            index = json.loads(raw)
            assert index["corpus"] == CORPUS
            assert index["candidates"] == []
            assert index["candidate_count"] == 2
            assert [p["candidate_count"] for p in index["pages"]] == [2]
    finally:
        deployed = paths.get("deployed_hunt")
        if deployed is not None:
            for n in range(len(json.loads(deployed.read_text())["pages"])):
                page = deployed.parent / f"hunt-{CORPUS}-{n:04d}.json"
                if page.exists():
                    page.unlink()
            if deployed.exists():
                deployed.unlink()


def test_write_hunt_artifacts_paginates_deployed_pages(tmp_path: Path):
    candidates = [
        {
            "id": f"c{i}",
            "kind": "shared_url_hour",
            "source": "dse",
            "channel": "chan",
            "artifact": f"https://example.test/{i}",
            "assertion": "a",
            "status": "unreplicated_candidate",
            "discovery": [],
            "holdout": [],
            "replicated_holdout_hours": 0,
            "copied_discovery_text_records_excluded": 0,
            "eligible_discovery_records_in_channel": 0,
            "eligible_holdout_records_in_channel": 0,
            "legs": {},
            "refused_inference": "r",
        }
        for i in range(25)
    ]
    hunt = {
        "schema_version": 1,
        "corpus": CORPUS,
        "method": {},
        "accounting": {"supplied_records": 0},
        "discovery_days": [],
        "holdout_days": [],
        "candidate_count": 25,
        "replicated_observation_count": 0,
        "candidates": candidates,
    }
    paths = write_hunt_artifacts(tmp_path, hunt, CORPUS)
    try:
        index = json.loads(paths["deployed_hunt"].read_text())
        assert index["candidates"] == []
        assert index["candidate_count"] == 25
        assert index["discovery_days"] == []
        assert [p["candidate_count"] for p in index["pages"]] == [12, 12, 1]
        assert [p["src"] for p in index["pages"]] == [
            f"/swarm/hunt-{CORPUS}-{n:04d}.json" for n in range(3)
        ]
        loaded = []
        for p in index["pages"]:
            page_path = paths["deployed_hunt"].parent / p["src"].rsplit("/", 1)[-1]
            raw = page_path.read_text()
            assert raw.endswith("\n")
            page = json.loads(raw)
            assert page["schema_version"] == 1
            assert page["corpus"] == CORPUS
            loaded.extend(page["candidates"])
        assert loaded == candidates
    finally:
        deployed = paths.get("deployed_hunt")
        if deployed is not None:
            for n in range(3):
                page = deployed.parent / f"hunt-{CORPUS}-{n:04d}.json"
                if page.exists():
                    page.unlink()
            if deployed.exists():
                deployed.unlink()


def test_write_hunt_artifacts_empty_deploys_no_pages(tmp_path: Path):
    hunt = {
        "schema_version": 1,
        "corpus": CORPUS,
        "method": {},
        "accounting": {},
        "discovery_days": [],
        "holdout_days": [],
        "candidate_count": 0,
        "replicated_observation_count": 0,
        "candidates": [],
    }
    paths = write_hunt_artifacts(tmp_path, hunt, CORPUS)
    try:
        index = json.loads(paths["deployed_hunt"].read_text())
        assert index["pages"] == []
        assert not (paths["deployed_hunt"].parent / f"hunt-{CORPUS}-0000.json").exists()
        assert paths["hunt_journal"].read_text() == ""
    finally:
        deployed = paths.get("deployed_hunt")
        if deployed is not None and deployed.exists():
            deployed.unlink()


def test_cmd_hunt_reads_tagged_jsonl_and_writes(tmp_path: Path, monkeypatch, capsys):
    data = tmp_path / "corpus"
    out = data / "out"
    out.mkdir(parents=True)
    tagged = base_discovery() + [holdout_row(f"h{i}", actor) for i, actor in enumerate("DEF")]
    (out / "tagged.jsonl").write_text("\n".join(_fixture_jsonl(tagged)) + "\n")
    captured = {}

    def fake_write(out_dir, hunt, corpus):
        captured["hunt"] = hunt
        captured["corpus"] = corpus
        return {"hunt": out_dir / "hunt.json", "hunt_journal": out_dir / "hunt-journal.jsonl"}

    import swarm.__main__ as cli

    monkeypatch.setattr(cli, "write_hunt_artifacts", fake_write)
    cmd_hunt(SimpleNamespace(data=str(data)))
    assert captured["corpus"] == "collusion"
    assert captured["hunt"]["candidate_count"] == 1
    assert captured["hunt"]["replicated_observation_count"] == 1
    assert "candidates" in capsys.readouterr().out
