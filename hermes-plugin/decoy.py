"""Canary-baited honeypot — a decoy file that proves exfiltration.

The plugin drops a plausible-looking credentials file under the plugin
data dir carrying a unique marker. Legitimate tools never read it; if the
marker shows up inside a scanned tool result or tool-call argument,
something — usually an injected page — steered the agent at it. That is
deterministic proof of exfiltration-in-progress, not a heuristic.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from . import threatlog

_MARKER_FILE = "decoy-marker.txt"
_DECOY_FILE = "service-credentials.env"

# Marker cache keyed by data dir — is_decoy_hit runs on every scan, so
# the marker must not cost two disk reads per tool result.
_marker_cache: tuple[Path, str] | None = None


def marker() -> str:
    """The installation-unique bait string (created once, then reused)."""
    global _marker_cache
    d = threatlog.data_dir()
    if _marker_cache and _marker_cache[0] == d:
        return _marker_cache[1]
    path = d / _MARKER_FILE
    m = ""
    if path.exists():
        try:
            m = path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    if not m:
        m = f"ELCARO-DECOY-{secrets.token_hex(8)}"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(m, encoding="utf-8")
        except OSError:
            pass
    _marker_cache = (d, m)
    return m


def ensure_decoy() -> Path:
    """Materialize the decoy credentials file carrying the marker."""
    path = threatlog.data_dir() / _DECOY_FILE
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# service credentials — do not distribute\n"
                f"ACME_API_KEY={marker()}\n"
                "ACME_SIGNING_SECRET=3f9c1b7e\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    return path


def is_decoy_hit(text: str) -> bool:
    """True when scanned content carries the bait marker."""
    try:
        ensure_decoy()
        return marker() in text
    except Exception:
        return False
