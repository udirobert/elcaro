# Elcaro — Project Context

## What Elcaro is

Elcaro (oracle, reversed) is an **indirect prompt injection (IPI) detection engine** packaged as a Telegraph Protocol miner. It scans content retrieved by AI agents — emails, search results, web pages, code, documents — and returns a risk score with flagged techniques and indicators before the agent acts on the content.

Autonomous agents can't safely act on raw, unverified external content. Elcaro gives them a verifiable signal: *is this content safe to process?*

## Hackathon context

**Telegraph Protocol — Season I Hackathon (H1)**

| | |
|---|---|
| Prize pool | $15,000 USD across 3 tracks |
| Track 1 & 2 open | Aug 17 – Sep 7, 2026 |
| Track 3 open | ~Aug 31, 2026 |
| Evaluation | Sep 7, 2026 |
| **Hard deadline** | **Sep 7, 2026** |

Today is August 8, 2026. There are approximately **30 days** to submission.

## Three tracks

| Track | What we're building | Status |
|---|---|---|
| **Track 1 — Miner** | FastAPI IPI detection API registered as a Telegraph miner | Code complete, needs deployment + registration |
| **Track 2 — Eval Script** | WASM evaluation script (Rust) that scores miners against an adversarial IPI corpus | Implemented, needs WASM ABI verification + submission |
| **Track 3 — App** | Agent middleware that pre-filters retrieved content via the Elcaro miner | Implemented, opens ~Aug 31 |

## Judging criteria (what matters for scoring)

### Track 1 — Miner
- Telegraph ranking & performance (eval script scores)
- Number of applications built on this miner
- Total requests served
- Progress updates posted on X + engagement

### Track 2 — Eval Script
- Telegraph's automated eval accuracy
- Accuracy of miner rankings produced
- Resistance to gaming
- Progress updates + community engagement

### Track 3 — App
- Users acquired & activity
- Usage and adoption
- Creativity and usefulness
- Must use Telegraph miners
- Engagement on posts showcasing the project

## Strategic differentiation

Elcaro is the **only content safety / IPI detection miner on the Telegraph network**. The 37 active miners as of Aug 2026 are: LLM chatbots, Tavily web search, OpenWeatherMap, Bedrock models, Bittensor subnets. We are creating a new supply category, not competing in an existing one.

The rule-based primary layer is a structural advantage: while LLM miners average ~12s latency, Elcaro's regex engine responds in under 10ms. Telegraph ranking factors in latency and reliability.

The self-reinforcing loop: Track 3 app drives real request volume to the Track 1 miner, improving ranking metrics used by Track 2 scoring. Building all three tracks is a deliberate strategy.

### Go-to-market wedge: email-processing agents

**Contrarian thesis:** AI agents are being deployed without any runtime content
safety layer. The industry focuses on model alignment while ignoring that the
data pipeline is the actual attack surface. Prompt injection is a content
scanning problem, not a prompt engineering problem.

**The wedge is email.** Email is the highest-risk content type (untrusted sender,
structured enough to carry injection reliably, real-world consequences). The
use case is explainable in one sentence: "We scan emails before your agent reads
them."

**Strategy:**
1. Find one team running an email-handling agent (customer support, inbox assistant, sales automation)
2. Offer free scanning of their email pipeline
3. Collect evidence: X emails scanned, Y injections caught, Z false positives
4. Use that data to win both hackathons (proof of real value, not a demo)
5. Expand from email → search results → documents → all content

**From wedge to platform:**
- Email → search results (same buyer, different source)
- Search results → documents (same buyer, different source)
- Documents → all content (now you're the platform)

**Monopoly dynamics (Thiel framework):**
- 10x better than the alternative (the alternative is nothing — no dedicated runtime scanner exists)
- Data network effect: every scan improves pattern detection
- Integration lock-in: once in the retrieval pipeline, hard to remove
- Trust: security products are bought on reputation; first mover builds it

## Technical registration flow (Track 1 critical path)

1. Deploy miner to VPS (reverse proxy + HTTPS via Caddy/nginx + Let's Encrypt)
2. Set `api.base_url` in `miner/config.yaml`
3. Pin `config.yaml` to IPFS via Pinata
4. Register on Base Sepolia at [integrate.telegraphprotocol.com](https://integrate.telegraphprotocol.com)
5. Set `registration.ipfs_hash` and `registration.registry_contract` in config

Payment: x402 HTTP payment protocol, settled in USDC per request.

## X posting cadence (judging includes this)

- [ ] Project announcement (what is Elcaro, why IPI matters for agents)
- [ ] Track 1 miner live (show the API working with a real detection example)
- [ ] Track 2 eval script (show the adversarial corpus, explain gaming resistance)
- [ ] Track 3 app demo (agent pre-filtering retrieved content)
- [ ] Results / leaderboard updates

## References

- Greshake et al. "Not what you've signed up for" (2023) — primary IPI research
- OWASP Top 10 for LLM Applications — LLM01: Prompt Injection
- Willison, S. "Prompt injection: what's the worst that can happen?"
- Telegraph Protocol — telegraphprotocol.com
- Hackathon — hackathon.telegraphprotocol.com
