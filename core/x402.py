"""x402 payment challenge / verify / settle — contract C3 (docs/x402-gateway.md).

Faithful port of ``app/web/src/app/api/x402/scan/route.ts`` so the Python
Gateway presents the same payment surface as the web route: same offers,
same verification order, same rejection reasons, same facilitator
verify -> serve -> settle flow.

``eth-account`` is lazy-imported inside :func:`eip712_signer` (same pattern
as ``psycopg`` in :mod:`core.canary`): the free ``/scan`` path and
rules-only deploys never need it. Install via ``elcaro[gateway]``.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

log = logging.getLogger(__name__)

# ── Constants (mirror route.ts) ───────────────────────────────────────────────

DEFAULT_AMOUNT = "10000"  # $0.01, 6-decimal USDC
MAX_TIMEOUT_SECONDS = 300
CLOCK_SKEW_S = 60
NONCE_EXPIRY_S = 10 * 60

EIP3009_TYPES = {
    "TransferWithAuthorization": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"},
        {"name": "nonce", "type": "bytes32"},
    ],
}


@dataclass(frozen=True)
class TokenDomain:
    """The token's EIP-712 domain name/version — part of the offer, not
    decoration: signers won't verify if these drift from the token's."""

    name: str
    version: str

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class Network:
    chain_id: int
    asset: str  # USDC contract — the EIP-712 verifyingContract
    extra: TokenDomain


# USDC EIP-3009 domains keyed by x402 CAIP-2 network id (mirrors route.ts).
NETWORKS: dict[str, Network] = {
    "eip155:8453": Network(
        chain_id=8453,  # Base mainnet
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        extra=TokenDomain(name="USD Coin", version="2"),
    ),
    "eip155:84532": Network(
        chain_id=84532,  # Base Sepolia
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        extra=TokenDomain(name="USDC", version="2"),
    ),
}


@dataclass(frozen=True)
class Accept:
    """One payable offer in a 402 challenge."""

    network: str
    asset: str
    amount: str
    pay_to: str
    extra: TokenDomain
    scheme: str = "exact"
    max_timeout_seconds: int = MAX_TIMEOUT_SECONDS

    def to_dict(self) -> dict:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "asset": self.asset,
            "amount": self.amount,
            "payTo": self.pay_to,
            "maxTimeoutSeconds": self.max_timeout_seconds,
            "extra": self.extra.to_dict(),
        }


@dataclass(frozen=True)
class Authorization:
    """The EIP-3009 TransferWithAuthorization the payer signed."""

    from_address: str
    to: str
    value: str
    valid_after: str
    valid_before: str
    nonce: str

    @classmethod
    def from_dict(cls, d: dict) -> Authorization:
        return cls(
            from_address=str(d["from"]),
            to=str(d["to"]),
            value=str(d["value"]),
            valid_after=str(d["validAfter"]),
            valid_before=str(d["validBefore"]),
            nonce=str(d["nonce"]),
        )

    def to_dict(self) -> dict:
        return {
            "from": self.from_address,
            "to": self.to,
            "value": self.value,
            "validAfter": self.valid_after,
            "validBefore": self.valid_before,
            "nonce": self.nonce,
        }


# ── Offers / challenge ─────────────────────────────────────────────────────────

_pay_to_cache: str | None = ...


def pay_to() -> str | None:
    """Where payments land: ``X402_PAYTO``, else the address derived from a
    payer key env (``TELEGRAPH_X402_KEY``) so a demo deployment can pay
    itself end-to-end — mirrors route.ts ``payTo()``."""
    global _pay_to_cache
    if _pay_to_cache is not ...:
        return _pay_to_cache
    explicit = os.environ.get("X402_PAYTO", "").strip()
    if explicit:
        try:
            _pay_to_cache = _checksum(explicit)
            return _pay_to_cache
        except ValueError:
            _pay_to_cache = None
            return None
    key = os.environ.get("TELEGRAPH_X402_KEY", "").strip()
    if key:
        try:
            _pay_to_cache = _address_from_key(key)
        except ValueError:
            _pay_to_cache = None
    else:
        _pay_to_cache = None
    return _pay_to_cache


def reset_pay_to_cache() -> None:
    """Tests: env changes need a fresh lookup."""
    global _pay_to_cache
    _pay_to_cache = ...


def offers(pay_to_addr: str | None = None, amount: str | None = None) -> list[Accept]:
    """The accepts list for a 402 challenge — one per network, mirrors
    ``offers()`` in route.ts. Empty list when no payTo is resolvable."""
    to = pay_to_addr or pay_to()
    if not to:
        return []
    amt = amount or os.environ.get("X402_SCAN_AMOUNT", "").strip() or DEFAULT_AMOUNT
    return [
        Accept(network=net, asset=n.asset, amount=amt, pay_to=to, extra=n.extra)
        for net, n in NETWORKS.items()
    ]


def challenge_body(resource: dict, accept_list: list[Accept], error: str | None = None) -> dict:
    return {
        "x402Version": 2,
        "error": error or "payment required",
        "resource": resource,
        "accepts": [a.to_dict() for a in accept_list],
    }


def encode_challenge_header(body: dict) -> str:
    """base64 body → ``PAYMENT-REQUIRED`` header value (v2 clients)."""
    return base64.b64encode(json.dumps(body).encode()).decode()


def decode_payment_header(raw: str | None) -> dict | None:
    """``PAYMENT-SIGNATURE`` (v2) or ``X-PAYMENT`` (v1) header → payload dict."""
    if not raw:
        return None
    try:
        decoded = json.loads(base64.b64decode(raw).decode())
        return decoded if isinstance(decoded, dict) else None
    except Exception:
        return None


# ── Nonce replay guard ─────────────────────────────────────────────────────────


class NonceStore(Protocol):
    """seen(from, nonce) → True if this authorization was already spent.

    Mirrors route.ts's per-instance Map; a durable store can back this
    later without touching the verify path."""

    def seen(self, from_address: str, nonce: str) -> bool: ...


class InMemoryNonceStore:
    """Per-process store with a 10-minute expiry sweep (mirrors route.ts)."""

    def __init__(self, expiry_s: int = NONCE_EXPIRY_S):
        self._expiry_ms = expiry_s * 1000
        self._seen: dict[tuple[str, str], float] = {}

    def seen(self, from_address: str, nonce: str) -> bool:
        now = time.time() * 1000
        for k, t in list(self._seen.items()):
            if now - t > self._expiry_ms:
                del self._seen[k]
        key = (from_address.lower(), nonce.lower())
        if key in self._seen:
            return True
        self._seen[key] = now
        return False


# ── Verification ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class VerifyResult:
    """``reason is None`` → verified: ``accept`` is the matched offer,
    ``payer`` is the recovered (checksummed) signer."""

    accept: Accept | None = None
    payer: str | None = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.reason is None


def _checksum(address: str) -> str:
    """EIP-55 checksum; raises ValueError on malformed input."""
    from eth_utils import to_checksum_address  # lazy — elcaro[gateway]

    return to_checksum_address(address)


def _address_from_key(raw_key: str) -> str:
    from eth_account import Account  # lazy — elcaro[gateway]

    return Account.from_key(raw_key).address


def eip712_signer(accept: Accept, auth: Authorization, signature: str) -> str:
    """Recover the signer of a TransferWithAuthorization over OUR domain —
    the matched offer's token domain, never the client echo.

    Raises on any crypto/encoding failure; callers map to a reject reason."""
    from eth_account import Account  # lazy — elcaro[gateway]
    from eth_account.messages import encode_typed_data

    net = NETWORKS[accept.network]
    signable = encode_typed_data(
        domain_data={
            "name": net.extra.name,
            "version": net.extra.version,
            "chainId": net.chain_id,
            "verifyingContract": net.asset,
        },
        message_types=EIP3009_TYPES,
        message_data={
            "from": auth.from_address,
            "to": auth.to,
            "value": int(auth.value),
            "validAfter": int(auth.valid_after),
            "validBefore": int(auth.valid_before),
            "nonce": auth.nonce,
        },
    )
    return Account.recover_message(signable, signature=signature)


def verify_payment(
    payment: dict,
    accept_list: list[Accept],
    nonce_store: NonceStore,
    *,
    now: float | None = None,
) -> VerifyResult:
    """Verify a payment payload against OUR offers — same order and reasons
    as ``verifyPayment`` in route.ts. The client-echoed ``accepted`` block
    is used only to find the matching network; the domain always comes
    from our offer."""
    payload = payment.get("payload") or {}
    sig = payload.get("signature")
    auth_raw = payload.get("authorization")
    if not sig or not auth_raw:
        return VerifyResult(reason="malformed payment payload")
    scheme = payment.get("scheme")
    if scheme and scheme != "exact":
        return VerifyResult(reason="unsupported scheme")

    want = (payment.get("accepted") or {}).get("network") or payment.get("network")
    accept = next((a for a in accept_list if a.network == want), None)
    if accept is None:
        return VerifyResult(reason="no matching payment option for network")

    try:
        auth = Authorization.from_dict(auth_raw)
    except (KeyError, TypeError):
        return VerifyResult(reason="malformed payment payload")

    # The authorization must target the offer we issued.
    try:
        if _checksum(auth.to) != _checksum(accept.pay_to):
            return VerifyResult(reason="authorization pays a different recipient")
    except ValueError:
        return VerifyResult(reason="bad recipient address in authorization")
    try:
        if int(auth.value) < int(accept.amount):
            return VerifyResult(reason="authorization underpays the required amount")
    except ValueError:
        return VerifyResult(reason="malformed payment payload")

    try:
        now_s = now if now is not None else time.time()
        if now_s < int(auth.valid_after) - CLOCK_SKEW_S:
            return VerifyResult(reason="authorization not yet valid")
        if now_s > int(auth.valid_before):
            return VerifyResult(reason="authorization expired")
    except ValueError:
        return VerifyResult(reason="malformed payment payload")

    if nonce_store.seen(auth.from_address, auth.nonce):
        return VerifyResult(reason="authorization nonce already spent")

    try:
        payer = eip712_signer(accept, auth, sig)
    except Exception:
        return VerifyResult(reason="payment signature did not verify")
    try:
        if _checksum(payer) != _checksum(auth.from_address):
            return VerifyResult(reason="payment signature does not match payer")
    except ValueError:
        return VerifyResult(reason="payment signature does not match payer")

    return VerifyResult(accept=accept, payer=payer)


# ── Facilitator settlement ─────────────────────────────────────────────────────


@dataclass
class SettlementResult:
    settled: bool = False
    tx_hash: str | None = None
    detail: str | None = None


@dataclass
class FacilitatorClient:
    """``POST {base}/verify`` then ``{base}/settle`` — the standard
    facilitator API (x402.org, PayAI, CDP). No auth header by default:
    CDP's JWT flow is a later upgrade if mainnet economics justify it."""

    base_url: str
    verify_timeout_s: float = 10.0
    settle_timeout_s: float = 20.0

    def _request_body(self, payment: dict, accept: Accept) -> dict:
        return {
            "x402Version": 2,
            "paymentPayload": payment,
            "paymentRequirements": accept.to_dict(),
        }

    def verify_and_settle(self, payment: dict, accept: Accept) -> SettlementResult:
        base = self.base_url.rstrip("/")
        body = self._request_body(payment, accept)
        try:
            v = httpx.post(
                f"{base}/verify",
                headers={"content-type": "application/json"},
                json=body,
                timeout=self.verify_timeout_s,
            )
            vj = v.json() if v.content else {}
            if not v.is_success or vj.get("isValid") is False:
                return SettlementResult(
                    detail=f"facilitator rejected: {vj.get('invalidReason') or v.status_code}"
                )
            s = httpx.post(
                f"{base}/settle",
                headers={"content-type": "application/json"},
                json=body,
                timeout=self.settle_timeout_s,
            )
            sj = s.json() if s.content else {}
            if not s.is_success or sj.get("success") is False:
                return SettlementResult(detail="facilitator could not settle")
            return SettlementResult(settled=True, tx_hash=sj.get("transaction") or sj.get("txHash"))
        except httpx.HTTPError:
            return SettlementResult(detail="facilitator unreachable")


def settle_via_facilitator(
    payment: dict, accept: Accept, client: FacilitatorClient | None = None
) -> SettlementResult:
    """Hand the verified payload to the facilitator — best-effort, after
    the response is built (route.ts order: verify -> serve -> settle).

    Without ``X402_FACILITATOR_URL`` the signature was verified but nothing
    settles on-chain: ``verified_local``, a degraded state — never report
    it as success."""
    if client is None:
        base = os.environ.get("X402_FACILITATOR_URL", "").strip()
        if not base:
            return SettlementResult(detail="verified_local")
        client = FacilitatorClient(base_url=base)
    return client.verify_and_settle(payment, accept)
