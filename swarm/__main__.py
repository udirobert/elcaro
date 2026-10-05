"""Elcaro Swarm CLI.

Usage:
    python -m swarm all          # ingest → scan → graph → integrity → report
    python -m swarm ingest|scan|graph|integrity|report|claims|hunt|audit   # individual stages
    python -m swarm audit        # traceability report card (no scan needed)

Data dir defaults to data/swarm/ (the collusion.wiki dump).
Outputs land in data/swarm/out/: tagged.jsonl, edges.jsonl, findings.{json,md}.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

from core.canary import extract_canaries
from swarm.claims import build_claim_ledger
from swarm.graph import build_graph
from swarm.hunt import _time as _parse_time
from swarm.hunt import build_hunt
from swarm.ingest import detect_corpus, load_messages
from swarm.integrity import run_all as integrity_run_all
from swarm.report import write_claim_artifacts, write_findings, write_hunt_artifacts
from swarm.scan import scan_messages, summarize
from swarm.schema import Edge, Finding, SwarmMessage, TaggedMessage, TechniqueHit

DEFAULT_DATA = "data/swarm"
OUT = "out"


def _out_dir(data_dir: str) -> Path:
    p = Path(data_dir) / OUT
    p.mkdir(parents=True, exist_ok=True)
    return p


def _save_tagged(tagged: list[TaggedMessage], path: Path) -> None:
    with path.open("w") as f:
        for t in tagged:
            f.write(json.dumps(t.to_dict(), default=str) + "\n")


def _iter_tagged(path: Path):
    """Stream tagged records — a generator keeps the 180k+ corpus out of
    resident memory on RAM-constrained machines. Consumers that need a list
    (integrity, summarize) materialize internally."""
    for line in path.open():
        d = json.loads(line)
        msg = SwarmMessage(
            id=d["id"],
            source=d["source"],
            channel=d["channel"],
            actor=d["actor"],
            ip16=d.get("ip16"),
            time=d["time"],
            text=d["text"],
            seq=d.get("seq", 0),
            deleted=d.get("deleted", False),
            meta=d.get("meta", {}),
        )
        yield TaggedMessage(
            message=msg,
            risk_score=d["risk_score"],
            risk_level=d["risk_level"],
            techniques=d.get("techniques", []),
            hits=[TechniqueHit(**h) for h in d.get("hits", [])],
        )


def _save_edges(edges: list[Edge], path: Path) -> None:
    with path.open("w") as f:
        for e in edges:
            f.write(json.dumps(e.to_dict()) + "\n")


def cmd_ingest(args) -> None:
    msgs = load_messages(args.data)
    print(f"ingested {len(msgs)} messages")
    from collections import Counter

    print(Counter(m.source for m in msgs))


def cmd_scan(args) -> None:
    msgs = load_messages(args.data)
    tagged = scan_messages(msgs, workers=args.workers)
    path = _out_dir(args.data) / "tagged.jsonl"
    _save_tagged(tagged, path)
    print(f"scanned → {path}")
    print(json.dumps(summarize(tagged), indent=2, default=str)[:3000])


def cmd_graph(args) -> None:
    tagged_path = _out_dir(args.data) / "tagged.jsonl"
    edges, stats = build_graph(lambda: _iter_tagged(tagged_path))
    _save_edges(edges, _out_dir(args.data) / "edges.jsonl")
    (_out_dir(args.data) / "graph_stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(
        f"edges={len(edges)} coedit={stats['coedit_edges']} "
        f"copy={stats['copy_edges']} artifacts={stats['propagated_artifacts']}"
    )
    for p in stats["propagations"][:10]:
        print(
            f"  [{p['kind']}] {p['artifact'][:70]!r} origin={p['origin_actor']} "
            f"adopters={p['n_adopters']}"
        )


def cmd_integrity(args) -> None:
    findings, stats = integrity_run_all(
        _iter_tagged(_out_dir(args.data) / "tagged.jsonl"), args.data
    )
    print(json.dumps(stats, indent=2))
    for f in findings:
        print(f"[{f.severity.upper():6}] {f.title}")


def cmd_report(args) -> None:
    out = _out_dir(args.data)
    tagged_path = out / "tagged.jsonl"
    edges, graph_stats = build_graph(lambda: _iter_tagged(tagged_path))
    _save_edges(edges, out / "edges.jsonl")
    # Fresh stream per consumer — each re-reads tagged.jsonl rather than
    # holding the whole corpus resident.
    findings, istats = integrity_run_all(_iter_tagged(tagged_path), args.data)
    corpus = detect_corpus(args.data)
    ledger = build_claim_ledger(_iter_tagged(tagged_path), graph_stats, findings, corpus)
    paths = write_findings(
        out,
        summarize(_iter_tagged(tagged_path)),
        graph_stats,
        findings,
        istats,
        corpus=corpus,
        claim_ledger=ledger,
    )
    print(f"findings → {paths['md']} / {paths['json']}")


def cmd_all(args) -> None:
    msgs = load_messages(args.data)
    print(f"[1/4] ingest: {len(msgs)} messages")
    tagged = scan_messages(msgs, workers=args.workers)
    _save_tagged(tagged, _out_dir(args.data) / "tagged.jsonl")
    print(f"[2/4] scan: {sum(1 for t in tagged if t.risk_score >= 0.5)} flagged ≥0.5")
    edges, graph_stats = build_graph(lambda: iter(tagged))
    _save_edges(edges, _out_dir(args.data) / "edges.jsonl")
    print(
        f"[3/4] graph: {len(edges)} edges, "
        f"{graph_stats['propagated_artifacts']} propagated artifacts"
    )
    findings, istats = integrity_run_all(tagged, args.data)
    corpus = detect_corpus(args.data)
    ledger = build_claim_ledger(tagged, graph_stats, findings, corpus)
    paths = write_findings(
        _out_dir(args.data),
        summarize(tagged),
        graph_stats,
        findings,
        istats,
        corpus=corpus,
        claim_ledger=ledger,
    )
    print(f"[4/4] findings → {paths['md']}")
    for f in findings:
        print(f"   [{f.severity.upper():6}] {f.title}")


def cmd_claims(args) -> None:
    out = _out_dir(args.data)
    tagged_path = out / "tagged.jsonl"
    graph_stats = json.loads((out / "graph_stats.json").read_text())
    report = json.loads((out / "findings.json").read_text())
    findings = [Finding(**f) for f in report["findings"]]
    corpus = detect_corpus(args.data)
    ledger = build_claim_ledger(_iter_tagged(tagged_path), graph_stats, findings, corpus)
    paths = write_claim_artifacts(out, ledger, corpus)
    print(f"claims → {paths['claims']} / {paths['journal']}")
    for c in ledger["claims"]:
        print(f"   [{c['status']:20}] {c['id']}")


def cmd_audit(args) -> None:
    """Traceability report card — can this corpus support propagation claims
    at all? Runs the provenance graph on raw messages (detector fields are
    unused, so no scan pass is needed) and reports the observability
    ceiling: naive-vs-calibrated copy calls, carrier coverage, coincidence
    exclusions, chain depth — plus the logging gaps to fix next."""
    from datetime import datetime

    msgs = load_messages(args.data)
    tagged = [
        TaggedMessage(message=m, risk_score=0.0, risk_level="safe", techniques=[], hits=[])
        for m in msgs
    ]
    edges, stats = build_graph(lambda: iter(tagged))
    edge_kinds = {}
    for e in edges:
        edge_kinds[e.kind] = edge_kinds.get(e.kind, 0) + 1

    gaps = {
        "records": len(msgs),
        "empty_text": 0,
        "missing_actor": 0,
        "weak_actor_label": 0,  # anon:/unsigned@/user: fallback labels
        "unparseable_time": 0,
        "naive_time_assumed_utc": 0,
        "read_events": 0,
        "canary_tokens": 0,  # messages carrying an elc- trap-street token
    }
    for m in msgs:
        if not m.text:
            gaps["empty_text"] += 1
        if not m.actor:
            gaps["missing_actor"] += 1
        elif m.actor.startswith(("anon:", "unsigned@", "user:")):
            gaps["weak_actor_label"] += 1
        if _parse_time(m.time) is None:
            gaps["unparseable_time"] += 1
        elif datetime.fromisoformat(m.time.replace("Z", "+00:00")).tzinfo is None:
            gaps["naive_time_assumed_utc"] += 1
        if m.meta.get("kind") == "read":
            gaps["read_events"] += 1
        if m.text and extract_canaries(m.text):
            gaps["canary_tokens"] += 1

    cal = stats["calibration"]
    hints = []
    if not gaps["read_events"]:
        hints.append(
            "no read/view events — all trails are inferred from shared strings; "
            "logging read receipts (meta.kind='read') would make them exact"
        )
    if gaps["naive_time_assumed_utc"] or gaps["unparseable_time"]:
        hints.append("emit timezone-aware ISO-8601 timestamps")
    if gaps["weak_actor_label"]:
        hints.append("attach verified actor/model identity to records")
    if gaps["canary_tokens"]:
        hints.append(
            f"{gaps['canary_tokens']:,} records carry elc- canary tokens — "
            "those notice relays are exactly attributable to their issuing "
            "scan (resolve via the miner's /canary endpoint)"
        )
    cov = cal["carrier_coverage"]
    if cov is not None and cov < 0.5 and not gaps["canary_tokens"]:
        hints.append(
            "carrier coverage is low — most copying happens through channels "
            "this log doesn't capture; per-view canary tokens on served "
            "content would make copies attributable"
        )

    card = {
        "schema_version": 1,
        "corpus": detect_corpus(args.data),
        "records": gaps,
        "channels": stats["channels"],
        "propagated_artifacts": stats["propagated_artifacts"],
        "copy_calls": cal,
        "edge_kinds": edge_kinds,
        "max_chain_depth": stats["max_chain_depth"],
        "recheck_median": stats["recheck_median"],
        "logging_gaps": hints,
        "scope": (
            "Observability audit of the supplied records — how much copying is "
            "traceable from what was logged. Not a measure of actual copying."
        ),
    }
    path = _out_dir(args.data) / "traceability.json"
    path.write_text(json.dumps(card, indent=2, default=str) + "\n")

    print(f"traceability report card — {card['corpus']} ({args.data})")
    print(
        f"  records      {gaps['records']:,} "
        f"({gaps['records'] - gaps['empty_text']:,} text-bearing, "
        f"{stats['channels']:,} channels)"
    )
    print(
        f"  propagations {stats['propagated_artifacts']:,} artifacts"
        + (
            f" · coincidence-suspect: {cal['coincidence_suspect_artifacts']}"
            if cal["coincidence_suspect_artifacts"]
            else ""
        )
    )
    print(
        f"  copy calls   {cal['naive_copy_calls']:,} naive → "
        f"{cal['carrier_visible_calls']:,} carrier-visible"
        + (f" ({cov:.0%} coverage)" if cov is not None else "")
        + f" · {cal['no_visible_carrier_calls']:,} no visible carrier"
        + f" · {cal['coincidence_excluded_calls']:,} coincidence-excluded"
    )
    print(f"  chains       deepest reconstructed chain: {stats['max_chain_depth']} hops")
    print(f"  re-check     median reached-output fraction: {stats['recheck_median']}")
    for h in hints:
        print(f"  gap          {h}")
    print(f"  → {path}")


def cmd_hunt(args) -> None:
    out = _out_dir(args.data)
    tagged_path = out / "tagged.jsonl"
    corpus = detect_corpus(args.data)
    hunt = build_hunt(lambda: _iter_tagged(tagged_path), corpus)
    paths = write_hunt_artifacts(out, hunt, corpus)
    print(
        f"hunt → {paths['hunt']} / {paths['hunt_journal']} "
        f"({hunt['candidate_count']} candidates, "
        f"{hunt['replicated_observation_count']} replicated observations)"
    )
    for c in hunt["candidates"]:
        print(f"   [{c['status']:24}] {c['artifact'][:70]}")


def main() -> None:
    # Batch pipeline: ~180k dataclass/dict objects per corpus make cyclic-GC
    # full-heap scans dominate runtime. Structures are acyclic — refcounting
    # suffices, and the process is short-lived.
    gc.disable()
    ap = argparse.ArgumentParser(prog="swarm", description=__doc__)
    ap.add_argument(
        "command",
        choices=[
            "ingest",
            "scan",
            "graph",
            "integrity",
            "report",
            "claims",
            "hunt",
            "audit",
            "all",
        ],
    )
    ap.add_argument("--data", default=DEFAULT_DATA, help="corpus directory")
    ap.add_argument("--workers", type=int, default=None, help="scan workers")
    args = ap.parse_args()
    {
        "ingest": cmd_ingest,
        "scan": cmd_scan,
        "graph": cmd_graph,
        "integrity": cmd_integrity,
        "report": cmd_report,
        "claims": cmd_claims,
        "hunt": cmd_hunt,
        "audit": cmd_audit,
        "all": cmd_all,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
