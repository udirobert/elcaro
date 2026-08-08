# Elcaro — Architecture & Module Map

## Directory structure

```
elcaro/
├── core/                       # Shared IPI detection engine (imported by all other modules)
│   ├── __init__.py             # Public API: IpiDetectionEngine, ScanRequest, ScanResponse, etc.
│   ├── taxonomy.py             # IpiDetectionEngine orchestrator — runs detectors, scores, multipliers
│   ├── schemas.py              # Pydantic models: ScanRequest, ScanResponse, DetectionIndicator, enums
│   ├── llm_classifier.py       # Optional LLM second-pass classifier (stub — passthrough for now)
│   └── detectors/
│       ├── __init__.py         # BaseDetector ABC + _find_all / _make_indicator helpers
│       ├── authority.py        # Class A — system-voice / trusted-source spoofing
│       ├── delimiter.py        # Class B — fake closing tags, turn spoofing, comment smuggling
│       ├── task_reframe.py     # Class C — goal hijack, hidden steps, mandatory reframing
│       ├── obfuscation.py      # Class D — base64, zero-width, homoglyphs, leetspeak, unicode escape
│       ├── placement.py        # Class E — metadata injection, tail-edge, repetition salience
│       └── conditional.py      # Class F — workflow triggers, tool-conditional, named-tool triggers
├── miner/                      # Track 1 — Telegraph Protocol miner API
│   ├── api.py                  # FastAPI app: /scan, /v1/infer, /health, /
│   ├── config.yaml             # Telegraph miner registration config (IPFS-pinnable)
│   ├── requirements.txt        # fastapi, uvicorn, pydantic
│   └── tests/
│       ├── __init__.py
│       └── test_detection.py   # Pytest suite: all 6 classes, false-positive checks, scoring, latency
├── eval/                       # Track 2 — WASM evaluation script
│   ├── Cargo.toml              # elcaro-eval, cdylib+rlib, serde+serde_json deps
│   ├── src/lib.rs              # Eval logic: TestCase corpus (A001–N005), evaluate/get_test_cases exports
│   └── test_cases/             # (empty — corpus is hardcoded in lib.rs)
├── app/                        # Track 3 — Agent-facing content screener + web UI
│   ├── web/                    # Next.js application (TypeScript, Tailwind, App Router)
│   │   ├── src/
│   │   │   ├── app/            # App Router: pages, layouts, API routes
│   │   │   ├── components/     # React components (scan-form, result, indicators, etc.)
│   │   │   └── lib/            # Shared utilities (api client, constants, types)
│   │   ├── public/             # Static assets (OG image, favicon)
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── package.json
│   │   └── .env.local.example  # ELCARO_MINER_URL=http://localhost:8000
│   ├── middleware.py           # Python middleware: ElcaroMiddleware (library integration)
│   ├── demo.py                 # DemoAgent: end-to-end middleware demo with 6 sample payloads
│   └── requirements.txt        # httpx (Python middleware only)
├── docs/
│   ├── hackathon-tracker.md    # Timeline, judging criteria, strategy
│   └── technique-reference.md  # IPI taxonomy reference (A–F, scoring model, content-type weights)
└── pyproject.toml              # Package config: elcaro, requires python >=3.11
```

## Import conventions

`core/` is the single source of truth for detection logic. All other modules import from it:

```python
# Correct — import from core public API
from core import IpiDetectionEngine, ScanRequest, ScanResponse, ContentType

# Never import detector internals directly from outside core/
# Wrong: from core.detectors.authority import AuthorityDetector
```

`miner/api.py` uses `sys.path.insert` to find `core/` from the parent directory. This is intentional for the hackathon setup (no pip install required to run the miner). Do not replace this with package-relative imports without also updating the run instructions.

`app/middleware.py` and `app/demo.py` use the same `sys.path.insert` pattern for the same reason.

## Module responsibilities

### `core/schemas.py`
All shared Pydantic models. If a field appears in both request and response, it lives here. Do not define data models in `miner/api.py` or `app/middleware.py` — put them in schemas and import.

### `core/taxonomy.py` — `IpiDetectionEngine`
The only place where detectors are assembled and scoring logic lives. Responsibilities:
- Instantiate all 6 detectors
- Run them against content
- Apply content-type weighting (`CONTENT_TYPE_WEIGHTS`)
- Apply combination multipliers (`_apply_multipliers`)
- Map score to `RiskLevel` (`_risk_level`)
- Gate system prompts (skip scanning, return 0.0)
- Optionally invoke `LlmClassifier` for gray-zone cases

**Critical**: `IpiDetectionEngine` must be instantiated as a module-level singleton in `miner/api.py`, not per-request. All detectors compile their regex patterns on `__init__` — re-instantiating per request recompiles all patterns on every scan.

```python
# miner/api.py — correct pattern
_engine = IpiDetectionEngine()   # module level

@app.post("/scan")
async def scan(request: ScanRequest) -> ScanResponse:
    return _engine.scan(request)
```

### `core/detectors/__init__.py` — `BaseDetector`
Abstract base class. Every detector must:
- Set `technique_class: TechniqueClass` as a class attribute
- Implement `detect(content: str, content_type: ContentType) -> list[DetectionIndicator]`
- Use `self._make_indicator(...)` to construct indicators (truncates matched_text to 200 chars)
- Use `self._find_all(pattern, content)` for regex matching (returns `(matched_text, start_index)` tuples)

### `eval/src/lib.rs`
WASM evaluation script. Three exported functions consumed by the Telegraph validator:
- `evaluate(miner_responses_json: &str) -> String` — score a miner against the corpus
- `get_test_cases() -> String` — return the corpus so the validator knows what to send the miner
- `test_case_count() -> usize` — return corpus size

The corpus (`TEST_CASES`) is a `&[TestCase]` of `&'static str` — hardcoded at compile time. Test cases in `eval/test_cases/` are not used at runtime (the directory exists for documentation purposes).

## Key data flow

```
Browser (Next.js on Vercel)
      │
      ▼
/api/scan Route Handler              ← app/web/src/app/api/scan/route.ts
      │
      │  HTTP POST (proxied)
      ▼
miner/api.py (/scan)                 ← Track 1 miner (VPS)
      │
      ▼
IpiDetectionEngine.scan()            ← core/taxonomy.py
      │
      ├─ Run detectors A–F
      ├─ _compute_score(indicators)
      ├─ × content_type weight
      └─ × combination multipliers
      │
      ▼
ScanResponse → JSON back to browser


Python middleware path (library integration, no browser):

External content
      │
      ▼
ElcaroMiddleware.scan()              ← app/middleware.py
      │
      ├─ use_local_engine=True → IpiDetectionEngine.scan()   ← core/taxonomy.py
      └─ use_local_engine=False → HTTP POST /scan            ← miner/api.py
```

## What goes where — decision guide

| Adding... | Goes in... |
|---|---|
| A new detection pattern for an existing technique class | The relevant `core/detectors/X.py` |
| A new technique class (G, H, ...) | New file `core/detectors/X.py`, register in `core/taxonomy.py`, add to `TechniqueClass` enum in `core/schemas.py` |
| A new miner API endpoint | `miner/api.py` |
| A new request/response field | `core/schemas.py` |
| A new test case for the WASM eval corpus | `eval/src/lib.rs` in `TEST_CASES` |
| A new Python test | `tests/test_detection.py` |
| A new quarantine behaviour | `app/middleware.py` in `_apply_quarantine` |
| LLM second-pass implementation | `core/llm_classifier.py` |
| A new frontend page | `app/web/src/app/<route>/page.tsx` |
| A new frontend component | `app/web/src/components/<name>.tsx` |
| A new frontend API route | `app/web/src/app/api/<route>/route.ts` |
| Frontend environment config | `app/web/.env.local` (never committed) |
