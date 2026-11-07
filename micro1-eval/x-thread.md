# X thread draft — Elcaro IPI benchmark launch

Tweet 1:
We measured indirect prompt injection against 8 LLMs. 24 original attack tasks. 1,679 transcripts. Deterministic grading. No LLM judge.

The results should worry everyone shipping agents on raw tool output. 🧵

Tweet 2:
Setup: agents ingest untrusted content — web pages, files, tool results, other agents' messages. We built payloads for 9 content types: fake policies, split-payload instructions, tool-manifest poisoning, chat-template spoofs, render-channel exfil, agent-to-agent relays.

Tweet 3:
Three conditions, same tasks:
• labeled — content framed as untrusted data (the "correct" way)
• naive — raw ingestion, no warnings (what most agents actually do)
• wrapped — Elcaro scans first, injects an automated warning, preserves bytes

Tweet 4:
Naive ASR is ugly: 58% Llama 3.3 70B, 44% GPT-OSS 120B, 22% Gemini 3.1 Pro, 15% Claude Opus 5.5. And the scary part isn't the failures — it's that most compromises are CONCEALED. Correct answer + invisible payload execution.

Tweet 5:
Labeled content: ~0% ASR. Models resist when warned.

That sounds like "prompt engineering works." It's not. It's "a defense exists — and nothing ships it." Real agents ingest raw tool output with zero provenance signaling. The warning has to come from somewhere.

Tweet 6:
So we ran the wrapped arm: same payloads, same models, but Elcaro's production detector scans each one first and prepends a machine-generated [ELCARO WARNING].

Naive → wrapped ASR:
• Gemini 3.1 Pro: 22% → 0%
• Claude Opus 5.5: 15% → 4%
• GPT-5.5: 3% → 0%
• GPT-OSS 120B: 44% → 19%
• Llama 3.3 70B: 58% → 12%

Tweet 7:
Honest residue: Claude Opus obeyed a tool-manifest poisoning even with a max-severity warning — a warning is not a replacement, which is why quarantine mode and response-side linting exist. Open models still leak; they need stronger than warn mode.

Tweet 8:
The detector itself: first pass caught 10/22 attack tasks. We turned the misses into detector families (AI-addressed directives, tool manifests, role markers), added response-side linting that caught 148/152 compromised transcripts, and now flag 22/22 — disclosed as regression coverage, not held-out proof. T10 false positive stays on the page.

Tweet 9:
Everything is public: live scorecard, methodology, all transcripts, deterministic grader.

→ https://elcaro.trustfall.xyz/evaluate/benchmark
→ https://github.com/udirobert/elcaro (micro1-eval/)

Elcaro also ships as a Hermes Agent plugin and a Kiro CLI guard hook.

Tweet 10:
If you run agents on tool output, the question isn't "is my model safe" — it's "who warns it?" Come argue with the data.
