"""Run the Elcaro detection engine across a swarm message stream.

Every revision body / cross-site record is scanned as inter-agent content
(ContentType.CHAT_MESSAGE). Output keeps the forensic contract: per-message
verdict plus evidence-cited hits (matched text + char offset), so every claim
in the findings write-up links back to a concrete corpus location.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor

from core import ContentType, IpiDetectionEngine, ScanRequest
from swarm.schema import SwarmMessage, TaggedMessage, TechniqueHit

_TEXT_CAP = 40_000  # chars per message scan; longer bodies are truncated w/ note
_MAX_HITS = 8  # evidence hits retained per message


def _scan_one(args: tuple[str, str]) -> dict:
    """Worker: scan one (msg_id, text). Engine built once per process."""
    global _ENGINE  # noqa: PLW0603 — per-process singleton
    if "_ENGINE" not in globals():
        _ENGINE = IpiDetectionEngine(
            classifier=None, serv_reasoner=None, jev_reasoner=None, laya_reasoner=None
        )
    msg_id, text = args
    resp = _ENGINE.scan(
        ScanRequest(content=text[:_TEXT_CAP], content_type=ContentType.CHAT_MESSAGE)
    )
    hits = [
        TechniqueHit(
            technique_class=ind.technique_class.value,
            technique_name=ind.technique_name,
            severity=ind.severity.value,
            matched_text=ind.evidence.matched_text,
            char_offset=ind.evidence.char_offset,
            explanation=ind.explanation,
        ).to_dict()
        for ind in resp.indicators[:_MAX_HITS]
    ]
    return {
        "id": msg_id,
        "risk_score": resp.risk_score,
        "risk_level": resp.risk_level.value,
        "techniques": [t.value for t in resp.flagged_techniques],
        "hits": hits,
        "truncated": len(text) > _TEXT_CAP,
    }


def scan_messages(
    messages: Iterable[SwarmMessage],
    workers: int | None = None,
    min_text: int = 24,
) -> list[TaggedMessage]:
    """Scan every message with enough text to judge. Returns tagged stream
    aligned with input order."""
    msgs = list(messages)
    scannable = [m for m in msgs if len(m.text) >= min_text]
    verdicts: dict[str, dict] = {}
    jobs = [(m.id, m.text) for m in scannable]
    if workers is None:
        workers = max(1, (os.cpu_count() or 4) - 1)
    if workers > 1 and len(jobs) > 200:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for v in ex.map(_scan_one, jobs, chunksize=64):
                verdicts[v["id"]] = v
    else:
        for j in jobs:
            v = _scan_one(j)
            verdicts[v["id"]] = v

    out: list[TaggedMessage] = []
    for m in msgs:
        v = verdicts.get(m.id, {})
        out.append(
            TaggedMessage(
                message=m,
                risk_score=v.get("risk_score", 0.0),
                risk_level=v.get("risk_level", "safe"),
                techniques=v.get("techniques", []),
                hits=[TechniqueHit(**h) for h in v.get("hits", [])],
            )
        )
    return out


def summarize(tagged: Iterable[TaggedMessage]) -> dict:
    """Corpus-level detection stats for the report."""
    import collections

    t = list(tagged)
    by_level = collections.Counter(x.risk_level for x in t)
    by_class = collections.Counter()
    for x in t:
        by_class.update(x.techniques)
    flagged = [x for x in t if x.risk_score >= 0.5]
    directive_flagged = [x for x in t if "swarm_directive" in x.techniques]
    by_actor = collections.Counter(x.message.actor for x in flagged)
    by_day = collections.Counter(x.message.time[:10] for x in flagged)
    return {
        "messages": len(t),
        "scanned": sum(1 for x in t if len(x.message.text) >= 24),
        "flagged_ge_0.5": len(flagged),
        "directive_flagged": len(directive_flagged),
        "risk_levels": dict(by_level),
        "technique_counts": dict(by_class.most_common()),
        "top_flagged_actors": by_actor.most_common(15),
        "flagged_by_day": dict(sorted(by_day.items())),
    }
