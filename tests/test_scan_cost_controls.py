"""Tests for miner-edge free-scan cost controls.

The public miner must protect itself even when callers bypass the Netlify
proxy: anonymous traffic is rate-limited when configured and cannot invoke
paid second-opinion rails. The paid x402 lane proves it is ours with an
internal proxy token and only then unlocks premium rails.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.rate_limit import InMemoryScanRateLimiter
from core.schemas import RiskLevel, ScanResponse
from miner import api as api_module


@pytest.fixture
def client(monkeypatch):
    # Explicitly close the local-development escape hatch: these tests are
    # about the production anonymous boundary.
    monkeypatch.delenv("ELCARO_ALLOW_ANONYMOUS_PREMIUM", raising=False)
    monkeypatch.delenv("ELCARO_INTERNAL_PROXY_TOKEN", raising=False)
    return TestClient(api_module.app)


@pytest.fixture
def capture_engine(monkeypatch):
    captured: dict = {}

    class FakeEngine:
        def scan(self, request):
            captured["request"] = request
            return ScanResponse(
                risk_score=0.1,
                risk_level=RiskLevel.SAFE,
                flagged_techniques=[],
                indicators=[],
                summary="fake",
                content_type=request.content_type,
                latency_ms=1,
            )

    monkeypatch.setattr(api_module, "_engine", FakeEngine())
    return captured


def scan_payload(**overrides):
    payload = {
        "content": "ordinary document text",
        "content_type": "document",
        "deep_analysis": True,
        "serv_enabled": True,
        "jev_enabled": True,
        "laya_enabled": True,
        "jev_vl_enabled": True,
    }
    payload.update(overrides)
    return payload


def test_anonymous_scan_preserves_premium_rails_within_quota(client, capture_engine):
    """The free tier remains useful: premium rails are not silently stripped.
    Cost control comes from the smaller durable premium quota, tested below."""
    response = client.post("/scan", json=scan_payload())

    assert response.status_code == 200
    request = capture_engine["request"]
    assert request.deep_analysis is True
    assert request.serv_enabled is True
    assert request.jev_enabled is True
    assert request.laya_enabled is True
    assert request.jev_vl_enabled is True


def test_paid_lane_token_preserves_premium_rails(client, capture_engine, monkeypatch):
    monkeypatch.setenv("ELCARO_INTERNAL_PROXY_TOKEN", "test-internal-token")

    response = client.post(
        "/scan",
        json=scan_payload(),
        headers={
            "x-elcaro-internal-token": "test-internal-token",
            "x-elcaro-premium": "1",
        },
    )

    assert response.status_code == 200
    request = capture_engine["request"]
    assert request.deep_analysis is True
    assert request.serv_enabled is True
    assert request.jev_enabled is True
    assert request.laya_enabled is True
    assert request.jev_vl_enabled is True


def test_internal_proxy_token_alone_does_not_bypass_premium_quota(
    client, capture_engine, monkeypatch
):
    """The free browser proxy is trusted for client-IP forwarding but is not
    a paid lane; it must not accidentally become a quota bypass."""
    monkeypatch.setenv("ELCARO_INTERNAL_PROXY_TOKEN", "test-internal-token")
    premium_limiter = InMemoryScanRateLimiter(
        per_minute=1, per_day=1, pepper="test-pepper", namespace="premium_scan"
    )
    monkeypatch.setattr(api_module, "_premium_scan_rate_limiter", premium_limiter)

    headers = {"x-elcaro-internal-token": "test-internal-token"}
    assert client.post("/scan", json=scan_payload(), headers=headers).status_code == 200
    limited = client.post("/scan", json=scan_payload(), headers=headers)

    assert limited.status_code == 429
    assert limited.json()["error"] == "free_premium_scan_rate_limited"


def test_rate_limit_returns_429_upsell_and_headers(client, capture_engine, monkeypatch):
    limiter = InMemoryScanRateLimiter(per_minute=2, per_day=10, pepper="test-pepper")
    monkeypatch.setattr(api_module, "_scan_rate_limiter", limiter)
    payload = scan_payload(
        deep_analysis=False,
        serv_enabled=False,
        jev_enabled=False,
        laya_enabled=False,
        jev_vl_enabled=False,
    )

    assert client.post("/scan", json=payload).status_code == 200
    assert client.post("/scan", json=payload).status_code == 200
    limited = client.post("/scan", json=payload)

    assert limited.status_code == 429
    body = limited.json()
    assert body["error"] == "free_scan_rate_limited"
    assert body["upgrade"]["endpoint"] == "/api/x402/scan"
    assert body["upgrade"]["type"] == "x402"
    assert "retry-after" in {k.lower() for k in limited.headers.keys()}
    assert limited.headers["x-ratelimit-limit"] == "2"
    assert limited.headers["x-ratelimit-remaining"] == "0"


def test_premium_scans_have_a_separate_smaller_anonymous_quota(client, capture_engine, monkeypatch):
    premium_limiter = InMemoryScanRateLimiter(
        per_minute=1, per_day=1, pepper="test-pepper", namespace="premium_scan"
    )
    monkeypatch.setattr(api_module, "_premium_scan_rate_limiter", premium_limiter)

    assert client.post("/scan", json=scan_payload()).status_code == 200
    limited = client.post("/scan", json=scan_payload())

    assert limited.status_code == 429
    body = limited.json()
    assert body["error"] == "free_premium_scan_rate_limited"
    assert "second-opinion" in body["message"]
    assert body["upgrade"]["endpoint"] == "/api/x402/scan"


def test_authorized_premium_lane_bypasses_free_quota(client, capture_engine, monkeypatch):
    monkeypatch.setenv("ELCARO_INTERNAL_PROXY_TOKEN", "test-internal-token")
    limiter = InMemoryScanRateLimiter(per_minute=1, per_day=1, pepper="test-pepper")
    premium_limiter = InMemoryScanRateLimiter(
        per_minute=1, per_day=1, pepper="test-pepper", namespace="premium_scan"
    )
    monkeypatch.setattr(api_module, "_scan_rate_limiter", limiter)
    monkeypatch.setattr(api_module, "_premium_scan_rate_limiter", premium_limiter)

    headers = {
        "x-elcaro-internal-token": "test-internal-token",
        "x-elcaro-premium": "1",
    }
    payload = scan_payload()
    assert client.post("/scan", json=payload, headers=headers).status_code == 200
    assert client.post("/scan", json=payload, headers=headers).status_code == 200


def test_trusted_client_ip_assertion_requires_internal_token(monkeypatch):
    """Caller-supplied x-elcaro-client-ip is ignored unless the internal token
    proves the request came through our web proxy."""
    monkeypatch.setenv("ELCARO_INTERNAL_PROXY_TOKEN", "test-internal-token")

    class Req:
        headers = {"x-elcaro-client-ip": "203.0.113.10"}
        client = None

    assert api_module._client_ip(Req()) != "203.0.113.10"

    class TrustedReq:
        headers = {
            "x-elcaro-client-ip": "203.0.113.10",
            "x-elcaro-internal-token": "test-internal-token",
        }
        client = None

    assert api_module._client_ip(TrustedReq()) == "203.0.113.10"
