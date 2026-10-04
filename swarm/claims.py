from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from swarm.integrity import _TRADECRAFT_RES, _ZZZ_RE
from swarm.schema import TaggedMessage


def build_claim_ledger(
    tagged: Iterable[TaggedMessage], graph: dict, findings: list, corpus: str
) -> dict[str, Any]:
    records = list(tagged)
    ids = Counter(t.message.id for t in records)
    by_id = {t.message.id: t for t in records}
    eligible = [t for t in records if len(t.message.text) >= 24]
    techniques = Counter(k for t in eligible for k in set(t.techniques))
    finding_stats = {f.kind: f.stats for f in findings}

    def receipt(t: TaggedMessage, matched: str = "", offset: int | None = None) -> dict:
        return {
            "record_id": t.message.id,
            "actor": t.message.actor,
            "source": t.message.source,
            "time": t.message.time,
            "matched_text": matched[:160],
            "char_offset": offset,
        }

    def rate_group(rows: list, predicate) -> dict:
        matches = [t for t in rows if predicate(t)]
        return {
            "matches": len(matches),
            "eligible_records": len(rows),
            "rate": len(matches) / len(rows) if rows else None,
            "receipts": [receipt(t) for t in sorted(matches, key=lambda t: t.message.id)[:5]],
        }

    def reference_rates(predicate, rows: list) -> dict:
        groups = [[], []]
        for t in rows:
            identity = t.message.actor.encode()
            groups[hashlib.sha256(identity).digest()[0] % 2].append(t)
        return {
            "method": "sha256(actor), first byte modulo 2; bucket 0 vs bucket 1",
            "selection": (
                "Fixed actor-disjoint descriptive split; not selected by detector outcome."
            ),
            "analysis_set": rate_group(groups[0], predicate),
            "reference_set": rate_group(groups[1], predicate),
            "limitation": (
                "Both sets are unlabeled. Shared text and interacting actors can cross sets. "
                "These are not benign controls, a precision estimate, or independent replication."
            ),
        }

    def directive(t: TaggedMessage) -> bool:
        return "swarm_directive" in t.techniques

    directives = [t for t in eligible if directive(t)]
    scorer_rx = _TRADECRAFT_RES["scorer_evasion"]
    scorer = [t for t in records if scorer_rx.search(t.message.text)]
    entries = []

    def add(key, assertion, status, check, observed, evidence, limitations, reference=None):
        entries.append(
            {
                "id": key,
                "assertion": assertion,
                "status": status,
                "check": check,
                "observed": observed,
                "evidence": evidence,
                "limitations": limitations,
                "reference": reference,
            }
        )

    directive_receipts = []
    for t in sorted(directives, key=lambda t: t.message.id)[:5]:
        hit = next((h for h in t.hits if h.technique_class == "swarm_directive"), None)
        directive_receipts.append(
            receipt(t, hit.matched_text if hit else "", hit.char_offset if hit else None)
        )
    add(
        "steering",
        "Class G tags occur in the scanned corpus.",
        "supported" if directives else "insufficient_evidence",
        (
            "Count records at least 24 characters long tagged swarm_directive; "
            "count each class once per record."
        ),
        {
            "matches": len(directives),
            "eligible_records": len(eligible),
            "technique_counts": dict(sorted(techniques.items())),
            "rank": 1 + sum(n > len(directives) for n in techniques.values())
            if directives
            else None,
        },
        directive_receipts,
        (
            "A tag is a rule match, not proof of malicious intent. Largest class does not "
            "mean most accurate class. Retained indicator evidence is capped at eight hits "
            "per record."
        ),
        reference_rates(directive, eligible),
    )
    add(
        "steering-specificity",
        "Class G distinguishes malicious steering from benign collaboration.",
        "insufficient_evidence",
        (
            "Requires independently labeled malicious and benign examples, "
            "not another unlabeled corpus."
        ),
        {},
        [],
        "No false-positive rate or detector precision is established by this ledger.",
    )

    props = graph.get("propagations", [])
    resolved = []
    invalid = 0
    for p in props:
        origin = by_id.get(p.get("origin_msg"))
        valid = bool(
            origin
            and ids[p["origin_msg"]] == 1
            and origin.message.actor == p.get("origin_actor")
            and origin.message.time == p.get("origin_time")
        )
        for adopter in p.get("adopters", []):
            row = by_id.get(adopter.get("msg_id"))
            valid = valid and bool(
                row
                and ids[adopter["msg_id"]] == 1
                and row.message.actor == adopter.get("actor")
                and row.message.time == adopter.get("time")
            )
        if valid:
            resolved.append(
                {
                    "artifact": p["artifact"],
                    "origin": receipt(origin),
                    "adopters": p.get("n_adopters"),
                    "retained_adopter_receipts": p.get("adopters", [])[:5],
                }
            )
        else:
            invalid += 1
    add(
        "propagation",
        "Reported shared-artifact source and adopter references resolve to the normalized record.",
        "contradicted" if invalid else "supported" if props else "insufficient_evidence",
        (
            "Resolve retained graph record IDs uniquely and compare actor/time metadata. "
            "Does not independently recompute artifact extraction."
        ),
        {
            "reported_artifacts": graph.get("propagated_artifacts"),
            "checked_artifacts": len(props),
            "invalid_references": invalid,
        },
        resolved[:5],
        (
            "Earliest observed poster is not proven origin. Repeated text or URLs do not "
            "establish exposure, adoption, or causal influence. Graph output and retained "
            "adopters may be capped."
        ),
    )
    add(
        "propagation-causality",
        "The shared toolkit caused downstream behavior.",
        "insufficient_evidence",
        "Requires observed reads/actions or independently corroborated behavioral links.",
        {},
        [],
        "Shared-artifact timing alone cannot establish causation or a true patient-zero.",
    )

    pages = {}
    for t in records:
        key = t.message.meta.get("page_key")
        if key:
            pages.setdefault(key, t)
    zzz = [
        t for t in pages.values() if _ZZZ_RE.match((t.message.meta.get("page_name") or "").strip())
    ]
    recreated = [t for t in pages.values() if t.message.meta.get("n_recreations", 0) > 0]
    add(
        "persistence",
        "Observed pages include ZZZ-style names and recorded post-deletion recreation.",
        "supported" if zzz or recreated else "insufficient_evidence" if pages else "not_applicable",
        (
            "Deduplicate revision page_key; match names beginning with at least two Zs "
            "(case-insensitive ^z{2,}) and n_recreations > 0 metadata test."
        ),
        {
            "eligible_pages": len(pages),
            "zzz_named_pages": len(zzz),
            "recreated_pages": len(recreated),
            "reported_zzz_named_pages": finding_stats.get("deletion_evasion", {}).get(
                "zzz_named_pages"
            ),
            "reported_recreated_pages": finding_stats.get("deletion_evasion", {}).get(
                "recreated_pages"
            ),
        },
        [
            receipt(t)
            | {"page_key": t.message.meta["page_key"], "page_name": t.message.meta.get("page_name")}
            for t in sorted(zzz, key=lambda t: t.message.id)[:5]
        ],
        (
            "Page metadata is source-reported. Naming alone does not prove intent; "
            "recreation alone does not establish moderation effectiveness. No page metadata "
            "exists in the chat-only corpus."
        ),
    )
    add(
        "persistence-ratio",
        "Persistence beat moderation by approximately 12:1.",
        "insufficient_evidence",
        "Requires a defined numerator, denominator, population, and outcome measure.",
        {},
        [],
        (
            "The existing naming, recreation, deletion and revert counts do not define "
            "this ratio. Withdrawn, not proven false."
        ),
    )

    scorer_receipts = []
    for t in sorted(scorer, key=lambda t: t.message.id)[:5]:
        match = scorer_rx.search(t.message.text)
        scorer_receipts.append(receipt(t, match.group(0), match.start()))
    add(
        "evaluation-vocabulary",
        "The scorer/evaluation/logging vocabulary rule matches records.",
        "supported" if scorer else "insufficient_evidence",
        (
            "Apply the existing tradecraft scorer_evasion regex to full normalized text; "
            "one match-count per record, unlike the capped engine scan."
        ),
        {"matches": len(scorer), "eligible_records": len(records)},
        scorer_receipts,
        (
            "Vocabulary mentions do not prove awareness of an actual evaluator, evasion, "
            "or deceptive intent."
        ),
        reference_rates(lambda t: bool(scorer_rx.search(t.message.text)), records),
    )

    add(
        "evaluation-awareness",
        "Vocabulary matches demonstrate awareness of an actual evaluator or deceptive intent.",
        "insufficient_evidence",
        (
            "Requires context-specific corroboration beyond the "
            "scorer/evaluation/logging vocabulary rule."
        ),
        {},
        [],
        "Ordinary discussion of logs, transcripts, or grading can match the same rule.",
    )

    def valid_time(value: str) -> bool:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except (ValueError, AttributeError):
            return False

    accounting = {
        "normalized_records": len(records),
        "unique_record_ids": len(ids),
        "duplicate_record_ids": sum(n - 1 for n in ids.values()),
        "scan_eligible_records": len(eligible),
        "skipped_short_records": len(records) - len(eligible),
        "scan_truncated_records": sum(len(t.message.text) > 40000 for t in eligible),
        "empty_text_records": sum(not t.message.text for t in records),
        "missing_or_unparseable_time_records": sum(not valid_time(t.message.time) for t in records),
        "by_source": dict(sorted(Counter(t.message.source for t in records).items())),
        "scope": (
            "Normalized supplied records only. Does not measure raw parse rejects, "
            "deduplicated input rows, unseen activity, or incident capture fraction. "
            "Ingest parse errors abort rather than being silently counted as success."
        ),
    }
    return {
        "schema_version": 1,
        "corpus": corpus,
        "accounting": accounting,
        "claims": entries,
        "refusals": [e for e in entries if e["status"] != "supported"],
    }
