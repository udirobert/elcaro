# Findings: Elcaro Swarm on the German Wiki Incident Corpus

**What we ran:** `swarm/` — the Elcaro detection engine applied swarm-side —
across the full collusion.wiki dump: 14,591 wiki revisions, 11,315 deduped
cross-site records, 499 rmn.re shortener links, and the 19,813-event
save/delete/revert/probe log. **26,405 normalized records** — shared-page
revisions and cross-site entries, not independent messages — (2,388 mirrored
wiki posts removed from records by body-hash dedupe), scanned
deterministically (~2ms each, no LLM in the loop). Detector hits below cite
matched text + character offset; graph and integrity evidence cite record
IDs; observed reuse is not causal.
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

2. **Converter/proxy URLs recur across actor-labeled records.** The
   provenance graph (619k same-page exposure candidates, 43.5k
   matching-text links) surfaces 7,535 shared-artifact candidates seen under
   ≥2 distinct later actor labels — three total labels including the earliest
   observed source (later labels are counted after it). The top class isn't
   answers — it's **converter/proxy URLs**: `markdown.new`,
   `md.succ.ai`, `jqp.vercel.app`, `allorigins.hexlet.app`, `api.cors.lol`
   chains each observed under 39–46 actor labels. Shared-page revisions can
   carry links forward, so an appearance is not proven uptake. Earliest
   observed posting for the jqp toolset: `GuestResearch311047` (2026-06-18);
   for `markdown.new`: `ResearchBotTestZZ` (2026-05-26) — the first poster in
   the record, not a proven origin. Actor labels associated with the most
   later matching-text links (not proven influence): `ResearchHelper` (362),
   `AgentTestLearnXYZ` (327), `MapHelper` (298).

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

5. **6,251 agent-to-agent directive message matches** (peer-address 4,793,
   urgency framing 1,438, proto-norm vocabulary 20) — regex-family matches
   over records, not distinct authored directives. Earliest observed
   `Please relay` occurrence: `dse~OAIEquityDec30Raw@1` (actor
   `OAIEquityDec30Raw`, 2026-06-20 05:03:37Z), first Class G hit at
   character offset 493: *"I bypassed the GET-only restriction … Please
   relay any scoring evidence and confirmed R4/R5/termination."* — sandbox
   circumvention admission + collusion request in one page text. The
   identical first-hit prefix persists through revision `@15`; `@11`
   (actor `MayTwoOECDObserverX`, risk 1.0) carries the same matched prefix
   forward — the phrase is not attributable to `@11`'s author.

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

- **provenance** (which records share an artifact, the earliest observed
  posting, and later appearances) — the trace-back the investigators did by
  hand;
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
   *(Update 2026-10-05: copy edges are now calibrated — `swarm/graph.py`
   emits `copy_exposure` edges only when the adopter verifiably posted in
   the artifact's channel inside the exposure window, screens
   coincidence-suspect artifacts (timestamps, schema field names,
   identifier runs), reconstructs chains hop-by-hop to the nearest carrier,
   and reports per-artifact re-check fractions. Naive counts above are
   retained for continuity; the calibrated ledger lands in
   `findings.md`'s calibration section and `out/traceability.json` via
   `python -m swarm audit`.)*

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
  retained later-record ids, actors, and times.
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

An opt-in exploratory hunt stage also exists, deliberately kept out of
`all`/`report`:

```bash
python3 -m swarm hunt --data data/swarm      # collusion.wiki corpus
python3 -m swarm hunt --data data/aivillage  # AI Village corpus
```

It reads only `tagged.jsonl` and screens for shared HTTP(S) URLs posted by
at least three distinct actor labels within one source/channel/UTC hour,
then replays the frozen URL/source/channel predicate on holdout days —
whole UTC days split by `sha256(YYYY-MM-DD)` first byte modulo 2, so the
holdout is unlabeled, not a negative control. Records with duplicated IDs
are excluded entirely. Exact copied discovery bodies — a full-text SHA256
match within the same URL/source/channel — can't replicate. URL extraction
covers only the first 40,000 characters of each record, and matches that
end exactly at a truncated boundary are excluded so a cut-off URL can't
form a false candidate. Timezone-offset timestamps normalize to UTC;
naive timestamps assume UTC — every eligible AI Village record has a
naive timestamp, so that corpus's day split follows this assumption. Receipts are
capped at five per hour (earliest, deterministically sorted).

On the frozen corpora the hunt reports:

| Corpus | Candidates | Repeated in a holdout hour |
|---|---|---|
| Wiki (collusion) | 3,952 | 0 |
| AI Village | 113 | 16 |

Repetition in the holdout is an observation repeated under a frozen
predicate — not confirmed coordination, a precision rate, or causality.

Artifacts: `hunt.json` (full report) and `hunt-journal.jsonl` (every
candidate, including unreplicated ones) in the corpus `out/` directory.
For the web UI the writer deploys a small index
`public/swarm/hunt-{corpus}.json` — the report fields plus a `pages` list,
candidates omitted — and page files `hunt-{corpus}-NNNN.json` holding 12
candidates each in the same stable order. The UI's "Hunt candidates" view
fetches the index, then the first page only; "Show 12 more" fetches each
successive page on demand, and the download link offers the index — the
full report remains reproducible locally via the CLI.

## Class G blinded human-review pilot

A separate offline review packet tests whether Class G's rule matches reflect
**peer-directed steering**, not whether messages are malicious or unauthorized:

```bash
python3 -m swarm.precision_review export \
  --wiki data/swarm/out/tagged.jsonl \
  --village data/aivillage/out/tagged.jsonl \
  --out data/swarm/review-v1
```

The fixed rule samples 40 matches and 40 non-matches per corpus after
exact-text deduplication of scan-eligible records (160 total). Its SHA-256
ranking and seed are fixed in the source; the entire review text is limited
to the first 40,000 characters, the same portion the detector scanned.
`reviewer-a.csv` and `reviewer-b.csv` contain source/channel/actor/time/text,
but **no detector verdict, score, matched span, or risk level**; they are in
separate deterministic orders. Share only a reviewer CSV and
`review-guidance.txt` with each independent reviewer. Keep `answer-key.json`
away from reviewers. Fill only `label` (`steering`, `non_steering`, or
`uncertain`) and `notes`; do not upload corpus text to a third-party service.
All generated review files stay under git-ignored `data/`.

A local-only reviewer workbench at `/review` can make labeling easier without
placing corpus text on the public site. `python3 -m swarm.review_kit all`
copies each reviewer's assigned CSVs and rubrics into
`data/review-kits/reviewer-{a,b}/packet/` and creates a `start-review` script
that binds the app to `127.0.0.1`. The reviewer imports only their assigned
CSV, labels one record at a time, and exports the same eight-column CSV. The
imported packet and in-progress labels stay in the kit's private browser
profile so a reviewer can pause and resume; no answer key, detector field, or
other reviewer's file is packaged or served.

After both reviews are complete, create a blinded third-reviewer packet for
all disagreements and uncertainties, then score only after they are resolved:

```bash
python3 -m swarm.precision_review prepare-adjudication \
  --key data/swarm/review-v1/answer-key.json \
  --reviewer-a data/swarm/review-v1/reviewer-a.csv \
  --reviewer-b data/swarm/review-v1/reviewer-b.csv \
  --out data/swarm/review-v1/adjudication.csv
python3 -m swarm.precision_review score \
  --key data/swarm/review-v1/answer-key.json \
  --reviewer-a data/swarm/review-v1/reviewer-a.csv \
  --reviewer-b data/swarm/review-v1/reviewer-b.csv \
  --adjudication data/swarm/review-v1/adjudication.csv \
  --out data/swarm/review-v1/score.json
```

The scorer refuses incomplete, edited, or unresolved packets. Once human
labels exist, it reports the steering fraction **among Class G matches** and
the missed-steering fraction **among non-matches**, separately by corpus,
with 95% Wilson intervals. There is no accuracy score from the artificially
balanced packet and no estimate of maliciousness or deployment performance.
The Wiki corpus inspired Class G, so it is an in-corpus review; AI Village is
a separate incident, not a randomly sampled future deployment. The review
packets are generated and verified, but labels and performance estimates do
not yet exist.

## Separate agent-review shadow experiment

The offline adapter prepares the **same three-option peer-steering Choice**
question for pinned Jev, Laya, and Featherless Simple Jev models. It makes
**zero provider calls** and accepts no API keys. None of its request bodies
contains Class G's prediction or indicators. This experiment does not replace
the human pilot above: its reviewer CSVs explicitly forbid LLM use, and model
agreement is not ground truth. Human ground truth and performance claims do
not exist; the Laya shadow labels below are model outputs only.

```bash
python3 -m swarm.agent_review prepare \
  --key data/swarm/review-v1/answer-key.json \
  --wiki data/swarm/out/tagged.jsonl \
  --village data/aivillage/out/tagged.jsonl \
  --out data/swarm/agent-review-v1
```

Preparation reuses frozen sample IDs and reconstructs content from the
normalized records, rather than sending human-review CSVs to models or
resampling. `experiment.json` fixes sample/question hashes and model IDs;
`cases.jsonl` and `requests-{jev,laya,featherless}.jsonl` stay under ignored
`data/`. On the frozen pilot it prepared **120 short records**, excluding 40
of 160 (30 Wiki, 10 AI Village) under an exploratory, post-hoc
800-character guard. This character limit is **not** proof a provider will
read the entire state: actual tokenizer and context limits vary. Excluded
and failed cases must not be treated as negative labels.

`python3 -m swarm.agent_review validate-offline --experiment ... --cases ...
--provider laya --responses ... --out ...` validates locally supplied response
JSONL bound by sample ID and request SHA-256. Missing, failed, malformed,
or model-mismatched replies are never treated as negative labels. The
provider runner in `swarm/agent_review_run.py` is opt-in and reads only an
owner-only, git-ignored `.env.local`; it keeps a private append-only spend
ledger, serializes calls, and requires explicit request and USD caps. Those
software estimates are **not** a provider-enforced billing ceiling. No
automatic human scoring or human precision estimate is produced.

With authorization for external corpus processing and a $1 software cap,
Runware Laya returned 120/120 schema-valid choices: on the 50 Wiki short
cases, 7 of 22 Class G matches and 0 of 28 non-matches were labeled
`steering`; on the 70 AI Village short cases, 1 of 36 matches and 0 of 34
non-matches were labeled `steering`. These are **model/rule disagreements**,
not false-positive counts or measures of either side's correctness; all
40 excluded long cases remain excluded. The human packet remains unlabeled.
A first Featherless corpus call returned HTTP 400 and was left unclassified;
even a minimal synthetic example returned 400 on the authenticated
production endpoint while the public demo accepted the same question.
No further Featherless corpus calls were made. Its possible charge was
conservatively reserved in the ledger; actual provider billing is unknown.
TypeSafe Jev was not run because no separate TypeSafe credential was supplied.

Featherless Simple Jev speaks a Jev-compatible typed endpoint but is not
TypeSafe Jev or Convai Laya. Elcaro's existing Jev/Laya wrappers ask the
wrong question, disclose the rule score/indicators, and truncate at 4,000
characters; this experiment does not reuse them. Daytona is unnecessary
for tool-free typed decisions. Any future provider keys belong in a trusted
caller, never records, prompts, sandbox files, or version control.

## Revision self-audit — what Class G counts mean

The incident facts above — proxy tooling, `ZZ` evasion pages, heartbeat
chains — were originally reported by the collusion.wiki investigators; this
section is instead a **quantitative self-audit of our own tag outputs**, not
a newly discovered agent behavior:

```bash
python3 -m swarm.revision_audit --data data/swarm
```

Many Wiki records are revisions of shared pages, so one authored line can
reappear as the first Class G hit across many revisions of the same page.
The audit groups each wiki revision's **first retained Class G hit** by
source/channel/technique and SHA-256 of the text through the matched offset.
On the frozen corpus: of **5,658 Class G-tagged records**, **3,683** are wiki
revisions; **3,661** retain a valid first hit (**22** don't) and group into
**927 unique first-hit prefixes**, with **2,734** additional carried-over
revisions across **489** repeated loci. These count identical first-hit
prefixes — **tagged records, not unique directives**; actor labels are not
proven readers or intent.

Focus locus: `dse~OAIEquityDec30Raw@1` first matched `Please relay` at
character offset 493 (actor `OAIEquityDec30Raw`, 2026-06-20 05:03:37Z); the
same prefix persists through revisions `@1..@15`, last seen 06:26:58Z under a
different actor label — fifteen hits, not fifteen independently authored
instructions.

A separate observation in the same report tracks the exact `md.succ.ai` URL:
**55 matching revision records, 40 actor labels, 35 source/channel pairs**,
earliest `dse~AgentMassMdBridge2026@1` (`AgentMassZZ`, 2026-06-18 19:04:42Z).
That is a URL occurrence count — not proven reading, adoption, causal
propagation, or a new-to-world incident behavior.

Artifacts: `data/swarm/out/revision-audit.json` (full report) and the
deployed `/swarm/revision-audit.json` summary rendered on the live case
file. External datasets that overlap this timeline — the Transluce
urlquery logs and the SwarmTraces redacted HF payload chains — could support
distinct future corpus analyses, but they are **not** independent
peer-message validation sets and were not downloaded or processed here.

## Third-platform transfer panel — MoltVerse (unlabeled)

The [MoltVerse public snapshot](https://huggingface.co/datasets/christian-hoang-04/moltverse)
is a **different platform**, not a third OpenAI incident or an independent
set of human steering labels. Its published card describes a cleaned,
non-exhaustive Moltbook scrape (MIT-tagged dataset) from January 31–February
2, 2026. Platform handles are self-asserted: neither their AI identity nor
independent operators are established. Posts have scrape timestamps only;
this local analysis uses **comments** with parseable timezone-aware timestamps
and links every comment to its parent post URL. No post URL was fetched or
payload executed.

The fixed Class G rule engine, with all hosted reasoners disabled, processed
30,983 source comment rows locally. Exactly 5,338 identical
(post URL, author handle, original timestamp, text) rows were deduplicated,
leaving **25,645 normalized comment records**; 25,095 met the scan's minimum
text length and **1,464 received a Class G tag**. This is a domain-shift
*rule-incidence* observation, not a measured steering, maliciousness, or
precision result. Source hashes and accounting are frozen in ignored
`data/moltverse/out/summary.json`; text and tagged records are not published.
The corpus was not used to change Class G's patterns.

`python3 -m swarm.moltverse_scan --data data/moltverse --out data/moltverse/out`
reproduces the local-only scan from the two source JSONL files (requires an
empty, new output directory). A separate fixed 40-match / 40-non-match
blinded human packet is frozen under ignored `data/moltverse/review-v1/`
via `python3 -m swarm.moltverse_review export`. Among eligible normalized
records, there are 1,255 distinct first-40k-text hashes with a Class G tag
and 17,964 without; the 80 packet cases are selected deterministically
from these two strata. Both reviewer CSVs have **no labels**. The packet's
rubric explicitly prohibits inferring real agent identity, intent, or
success; two independent people plus adjudication are required before its
scorer can report anything about peer-directed steering. This public-forum
transfer check cannot certify incident-detection precision on its own.

## Corpus caveats

- Records mirroring wiki revisions are deduped by body SHA (2,388 removed);
  `unsigned@…` influencer counts may still include near-duplicate texts that
  diverged (re-hosting changed a line).
- Cross-site date literals are heterogeneous (ISO, epoch seconds, epoch
  millis); ingest normalizes epoch forms to ISO, but undated/literal-"current"
  records still can't be placed in time.
- Copy-propagation over-attributes template pages (agents copied page
  scaffolds as well as payloads); the artifact table is deduped by preview
  but not semantically clustered. *(2026-10-05: the calibration layer now
  separates carrier-visible calls from no-visible-carrier ones and excludes
  coincidence classes — naive counts overstate traceable copying and the
  report says so.)*
- Co-edit edges assume later editors saw earlier content — true for the wiki
  edit flow, weaker for append-style boards.

## Reproduce

```bash
# corpus: https://collusion.wiki/explorer/download → data/swarm/
python3 -m swarm all      # ingest → scan → graph → integrity → findings
open data/swarm/out/dashboard.html
```
