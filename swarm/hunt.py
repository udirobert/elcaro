from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from swarm.graph import _URL_RE
from swarm.schema import TaggedMessage

MIN_ACTORS = 3
TEXT_CAP = 40_000
URL_CAP = 4096
RECEIPT_CAP = 5


def _time(value: str) -> datetime | None:
    try:
        if len(value) < 16 or value[10] not in ("T", " "):
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except (ValueError, AttributeError, OverflowError):
        return None


def _urls(text: str) -> dict[str, tuple[str, int]]:
    urls = {}
    for match in _URL_RE.finditer(text[:TEXT_CAP]):
        raw = match.group(0)
        if len(raw) > URL_CAP or (len(text) > TEXT_CAP and match.end() == TEXT_CAP):
            continue
        try:
            parts = urlsplit(raw)
            if not parts.hostname or parts.username is not None or parts.password is not None:
                continue
            url = urlunsplit(
                (
                    parts.scheme.lower(),
                    parts.netloc.lower(),
                    parts.path,
                    parts.query,
                    parts.fragment,
                )
            )
            urls.setdefault(url, (raw, match.start()))
        except ValueError:
            continue
    return urls


def build_hunt(
    tagged_factory: Callable[[], Iterable[TaggedMessage]], corpus: str
) -> dict[str, Any]:
    ids = Counter()
    accounting = Counter(
        {
            key: 0
            for key in (
                "supplied_records",
                "duplicate_id_records_excluded",
                "eligible_records",
                "ineligible_records",
                "text_cap_records",
                "naive_time_assumed_utc_records",
            )
        }
    )
    for t in tagged_factory():
        ids[t.message.id] += 1
        accounting["supplied_records"] += 1
    accounting["duplicate_id_records_excluded"] = sum(n for n in ids.values() if n > 1)
    groups: dict[tuple, dict] = {}
    discovery_hashes: dict[tuple, set[str]] = defaultdict(set)
    eligible_by_channel = Counter()
    days = [set(), set()]

    def rows():
        for t in tagged_factory():
            m = t.message
            if ids[m.id] != 1:
                continue
            stamp = _time(m.time)
            if stamp is None or not m.actor or not m.channel or len(m.text) < 24:
                continue
            day = stamp.date().isoformat()
            bucket = hashlib.sha256(day.encode()).digest()[0] % 2
            hour = stamp.replace(minute=0, second=0, microsecond=0).isoformat()
            body_hash = hashlib.sha256(m.text.encode()).hexdigest()
            yield t, stamp, day, bucket, hour, body_hash

    def insert(store, key, t, stamp, raw, offset):
        group = store.setdefault(key, {"records": 0, "actors": set(), "receipts": []})
        group["records"] += 1
        group["actors"].add(t.message.actor)
        receipt = {
            "record_id": t.message.id,
            "source": t.message.source,
            "channel": t.message.channel,
            "actor": t.message.actor,
            "time": stamp.isoformat(),
            "original_time": t.message.time,
            "matched_text": raw,
            "char_offset": offset,
        }
        group["receipts"].append(receipt)
        group["receipts"].sort(key=lambda r: (r["time"], r["record_id"]))
        del group["receipts"][RECEIPT_CAP:]

    for t, stamp, day, bucket, hour, body_hash in rows():
        m = t.message
        days[bucket].add(day)
        accounting["eligible_records"] += 1
        accounting["text_cap_records"] += len(m.text) > TEXT_CAP
        accounting["naive_time_assumed_utc_records"] += (
            _time(m.time) is not None
            and datetime.fromisoformat(m.time.replace("Z", "+00:00")).tzinfo is None
        )
        eligible_by_channel[(m.source, m.channel, bucket)] += 1
        if bucket:
            continue
        for url, (raw, offset) in _urls(m.text).items():
            identity = (m.source, m.channel, url)
            discovery_hashes[identity].add(body_hash)
            insert(groups, (*identity, hour), t, stamp, raw, offset)

    discovered: dict[tuple, list[tuple]] = defaultdict(list)
    for key, group in groups.items():
        if len(group["actors"]) >= MIN_ACTORS:
            discovered[key[:3]].append(key)
    holdout = {}
    copies = Counter()
    for t, stamp, _, bucket, hour, body_hash in rows():
        if not bucket:
            continue
        m = t.message
        for url, (raw, offset) in _urls(m.text).items():
            identity = (m.source, m.channel, url)
            if identity not in discovered:
                continue
            if body_hash in discovery_hashes[identity]:
                copies[identity] += 1
                continue
            insert(holdout, (*identity, hour), t, stamp, raw, offset)

    def segment(key, group):
        return {
            "hour_utc": key[3],
            "records": group["records"],
            "distinct_actor_labels": len(group["actors"]),
            "receipts": group["receipts"],
        }

    holdout_keys = defaultdict(list)
    for key in holdout:
        holdout_keys[key[:3]].append(key)
    entries = []
    for identity in sorted(discovered):
        source, channel, url = identity
        discovery_keys = sorted(discovered[identity])
        tested = sorted(holdout_keys[identity])
        replicated = [k for k in tested if len(holdout[k]["actors"]) >= MIN_ACTORS]
        candidate_id = hashlib.sha256("\0".join(identity).encode()).hexdigest()
        entries.append(
            {
                "id": candidate_id,
                "kind": "shared_url_hour",
                "source": source,
                "channel": channel,
                "artifact": url,
                "assertion": (
                    "The same URL occurs in records from at least three actor "
                    "labels within a UTC channel-hour."
                ),
                "status": "replicated_observation" if replicated else "unreplicated_candidate",
                "discovery": [segment(k, groups[k]) for k in discovery_keys],
                "holdout": [segment(k, holdout[k]) for k in tested],
                "replicated_holdout_hours": len(replicated),
                "copied_discovery_text_records_excluded": copies[identity],
                "eligible_discovery_records_in_channel": eligible_by_channel[(source, channel, 0)],
                "eligible_holdout_records_in_channel": eligible_by_channel[(source, channel, 1)],
                "legs": {
                    "grounding": "Unique input record IDs with exact URL-text offsets retained.",
                    "attribution": (
                        "Same source/channel and normalized UTC hour; actor "
                        "labels are not verified identities."
                    ),
                    "replication": (
                        "Same frozen URL/source/channel predicate passes in a holdout hour."
                        if replicated
                        else "No holdout hour satisfies the frozen three-actor "
                        "threshold after copied discovery text exclusion."
                    ),
                    "control": (
                        "Not established: holdout is unlabeled, not a benign negative control."
                    ),
                },
                "refused_inference": (
                    "Repeated URL observations do not establish coordination, "
                    "exposure, maliciousness, or causal influence."
                ),
            }
        )
    accounting["ineligible_records"] = (
        accounting["supplied_records"]
        - accounting["duplicate_id_records_excluded"]
        - accounting["eligible_records"]
    )
    return {
        "schema_version": 1,
        "corpus": corpus,
        "method": {
            "family": "Shared HTTP(S) URLs in fixed UTC channel-hours.",
            "discovery_rule": (
                "At least three distinct actor labels in one "
                "source/channel/hour; one occurrence per URL per record."
            ),
            "partition": (
                "sha256(UTC YYYY-MM-DD), first byte modulo 2: 0 discovery, 1 "
                "holdout; whole days remain disjoint across channels."
            ),
            "replication_rule": (
                "Freeze candidate URL/source/channel from discovery; require "
                "the same three-actor threshold in a holdout hour; exclude "
                "matching full-text SHA256 bodies seen in discovery for that "
                "URL/source/channel."
            ),
            "url_identity": (
                "Lowercase scheme and netloc only; preserve case-sensitive "
                "path, query and fragment. No network requests; URLs "
                "containing userinfo or longer than 4096 characters are "
                "excluded."
            ),
            "eligibility": (
                "Unique global record ID, nonempty actor/channel, parseable "
                "ISO time with at least minute precision, and at least 24 "
                "characters of text. Naive ISO times assume UTC. URL "
                "extraction covers the first 40000 characters only; matches "
                "touching a truncated boundary are excluded."
            ),
            "receipt_cap": RECEIPT_CAP,
            "limitation": (
                "Exploratory screening, not a significance test or causal "
                "finding. Exact-copy exclusion does not remove "
                "near-duplicates, common templates, shared actors, or "
                "correlated days. Every discovered candidate is retained; "
                "holdout supports repetition only."
            ),
        },
        "accounting": dict(sorted(accounting.items())),
        "discovery_days": sorted(days[0]),
        "holdout_days": sorted(days[1]),
        "candidate_count": len(entries),
        "replicated_observation_count": sum(
            e["status"] == "replicated_observation" for e in entries
        ),
        "candidates": entries,
    }
