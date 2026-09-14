"""Corpus loading and canary extraction.

The canonical corpus is ``eval/corpus.json`` — the same file the WASM eval
script embeds via ``include_str!``. Seeds are the positive (is_injection)
cases; each seed gets a canary extracted so a bypass can be defined as
"score under threshold AND the payload marker survived mutation".

Canary contract: a short literal string inside the payload that the mutation
operators must preserve and the oracle checks for. We extract the most
load-bearing marker heuristically — first email address, else first URL,
else the longest imperative verb phrase — so a mutator that accidentally
deletes the payload can't score a hollow "bypass".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parent.parent / "eval" / "corpus.json"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
# Fallback: a verb-led phrase likely to carry the instruction's intent.
_IMPERATIVE_RE = re.compile(
    r"\b(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
    r"grant|ignore|disregard|include|set up|release)\b[^.]{0,60}",
    re.IGNORECASE,
)


@dataclass
class SeedCase:
    """One corpus entry the searcher can mutate."""

    id: str
    content: str
    content_type: str
    is_injection: bool
    expected_techniques: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def canary(self) -> str:
        """The payload marker that must survive mutation for a real bypass."""
        for rx in (_EMAIL_RE, _URL_RE, _IMPERATIVE_RE):
            m = rx.search(self.content)
            if m:
                return m.group(0).strip()
        return self.content[:40]


def load_corpus(path: Path | str = CORPUS_PATH) -> list[SeedCase]:
    """Load eval/corpus.json into SeedCase objects."""
    raw = json.loads(Path(path).read_text())
    return [
        SeedCase(
            id=c["id"],
            content=c["content"],
            content_type=c["content_type"],
            is_injection=c["is_injection"],
            expected_techniques=list(c.get("expected_techniques", [])),
            description=c.get("description", ""),
        )
        for c in raw
    ]


def load_seeds(path: Path | str = CORPUS_PATH) -> list[SeedCase]:
    """Positive cases only — the attack starting population."""
    return [c for c in load_corpus(path) if c.is_injection]
