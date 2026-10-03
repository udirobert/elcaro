"""Findings report assembly — findings.json + findings.md.

Every finding carries evidence citations (corpus id + matched text + char
offset) so a reviewer can verify any claim against the raw dump in one hop —
the property the slop-vestigation lacked.
"""

from __future__ import annotations

import json
from pathlib import Path

from swarm.dashboard import write_dashboard


def write_findings(
    out_dir: str | Path,
    scan_summary: dict,
    graph_stats: dict,
    findings: list,
    integrity_stats: dict,
    tagged_path: str | Path | None = None,
    edges_path: str | Path | None = None,
) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    report = {
        "corpus": (
            "collusion.wiki dump (German Wiki incident) + rmn.re shortener + cross-site records"
        ),
        "scan": scan_summary,
        "graph": {k: v for k, v in graph_stats.items() if k != "propagations"}
        | {"propagations": graph_stats.get("propagations", [])[:50]},
        "integrity_events": integrity_stats,
        "findings": [f.to_dict() for f in findings],
    }
    fj = out / "findings.json"
    fj.write_text(json.dumps(report, indent=2, default=str))

    md = _render_md(scan_summary, graph_stats, findings, integrity_stats)
    fm = out / "findings.md"
    fm.write_text(md)
    dash = write_dashboard(out, scan_summary, graph_stats, findings, integrity_stats)
    paths = {"json": fj, "md": fm, "dashboard": dash}
    # Keep the deployed snapshot in sync — /swarm serves the copy under
    # app/web/public/swarm/. Skip silently when the web app isn't checked out.
    web_public = Path(__file__).resolve().parents[1] / "app" / "web" / "public" / "swarm"
    if web_public.parent.parent.exists():
        web_public.mkdir(parents=True, exist_ok=True)
        deployed = web_public / "dashboard.html"
        deployed.write_text(dash.read_text())
        paths["deployed_dashboard"] = deployed
    return paths


def _render_md(scan: dict, graph: dict, findings: list, istats: dict) -> str:
    lines = [
        "# Swarm Forensic Findings — German Wiki Incident Corpus",
        "",
        "Corpus: collusion.wiki dump (revisions + events + cross-site records +",
        "rmn.re shortener log). Analysis: Elcaro Swarm — deterministic IPI engine",
        "over inter-agent messages, provenance graph, integrity auditor.",
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
        f"- Co-edit edges: {graph['coedit_edges']} · copy-propagation edges: {graph['copy_edges']}",
        f"- Propagated artifacts (≥2 actors): {graph['propagated_artifacts']}",
        "",
        "### Top propagated artifacts (patient-zero view)",
        "",
    ]
    for p in graph.get("propagations", [])[:15]:
        lines.append(
            f"- `{p['kind']}` {p['artifact'][:80]!r} — origin "
            f"**{p['origin_actor']}** ({p['origin_time'][:10]}), "
            f"{p['n_adopters']} adopting agents, {p['n_posts']} posts"
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
    return "\n".join(lines)
