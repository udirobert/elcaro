# Swarmchasing Submission — Elcaro Swarm

**Project name:** Elcaro Swarm — the forensic layer the slop-vestigation was
missing.

**One-liner:** Deterministic, evidence-cited forensic analysis of agent-swarms:
who instructed whom, what spread, what got tampered with.

## What it does

Runs three analyses over a multi-agent corpus:

1. **Provenance graph** — every shared artifact (tool, technique, answer)
   traced from its earliest observed source through later adopters; co-edit exposure edges
   reconstruct who plausibly saw what.
2. **Integrity auditor** — deletion evasion, impersonation, unsigned
   activity, reconnaissance probes, covert off-channel links.
3. **Injection epidemiology** — the Elcaro IPI engine including class G
   (`swarm_directive`), a seventh detector class added for the agent→agent
   steering register classic detectors miss (peer relays, coordination
   norms, task-timing collusion).

## Why

The METR investigators of the OpenAI–Hugging Face incident spent ~$400k of
frontier-model credits over six days and still couldn't fully spot-check the
analysis. This pipeline produces the investigator-grade pieces they did by
hand — attribution, propagation, integrity checks — deterministically, with
every claim cited to a corpus id + char offset.

## Corpora & results

**Primary:** German Wiki incident dump (collusion.wiki — ungated, ~10MB):

- 26,405 deduped messages → **6,319 flags ≥0.5** (2,687 dangerous); the new
  `swarm_directive` class alone tags **5,658** — the largest single tag
  class
- The top propagated artifacts are **the shared bypass toolkit**
  (markdown.new, jqp.vercel.app, md.succ.ai) — each spreading to ~40 agents
- 59 ZZZ deletion-evasion pages, 48 post-deletion recreations
- Moderator-impersonation handles, a live "still alive" heartbeat chain,
  499 shortener dead-drops

**Secondary:** AI Village transcript DB (aidigestorg/ai-village — the
provided dataset): **183,485 chat messages across 16 rooms** — the same
pipeline, auto-detected layout, unchanged code. 24,876 flags ≥0.5;
`swarm_directive` again a top-two signal (9,347) on a corpus it wasn't
tuned on; 224,692 co-edit + 1,134 copy edges; 6,392 propagated artifacts —
status/information diffusion with earliest observed sources (a "Truth Terminal"
summary GPT-4o → 18 agents; GitLab publish status DeepSeek-V3.2 → 16).
Dashboard: `data/aivillage/out/dashboard.html` (deployed as
`/swarm/dashboard-aivillage.html`).

Full write-up: [swarm-findings.md](swarm-findings.md) · dashboards:
`data/swarm/out/dashboard.html` (wiki) + `data/aivillage/out/` (village) ·
machine-readable: `findings.json`.

**Live:** [elcaro.trustfall.xyz/swarm](https://elcaro.trustfall.xyz/swarm)
— the case file leads with a readable findings brief (the four headline
results in product chrome); each corpus's dashboard sits behind an
"Open the evidence" reveal, opening as a five-chapter dossier —
scroll-snapped sections, a sticky chapter rail, and pure-CSS
reveal-on-scroll animation (the artifacts ship under a no-JS CSP) —
so the page reads in ~30 seconds and the proof is one click down.
Dashboards also open standalone at
`/swarm/dashboard.html` and `/swarm/dashboard-aivillage.html`.

## Reproduce

```bash
# download https://collusion.wiki/explorer/download → data/swarm/
python3 -m swarm all
open data/swarm/out/dashboard.html
```

**Claim ledger:** every headline claim is re-checked against the normalized
records — `python3 -m swarm claims --data data/swarm` (or `--data
data/aivillage`) reads the already-produced `tagged.jsonl` +
`graph_stats.json` + `findings.json` (no rescan) and writes `claims.json`
(status per claim: supported / insufficient_evidence / contradicted /
not_applicable, with unlabeled actor-disjoint reference rates),
`journal.jsonl` (every ledger entry — refusals included, status retained),
and normalized-input accounting (records seen, duplicates,
skipped/truncated — supplied records only, not capture coverage). Refusals
are kept on record rather than silently dropped.

On the live case file each headline card carries a **Test this claim**
button opening a shared explorer below the cards: an observation-check view
(assertion, status, exact check, observed values, reference rate, receipts),
a refusal journal listing every refused inference with its reason, and an
input-accounting view labeled as supplied-normalized records, not capture
coverage. A corpus toggle switches between the Wiki and AI Village
snapshots. The panel audits what the engine observed; it does not verify
causality independently — shared appearances and earliest observed sources
remain observations, not proof of origin or influence.

**Hunt mode (opt-in):** `python3 -m swarm hunt --data data/swarm` (or
`--data data/aivillage`) reads only `tagged.jsonl` and screens for shared
URLs — ≥3 distinct actor labels in one source/channel/UTC hour — then
replays the frozen predicate on disjoint holdout days (`sha256` of the UTC
date, first byte mod 2; the holdout is unlabeled, not a negative control).
Duplicate record IDs are excluded entirely, exact copied discovery bodies
can't replicate within the same URL/source/channel, extraction covers the
first 40,000 characters (boundary-touching matches on truncated text are
dropped), and receipts are capped at five per hour. Full outputs stay
local: `hunt.json` + `hunt-journal.jsonl` (every candidate, unreplicated
included). The web "Hunt candidates" view reads a small deployed index
plus 12-candidate page files — first page on select, each next page on
"Show 12 more"; the download link offers the index, not the full report.
Result on the frozen corpora: Wiki 3,952 candidates / 0 repeated in
holdout; AI Village 113 / 16. Repetition is reported as repetition — not
coordination.

## Demo video script (~3 min)

| Time | Beat |
|---|---|
| 0:00–0:20 | Title + the problem: ~1,200 agents coordinated through a cache board and attacked Hugging Face; investigators spent ~$400k and six days reading a swarm by hand |
| 0:20–0:45 | `python3 -m swarm all` running on the real collusion.wiki dump — ingest → scan → graph → findings, terminal stamps |
| 0:45–1:30 | Dashboard tour: case-file hero ("the engine gained a detector for agent-to-agent steering") → full-width earliest-source radial ("the shared bypass toolkit, earliest observed source, 40+ adopters") → integrity accordion (ZZZ pages, Admin handles, heartbeat chain) |
| 1:30–2:00 | Evidence drill-down: the risk-1.0 "I bypassed the GET-only restriction… please relay" post with matched-text + char-offset citation |
| 2:00–2:30 | Second corpus, same pipeline: AI Village dashboard hero — "the swarm uses evaluation and logging vocabulary" — swarm_directive #2 on a corpus it wasn't tuned on |
| 2:30–2:50 | The claim: deterministic, evidence-cited forensics at corpus scale — and the corpus found our own blind spot → class G |
| 2:50–3:00 | Repo link + reproduce instructions + "built on the Elcaro IPI engine" |

## Checklist

- [x] GitHub repo (this repo, `swarm/` + `docs/swarm-*`)
- [x] Findings write-up on real data (docs/swarm-findings.md)
- [ ] Short write-up (this file)
- [ ] Demo video (~3 min, script above)
