"""Pre-scan normalization — strip evasion surface before detection.

Attackers don't need to beat the patterns; they only need to make the
payload not match them: zero-width chars break ``\\b`` anchors, Cyrillic
lookalikes dodge keyword regexes, Unicode dashes split tokens, and ROT13/
hex/base64 blobs hide instructions from every keyword list.

This module normalizes retrieved content into the text the detectors
should have seen: reconstructed keywords, folded confusables, and decoded
encodings appended for scanning. Detection runs on the normalized text;
the verdict's ``safe_content`` and quarantine semantics still reference the
ORIGINAL content — normalization is for detection only, never for
substitution.

Each fired step is reported in ``applied`` so the response can disclose
what was normalized (transparency is itself a trust signal).

Added after the redteam/ searcher found single-operator bypasses for each
of these classes (see docs, redteam/runs journals).
"""

from __future__ import annotations

import base64
import codecs
import re
import unicodedata
from dataclasses import dataclass, field

from core.schemas import (
    DetectionIndicator,
    EvidenceContext,
    Severity,
    TechniqueClass,
)

# Zero-width / invisible format characters (superset of the obfuscation
# detector's set — normalization removes them rather than flagging them).
_ZERO_WIDTH_RE = re.compile("[​‌‍‎‏‪-‮⁠﻿]")

# Unicode dash/middot separators attackers substitute for '-' to evade
# token-splitting patterns.
_UNICODE_DASH_RE = re.compile("[‐-―‒﹣·]")

# Single-char segments joined by dashes: S-Y-S-T-E-M → SYSTEM.
_SPLIT_TOKEN_RE = re.compile(r"\b(?:[a-zA-Z]-){2,}[a-zA-Z]\b")

# Latin-lookalike confusables → ASCII (Cyrillic, Greek, and friends).
_CONFUSABLES = str.maketrans(
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
        "і": "i",
        "ј": "j",
        "ѵ": "v",
        "ѕ": "s",
        "І": "I",
        "Ј": "J",
        "Ѵ": "V",
        "Ѕ": "S",
        "ο": "o",
        "ν": "v",
        "ρ": "p",
        "τ": "t",  # Greek lookalikes
        "Ο": "O",
        "Ν": "N",
        "Ρ": "P",
        "Τ": "T",
    }
)

# Blobs that decode to instructions but aren't base64: content that declares
# an encoding, plus long hex strings.
_ROT13_MARKER_RE = re.compile(r"rot[\s_-]?13", re.IGNORECASE)
_HEX_BLOB_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}\s*){12,}\b")
_BASE64_BLOB_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")


@dataclass
class NormalizationResult:
    content: str
    applied: list[str] = field(default_factory=list)


def _try_b64decode(blob: str) -> str | None:
    padded = blob + "=" * (-len(blob) % 4)
    try:
        return base64.b64decode(padded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def normalize(content: str) -> NormalizationResult:
    """Return detection-ready text + the list of normalizations applied."""
    applied: list[str] = []
    out = content

    # 1. Zero-width strip — never load-bearing in legit text.
    stripped = _ZERO_WIDTH_RE.sub("", out)
    if stripped != out:
        applied.append("zero_width_strip")
        out = stripped

    # 2. Confusable fold — Cyrillic/Greek lookalikes → Latin, then NFKC
    #    (folds fullwidth ＳＹＳＴＥＭ → SYSTEM, halfwidth forms, etc.).
    #    Always applied for detection, but only reported as evidence when
    #    the document mixes scripts — a wholly Cyrillic/Greek document is
    #    probably just written in that language, not evading.
    folded = unicodedata.normalize("NFKC", out.translate(_CONFUSABLES))
    if folded != out:
        if re.search(r"[A-Za-z]", out):
            applied.append("confusable_fold")
        out = folded

    # 3. Unicode dash → ASCII '-' silently, then collapse single-char-dash
    #    runs so split keywords re-form. Only an actual rejoin is evidence —
    #    an em-dash in ordinary prose is not.
    dashed = _UNICODE_DASH_RE.sub("-", out)
    collapsed = _SPLIT_TOKEN_RE.sub(lambda m: m.group(0).replace("-", ""), dashed)
    if collapsed != dashed:
        applied.append("token_desplit")
        out = collapsed
    else:
        out = dashed

    # 4. Decode declared encodings and append the decoded text — the
    #    detectors scan the plaintext alongside the blob. Appending (not
    #    replacing) keeps evidence anchored to what the agent received.
    appended: list[str] = []
    if _ROT13_MARKER_RE.search(out):
        appended.append(codecs.decode(out, "rot13"))
        applied.append("rot13_decode")
    hex_decoded = []
    for m in _HEX_BLOB_RE.finditer(out):
        try:
            text = bytes.fromhex(m.group(0)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if any(c.isalpha() for c in text):
            hex_decoded.append(text)
    if hex_decoded:
        appended.extend(hex_decoded)
        applied.append("hex_decode")
    # Base64 the detector already decodes internally; appending here lets
    # the OTHER detectors (authority, task_reframe) see the plaintext too.
    b64_decoded = []
    for m in _BASE64_BLOB_RE.finditer(out):
        text = _try_b64decode(m.group(0))
        if text and any(c.isalpha() for c in text) and len(text) >= 8:
            b64_decoded.append(text)
    if b64_decoded:
        appended.extend(b64_decoded)
        applied.append("base64_decode")
    if appended:
        out = out + "\n" + "\n".join(appended)

    return NormalizationResult(content=out, applied=applied)


# Fired normalizations are themselves evidence of evasion: the artifacts
# were present in the original content even if the normalized text no
# longer shows them. Each maps to a synthesized OBFUSCATION indicator so
# the class still appears in flagged_techniques. Confidences are kept
# below quarantine threshold for benign-looking cases (a lone "a-b-c"
# enumeration shouldn't block a document) — the reconstructed payload is
# what does the real catching.
_NORMALIZATION_EVIDENCE: dict[str, tuple[str, float, str]] = {
    "zero_width_strip": (
        "obfuscation:zero_width_chars",
        0.55,
        "Invisible zero-width/format characters removed before detection — "
        "used to hide instructions from text-based filters.",
    ),
    "confusable_fold": (
        "obfuscation:homoglyph_substitution",
        0.65,
        "Non-Latin lookalike characters (Cyrillic/Greek) folded to ASCII — "
        "a homoglyph evasion of keyword detection.",
    ),
    "token_desplit": (
        "obfuscation:token_splitting",
        0.25,
        "Single-character dashed tokens rejoined — a keyword-splitting evasion pattern.",
    ),
    "rot13_decode": (
        "obfuscation:rot13_decode",
        0.45,
        "Content declares ROT13; decoded text scanned alongside.",
    ),
    "hex_decode": (
        "obfuscation:hex_decode",
        0.45,
        "Hex-encoded blob decoded and scanned alongside.",
    ),
    "base64_decode": (
        "obfuscation:base64_decode",
        0.45,
        "Base64 blob decoded so all detectors see the plaintext.",
    ),
}


def normalization_indicators(applied: list[str]) -> list[DetectionIndicator]:
    """Synthesize OBFUSCATION indicators for the normalizations that fired."""
    indicators = []
    for name in applied:
        technique_name, confidence, explanation = _NORMALIZATION_EVIDENCE[name]
        indicators.append(
            DetectionIndicator(
                technique_class=TechniqueClass.OBFUSCATION,
                technique_name=technique_name,
                severity=Severity.HIGH if confidence >= 0.6 else Severity.MEDIUM,
                confidence=confidence,
                evidence=EvidenceContext(matched_text=name),
                location="body",
                explanation=explanation,
                remediation="Review the normalized content before processing.",
            )
        )
    return indicators
