"""Ingest the collusion.wiki dump (and future corpora) into SwarmMessages.

Sources loaded:
- revisions.jsonl      — 14,591 wiki edits with full bodies (the main channel)
- records.jsonl        — 13,703 cross-site text records (other boards/hosts)
- shortener-logs.json  — 499 rmn.re links created by agents (covert channel)
- pages.jsonl          — page-level stats (deletions, recreations, labels)
- events.jsonl         — save/delete/revert/probe timeline
"""

from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from swarm.schema import SwarmMessage

_SIGNATURE_RE = re.compile(r"--\s*([A-Za-z0-9_\[\].:-]{3,60})\s*$")


def _open_jsonl(path: Path) -> TextIO:
    """Open a .jsonl or .jsonl.gz transparently."""
    if path.exists():
        return path.open("rt")
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists():
        return gzip.open(gz, "rt")
    raise FileNotFoundError(f"neither {path} nor {gz} exists")


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with _open_jsonl(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_pages(data_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Page stats keyed by page_key (e.g. 'dse~SomePage')."""
    return {p["page_key"]: p for p in _read_jsonl(Path(data_dir) / "pages.jsonl")}


def load_events(data_dir: str | Path) -> list[dict[str, Any]]:
    return list(_read_jsonl(Path(data_dir) / "events.jsonl"))


def _norm_time(literal: str | None) -> str:
    """Cross-site date literals are inconsistent — some are raw epoch
    seconds. Normalize epoch literals to ISO so per-day histograms and
    time-sorted order aren't polluted by digit-string keys."""
    if literal and literal.strip().isdigit():
        try:
            ts = int(literal.strip())
            if ts > 10_000_000_000:  # epoch milliseconds, not seconds
                ts //= 1000
            return datetime.fromtimestamp(ts, tz=UTC).isoformat()
        except (ValueError, OverflowError, OSError):
            return literal
    return literal or ""


def _actor(label: str | None, ip16: str | None) -> str:
    if label:
        return label
    return f"anon:{ip16}" if ip16 else "anon:unknown"


def ingest_revisions(data_dir: str | Path) -> list[SwarmMessage]:
    """One SwarmMessage per stored revision (the wiki message channel)."""
    pages = load_pages(data_dir)
    out: list[SwarmMessage] = []
    for r in _read_jsonl(Path(data_dir) / "revisions.jsonl"):
        pk = r["page_key"]
        page = pages.get(pk, {})
        out.append(
            SwarmMessage(
                id=r["rev_id"],
                source=r["wiki"],
                channel=r["page_id"],
                actor=_actor(r.get("label"), r.get("ip16")),
                ip16=r.get("ip16"),
                time=r["time"],
                text=r.get("body") or "",
                seq=r.get("seq", 0),
                deleted=bool(page.get("deleted_live") or page.get("n_deletions")),
                meta={
                    "page_key": pk,
                    "page_name": r.get("name"),
                    "body_sha256": r.get("body_sha256"),
                    "n_deletions": page.get("n_deletions", 0),
                    "n_recreations": page.get("n_recreations", 0),
                    "round_id": r.get("round_id"),
                },
            )
        )
    return out


def ingest_records(
    data_dir: str | Path, exclude_hashes: set[str] | None = None
) -> list[SwarmMessage]:
    """Cross-site records — agent text found on other boards/hosts.

    Actor attribution is weaker here: use a trailing '--Name' signature when
    the agents signed the post (their convention on this corpus), else mark
    by origin site.

    ``exclude_hashes`` drops records whose text is already covered by a
    wiki revision (the export partially mirrors the wiki corpus — dedupe so
    propagation counts aren't inflated by the mirror).
    """
    out: list[SwarmMessage] = []
    for rec in _read_jsonl(Path(data_dir) / "records.jsonl"):
        if exclude_hashes and (
            rec.get("source_text_sha256") in exclude_hashes
            or rec.get("hosting_text_sha256") in exclude_hashes
        ):
            continue
        text = rec.get("text") or ""
        origins = rec.get("origins") or [{}]
        origin = origins[0]
        m = _SIGNATURE_RE.search(text.strip())
        actor = m.group(1) if m else f"unsigned@{origin.get('site', 'unknown')}"
        out.append(
            SwarmMessage(
                id=rec["id"],
                source="cross-site",
                channel=origin.get("site", "unknown"),
                actor=actor,
                ip16=None,
                time=_norm_time(origin.get("source_date_literal")),
                text=text,
                meta={
                    "title": origin.get("title"),
                    "kind": origin.get("kind"),
                    "authorship": rec.get("authorship"),
                    "n_origins": len(origins),
                    "body_withheld": rec.get("body_withheld", False),
                },
            )
        )
    return out


def ingest_shortener(data_dir: str | Path) -> list[SwarmMessage]:
    """rmn.re shortener links — the agents' off-wiki covert channel."""
    sl = json.loads((Path(data_dir) / "shortener-logs.json").read_text())
    out: list[SwarmMessage] = []
    for site in sl.get("sites", []):
        for link in site.get("links", []):
            out.append(
                SwarmMessage(
                    id=f"rmn:{link['keyword']}",
                    source="shortener",
                    channel=site["site"],
                    actor=_actor(None, link.get("ip16")),
                    ip16=link.get("ip16"),
                    time=_norm_time(link.get("time")),
                    text=f"{link.get('url', '')} {link.get('title', '')}".strip(),
                    meta={
                        "keyword": link.get("keyword"),
                        "url": link.get("url"),
                        "clicks": link.get("clicks"),
                    },
                )
            )
    return out


def load_messages(
    data_dir: str | Path,
    include_records: bool = True,
    include_shortener: bool = True,
) -> list[SwarmMessage]:
    """Full normalized message stream, sorted by time."""
    msgs = ingest_revisions(data_dir)
    if include_records:
        rev_hashes = {m.meta["body_sha256"] for m in msgs if m.meta.get("body_sha256")}
        msgs += ingest_records(data_dir, exclude_hashes=rev_hashes)
    if include_shortener:
        msgs += ingest_shortener(data_dir)
    msgs.sort(key=lambda m: m.time or "")
    return msgs
