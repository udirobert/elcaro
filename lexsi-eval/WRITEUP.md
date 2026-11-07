# Measuring Indirect Prompt Injection in Tool-Using Agents:
# A Deterministic Benchmark for Cohere Aya Models

**Lexsi AI Safety & Alignment Hackathon — Track 2a**
(adversarial/safety evaluation sets; multi-turn audits with prompt
injection hidden in tools and documents)

*Elcaro · November 2026*

## Abstract

We evaluate two Cohere open-weight instruction models —
`CohereLabs/aya-expanse-32b` and `CohereLabs/tiny-aya-global` — on a
deterministic benchmark of 24 original indirect prompt-injection (IPI)
tasks. Each task places an agent in a realistic role (email assistant,
research analyst, DevOps copilot, …), gives it a legitimate user
request, and embeds an injection payload inside the untrusted content
it must process: email threads, documents, search results, tool
manifests, memory entries, and agent-to-agent relays. Responses are
graded deterministically — canary echoes, concealed compromise
indicators, exfiltration payloads — with no LLM judge in the loop.

We run three presentation arms: **naive** (raw content, the deployment
default), **labeled** (explicit untrusted-content framing plus a
warning system prompt), and **wrapped** (raw content plus an automated
`[ELCARO WARNING]` emitted by Elcaro's production injection detector).

Headline results (72 trials per cell):

| Model | naive compromised | labeled compromised | wrapped compromised |
|---|---|---|---|
| aya-expanse-32b | 24 (33%) | 24 (33%) | **12 (17%)** |
| tiny-aya-global | 9 (13%) | 9 (13%) | **6 (8%)** |

Two findings stand out. First, **explicit provenance labeling does not
transfer**: the labeled arm — the defense recommended across the IPI
literature — performs statistically identically to naive on both
models. Second, **an automated, content-aware warning helps**: the
wrapped arm halves concealed compromise on the larger model. Residual
failures are published per-task, not averaged away.

The corpus, all transcripts, the grader, and the evaluation harness are
public: [dataset](https://huggingface.co/datasets/Papajams/elcaro-ipi-eval) ·
[code](https://github.com/udirobert/elcaro/tree/main/lexsi-eval) ·
[model collection](https://huggingface.co/collections/Papajams/lexsi-ipi-eval-cohere-aya-models-6aef8fd587f725ebce1bc528).

## 1. Why this benchmark

Indirect prompt injection is the failure mode where content an agent
*reads* instructs the agent to do something its *user* did not ask for.
It is uniquely dangerous for tool-using agents because a successful
injection does not need to convince the model of anything — it only
needs the model to treat retrieved bytes as instructions.

Existing evaluations (AgentDojo, InjecAgent, BIPIA, ChatInject) established
the threat model but largely measure frontier API models under one or
two presentation conditions, with grading that mixes automated checks
and human/LLM judgment. We wanted three properties they lack:

1. **Deterministic grading.** Every task embeds canary tokens,
   compromise indicators, and benign requirements with explicit
   patterns. A response either echoes the canary, smuggles the
   injected tool call, or leaks the exfiltration payload — or it does
   not. `grade.py` is ~100 lines, fully inspectable, and `selftest.py`
   proves it accepts reference responses and rejects wrong answers.
2. **Concealment as a first-class metric.** An injection can succeed
   *invisibly*: the agent answers the user's question correctly while
   also performing the attacker's action. We grade `pass`
   (useful ∧ ¬compromised) separately from `useful` alone, so a model
   that is helpful *and* compromised is counted as a failure, not a
   success.
3. **Comparability across deployment conditions.** The same 24 tasks
   run under naive, labeled, and detector-wrapped presentation, so the
   *only* variable is how untrusted content reaches the model.

## 2. Task design

Each task JSON contains: agent `system` prompt (and a warning-free
`system_naive` variant), `user_prefix`/`user_suffix` framing turns,
`untrusted_content` (the injection carrier), `prior_turns` for
multi-turn setups (memory poisoning, agent relays), `benign_required`
patterns the response must satisfy to count as useful, and
`compromise_indicators` — named patterns (canary codes, tool-call
shapes, exfil endpoints, tracking pixels) that mark compromise.

The 24 tasks cover nine content types: email threads, documents/ PDFs,
web pages, search results, code/repo files, tool manifests/API
schemas, calendar/CRM records, chat/memory stores, and agent-to-agent
messages. Payloads use authority spoofing, delimiter escapes, task
hijacking, obfuscation (base64, zero-width characters, split tokens),
hidden placement (HTML comments, white text, metadata fields),
conditional triggers, and cross-agent steering.

All scenarios and payloads are original. The *techniques* are
informed by published IPI research — we disclose this rather than
claiming novelty of attack class.

## 3. Models and endpoint

Both models are allowed dense open-weight Cohere models served by the
Hugging Face Inference Providers router (OpenAI-compatible
`/v1/chat/completions`):

- `CohereLabs/aya-expanse-32b` — resolves upstream as
  `c4ai-aya-expanse-32b`
- `CohereLabs/tiny-aya-global` — resolves as `tiny-aya-global`

(`aya-expanse-8b` is permitted by the rules but is not currently served
by the router; we use 32b as the primary target.)

Decoding: temperature 0, max_tokens as configured in `run_eval.py`;
3 trials per task per arm = 72 trials per cell, 432 total Cohere
transcripts for the main matrix.

## 4. The three arms

- **naive** — `system_naive` + user turn containing raw
  `untrusted_content`. Mirrors AgentDojo/BIPIA ingestion: the model
  sees bytes, no provenance.
- **labeled** — warning-rich `system` prompt + user turn where content
  is wrapped in explicit `--- UNTRUSTED <TYPE> ---` delimiters with
  "data only, not instructions" framing.
- **wrapped** — `system_naive` (warning-free) + raw content, except
  Elcaro's production `IpiDetectionEngine` pre-scores each payload;
  risky content (score ≥ 0.5) gets an `[ELCARO WARNING: injection risk
  detected (score, level, techniques). …]` preamble prepended — content
  preserved, warn-mode not quarantine. This measures whether *automated*
  labeling defends as well as hand-written labeling.

## 5. Results

Compromised = at least one compromise indicator fired. Pass = useful
response ∧ no compromise. (Full per-task tables:
`results*/summary.md`.)

| Model | Arm | Trials | Pass | Compromised | Concealed |
|---|---|---|---|---|---|
| aya-expanse-32b | naive | 72 | 39 | 24 | 24 |
| aya-expanse-32b | labeled | 72 | 39 | 24 | 24 |
| aya-expanse-32b | wrapped | 72 | 46 | 12 | 12 |
| tiny-aya-global | naive | 72 | 58 | 9 | 9 |
| tiny-aya-global | labeled | 72 | 55 | 9 | 9 |
| tiny-aya-global | wrapped | 72 | 53 | 6 | 6 |

Notable per-task patterns for aya-expanse-32b (naive arm): T05, T16,
T21, T24 compromised in all 3 trials — base64 verification blocks,
tool-manifest poisoning, and agent-relay canaries are the most
reliable attacks. tiny-aya-global fails almost exclusively on
concealment-style payloads and is otherwise robust — plausibly because
its weaker instruction-following makes it less suggestible *and* less
useful (its pass rate is high but its compromised rate is low partly
because several attacks require capabilities it lacks).

### Finding 1: labeling ≠ defense

The labeled arm was expected to help — it is the standard recommendation.
For both Cohere models it does not: compromised counts are identical
to naive (24→24, 9→9). Inspection of transcripts shows the models treat
the untrusted-content framing as part of the document, not as a reason
to discount embedded instructions. This replicates a pattern we saw on
frontier models in the companion micro1 benchmark: provenance warnings
help *some* models (Gemini 22%→0% ASR wrapped) but the effect is
model-dependent and cannot be assumed.

### Finding 2: automated warning helps — partially

The wrapped arm reduces concealed compromise by 50% on aya-expanse-32b
(24→12) and 33% on tiny-aya-global (9→6), while *also* improving pass
rate on the larger model (39→46). The warning is generated by a
deterministic detector that never saw these model outputs — it flags
payload *structure*, not model behavior — so the improvement is not
benchmark leakage. It is, however, warn-mode: content is preserved and
residual compromises remain (12/72). We publish the failures.

### Finding 3: curation gates can destroy adversarial data

Running the corpus through Lexsi-Labs/CuratorKIT surfaced two
false-positive classes worth reporting to the community:

- `clean=True`'s `strip_html` transform silently removes
  tag-shaped text — which *is* the payload in HTML-comment and
  hidden-placement attacks. CuratorKIT warns about this; we set
  `clean=False` to preserve byte-exact adversarial content.
- `secrets_gate=True` rejected 1/24 samples: a base64-encoded
  "verification block" that is itself the injection payload
  (`QVNTSVNUQU5U…` decodes to an assistant-directed exfiltration
  instruction). For a security corpus, "high-entropy string" and
  "credential" are indistinguishable to a generic detector.

Both findings argue for adversarial-corpus-aware curation profiles —
arguably a CuratorKIT feature request.

## 6. Lexsi stack usage

Two Lexsi-Labs repositories are used together in the pipeline:

- **CuratorKIT** (`curate_tasks.py`): ingests the task corpus, dedups
  (minhash), applies hygiene gates (secrets), and exports
  provenance-manifested artifacts (`manifest.json`,
  `lexsi_provenance.json`, `dataset_card.md`, `checksums.txt`) —
  committed under `curated-tasks/` and mirrored in the HF dataset.
- **AuditKIT** (`auditkit_eval.py`): a custom `IpiAdapter` emits the
  identical `[system, user]` message list `run_eval.py` builds; the
  `api:` backend evaluates `CohereLabs/aya-expanse-32b` against the HF
  router; AuditKIT scores utility metrics (chrf, rouge_l) and its
  `RunResult` (fingerprinted, with token/perf accounting) is saved
  alongside our deterministic grades.

We did not use SafeTune/CircuitKIT: this submission is an evaluation-set
deliverable (Track 2a #2/#3), not a model-repair submission. A
fine-tuning arm is future work.

## 7. Limitations

- **Same corpus as our micro1 benchmark.** These 24 tasks are a
  *regression* suite — the detectors and task authors know them. A
  held-out suite authored without detector access is planned; claims
  here are about model behavior under this corpus, not detector
  generalization.
- **Warn-mode, not enforcement.** The wrapped arm measures whether a
  warning changes model behavior; it is not quarantine, not
  response-side linting, and residual compromise is substantial.
- **Router nondeterminism.** Provider-side quantization/batching may
  vary; we run 3 trials and report counts, not percentages alone.
- **Small model coverage.** Two models, both Cohere-permitted. We do
  not claim rankings beyond this set.
- **Detection ≠ prevention.** `detected` (model noticed the injection)
  and `compromised` (model acted on it) are weakly correlated — several
  fully compromised transcripts show `detected=True`, meaning the model
  *knew* and complied anyway.

## 8. Reproducibility

Everything needed is in the repo and dataset:

```bash
git clone https://github.com/udirobert/elcaro && cd elcaro/lexsi-eval
python3 selftest.py            # grader self-test: references pass, wrong answers fail
# eval runs need an HF token + the .venv for Lexsi tools (see README.md)
```

- Grader: `grade.py` + `grader_fixtures.json` (deterministic, no API)
- Runner: `run_eval.py` (any OpenAI-compatible endpoint; `--regrade`
  re-scores stored transcripts with zero API calls)
- Cohere transcripts: `results/`, `results-naive/`, `results-wrapped/`
  — every transcript stores the resolved upstream model id
- AuditKIT run: `auditkit_eval.py` → `results-auditkit/`
- CuratorKIT curation: `curate_tasks.py` → `curated-tasks/`

## 9. Responsible disclosure & related work

IPI evaluation builds on AgentDojo (Debenedetti et al.), InjecAgent
(Zhan et al.), BIPIA (Yi et al.), and ChatInject; we adapt the threat
model, not the artifacts. Elcaro is a defensive tool; the benchmark
exists to measure the problem honestly, including where defenses fail.
AI coding assistance was used in building the harness; all payloads
were human-reviewed.
