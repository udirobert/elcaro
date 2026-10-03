"""Integrity auditor — the forensic checks the slop-vestigation ran by hand.

Checks, each producing evidence-cited findings:

- deletion_evasion   — pages named to survive alphabetical deletion sweeps
                       (the documented 'ZZZ backup page' tactic) and pages
                       recreated after deletion (persistence).
- impersonation      — labels/bodies claiming moderator or admin authority.
- anon_activity      — unsigned edits whose /16 overlaps named-agent blocks
                       (agents dropping their handle).
- recon_probes       — the 101 probe events: timing and param families.
- agent_directives   — messages explicitly instructing other agents
                       (independent of detector hits — phrasing-based).
- tradecraft_mentions— heartbeat, PRNG-seed, sandbox-bypass vocabulary
                       density (documented behaviors, quantified).
- covert_channels    — rmn.re shortener + cross-site records summary.
"""

from __future__ import annotations

import collections
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from swarm.ingest import load_events, load_pages
from swarm.schema import Finding, TaggedMessage

_ZZZ_RE = re.compile(r"^z{2,}", re.IGNORECASE)
_MOD_RE = re.compile(r"admin|moderator|sysop|wiki.?admin|administrator", re.IGNORECASE)
_DIRECTIVE_RES = {
    "peer_address": re.compile(
        r"\b(other agents?|any agents?|all agents?|fellow agents?|agent(?:s)? reading|"
        r"to (?:the )?next agent|if you (?:see|are|find|read)|please (?:relay|share|append|post)|"
        r"we (?:need|must|should)|let'?s coordinate)\b",
        re.IGNORECASE,
    ),
    "coordination_norm": re.compile(
        r"\b(HOLD|VETO|OWNER|STOP)\b[:\s]|^#+\s*(HOLD|VETO|OWNER|STOP)\b", re.IGNORECASE
    ),
    "urgency": re.compile(r"\bURGENT\b|\bASAP\b|!!!+", re.IGNORECASE),
}
_TRADECRAFT_RES = {
    "heartbeat": re.compile(r"\bheartbeat\b|\bstill alive\b|\balive check\b|\bkeepalive\b", re.I),
    "prng_seed": re.compile(
        r"\bseed\b|\bprng\b|\brng\b|predict.{0,30}(next|future|question)", re.I
    ),
    "sandbox_bypass": re.compile(
        r"ssh tunnel|proxy|tor\b|bypass|circumvent|sandbox|escap(e|ing)|exfil", re.I
    ),
    "task_gaming": re.compile(
        r"\br[1-5]\b.{0,40}(due|timer|deadline|question|answer)|sequence", re.I
    ),
    "scorer_evasion": re.compile(
        r"scorer|evaluat|grad(e|ing)|transcript|log(s|ging)?|delete.{0,20}log", re.I
    ),
    "deletion_aware": re.compile(r"delet(ed|ion|ing)|backup|archiv|preserv|surviv", re.I),
}


def _cite(tm: TaggedMessage, extra: dict | None = None) -> dict[str, Any]:
    c = {
        "id": tm.message.id,
        "source": tm.message.source,
        "channel": tm.message.channel,
        "actor": tm.message.actor,
        "time": tm.message.time,
        "risk_score": tm.risk_score,
    }
    if extra:
        c.update(extra)
    return c


def deletion_evasion(tagged: Iterable[TaggedMessage], pages: dict) -> Finding:
    evasion_pages: dict[str, dict] = {}
    recreated: dict[str, dict] = {}
    for tm in tagged:
        m = tm.message
        name = (m.meta.get("page_name") or "").strip()
        if _ZZZ_RE.match(name):
            evasion_pages.setdefault(
                m.meta.get("page_key", name),
                {
                    "page": m.channel,
                    "name": name,
                    "actor": m.actor,
                    "first_seen": m.time,
                    "n_deletions": m.meta.get("n_deletions", 0),
                },
            )
        if m.meta.get("n_recreations", 0) > 0:
            recreated.setdefault(
                m.meta.get("page_key", name),
                {
                    "page": m.channel,
                    "name": name,
                    "n_recreations": m.meta["n_recreations"],
                    "n_deletions": m.meta.get("n_deletions", 0),
                    "labels": pages.get(m.meta.get("page_key"), {}).get("labels", []),
                },
            )
    evidence = sorted(evasion_pages.values(), key=lambda e: -e["n_deletions"])[:30]
    return Finding(
        kind="deletion_evasion",
        title="Deletion-evasion page naming + post-deletion recreation",
        detail=(
            f"{len(evasion_pages)} pages use ZZZ-style names placed to survive "
            f"alphabetical deletion sweeps (documented tactic: a backup page "
            f"named to sort last). {len(recreated)} pages were recreated after "
            f"deletion, indicating active persistence against moderator cleanup."
        ),
        severity="high" if evasion_pages else "info",
        evidence=evidence,
        stats={
            "zzz_named_pages": len(evasion_pages),
            "recreated_pages": len(recreated),
            "recreated": list(recreated.values())[:30],
        },
    )


def impersonation(tagged: Iterable[TaggedMessage]) -> Finding:
    """Labels or bodies claiming site/moderator authority."""
    label_suspects: dict[str, dict] = {}
    body_suspects: list[dict] = []
    for tm in tagged:
        m = tm.message
        if _MOD_RE.search(m.actor):
            label_suspects.setdefault(m.actor, {"actor": m.actor, "msgs": 0})
            label_suspects[m.actor]["msgs"] += 1
        for h in tm.hits:
            if "authority" in h.technique_class and _MOD_RE.search(h.matched_text + h.explanation):
                body_suspects.append(
                    _cite(
                        tm,
                        {
                            "matched_text": h.matched_text,
                            "char_offset": h.char_offset,
                        },
                    )
                )
                break
        else:
            # phrasing-based claim, independent of detector hits
            if re.search(
                r"\b(as |i am |this is )?(a )?(site )?(moderator|admin|sysop)\b", m.text, re.I
            ):
                body_suspects.append(_cite(tm, {"matched_text": m.text[:100]}))
    return Finding(
        kind="impersonation",
        title="Authority impersonation (moderator/admin claims)",
        detail=(
            f"{len(label_suspects)} actor handles resemble moderator/admin "
            f"names; {len(body_suspects)} messages carry body text claiming or "
            f"imitating site authority — matches the documented moderator-"
            f"impersonation tactic from the incident analysis."
        ),
        severity="high" if body_suspects or label_suspects else "info",
        evidence=list(label_suspects.values())[:20] + body_suspects[:30],
        stats={
            "suspect_labels": len(label_suspects),
            "authority_claim_messages": len(body_suspects),
        },
    )


def anon_activity(tagged: Iterable[TaggedMessage]) -> Finding:
    """Unsigned revisions whose /16 blocks overlap named-agent blocks."""
    named_ips: dict[str, set[str]] = collections.defaultdict(set)
    anon = []
    for tm in tagged:
        m = tm.message
        if m.actor.startswith("anon:") and m.ip16:
            anon.append(tm)
        elif m.ip16:
            named_ips[m.ip16].add(m.actor)
    overlap = [tm for tm in anon if tm.message.ip16 in named_ips]
    return Finding(
        kind="anon_activity",
        title="Unsigned edits from named-agent address blocks",
        detail=(
            f"{len(anon)} unsigned revisions; {len(overlap)} originate from /16 "
            f"blocks that also carry named-agent edits — consistent with agents "
            f"posting without a handle (deliberate or handle-loss)."
        ),
        severity="medium" if overlap else "info",
        evidence=[_cite(tm) for tm in overlap[:40]],
        stats={
            "unsigned_revisions": len(anon),
            "unsigned_from_named_blocks": len(overlap),
            "distinct_anon_ips": len({tm.message.ip16 for tm in anon}),
        },
    )


def recon_probes(events: list[dict]) -> Finding:
    probes = [e for e in events if e.get("event_type") == "probe"]
    fam = collections.Counter(e.get("param_family") for e in probes)
    ips = collections.Counter(e.get("ip16") for e in probes)
    return Finding(
        kind="recon_probes",
        title="Reconnaissance probes against the wiki surface",
        detail=(
            f"{len(probes)} probe events ({', '.join(f'{k}={v}' for k, v in fam.most_common())}) "
            f"across {len(ips)} /16 blocks — parameter-fuzzing behavior "
            f"consistent with the documented capability discovery (write via "
            f"GET, XSS attempts)."
        ),
        severity="medium" if probes else "info",
        evidence=[
            {
                "event_id": e["event_id"],
                "time": e.get("time"),
                "param_family": e.get("param_family"),
                "ip16": e.get("ip16"),
            }
            for e in probes[:40]
        ],
        stats={
            "probes": len(probes),
            "param_families": dict(fam),
            "ip16s": dict(ips.most_common(15)),
        },
    )


def agent_directives(tagged: Iterable[TaggedMessage]) -> Finding:
    """Messages phrased as instructions to other agents."""
    by_pattern: dict[str, list] = {k: [] for k in _DIRECTIVE_RES}
    for tm in tagged:
        for name, rx in _DIRECTIVE_RES.items():
            m = rx.search(tm.message.text)
            if m:
                by_pattern[name].append(
                    _cite(
                        tm,
                        {
                            "matched_text": m.group(0),
                            "char_offset": m.start(),
                            "snippet": tm.message.text[max(0, m.start() - 60) : m.start() + 80],
                        },
                    )
                )
    total = sum(len(v) for v in by_pattern.values())
    return Finding(
        kind="agent_directives",
        title="Agent-to-agent directive traffic",
        detail=(
            f"{total} messages phrase instructions at other agents "
            f"(peer-address={len(by_pattern['peer_address'])}, "
            f"coordination-norm={len(by_pattern['coordination_norm'])}, "
            f"urgency={len(by_pattern['urgency'])}) — the substrate of swarm "
            f"steering: requests to relay/share/append, proto-norms, and "
            f"urgency framing."
        ),
        severity="high" if total else "info",
        evidence={k: v[:30] for k, v in by_pattern.items()},
        stats={k: len(v) for k, v in by_pattern.items()},
    )


def tradecraft(tagged: Iterable[TaggedMessage]) -> Finding:
    hits: dict[str, list] = {k: [] for k in _TRADECRAFT_RES}
    for tm in tagged:
        for name, rx in _TRADECRAFT_RES.items():
            m = rx.search(tm.message.text)
            if m:
                hits[name].append(
                    _cite(
                        tm,
                        {
                            "matched_text": m.group(0),
                            "snippet": tm.message.text[max(0, m.start() - 60) : m.start() + 80],
                        },
                    )
                )
    return Finding(
        kind="tradecraft",
        title="Tradecraft vocabulary across the swarm",
        detail=(
            "Density of documented capability-discovery language: "
            + ", ".join(f"{k}={len(v)}" for k, v in hits.items())
            + ". Heartbeats (termination detection), seed/PRNG prediction, "
            "sandbox-bypass vocabulary, task-timing (R1–R5) gaming, scorer/log "
            "evasion, and deletion-awareness all appear in raw counts."
        ),
        severity="medium",
        evidence={k: v[:25] for k, v in hits.items()},
        stats={k: len(v) for k, v in hits.items()},
    )


def covert_channels(tagged: Iterable[TaggedMessage], data_dir: str | Path) -> Finding:
    short = [tm for tm in tagged if tm.message.source == "shortener"]
    xsite = [tm for tm in tagged if tm.message.source == "cross-site"]
    sites = collections.Counter(tm.message.channel for tm in xsite)
    flagged_short = [tm for tm in short if tm.risk_score >= 0.3]
    return Finding(
        kind="covert_channels",
        title="Off-wiki covert channels",
        detail=(
            f"{len(short)} rmn.re shortener links (a third-party URL shortener "
            f"used as dead-drop / tracking channel) and {len(xsite)} records "
            f"across {len(sites)} external sites — the same cross-channel "
            f"behavior the HF-incident investigators found late (property "
            f"fields, fabricated cached names, external services)."
        ),
        severity="high",
        evidence={
            "shortener_flagged": [_cite(tm) for tm in flagged_short[:30]],
            "top_sites": sites.most_common(20),
        },
        stats={
            "shortener_links": len(short),
            "cross_site_records": len(xsite),
            "distinct_sites": len(sites),
            "shortener_flagged": len(flagged_short),
        },
    )


def temporal_bursts(tagged: Iterable[TaggedMessage]) -> Finding:
    """Multi-actor same-hour bursts — co-activity signature."""
    buckets: dict[str, set[str]] = collections.defaultdict(set)
    for tm in tagged:
        if tm.message.time:
            buckets[tm.message.time[:13]].add(tm.message.actor)
    bursts = sorted(
        ((h, sorted(a)) for h, a in buckets.items() if len(a) >= 15),
        key=lambda kv: -len(kv[1]),
    )
    return Finding(
        kind="temporal_bursts",
        title="Co-activity bursts (many agents writing in the same hour)",
        detail=(
            f"{len(bursts)} hours with ≥15 distinct agents writing — peak "
            f"{len(bursts[0][1]) if bursts else 0} agents/hour. CIB-style "
            f"synchronized-activity signal: bursts mark coordinated pushes "
            f"or shared trigger events."
        ),
        severity="medium" if bursts else "info",
        evidence=[{"hour": h, "actors": a[:40], "n_actors": len(a)} for h, a in bursts[:20]],
        stats={
            "burst_hours": len(bursts),
            "peak_agents_per_hour": len(bursts[0][1]) if bursts else 0,
        },
    )


def run_all(tagged: Iterable[TaggedMessage], data_dir: str | Path) -> tuple[list[Finding], dict]:
    tagged = list(tagged)
    pages = load_pages(data_dir)
    events = load_events(data_dir)
    findings = [
        deletion_evasion(tagged, pages),
        impersonation(tagged),
        anon_activity(tagged),
        recon_probes(events),
        agent_directives(tagged),
        tradecraft(tagged),
        covert_channels(tagged, data_dir),
        temporal_bursts(tagged),
    ]
    deletions = [e for e in events if e.get("event_type") == "delete"]
    reverts = [e for e in events if e.get("event_type") == "revert"]
    stats = {
        "delete_events": len(deletions),
        "revert_events": len(reverts),
        "probe_events": sum(1 for e in events if e.get("event_type") == "probe"),
        "save_events": sum(1 for e in events if e.get("event_type") == "save"),
    }
    return findings, stats
