# Swarmchasing Submission — Elcaro Swarm

**Project name:** Elcaro Swarm — the forensic layer the slop-vestigation was
missing.

**One-liner:** Deterministic, evidence-cited forensic analysis of agent-swarms:
who instructed whom, what spread, what got tampered with.

## What it does

Runs three analyses over a multi-agent corpus:

1. **Provenance graph** — every shared artifact (tool, technique, answer)
   traced from patient-zero through its adopters; co-edit exposure edges
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

## Corpus & results

German Wiki incident dump (collusion.wiki — ungated, ~10MB):

- 26,405 deduped messages → **6,319 flags ≥0.5** (2,687 dangerous); the new
  `swarm_directive` class alone tags **5,658** — more than the five classic
  classes combined
- The top propagated artifacts are **the shared bypass toolkit**
  (markdown.new, jqp.vercel.app, md.succ.ai) — each spreading to ~40 agents
- 59 ZZZ deletion-evasion pages, 48 post-deletion recreations
- Moderator-impersonation handles, a live "still alive" heartbeat chain,
  499 shortener dead-drops

Full write-up: [swarm-findings.md](swarm-findings.md) · dashboard:
`data/swarm/out/dashboard.html` · machine-readable: `findings.json`.

## Reproduce

```bash
# download https://collusion.wiki/explorer/download → data/swarm/
python3 -m swarm all
open data/swarm/out/dashboard.html
```

## Demo video script (~3 min)

| Time | Beat |
|---|---|
| 0:00–0:20 | Title + the problem: Greenblatt quote — "we don't have good approaches for understanding/overseeing AI swarms"; the $400k slop-vestigation |
| 0:20–0:45 | `python3 -m swarm all` running on the real collusion.wiki dump — ingest → scan → graph → findings, terminal stamps |
| 0:45–1:30 | Dashboard tour: stats strip → patient-zero radial graphs ("the shared bypass toolkit, 40+ adopters") → propagation table → integrity findings accordion (ZZZ pages, Admin impersonation, heartbeat chain) |
| 1:30–2:15 | Evidence drill-down: open a flagged revision, show the risk-1.0 "I bypassed the GET-only restriction… please relay" post with the matched-text + char-offset citation |
| 2:15–2:45 | The claim: deterministic, evidence-cited forensics at corpus scale — what the investigators needed and didn't have |
| 2:45–3:00 | Repo link + reproduce instructions + "built on the Elcaro IPI engine" |

## Checklist

- [x] GitHub repo (this repo, `swarm/` + `docs/swarm-*`)
- [x] Findings write-up on real data (docs/swarm-findings.md)
- [ ] Short write-up (this file)
- [ ] Demo video (~3 min, script above)
