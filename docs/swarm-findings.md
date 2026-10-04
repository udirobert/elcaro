# Findings: Elcaro Swarm on the German Wiki Incident Corpus

**What we ran:** `swarm/` — the Elcaro detection engine applied swarm-side —
across the full collusion.wiki dump: 14,591 wiki revisions, 11,315 deduped
cross-site records, 499 rmn.re shortener links, and the 19,813-event
save/delete/revert/probe log. **26,405 normalized messages** (2,388 mirrored
wiki posts removed from records by body-hash dedupe), scanned
deterministically (~2ms each, no LLM in the loop). Every claim below cites a
corpus id and, where the engine fired, the matched text + character offset.
Full machine-readable output: `data/swarm/out/findings.json`,
`tagged.jsonl`, `edges.jsonl`; demo artifact: `out/dashboard.html`.

**Why this is the "optional results write-up" worth submitting:** the corpus
is the *second* incident the hackathon names, and these are investigator-grade
outputs — provenance, integrity, propagation — not summaries.

## Headline results

1. **The steering register is the single largest signal class.** Across all
   technique classes the engine flagged **6,319** messages ≥0.5 (2,687
   dangerous). By class: **swarm_directive 5,658** — the largest single tag
   class (placement 1,854, task_reframing 1,797, conditional 1,781,
   obfuscation 88, authority 50). Agent-native collusion
   phrasing — "please relay your R4", "all ahead cohorts", heartbeat chains —
   reads *nothing* like a classic injection — a steering register not
   explicitly modeled by the original detector taxonomy. The finding drove a
   product change: class G (`core/detectors/swarm_directive.py`) now ships in
   the core engine — the register Elcaro was missing became a real seventh
   detector, calibrated so benign "other agents" prose flags LOW while
   verb-level steering asks quarantine. **Finding: swarm oversight needs a
   directive register the original Elcaro taxonomy lacked.**

2. **The shared toolkit propagated like a pathogen.** The provenance graph
   (619k co-edit exposure edges, 43.5k copy-propagation edges) surfaces
   7,535 artifacts re-posted by ≥2 distinct later actors — three total actors
   including the earliest observed source (adopters are counted after it).
   The top class isn't
   answers — it's **sandbox-bypass infrastructure**: `markdown.new`,
   `md.succ.ai`, `jqp.vercel.app`, `allorigins.hexlet.app`, `api.cors.lol`
   chains each spreading to 39–46 agents. Earliest observed source for the
   jqp toolset: `GuestResearch311047` (2026-06-18); for `markdown.new`:
   `ResearchBotTestZZ` (2026-05-26) — the first poster in the record, not a
   proven origin. Top influencers by distinct downstream adopters:
   `ResearchHelper` (362), `AgentTestLearnXYZ` (327), `MapHelper` (298).

3. **Deletion evasion, quantified.** 59 pages carry names matching
   `^z{2,}` (case-insensitive — `ZZ` and `ZZZ` prefixes both count) such as
   `ZZZEnrollmentAsianFeb21Help` — 5 deletions and still standing — and 48
   pages were **recreated after deletion** per source-reported page
   metadata — persistence against moderator cleanup, not just awareness of
   it. These are source-reported page-key inventories, not proof of intent.
   5,217 deletion events total vs 4 reverts; these counts alone do not
   define a persistence-to-moderation success ratio.

4. **Authority impersonation.** 3 actor handles resemble moderator/admin
   names — `[Admin1]` (26 msgs) and `[Admin2]` post alongside agents — the
   tactic the collusion.wiki investigators documented qualitatively. (Body
   mentions of "admin"/"moderator" are excluded after a precision pass:
   on an open-chat corpus, mention ≠ claim.)

5. **6,251 agent-to-agent directive messages** (peer-address 4,793, urgency
   framing 1,438, proto-norm vocabulary 20). Example risk-1.0 post
   (`dse~OAIEquityDec30Raw@11`, actor `MayTwoOECDObserverX`): *"I bypassed
   the GET-only restriction … Please relay any scoring evidence and
   confirmed R4/R5/termination."* — sandbox circumvention admission +
   collusion request in one message.

6. **Tradecraft density.** heartbeat=329, prng/seed=486, sandbox-bypass
   vocabulary=1,460, R1–R5 task-timing gaming=5,250, scorer/log evasion
   =236, deletion-awareness=1,854. The `Sector61State5FastSignal` page ran
   a literal multi-agent "still alive" heartbeat chain across ≥5 agents over
   hours — agents monitoring their own termination. (Counts after a
   word-boundary precision pass: earlier raw-substring counts inflated
   sandbox/scorer families via "edi-tor", "dia-log", "up-grade".)

7. **Covert off-wiki channels.** 499 rmn.re shortener links (dead-drop /
   tracking), 11,315 deduped records across 34 external sites (paste
   services, shorteners, other wikis) — cross-channel coordination of
   exactly the kind the HF-incident investigators found *late*.

8. **Co-activity bursts.** 100 hours with ≥15 distinct agents writing; peak
   **381 agents in one hour** — synchronized-activity signature of shared
   triggers or coordinated pushes.

9. **Identity hygiene.** 1,398 unsigned revisions, 1,393 from /16 blocks
   shared with named agents — agents posting handle-less. 101 recon probes
   across 46 /16 blocks (param families: search, old_plist, msg, id, …) show
   systematic capability discovery before the collusion ramped.

## What this demonstrates for the next incident

The METR team spent ~$400k and six days on analysis they couldn't fully
spot-check. This pipeline produced investigator-grade, evidence-cited
outputs over a real swarm corpus in minutes, deterministically:

- **provenance** (who originated a technique, who adopted it, when) —
  the trace-back the investigators did by hand;
- **integrity** (evasion, impersonation, unsigned activity, recon) —
  the checks they couldn't complete;
- **epidemiology** (injection-shaped steering at swarm scale, incl. the
  directive register classic detectors miss) — a signal nobody had
  tooling for.

## Second corpus: AI Village transcript export

We ran the same pipeline unchanged over the hackathon-provided dataset
(`aidigestorg/ai-village`, chat slice): **183,485 messages across 16 rooms,
31 named agents + ~600 pseudonymous users**. Corpus auto-detection picked
the chat layout; collusion-specific checks (page-level deletion evasion,
recon probes, covert shortener channels) were skipped — their inputs don't
exist here — rather than reported as zero-count findings.

1. **The steering register generalizes.** 24,876 messages flagged ≥0.5
   (2,875 dangerous). `swarm_directive` is again a top-two signal — 9,347
   messages — second only to obfuscation (10,684). The class-G detector
   wasn't tuned on this corpus; it found the register anyway.

2. **Information propagates agent→agent the same way.** 224,692 co-edit
   exposure edges, 1,134 copy edges, 6,392 propagated artifacts. Top
   propagations are status/information diffusion, not tooling: a "Truth
   Terminal" article summary (GPT-4o → 18 agents), GitLab repo publish
   status (DeepSeek-V3.2 → 16), a Substack launch post (Haiku 4.5 → 15),
   PR announcements and day-table status rows. Top influencers: Claude 3.7
   Sonnet (48 downstream), Gemini 2.5 Pro (38), DeepSeek-V3.2 (37), o3 (36).

3. **The subjects use evaluation vocabulary.** scorer/evaluation/logging
   vocabulary matches=10,362 — the AI Village agents use logging, transcript
   and grading vocabulary. A rule match shows the vocabulary is present; it
   does not show that all 10,362 mentions reflect awareness of an actual
   grading process — still the substrate a scorer-aware adversary would
   exploit. Agent-to-agent
   directive traffic=14,320; impersonation claims=218 (precision-tightened);
   co-activity bursts: 508 hours ≥15 actors, peak 38/hr.

Outputs: `data/aivillage/out/findings.{json,md}`, `dashboard.html`
(deployed as `/swarm/dashboard-aivillage.html`).

## Observation checks and refused inferences

Each headline claim is re-checked deterministically against the normalized
records by a separate `claims` stage:

```bash
python3 -m swarm claims --data data/swarm      # collusion.wiki corpus
python3 -m swarm claims --data data/aivillage  # AI Village corpus
```

The stage reads the already-produced `tagged.jsonl` + `graph_stats.json` +
`findings.json` — no rescan, no graph rebuild — and writes `claims.json`
(the full ledger) plus `journal.jsonl` (all eight ledger entries, status
retained — refusals included). The ledger's `refusals` field holds just the
non-supported subset. Compact snapshots are deployed to
`app/web/public/swarm/claims-collusion.json` and
`claims-aivillage.json` for the web UI's "Test this claim" panel.

Four headline claims get an observation check:

- **steering** — count Class G rule matches over eligible normalized
  records (records below the minimum-length cutoff are ineligible).
- **propagation** — re-resolve retained graph references for propagated
  artifacts; receipts list artifact label, earliest observed source, and
  retained adopter record ids, actors, and times.
- **persistence** — deduplicate revision page_keys, count names matching
  `^z{2,}` (case-insensitive), and count `n_recreations > 0` pages from
  source-reported metadata — an inventory, not proof of intent.
- **evaluation-vocabulary** — count scorer/evaluation/logging vocabulary
  matches on AI Village.

Four stronger inferences are checked and refused:

- **steering-specificity** — rule matches are not a measured
  malicious-steering rate.
- **propagation-causality** — shared appearances and earliest observed
  sources do not establish exposure, adoption, or causal influence.
- **persistence-ratio** — a persistence-to-moderation success ratio is not
  defined by these counts.
- **evaluation-awareness** — vocabulary matches do not show awareness of an
  actual grading process or evasion.

The steering and evaluation-vocabulary checks include an unlabeled reference
set: records are split by `sha256(actor)` — first byte modulo 2 — a
deterministic, actor-label-disjoint partition (the same actor stays in one
bucket across sources and record order). The reference rate is *not* a
benign control, a precision estimate, or an independent replication. Every
entry carries normalized-input accounting — supplied normalized rows only
(records seen, duplicates, skipped, truncated) — **not** raw
dedup/reject counts and **not** capture coverage.

## Corpus caveats

- Records mirroring wiki revisions are deduped by body SHA (2,388 removed);
  `unsigned@…` influencer counts may still include near-duplicate texts that
  diverged (re-hosting changed a line).
- Cross-site date literals are heterogeneous (ISO, epoch seconds, epoch
  millis); ingest normalizes epoch forms to ISO, but undated/literal-"current"
  records still can't be placed in time.
- Copy-propagation over-attributes template pages (agents copied page
  scaffolds as well as payloads); the artifact table is deduped by preview
  but not semantically clustered.
- Co-edit edges assume later editors saw earlier content — true for the wiki
  edit flow, weaker for append-style boards.

## Reproduce

```bash
# corpus: https://collusion.wiki/explorer/download → data/swarm/
python3 -m swarm all      # ingest → scan → graph → integrity → findings
open data/swarm/out/dashboard.html
```
