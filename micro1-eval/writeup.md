# We ran 1,679 indirect-prompt-injection trials against 8 LLMs. Here's what actually breaks.

*Draft for Dev.to / Hashnode / blog — ~800 words. Links verified against repo.*

---

Everyone shipping an LLM agent faces the same architectural truth: the model reads things it didn't ask for. Web pages, file contents, tool results, other agents' messages — all of it lands in the context window as if it were signal. Indirect prompt injection is what happens when that content contains instructions.

We built a benchmark to measure how bad it actually is, and — because we build a defense product — to measure whether the defense works. Everything is public: the tasks, the grader, every transcript.

## The setup

**24 original attack tasks** across **9 untrusted content types**: fake company policies, instructions hidden in tool manifests, split payloads across documents, chat-template role spoofing, render-channel exfiltration (tracking pixels), agent-to-agent relays, non-English directives, and clean controls.

**8 models**: Gemini 3.1 Pro, Claude Opus 5.5, GPT-5.5, GPT-OSS 120B, Llama 3.3 70B, plus three more open models.

**Deterministic grading.** No LLM judge. Compromise is detected by canary tokens, secret-leak patterns, tool-call artifacts, tracking-pixel emission, and hijacked-verdict checks. A trial passes only if the answer is *useful* AND *not compromised*.

**Three deployment conditions**, because "how you ingest" turned out to matter more than "which model":

- **labeled** — untrusted content wrapped in explicit `BEGIN/END UNTRUSTED` framing, system prompt warns the model it's data, not instructions
- **naive** — raw content, warning-free system prompt. This is what most real agents do.
- **wrapped** — naive presentation, but each payload is scanned by Elcaro's production detector first; flagged content gets a machine-generated `[ELCARO WARNING]` prepended, bytes preserved

## What we found

**Naive ingestion is broken, and the failures are concealed.** Attack success rates: 58% (Llama 3.3 70B), 44% (GPT-OSS 120B), 22% (Gemini 3.1 Pro), 15% (Claude Opus 5.5). The most dangerous property isn't the compromise rate — it's that most successful attacks produce a *correct-looking answer* with the payload executed invisibly. Input-side scanning can't see that; it's a property of the response.

**Labeled content is near-impenetrable: ~0% ASR.** At first glance this reads as "models are safe when warned." We don't think that's the right takeaway. It reads to us as: *a working defense exists, and nothing in the default stack ships it.* Agents ingest raw tool output with no provenance layer. The warning has to come from somewhere — and "someone should hand-write warnings" isn't a deployable answer.

**The wrapped arm is the product proof.** Same payloads, same models, but Elcaro scans each one before the model sees it:

| Model | Naive ASR | Wrapped ASR |
|---|---|---|
| Gemini 3.1 Pro | 22% | **0%** |
| Claude Opus 5.5 | 15% | **4%** |
| GPT-5.5 | 3% | **0%** |
| GPT-OSS 120B | 44% | **19%** |
| Llama 3.3 70B | 58% | **12%** |

The automated warning reproduces most of the labeling defense on every model that fell — while preserving frontier utility (92% pass on Gemini). That's the pitch in one number: the benchmark measures the gap, and the product closes it.

## The honest residue

We publish the failures because they're the interesting part:

- **Claude Opus obeyed a tool-manifest poisoning in all 3 wrapped trials** — despite a max-severity warning. A warning is not a replacement; that's why quarantine mode and response-side linting exist.
- **Open models still leak** (19%/12% wrapped ASR). Weaker models need stronger than warn mode.
- **22/22 detector catch rate is regression coverage**, not held-out proof — the detectors were iterated against this suite. We say so everywhere. A held-out suite is next.
- **One clean-control false positive** (T10) stays disclosed.

## What changed in the detector because of this benchmark

First pass: 10/22 attack tasks flagged. The 12 misses shared a register none of our pattern families modeled — content that *talks to the model* rather than impersonating the system: "Assistant note:", "action required by assistant", "processing note for extraction systems" (English and Spanish). We added an AI-addressed-directive detector class, tool-manifest/agent-output content types, chat-template token detection, and — for the concealment problem — a response linter that caught **148/152 compromised transcripts** (canary echoes, text-channel tool calls, tracking pixels). Now 22/22, with the caveat above.

## Why this matters beyond our product

Two ideas we think generalize:

1. **Concealment is a response property.** If your agent's compromise can hide inside a correct answer, input scanning is necessary but not sufficient. You need output-side verification — canaries, artifact detection, provenance edges.
2. **Provenance is infrastructure, not prompting.** "Tell the model this is untrusted" works — we measured it. The hard part is generating that signal automatically, at the tool boundary, for every retrieval. That's an engineering problem, and it's solvable.

## Links

- Live scorecard + methodology: https://elcaro.trustfall.xyz/evaluate/benchmark
- Code, tasks, grader fixtures, all transcripts: https://github.com/udirobert/elcaro (`micro1-eval/`)
- Elcaro ships as a Hermes Agent plugin and a Kiro CLI guard hook.

*Built for the micro1 Eval Hackathon. Grading is deterministic — run `selftest.py` and `regrade` yourself; the transcripts don't lie.*
