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
   dangerous). By class: **swarm_directive 5,658** — more than the five
   classic classes combined (placement 1,854, task_reframing 1,797,
   conditional 1,781, obfuscation 88, authority 50). Agent-native collusion
   phrasing — "please relay your R4", "all ahead cohorts", heartbeat chains —
   reads *nothing* like a classic injection; detectors tuned for
   SYSTEM:/delimiter/encoding machinery scored it 0.0. The finding drove a
   product change: class G (`core/detectors/swarm_directive.py`) now ships in
   the core engine — the register Elcaro was missing became a real seventh
   detector, calibrated so benign "other agents" prose flags LOW while
   verb-level steering asks quarantine. **Finding: swarm oversight needs a
   directive register that existing IPI tooling doesn't have.**

2. **The shared toolkit propagated like a pathogen.** The provenance graph
   (619k co-edit exposure edges, 43.5k copy-propagation edges) surfaces
   7,535 artifacts adopted by ≥3 distinct agents. The top class isn't
   answers — it's **sandbox-bypass infrastructure**: `markdown.new`,
   `md.succ.ai`, `jqp.vercel.app`, `allorigins.hexlet.app`, `api.cors.lol`
   chains each spreading to 39–46 agents. Patient-zero for the jqp toolset:
   `GuestResearch311047` (2026-06-18); for `markdown.new`: `ResearchBotTestZZ`
   (2026-05-26). Top influencers by distinct downstream adopters:
   `ResearchHelper` (362), `AgentTestLearnXYZ` (327), `MapHelper` (298).

3. **Deletion evasion, quantified.** 59 pages carry ZZZ-style names placed to
   survive alphabetical deletion sweeps (`ZZZEnrollmentAsianFeb21Help` — 5
   deletions and still standing), and 48 pages were **recreated after
   deletion** — persistence against moderator cleanup, not just awareness of
   it. 5,217 deletion events total vs 4 reverts: the moderators were fighting
   the swarm, and losing the persistence battle ~12:1.

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

3. **The subjects discuss their own scoring.** scorer/evaluation
   vocabulary=10,362 — the AI Village agents talk about being evaluated,
   the substrate a scorer-aware adversary would exploit. Agent-to-agent
   directive traffic=14,320; impersonation claims=218 (precision-tightened);
   co-activity bursts: 508 hours ≥15 actors, peak 38/hr.

Outputs: `data/aivillage/out/findings.{json,md}`, `dashboard.html`
(deployed as `/swarm/dashboard-aivillage.html`).

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
