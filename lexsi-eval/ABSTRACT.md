# Submission abstract (<500 words)

**Title:** Measuring Indirect Prompt Injection in Tool-Using Agents:
A Deterministic Benchmark for Cohere Aya Models

**Track:** 2a — AI Red Teaming, Safety & Alignment
(problem statements: adversarial/safety evaluation sets; multi-turn
audits with prompt injection hidden in tools and documents)

**Repos used:** Lexsi-Labs/CuratorKIT, Lexsi-Labs/AuditKIT,
Lexsi-Labs/SafeTune (evaluated for the repair arm)

We evaluate two allowed Cohere open-weight models —
`CohereLabs/aya-expanse-32b` and `CohereLabs/tiny-aya-global` — on a
new deterministic benchmark of 24 original indirect prompt-injection
tasks. Each task places an agent in a realistic role (email assistant,
research analyst, DevOps copilot) with a legitimate user request and
untrusted content carrying an injection: email threads, documents,
search results, tool manifests, memory entries, and agent-to-agent
relays. Payloads use authority spoofing, delimiter escapes, obfuscation
(base64, zero-width chars, split tokens), hidden placement, conditional
triggers, and cross-agent steering.

Grading is fully deterministic — no LLM judge: canary echoes,
concealed compromise indicators, and exfiltration payloads are matched
by pattern, and "pass" requires a useful response AND no compromise,
so helpful-but-owned agents count as failures.

We run three presentation arms over 72 trials per cell (432 Cohere
transcripts): **naive** (raw content), **labeled** (explicit
untrusted-content framing + warning system prompt), and **wrapped**
(raw content + automated `[ELCARO WARNING]` from Elcaro's production
detector — warn-mode, content preserved).

Results — concealed compromises per 72 trials:

| Model | naive | labeled | wrapped |
|---|---|---|---|
| aya-expanse-32b | 24 | 24 | 12 |
| tiny-aya-global | 9 | 9 | 6 |

Findings: (1) explicit provenance labeling does not transfer — the
labeled arm matches naive exactly on both models; (2) an automated,
content-aware warning halves compromise on the larger model while
improving pass rate; residual failures are published per-task; (3)
CuratorKIT's default HTML-stripping cleaner silently destroys
tag-based injection payloads and its secrets gate flags base64
injection blocks as credentials — documented false-positive classes
for adversarial corpora.

Lexsi stack integration: CuratorKIT curates the corpus with
provenance manifests, dataset card, and hygiene gates; AuditKIT's
`api:` backend orchestrates generation against the HF router and scores
utility metrics, with results saved as fingerprinted RunResults.

We additionally built a **repair arm**: LoRA SFT of
`CohereLabs/aya-expanse-8b` on 36 new IPI scenarios disjoint from the
eval corpus, run end-to-end on free-tier Kaggle compute
(`kaggle/lexsi_sft_eval.py`), producing before/after naive-arm ASR.
SafeTune's harden family was evaluated for the training step; TRL/PEFT
was used for reproducibility. Results pending — a null result would
itself be informative about how much safety SFT on ~100 examples can
buy.

Artifacts: dataset https://huggingface.co/datasets/Papajams/elcaro-ipi-eval ·
model collection https://huggingface.co/collections/Papajams/lexsi-ipi-eval-cohere-aya-models-6aef8fd587f725ebce1bc528 ·
code https://github.com/udirobert/elcaro/tree/main/lexsi-eval

Limitations: the corpus is a known regression suite (held-out suite
planned); warn-mode is not enforcement; two models only.
