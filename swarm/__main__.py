"""Elcaro Swarm CLI.

Usage:
    python -m swarm all          # ingest → scan → graph → integrity → report
    python -m swarm ingest|scan|graph|integrity|report|claims   # individual stages

Data dir defaults to data/swarm/ (the collusion.wiki dump).
Outputs land in data/swarm/out/: tagged.jsonl, edges.jsonl, findings.{json,md}.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

from swarm.claims import build_claim_ledger
from swarm.graph import build_graph
from swarm.ingest import detect_corpus, load_messages
from swarm.integrity import run_all as integrity_run_all
from swarm.report import write_claim_artifacts, write_findings
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


def main() -> None:
    # Batch pipeline: ~180k dataclass/dict objects per corpus make cyclic-GC
    # full-heap scans dominate runtime. Structures are acyclic — refcounting
    # suffices, and the process is short-lived.
    gc.disable()
    ap = argparse.ArgumentParser(prog="swarm", description=__doc__)
    ap.add_argument(
        "command",
        choices=["ingest", "scan", "graph", "integrity", "report", "claims", "all"],
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
        "all": cmd_all,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
