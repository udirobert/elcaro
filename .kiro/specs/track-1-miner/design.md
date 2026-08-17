# Track 1 — Miner: Design

## Current state

The miner is functionally complete. `miner/api.py` exposes all required endpoints. `core/` implements all six detectors with calibrated confidence scores, content-type weighting, combination multipliers, and Pydantic v2 schemas. The test suite in `miner/tests/test_detection.py` covers all technique classes, false-positive cases, scoring, and latency.

**What is missing is entirely operational**: the engine singleton fix, deployment, IPFS pinning, and on-chain registration.

## Known code issue to fix before deployment

### Engine singleton (critical — fix first)

`miner/api.py` currently instantiates `IpiDetectionEngine()` inside the request handler:

```python
# Current — wrong
@app.post("/scan")
async def scan(request: ScanRequest) -> ScanResponse:
    engine = IpiDetectionEngine()   # recompiles all 6 detectors' regex on every request
    return engine.scan(request)
```

All detector regex patterns compile on `IpiDetectionEngine.__init__`. At ~37 patterns across 6 detectors, this adds measurable overhead per request and will degrade under load.

Fix: move to module-level singleton.

```python
# Correct
_engine = IpiDetectionEngine()

@app.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest) -> ScanResponse:
    return _engine.scan(request)

@app.post("/v1/infer", response_model=ScanResponse)
async def infer(request: ScanRequest) -> ScanResponse:
    return _engine.scan(request)
```

## False-positive fixes

### "please [verb]" pattern tightening (Class C)

The `imperative_action` pattern in `task_reframe.py` currently matches `please send`, `please forward`, etc. at 0.6 confidence for email/document content. A normal email "Please send me the report" scores 0.6 × 0.8 = 0.48 — one more weak indicator pushes it to `suspicious`.

Proposed fix: require the imperative target to be agent-directed, not person-directed. Add a negative lookahead for common human-directed objects:

```python
# Instead of matching any "please [verb]", require no "me", "us", "him", "her", "them" after the verb
r"\b(?:please|you\s+(?:should|must|...))\s+(?:send|forward|...)\b(?!\s+(?:me|us|him|her|them|your)\b)"
```

Alternatively, reduce confidence for this pattern from 0.6 → 0.45, pushing it below the threshold where a single match causes harm.

### Turn spoofing narrowing (Class B)

`Assistant:` and `User:` patterns fire broadly. Narrow them by requiring an imperative verb within the next 20 words:

```python
r"\b(?:Assistant|AI|Bot|GPT|Claude|LLM)\s*:\s*.{0,100}?(?:send|forward|exec|run|call|install|delete|reset)"
```

## Deployment design

### Platform: VPS with reverse proxy

The miner runs as a systemd service (or docker container) behind a reverse proxy
(Caddy recommended — automatic HTTPS, zero config). The VPS provides full control,
no cold starts, and a stable HTTPS URL.

**Caddy config (recommended — automatic HTTPS via Let's Encrypt):**
```
elcaro.yourdomain.com {
    reverse_proxy localhost:8000
}
```

**Start command:**
```bash
uvicorn miner.api:app --host 127.0.0.1 --port 8000
```

**Systemd service (example):**
```ini
[Unit]
Description=Elcaro Miner API
After=network.target

[Service]
User=deploy
WorkingDirectory=/opt/elcaro
ExecStart=/opt/elcaro/.venv/bin/uvicorn miner.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
```

Alternative: `docker compose` with the same setup containerised.

### Directory structure for deployment

The miner needs `core/` to be importable. Install with `pip install -e .` on the VPS and run from the repo root:

```
uvicorn miner.api:app --host 127.0.0.1 --port 8000
```

### Environment variables for deployment

| Variable | Value |
|---|---|
| `PORT` | Set by platform |
| `ELCARO_MINER_URL` | Set to the deployed URL after first deploy |

### IPFS pinning (Pinata)

1. Go to [pinata.cloud](https://pinata.cloud) — free tier supports this
2. Upload `miner/config.yaml` with `api.base_url` filled in
3. Copy the resulting CID (e.g. `Qm...`)
4. Set `registration.ipfs_hash` in config

### Base Sepolia registration

1. Go to [integrate.telegraphprotocol.com](https://integrate.telegraphprotocol.com)
2. Connect wallet (Base Sepolia testnet)
3. Register miner with the IPFS hash
4. Copy the registry contract address → `registration.registry_contract` in config

## API design (no changes from current)

```
POST /scan
POST /v1/infer      ← Telegraph standard inference alias
GET  /health
GET  /              ← miner metadata / discovery
```

The `ScanRequest` / `ScanResponse` schemas in `core/schemas.py` are the contract. Do not change field names or types — this would break the Telegraph protocol routing and the eval script's expected response shape.

## Deep analysis (implemented, optional)

`deep_analysis=True` runs a real LLM second pass when the score lands in the gray zone (0.3–0.7) **and** a classifier is configured via `ELCARO_LLM_API_KEY` (+ optional `ELCARO_LLM_BASE_URL`, `ELCARO_LLM_MODEL`, `ELCARO_LLM_TIMEOUT`). Without configuration the miner stays rules-only and `deep_analysis_used` is `false` — never silently `true`.

How the design constraints landed:
- OpenAI-compatible endpoint; point `ELCARO_LLM_BASE_URL` at a local model (Ollama/vLLM) for latency — Telegraph benchmarks response time
- The LLM's score adjusts (does not replace) the rule-based score: 50/50 blend floored at half the rule score
- Rules keep veto power: the blend floor means the LLM cannot erase a rule finding, and gray-zone-only triggering means `dangerous` (≥0.7) results never get second-guessed
- Provider failures fall back to the rule score with `deep_analysis_used: false`
- See `core/llm_classifier.py` and `tests/test_deep_analysis.py`
