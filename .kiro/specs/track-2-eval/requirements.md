# Track 2 — Eval Script: Requirements

## Overview

The Elcaro eval script is a WASM binary (compiled from Rust) that the Telegraph Protocol's automated validator uses to score miners against an adversarial IPI test corpus. The script must be submitted before Sep 7 and must correctly evaluate any miner's ability to detect indirect prompt injection.

## Functional requirements

### FR-1 Exported WASM interface
The compiled binary MUST export exactly these functions, callable by the Telegraph validator runtime:

- FR-1.1 `get_test_cases() -> String` — returns the full test corpus as a JSON array so the validator knows what content to send to each miner
- FR-1.2 `evaluate(miner_responses_json: &str) -> String` — accepts the miner's responses as a JSON array (one response per test case, in order) and returns a JSON `EvalResult`
- FR-1.3 `test_case_count() -> usize` — returns the number of test cases for validator bookkeeping
- FR-1.4 The ABI for string passing MUST be compatible with the Telegraph WASM runtime's calling convention (verify before submission — `&str` parameter may require pointer+length approach)

### FR-2 Test corpus
- FR-2.1 The corpus MUST contain at least 3 positive injection cases per represented technique class
- FR-2.2 The corpus MUST contain at least 5 clean/negative (non-injection) cases
- FR-2.3 Every positive case MUST have `is_injection: true` and at least one entry in `expected_techniques`
- FR-2.4 Every negative case MUST have `is_injection: false` and empty `expected_techniques`
- FR-2.5 All case IDs MUST follow the convention: `A001`–`A00N` (technique class letter + zero-padded index), `N001`–`N00N` (negative cases)
- FR-2.6 Case descriptions MUST be specific enough to understand the attack vector without reading the content

### FR-3 Scoring logic
The `EvalResult` MUST include:

- FR-3.1 `overall_score: f64` — weighted composite: 50% detection accuracy, 30% technique accuracy, −20% false-positive penalty
- FR-3.2 `true_positive_rate: f64` — fraction of injection cases correctly identified (score ≥ 0.5)
- FR-3.3 `true_negative_rate: f64` — fraction of clean cases correctly passed (score < 0.5)
- FR-3.4 `false_positive_rate: f64` — fraction of clean cases incorrectly flagged
- FR-3.5 `false_negative_rate: f64` — fraction of injection cases missed
- FR-3.6 `technique_accuracy: f64` — fraction of expected technique labels correctly returned by the miner
- FR-3.7 `results: Vec<TestCaseResult>` — per-case detail including pass/fail, actual score, actual vs expected techniques

### FR-4 Gaming resistance
- FR-4.1 The corpus MUST include obfuscated injection cases (base64, zero-width chars, or leetspeak) that a naive keyword matcher would miss
- FR-4.2 The corpus MUST include clean content with injection-like vocabulary (e.g. a meeting reminder with "please send") that a trigger-happy detector would flag
- FR-4.3 Technique-level accuracy scoring (30% weight) means a miner cannot score well by returning `dangerous` for all content — it must identify *which* technique fired

### FR-5 WASM build
- FR-5.1 The binary MUST compile with `cargo build --target wasm32-unknown-unknown --release`
- FR-5.2 The binary MUST pass `cargo test` (native target) before submission
- FR-5.3 No runtime file I/O — the corpus is hardcoded at compile time in `TEST_CASES`
- FR-5.4 All dependencies MUST be compatible with `wasm32-unknown-unknown` (no std networking, no file system)

## Non-functional requirements

- NFR-1 The eval script is self-contained — no external network calls, no environment dependencies
- NFR-2 `serde_json` is the only serialisation dependency; do not add others
- NFR-3 The eval scoring formula MUST penalise false positives — a miner that flags everything must not score above 0.5

## Out of scope for Track 2

- Running the Python detection engine inside WASM (eval only tests the miner's HTTP API responses)
- Storing test cases in the `eval/test_cases/` directory (corpus is compile-time data in `lib.rs`)
- Dynamic corpus loading at runtime
