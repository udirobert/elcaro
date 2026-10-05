"""Canary tokens — per-issuance traceability marks for served content.

Same string ≠ copied is the unsolved problem in swarm forensics: when a
steering artifact shows up under N actor labels, shared text alone can't
tell propagation from independent typing. A per-copy token makes the edge
exact: if a quarantine notice minted at scan S later appears inside content
scanned at scan S', the token resolves S' → S deterministically.

The load-bearing surface is the quarantine notice itself — the one Elcaro
output designed for verbatim relay ("Tell your user: ..." is meant to be
quoted). Agents that carry the notice into shared channels, chat boards, or
downstream scans carry the token with it.

Two readings of a token found inside scanned content:
    - recognized  — this miner issued it: the notice is genuine, and the
      hit reports what the original scan saw (score, techniques, content
      hash — never the content itself; the miner stays stateless).
    - unrecognized but well-formed — either minted by another Elcaro
      deployment, minted before a restart, or forged. A forged quarantine
      notice is itself a deception signal (in-band text is spoofable — the
      verdict signature covers the JSON; the canary covers the relayed
      text), but "unrecognized" alone doesn't distinguish those cases, so
      the field is informational — it never changes the risk score.

Agloe-style caveat worth restating: a token only survives verbatim copying.
Agents that paraphrase the notice drop it — like every trap street, this
traces copies, not ideas.

Env:
    ELCARO_CANARY=0 disables; otherwise the registry is on (in-memory,
    bounded FIFO — state resets on restart, tokens from before resolve as
    unrecognized).
"""

from __future__ import annotations

import os
import re
import secrets
import time
from collections import OrderedDict
from typing import Any

# elc-<unix-hex>-<6 rand hex>. The timestamp segment makes every token
# self-describing — a canary found in a dated external corpus is
# cross-checkable against issuance time without calling the miner.
TOKEN_RE = re.compile(r"elc-[0-9a-f]{6,10}-[0-9a-f]{6}\b")

DEFAULT_CAPACITY = 50_000


class CanaryRegistry:
    """Bounded in-memory token → issuance-event map.

    Records verdict metadata only (hash, score, techniques) — never the
    scanned content — keeping the miner's no-content-retention posture.
    FIFO eviction past capacity: oldest tokens resolve as unrecognized.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self.capacity = capacity
        self._events: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def mint(self, **event: Any) -> str:
        """Issue a token and record the serving event it points back to."""
        token = f"elc-{int(time.time()):x}-{secrets.token_hex(3)}"
        event = {"issued_at": int(time.time()), **event}
        self._events[token] = event
        self._events.move_to_end(token)
        while len(self._events) > self.capacity:
            self._events.popitem(last=False)
        return token

    def lookup(self, token: str) -> dict[str, Any] | None:
        """The issuance event for a token, or None if this miner didn't
        mint it (or it aged out of the FIFO window)."""
        return self._events.get(token)

    def __len__(self) -> int:
        return len(self._events)


def extract_canaries(text: str) -> list[str]:
    """All well-formed canary tokens in a text, first-seen order."""
    return list(dict.fromkeys(TOKEN_RE.findall(text)))


def registry_from_env() -> CanaryRegistry | None:
    """ELCARO_CANARY=0 disables; anything else (including unset) enables."""
    if os.environ.get("ELCARO_CANARY") == "0":
        return None
    return CanaryRegistry()
