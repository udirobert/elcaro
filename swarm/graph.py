"""Provenance graph + epidemiology over the tagged swarm stream.

Edges:
- 'coedit'  — B edited a channel after A: B was exposed to A's prior content
              (wiki editing surfaces previous revisions — the documented
              mechanism by which techniques spread on the collusion wikis).
- 'copy'    — B reposted an artifact (URL or rare text shingle) that A posted
              earlier: naive same-string attribution of technique/answer
              propagation across channels. Kept for continuity, but an
              adopter may have typed the string independently.
- 'copy_exposure' — the calibrated form of 'copy': B's adoption has a
              visible carrier — B posted in the channel where an earlier
              actor posted the artifact, between that post and B's adoption.
              The edge src is the most recent carrier B was exposed to, so
              propagation chains reconstruct hop-by-hop instead of
              collapsing every adopter onto the earliest poster.

Calibration: same string ≠ copied. Agents type timestamps, schema field
names, and template boilerplate independently — the FP class that sinks
naive matching. Every origin→adopter attribution lands in exactly one
bucket: coincidence_excluded (artifact matches an independent-typing
class), carrier_visible (a copy_exposure edge exists), or
no_visible_carrier. carrier_coverage — the share of non-coincidence calls
with a visible carrier — bounds how much of the corpus's copying is even
traceable from this log substrate.

Patient-zero scoring: for every propagated artifact, the earliest poster is
the candidate source; distinct adopting actors = R (spread). This is the
cheap operationalization of rumor-centrality/source-localization on the
observed diffusion subgraph.
"""

from __future__ import annotations

import bisect
import collections
import hashlib
import os
import re
import sqlite3
import statistics
import tempfile
from collections.abc import Callable, Iterable

from swarm.schema import Edge, TaggedMessage

_WORD_RE = re.compile(r"[a-z0-9_]+")
_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>,]+")
_SHINGLE_N = 8
_SHINGLE_BODY_CAP = 20_000
_SHINGLE_CAP_PER_MSG = 400
_MIN_ADOPTERS = 2
_MAX_DF = 60  # shingles more common than this are boilerplate, not signal
_RAW_TEXT_CAP = 500_000  # surviving shingle surface forms kept for coincidence screening

_NUM_TOKEN_RE = re.compile(r"[0-9][0-9:.\-/]*")
_HEX_TOKEN_RE = re.compile(r"[0-9a-f]{8,}")
_DATE_WORDS = frozenset(
    {
        "utc",
        "gmt",
        "am",
        "pm",
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "january",
        "february",
        "march",
        "april",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)
_FIELD_WORDS = frozenset(
    {
        "id",
        "ids",
        "time",
        "timestamp",
        "created",
        "created_at",
        "updated",
        "updated_at",
        "actor",
        "agent",
        "channel",
        "room",
        "room_id",
        "source",
        "text",
        "content",
        "message",
        "msg",
        "record",
        "record_id",
        "seq",
        "name",
        "user",
        "speaker",
        "speaker_type",
        "date",
        "url",
        "kind",
        "type",
        "meta",
        "key",
        "value",
        "page",
        "page_id",
        "wiki",
        "rev",
        "rev_id",
        "version",
        "status",
        "role",
    }
)


def _shingles(text: str) -> dict[int, str]:
    """8-gram digests → first raw surface form (kept so propagated artifacts
    can be screened for independent-typing coincidence classes)."""
    words = _WORD_RE.findall(text[:_SHINGLE_BODY_CAP].lower())
    out: dict[int, str] = {}
    for i in range(0, max(0, len(words) - _SHINGLE_N + 1)):
        raw = " ".join(words[i : i + _SHINGLE_N])
        h = int.from_bytes(hashlib.blake2b(raw.encode(), digest_size=8).digest(), "big")
        if h not in out:
            out[h] = raw
        if len(out) >= _SHINGLE_CAP_PER_MSG:
            break
    return out


def _urls(text: str) -> set[str]:
    return set(_URL_RE.findall(text))


def _msg_artifacts(text: str) -> list[tuple[bytes, str]]:
    """(artifact key, raw surface) pairs for one message: b"U"+normalized
    url / b"S"+8-byte shingle digest, sorted by key for deterministic
    downstream iteration."""
    artifacts: dict[bytes, str] = {}
    for u in _urls(text):
        nu = u.rstrip("/").lower()
        artifacts.setdefault(b"U" + nu.encode(), nu)
    for sh, raw in _shingles(text).items():
        artifacts.setdefault(b"S" + sh.to_bytes(8, "big"), raw)
    return sorted(artifacts.items())


def _coincidence_class(raw: str) -> str | None:
    """Shingle surface forms agents type independently — timestamps, schema
    field names, identifier runs. Conservative: only fires when all but two
    words of the shingle fit the class."""
    words = raw.split()
    n = len(words)
    if n < 6:
        return None
    if sum(1 for w in words if _NUM_TOKEN_RE.fullmatch(w) or w in _DATE_WORDS) >= n - 2:
        return "timestamp_or_numeric"
    if sum(1 for w in words if _HEX_TOKEN_RE.fullmatch(w)) >= n - 2:
        return "identifier_run"
    if sum(1 for w in words if w in _FIELD_WORDS) >= n - 2:
        return "schema_field_names"
    return None


def build_graph(
    tagged_factory: Callable[[], Iterable[TaggedMessage]],
) -> tuple[list[Edge], dict]:
    """Build provenance edges + propagation stats from the tagged stream.

    Two streaming passes over `tagged_factory()` so a large corpus (AI
    Village: 183k msgs ≈ ~1GB of texts, 10M+ distinct artifact keys) never
    materializes in RAM — on an 8GB machine an in-RAM keyspace page-faults
    into livelock. Pass A counts artifact document-frequency in a
    disk-backed sqlite table (8-byte BLOB keys); pass B re-streams and
    collects posts/previews only for keys that can propagate.
    """
    tmp = tempfile.NamedTemporaryFile(prefix="elcaro-swarm-", suffix=".db", delete=False)
    tmp.close()
    chan_slim: dict[str, list[tuple[str, int, str, str]]] = collections.defaultdict(list)
    n_msgs = 0
    try:
        con = sqlite3.connect(tmp.name)
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.execute("CREATE TABLE ac (k BLOB PRIMARY KEY, df INTEGER NOT NULL) WITHOUT ROWID")
        cur = con.cursor()
        batch: list[tuple[bytes]] = []
        for t in tagged_factory():
            m = t.message
            if not m.text:
                continue
            n_msgs += 1
            chan_slim[m.channel].append((m.time, m.seq, m.actor, m.id))
            for a, _raw in _msg_artifacts(m.text):
                batch.append((a,))
            if len(batch) >= 50_000:
                cur.executemany(
                    "INSERT INTO ac(k,df) VALUES(?,1) ON CONFLICT(k) DO UPDATE SET df=df+1",
                    batch,
                )
                con.commit()
                batch.clear()
        if batch:
            cur.executemany(
                "INSERT INTO ac(k,df) VALUES(?,1) ON CONFLICT(k) DO UPDATE SET df=df+1",
                batch,
            )
            con.commit()
        # A propagation needs an origin + ≥_MIN_ADOPTERS distinct adopters,
        # so df < _MIN_ADOPTERS+1 can never produce one; df > _MAX_DF is
        # boilerplate. Everything else is worth a second-pass collection.
        survivors = dict(
            cur.execute(
                "SELECT k, df FROM ac WHERE df >= ? AND df <= ?",
                (_MIN_ADOPTERS + 1, _MAX_DF),
            )
        )
        con.close()
    finally:
        os.unlink(tmp.name)

    artifact_posts: dict[bytes, list[tuple[str, str, str, str]]] = collections.defaultdict(list)
    artifact_preview: dict[bytes, str] = {}
    artifact_text: dict[bytes, str] = {}
    for t in tagged_factory():
        m = t.message
        if not m.text:
            continue
        for a, raw in _msg_artifacts(m.text):
            if a not in survivors:
                continue
            artifact_posts[a].append((m.time, m.actor, m.id, m.channel))
            if a[:1] == b"U":
                artifact_preview[a] = raw
            elif a not in artifact_preview:
                artifact_preview[a] = m.text[:120].replace("\n", " ")
            if a[:1] == b"S" and a not in artifact_text and len(artifact_text) < _RAW_TEXT_CAP:
                artifact_text[a] = raw

    # Exposure indexes. "B had a visible carrier for artifact X" asks whether
    # B posted in the channel where the artifact appeared, between that post
    # and B's adoption. chan_slim holds text-bearing messages only — none of
    # these corpora have read/view events, so this is exposure opportunity,
    # not observed reading.
    chan_actor_times: dict[str, dict[str, list[str]]] = {}
    actor_times: dict[str, list[str]] = collections.defaultdict(list)
    all_times: list[str] = []

    # ── co-edit edges ────────────────────────────────────────────────────
    coedit: dict[tuple[str, str, str], Edge] = {}
    for channel, recs in chan_slim.items():
        # (time, seq) sort; stable — ties keep stream order, matching the
        # original full-message sort.
        recs.sort(key=lambda r: (r[0], r[1]))
        per_actor: dict[str, list[str]] = collections.defaultdict(list)
        for time, _, actor, _mid in recs:
            per_actor[actor].append(time)
            actor_times[actor].append(time)
            all_times.append(time)
        chan_actor_times[channel] = dict(per_actor)
        # Closed form rather than the naive pairwise scan: weight(a→b) is the
        # count of b's messages after a's first appearance, so first-seen
        # indices + binary search give every edge in O(actors²·log n) —
        # O(msgs×actors) per message still blows up on few-channel corpora.
        first_seen: dict[str, int] = {}
        msg_idx: dict[str, list[int]] = collections.defaultdict(list)
        for i, (_, _, actor, _) in enumerate(recs):
            first_seen.setdefault(actor, i)
            msg_idx[actor].append(i)
        for b, idxs in msg_idx.items():
            for a, a_first in first_seen.items():
                if a == b:
                    continue
                j = bisect.bisect_right(idxs, a_first)
                w = len(idxs) - j
                if w <= 0:
                    continue
                ft, _, _, fid = recs[idxs[j]]
                e = Edge(
                    src=a,
                    dst=b,
                    kind="coedit",
                    channel=channel,
                    time=ft,
                    evidence_id=fid,
                )
                e.weight = float(w)
                coedit[(a, b, channel)] = e

    for times in actor_times.values():
        times.sort()
    all_times.sort()

    copy_edges: dict[tuple[str, str], Edge] = {}
    exposure_edges: dict[tuple[str, str], Edge] = {}
    propagations: list[dict] = []
    seen_previews: set[str] = set()
    n_screened = n_visible = n_no_carrier = n_coincidence = 0
    coincidence_artifacts: collections.Counter = collections.Counter()
    max_chain_depth = 0
    recheck_fractions: list[float] = []
    for a, posts in artifact_posts.items():
        posts.sort()
        # distinct actors in order of first appearance
        first_by_actor: dict[str, tuple[str, str]] = {}
        for t, actor, mid, _ch in posts:
            first_by_actor.setdefault(actor, (t, mid))
        if len(first_by_actor) < _MIN_ADOPTERS + 1:
            continue
        ordered = sorted(first_by_actor.items(), key=lambda kv: kv[1][0])
        origin_actor, (origin_t, origin_mid) = ordered[0]
        adopters = [{"actor": ac, "time": t, "msg_id": mid} for ac, (t, mid) in ordered[1:]]
        coinc = _coincidence_class(artifact_text.get(a, "")) if a[:1] == b"S" else None
        if a[:1] == b"S":
            n_screened += 1
        if coinc:
            n_coincidence += len(adopters)
            coincidence_artifacts[coinc] += 1

        # Carrier resolution over adopters in time order. A carrier for B is
        # an earlier poster P of the artifact whose channel B verifiably
        # posted in, inside (P's artifact post, B's adoption). Coincidence-
        # class artifacts skip resolution — a shared-channel hit on a string
        # everyone types is itself coincidence.
        depths = {origin_actor: 0}
        visible = 0
        artifact_depth = 0
        for ad in adopters:
            if coinc:
                continue
            t_b = ad["time"]
            carrier: tuple[str, str, str] | None = None
            for t_p, actor_p, _mid_p, ch_p in posts:
                if t_p >= t_b:
                    break
                if actor_p == ad["actor"]:
                    continue
                times = chan_actor_times.get(ch_p, {}).get(ad["actor"])
                if not times:
                    continue
                i = bisect.bisect_right(times, t_p)
                if (
                    i < len(times)
                    and times[i] < t_b
                    and (carrier is None or (t_p, actor_p) > (carrier[0], carrier[1]))
                ):
                    carrier = (t_p, actor_p, ch_p)
            if carrier is None:
                n_no_carrier += 1
                continue
            n_visible += 1
            visible += 1
            _t_c, c_actor, c_chan = carrier
            # Unattributed carriers (no depth) count as chain starts — depth
            # measures visible hops, so a broken link doesn't inflate it.
            depths[ad["actor"]] = depths.get(c_actor, 0) + 1
            artifact_depth = max(artifact_depth, depths[ad["actor"]])
            key = (c_actor, ad["actor"])
            e = exposure_edges.get(key)
            if e is None:
                exposure_edges[key] = Edge(
                    src=c_actor,
                    dst=ad["actor"],
                    kind="copy_exposure",
                    channel=c_chan,
                    time=ad["time"],
                    evidence_id=ad["msg_id"],
                )
            else:
                # Keep the most recent supporting pair as the citation.
                e.weight += 1.0
                e.channel = c_chan
                e.time = ad["time"]
                e.evidence_id = ad["msg_id"]
        max_chain_depth = max(max_chain_depth, artifact_depth)

        # Re-check-list math: an artifact first posted at origin_t puts every
        # later message in the suspect pool; tracing shrinks the audit surface
        # to the adopters' own post-adoption output.
        suspect_pool = len(all_times) - bisect.bisect_right(all_times, origin_t)
        reached = sum(
            len(actor_times[ad["actor"]]) - bisect.bisect_left(actor_times[ad["actor"]], ad["time"])
            for ad in adopters
        )
        recheck = reached / suspect_pool if suspect_pool else None
        if recheck is not None and not coinc:
            recheck_fractions.append(recheck)

        preview = artifact_preview.get(a, "")[:100]
        # Shingles from the same copied block share a preview — dedupe so one
        # propagated block counts once in the artifact table.
        if preview not in seen_previews:
            seen_previews.add(preview)
            propagations.append(
                {
                    "artifact": preview,
                    "kind": "url" if a[:1] == b"U" else "shingle",
                    "origin_actor": origin_actor,
                    "origin_time": origin_t,
                    "origin_msg": origin_mid,
                    "n_posts": survivors[a],
                    "n_adopters": len(adopters),
                    "adopters": adopters[:25],
                    "coincidence_suspect": coinc,
                    "carrier_visible_adopters": visible,
                    "chain_depth": artifact_depth,
                    "reached_posts": reached,
                    "suspect_pool_posts": suspect_pool,
                    "recheck_fraction": round(recheck, 4) if recheck is not None else None,
                }
            )
        for ad in adopters:
            key = (origin_actor, ad["actor"])
            e = copy_edges.get(key)
            if e is None:
                copy_edges[key] = Edge(
                    src=origin_actor,
                    dst=ad["actor"],
                    kind="copy",
                    channel="corpus",
                    time=ad["time"],
                    evidence_id=ad["msg_id"],
                )
            else:
                e.weight += 1.0

    propagations.sort(key=lambda p: (-p["n_adopters"], -p["n_posts"]))

    edges = list(coedit.values()) + list(copy_edges.values()) + list(exposure_edges.values())

    # per-actor influence: distinct downstream actors reachable via copy edges
    downstream: dict[str, set[str]] = collections.defaultdict(set)
    for e in copy_edges.values():
        downstream[e.src].add(e.dst)
    influence = sorted(((s, len(d)) for s, d in downstream.items()), key=lambda kv: -kv[1])

    traceable = n_visible + n_no_carrier
    stats = {
        "messages": n_msgs,
        "channels": len(chan_slim),
        "coedit_edges": len(coedit),
        "copy_edges": len(copy_edges),
        "copy_exposure_edges": len(exposure_edges),
        "propagated_artifacts": len(propagations),
        "max_chain_depth": max_chain_depth,
        "recheck_median": statistics.median(recheck_fractions) if recheck_fractions else None,
        "top_influencers": influence[:20],
        "propagations": propagations[:200],
        "calibration": {
            # Every origin→adopter attribution lands in exactly one bucket.
            "naive_copy_calls": n_visible + n_no_carrier + n_coincidence,
            "coincidence_excluded_calls": n_coincidence,
            "coincidence_suspect_artifacts": dict(sorted(coincidence_artifacts.items())),
            "carrier_visible_calls": n_visible,
            "no_visible_carrier_calls": n_no_carrier,
            "carrier_coverage": n_visible / traceable if traceable else None,
            "propagated_shingles_screened": n_screened,
            "shingle_surface_forms_retained": len(artifact_text),
            "note": (
                "Shared strings are not proof of copying. carrier_coverage is "
                "the observability ceiling for this corpus — attributions "
                "without a visible carrier may be real copying through "
                "unlogged channels or independent typing."
            ),
        },
    }
    return edges, stats
