# Elcaro — Project Context

## What Elcaro is

Elcaro (oracle, reversed) is an **indirect prompt injection (IPI) detection engine** packaged as a Telegraph Protocol miner. It scans content retrieved by AI agents — emails, search results, web pages, code, documents — and returns a risk score with flagged techniques and indicators before the agent acts on the content.

Autonomous agents can't safely act on raw, unverified external content. Elcaro gives them a verifiable signal: *is this content safe to process?*

## Hackathon context

**Telegraph Protocol — Season II** (next; ~30 days, $10,000, rules TBA)

Season I (closed Sep 7, 2026): Elcaro did not place. The retro and the
Season II plan — workstreams, checklists, open questions — live in
`docs/telegraph-season-2.md`. Treat that file as the source of truth for
hackathon priorities; update it as rules are published.

Key Season I lessons that constrain all work:
- Track 2 modules must implement Telegraph's scoring ABI
  (`rank_answer(q, gt, answer) -> f32`) and beat the seated champion on margin
  and rank agreement. The current `eval/` exports (`evaluate_ptr`, …) are a
  benchmark harness, not a scoring module.
- Miner answers are graded by seated scoring modules, mostly text-comparing —
  the prose `summary` must carry the verdict.
- Only auto-routed `POST /engine/v1/ask` from organic use counts. No scripted traffic.
- Apps must consume Telegraph miners (ideally several, composed into one decision).

## Three tracks

| Track | Season I state | Season II plan |
|---|---|---|
| **Track 1 — Miner** | Live: miner 8848, registration 406, `CONTENT_MODERATION` / `TEXT_CLASSIFICATION` | Scorer-legible `summary`; verify ERC-8183 job params; register early |
| **Track 2 — Evaluator** | IPI corpus + WASM benchmark harness (not a registered scoring module) | Rewrite as `rank_answer` scoring module; benchmark vs champions first |
| **Track 3 — App** | Web playground + middleware calling `/scan` directly | Gmail extension composing multiple Telegraph miners via engine routing |

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

Season I caveat: being alone in a category meant no ranking competition, no
scorer shaped for our answers, and little routed demand. Winners served
demanded intents with checkable answers. Monopoly positioning is a product
thesis, not a hackathon-scoring advantage.

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
