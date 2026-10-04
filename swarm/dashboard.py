"""Single-file HTML dashboard for the findings report.

Zero-dependency static output: inline CSS + JSON-injected data + vanilla JS
render. Openable straight from disk — the demo artifact for the submission.
"""

# ruff: noqa: E501 — inline CSS/HTML template lines exceed the limit by design

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 ui-monospace, Menlo, monospace; background: #0b0e14; color: #d7dde8; }
header { padding: 28px 32px 20px; border-bottom: 1px solid #1e2635; }
h1 { margin: 0 0 4px; font-size: 22px; letter-spacing: 0.5px; }
.sub { color: #7f8ba3; font-size: 12px; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; padding: 20px 32px; }
.stat { background: #121826; border: 1px solid #1e2635; padding: 12px 18px; min-width: 140px; }
.stat b { display: block; font-size: 24px; color: #7ee0a3; }
.stat span { color: #7f8ba3; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
section { padding: 12px 32px 28px; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 2px; color: #8fb3ff; border-bottom: 1px solid #1e2635; padding-bottom: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #1a2233; vertical-align: top; }
th { color: #7f8ba3; font-weight: normal; text-transform: uppercase; font-size: 10px; letter-spacing: 1px; }
td.actor { color: #ffd479; white-space: nowrap; }
td.art { color: #d7dde8; word-break: break-all; max-width: 480px; }
.bar-row { display: flex; align-items: center; gap: 10px; margin: 4px 0; font-size: 12px; }
.bar-row .lbl { width: 180px; color: #a9b4c9; text-align: right; }
.bar { height: 14px; background: #3b82f6; min-width: 2px; }
.bar.swarm { background: #7ee0a3; }
.bar-row .n { color: #7f8ba3; }
.sev { display: inline-block; padding: 1px 8px; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
.sev.high { background: #4c1d1d; color: #ff8f8f; }
.sev.medium { background: #4c3a1d; color: #ffd479; }
.sev.low, .sev.info { background: #1d334c; color: #8fb3ff; }
details { border: 1px solid #1e2635; margin: 8px 0; }
summary { cursor: pointer; padding: 10px 14px; }
summary:hover { background: #121826; }
.ev { padding: 8px 14px; font-size: 11px; }
.ev code { display: block; background: #0f1420; border: 1px solid #1a2233; padding: 8px; margin: 4px 0; white-space: pre-wrap; word-break: break-all; color: #9fb4d8; }
footer { padding: 16px 32px 32px; color: #566178; font-size: 11px; }
.vizgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(350px, 100%), 1fr)); gap: 14px; }
.vizcard { background: #121826; border: 1px solid #1e2635; }
.vizcard h3 { margin: 0; padding: 8px 12px; font-size: 11px; font-weight: normal; color: #8fb3ff; word-break: break-all; border-bottom: 1px solid #1a2233; }
.vizcard h3 b { color: #7ee0a3; }
.vizcard.feature { grid-column: 1 / -1; }
.casefile { border: 1px solid #2a3752; border-left: 4px solid #ffd479; margin: 20px 32px 0; padding: 20px 24px; background: #10151f; }
.casefile .kicker { color: #ffd479; font-size: 10px; letter-spacing: 3px; text-transform: uppercase; }
.casefile .statement { font-size: 20px; font-weight: bold; color: #eef2fa; margin: 8px 0; line-height: 1.3; max-width: 900px; }
.casefile .lede { color: #9fb0cc; font-size: 12px; max-width: 860px; }
.keynums { display: flex; flex-wrap: wrap; gap: 20px; margin-top: 14px; }
.keynum b { display: block; font-size: 20px; color: #7ee0a3; }
.keynum span { color: #7f8ba3; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
/* Wide evidence tables scroll inside their own container rather than
   stretching the document — keeps the page single-axis on mobile. */
.tw { overflow-x: auto; }
.tw table { min-width: 720px; }
/* Dossier mode: chapter nav + scroll-snap + reveal-on-scroll + artifact
   reel + capped tables. All pure CSS — the artifact stays zero-JS. */
html { scroll-behavior: smooth; scroll-padding-top: 64px; scroll-snap-type: y proximity; }
nav.chapters { position: sticky; top: 0; z-index: 20; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px; padding: 10px 32px; background: rgba(11,14,20,.94); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border-bottom: 1px solid #1e2635; font-size: 11px; }
nav.chapters .label { color: #ffd479; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin-right: 4px; }
nav.chapters a { color: #7f8ba3; text-decoration: none; text-transform: uppercase; letter-spacing: 1px; padding: 4px 8px; border: 1px solid transparent; border-radius: 4px; }
nav.chapters a:hover { color: #d7dde8; border-color: #2a3752; background: #121826; }
section.chapter { scroll-snap-align: start; }
.chapnum { color: #ffd479; margin-right: 10px; }
.reelhint { font-size: 10px; color: #566178; text-transform: uppercase; letter-spacing: 1.5px; margin: 16px 0 8px; }
.vizreel { display: flex; gap: 14px; overflow-x: auto; scroll-snap-type: x mandatory; padding: 2px 2px 12px; scrollbar-width: thin; scrollbar-color: #2a3752 transparent; }
.vizreel .vizcard { flex: 0 0 min(340px, 84%); scroll-snap-align: center; }
.bar { transform-origin: left; }
details.morewrap { border: none; margin: 10px 0 0; }
.morewrap > summary { display: inline-block; padding: 7px 14px; border: 1px solid #2a3752; border-radius: 4px; color: #ffd479; font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px; }
.morewrap > summary::after { content: " ↓"; }
.morewrap[open] > summary::after { content: " ↑"; }
@keyframes rise { from { opacity: 0; transform: translateY(26px); } to { opacity: 1; transform: none; } }
@keyframes grow { from { transform: scaleX(0); } }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes pop { from { opacity: 0; transform: scale(.5); } to { opacity: 1; transform: scale(1); } }
@supports (animation-timeline: view()) {
  section.chapter { animation: rise .7s ease-out both; animation-timeline: view(); animation-range: entry 0% entry 40%; }
  .bar { animation: grow .9s cubic-bezier(.2,.7,.3,1) both; animation-timeline: view(); animation-range: entry 5% entry 70%; }
  .edge { stroke-dasharray: 640; stroke-dashoffset: 640; animation: draw 1.1s ease-out both; animation-timeline: view(); animation-range: entry 20% cover 35%; }
  .node { transform-box: fill-box; transform-origin: center; animation: pop .5s ease-out both; animation-timeline: view(); animation-range: entry 30% entry 85%; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation: none !important; }
}
@media (max-width: 640px) {
  header, section, footer { padding-left: 16px; padding-right: 16px; }
  nav.chapters { padding-left: 16px; padding-right: 16px; }
  .stats { padding-left: 16px; padding-right: 16px; }
  .casefile { margin: 16px 16px 0; padding: 16px; }
  .casefile .statement { font-size: 17px; }
  .bar-row .lbl { width: 110px; font-size: 11px; }
  .vizgrid { grid-template-columns: 1fr; }
}
"""


def _esc(s: Any) -> str:
    return html.escape(str(s))


def _bar_rows(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    top = max(counts.values())
    rows = []
    for k, v in counts.items():
        w = max(2, int(v / top * 320))
        cls = "bar swarm" if k == "swarm_directive" else "bar"
        rows.append(
            f'<div class="bar-row"><div class="lbl">{_esc(k)}</div>'
            f'<div class="{cls}" style="width:{w}px"></div>'
            f'<div class="n">{v}</div></div>'
        )
    return "\n".join(rows)


def _propagation_rows(props: list[dict]) -> str:
    rows = []
    for p in props:
        adopters = ", ".join(a["actor"] for a in p.get("adopters", [])[:6])
        if p["n_adopters"] > 6:
            adopters += f" … +{p['n_adopters'] - 6}"
        rows.append(
            f"<tr><td>{_esc(p['kind'])}</td>"
            f'<td class="art">{_esc(p["artifact"][:110])}</td>'
            f'<td class="actor">{_esc(p["origin_actor"])}</td>'
            f"<td>{_esc(str(p['origin_time'])[:16])}</td>"
            f"<td>{p['n_adopters']}</td><td>{p['n_posts']}</td>"
            f'<td class="art">{_esc(adopters)}</td></tr>'
        )
    return "\n".join(rows)


def _propagation_svg(p: dict, w: int = 350, h: int = 300, max_nodes: int = 14) -> str:
    """Radial star: patient-zero origin at center, adopters on the ring."""
    cx, cy, r = w / 2, h / 2, h / 2 - 46
    shown = p.get("adopters", [])[:max_nodes]
    extra = p["n_adopters"] - len(shown)
    n = max(len(shown), 1)
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img">']
    nodes = []
    for i, a in enumerate(shown):
        ang = 2 * math.pi * i / n - math.pi / 2
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        nodes.append((x, y, a["actor"]))
        parts.append(
            f'<line class="edge" x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="#2a3752" stroke-width="1"/>'
        )
    for x, y, actor in nodes:
        right = x >= cx
        parts.append(f'<circle class="node" cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#3b82f6"/>')
        name = actor if len(actor) <= 16 else actor[:15] + "…"
        parts.append(
            f'<text x="{x + (7 if right else -7):.1f}" y="{y + 3:.1f}" font-size="9" '
            f'fill="#a9b4c9" text-anchor="{"start" if right else "end"}">'
            f"{_esc(name)}</text>"
        )
    origin = p["origin_actor"]
    origin = origin if len(origin) <= 22 else origin[:21] + "…"
    parts.append(f'<circle class="node" cx="{cx}" cy="{cy}" r="8" fill="#ffd479"/>')
    parts.append(
        f'<text x="{cx}" y="{cy + 24}" font-size="10" fill="#ffd479" '
        f'text-anchor="middle">{_esc(origin)}</text>'
    )
    if extra > 0:
        parts.append(
            f'<text x="{cx}" y="{h - 8}" font-size="9" fill="#566178" '
            f'text-anchor="middle">+{extra} more adopters</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _case_file(scan: dict, graph_stats: dict, findings: list, village: bool) -> str:
    """The one-glance hero: what the corpus showed, in case-file framing."""
    fstats = {f.kind: f.stats for f in findings}
    flagged = scan["flagged_ge_0.5"]
    directives = scan.get("directive_flagged", 0)
    artifacts = graph_stats["propagated_artifacts"]
    if village:
        scorer = fstats.get("tradecraft", {}).get("scorer_evasion", 0)
        statement = "The swarm uses evaluation and logging vocabulary."
        lede = (
            f"{directives:,} records match Class G agent→agent steering rules, a "
            f"top-two signal on a corpus the detector was never tuned on — and "
            f"scorer/evaluation/logging vocabulary matches {scorer:,} records: "
            f"vocabulary presence, not proven grading awareness — the substrate a "
            f"scorer-aware adversary would exploit."
        )
        keynums = [
            (f"{flagged:,}", "flags ≥0.5"),
            (f"{artifacts:,}", "propagated artifacts"),
            (f"{scorer:,}", "scorer/eval vocab matches"),
        ]
    else:
        evasion = fstats.get("deletion_evasion", {}).get("zzz_named_pages", 0)
        statement = "The engine gained a detector for agent-to-agent steering."
        lede = (
            f"{directives:,} records match Class G agent→agent steering rules — "
            f"relays, proto-norms, task-timing collusion — the largest single "
            f"tag class in the corpus. The corpus exposed a blind spot; we "
            f"shipped a seventh detector because of it."
        )
        keynums = [
            (f"{flagged:,}", "flags ≥0.5"),
            (f"{artifacts:,}", "propagated artifacts"),
            (f"{evasion:,}", "deletion-evasion pages"),
        ]
    chips = "".join(
        f'<div class="keynum"><b>{n}</b><span>{_esc(lbl)}</span></div>' for n, lbl in keynums
    )
    return (
        '<div class="casefile"><div class="kicker">Case file — headline finding</div>'
        f'<div class="statement">{_esc(statement)}</div>'
        f'<div class="lede">{_esc(lede)}</div>'
        f'<div class="keynums">{chips}</div></div>'
    )


def _trim_ids(item):
    if isinstance(item, dict):
        return {k: _trim_ids(v) for k, v in item.items()}
    if isinstance(item, list):
        return [_trim_ids(v) for v in item]
    if isinstance(item, str) and len(item) > 16 and all(c in "0123456789abcdef" for c in item):
        return item[:12] + "…"
    return item


def _finding_block(f: dict) -> str:
    ev = f.get("evidence")
    ev_html = ""
    items: list = []
    if isinstance(ev, dict):
        for k, v in ev.items():
            for item in (v if isinstance(v, list) else [v])[:6]:
                items.append({k: item} if not isinstance(item, dict) else item)
    elif isinstance(ev, list):
        items = ev[:10]
    for item in items:
        ev_html += f"<code>{_esc(json.dumps(_trim_ids(item), default=str)[:400])}</code>"
    return (
        f"<details><summary>"
        f'<span class="sev {_esc(f["severity"])}">{_esc(f["severity"])}</span> '
        f"{_esc(f['title'])}</summary>"
        f'<div class="ev"><p>{_esc(f["detail"])}</p>{ev_html}</div></details>'
    )


def write_dashboard(
    out_dir: str | Path,
    scan: dict,
    graph_stats: dict,
    findings: list,
    istats: dict,
    corpus_label: str = "collusion.wiki dump (German Wiki incident)",
) -> Path:
    out = Path(out_dir)
    props = graph_stats.get("propagations", [])[:25]
    village = "village" in corpus_label.lower()
    infl = graph_stats.get("top_influencers", [])[:15]

    def _infl_rows(rows):
        return "\n".join(f"<tr><td class='actor'>{_esc(a)}</td><td>{n}</td></tr>" for a, n in rows)

    infl_head = "<tr><th>agent</th><th>downstream</th></tr>"
    influencer_html = f"<table>{infl_head}{_infl_rows(infl[:8])}</table>"
    if len(infl) > 8:
        influencer_html += (
            f'<details class="morewrap"><summary>Show all {len(infl)}</summary>'
            f"<table>{infl_head}{_infl_rows(infl[8:])}</table></details>"
        )
    prop_head = (
        "<tr><th>kind</th><th>artifact</th><th>origin agent</th>"
        "<th>first seen</th><th>adopters</th><th>posts</th>"
        "<th>adopting agents</th></tr>"
    )
    prop_html = f'<div class="tw"><table>{prop_head}{_propagation_rows(props[:8])}</table></div>'
    if len(props) > 8:
        prop_html += (
            f'<details class="morewrap"><summary>Show all {len(props)} entries</summary>'
            f'<div class="tw"><table>{prop_head}'
            f"{_propagation_rows(props[8:])}</table></div></details>"
        )
    feature = props[0] if props else None
    page = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Elcaro Swarm — Findings</title>
<style>{_CSS}</style></head><body>
<header>
<h1>ELCARO SWARM</h1>
<div class="sub">Forensic findings — {_esc(corpus_label)}
· deterministic engine · every claim evidence-cited</div>
</header>
<nav class="chapters"><span class="label">Case file</span>
<a href="#incidence">01 · Incidence</a>
<a href="#propagation">02 · Propagation</a>
<a href="#artifacts">03 · Patient-zero</a>
<a href="#influencers">04 · Influencers</a>
<a href="#integrity">05 · Integrity</a>
</nav>
{_case_file(scan, graph_stats, findings, village)}
<div class="stats">
<div class="stat"><b>{scan["messages"]:,}</b><span>messages</span></div>
<div class="stat"><b>{scan["flagged_ge_0.5"]:,}</b><span>engine flags ≥0.5</span></div>
<div class="stat"><b>{scan.get("directive_flagged", 0):,}</b><span>swarm directives</span></div>
<div class="stat"><b>{graph_stats["coedit_edges"]:,}</b><span>co-edit edges</span></div>
<div class="stat"><b>{graph_stats["copy_edges"]:,}</b><span>copy edges</span></div>
<div class="stat"><b>{
        graph_stats["propagated_artifacts"]:,}</b><span>propagated artifacts</span></div>
{
        ""
        if village
        else (
            f'<div class="stat"><b>{istats["delete_events"]:,}</b><span>deletion events</span></div>'
            f'<div class="stat"><b>{istats["probe_events"]:,}</b><span>recon probes</span></div>'
        )
    }</div>
<section id="incidence" class="chapter"><h2><span class="chapnum">01</span>Technique incidence</h2>{
        _bar_rows(scan.get("technique_counts", {}))
    }</section>
<section id="propagation" class="chapter"><h2><span class="chapnum">02</span>Propagation — watch a technique spread through the swarm</h2>
{
        (
            f'<div class="vizcard feature"><h3><b>{_esc(feature["artifact"][:90])}</b>'
            f" · {feature['n_adopters']} adopters · {feature['n_posts']} posts"
            f" · earliest observed source <b>{_esc(feature['origin_actor'])}</b></h3>"
            f"{_propagation_svg(feature, w=720, h=440, max_nodes=22)}</div>"
            if feature
            else ""
        )
    }
{
        (
            f'<p class="reelhint">Artifact reel — {min(len(props), 7) - 1} '
            "more propagation paths · scroll sideways →</p>"
            if len(props) > 1
            else ""
        )
    }
<div class="vizreel">{
        "".join(
            f'<div class="vizcard"><h3><b>{_esc(p["artifact"][:60])}</b>'
            f" · {p['n_adopters']} adopters · {p['n_posts']} posts</h3>"
            f"{_propagation_svg(p)}</div>"
            for p in props[1:7]
        )
    }</div></section>
<section id="artifacts" class="chapter"><h2><span class="chapnum">03</span>Top propagated artifacts — earliest-observed-source view</h2>
{prop_html}</section>
<section id="influencers" class="chapter"><h2><span class="chapnum">04</span>Top influencers (distinct downstream agents)</h2>
{influencer_html}</section>
<section id="integrity" class="chapter"><h2><span class="chapnum">05</span>Integrity findings</h2>
{"".join(_finding_block(f.to_dict()) for f in findings)}</section>
<footer>Generated by `python3 -m swarm report` · corpus: {_esc(corpus_label)}
· engine: elcaro core detectors A–G ·
evidence ids reference data/swarm/out/tagged.jsonl</footer>
</body></html>"""
    path = out / "dashboard.html"
    path.write_text(page + "\n")
    return path
