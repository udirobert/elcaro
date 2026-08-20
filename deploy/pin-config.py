#!/usr/bin/env python3
"""Pin the Elcaro miner config to IPFS via Pinata, so it can be registered on
the Telegraph Protocol.

Usage
-----
    PINATA_JWT=... python deploy/pin-config.py
    PINATA_JWT=... python deploy/pin-config.py miner/config.yaml

Pinata exposes two REST generations. This script tries the current v3
``/files`` multipart endpoint first and falls back to the legacy v1
``/pinning/pinFileToIPFS`` for older APIs. In both cases the file is uploaded
from local disk (no staged / keyless tricks).

On success it prints the **IPFS CID** — paste that into ``miner/config.yaml``
under ``registration: ipfs_hash`` and commit before registering.

Env:
    PINATA_JWT            Pinata API JWT (required).
    ELCARO_CONFIG_PATH    Optional override for the config path.

The script never logs the token. It only prints the CID and next steps.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import httpx

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "miner" / "config.yaml"

PINATA_V3_URL = "https://uploads.pinata.cloud/v3/files"
PINATA_V1_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
TIMEOUT_S = 90.0


class PinningError(RuntimeError):
    """Raised when Pinata rejects the upload."""


def _jwt() -> str:
    token = os.environ.get("PINATA_JWT", "").strip()
    if not token:
        raise SystemExit(
            "Missing PINATA_JWT. Set it first, e.g.\n"
            "  PINATA_JWT=... python deploy/pin-config.py\n"
            "Create a Pinata JWT at: https://app.pinata.cloud "
            "(API Keys -> New Key -> Admin: Files + Pinning)."
        )
    return token


def _pin_v3(client: httpx.Client, path: Path, token: str) -> str:
    """Pin via the current Pinata v3 /files multipart endpoint."""
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    files = {"file": (path.name, path.read_bytes(), mime)}
    res = client.post(PINATA_V3_URL, headers={"Authorization": f"Bearer {token}"}, files=files)
    if res.status_code not in (200, 201):
        raise PinningError(f"v3 upload failed (HTTP {res.status_code}): {res.text}")
    try:
        cid: str = res.json()["data"]["cid"]
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - network shape
        raise PinningError(f"v3 response missing cid: {res.text[:400]}") from exc
    return cid


def _pin_v1(client: httpx.Client, path: Path, token: str) -> str:
    """Fallback to the legacy v1 endpoint, using the JWT as a bearer token."""
    with path.open("rb") as handle:
        files = {"file": ("config.yaml", handle, "application/x-yaml")}
        res = client.post(
            PINATA_V1_URL,
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
    if res.status_code not in (200, 201):
        raise PinningError(f"v1 failed (HTTP {res.status_code}): {res.text}")
    try:
        cid: str = res.json()["ipfsHash"]
    except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - network shape
        raise PinningError(f"v1 response missing ipfsHash: {res.text[:400]}") from exc
    return cid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()

    path = Path(args.config).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"Config not found: {path}")

    token = _jwt()
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            try:
                cid = _pin_v3(client, path, token)
            except PinningError:
                # Try the legacy endpoint rather than failing outright.
                cid = _pin_v1(client, path, token)
    except httpx.HTTPError as exc:
        raise SystemExit(f"Pinata request failed: {exc}") from exc

    print("Pinned to IPFS:")
    print(f"  CID         : {cid}")
    print(f"  ipfs://     : ipfs://{cid}")
    print(f"  https://ipfs.io/ipfs/{cid}")
    print()
    print("Next: set in miner/config.yaml -> registration: ipfs_hash, then commit:")
    print(f'  ipfs_hash: "{cid}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
