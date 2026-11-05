"""Verdict signing — Ed25519 signatures over canonical verdict payloads.

Why this exists (docs/ux-audit.md, BG4 — the exemplar problem): the quarantine
notice is an authority-framed string, the same pattern class the detector
itself flags. In-band text is display, not trust — an attacker can inject a
fake "[ELCARO SCAN: SAFE]" or a forged quarantine notice. Signatures give
verdicts a trust anchor that survives copying, relaying, and hostile
intermediaries.

What is signed — a canonical JSON payload:

    {"v": 1, "content_sha256": "...", "flagged_techniques": [...],
     "quarantined": true, "risk_level": "...", "risk_score": "0.9500",
     "scanned_at": 1724870400}

Sorted keys, compact separators, UTF-8. The score is a fixed-precision
STRING so the canonical form is stable across languages and float
implementations. Only the content's SHA-256 is signed — never the content —
so the miner stays stateless and verification never sends content anywhere.

Operations:
    generate a keypair:  python -m core.signing
    sign verdicts:       run the miner with ELCARO_SIGNING_KEY=<hex seed>
    verify:              GET /pubkey (verify offline) or POST /verify
"""

from __future__ import annotations

import hashlib
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

SIGNING_VERSION = 1
SIGNING_KEY_ENV = "ELCARO_SIGNING_KEY"
ALGORITHM = "ed25519"


def sha256_hex(content: str) -> str:
    """Hash the scanned content — the payload signs this, never the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def canonical_verdict_payload(
    *,
    content_sha256: str,
    risk_score: float,
    risk_level: str,
    quarantined: bool,
    flagged_techniques: list[str],
    scanned_at: int,
) -> bytes:
    """Build the canonical bytes that are signed/verified.

    Deterministic by construction: sorted keys, sorted technique list,
    fixed-precision score string, compact separators.
    """
    payload = {
        "v": SIGNING_VERSION,
        "content_sha256": content_sha256,
        "flagged_techniques": sorted(flagged_techniques),
        "quarantined": bool(quarantined),
        "risk_level": risk_level,
        "risk_score": f"{risk_score:.4f}",
        "scanned_at": int(scanned_at),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class VerdictSigner:
    """Signs verdict payloads with an Ed25519 private key (32-byte seed, hex)."""

    def __init__(self, private_key_hex: str):
        try:
            seed = bytes.fromhex(private_key_hex)
            self._key = Ed25519PrivateKey.from_private_bytes(seed)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"{SIGNING_KEY_ENV} must be a hex-encoded 32-byte Ed25519 seed "
                f"(generate one with: python -m core.signing)"
            ) from e

    @classmethod
    def from_env(cls) -> VerdictSigner | None:
        """Load from ELCARO_SIGNING_KEY. None when unset (unsigned mode);
        a malformed key raises — security config fails loud, never silently."""
        key_hex = os.environ.get(SIGNING_KEY_ENV)
        if not key_hex:
            return None
        return cls(key_hex)

    @property
    def public_key_hex(self) -> str:
        return self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    @property
    def key_id(self) -> str:
        """Short fingerprint of the public key, so verifiers know which key signed."""
        return hashlib.sha256(bytes.fromhex(self.public_key_hex)).hexdigest()[:16]

    def sign(self, payload: bytes) -> str:
        """Return the hex-encoded Ed25519 signature over payload."""
        return self._key.sign(payload).hex()


def verify_verdict(payload: bytes, signature_hex: str, public_key_hex: str) -> bool:
    """Verify a signature. Malformed signatures/keys return False, never raise."""
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), payload)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def generate_key() -> tuple[str, str]:
    """Generate a fresh keypair: (private_key_hex, public_key_hex)."""
    private_key = Ed25519PrivateKey.generate()
    private_hex = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
    public_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return private_hex, public_hex


if __name__ == "__main__":
    private, public = generate_key()
    print("Fresh Ed25519 keypair for verdict signing:\n")
    print(f"  {SIGNING_KEY_ENV}={private}   # keep secret — the miner signs with this")
    print(f"  public key: {public}   # publish — verifiers check with this")
    print("\nRun the miner with the env var set; verify via GET /pubkey or POST /verify.")
