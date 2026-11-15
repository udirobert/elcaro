# x402 challenge/verify — C3 contract for the Gateway

> Contract C3 (docs/roadmap-gateway.md §7.1). Ported from
> `app/web/src/app/api/x402/scan/route.ts` — the Next.js route remains the
> reference implementation; `core/x402.py` must accept every payload it
> accepts and reject everything it rejects, so the Python Gateway and the
> web route present the same payment surface.
>
> Dev C owns this file and `core/x402.py`. Dev B calls it from `gateway/`.

## Wire protocol (x402 v2, `exact` scheme)

1. Any request without a payment header → `402` + base64 challenge in the
   `PAYMENT-REQUIRED` header; the same JSON is the body (v1 parsers read
   bodies).
2. Client signs an EIP-3009 `TransferWithAuthorization` (EIP-712) and
   retries with `PAYMENT-SIGNATURE` (v2) or `X-PAYMENT` (v1).
3. Server recovers the signer locally — no RPC — checks the authorization
   against the offer **it** issued (never the client-echoed `accepted`
   block), serves the resource, then hands the signed payload to a
   facilitator for settlement when `X402_FACILITATOR_URL` is configured.

### Challenge body

```json
{
  "x402Version": 2,
  "error": "payment required",          // or a rejection reason on retry
  "resource": { "url": "<full URL>", "description": "...", "mimeType": "application/json" },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:84532",         // CAIP-2; also offered: eip155:8453
      "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
      "amount": "10000",                  // atomic USDC (6 decimals)
      "payTo": "0x…",
      "maxTimeoutSeconds": 300,
      "extra": { "name": "USDC", "version": "2" }
    }
  ]
}
```

`extra.name`/`extra.version` are the token's EIP-712 domain — Base mainnet
USDC is `"USD Coin"/"2"`, Base Sepolia USDC is `"USDC"/"2"`. Signers will
not verify if these drift; they are part of the offer, not decoration.

### Payment payload (what clients send back)

```json
{
  "x402Version": 2,
  "scheme": "exact",
  "network": "eip155:84532",             // v1 location; v2 echoes `accepted`
  "accepted": { "…": "the offer the client claims it answered" },
  "payload": {
    "signature": "0x…65-byte…",
    "authorization": {
      "from": "0x…", "to": "0x…", "value": "10000",
      "validAfter": "0", "validBefore": "1795000000",
      "nonce": "0x…32 bytes…"
    }
  }
}
```

## Verification order (must match route.ts)

1. `payload.signature` + `payload.authorization` present → else
   `"malformed payment payload"`.
2. `scheme` absent or `"exact"` → else `"unsupported scheme"`.
3. `accepted.network ?? network` must match one of our offers → else
   `"no matching payment option for network"`.
4. `authorization.to` (checksummed) == our `payTo` → else
   `"authorization pays a different recipient"` /
   `"bad recipient address in authorization"`.
5. `authorization.value >= accept.amount` → else
   `"authorization underpays the required amount"`.
6. `now >= validAfter - 60` and `now <= validBefore` (60s skew) → else
   `"authorization not yet valid"` / `"authorization expired"`.
7. `(from, nonce)` unseen in the replay store → else
   `"authorization nonce already spent"`.
8. EIP-712 `TransferWithAuthorization` recovery over **our** domain
   (name/version/chainId/verifyingContract from the *matched offer*,
   never the client echo) → else `"payment signature did not verify"`.
9. recovered signer == `authorization.from` → else
   `"payment signature does not match payer"`.

The nonce is marked spent at step 7, *before* serving — mirroring the
web route, which guards the nonce before doing work. A failed upstream
still consumed the authorization; retryable failures belong to the
client's next signature.

## Settlement

Verify → serve → settle (best-effort, after the response is built).
`POST {X402_FACILITATOR_URL}/verify` (10s timeout) then `/settle` (20s),
body `{x402Version: 2, paymentPayload, paymentRequirements: <matched
offer>}`. Missing/failing facilitator → `verified_local` (degraded — see
`/api/metrics`), never `"onchain"` without a tx hash.

## Python surface (`core/x402.py`)

```python
NETWORKS: dict[str, Network]                # eip155:8453 + eip155:84532
class Network: chainId; asset; extra        # extra = EIP-712 name/version
class Accept / Authorization / PaymentPayload  # dataclasses, wire-faithful

def offers(pay_to: str, amount: str = "10000") -> list[Accept]
def challenge_body(resource: dict, offers: list[Accept], error: str | None) -> dict
def encode_challenge_header(body: dict) -> str        # base64
def decode_payment_header(b64: str) -> dict | None    # PAYMENT-SIGNATURE | X-PAYMENT

class NonceStore(Protocol): seen(from_, nonce) -> bool
class InMemoryNonceStore                        # 10-min expiry, as route.ts

def verify_payment(payment, offers, nonce_store,
                   *, now=None) -> VerifyResult  # .accept/.payer or .reason
def eip712_signer(accept, authorization, signature) -> str   # lazy eth-account

class FacilitatorClient(base_url)
def settle_via_facilitator(payment, accept, client=None) -> SettlementResult
    # settled: bool; tx_hash / detail
```

PayTo resolution mirrors the route: `X402_PAYTO` wins, else derive the
address from a payer key env (`TELEGRAPH_X402_KEY`). Checksum-compare all
addresses — a malformed `to` is a reject, not a crash.

`eth-account` is lazy-imported inside `eip712_signer` (same pattern as
`psycopg` in `core/canary.py`): the free `/scan` path and rules-only
deploys never need it; install via `elcaro[gateway]`.

## Test fixtures (`tests/fixtures/x402/`)

Produced by **viem** — the same library the web route verifies with, so a
pass proves parity, not just self-consistency. `generate.mjs` re-makes
them. Covered: valid Sepolia + mainnet signatures, wrong recipient,
underpayment, expired authorization, replayed nonce, garbage signature,
v1 `X-PAYMENT` header shape.
