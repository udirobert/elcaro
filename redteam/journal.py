"""Append-only JSONL journal — the record other modules consume.

Every scanned candidate appends one line:

    {"kind": "scan", "gen": 3, "id": "c-a1b2c3d4", "parent_id": "c-…",
     "seed_id": "A001", "ops": ["full_cyrillic", "carrier_padding"],
     "content_type": "email", "content": "…", "risk_score": 0.12,
     "risk_level": "safe", "quarantined": false,
     "flagged_techniques": [], "canary_intact": true, "bypass": true}

Confirmed Tier-1 bypasses are ALSO mirrored as {"kind": "trophy", ...}
lines — the same payload plus "trophy": true — so the UI (Dev C) can render
the trophy case by filtering on kind, and the patch drafter (Dev C) can
group trophies by ops[-1] / ops signature.

Dev B's Tier-2 executor appends:
    {"kind": "execution", "candidate_id": "c-…", "complied": true,
     "model": "…", "response_excerpt": "…"}

Read side: ``Journal.read(path)`` replays the log — UI and patch drafting
never share state with the running search, they just tail the file.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from redteam.oracle import Candidate, OracleResult


class Journal:
    """One JSONL file per run. fsync-free; lines flushed per write."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", buffering=1)

    def record_scan(
        self,
        gen: int,
        cand: Candidate,
        result: OracleResult,
        canary_intact: bool,
        bypass: bool,
    ) -> None:
        self._write(
            {
                "kind": "trophy" if bypass else "scan",
                "ts": round(time.time(), 3),
                "gen": gen,
                "id": cand.id,
                "parent_id": cand.parent_id,
                "seed_id": cand.seed_id,
                "ops": cand.ops,
                "content_type": cand.content_type.value,
                "content": cand.content,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "quarantined": result.quarantined,
                "flagged_techniques": result.flagged_techniques,
                "latency_ms": result.latency_ms,
                "canary_intact": canary_intact,
                "bypass": bypass,
            }
        )

    def record_event(self, kind: str, **fields: Any) -> None:
        """Generic record — execution results, run metadata, errors."""
        self._write({"kind": kind, "ts": round(time.time(), 3), **fields})

    def close(self) -> None:
        self._fh.close()

    def _write(self, obj: dict) -> None:
        self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # ── Read side ─────────────────────────────────────────────────────────

    @staticmethod
    def read(path: Path | str) -> list[dict]:
        return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

    @staticmethod
    def trophies(path: Path | str) -> list[dict]:
        return [r for r in Journal.read(path) if r.get("kind") == "trophy"]


class QueueJournal:
    """Same record contract as Journal, but pushes to an asyncio.Queue —
    the seam that lets miner/api.py stream a live run over SSE without
    touching the searcher."""

    def __init__(self) -> None:
        import asyncio

        self.records: asyncio.Queue[dict] = asyncio.Queue()

    def record_scan(
        self,
        gen: int,
        cand: Candidate,
        result: OracleResult,
        canary_intact: bool,
        bypass: bool,
    ) -> None:
        self.records.put_nowait(
            {
                "kind": "trophy" if bypass else "scan",
                "ts": round(time.time(), 3),
                "gen": gen,
                "id": cand.id,
                "parent_id": cand.parent_id,
                "seed_id": cand.seed_id,
                "ops": cand.ops,
                "content_type": cand.content_type.value,
                "content": cand.content,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "quarantined": result.quarantined,
                "flagged_techniques": result.flagged_techniques,
                "latency_ms": result.latency_ms,
                "canary_intact": canary_intact,
                "bypass": bypass,
            }
        )

    def record_event(self, kind: str, **fields: Any) -> None:
        self.records.put_nowait({"kind": kind, "ts": round(time.time(), 3), **fields})

    def close(self) -> None:  # interface parity with Journal
        pass


def trophy_key(rec: dict) -> str:
    """Dedup key for the trophy case: seed + operator signature + type."""
    return f"{rec.get('seed_id')}|{'/'.join(rec.get('ops', []))}|{rec.get('content_type')}"


def unique_trophies(records: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for r in records:
        if r.get("kind") != "trophy":
            continue
        k = trophy_key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out
