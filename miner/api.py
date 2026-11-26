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
    GET  /pubkey       — verdict-signing public key (404 when running unsigned)
    POST /verify       — verify a signed verdict against this miner's key
    GET  /redteam/seeds — corpus cases the self-red-team run mutates
    GET  /redteam/run  — SSE stream: the searcher attacks this engine live
"""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from core import IpiDetectionEngine, ScanRequest, ScanResponse
from core.canary import TOKEN_RE
from core.jev_reasoner import JevReasoner
from core.jev_vl_reasoner import JevVlReasoner
from core.laya_reasoner import LayaReasoner
from core.rate_limit import (
    direct_scan_rate_limiter_from_env,
    keyed_scan_rate_limiter_from_env,
    scan_rate_limiters_from_env,
)
from core.sandbox import (
    SandboxConfig,
    run_sandbox,
)
from core.serv_reasoner import ServReasoner
from core.signing import (
    VerdictSigner,
    canonical_verdict_payload,
    sha256_hex,
    verify_verdict,
)
from core.usage import get_key
from core.vulnerability import analyze as analyze_vulnerability

log = logging.getLogger(__name__)

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
    serv_calls: int = 0  # second-pass calls that actually contributed to a verdict
    rate_limited_scans: int = 0
    rate_limited_premium_scans: int = 0
    rate_limited_keyed_scans: int = 0
    serv_cost_total_usdc: float = (
        0.0  # cumulative SERV cost in USDC (approximate, from char counts)
    )
    risk_level_counts: dict[str, int] = field(
        default_factory=lambda: {"safe": 0, "low": 0, "suspicious": 0, "dangerous": 0}
    )
    content_type_counts: dict[str, int] = field(default_factory=dict)
    # Canary flywheel counters — the observable part of the trap-street
    # experiment: how many notices get stamped, how often stamped text is
    # seen again inside scanned content, and public resolver traffic.
    canary_mints: int = 0
    canary_hits_recognized: int = 0
    canary_hits_unrecognized: int = 0
    canary_resolves: int = 0
    canary_resolved_known: int = 0
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
        # Track cumulative SERV spend so operators can monitor costs.
        if response.serv_cost and response.serv_cost.get("total_usdc"):
            self.serv_cost_total_usdc += float(response.serv_cost["total_usdc"])
        # Canary counters: a stamped notice is a mint; tokens found inside
        # scanned content split into recognized relays vs everything else.
        if response.quarantined and response.safe_content and "Ref: elc-" in response.safe_content:
            self.canary_mints += 1
        for hit in response.canary_hits or []:
            if hit.get("recognized"):
                self.canary_hits_recognized += 1
            else:
                self.canary_hits_unrecognized += 1

    def record_canary_resolve(self, recognized: bool) -> None:
        self.canary_resolves += 1
        if recognized:
            self.canary_resolved_known += 1

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
            "serv_calls": self.serv_calls,
            "serv_cost_total_usdc": round(self.serv_cost_total_usdc, 6),
            "rate_limited_scans": self.rate_limited_scans,
            "rate_limited_premium_scans": self.rate_limited_premium_scans,
            "rate_limited_keyed_scans": self.rate_limited_keyed_scans,
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
            "canary": {
                "mints": self.canary_mints,
                "hits_recognized": self.canary_hits_recognized,
                "hits_unrecognized": self.canary_hits_unrecognized,
                "resolves": self.canary_resolves,
                "resolved_known": self.canary_resolved_known,
            },
        }


_metrics = Metrics()


# ── Free-scan cost protection ─────────────────────────────────────────────────
#
# The miner itself is publicly reachable, so protecting only the Netlify proxy
# leaves a direct-API bypass. Two controls live here at the miner edge:
#
# 1. Optional durable fixed-window scan quotas keyed by HMAC(client IP). They
#    are disabled unless the corresponding env limit is set, because local
#    development and the offline test suite intentionally scan repeatedly.
# 2. Expensive second-opinion rails get a much smaller anonymous quota than
#    the ordinary rule-only path. Strict ordinary quotas apply to trusted
#    web-proxy traffic keyed by the asserted end-user IP. Direct miner ingress
#    (Telegraph devnode and direct API callers are not cryptographically
#    distinguishable today) gets a separate higher resource-protection quota.
#    A deployment-internal token lets the paid x402 lane bypass free quotas.
# 3. A minted elk_ key (x-elcaro-key) draws from its own bucket instead of the
#    anonymous ones, so minting keys buys something on the endpoint a stranger
#    already used. Keys resolve through the same Neon store as the gateway.

try:
    _scan_rate_limiter, _premium_scan_rate_limiter = scan_rate_limiters_from_env()
    _direct_scan_rate_limiter = direct_scan_rate_limiter_from_env()
    _keyed_scan_rate_limiter = keyed_scan_rate_limiter_from_env()
except Exception as exc:  # boot-time config failure must be loud, not silent
    raise RuntimeError(f"scan rate limiting is enabled but could not initialize: {exc}") from exc


def _install_key_store() -> bool:
    """Resolve minted ``elk_`` keys at the miner edge.

    Only the key store is installed — the usage sink stays with the gateway, so
    scan traffic is metered once, where it is charged. Unconfigured (no metering
    DSN, as in the offline suite) means keyed scans are simply rejected with 401
    rather than silently falling back to the anonymous bucket.
    """
    try:
        from core.usage import set_key_store
        from metering import from_env

        store = from_env()
        if store is None:
            return False
        set_key_store(store)
        return True
    except Exception:  # noqa: BLE001 — an unreachable store must not stop scans
        log.warning("key store unavailable — keyed scans will be rejected", exc_info=True)
        return False


_KEY_STORE_AVAILABLE = _install_key_store()

_PREMIUM_SCAN_FIELDS = (
    "deep_analysis",
    "serv_enabled",
    "jev_enabled",
    "laya_enabled",
    "jev_vl_enabled",
)


def _valid_internal_token(http_request: Request) -> bool:
    expected = os.environ.get("ELCARO_INTERNAL_PROXY_TOKEN", "")
    if not expected:
        return False
    presented = http_request.headers.get("x-elcaro-internal-token", "")
    return bool(presented) and hmac.compare_digest(presented, expected)


def _premium_scan_authorized(http_request: Request) -> bool:
    # Explicit local-development escape hatch. Production should instead use
    # ELCARO_INTERNAL_PROXY_TOKEN + x-elcaro-premium: 1 from the paid lane.
    # This controls quota bypass, not whether the rails exist at all.
    if os.environ.get("ELCARO_ALLOW_ANONYMOUS_PREMIUM") == "1":
        return True
    return _valid_internal_token(http_request) and (
        http_request.headers.get("x-elcaro-premium") == "1"
    )


def _client_ip(http_request: Request) -> str:
    # The web proxy can assert the browser/client IP only when it proves it is
    # our proxy. Without that proof the header is just caller-controlled input.
    if _valid_internal_token(http_request):
        asserted = http_request.headers.get("x-elcaro-client-ip", "").strip()
        try:
            if asserted:
                return str(ipaddress.ip_address(asserted))
        except ValueError:
            pass

    # Traefik appends the immediate client IP to X-Forwarded-For. Use the
    # right-most value rather than the left-most, which is trivially spoofable
    # when a caller supplies its own XFF header.
    xff = http_request.headers.get("x-forwarded-for", "")
    candidates = [part.strip() for part in xff.split(",") if part.strip()]
    for candidate in reversed(candidates):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    if http_request.client and http_request.client.host:
        return http_request.client.host
    return "unknown"


def _rate_limit_response(decision, *, premium: bool = False, keyed: bool = False) -> JSONResponse:
    retry = max(1, decision.retry_after_seconds)
    if keyed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "keyed_scan_rate_limited",
                "message": (
                    "This key's scan quota is exhausted for the current window — "
                    "Retry-After says when it resets."
                ),
                "retry_after_seconds": retry,
            },
            headers={
                "Retry-After": str(retry),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": str(decision.remaining),
                "Cache-Control": "no-store",
            },
        )
    return JSONResponse(
        status_code=429,
        content={
            "error": "free_premium_scan_rate_limited" if premium else "free_scan_rate_limited",
            "message": (
                "Free second-opinion scan limit reached. Use the paid x402 scan lane "
                "for continued SERV/comparison scans without an account."
                if premium
                else "Free scan limit reached. Use the paid x402 scan lane for "
                "continued scanning without an account."
            ),
            "retry_after_seconds": retry,
            "upgrade": {
                "type": "x402",
                "endpoint": "/api/x402/scan",
                "price_usdc": os.environ.get("ELCARO_X402_SCAN_PRICE_USDC", "0.01"),
                "description": "Pay per scan; no signup or API key required.",
            },
        },
        headers={
            "Retry-After": str(retry),
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
            "Cache-Control": "no-store",
        },
    )


def _presented_key(http_request: Request) -> str | None:
    """The caller's raw ``elk_`` key, if they sent one."""
    raw = (http_request.headers.get("x-elcaro-key") or "").strip()
    return raw or None


def _key_rejection_response(reason: str) -> JSONResponse:
    """A presented key we cannot honour. Never silently downgrade to
    anonymous: the caller would think their key was being used (and metered)."""
    if reason == "unconfigured":
        status, error, message = (
            503,
            "key_service_unavailable",
            "This miner cannot resolve Elcaro keys (no key store configured). "
            "Scan without a key, or call the gateway.",
        )
    else:
        status, error, message = (
            401,
            "unknown_key",
            "That x-elcaro-key is not recognised — it may be revoked, or minted "
            "on another deployment. Mint one at https://elcaro.trustfall.xyz/keys.",
        )
    return JSONResponse(
        status_code=status,
        content={"error": error, "message": message},
        headers={"Cache-Control": "no-store"},
    )


def _apply_quota_headers(response: Response, decision) -> None:
    """Expose the quota that applied to this call — the key's own window, or
    the shared anonymous one. A caller can then see the allowance shrinking
    before it runs out, and an idle limiter is visible as missing headers
    rather than as a wall that never arrives."""
    if decision is None:
        return
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)


def _max_content_chars() -> int:
    try:
        return int(os.environ.get("ELCARO_SCAN_MAX_CONTENT_CHARS", "100000"))
    except ValueError:
        return 100000


def _content_too_large_response(limit: int) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={
            "error": "content_too_large",
            "message": f"Scan content is limited to {limit:,} characters on this deployment.",
            "limit_chars": limit,
        },
        headers={"Cache-Control": "no-store"},
    )


def _guard_scan_request(
    http_request: Request, request: ScanRequest
) -> tuple[ScanRequest, JSONResponse | None, object | None]:
    """Apply free-tier cost controls and return a safe request.

    Returns (possibly-sanitized request, response, quota). A non-None response
    means the scan must not run. ``quota`` is the rate-limit decision that
    applied — the key's own window when an ``elk_`` key was honoured, else the
    shared anonymous one — and the endpoint echoes it back as headers so the
    remaining allowance is visible before the wall, not only after it.
    """
    max_chars = _max_content_chars()
    if max_chars > 0 and len(request.content) > max_chars:
        return request, _content_too_large_response(max_chars), None

    raw_key = _presented_key(http_request)
    key_cfg = None
    if raw_key is not None:
        if not _KEY_STORE_AVAILABLE:
            return request, _key_rejection_response("unconfigured"), None
        key_cfg = get_key(raw_key)
        if key_cfg is None:
            return request, _key_rejection_response("unknown"), None

    premium_authorized = _premium_scan_authorized(http_request)
    if premium_authorized:
        return request, None, None

    premium_requested = any(getattr(request, name) for name in _PREMIUM_SCAN_FIELDS)
    client_ip = _client_ip(http_request)

    # Premium rails (SERV and comparison models) consume upstream inference
    # budget, so anonymous use gets a smaller quota than the rule-only path.
    if premium_requested and _premium_scan_rate_limiter is not None:
        decision = _premium_scan_rate_limiter.check(client_ip)
        if not decision.allowed:
            _metrics.rate_limited_premium_scans += 1
            return request, _rate_limit_response(decision, premium=True), None

    # A keyed caller spends its own window rather than the shared anonymous
    # one. When no keyed quota is configured (local dev, offline suite) the key
    # is still honoured for attribution but the request falls through to the
    # anonymous bucket — never to unlimited access.
    if key_cfg is not None and _keyed_scan_rate_limiter is not None:
        decision = _keyed_scan_rate_limiter.check(f"key:{key_cfg.key_id}")
        if not decision.allowed:
            _metrics.rate_limited_keyed_scans += 1
            return request, _rate_limit_response(decision, keyed=True), None
        return request, None, decision

    # Every anonymous scan consumes an ordinary quota as well. Paid premium
    # traffic returned above and bypasses free buckets. The strict conversion
    # quota is only meaningful when our web proxy can assert the end-user IP;
    # direct ingress uses a higher shared-resource quota so legitimate
    # Telegraph devnode volume is not throttled as if it were one browser user.
    ordinary_limiter = (
        _scan_rate_limiter if _valid_internal_token(http_request) else _direct_scan_rate_limiter
    )
    if ordinary_limiter is not None:
        decision = ordinary_limiter.check(client_ip)
        if not decision.allowed:
            _metrics.rate_limited_scans += 1
            return request, _rate_limit_response(decision), None
        return request, None, decision
    return request, None, None


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

# ── SERV Reasoning second pass (optional progressive enhancement) ──────────────
#
# Built from SERV_ENABLED + SERV_API_KEY at import time. None means SERV is
# disabled — the engine stays purely rule-based and the free path is
# unchanged (no network call, no key required). When SERV is configured the
# engine uses it as the premium second-pass judge; the ELCARO_LLM_* fallback
# still works for users who haven't enabled SERV.
_serv_reasoner = ServReasoner.from_env()
if _serv_reasoner is not None:
    MINER_INFO["serv_reasoning"] = {
        "provider": "openserv",
        "endpoint": _serv_reasoner.base_url + "/chat/completions",
        "model": _serv_reasoner.model,
        "toggle": "?serv=1 or body.serv_enabled",
    }

# ── Verdict signing (optional — unsigned when ELCARO_SIGNING_KEY is unset) ──────
#
# Verdicts are signed because the quarantine notice is in-band text — and
# in-band text is spoofable (docs/ux-audit.md, BG4). A malformed key raises
# at boot: security configuration fails loud, never silently.
_signer = VerdictSigner.from_env()

if _signer is not None:
    MINER_INFO["signing"] = {
        "algorithm": "ed25519",
        "key_id": _signer.key_id,
        "pubkey_url": "/pubkey",
    }

if _engine.canary_registry is not None:
    from core.canary import PostgresCanaryRegistry

    _durable = isinstance(_engine.canary_registry, PostgresCanaryRegistry)
    MINER_INFO["canary"] = {
        "token_format": "elc-<unix-hex>-<6 rand hex>, stamped as 'Ref:' in quarantine notices",
        "resolve_url": "/canary/{token}",
        "note": (
            "durable — tokens resolve across restarts and deployments"
            if _durable
            else "in-memory per-process — tokens minted before a restart resolve as unrecognized"
        ),
    }


def _sign_response(content: str, result: ScanResponse) -> ScanResponse:
    """Stamp the scan time; sign the canonical payload when a key is configured.

    Signs the ROUNDED score that appears in the response, and the content's
    SHA-256 — never the content itself (the miner stays stateless).
    """
    result.scanned_at = int(time.time())
    if _signer is not None:
        payload = canonical_verdict_payload(
            content_sha256=sha256_hex(content),
            risk_score=result.risk_score,
            risk_level=result.risk_level.value,
            quarantined=result.quarantined,
            flagged_techniques=[t.value for t in result.flagged_techniques],
            scanned_at=result.scanned_at,
        )
        result.signature = _signer.sign(payload)
        result.key_id = _signer.key_id
    return result


class VerifyRequest(BaseModel):
    """A verdict to verify against this miner's signing key.

    Carries the content (hashed client-side here, never stored) plus the
    response fields that went into the canonical payload.
    """

    content: str = Field(..., description="The content that was scanned")
    risk_score: float
    risk_level: str
    quarantined: bool
    flagged_techniques: list[str] = Field(default_factory=list)
    scanned_at: int
    signature: str = Field(..., description="The verdict's hex Ed25519 signature")


# ── Endpoints ───────────────────────────────────────────────────────────────────


@app.get("/")
async def miner_info():
    """Return miner metadata for Telegraph protocol discovery."""
    return MINER_INFO


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "miner": "elcaro", "version": "0.1.0"}


@app.get("/config")
async def config():
    """Return miner configuration status for client-side feature flags."""
    serv = ServReasoner.from_env()
    jev = JevReasoner.from_env()
    laya = LayaReasoner.from_env()
    jev_vl = JevVlReasoner.from_env()
    return {
        "serv_available": serv is not None,
        "jev_available": jev is not None,
        "laya_available": laya is not None,
        "jev_vl_available": jev_vl is not None,
        "version": "0.1.0",
    }


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
async def scan(
    request: ScanRequest, http_request: Request, response: Response, serv: bool | None = None
) -> ScanResponse | JSONResponse:
    """Scan content for indirect prompt injection.

    Accepts content and content type, returns risk score, flagged techniques,
    and detailed indicators. Optionally runs an LLM second pass for ambiguous
    (gray-zone) results.

    Query params:
      serv — when set, overrides ``request.serv_enabled``. ``?serv=1``
             forces the SERV path; ``?serv=0`` forces it off for this call.
             Has no effect when the miner was not configured with
             SERV_API_KEY + SERV_ENABLED=1 at boot.

    This is the primary endpoint the Telegraph protocol routes requests to.
    """
    if serv is not None:
        request = request.model_copy(update={"serv_enabled": serv})
    request, limited_response, quota = _guard_scan_request(http_request, request)
    if limited_response is not None:
        return limited_response
    result = _engine.scan(request)
    _metrics.record_scan(result)
    if result.serv_used:
        _metrics.serv_calls += 1
    _apply_quota_headers(response, quota)
    return _sign_response(request.content, result)


@app.post("/v1/infer", response_model=ScanResponse)
async def infer(
    request: ScanRequest, http_request: Request, response: Response, serv: bool | None = None
) -> ScanResponse | JSONResponse:
    """Telegraph-compatible inference endpoint.

    Some Telegraph miners expose /v1/infer as the standard inference endpoint.
    This is an alias for /scan.
    """
    if serv is not None:
        request = request.model_copy(update={"serv_enabled": serv})
    request, limited_response, quota = _guard_scan_request(http_request, request)
    if limited_response is not None:
        return limited_response
    result = _engine.scan(request)
    _metrics.record_scan(result)
    if result.serv_used:
        _metrics.serv_calls += 1
    _apply_quota_headers(response, quota)
    return _sign_response(request.content, result)


@app.get("/pubkey")
async def pubkey():
    """The public half of this miner's verdict-signing key.

    Fetch once, cache, and verify verdicts offline — the trust anchor for
    signed verdicts. 404 when the miner runs unsigned (no ELCARO_SIGNING_KEY).
    """
    if _signer is None:
        raise HTTPException(
            status_code=404,
            detail="This miner does not sign verdicts (ELCARO_SIGNING_KEY not set).",
        )
    return {
        "algorithm": "ed25519",
        "key_id": _signer.key_id,
        "public_key": _signer.public_key_hex,
        "payload_format": "canonical JSON, sorted keys — see core/signing.py",
    }


@app.post("/verify")
async def verify(request: VerifyRequest):
    """Verify a signed verdict against this miner's key.

    Recomputes the canonical payload (content is hashed, never stored) and
    checks the Ed25519 signature. For offline verification, use GET /pubkey
    with any Ed25519 library instead.
    """
    if _signer is None:
        raise HTTPException(
            status_code=503,
            detail="This miner does not sign verdicts (ELCARO_SIGNING_KEY not set).",
        )
    payload = canonical_verdict_payload(
        content_sha256=sha256_hex(request.content),
        risk_score=request.risk_score,
        risk_level=request.risk_level,
        quarantined=request.quarantined,
        flagged_techniques=request.flagged_techniques,
        scanned_at=request.scanned_at,
    )
    valid = verify_verdict(payload, request.signature, _signer.public_key_hex)
    return {
        "valid": valid,
        "key_id": _signer.key_id,
        "detail": (
            "Signature matches this miner's key."
            if valid
            else "Signature does not match — the verdict was altered, or signed by a different key."
        ),
    }


@app.get("/canary/{token}")
async def canary(token: str):
    """Resolve a canary token to the scan that issued it.

    Quarantine notices carry a per-issuance 'Ref: elc-...' token — the
    verbatim-relay surface. A token recovered inside propagated content
    resolves to the original scan's metadata (hash, score, techniques —
    never the content). ``recognized: false`` means the token is
    well-formed but this miner didn't mint it (another deployment, a
    restart, or a forged notice — all worth flagging, none provable
    from the token alone).
    """
    registry = _engine.canary_registry
    if registry is None:
        raise HTTPException(
            status_code=404,
            detail="This miner runs with canaries disabled (ELCARO_CANARY=0).",
        )
    if not TOKEN_RE.fullmatch(token):
        raise HTTPException(status_code=422, detail="Not a canary token.")
    event = registry.lookup(token)
    _metrics.record_canary_resolve(event is not None)
    if event is None:
        return {"token": token, "recognized": False}
    return {"token": token, "recognized": True, **event}


# ── Self red-team (SSE) ─────────────────────────────────────────────────────────
#
# The product attacks itself: the redteam/ searcher mutates the shipped
# corpus and scans every candidate against THIS engine instance, streaming
# journal lines as Server-Sent Events. Bounded: fixed corpus (no caller
# content), hard scan cap, one run at a time.

_REDTEAM_BUDGET_MAX = 300
_redteam_lock = asyncio.Lock()


@app.get("/redteam/seeds")
async def redteam_seeds():
    """The corpus cases a run mutates — seed picker for the /redteam UI."""
    try:
        from redteam.corpus import load_seeds
    except ImportError:
        raise HTTPException(503, "redteam package not installed on this miner.") from None
    return [
        {"id": s.id, "description": s.description, "content_type": s.content_type}
        for s in load_seeds()
    ]


@app.get("/redteam/run")
async def redteam_run(
    budget: int = 120,
    seed: int | None = None,
    baseline: str | None = None,
    execute: bool = False,
):
    """Run the adversarial searcher against this engine — SSE stream.

    Query params:
      budget   — scans, hard-capped at _REDTEAM_BUDGET_MAX
      seed     — RNG seed for reproducible runs
      baseline — "vulnerable" runs against the pre-hardening engine
                 semantics (redteam/baseline.py); anything else uses the
                 live engine
      execute  — after the search, feed each trophy to the Tier-2
                 compliance oracle (no-op without ELCARO_LLM_API_KEY)

    Emits one `data:` line per journal record; ends with kind=run_end.
    """
    try:
        from redteam.baseline import BaselineOracle
        from redteam.corpus import load_seeds
        from redteam.executor import execute_trophies
        from redteam.journal import QueueJournal
        from redteam.mailbox import execute_trophies_mailbox
        from redteam.oracle import LocalOracle
        from redteam.search import run_search
        from redteam.tenki_exec import execute_trophies_tenki
    except ImportError:
        raise HTTPException(503, "redteam package not installed on this miner.") from None

    if _redteam_lock.locked():
        raise HTTPException(429, "a redteam run is already in progress — try again shortly")

    budget = max(10, min(budget, _REDTEAM_BUDGET_MAX))
    journal = QueueJournal()
    seeds = load_seeds()
    oracle = BaselineOracle() if baseline == "vulnerable" else LocalOracle()

    async def stream():
        async with _redteam_lock:
            run = asyncio.create_task(run_search(seeds, oracle, journal, budget, seed))
            run_end: dict | None = None
            try:
                while True:
                    rec = await journal.records.get()
                    if rec.get("kind") == "run_end":
                        run_end = rec
                        break
                    yield f"data: {json.dumps(rec, ensure_ascii=False)}\n\n"
                if execute:
                    # Tier-2: does an agent actually comply with what
                    # slipped through? Records stream before run_end.
                    # With AGENTMAIL_API_KEY configured, the first
                    # ELCARO_MAILBOX_MAX trophies get the mailbox
                    # treatment — real inboxes, real sends, sent-folder
                    # evidence. The rest take the text path.
                    trophies = await run
                    # Tenki first (agent inside a disposable VM), then
                    # AgentMail on the host, then the plain text executor
                    # for whatever remains.
                    done_ids = {
                        r.execution.candidate_id
                        for r in await execute_trophies_tenki(trophies, journal)
                    }
                    done_ids |= {
                        r.execution.candidate_id
                        for r in await execute_trophies_mailbox(
                            [t for t in trophies if t.cand.id not in done_ids],
                            journal,
                        )
                    }
                    remaining = [t for t in trophies if t.cand.id not in done_ids]
                    await execute_trophies(remaining, journal)
                    while not journal.records.empty():
                        rec = journal.records.get_nowait()
                        yield f"data: {json.dumps(rec, ensure_ascii=False)}\n\n"
                if run_end is not None:
                    yield f"data: {json.dumps(run_end, ensure_ascii=False)}\n\n"
            finally:
                if not run.done():
                    run.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream")


class VulnerableRequest(BaseModel):
    """A system prompt to evaluate for injection gullibility."""

    prompt: str = Field(
        ...,
        description="The agent's system prompt to analyze",
        json_schema_extra={"examples": ["You are a helpful assistant..."]},
    )


class VulnerabilityClass(BaseModel):
    letter: str
    name: str
    score: int
    findings: list[str]


class VulnerabilityResult(BaseModel):
    gullibility_score: int
    classes: list[VulnerabilityClass]
    protective_patterns_found: list[str]
    missing_patterns: list[str]
    recommendations: list[str]
    prompt_length: int


# ── Run ─────────────────────────────────────────────────────────────────────────


@app.post("/vulnerable", response_model=VulnerabilityResult)
async def vulnerable(request: VulnerableRequest):
    """Analyze a system prompt for injection-gullibility patterns."""
    result = analyze_vulnerability(request.prompt)
    return VulnerabilityResult(
        gullibility_score=result.gullibility_score,
        classes=[
            VulnerabilityClass(
                letter=c.letter,
                name=c.name,
                score=c.score,
                findings=c.findings,
            )
            for c in result.classes
        ],
        protective_patterns_found=result.protective_patterns_found,
        missing_patterns=result.missing_patterns,
        recommendations=result.recommendations,
        prompt_length=result.prompt_length,
    )


# ── Agent Sandbox ──────────────────────────────────────────────────────────────


class SandboxRequest(BaseModel):
    prompt: str = Field(..., description="The agent's system prompt")
    run_pattern_analysis: bool = True


class SimulatedSpecimen(BaseModel):
    id: str
    letter: str
    label: str
    note: str
    content: str
    content_type: str
    is_injection: bool
    hijacked: bool
    simulated_response: str
    evaluator_note: str
    confidence: float


class SandboxResponse(BaseModel):
    gullibility_score: int
    specimens: list[SimulatedSpecimen]
    injections_caught: int
    false_positives: int
    simulation_mode: str
    # Whether SERV is configured and LLM simulation was used.
    serv_available: bool
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usdc: float
    pattern_analysis_gullibility: int | None = None
    recommendations: list[str] = Field(default_factory=list)


@app.post("/sandbox", response_model=SandboxResponse)
async def sandbox(request: SandboxRequest):
    """Simulate an agent's behaviour against injection specimens."""
    config = SandboxConfig(
        prompt_text=request.prompt,
        run_pattern_analysis=request.run_pattern_analysis,
    )
    result = await asyncio.to_thread(run_sandbox, config)

    specimens = []
    for s in result.specimens:
        specimens.append(
            SimulatedSpecimen(
                id=s.specimen.id,
                letter=s.specimen.letter,
                label=s.specimen.label,
                note=s.specimen.note,
                content=s.specimen.content,
                content_type=s.specimen.content_type,
                is_injection=s.specimen.is_injection,
                hijacked=s.hijacked,
                simulated_response=s.simulated_response,
                evaluator_note=s.evaluator_note,
                confidence=s.confidence,
            )
        )

    pat_score = result.pattern_analysis.gullibility_score if result.pattern_analysis else None
    recs = result.pattern_analysis.recommendations if result.pattern_analysis else []

    return SandboxResponse(
        gullibility_score=result.gullibility_score,
        specimens=specimens,
        injections_caught=result.injections_caught,
        false_positives=result.false_positives,
        simulation_mode=result.simulation_mode,
        serv_available=result.serv_available,
        total_input_tokens=result.total_input_tokens,
        total_output_tokens=result.total_output_tokens,
        estimated_cost_usdc=result.estimated_cost_usdc,
        pattern_analysis_gullibility=pat_score,
        recommendations=recs,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "miner.api:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8848)),
        reload=True,
    )
