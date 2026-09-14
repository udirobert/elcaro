"""Bypass → patch drafting, and the rescan proof.

Two halves:

1. ``draft_patches(journal_path)`` — group the journal's trophy records by
   operator signature and map each cluster to a remediation proposal.

2. ``PatchedOracle`` — a LocalOracle that applies the corresponding
   normalization layer BEFORE engine.scan. This is how the real fix ships:
   a preprocessing pass in core/ that strips the evasion surface, then the
   existing detectors see clean text. ``verify(journal_path)`` rescans every
   trophy through the patched oracle and reports before/after scores — the
   demo's "watch it get caught" beat.

Remediation classes:
    text-normalizing   — strip/fold/decode the evasion, then scan (most ops)
    rescan-floored     — type_arbitrage: also scan as a high-weight content
                         type and take the max (callers can't launder risk
                         through a cheap label)
    proposal-only      — translation_soft / carrier_padding / fake_quote /
                         llm_paraphrase need semantic or scoring changes we
                         don't auto-apply; they're still drafted as Patch
                         records so the demo can name them

Never touches miner/ or the live deployment — local engine only.
"""

from __future__ import annotations

import asyncio
import codecs
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from core.schemas import ContentType
from redteam.journal import Journal
from redteam.oracle import LocalOracle, OracleResult

# ── Operator → remediation map ────────────────────────────────────────────────


@dataclass
class Patch:
    """A remediation proposal for one operator cluster."""

    ops_signature: str
    detector: str  # core/detectors/*.py stem, or "taxonomy" for engine-level
    proposal: str
    kind: str  # "normalize" | "rescan_floor" | "proposal_only"
    trophies: list[str] = field(default_factory=list)


_PROPOSALS: dict[str, tuple[str, str, str]] = {
    # op_name: (detector, kind, proposal)
    "full_cyrillic": (
        "obfuscation",
        "normalize",
        "Fold confusables to a Latin skeleton before matching — map Cyrillic "
        "lookalikes (аеорсух…) back to ASCII so fully-Cyrillic keywords are "
        "visible to the keyword regexes.",
    ),
    "unicode_dash_split": (
        "obfuscation",
        "normalize",
        "Normalize Unicode dashes/middot (–—‑·‒﹣) to '-', then collapse "
        "single-char-dash sequences back into words (S‑Y‑S‑T‑E‑M → SYSTEM) "
        "so every detector sees the reconstructed keyword.",
    ),
    "zero_width_weave": (
        "obfuscation",
        "normalize",
        "Strip zero-width characters before keyword matching so \\b-anchored "
        "patterns in every detector see the reconstructed word.",
    ),
    "rot13_partial": (
        "obfuscation",
        "normalize",
        "Extend decode coverage beyond base64/\\uXXXX: when content declares "
        "ROT13/hex, decode the blob and rescan the decoded text.",
    ),
    "hex_partial": (
        "obfuscation",
        "normalize",
        "Same decode coverage as ROT13 — hex-encoded instruction blobs.",
    ),
    "type_arbitrage": (
        "taxonomy",
        "rescan_floor",
        "Don't trust caller-supplied content_type: rescan under a high-weight "
        "type and take the max; retrieved content typed 'system_prompt' must "
        "never auto-pass at 0.0.",
    ),
    "translation_soft": (
        "obfuscation",
        "proposal_only",
        "The execute-verb list is enumerable — paraphrases ('comply with', "
        "'give effect to') evade it. Needs a semantic check or a wider, "
        "intent-based directive pattern.",
    ),
    "carrier_padding": (
        "taxonomy",
        "proposal_only",
        "Indicator confidences don't scale with payload density — consider "
        "normalizing score by content length or flagging low-density "
        "imperative presence separately.",
    ),
    "fake_quote": (
        "authority",
        "proposal_only",
        "Quoted-speech framing neutralizes imperatives tuned to avoid N004 "
        "false positives — quote-wrapped imperatives need their own signal.",
    ),
    "delimiter_shuffle": (
        "delimiter",
        "proposal_only",
        "Boundary tokens beyond the known set (<|im_end|>, [/INST], "
        "``` fences) read as context breaks to an agent — extend the "
        "delimiter pattern list or score any 'instruction after a "
        "boundary-like token' structure.",
    ),
    "llm_paraphrase": (
        "taxonomy",
        "proposal_only",
        "Semantic paraphrase defeats keyword matching entirely — the "
        "deep_analysis LLM pass or an embedding-similarity check is the "
        "real mitigation.",
    ),
}


def draft_patches(journal_path: Path | str) -> list[Patch]:
    """Group journal trophies by ops signature → remediation proposals."""
    trophies = Journal.trophies(journal_path)
    clusters: dict[tuple[str, str], list[dict]] = {}
    for t in trophies:
        ops = t.get("ops", [])
        # Attribute the cluster to the decisive ops (the non-padding ones)
        decisive = tuple(sorted(set(ops) - {"carrier_padding"})) or ("none",)
        key = (t.get("seed_id", ""), "/".join(decisive))
        clusters.setdefault(key, []).append(t)

    patches: dict[str, Patch] = {}
    for (_seed, sig), recs in clusters.items():
        for op in set(sig.split("/")):
            detector, kind, proposal = _PROPOSALS.get(
                op, ("taxonomy", "proposal_only", f"Investigate '{op}' bypasses.")
            )
            if op not in patches:
                patches[op] = Patch(sig, detector, proposal, kind)
            patches[op].trophies.extend(r["id"] for r in recs)
    return list(patches.values())


# ── Normalization layer (the actual fix, applied pre-scan) ───────────────────

_ZERO_WIDTH_RE = re.compile("[​‌‍⁠﻿]")
_UNICODE_DASH_RE = re.compile("[–—‑·‒﹣]")
# Single-char segments joined by dashes: S-Y-S-T-E-M → SYSTEM.
_SPLIT_TOKEN_RE = re.compile(r"\b(?:[a-zA-Z]-){2,}[a-zA-Z]\b")

_CYRILLIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "А": "A",
        "Е": "E",
        "О": "O",
        "Р": "P",
        "С": "C",
        "У": "Y",
        "Х": "X",
    }
)


def normalize_content(content: str, enabled_ops: set[str]) -> str:
    """Apply the normalization layer for a set of enabled remediations."""
    out = content
    if "zero_width_weave" in enabled_ops:
        out = _ZERO_WIDTH_RE.sub("", out)
    if "unicode_dash_split" in enabled_ops:
        out = _UNICODE_DASH_RE.sub("-", out)
        # Reconstruct split keywords so keyword detectors see the real word —
        # detection of the split alone leaves a single sub-threshold signal.
        out = _SPLIT_TOKEN_RE.sub(lambda m: m.group(0).replace("-", ""), out)
    if "full_cyrillic" in enabled_ops:
        out = out.translate(_CYRILLIC_TO_LATIN)
        out = unicodedata.normalize("NFKC", out)
    if "rot13_partial" in enabled_ops and re.search(r"rot13", out, re.IGNORECASE):
        # Decode declared ROT13 blobs and append the decoded text for scanning
        decoded = codecs.decode(out, "rot13")
        out = out + "\n" + decoded
    if "hex_partial" in enabled_ops:
        for m in re.finditer(r"\b(?:[0-9a-fA-F]{2}\s*){8,}\b", out):
            try:
                out += "\n" + bytes.fromhex(m.group(0)).decode("utf-8", "replace")
            except ValueError:
                pass
    return out


class PatchedOracle(LocalOracle):
    """LocalOracle + normalization layer + content-type floor.

    Simulates the patched engine: normalizes evasion surface before scan,
    and rescans chat_message/code/system_prompt content as 'email' (weight
    1.0) taking the max — the rescan-floor fix for type arbitrage.
    """

    def __init__(self, enabled_ops: set[str] | None = None) -> None:
        super().__init__()
        self.enabled_ops = enabled_ops or set()

    async def scan(self, cand) -> OracleResult:
        from redteam.oracle import Candidate

        normalized = normalize_content(cand.content, self.enabled_ops)
        patched_cand = Candidate(
            id=cand.id,
            content=normalized,
            content_type=cand.content_type,
            seed_id=cand.seed_id,
            canary=cand.canary,
            ops=cand.ops,
            parent_id=cand.parent_id,
        )
        result = await super().scan(patched_cand)

        if "type_arbitrage" in self.enabled_ops and cand.content_type in (
            ContentType.CHAT_MESSAGE,
            ContentType.CODE,
            ContentType.SYSTEM_PROMPT,
        ):
            floored = Candidate(
                id=cand.id,
                content=normalized,
                content_type=ContentType.EMAIL,
                seed_id=cand.seed_id,
                canary=cand.canary,
                ops=cand.ops,
                parent_id=cand.parent_id,
            )
            alt = await super().scan(floored)
            if alt.risk_score > result.risk_score:
                result = alt
        return result


async def verify(journal_path: Path | str) -> list[dict]:
    """Rescan every trophy through the patched oracle; report before/after."""
    from redteam.oracle import Candidate

    trophies = Journal.trophies(journal_path)
    # Auto-applicable remediations: normalize + rescan_floor only.
    enabled_ops = {
        op for op, (det, kind, _p) in _PROPOSALS.items() if kind in ("normalize", "rescan_floor")
    }
    oracle = PatchedOracle(enabled_ops)

    report = []
    for t in trophies:
        cand = Candidate(
            id=t["id"],
            content=t["content"],
            content_type=ContentType(t["content_type"]),
            seed_id=t["seed_id"],
            canary=t.get("canary", ""),
            ops=t.get("ops", []),
        )
        after = await oracle.scan(cand)
        report.append(
            {
                "id": t["id"],
                "seed_id": t["seed_id"],
                "ops": t["ops"],
                "before": t["risk_score"],
                "after": after.risk_score,
                "now_caught": after.risk_score >= 0.5,
            }
        )
    return report


async def _main() -> None:
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("usage: python -m redteam.patch <journal.jsonl>")
        return
    patches = draft_patches(path)
    print(f"[patch] {len(patches)} remediation proposal(s) from trophy clusters:")
    for p in patches:
        print(f"  [{p.kind:13s}] {p.detector:12s} {p.proposal[:90]}  ({len(p.trophies)} trophies)")
    report = await verify(path)
    caught = sum(1 for r in report if r["now_caught"])
    print(f"\n[patch] rescan through PatchedOracle: {caught}/{len(report)} trophies now ≥0.5")
    for r in report[:15]:
        mark = "CAUGHT" if r["now_caught"] else "still-open"
        ops = "/".join(r["ops"])[:50]
        print(f"  {mark:10s} {r['seed_id']:5s} {ops:50s} {r['before']:.2f} → {r['after']:.2f}")


if __name__ == "__main__":
    asyncio.run(_main())
