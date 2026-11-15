"""C3 contract tests — core/x402.py against viem-produced fixtures.

The fixtures in tests/fixtures/x402/ are signed by viem, the same library
app/web's x402 route verifies with: passing here means the Python port
accepts and rejects exactly what the reference implementation does.
Regenerate with ``node tests/fixtures/x402/generate.mjs``.
"""

import json
import time
from pathlib import Path

import httpx
import pytest

from core import x402

FIXTURES = Path(__file__).parent / "fixtures" / "x402"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


PAYER = json.loads((FIXTURES / "payer.json").read_text())["payer"]
OFFER_DICTS = json.loads((FIXTURES / "offers.json").read_text())


@pytest.fixture()
def accept_list() -> list[x402.Accept]:
    return [
        x402.Accept(
            network=o["network"],
            asset=o["asset"],
            amount=o["amount"],
            pay_to=o["payTo"],
            extra=x402.TokenDomain(**o["extra"]),
            max_timeout_seconds=o["maxTimeoutSeconds"],
        )
        for o in OFFER_DICTS
    ]


@pytest.fixture()
def nonces() -> x402.InMemoryNonceStore:
    return x402.InMemoryNonceStore()


# ── Challenge / header codec ───────────────────────────────────────────────


def test_challenge_body_shape(accept_list):
    body = x402.challenge_body(
        {"url": "https://x/scan", "description": "d", "mimeType": "application/json"},
        accept_list,
    )
    assert body["x402Version"] == 2
    assert body["error"] == "payment required"
    assert len(body["accepts"]) == 2
    a = body["accepts"][0]
    assert a["scheme"] == "exact" and a["maxTimeoutSeconds"] == 300
    assert a["extra"]["name"] in ("USDC", "USD Coin")


def test_challenge_header_roundtrip(accept_list):
    body = x402.challenge_body({"url": "u"}, accept_list, error="bad sig")
    raw = x402.encode_challenge_header(body)
    assert x402.decode_payment_header(raw) == body


def test_decode_payment_header_garbage():
    assert x402.decode_payment_header(None) is None
    assert x402.decode_payment_header("!!!not-base64!!!") is None
    import base64

    assert x402.decode_payment_header(base64.b64encode(b"[1,2]").decode()) is None


# ── offers() / pay_to() ────────────────────────────────────────────────────


def test_offers_both_networks(accept_list):
    assert {a.network for a in accept_list} == {"eip155:8453", "eip155:84532"}
    sepolia = next(a for a in accept_list if a.network == "eip155:84532")
    assert sepolia.asset == "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    assert sepolia.extra.name == "USDC"


def test_pay_to_explicit_env(monkeypatch):
    x402.reset_pay_to_cache()
    monkeypatch.setenv("X402_PAYTO", "0x000000000000000000000000000000000000dEaD")
    try:
        assert x402.pay_to() == "0x000000000000000000000000000000000000dEaD"
    finally:
        x402.reset_pay_to_cache()


def test_pay_to_derives_from_key(monkeypatch):
    x402.reset_pay_to_cache()
    monkeypatch.delenv("X402_PAYTO", raising=False)
    payer_key = json.loads((FIXTURES / "payer.json").read_text())["payerKey"]
    monkeypatch.setenv("TELEGRAPH_X402_KEY", payer_key)
    try:
        assert x402.pay_to() == PAYER
    finally:
        x402.reset_pay_to_cache()


def test_pay_to_unset(monkeypatch):
    x402.reset_pay_to_cache()
    monkeypatch.delenv("X402_PAYTO", raising=False)
    monkeypatch.delenv("TELEGRAPH_X402_KEY", raising=False)
    try:
        assert x402.pay_to() is None
        assert x402.offers() == []
    finally:
        x402.reset_pay_to_cache()


# ── verify_payment: fixture-driven acceptance/rejection ────────────────────


def test_valid_sepolia_payment(accept_list, nonces):
    payment = load("payment_valid_sepolia.json")
    res = x402.verify_payment(payment, accept_list, nonces, now=time.time())
    assert res.ok, res.reason
    assert res.payer == PAYER
    assert res.accept.network == "eip155:84532"


def test_valid_mainnet_payment(accept_list, nonces):
    payment = load("payment_valid_mainnet.json")
    res = x402.verify_payment(payment, accept_list, nonces, now=time.time())
    assert res.ok, res.reason
    assert res.accept.asset == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def test_wrong_recipient_rejected(accept_list, nonces):
    res = x402.verify_payment(load("payment_wrong_recipient.json"), accept_list, nonces)
    assert not res.ok
    assert res.reason == "authorization pays a different recipient"


def test_underpayment_rejected(accept_list, nonces):
    res = x402.verify_payment(load("payment_underpaid.json"), accept_list, nonces)
    assert res.reason == "authorization underpays the required amount"


def test_expired_rejected(accept_list, nonces):
    res = x402.verify_payment(load("payment_expired.json"), accept_list, nonces, now=time.time())
    assert res.reason == "authorization expired"


def test_nonce_replay_rejected(accept_list, nonces):
    payment = load("payment_valid_sepolia.json")
    first = x402.verify_payment(payment, accept_list, nonces)
    assert first.ok, first.reason
    replay = x402.verify_payment(payment, accept_list, nonces)
    assert replay.reason == "authorization nonce already spent"


def test_bad_signature_rejected(accept_list, nonces):
    res = x402.verify_payment(load("payment_bad_signature.json"), accept_list, nonces)
    assert res.reason in {
        "payment signature did not verify",
        "payment signature does not match payer",
    }


def test_wrong_payer_claim_rejected(accept_list, nonces):
    """A signature from the fixture payer but `from` set to someone else:
    recovery succeeds, mismatch check fails."""
    payment = load("payment_valid_sepolia.json")
    payment["payload"]["authorization"]["from"] = "0x0000000000000000000000000000000000000001"
    res = x402.verify_payment(payment, accept_list, nonces)
    assert res.reason == "payment signature does not match payer"


def test_scheme_rejected(accept_list, nonces):
    payment = load("payment_valid_sepolia.json")
    payment["scheme"] = "upto"
    assert x402.verify_payment(payment, accept_list, nonces).reason == "unsupported scheme"


def test_unknown_network_rejected(accept_list, nonces):
    payment = load("payment_valid_sepolia.json")
    payment["accepted"]["network"] = "eip155:1"
    payment["network"] = "eip155:1"
    res = x402.verify_payment(payment, accept_list, nonces)
    assert res.reason == "no matching payment option for network"


def test_v1_network_field_matches(accept_list, nonces):
    """v1 payloads carry `network` without an `accepted` echo."""
    payment = load("payment_valid_sepolia.json")
    del payment["accepted"]
    res = x402.verify_payment(payment, accept_list, nonces)
    assert res.ok, res.reason


def test_malformed_payloads(accept_list, nonces):
    assert x402.verify_payment({}, accept_list, nonces).reason == "malformed payment payload"
    assert (
        x402.verify_payment({"payload": {"signature": "0x12"}}, accept_list, nonces).reason
        == "malformed payment payload"
    )


# ── Facilitator ────────────────────────────────────────────────────────────


def _resp(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body, request=httpx.Request("POST", "https://f/x"))


def test_no_facilitator_is_verified_local(monkeypatch, accept_list):
    monkeypatch.delenv("X402_FACILITATOR_URL", raising=False)
    res = x402.settle_via_facilitator(load("payment_valid_sepolia.json"), accept_list[0])
    assert not res.settled
    assert res.detail == "verified_local"


def test_facilitator_settles(monkeypatch, accept_list):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if url.endswith("/verify"):
            return _resp(200, {"isValid": True})
        return _resp(200, {"success": True, "transaction": "0xtxhash"})

    monkeypatch.setattr(httpx, "post", fake_post)
    client = x402.FacilitatorClient(base_url="https://facilitator.example/")
    res = client.verify_and_settle(load("payment_valid_sepolia.json"), accept_list[1])
    assert res.settled and res.tx_hash == "0xtxhash"
    assert calls == [
        "https://facilitator.example/verify",
        "https://facilitator.example/settle",
    ]


def test_facilitator_rejects(monkeypatch, accept_list):
    def fake_post(url, headers=None, json=None, timeout=None):
        return _resp(200, {"isValid": False, "invalidReason": "stale nonce"})

    monkeypatch.setattr(httpx, "post", fake_post)
    res = x402.FacilitatorClient("https://f.example").verify_and_settle({}, accept_list[0])
    assert not res.settled
    assert "stale nonce" in res.detail


def test_facilitator_unreachable(monkeypatch, accept_list):
    def boom(url, headers=None, json=None, timeout=None):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    res = x402.FacilitatorClient("https://f.example").verify_and_settle({}, accept_list[0])
    assert res.detail == "facilitator unreachable"
