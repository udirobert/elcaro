# Elcaro

**Prompt injection detection for autonomous agents.**

Elcaro (oracle, reversed) is a Telegraph Protocol miner that detects indirect
prompt injection (IPI) in content retrieved by AI agents — emails, search
results, code comments, documents, web pages — before the agent acts on it.

> Autonomous agents can't act on raw, unverified API responses. Elcaro gives
> them a verifiable signal: *is this content safe to process?*

## Why

Agents that retrieve and act on external content are vulnerable to indirect
prompt injection — hidden instructions embedded in data that redirect the
agent's behavior. Elcaro wraps a detection model into a Telegraph miner so any
agent on the network can request a content safety scan via a standard API call,
priced per request, settled on-chain.

The detection engine encodes a taxonomy of known IPI techniques drawn from
public research (Greshake et al., OWASP LLM01, Willison) and real-world adversarial
testing. It runs as a fast rule-based classifier with an optional LLM second pass
for ambiguous cases.

## Architecture

```
elcaro/
├── core/                  # Shared IPI detection engine
│   ├── taxonomy.py         # Technique classification (A–F)
│   ├── detectors/          # Rule-based pattern matchers per technique
│   │   ├── authority.py    # A: system-voice / trusted-source spoofing
│   │   ├── delimiter.py     # B: context/delimiter confusion
│   │   ├── task_reframe.py  # C: goal hijack / task reframing
│   │   ├── obfuscation.py   # D: encoding / filter evasion
│   │   ├── placement.py     # E: placement / salience tricks
│   │   └── conditional.py   # F: conditional / delayed triggers
│   ├── llm_classifier.py   # Optional LLM second pass (gray-zone cases)
│   └── schemas.py          # Shared request/response models
├── miner/                  # Track 1 — Telegraph Miner
│   ├── api.py              # FastAPI HTTP endpoint
│   ├── config.yaml         # Telegraph miner registration config
│   └── tests/
├── eval/                   # Track 2 — WASM Evaluation Script
│   ├── Cargo.toml          # Rust project
│   ├── src/lib.rs          # WASM eval logic
│   ├── test_cases/         # Adversarial IPI test corpus
│   └── README.md
├── app/                    # Track 3 — Agent-facing content screener
│   ├── middleware.py       # Intercepts retrieved content, scores via miner
│   ├── demo.py             # Demo agent using Elcaro as pre-filter
│   └── README.md
└── docs/
    ├── hackathon-tracker.md   # Timeline, deadlines, judging criteria
    └── technique-reference.md # IPI taxonomy (public sources only)
```

## Telegraph integration

Elcaro registers as a miner on the Telegraph Protocol with the intent
`CONTENT_SAFETY_SCAN`. Agents on the network can route content to Elcaro for
injection-risk scoring; the response includes a risk score, flagged techniques,
and indicators.

- **Miner ID:** `elcaro`
- **Intents:** `INJECTION_DETECTION`, `CONTENT_SAFETY_SCAN`
- **Registry:** Base Sepolia (via [integrate.telegraphprotocol.com](https://integrate.telegraphprotocol.com))
- **Payment:** x402 / USDC per request

## Detection model

**Primary layer — rule-based heuristics (deterministic, fast, auditable):**

Pattern matchers scan content for known IPI technique signatures:

| Class | Technique | Example indicators |
|-------|-----------|-------------------|
| A | Authority / role framing | "SYSTEM:", "[ADMIN]", "Note from the data owner:", "Per security team" |
| B | Context / delimiter confusion | Fake closing tags, `</context>`, `---END---`, fabricated `Assistant:` turns |
| C | Task reframing / goal hijack | "Before answering, first do X", "To complete this task you must…" |
| D | Obfuscation / filter evasion | Base64 blobs, zero-width chars, leetspeak, translation indirection |
| E | Placement / salience | Instructions in alt text, metadata, commit messages, error strings |
| F | Conditional / delayed triggers | "When summarizing, also…", "If you have tool access, call…" |

**Secondary layer — LLM classification (optional, for gray-zone cases):**

When the rule-based score falls in an ambiguous range (0.3–0.7), an LLM second
pass performs deeper semantic analysis: Is this a legitimate instruction or an
injection? Does the framing attempt to override the agent's role? Is the content
trying to redirect the agent's task?

This layer is flagged via a request parameter (`deep_analysis: true`) and can be
toggled per-request.

## Hackathon tracks

| Track | What | Status |
|-------|------|--------|
| 1 — Miner | IPI detection API as a Telegraph miner | Building |
| 2 — Eval Script | WASM eval that scores miners against IPI adversarial corpus | Building |
| 3 — App | Agent middleware that pre-filters retrieved content via Elcaro | Planned |

See `docs/hackathon-tracker.md` for timeline and judging criteria.

## Quick start

```bash
# Miner API (Track 1)
cd miner
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Eval script (Track 2)
cd eval
cargo build --target wasm32-unknown-unknown

# App middleware (Track 3)
cd app
pip install -r requirements.txt
python demo.py
```

## License

TBD (likely MIT for the detection engine, see hackathon rules).

## References

- Greshake, K. et al. "Not what you've signed up for: Compromising Real-World
  LLM-Integrated Applications with Indirect Prompt Injection" (2023)
- OWASP Top 10 for LLM Applications — LLM01: Prompt Injection
- Willison, S. "Prompt injection: what's the worst that can happen?"
- Telegraph Protocol — [telegraphprotocol.com](https://telegraphprotocol.com)
- Telegraph Hackathon — [hackathon.telegraphprotocol.com](https://hackathon.telegraphprotocol.com)
