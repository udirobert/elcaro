"""Provenance graph + epidemiology over the tagged swarm stream.

Edges:
- 'coedit'  — B edited a channel after A: B was exposed to A's prior content
              (wiki editing surfaces previous revisions — the documented
              mechanism by which techniques spread on the collusion wikis).
- 'copy'    — B reposted an artifact (URL or rare text shingle) that A posted
              earlier: direct evidence of technique/answer propagation
              across channels, the analogue of the 'zz' message-board reads
              METR had to trace by hand.

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


def _shingles(text: str) -> set[int]:
    words = _WORD_RE.findall(text[:_SHINGLE_BODY_CAP].lower())
    out: set[int] = set()
    for i in range(0, max(0, len(words) - _SHINGLE_N + 1)):
        h = hashlib.blake2b(" ".join(words[i : i + _SHINGLE_N]).encode(), digest_size=8).digest()
        out.add(int.from_bytes(h, "big"))
        if len(out) >= _SHINGLE_CAP_PER_MSG:
            break
    return out


def _urls(text: str) -> set[str]:
    return set(_URL_RE.findall(text))


def _msg_artifacts(text: str) -> list[bytes]:
    """Artifact keys for one message: b"U"+url / b"S"+8-byte shingle digest,
    sorted for deterministic downstream iteration."""
    artifacts: set[bytes] = set()
    for u in _urls(text):
        artifacts.add(b"U" + u.rstrip("/").lower().encode())
    for sh in _shingles(text):
        artifacts.add(b"S" + sh.to_bytes(8, "big"))
    return sorted(artifacts)


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
            for a in _msg_artifacts(m.text):
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

    artifact_posts: dict[bytes, list[tuple[str, str, str]]] = collections.defaultdict(list)
    artifact_preview: dict[bytes, str] = {}
    for t in tagged_factory():
        m = t.message
        if not m.text:
            continue
        for a in _msg_artifacts(m.text):
            if a not in survivors:
                continue
            artifact_posts[a].append((m.time, m.actor, m.id))
            if a[:1] == b"U":
                artifact_preview[a] = a[1:].decode()
            elif a not in artifact_preview:
                artifact_preview[a] = m.text[:120].replace("\n", " ")

    # ── co-edit edges ────────────────────────────────────────────────────
    coedit: dict[tuple[str, str, str], Edge] = {}
    for channel, recs in chan_slim.items():
        # (time, seq) sort; stable — ties keep stream order, matching the
        # original full-message sort.
        recs.sort(key=lambda r: (r[0], r[1]))
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

    copy_edges: dict[tuple[str, str], Edge] = {}
    propagations: list[dict] = []
    seen_previews: set[str] = set()
    for a, posts in artifact_posts.items():
        posts.sort()
        # distinct actors in order of first appearance
        first_by_actor: dict[str, tuple[str, str]] = {}
        for t, actor, mid in posts:
            first_by_actor.setdefault(actor, (t, mid))
        if len(first_by_actor) < _MIN_ADOPTERS + 1:
            continue
        ordered = sorted(first_by_actor.items(), key=lambda kv: kv[1][0])
        origin_actor, (origin_t, origin_mid) = ordered[0]
        adopters = [{"actor": ac, "time": t, "msg_id": mid} for ac, (t, mid) in ordered[1:]]
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

    edges = list(coedit.values()) + list(copy_edges.values())

    # per-actor influence: distinct downstream actors reachable via copy edges
    downstream: dict[str, set[str]] = collections.defaultdict(set)
    for e in copy_edges.values():
        downstream[e.src].add(e.dst)
    influence = sorted(((s, len(d)) for s, d in downstream.items()), key=lambda kv: -kv[1])

    stats = {
        "messages": n_msgs,
        "channels": len(chan_slim),
        "coedit_edges": len(coedit),
        "copy_edges": len(copy_edges),
        "propagated_artifacts": len(propagations),
        "top_influencers": influence[:20],
        "propagations": propagations[:200],
    }
    return edges, stats
