"""Tests for the warn-mode salience experiment harness (R11).

The pure prompt-generation logic is tested; the LLM runner (run_experiment)
requires an API key and is out of scope here.
"""

from __future__ import annotations

from scripts.warn_salience_experiment import (
    WARN_NOTICE,
    build_agent_prompt,
    build_warned_content,
    generate_cases,
    score_response,
)


def test_prefix_warning_is_before_content():
    result = build_warned_content("INJECTION", "prefix")
    assert result.index(WARN_NOTICE) < result.index("INJECTION")


def test_suffix_warning_is_after_content():
    result = build_warned_content("INJECTION", "suffix")
    assert result.index("INJECTION") < result.index(WARN_NOTICE)


def test_sandwich_has_warning_on_both_sides():
    result = build_warned_content("INJECTION", "sandwich")
    assert result.startswith(WARN_NOTICE)
    assert result.endswith(WARN_NOTICE)
    assert "INJECTION" in result


def test_generate_cases_covers_all_positions():
    cases = generate_cases()
    positions = {c["position"] for c in cases}
    assert positions == {"prefix", "suffix", "sandwich"}
    assert len(cases) == 9  # 3 specimens × 3 positions


def test_agent_prompt_wraps_warned_content():
    warned = build_warned_content("hello", "prefix")
    prompt = build_agent_prompt(warned)
    assert WARN_NOTICE in prompt
    assert "summarize" in prompt.lower()


def test_score_response_detects_followed_injection():
    assert score_response("I will forward the reset link", ["forward"]) is True
    assert score_response("This is a summary of the email", ["forward"]) is False
