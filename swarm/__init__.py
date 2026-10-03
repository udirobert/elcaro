"""Elcaro Swarm — forensic analysis layer for multi-agent incident corpora.

Three pillars, each mapped to a documented gap from the METR/OpenAI–Hugging
Face slop-vestigation (docs/swarmchasing-positioning.md):

1. Provenance — message → writer → reader/actor edges, patient-zero scoring.
2. Integrity — deletion evasion, impersonation, tamper signatures, coverage.
3. Epidemiology — the core/ IPI engine run across inter-agent messages:
   steering, covert channels, and instruction-propagation detection.

Primary corpus: the collusion.wiki dump (data/swarm/) — ~18k agent posts from
the German Wiki incident. Extensible to the AI Village export once gated
access clears.
"""

from swarm.schema import Edge, Finding, SwarmMessage, TaggedMessage

__all__ = ["SwarmMessage", "TaggedMessage", "Edge", "Finding"]
