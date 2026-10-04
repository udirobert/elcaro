from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from swarm.__main__ import _iter_tagged
from swarm.graph import _urls
from swarm.schema import TaggedMessage

FOCUS_RECORD_ID = "dse~OAIEquityDec30Raw@1"
ARTIFACT_HOST = "md.succ.ai"
ARTIFACT_LATER_ACTORS = 39


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _receipt(tagged: TaggedMessage) -> dict:
    m = tagged.message
    return {"id": m.id, "actor": m.actor, "time": m.time, "channel": m.channel}


def select_artifact(graph: dict) -> str:
    matches = [
        p
        for p in graph.get("propagations", [])
        if p.get("kind") == "url"
        and urlsplit(p.get("artifact", "")).hostname == ARTIFACT_HOST
        and p.get("n_adopters") == ARTIFACT_LATER_ACTORS
    ]
    if len(matches) != 1 or len(matches[0]["artifact"]) >= 100:
        raise ValueError("Expected one fully retained exact URL artifact")
    return matches[0]["artifact"]


def audit_records(tagged: list[TaggedMessage], artifact_url: str) -> dict:
    loci: dict[tuple, list[TaggedMessage]] = defaultdict(list)
    counts = Counter()
    matched_artifact: list[TaggedMessage] = []
    target = artifact_url.rstrip("/").lower()
    for record in tagged:
        m = record.message
        if target in {url.rstrip("/").lower() for url in _urls(m.text)}:
            matched_artifact.append(record)
        if "swarm_directive" not in record.techniques:
            continue
        counts["class_g_tagged_records"] += 1
        if not m.meta.get("page_key"):
            continue
        counts["wiki_tagged_revisions"] += 1
        hits = [h for h in record.hits if h.technique_class == "swarm_directive"]
        if not hits:
            counts["wiki_without_retained_g_hit"] += 1
            continue
        first = hits[0]
        offset = first.char_offset
        if (
            not isinstance(offset, int)
            or offset < 0
            or m.text[offset : offset + len(first.matched_text)].lower()
            != first.matched_text.lower()
        ):
            raise ValueError(f"Retained Class G offset does not resolve: {m.id}")
        prefix = m.text[: offset + len(first.matched_text)]
        key = (m.source, m.channel, first.technique_name, _digest(prefix))
        loci[key].append(record)
        counts["wiki_valid_first_hit_revisions"] += 1
    grouped = sorted(
        loci.values(), key=lambda group: (-len(group), min(r.message.id for r in group))
    )
    counts["wiki_unique_first_hit_loci"] = len(loci)
    counts["wiki_repeated_first_hit_revisions"] = sum(len(group) - 1 for group in loci.values())
    counts["wiki_loci_repeated_in_revisions"] = sum(len(group) > 1 for group in loci.values())
    if (
        counts["wiki_valid_first_hit_revisions"]
        != counts["wiki_unique_first_hit_loci"] + counts["wiki_repeated_first_hit_revisions"]
    ):
        raise ValueError("Revision audit accounting did not reconcile")
    focus = next(
        (group for group in loci.values() if any(r.message.id == FOCUS_RECORD_ID for r in group)),
        [],
    )
    focus.sort(key=lambda r: (r.message.time, r.message.seq, r.message.id))
    if focus:
        first_hit = next(h for h in focus[0].hits if h.technique_class == "swarm_directive")
        focus_case = {
            "first_hit": {
                "matched_text": first_hit.matched_text,
                "char_offset": first_hit.char_offset,
            },
            "revisions_with_same_first_hit_prefix": len(focus),
            "first": _receipt(focus[0]),
            "last": _receipt(focus[-1]),
            "example_revision_ids": [r.message.id for r in focus],
        }
    else:
        focus_case = None
    normalized = sorted(matched_artifact, key=lambda r: (r.message.time, r.message.id))
    channels: dict[tuple[str, str], TaggedMessage] = {}
    for record in normalized:
        channels.setdefault((record.message.source, record.message.channel), record)
    examples = sorted(channels.values(), key=lambda r: (r.message.time, r.message.id))[:6]
    return {
        "schema_version": 1,
        "method": "For each wiki revision with a retained first Class G hit, group identical "
        "source/channel/technique and SHA256 of text through the matched offset; repeated "
        "prefixes are carried-over first-hit loci, not independent authored directives.",
        "scope": "Records tagged by Class G, not unique directives. Missing retained hits are "
        "excluded from locus analysis. Different prefixes are not proven distinct intentions; "
        "same URL across channels does not prove reading, adoption, or causal influence.",
        "counts": dict(sorted(counts.items())),
        "focus": focus_case,
        "artifact_reuse": {
            "host": ARTIFACT_HOST,
            "matching_records": len(normalized),
            "distinct_actor_labels": len({r.message.actor for r in normalized}),
            "distinct_source_channels": len(channels),
            "earliest_observed": _receipt(normalized[0]) if normalized else None,
            "independent_channel_examples": [_receipt(r) for r in examples],
            "limitation": "A repeat in another channel is an observed appearance, not evidence "
            "that an actor read the earlier post or acted on its contents.",
        },
        "largest_repeated_loci": [
            {
                "first": _receipt(min(group, key=lambda r: (r.message.time, r.message.id))),
                "revisions": len(group),
                "actor_labels": len({r.message.actor for r in group}),
            }
            for group in grouped[:5]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit inherited Class G spans in wiki revisions")
    parser.add_argument("--data", type=Path, default=Path("data/swarm"))
    args = parser.parse_args()
    source = args.data / "out"
    graph = json.loads((source / "graph_stats.json").read_text())
    result = audit_records(list(_iter_tagged(source / "tagged.jsonl")), select_artifact(graph))
    (source / "revision-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    public = Path(__file__).resolve().parents[1] / "app" / "web" / "public" / "swarm"
    if public.exists():
        (public / "revision-audit.json").write_text(
            json.dumps(result, separators=(",", ":")) + "\n"
        )
    print("Revision audit written locally and as a bounded public summary")


if __name__ == "__main__":
    main()
