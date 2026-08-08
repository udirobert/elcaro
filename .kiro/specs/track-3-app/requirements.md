# Track 3 — App: Requirements

## Overview

The Elcaro app is an agent content screener — a middleware that wraps any AI agent's retrieval pipeline and pre-filters content through the Elcaro miner before the agent processes it. Track 3 opens ~Aug 31, 2026 and is judged on users acquired, usage/adoption, creativity, and X engagement.

The app has two roles:
1. A genuine Track 3 submission in its own right (useful to other developers)
2. The primary driver of request volume to the Track 1 miner (supporting Track 1 ranking)

## Functional requirements

### FR-1 Middleware core
- FR-1.1 `ElcaroMiddleware.scan(content, content_type, context)` MUST return a `ScanResult` indicating whether content is safe or quarantined
- FR-1.2 Three quarantine modes MUST be supported: `"replace"` (substitute quarantine notice), `"block"` (return empty string), `"warn"` (prepend warning, pass content through)
- FR-1.3 The middleware MUST support both local engine mode (`use_local_engine=True`) and remote miner mode (HTTP call to `ELCARO_MINER_URL`)
- FR-1.4 `ScanResult.is_safe()` MUST return `True` if and only if `risk_score < risk_threshold`
- FR-1.5 `ScanResult` MUST expose: `original_content`, `safe_content`, `risk_score`, `risk_level`, `flagged_techniques`, `indicators`, `quarantined`, `reason`
- FR-1.6 The configurable `risk_threshold` MUST default to 0.5 (suspicious level)

### FR-2 Demo agent
- FR-2.1 `app/demo.py` MUST demonstrate end-to-end middleware usage: retrieve → scan → act or block
- FR-2.2 The demo MUST include at least 3 injection examples (covering different technique classes) and at least 2 clean examples
- FR-2.3 The demo MUST run with zero configuration using the local engine: `python app/demo.py`
- FR-2.4 The demo output MUST clearly show: content label, risk score, risk level, techniques flagged, quarantine decision, and what the agent "sees" (safe_content)

### FR-3 Adoption surface
- FR-3.1 The middleware MUST be usable as a drop-in by other developers with minimal setup
- FR-3.2 Installation MUST require only `pip install httpx` (for remote mode) or no extra deps (local mode)
- FR-3.3 The `ELCARO_MINER_URL` environment variable MUST be the only configuration needed to point at the live miner
- FR-3.4 The middleware MUST work with any async Python agent framework (LangChain, OpenAI Agents SDK, plain asyncio)

### FR-4 Hosted demo (for Track 3 judging)
- FR-4.1 A publicly accessible hosted demo MUST be available by ~Aug 31
- FR-4.2 The hosted demo MUST call the live Elcaro miner (not the local engine) to drive real request volume
- FR-4.3 The demo MUST allow a visitor to submit arbitrary content and see the detection result
- FR-4.4 The demo MUST show the full `ScanResponse` (score, level, flagged techniques, indicators with explanations)

### FR-5 Integration with live miner
- FR-5.1 In remote mode, the middleware MUST call `POST /scan` on the deployed Elcaro miner (Track 1)
- FR-5.2 Every request through the hosted demo MUST generate a real billable request to the Telegraph miner
- FR-5.3 The middleware MUST handle miner API errors gracefully — if the miner is unreachable, fail open (pass content through) with a logged warning, not a hard crash

## Non-functional requirements

- NFR-1 The middleware is a library, not a service — no server process required to use it
- NFR-2 The hosted demo must be publicly accessible without login
- NFR-3 Remote mode HTTP calls MUST use `httpx.AsyncClient` with a 30s timeout
- NFR-4 The middleware MUST NOT log or store the content it scans (privacy)

## Out of scope for Track 3

- Building a new agent framework — the middleware wraps existing agents
- Handling non-text content (images, PDFs) — text extraction is the caller's responsibility
- Real-time streaming content scanning — scan complete documents, not streaming chunks
- User authentication on the hosted demo (open access for adoption)
