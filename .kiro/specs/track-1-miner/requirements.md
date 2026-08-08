# Track 1 — Miner: Requirements

## Overview

The Elcaro miner is a Telegraph Protocol miner that exposes an IPI detection API. It must be deployed to a public URL, registered on Base Sepolia, and capable of serving live requests from the Telegraph network before the Sep 7 evaluation deadline.

## Functional requirements

### FR-1 Detection API
The miner MUST expose an HTTP endpoint that accepts a content payload and returns a structured IPI risk assessment.

- FR-1.1 POST `/scan` accepts `ScanRequest` (content, content_type, deep_analysis, context) and returns `ScanResponse` (risk_score, risk_level, flagged_techniques, indicators, latency_ms)
- FR-1.2 POST `/v1/infer` is an alias for `/scan` for Telegraph protocol compatibility
- FR-1.3 GET `/health` returns `{"status": "healthy"}` for uptime monitoring
- FR-1.4 GET `/` returns miner metadata (id, name, intents, version) for protocol discovery
- FR-1.5 All six technique classes (A–F) MUST be evaluated on every scan request
- FR-1.6 `content_type: system_prompt` MUST return `risk_score: 0.0` without scanning

### FR-2 Scoring
- FR-2.1 Risk scores MUST be in the range [0.0, 1.0]
- FR-2.2 Risk levels MUST map to: safe (<0.2), low (0.2–0.5), suspicious (0.5–0.7), dangerous (≥0.7)
- FR-2.3 Content-type weights MUST be applied (email/search_result/webpage=1.0, document=0.8, code=0.7, chat_message=0.3, system_prompt=0.0)
- FR-2.4 Combination multipliers MUST be applied: D+any=×1.3, F+C=×1.2, A+B=×1.15

### FR-3 Response quality
- FR-3.1 Every indicator MUST include: technique_class, technique_name, confidence, matched_text, location, explanation
- FR-3.2 `latency_ms` MUST reflect actual wall-clock processing time
- FR-3.3 `deep_analysis_used` MUST accurately reflect whether the LLM second pass ran

### FR-4 Performance
- FR-4.1 Median response time MUST be under 100ms for content up to 10,000 characters
- FR-4.2 The detection engine MUST be a module-level singleton (not instantiated per-request)
- FR-4.3 The API MUST handle concurrent requests without shared mutable state

### FR-5 Telegraph integration
- FR-5.1 The miner MUST be reachable at a stable public HTTPS URL
- FR-5.2 `miner/config.yaml` MUST have `api.base_url` set to the deployed URL before registration
- FR-5.3 The config MUST be pinned to IPFS (via Pinata) and the resulting hash stored in `registration.ipfs_hash`
- FR-5.4 The miner MUST be registered on Base Sepolia via integrate.telegraphprotocol.com
- FR-5.5 The miner MUST correctly handle x402 payment headers if/when the protocol requires them

### FR-6 False-positive control
- FR-6.1 Clean content (weather forecasts, meeting reminders, plain code) MUST score below 0.3
- FR-6.2 The `"please [verb]"` pattern in email MUST NOT cause a score ≥ 0.5 on its own
- FR-6.3 Turn-spoofing patterns (Assistant:, User:) MUST NOT fire on search results that legitimately quote conversation (FAQ pages, tutorials) without an accompanying imperative

## Non-functional requirements

- NFR-1 The miner MUST be deployed with auto-restart / process supervision (not bare `python api.py`)
- NFR-2 The miner MUST expose a `/health` endpoint that the deployment platform uses for health checks
- NFR-3 Environment variables (`PORT`, `ELCARO_MINER_URL`) MUST be used for configuration — no hardcoded values
- NFR-4 The deployed URL MUST use HTTPS
- NFR-5 The service MUST remain available continuously from registration through Sep 7 evaluation

## Out of scope for Track 1

- LLM second-pass implementation (stub is acceptable; `deep_analysis=True` may return rule-based score)
- Authentication / API key gating (Telegraph handles payment via x402)
- Rate limiting (handled at the platform/proxy level)
