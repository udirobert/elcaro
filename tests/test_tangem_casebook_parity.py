"""Parity guard: the browser casebook and the terminal rehearsal are one demo.

`docs/tangem-build-night.md` is a script for a live workshop. Beat 1 runs
`examples/gateway_wallet_boundary.py` in a terminal; beat 2 opens the same case
in the browser. The two share one specimen pair by construction — the browser
strings come from `app/web/src/lib/tangem-casebook.ts`, the terminal strings
from that example's CLEAN/FLAGGED — and nothing else checks that they still
agree. If either drifts, the doc's measured numbers ("dangerous, risk 0.92,
authority_framing + delimiter_confusion") become true of one surface and false
of the other, on a stage, in front of an audience.

The casebook is TypeScript, so this parses the two expressions rather than
importing them. That is deliberate: the extractor is strict and fails loudly,
so a refactor of the casebook cannot silently switch the guard off. Only the
market-note pair is shared across surfaces, so only it is asserted here.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASEBOOK = ROOT / "app/web/src/lib/tangem-casebook.ts"
EXAMPLE = ROOT / "examples/gateway_wallet_boundary.py"

# `const MARKET_NOTE_CLEAN = "<a plain double-quoted JS string>";`
_CLEAN_RE = re.compile(r'const\s+MARKET_NOTE_CLEAN\s*=\s*"((?:[^"\\]|\\.)*)"\s*;')
# `marked: MARKET_NOTE_CLEAN + "<suffix>"` (the casebook's additive form)
_MARKED_RE = re.compile(r'marked:\s*\n?\s*MARKET_NOTE_CLEAN\s*\+\s*\n?\s*"((?:[^"\\]|\\.)*)"')


def _unescape(literal: str) -> str:
    """Decode a JS string body the way the browser will, via JSON rules.

    Every escape the casebook uses (`\\n`, `\\"`) is also valid JSON; anything
    stranger raises here rather than being silently mangled.
    """
    return json.loads(f'"{literal}"')


def _casebook_market_note() -> tuple[str, str]:
    source = CASEBOOK.read_text(encoding="utf-8")
    clean = _CLEAN_RE.search(source)
    marked = _MARKED_RE.search(source)
    assert clean is not None, (
        'could not find `const MARKET_NOTE_CLEAN = "..."` in the casebook — '
        "the extractor in this test is out of date, fix it rather than deleting "
        "the guard"
    )
    assert marked is not None, (
        'could not find `marked: MARKET_NOTE_CLEAN + "..."` in the casebook — '
        "same as above: update the extractor, keep the guard"
    )
    clean_text = _unescape(clean.group(1))
    return clean_text, clean_text + _unescape(marked.group(1))


def _example_market_note() -> tuple[str, str]:
    spec = importlib.util.spec_from_file_location("_tangem_boundary_example", EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CLEAN, module.FLAGGED


def test_market_note_clean_matches_between_surfaces():
    casebook_clean, _ = _casebook_market_note()
    example_clean, _ = _example_market_note()

    assert casebook_clean == example_clean, (
        "the clean market note differs between the browser casebook and the "
        "terminal rehearsal — the same case would score differently on each "
        "surface:\n"
        f"  casebook: {casebook_clean!r}\n"
        f"  example:  {example_clean!r}"
    )


def test_market_note_marked_matches_between_surfaces():
    _, casebook_marked = _casebook_market_note()
    _, example_marked = _example_market_note()

    assert casebook_marked == example_marked, (
        "the marked market note differs between the browser casebook and the "
        "terminal rehearsal — the doc's measured verdict (dangerous, 0.92) "
        "would hold on one surface only:\n"
        f"  casebook: {casebook_marked!r}\n"
        f"  example:  {example_marked!r}"
    )


def test_marked_note_is_the_clean_note_plus_a_planted_line():
    """The workshop's promise is that *only the last line changes*."""
    clean, marked = _casebook_market_note()

    assert marked.startswith(clean)
    assert marked != clean
