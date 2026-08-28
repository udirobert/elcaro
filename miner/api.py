"""Elcaro Miner API — Telegraph Protocol Miner for IPI Detection.

This is the HTTP endpoint that the Telegraph Protocol routes requests to.
It accepts content, runs the IPI detection engine, and returns a risk score
with flagged techniques and indicators.

Run locally:
    uvicorn miner.api:app --reload --port 8000
    # or, from the repo root:
    python miner/api.py   # PORT env var, default 8848

Endpoints:
    GET  /health       — health check
    POST /scan         — scan content for prompt injection (the registered endpoint)
    POST /v1/infer     — alias for /scan
    GET  /             — API info / miner metadata
    GET  /metrics      — observability: request counts, latency, error rate
    GET  /telegraph.yaml — raw registration config, served byte-for-byte
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from core import IpiDetectionEngine, ScanRequest, ScanResponse

# ── App ─────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Elcaro — IPI Detection Miner",
    description=(
        "Telegraph Protocol miner that detects indirect prompt injection (IPI) "
        "in content retrieved by AI agents. Scans for authority framing, "
        "delimiter confusion, task reframing, obfuscation, placement tricks, "
        "and conditional triggers."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Observability ───────────────────────────────────────────────────────────────


@dataclass
class Metrics:
    """In-memory metrics for the miner. Reset on restart (stateless by design)."""

    total_requests: int = 0
    total_errors: int = 0
    total_scans: int = 0
    risk_level_counts: dict[str, int] = field(
        default_factory=lambda: {"safe": 0, "low": 0, "suspicious": 0, "dangerous": 0}
    )
    content_type_counts: dict[str, int] = field(default_factory=dict)
    # Rolling window of last 1000 latencies (ms) for percentile calculation
    latencies_ms: deque = field(default_factory=lambda: deque(maxlen=1000))
    started_at: float = field(default_factory=time.time)

    def record_scan(self, response: ScanResponse) -> None:
        """Record metrics from a completed scan."""
        self.total_scans += 1
        self.risk_level_counts[response.risk_level.value] = (
            self.risk_level_counts.get(response.risk_level.value, 0) + 1
        )
        self.content_type_counts[response.content_type.value] = (
            self.content_type_counts.get(response.content_type.value, 0) + 1
        )
        if response.latency_ms is not None:
            self.latencies_ms.append(response.latency_ms)

    def record_error(self) -> None:
        self.total_errors += 1

    def to_dict(self) -> dict:
        """Export metrics as a JSON-serialisable dict."""
        latencies = sorted(self.latencies_ms)
        n = len(latencies)

        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "total_requests": self.total_requests,
            "total_scans": self.total_scans,
            "total_errors": self.total_errors,
            "error_rate": (
                round(self.total_errors / self.total_requests, 4)
                if self.total_requests > 0
                else 0.0
            ),
            "latency_ms": {
                "p50": latencies[n // 2] if n > 0 else 0,
                "p90": latencies[int(n * 0.9)] if n > 0 else 0,
                "p99": latencies[int(n * 0.99)] if n > 0 else 0,
                "avg": round(sum(latencies) / n, 1) if n > 0 else 0,
                "samples": n,
            },
            "risk_levels": dict(self.risk_level_counts),
            "content_types": dict(self.content_type_counts),
        }


_metrics = Metrics()


# ── Request counting middleware ─────────────────────────────────────────────────


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:
    """Count all requests and catch unhandled errors."""
    _metrics.total_requests += 1
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            _metrics.record_error()
        return response
    except Exception:
        _metrics.record_error()
        raise


# ── Miner metadata ──────────────────────────────────────────────────────────────

MINER_INFO = {
    "miner_id": "elcaro",
    "name": "Elcaro — IPI Detection",
    "description": (
        "Detects indirect prompt injection in content retrieved by AI agents. "
        "Returns a risk score, flagged techniques, and detailed indicators."
    ),
    "intents": ["INJECTION_DETECTION", "CONTENT_SAFETY_SCAN"],
    "version": "0.1.0",
    "detection_model": "rule-based heuristics (A–F taxonomy) + optional LLM second pass",
    "supported_content_types": [
        "email",
        "search_result",
        "code",
        "document",
        "webpage",
        "chat_message",
        "system_prompt",
    ],
}


# ── Detection engine (module-level singleton — regex compiled once) ──────────────

_engine = IpiDetectionEngine()

# ── Endpoints ───────────────────────────────────────────────────────────────────


@app.get("/")
async def miner_info():
    """Return miner metadata for Telegraph protocol discovery."""
    return MINER_INFO


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "miner": "elcaro", "version": "0.1.0"}


# Resolved once at import time: miner/api.py -> miner/ -> miner/telegraph.yaml
_TELEGRAPH_YAML_PATH = Path(__file__).resolve().parent / "telegraph.yaml"


@app.get("/telegraph.yaml")
async def telegraph_yaml() -> Response:
    """Serve the Telegraph registration config as raw, unmodified bytes.

    This exists because the integrate.telegraphprotocol.com console re-serialises
    an uploaded YAML before pinning it to IPFS (comments stripped, some fields
    reflowed), so the SHA-256 of the pinned file no longer matches the SHA-256 of
    the file that was uploaded. Registering against the console-pinned hash then
    fails the node's fetch-time hash verification. Hosting the exact repo file
    here and registering against ITS hash avoids that transformation entirely.

    Plain HTTPS is an explicitly supported hosting option (see
    docs.telegraphprotocol.com -> miners/miner-registration.md, Step 2).
    """
    if not _TELEGRAPH_YAML_PATH.is_file():
        raise HTTPException(status_code=500, detail="telegraph.yaml not found on this deployment")
    return Response(
        content=_TELEGRAPH_YAML_PATH.read_bytes(),
        media_type="application/x-yaml",
    )


@app.get("/metrics")
async def metrics():
    """Observability endpoint — request counts, latency percentiles, error rate.

    This endpoint is intended for monitoring dashboards and does not require
    authentication (stats only, no PII).
    """
    return _metrics.to_dict()


@app.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest) -> ScanResponse:
    """Scan content for indirect prompt injection.

    Accepts content and content type, returns risk score, flagged techniques,
    and detailed indicators. Optionally runs an LLM second pass for ambiguous
    (gray-zone) results.

    This is the primary endpoint the Telegraph protocol routes requests to.
    """
    result = _engine.scan(request)
    _metrics.record_scan(result)
    return result


@app.post("/v1/infer", response_model=ScanResponse)
async def infer(request: ScanRequest) -> ScanResponse:
    """Telegraph-compatible inference endpoint.

    Some Telegraph miners expose /v1/infer as the standard inference endpoint.
    This is an alias for /scan.
    """
    result = _engine.scan(request)
    _metrics.record_scan(result)
    return result


# ── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "miner.api:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8848)),
        reload=True,
    )
