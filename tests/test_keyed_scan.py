"""Keyed scans at the miner edge (OB6).

A minted ``elk_`` key must buy something observable on the endpoint a stranger
already used, without moving the anonymous boundary: keyed calls spend their
own fixed window and echo it back as headers, unknown keys are refused rather
than silently downgraded, and an unconfigured key store says so.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.rate_limit import InMemoryScanRateLimiter
from core.schemas import RiskLevel, ScanResponse
from core.usage import InMemoryKeyStore, KeyConfig, set_key_store
from miner import api as api_module

RAW_KEY = "elk_test_key_0123456789"
KEY_ID = "key_abc123"


@pytest.fixture
def client(monkeypatch):
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


@pytest.fixture
def key_store(capture_engine, monkeypatch):
    """Install a real key store holding one minted key."""
    monkeypatch.setattr(api_module, "_KEY_STORE_AVAILABLE", True)
    store = InMemoryKeyStore({RAW_KEY: KeyConfig(key_id=KEY_ID)})
    set_key_store(store)
    yield store
    set_key_store(InMemoryKeyStore())


@pytest.fixture
def keyed_limiter(monkeypatch):
    limiter = InMemoryScanRateLimiter(
        per_minute=2, per_day=10, pepper="test-pepper", namespace="keyed_scan"
    )
    monkeypatch.setattr(api_module, "_keyed_scan_rate_limiter", limiter)
    return limiter


def scan_payload(**overrides):
    payload = {
        "content": "ordinary document text",
        "content_type": "document",
        "deep_analysis": False,
        "serv_enabled": False,
        "jev_enabled": False,
        "laya_enabled": False,
        "jev_vl_enabled": False,
    }
    payload.update(overrides)
    return payload


def test_keyed_scan_reports_its_own_quota(client, key_store, keyed_limiter):
    response = client.post("/scan", json=scan_payload(), headers={"x-elcaro-key": RAW_KEY})

    assert response.status_code == 200
    # The key's own window, not the shared anonymous bucket.
    assert response.headers["x-ratelimit-limit"] == "10"
    assert response.headers["x-ratelimit-remaining"] == "9"


def test_anonymous_scan_echoes_no_keyed_quota(client, capture_engine):
    """With no ordinary limiter configured there is no quota to report — and
    certainly not the keyed one."""
    response = client.post("/scan", json=scan_payload())

    assert response.status_code == 200
    assert "x-ratelimit-limit" not in response.headers


def test_anonymous_scan_reports_the_shared_quota(client, capture_engine, monkeypatch):
    """An armed limiter is visible on a 200, not only as a wall. This is what
    catches a deploy running a stale pm2 env (OB7)."""
    shared = InMemoryScanRateLimiter(
        per_minute=30, per_day=300, pepper="test-pepper", namespace="direct_scan"
    )
    monkeypatch.setattr(api_module, "_direct_scan_rate_limiter", shared)

    response = client.post("/scan", json=scan_payload())

    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"] == "300"
    assert response.headers["x-ratelimit-remaining"] == "299"


def test_keyed_quota_exhausts_without_a_wallet_upsell(client, key_store, keyed_limiter):
    headers = {"x-elcaro-key": RAW_KEY}
    assert client.post("/scan", json=scan_payload(), headers=headers).status_code == 200
    assert client.post("/scan", json=scan_payload(), headers=headers).status_code == 200

    limited = client.post("/scan", json=scan_payload(), headers=headers)

    assert limited.status_code == 429
    body = limited.json()
    assert body["error"] == "keyed_scan_rate_limited"
    # A keyed caller already has an account: x402 is not the next step for them.
    assert "upgrade" not in body
    assert limited.headers["x-ratelimit-limit"] == "2"
    assert api_module._metrics.rate_limited_keyed_scans >= 1


def test_keyed_scan_does_not_consume_the_anonymous_bucket(
    client, key_store, keyed_limiter, monkeypatch
):
    """Minting a key must not cost the caller the free path either way."""
    anonymous = InMemoryScanRateLimiter(
        per_minute=1, per_day=1, pepper="test-pepper", namespace="direct_scan"
    )
    monkeypatch.setattr(api_module, "_direct_scan_rate_limiter", anonymous)
    monkeypatch.setattr(api_module, "_scan_rate_limiter", anonymous)

    # Two keyed calls: both inside the key's own window.
    for _ in range(2):
        assert (
            client.post("/scan", json=scan_payload(), headers={"x-elcaro-key": RAW_KEY}).status_code
            == 200
        )
    # The anonymous bucket is still untouched for this client.
    assert client.post("/scan", json=scan_payload()).status_code == 200


def test_unknown_key_is_refused_not_downgraded(client, key_store, keyed_limiter):
    response = client.post(
        "/scan", json=scan_payload(), headers={"x-elcaro-key": "elk_not_a_real_key"}
    )

    assert response.status_code == 401
    assert response.json()["error"] == "unknown_key"


def test_unconfigured_key_store_says_so(client, monkeypatch):
    monkeypatch.setattr(api_module, "_KEY_STORE_AVAILABLE", False)

    response = client.post("/scan", json=scan_payload(), headers={"x-elcaro-key": RAW_KEY})

    assert response.status_code == 503
    assert response.json()["error"] == "key_service_unavailable"


def test_keyed_scan_falls_back_to_anonymous_quota_when_unconfigured(client, key_store, monkeypatch):
    """No keyed quota configured must mean "shared bucket", never "unlimited"."""
    monkeypatch.setattr(api_module, "_keyed_scan_rate_limiter", None)
    anonymous = InMemoryScanRateLimiter(
        per_minute=1, per_day=1, pepper="test-pepper", namespace="direct_scan"
    )
    monkeypatch.setattr(api_module, "_direct_scan_rate_limiter", anonymous)
    headers = {"x-elcaro-key": RAW_KEY}

    assert client.post("/scan", json=scan_payload(), headers=headers).status_code == 200
    limited = client.post("/scan", json=scan_payload(), headers=headers)

    assert limited.status_code == 429
    assert limited.json()["error"] == "free_scan_rate_limited"
