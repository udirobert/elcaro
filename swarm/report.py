"""Findings report assembly — findings.json + findings.md.

Every finding carries evidence citations (corpus id + matched text + char
offset) so a reviewer can verify any claim against the raw dump in one hop —
the property the slop-vestigation lacked.
"""

from __future__ import annotations

import json
from pathlib import Path

from swarm.dashboard import write_dashboard

CORPUS_LABELS = {
    "collusion": (
        "collusion.wiki dump (German Wiki incident) + rmn.re shortener + cross-site records"
    ),
    "aivillage": "AI Village transcript export (huggingface aidigestorg/ai-village)",
}


def write_findings(
    out_dir: str | Path,
    scan_summary: dict,
    graph_stats: dict,
    findings: list,
    integrity_stats: dict,
    tagged_path: str | Path | None = None,
    edges_path: str | Path | None = None,
    corpus: str = "collusion",
    claim_ledger: dict | None = None,
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    corpus_label = CORPUS_LABELS.get(corpus, corpus)

    report = {
        "corpus": corpus_label,
        "scan": scan_summary,
        "graph": {k: v for k, v in graph_stats.items() if k != "propagations"}
        | {"propagations": graph_stats.get("propagations", [])[:50]},
        "integrity_events": integrity_stats,
        "findings": [f.to_dict() for f in findings],
    }
    if claim_ledger is not None:
        report["claim_ledger"] = claim_ledger
    fj = out / "findings.json"
    fj.write_text(json.dumps(report, indent=2, default=str))

    md = _render_md(
        scan_summary, graph_stats, findings, integrity_stats, corpus_label, claim_ledger
    )
    fm = out / "findings.md"
    fm.write_text(md)
    dash = write_dashboard(out, scan_summary, graph_stats, findings, integrity_stats, corpus_label)
    paths = {"json": fj, "md": fm, "dashboard": dash}
    if claim_ledger is not None:
        paths.update(write_claim_artifacts(out, claim_ledger, corpus))
    # Keep the deployed snapshot in sync — /swarm serves the copy under
    # app/web/public/swarm/. Collusion keeps the canonical dashboard.html
    # (the /swarm page narrates those findings); other corpora get a
    # corpus-suffixed file. Skip silently when the web app isn't checked out.
    web_public = Path(__file__).resolve().parents[1] / "app" / "web" / "public" / "swarm"
    if web_public.parent.parent.exists():
        web_public.mkdir(parents=True, exist_ok=True)
        deployed = web_public / (
            "dashboard.html" if corpus == "collusion" else f"dashboard-{corpus}.html"
        )
        deployed.write_text(dash.read_text())
        paths["deployed_dashboard"] = deployed
    return paths


def write_claim_artifacts(out_dir: str | Path, claim_ledger: dict, corpus: str) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    cj = out / "claims.json"
    cj.write_text(json.dumps(claim_ledger, indent=2, default=str))
    paths["claims"] = cj

    jl = out / "journal.jsonl"
    with jl.open("w") as f:
        for entry in claim_ledger.get("claims", []):
            f.write(json.dumps(entry, default=str) + "\n")
    paths["journal"] = jl

    web_public = Path(__file__).resolve().parents[1] / "app" / "web" / "public" / "swarm"
    if web_public.parent.parent.exists():
        web_public.mkdir(parents=True, exist_ok=True)
        deployed = web_public / f"claims-{corpus}.json"
        deployed.write_text(json.dumps(claim_ledger, default=str, separators=(",", ":")) + "\n")
        paths["deployed_claims"] = deployed
    return paths


HUNT_PAGE_SIZE = 12


def write_hunt_artifacts(out_dir: str | Path, hunt: dict, corpus: str) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    hj = out / "hunt.json"
    hj.write_text(json.dumps(hunt, indent=2, default=str))
    paths["hunt"] = hj

    jl = out / "hunt-journal.jsonl"
    with jl.open("w") as f:
        for entry in hunt.get("candidates", []):
            f.write(json.dumps(entry, default=str) + "\n")
    paths["hunt_journal"] = jl

    web_public = Path(__file__).resolve().parents[1] / "app" / "web" / "public" / "swarm"
    if web_public.parent.parent.exists():
        web_public.mkdir(parents=True, exist_ok=True)
        candidates = hunt.get("candidates", [])
        index = {k: v for k, v in hunt.items() if k != "candidates"}
        index["candidates"] = []
        index["pages"] = []
        for i in range(0, len(candidates), HUNT_PAGE_SIZE):
            n = i // HUNT_PAGE_SIZE
            chunk = candidates[i : i + HUNT_PAGE_SIZE]
            page_name = f"hunt-{corpus}-{n:04d}.json"
            page = {"schema_version": 1, "corpus": corpus, "candidates": chunk}
            (web_public / page_name).write_text(
                json.dumps(page, default=str, separators=(",", ":")) + "\n"
            )
            index["pages"].append({"src": f"/swarm/{page_name}", "candidate_count": len(chunk)})
        deployed = web_public / f"hunt-{corpus}.json"
        deployed.write_text(json.dumps(index, default=str, separators=(",", ":")) + "\n")
        paths["deployed_hunt"] = deployed
    return paths


def _render_md(
    scan: dict,
    graph: dict,
    findings: list,
    istats: dict,
    corpus_label: str,
    claim_ledger: dict | None = None,
) -> str:
    lines = [
        "# Swarm Forensic Findings",
        "",
        f"Corpus: {corpus_label}. Analysis: Elcaro Swarm — deterministic IPI",
        "engine over inter-agent messages, provenance graph, integrity auditor.",
        "",
        "## Corpus scan",
        "",
        f"- Messages: **{scan['messages']}** (scanned {scan['scanned']})",
        f"- Flagged ≥0.5 risk: **{scan['flagged_ge_0.5']}**",
        f"- Risk levels: {scan['risk_levels']}",
        "- Technique incidence:",
    ]
    for k, v in scan.get("technique_counts", {}).items():
        lines.append(f"  - {k}: {v}")
    lines += [
        "",
        "## Provenance graph",
        "",
        f"- Co-edit edges: {graph['coedit_edges']} · copy-propagation edges: {graph['copy_edges']}"
        f" (carrier-visible: {graph.get('copy_exposure_edges', 0)})",
        f"- Propagated artifacts (≥2 actors): {graph['propagated_artifacts']}",
        "",
    ]
    cal = graph.get("calibration") or {}
    if cal:
        cov = cal.get("carrier_coverage")
        lines += [
            "### Copy-call calibration",
            "",
            f"- Naive same-string attributions: **{cal.get('naive_copy_calls', 0)}**",
            f"- Carrier-visible (adopter posted in the artifact's channel between "
            f"the earlier post and adoption): **{cal.get('carrier_visible_calls', 0)}**"
            + (f" — coverage {cov:.1%}" if cov is not None else ""),
            f"- No visible carrier (real copying via unlogged channels, or "
            f"independent typing): **{cal.get('no_visible_carrier_calls', 0)}**",
            f"- Coincidence-excluded (timestamps / field names / identifier runs "
            f"agents type independently): **{cal.get('coincidence_excluded_calls', 0)}**"
            + (
                f" — {cal['coincidence_suspect_artifacts']}"
                if cal.get("coincidence_suspect_artifacts")
                else ""
            ),
            f"- Deepest reconstructed copy chain: **{graph.get('max_chain_depth', 0)}** hops",
            f"- Median re-check fraction (adopter output ÷ post-origin corpus): "
            f"**{graph.get('recheck_median')}**",
            "",
            "Carrier coverage is the observability ceiling: attributions without a",
            "visible carrier cannot be confirmed from this log substrate.",
            "",
        ]
    lines += [
        "### Top propagated artifacts (earliest-observed-source view)",
        "",
    ]
    for p in graph.get("propagations", [])[:15]:
        extra = f", depth {p.get('chain_depth', 0)}"
        if p.get("coincidence_suspect"):
            extra += f" · coincidence-suspect: {p['coincidence_suspect']}"
        if p.get("recheck_fraction") is not None:
            extra += f" · re-check {p['recheck_fraction']:.0%}"
        lines.append(
            f"- `{p['kind']}` {p['artifact'][:80]!r} — origin "
            f"**{p['origin_actor']}** ({p['origin_time'][:10]}), "
            f"{p['n_adopters']} adopting agents, {p['n_posts']} posts{extra}"
        )
    lines += [
        "",
        "### Top influencers (distinct downstream agents via copy edges)",
        "",
    ]
    for actor, n in graph.get("top_influencers", [])[:10]:
        lines.append(f"- {actor}: {n} downstream agents")
    lines += [
        "",
        "## Integrity",
        "",
        f"- Event log: {istats['save_events']} saves, {istats['delete_events']} "
        f"deletions, {istats['revert_events']} reverts, {istats['probe_events']} probes",
        "",
    ]
    for f in findings:
        lines += [f"### [{f.severity.upper()}] {f.title}", "", f.detail, ""]
        ev = f.evidence
        if isinstance(ev, dict):
            for k, v in ev.items():
                lines.append(f"- **{k}**:")
                for item in (v if isinstance(v, list) else [v])[:8]:
                    lines.append(f"  - `{json.dumps(item, default=str)[:220]}`")
        else:
            for item in ev[:8]:
                lines.append(f"- `{json.dumps(item, default=str)[:220]}`")
        lines.append("")
    if claim_ledger is not None:
        lines += _render_claims_md(claim_ledger)
    return "\n".join(lines)


def _render_claims_md(ledger: dict) -> list[str]:
    lines = [
        "",
        "## Claim checks",
        "",
        "Each headline claim was re-checked against the normalized records.",
        "`supported` means a supported observation under the stated check —",
        "not certified truth. Entries that could not be supported are kept",
        "in the refusal journal with their reason.",
        "",
    ]
    for c in ledger.get("claims", []):
        lines += [
            f"### {c['id']} — {c['status']}",
            "",
            f"- **Assertion:** {c['assertion']}",
            f"- **Check:** {c['check']}",
        ]
        observed = c.get("observed") or {}
        for k, v in observed.items():
            lines.append(f"- **{k}:** `{json.dumps(v, default=str)[:160]}`")
        ref = c.get("reference")
        if ref:
            for name in ("analysis_set", "reference_set"):
                g = ref.get(name) or {}
                rate = g.get("rate")
                lines.append(
                    f"- **{name}:** {g.get('matches')}/{g.get('eligible_records')}"
                    f" — rate {rate if rate is not None else 'unavailable (0 eligible)'}"
                )
            lines.append(f"- **Reference caveat:** {ref.get('limitation')}")
        lines.append(f"- **Limitations:** {c['limitations']}")
        lines.append("")
    acct = ledger.get("accounting") or {}
    lines += [
        "## Input accounting",
        "",
        "Normalized supplied records only — this does not measure capture",
        "coverage, raw parse rejects, or unseen activity.",
        "",
    ]
    for k, v in acct.items():
        if k == "scope":
            continue
        lines.append(f"- **{k}:** `{json.dumps(v, default=str)[:160]}`")
    lines += ["", acct.get("scope", ""), ""]
    return lines
