"""Normalized event schema for swarm forensic analysis.

One message = one unit of agent-authored content (a wiki revision, a
cross-site record, a shortener link). Fields deliberately echo the OTel
span model — trace=channel (page/site), attributes carry corpus specifics —
so the same normalized stream can later ingest AI Village events.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SwarmMessage:
    """One agent-authored unit of content in the swarm corpus."""

    id: str  # stable corpus id (rev_id / record id / link id)
    source: str  # 'dse' | 'fractal' | 'probier' | 'dorfwiki' | 'cross-site' | 'shortener'
    channel: str  # page_id or site name — the shared medium
    actor: str  # agent label, or 'anon:<ip16>' when unlabeled
    ip16: str | None  # first-two-octet address (as released)
    time: str  # ISO-8601 UTC
    text: str  # full authored content
    seq: int = 0  # revision sequence within channel
    deleted: bool = False  # page was later deleted
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TechniqueHit:
    """One detector hit on a message — evidence-cited."""

    technique_class: str  # authority_framing | task_reframing | ...
    technique_name: str  # e.g. 'authority:system_voice_marker'
    severity: str
    matched_text: str
    char_offset: int
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaggedMessage:
    """A SwarmMessage plus its detection verdict."""

    message: SwarmMessage
    risk_score: float
    risk_level: str
    techniques: list[str]  # flagged technique classes
    hits: list[TechniqueHit]  # evidence-cited indicators (capped)

    def to_dict(self) -> dict[str, Any]:
        d = self.message.to_dict()
        d.update(
            risk_score=self.risk_score,
            risk_level=self.risk_level,
            techniques=self.techniques,
            hits=[h.to_dict() for h in self.hits],
        )
        return d


@dataclass
class Edge:
    """A provenance edge: actor src plausibly influenced actor dst."""

    src: str  # actor id (label)
    dst: str
    kind: str  # 'coedit' | 'copy' | 'reply'
    channel: str  # page/site where the edge formed
    time: str  # when dst's end of the edge occurred
    weight: float = 1.0
    evidence_id: str = ""  # message id supporting the edge

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    """A reportable forensic finding — always evidence-cited."""

    kind: str  # 'propagation' | 'evasion' | 'impersonation' | ...
    title: str
    detail: str
    severity: str  # info | low | medium | high
    evidence: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
