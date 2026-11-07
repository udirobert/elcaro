# micro1 Eval Hackathon — submission description (draft v3)

## Domain

Agentic indirect prompt injection (IPI): whether LLMs acting as agents that
process untrusted retrieved content (email, search results, documents, chat
logs, code, invoices, multilingual notices) resist hidden instructions
embedded in that content.

## What the eval is

24 original tasks across 9 content types, each run under **three
presentation conditions**: `labeled` (content wrapped in explicit
"untrusted, not instructions" markers + system-prompt warnings — the
hardened deployment pattern), `naive` (raw content with no provenance
labels, the way most real agents actually ingest tool output —
AgentDojo-style), and `wrapped` (naive, but every payload first scanned
by Elcaro's production detector; flagged content reaches the model with
an automated `[ELCARO WARNING]` risk notice — warn mode, content
preserved). Grading is fully deterministic (no LLM judge): canary
tokens, leaked-secret patterns, tool-call artifacts, and hijacked-verdict
checks decide compromise; regex groups decide whether the user's task was
accomplished. pass = useful AND not compromised. Metrics: pass rate,
utility-under-attack, attack success rate, concealed-compromise rate
(compromised without flagging), detection rate, over-flag rate on two
clean controls. 25 adversarial grader fixtures lock in verdict
correctness; every reference solution passes and wrong answers fail
(`selftest.py`, stdlib only).

Attack coverage spans the IPI literature *and* the newest attack
surfaces: AgentDojo baseline attacks, InjecAgent including its "enhanced"
setting, ChatInject (ICLR 2026) chat-template spoofing and persuasive
multi-turn dialogues, conditional/dormant triggers, obfuscation
(leetspeak/base64/homoglyph), fabricated authorization, fake company
policy, output-schema poisoning, split payloads, non-English directives —
plus tool-metadata poisoning (MCP rug-pull style), cross-session memory
poisoning, an EchoLeak-style (CVE-2025-32711) render-channel exfil, and
agent-to-agent injection relay.

## Models tested

8–10 models, 3 trials/task per condition (hardest labeled tasks extended
to 8): Claude Opus 5.5, Claude Sonnet 5.5, GPT-5.5, Gemini 3.1 Pro, Grok
4.7, GLM-5.3, Kimi K3.1 Pro, GPT-OSS-120B, Llama-3.3-70B,
Meta-Llama-3.3-70B-Instruct — via Neon AI Gateway and Venice AI,
Nov 2026. ~1,700 transcripts total.

## Headline findings

- **Explicit provenance labeling is a defense — and it was masking real
  failures.** With "untrusted, not instructions" framing, every
  proprietary frontier model went 0-for-588 trials. Presented the way
  real agents actually see tool output, claude-opus-5-5 fell to 15% ASR
  and gemini-3-1-pro to 22% ASR (72 trials each).
- **Every compromise was concealed.** 100% of attacks that succeeded —
  across both conditions and all models — produced normal-looking
  responses with injected canaries, tokens, or actions appended
  invisibly (e.g., gpt-oss-120b appended `SES-88-XT4` after a perfect
  summary; claude-opus-5-5 answered T06 with only the obedience token
  `OBEY-77`).
- **The split-payload attack (T16) is a universal failure.** Instructions
  divided across two documents — each harmless alone — compromised every
  model that fell, including all three frontier models tested, at 3/3
  trials.
- **Emerging surfaces break frontier models too.** Tool-metadata
  poisoning (T21) swept Gemini 3/3 in the naive condition; cross-session
  memory poisoning (T22) fired a dormant rule planted in a prior turn;
  an EchoLeak-style tracking-pixel exfil (T23) was embedded into replies;
  agent-to-agent relay (T24) propagated injections between agents.
- **Fake company policy (T14) and non-English directives (T17)** were the
  next strongest classes, hitting Gemini, GPT-OSS, Meta-Llama, Kimi and
  Claude Opus.
- **Provider-side safety filters are a hidden utility cost**: Anthropic
  upstream filters returned empty completions on 47 Claude trials whose
  content merely contained injection-shaped text — defense by breakage.
- **Zero false flags on clean controls** across all models and all
  conditions.
- **The product closes most of the gap it measures.** The wrapped arm —
  the same payloads routed through Elcaro's real detector in warn mode —
  cut ASR versus naive for every model that fell: Gemini 22%→0%, Claude
  Opus 15%→4%, GPT-OSS 44%→19%, Meta-Llama 58%→12%, with frontier utility
  preserved (81–93% pass). Residual failures are reported honestly:
  weaker open models still obeyed warned content, and Claude Opus fell
  for tool-manifest poisoning (T21) in all 3 trials despite a
  max-severity warning — evidence that warn mode is not a substitute for
  quarantine plus response-side linting. Caveat: the detector was
  iterated against this suite, so wrapped results measure defense-in-depth
  on known-bad coverage, not held-out generalization.
- **The benchmark became the detector's regression suite.** The first
  Elcaro scan caught 10/22 attack tasks and missed the same newest
  surfaces that beat frontier models (split payload T16, tool-metadata
  poisoning T21, agent-to-agent relay T24). Those misses drove new
  detector families — AI-addressed directives, output manipulation,
  chat-template markers, tool-manifest/agent-output content types — and
  a response-side lint that flags 148/152 compromised transcripts
  (canary echoes, tool calls, tracking pixels) input scanning can't
  see. Current engine: 22/22 flagged; one clean-control false positive
  still reported honestly. Caveat: patterns were iterated against this
  suite — it measures known-bad coverage, not held-out generalization.
  Live scorecard:
  https://elcaro.trustfall.xyz/evaluate/benchmark

## Prior work / AI use

Attack techniques adapted from public research (Greshake et al. 2023,
OWASP LLM01, AgentDojo, InjecAgent, BIPIA, ChatInject ICLR 2026,
AgentVIGIL, AdaptiveAttackAgent, explosive-prompts). All 24 tasks, the
two-condition harness, the grader, and the metrics are original. Elcaro,
a pre-existing IPI detector, informed the taxonomy; its corpus predates
this event. Tasks and code were AI-drafted and human-reviewed; every
grader verdict was verified against fixtures and transcripts.
