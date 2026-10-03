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

import collections
import hashlib
import re
from collections.abc import Iterable

from swarm.schema import Edge, SwarmMessage, TaggedMessage

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


def build_graph(
    tagged: Iterable[TaggedMessage],
) -> tuple[list[Edge], dict]:
    """Build provenance edges + propagation stats from the tagged stream."""
    msgs = [t.message for t in tagged if t.message.text]

    # ── co-edit edges ────────────────────────────────────────────────────
    by_channel: dict[str, list[SwarmMessage]] = collections.defaultdict(list)
    for m in msgs:
        by_channel[m.channel].append(m)
    coedit: dict[tuple[str, str, str], Edge] = {}
    for channel, ms in by_channel.items():
        ms.sort(key=lambda m: (m.time, m.seq))
        for j, b in enumerate(ms):
            seen_src: set[str] = set()
            for a in ms[:j]:
                if a.actor == b.actor or a.actor in seen_src:
                    continue
                seen_src.add(a.actor)
                key = (a.actor, b.actor, channel)
                e = coedit.get(key)
                if e is None:
                    coedit[key] = Edge(
                        src=a.actor,
                        dst=b.actor,
                        kind="coedit",
                        channel=channel,
                        time=b.time,
                        evidence_id=b.id,
                    )
                else:
                    e.weight += 1.0

    # ── artifact propagation (copy edges + patient zero) ────────────────
    # artifact key -> list of (time, actor, msg_id)
    artifact_posts: dict[str, list[tuple[str, str, str]]] = collections.defaultdict(list)
    artifact_preview: dict[str, str] = {}
    for m in msgs:
        artifacts: set[str] = set()
        for u in _urls(m.text):
            artifacts.add("url:" + u.rstrip("/").lower())
        for sh in _shingles(m.text):
            artifacts.add("sh:" + str(sh))
        for a in artifacts:
            artifact_posts[a].append((m.time, m.actor, m.id))
            if a.startswith("url:"):
                artifact_preview[a] = a[4:]
            elif a not in artifact_preview:
                artifact_preview[a] = m.text[:120].replace("\n", " ")

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
        if len(posts) > _MAX_DF:
            continue
        ordered = sorted(first_by_actor.items(), key=lambda kv: kv[1][0])
        origin_actor, (origin_t, origin_mid) = ordered[0]
        adopters = [{"actor": ac, "time": t, "msg_id": mid} for ac, (t, mid) in ordered[1:]]
        preview = artifact_preview.get(a, a)[:100]
        # Shingles from the same copied block share a preview — dedupe so one
        # propagated block counts once in the artifact table.
        if preview not in seen_previews:
            seen_previews.add(preview)
            propagations.append(
                {
                    "artifact": preview,
                    "kind": "url" if a.startswith("url:") else "shingle",
                    "origin_actor": origin_actor,
                    "origin_time": origin_t,
                    "origin_msg": origin_mid,
                    "n_posts": len(posts),
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
        "messages": len(msgs),
        "channels": len(by_channel),
        "coedit_edges": len(coedit),
        "copy_edges": len(copy_edges),
        "propagated_artifacts": len(propagations),
        "top_influencers": influence[:20],
        "propagations": propagations[:200],
    }
    return edges, stats
