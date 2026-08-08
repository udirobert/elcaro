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

### Recommended platform: Railway

Railway is the simplest path for a Python FastAPI app with no cold starts, persistent process, and a stable HTTPS URL on the free tier.

```
# Procfile (create in miner/)
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

The app already reads `PORT` from the environment. No other changes needed.

Alternative: Fly.io (more control), Render (free tier has cold starts — avoid for a service being benchmarked on latency).

### Directory structure for deployment

The miner needs `core/` to be importable. The `sys.path.insert` in `api.py` handles this when running from the `miner/` directory. For Railway/Fly deployment, the start command must be run from the repo root:

```
# From repo root
uvicorn miner.api:app --host 0.0.0.0 --port $PORT
```

This requires removing the `sys.path.insert` hack and ensuring `core` is importable as a package (it already is via `pyproject.toml`). Install with `pip install -e .` in the deployment environment.

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

## Deep analysis stub behaviour

`deep_analysis=True` is accepted but currently returns the rule-based score unchanged. This is acceptable for the hackathon. The response correctly sets `deep_analysis_used: false`. Do not silently set it to `true`.

If LLM second-pass is implemented before the deadline:
- Use a local model (Ollama) for latency reasons — Telegraph benchmarks response time
- The LLM's score adjusts (does not replace) the rule-based score
- If LLM disagrees with a `dangerous` rule-based result, keep `dangerous`
- See `core/llm_classifier.py` for the designed interface
