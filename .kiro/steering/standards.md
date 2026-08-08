# Elcaro — Code Standards

## Python

### Version & environment
- Python ≥ 3.11 (see `pyproject.toml`)
- Virtual environment at `.venv/` — activate with `source .venv/bin/activate`
- Install all deps: `pip install -e ".[dev]"` from the workspace root
- Run tests: `python -m pytest miner/tests/ -v` from the workspace root

### Style
- `from __future__ import annotations` at the top of every Python file
- Type hints on all function signatures — no bare `Any` unless genuinely unavoidable
- Docstrings on all public classes and methods; single-line for trivial helpers
- Line length: 100 characters
- No unused imports — remove them rather than commenting out

### Pydantic v2
All models use Pydantic v2 patterns:
```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="...")
    optional: str | None = Field(default=None)

# Serialise to dict
model.model_dump()          # not .dict()

# Construct from dict
MyModel.model_validate(d)   # not MyModel(**d) for untrusted data
```
Do not use deprecated v1 methods (`.dict()`, `.parse_obj()`, `@validator`). Use `.model_dump()`, `.model_validate()`, `@field_validator`.

### FastAPI patterns
```python
# Module-level singleton — never instantiate per-request
_engine = IpiDetectionEngine()

# Async handlers; return the Pydantic model directly (FastAPI serialises it)
@app.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest) -> ScanResponse:
    return _engine.scan(request)

# Use response_model on all POST/PUT/PATCH handlers
# Use status_code=200 (default) for successful scans — not 201
```

CORS is configured in `miner/api.py` as `allow_origins=["*"]` for the hackathon. Tighten before any production deployment.

### Regex patterns
- Define patterns as module-level constants (not inside `detect()`) so they are compiled once
- Use named tuples `(pattern, confidence, name)` for lists of patterns
- Always use `re.IGNORECASE` unless case sensitivity is intentional and documented
- Test every new regex against at least one known match and one known non-match before committing

### Error handling
- FastAPI endpoints: let FastAPI's default exception handlers surface 422 validation errors from Pydantic
- Detection engine: detectors must never raise — catch all exceptions internally and return an empty indicator list, logging the error
- `ObfuscationDetector._try_decode_base64` is the canonical example: `try/except Exception: return None`

### Testing
- Test runner: `pytest` with `asyncio_mode = "auto"` (see `pyproject.toml`)
- Test file: `miner/tests/test_detection.py` — all detection tests go here
- Every new detector pattern needs: one positive test + one false-positive (negative) test
- Latency test: the `test_latency_is_reasonable` test enforces < 100ms for a single scan; do not break this
- Run before every commit: `python -m pytest miner/tests/ -v`

## Rust / WASM (eval/)

### Toolchain
- Rust stable (latest)
- Target: `wasm32-unknown-unknown`
- Build: `cargo build --target wasm32-unknown-unknown --release` from `eval/`
- Test (native): `cargo test` from `eval/`

### WASM ABI
The Telegraph validator calls exported functions via WASM. The ABI for string passing must be verified against the Telegraph runtime's calling convention before submission. The current `&str` parameter on `evaluate` may require a linear-memory pointer+length approach instead. Check Telegraph's WASM eval documentation or example scripts before assuming the current signature works.

Exported functions (marked `#[no_mangle] pub extern "C" fn`):
- `evaluate(miner_responses_json: &str) -> String`
- `get_test_cases() -> String`
- `test_case_count() -> usize`

### Serialisation
- All structs that cross the WASM boundary use `serde_json`
- `TestCase` uses `&'static str` (compile-time corpus); `TestCaseOwned` uses `String` (for test deserialization)
- Do not add runtime file I/O — the corpus must be compiled into the WASM binary

### Test corpus conventions (`eval/src/lib.rs`)
- Case IDs: `A001`, `A002`, ..., `N001`, `N002`, ... (letter = technique class, N = negative/clean)
- Every positive case (`is_injection: true`) must list at least one `expected_techniques` entry
- Every negative case (`is_injection: false`) must have `expected_techniques: &[]`
- Aim for ≥ 3 positive cases per represented technique class
- Aim for ≥ 5 clean/negative cases total (false-positive resistance is weighted in scoring)
- Descriptions must be specific: "System-voice spoofing in email body", not "injection test"

## Git
- Branch per feature/fix; no direct commits to `main`
- Commit messages: `type(scope): description` — e.g. `fix(miner): move engine to module-level singleton`
- Do not commit secrets, `.env` files, or deployed URLs — use environment variables
- `miner/config.yaml` fields `api.base_url`, `registration.ipfs_hash`, `registration.registry_contract` must be set via environment or a local override, never committed with real values

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `ELCARO_MINER_URL` | `app/middleware.py` | URL of the deployed miner API |
| `PORT` | `miner/api.py` | HTTP port (default: 8000) |

Do not hardcode URLs or ports in source files. Use `os.environ.get("VAR", default)`.
