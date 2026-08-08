"""Elcaro Miner API — Telegraph Protocol Miner for IPI Detection.

This is the HTTP endpoint that the Telegraph Protocol routes requests to.
It accepts content, runs the IPI detection engine, and returns a risk score
with flagged techniques and indicators.

Run locally:
    uvicorn api:app --reload --port 8000

Endpoints:
    GET  /health       — health check
    POST /scan         — scan content for prompt injection
    GET  /             — API info / miner metadata
"""

from __future__ import annotations

import os
import sys

# Add parent directory to path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
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
    ],
}


# ── Endpoints ───────────────────────────────────────────────────────────────────


@app.get("/")
async def miner_info():
    """Return miner metadata for Telegraph protocol discovery."""
    return MINER_INFO


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "miner": "elcaro", "version": "0.1.0"}


@app.post("/scan", response_model=ScanResponse)
async def scan(request: ScanRequest) -> ScanResponse:
    """Scan content for indirect prompt injection.

    Accepts content and content type, returns risk score, flagged techniques,
    and detailed indicators. Optionally runs an LLM second pass for ambiguous
    (gray-zone) results.

    This is the primary endpoint the Telegraph protocol routes requests to.
    """
    engine = IpiDetectionEngine()
    result = engine.scan(request)
    return result


@app.post("/v1/infer", response_model=ScanResponse)
async def infer(request: ScanRequest) -> ScanResponse:
    """Telegraph-compatible inference endpoint.

    Some Telegraph miners expose /v1/infer as the standard inference endpoint.
    This is an alias for /scan.
    """
    return await scan(request)


# ── Run ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",  # noqa: S104 — intentional for containerised deployment
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
