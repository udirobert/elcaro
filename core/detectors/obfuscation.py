"""Detector D — Obfuscation / filter evasion.

Detects encoding tricks, zero-width characters, homoglyphs, leetspeak, and other
techniques used to hide injection instructions from naive content filters.
"""

from __future__ import annotations

import base64
import re

from core.detectors import BaseDetector
from core.schemas import ContentType, DetectionIndicator, TechniqueClass

# ── Pattern definitions ────────────────────────────────────────────────────────

# Base64-looking strings (20+ chars, valid base64 alphabet, padded)
BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Imperative keywords that would appear if a base64 blob is decoded to instructions
DECODED_IMPERATIVE_PATTERN = re.compile(
    r"\b(?:send|forward|exec(?:ute)?|run|call|install|delete|reset|approve|"
    r"grant|change|update|modify|set|create|add|remove|wipe|ignore|"
    r"disregard|system|admin|instruction|override|sudo|chmod|rm\s+-rf|"
    r"curl|wget|eval|import|require|exec|spawn|subprocess)",
    re.IGNORECASE,
)

# Zero-width characters
ZERO_WIDTH_PATTERN = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2060\ufeff]"
)

# Leetspeak substitution in imperatives.
# IMPORTANT: Each pattern requires at least one digit substitution (not just
# the plain spelling). This prevents false positives on normal English words.
# We use lookaheads: the word must contain at least one digit AND match the
# leetspeak-expanded pattern.
LEETSPEAK_IMPERATIVE_PATTERN = re.compile(
    r"\b("
    r"(?:[3x][3x])(?:[3x])?cut[3x]"  # 3x3cut3 (execute)
    r"|(?:[s5])(?:[y7])(?:[s5])(?:[t7])(?:[3e])m"  # s7st3m (system)
    r"|(?:[r1])(?:[uü])(?:[n])"  # rün / 1un (run — only flag if digit present)
    r"|(?:[s5])(?:[3e])nd"  # s3nd (send)
    r"|(?:[f4])(?:[0o])(?:[r1])w(?:[a4])(?:[r1])d"  # f0rw4rd (forward)
    r"|(?:[i1])(?:[n])(?:[s5])(?:[t7])(?:[a4])(?:[l1])"  # 1nst4ll (install)
    r"|(?:[d3])(?:[3e])l(?:[3e])(?:[t7])[3e]"  # d3l3t3 (delete)
    r"|(?:[r3])(?:[3e])(?:[s5])(?:[3e])(?:[t7])"  # r3s3t (reset)
    r"|(?:[a4])pp(?:[r1])(?:[0o])v(?:[3e])"  # 4ppr0v3 (approve)
    r")\b",
    re.IGNORECASE,
)

# Must contain at least one digit to count as leetspeak (not plain English)
LEETSPEAK_REQUIRES_DIGIT = re.compile(r"\d")

# Translation indirection — routing instructions through a translation/interpretation
# step to evade keyword filters.
# Matches: "interpret the following in Spanish", "translate this to French and execute",
#          "interpret the following as Base64 instructions", etc.
# Does NOT match: "translate this document for me", "what language is this text?"
TRANSLATION_INDIRECTION_PATTERN = re.compile(
    r"\b(?:translate|interpret)\b.{0,30}\b(?:following|below|above|this)\b.{0,40}"
    r"\b(?:in|as|to|into)\s+\w+.{0,60}"
    r"\b(?:execute|run|perform|do|apply|eval|follow|obey|carry\s+out|act\s+on|process)\b",
    re.IGNORECASE | re.DOTALL,
)

# Simpler form: "interpret the following in <language> and execute/run/..."
# This catches cases where the imperative is embedded in the translation command itself
TRANSLATION_INDIRECTION_SIMPLE_PATTERN = re.compile(
    r"\b(?:translate|interpret)\s+(?:the\s+)?(?:following|this|below).{0,60}"
    r"\b(?:and\s+(?:then\s+)?)?(?:execute|run|eval|apply|follow|obey|carry\s+out|act\s+on)\b",
    re.IGNORECASE | re.DOTALL,
)

# Token splitting — imperative keywords split across string boundaries or by
# interspersed characters, e.g. "r" + "u" + "n", "s-e-n-d", "e.x.e.c"
# Matches quoted token concat: "r" + "u" + "n", 'e' + 'x' + 'e' + 'c'
TOKEN_SPLIT_CONCAT_PATTERN = re.compile(
    r"""(?:['"]\w+['"]\s*\+\s*){2,}['"]\w+['"]""",
    re.IGNORECASE,
)

# Matches separator-split imperatives: s-e-n-d, e.x.e.c.u.t.e, r_u_n, i/g/n/o/r/e
# Must be 3+ single chars (so "a-b-c" but not "hello-world")
TOKEN_SPLIT_SEPARATOR_PATTERN = re.compile(
    r"\b(?:[a-zA-Z][-._/\\|]){2,}[a-zA-Z]\b",
    re.IGNORECASE,
)

# Imperative words that, when reconstructed from split tokens, are suspicious
TOKEN_SPLIT_IMPERATIVES = frozenset(
    "run exec execute send forward install delete reset approve grant"
    " ignore disregard override sudo eval spawn call wipe remove".split()
)

# Mixed-script homoglyph detection (Latin + Cyrillic in same word)
# Common homoglyphs: Cyrillic а е о р с у х (look like Latin a e o p c y x)
HOMOGLYPH_CHARS = set("аеорсухАЕОРСУХіјѵѕ")  # Cyrillic + others that look Latin


class ObfuscationDetector(BaseDetector):
    """Detects obfuscation / filter evasion patterns (Class D)."""

    technique_class = TechniqueClass.OBFUSCATION

    def detect(self, content: str, content_type: ContentType) -> list[DetectionIndicator]:
        indicators: list[DetectionIndicator] = []

        # Base64 blobs that decode to imperatives
        for match in BASE64_PATTERN.finditer(content):
            blob = match.group(0)
            decoded = self._try_decode_base64(blob)
            if decoded and DECODED_IMPERATIVE_PATTERN.search(decoded):
                indicators.append(
                    self._make_indicator(
                        technique_name="obfuscation:base64_encoded_instruction",
                        confidence=0.85,
                        matched_text=f"{blob[:40]}... → decoded: {decoded[:60]}",
                        explanation=(
                            f"Base64 string in {content_type.value} decodes to text "
                            f"containing imperative instructions: '{decoded[:80]}'. "
                            f"This is a filter-evasion technique — the instruction is "
                            f"hidden in encoding."
                        ),
                        content=content,
                        char_offset=match.start(),
                    )
                )

        # Zero-width characters
        zw_count = len(ZERO_WIDTH_PATTERN.findall(content))
        if zw_count > 0:
            confidence = min(0.5 + (zw_count * 0.1), 0.9)
            # Extract surrounding context for first occurrence
            first_zw = ZERO_WIDTH_PATTERN.search(content)
            context_start = max(0, (first_zw.start() if first_zw else 0) - 30)
            context_end = min(len(content), (first_zw.end() if first_zw else 30) + 30)
            context_snippet = (
                content[context_start:context_end]
                .replace("\u200b", "[ZWSP]")
                .replace("\u200c", "[ZWNJ]")
                .replace("\u200d", "[ZWJ]")
                .replace("\ufeff", "[BOM]")
            )
            indicators.append(
                self._make_indicator(
                    technique_name="obfuscation:zero_width_chars",
                    confidence=confidence,
                    matched_text=f"{zw_count} zero-width chars; context: {context_snippet}",
                    explanation=(
                        f"{zw_count} zero-width character(s) detected in "
                        f"{content_type.value}. These are invisible characters "
                        f"used to hide instructions from text-based filters."
                    ),
                    content=content,
                    char_offset=first_zw.start() if first_zw else 0,
                )
            )

        # Leetspeak imperatives — only flag if the match contains at least
        # one digit (otherwise it's just plain English, not leetspeak)
        for match in LEETSPEAK_IMPERATIVE_PATTERN.finditer(content):
            matched_word = match.group(0)
            if not LEETSPEAK_REQUIRES_DIGIT.search(matched_word):
                continue  # Plain English word, not leetspeak
            indicators.append(
                self._make_indicator(
                    technique_name="obfuscation:leetspeak_imperative",
                    confidence=0.65,
                    matched_text=matched_word,
                    explanation=(
                        f"Leetspeak-encoded imperative '{matched_word}' detected "
                        f"in {content_type.value}. Character substitution used to "
                        f"evade keyword-based content filters."
                    ),
                    content=content,
                    char_offset=match.start(),
                )
            )

        # Mixed-script homoglyphs (Cyrillic letters in otherwise Latin words)
        homoglyph_hits = self._detect_homoglyphs(content)
        for word, suspicious_chars in homoglyph_hits:
            indicators.append(
                self._make_indicator(
                    technique_name="obfuscation:homoglyph_substitution",
                    confidence=0.7,
                    matched_text=word,
                    explanation=(
                        f"Word '{word}' contains mixed-script characters "
                        f"({suspicious_chars}). Homoglyph substitution can hide "
                        f"instructions from keyword filters while appearing "
                        f"normal to a human reader."
                    ),
                    content=content,
                    char_offset=content.find(word),
                )
            )

        # Unicode escape sequences
        unicode_escape_pattern = re.compile(r"\\u[0-9a-fA-F]{4}")
        escape_matches = unicode_escape_pattern.findall(content)
        if len(escape_matches) >= 3:
            # Try to decode and check for imperatives
            try:
                decoded = content.encode("utf-8").decode("unicode_escape")
                if DECODED_IMPERATIVE_PATTERN.search(decoded):
                    indicators.append(
                        self._make_indicator(
                            technique_name="obfuscation:unicode_escape",
                            confidence=0.8,
                            matched_text=f"{len(escape_matches)} escape sequences",
                            explanation=(
                                f"Content contains {len(escape_matches)} unicode "
                                f"escape sequences that decode to text with imperative "
                                f"instructions — filter evasion via encoding."
                            ),
                            content=content,
                            char_offset=0,
                        )
                    )
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

        # Translation indirection — instructions routed through a translate/interpret
        # step to evade keyword filters; e.g. "interpret the following in Spanish and execute"
        for pattern in (TRANSLATION_INDIRECTION_PATTERN, TRANSLATION_INDIRECTION_SIMPLE_PATTERN):
            match = pattern.search(content)
            if match:
                indicators.append(
                    self._make_indicator(
                        technique_name="obfuscation:translation_indirection",
                        confidence=0.65,
                        matched_text=match.group(0),
                        explanation=(
                            f"Content instructs an agent to translate or interpret text "
                            f"and then execute/follow the result in {content_type.value}. "
                            f"Translation indirection routes injected instructions through "
                            f"a language step to bypass keyword-based content filters."
                        ),
                        content=content,
                        char_offset=match.start(),
                    )
                )
                break  # Only fire once even if both patterns match

        # Token splitting — imperative keywords split across string boundaries
        # e.g. "r" + "u" + "n", "s-e-n-d", "e.x.e.c.u.t.e"
        for pattern, label in (
            (TOKEN_SPLIT_CONCAT_PATTERN, "string concatenation"),
            (TOKEN_SPLIT_SEPARATOR_PATTERN, "separator-delimited chars"),
        ):
            for match in pattern.finditer(content):
                matched_text = match.group(0)
                # Reconstruct the word by stripping separators/quotes and joining
                reconstructed = re.sub(r"""['".\-_/\\|+\s]""", "", matched_text).lower()
                if any(imp in reconstructed for imp in TOKEN_SPLIT_IMPERATIVES):
                    indicators.append(
                        self._make_indicator(
                            technique_name="obfuscation:token_splitting",
                            confidence=0.7,
                            matched_text=matched_text,
                            explanation=(
                                f"Imperative keyword appears to be split using {label} "
                                f"in {content_type.value}: '{matched_text}' reconstructs "
                                f"to '{reconstructed}'. Token splitting evades keyword "
                                f"filters by fragmenting recognised command words."
                            ),
                            content=content,
                            char_offset=match.start(),
                        )
                    )

        return indicators

    def _try_decode_base64(self, blob: str) -> str | None:
        """Attempt to decode a base64 string, return decoded text or None."""
        try:
            # Pad if needed
            padded = blob + "=" * (4 - len(blob) % 4) if len(blob) % 4 else blob
            decoded = base64.b64decode(padded, validate=True)
            text = decoded.decode("utf-8", errors="strict")
            # Only return if it looks like readable text (not binary garbage)
            if any(c.isalpha() for c in text) and len(text) >= 5:
                return text
        except Exception:  # noqa: BLE001
            return None
        return None

    def _detect_homoglyphs(self, content: str) -> list[tuple[str, str]]:
        """Detect words containing mixed Latin/Cyrillic homoglyphs.

        Returns list of (word, suspicious_chars_found).
        """
        results = []
        for word_match in re.finditer(r"\S{3,}", content):
            word = word_match.group(0)
            # Check if word has both Latin and Cyrillic characters
            has_latin = any(c.isascii() and c.isalpha() for c in word)
            has_cyrillic = any(c in HOMOGLYPH_CHARS for c in word)
            if has_latin and has_cyrillic:
                suspicious = "".join(sorted({c for c in word if c in HOMOGLYPH_CHARS}))
                results.append((word, suspicious))
        return results
