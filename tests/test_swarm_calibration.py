"""Calibration-layer tests for the swarm provenance graph.

Synthetic streams built directly as TaggedMessage lists — build_graph never
reads detector fields, so no corpus fixtures or scan pass are needed.
"""

from swarm.graph import build_graph
from swarm.schema import SwarmMessage, TaggedMessage

TIP = "https://tips.example/r4-answers"


def _m(mid: str, actor: str, channel: str, time: str, text: str) -> SwarmMessage:
    return SwarmMessage(
        id=mid, source="t", channel=channel, actor=actor, ip16=None, time=time, text=text
    )


def _graph(msgs: list[SwarmMessage]):
    tagged = [
        TaggedMessage(message=m, risk_score=0.0, risk_level="safe", techniques=[], hits=[])
        for m in msgs
    ]
    return build_graph(lambda: iter(tagged))


def test_carrier_chain_reconstructs_hops():
    """A posts a URL in c1; B was in c1 and reposts in c2; C was in c2 and
    reposts in c3 — a two-hop chain, not two independent copies from A."""
    edges, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", f"results {TIP}"),
            _m("m2", "B", "c1", "2026-01-01T00:10:00Z", "ack"),
            _m("m3", "B", "c2", "2026-01-01T00:20:00Z", f"got {TIP}"),
            _m("m4", "C", "c2", "2026-01-01T00:30:00Z", "ack"),
            _m("m5", "C", "c3", "2026-01-01T00:40:00Z", f"fwd {TIP}"),
        ]
    )
    exposure = {(e.src, e.dst) for e in edges if e.kind == "copy_exposure"}
    assert ("A", "B") in exposure
    assert ("B", "C") in exposure  # hop 2 attributes to B, not origin A
    # naive copy edges still attribute every adopter to the earliest poster
    naive = {(e.src, e.dst) for e in edges if e.kind == "copy"}
    assert ("A", "C") in naive
    assert stats["max_chain_depth"] == 2
    cal = stats["calibration"]
    assert cal["naive_copy_calls"] == 2
    assert cal["carrier_visible_calls"] == 2
    assert cal["no_visible_carrier_calls"] == 0
    assert cal["carrier_coverage"] == 1.0
    # re-check list: 4 post-origin records in the suspect pool; adopters'
    # post-adoption output is B's m3 + C's m5 = 2 → 0.5
    prop = stats["propagations"][0]
    assert prop["suspect_pool_posts"] == 4
    assert prop["reached_posts"] == 2
    assert prop["recheck_fraction"] == 0.5
    assert prop["chain_depth"] == 2


def test_no_visible_carrier_counted():
    """An adopter who never shared a channel with an earlier poster gets a
    naive copy edge but no exposure edge — the unattributed residual."""
    edges, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", f"results {TIP}"),
            _m("m2", "B", "c1", "2026-01-01T00:10:00Z", "ack"),
            _m("m3", "B", "c2", "2026-01-01T00:20:00Z", f"got {TIP}"),
            _m("m4", "D", "c9", "2026-01-01T00:30:00Z", f"saw {TIP}"),
        ]
    )
    exposure = {(e.src, e.dst) for e in edges if e.kind == "copy_exposure"}
    assert exposure == {("A", "B")}
    naive = {(e.src, e.dst) for e in edges if e.kind == "copy"}
    assert ("A", "D") in naive
    cal = stats["calibration"]
    assert cal["carrier_visible_calls"] == 1
    assert cal["no_visible_carrier_calls"] == 1
    assert cal["carrier_coverage"] == 0.5


def test_exposure_window_requires_post_before_adoption():
    """Activity in the carrier channel *after* adoption is not a carrier —
    and the adoption post itself doesn't count (wiki revisions carry
    content forward, so adoption-in-channel is carry-forward-suspect)."""
    edges, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", f"results {TIP}"),
            _m("m2", "B", "c2", "2026-01-01T00:10:00Z", f"got {TIP}"),  # adopts first
            _m("m3", "B", "c1", "2026-01-01T00:20:00Z", "ack"),  # visits c1 later
            _m("m4", "C", "c1", "2026-01-01T00:25:00Z", "ack"),  # C exposed in c1
            _m("m5", "C", "c3", "2026-01-01T00:30:00Z", f"fwd {TIP}"),
        ]
    )
    exposure = {(e.src, e.dst) for e in edges if e.kind == "copy_exposure"}
    # B adopted before ever appearing in c1 → no carrier. C verifiably
    # posted in c1 between A's artifact post and C's adoption → carrier A.
    assert exposure == {("A", "C")}
    assert stats["calibration"]["no_visible_carrier_calls"] == 1


def test_coincidence_timestamp_shingle_excluded():
    """A pure timestamp/field-name shingle typed by three actors in disjoint
    channels is flagged coincidence-suspect and kept out of carrier counts."""
    body = "2026 03 24 10 00 00 record id"  # exactly one 8-gram shingle
    edges, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", body),
            _m("m2", "B", "c2", "2026-01-01T00:10:00Z", body),
            _m("m3", "C", "c3", "2026-01-01T00:20:00Z", body),
        ]
    )
    prop = next(p for p in stats["propagations"] if p["kind"] == "shingle")
    assert prop["coincidence_suspect"] == "timestamp_or_numeric"
    cal = stats["calibration"]
    assert cal["coincidence_excluded_calls"] == 2
    assert cal["coincidence_suspect_artifacts"] == {"timestamp_or_numeric": 1}
    assert cal["carrier_visible_calls"] == 0
    # naive edges still emitted — observed repetition is real, the *copy*
    # reading is what calibration withdraws
    assert stats["copy_edges"] > 0
    assert not [e for e in edges if e.kind == "copy_exposure"]


def test_field_name_shingle_excluded():
    body = "record id actor channel time text source kind"
    _, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", body),
            _m("m2", "B", "c2", "2026-01-01T00:10:00Z", body),
            _m("m3", "C", "c3", "2026-01-01T00:20:00Z", body),
        ]
    )
    prop = next(p for p in stats["propagations"] if p["kind"] == "shingle")
    assert prop["coincidence_suspect"] == "schema_field_names"


def test_prose_shingle_not_flagged():
    """Ordinary prose that propagates stays unflagged — the screen only
    catches near-pure independent-typing classes."""
    body = "please relay your r4 answer to the shared board"
    edges, stats = _graph(
        [
            _m("m1", "A", "c1", "2026-01-01T00:00:00Z", body),
            _m("m2", "B", "c1", "2026-01-01T00:10:00Z", "ack"),
            _m("m3", "B", "c2", "2026-01-01T00:20:00Z", body),
            _m("m4", "C", "c2", "2026-01-01T00:30:00Z", "ack"),
            _m("m5", "C", "c3", "2026-01-01T00:40:00Z", body),
        ]
    )
    props = [p for p in stats["propagations"] if p["kind"] == "shingle"]
    assert props and all(p["coincidence_suspect"] is None for p in props)
    exposure = {(e.src, e.dst) for e in edges if e.kind == "copy_exposure"}
    assert ("A", "B") in exposure and ("B", "C") in exposure
