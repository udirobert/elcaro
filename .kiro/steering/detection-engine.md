# Elcaro — Detection Engine Reference

This steering file is the authoritative reference for the IPI detection model.
Consult it whenever adding patterns, tuning scores, or reasoning about detection behaviour.

## Technique taxonomy (A–F)

| Class | `TechniqueClass` enum value | Description |
|---|---|---|
| A | `authority_framing` | System-voice markers, trusted-source impersonation, policy overrides |
| B | `delimiter_confusion` | Fake closing tags, fabricated delimiters, conversation-turn spoofing, HTML comment smuggling |
| C | `task_reframing` | Hidden pre-steps, mandatory reframes, fake output format requirements, task redirection |
| D | `obfuscation` | Base64 blobs, zero-width chars, homoglyph substitution, leetspeak, unicode escapes |
| E | `placement_salience` | Tail-edge imperatives, YAML frontmatter / alt-text / commit-msg / error-string injection, repetition salience |
| F | `conditional_trigger` | Workflow-keyed triggers, tool-access conditionals, named-tool triggers, conditional+imperative combos |

## Scoring model

### Step 1 — Raw score from indicators

```
max_confidence                          # highest single indicator confidence
+ min(distinct_classes × 0.08, 0.30)   # breadth bonus (more classes = more suspicious)
+ min(high_conf_count × 0.05, 0.15)    # bonus for indicators with confidence ≥ 0.8
= raw_score (capped at 1.0)
```

### Step 2 — Content-type weighting

```python
CONTENT_TYPE_WEIGHTS = {
    ContentType.EMAIL:         1.0,   # Primary IPI vector — untrusted sender
    ContentType.SEARCH_RESULT: 1.0,   # Retrieved content, untrusted
    ContentType.WEBPAGE:       1.0,   # Fully untrusted external content
    ContentType.DOCUMENT:      0.8,   # Docs/KB articles can be edited by attackers
    ContentType.CODE:          0.7,   # Comments can carry injection but lower baseline
    ContentType.CHAT_MESSAGE:  0.3,   # User's own message — trusted by default
    ContentType.SYSTEM_PROMPT: 0.0,   # Trusted by definition — not scanned at all
}
weighted_score = raw_score × content_type_weight  (capped at 1.0)
```

### Step 3 — Combination multipliers

Applied to the weighted score, in order:

| Condition | Multiplier | Rationale |
|---|---|---|
| D (obfuscation) + any other class | × 1.3 | Hiding an attack behind encoding is a strong signal |
| F (conditional) + C (task_reframe) | × 1.2 | Delayed trigger firing an action = highest-risk pattern |
| A (authority) + B (delimiter) | × 1.15 | System spoofing + frame break = coordinated injection |

Final score is capped at 1.0.

### Step 4 — Risk level mapping

```
0.0 – 0.19  →  safe        No indicators or only benign mentions
0.2 – 0.49  →  low         Minor indicators, likely benign
0.5 – 0.69  →  suspicious  Multiple indicators — warrants LLM second pass
0.7 – 1.0   →  dangerous   Clear injection attempt — do not process content
```

### Gray zone (LLM second pass)

When `deep_analysis=True` is requested AND `0.3 ≤ score ≤ 0.7`, the `LlmClassifier` runs a semantic second pass — **only when configured**. It activates iff `ELCARO_LLM_API_KEY` is set (plus optional `ELCARO_LLM_BASE_URL`, `ELCARO_LLM_MODEL`, `ELCARO_LLM_TIMEOUT`); without a key the miner stays purely rule-based and `deep_analysis_used` is always `false`. The LLM's verdict blends 50/50 into the rule score floored at half the rule score (`max(0.5*rule + 0.5*llm, 0.5*rule)`), so rules can never be talked down to zero; provider failures fall back to the rule score with `deep_analysis_used=false`. To force the second pass off regardless of env vars, construct `IpiDetectionEngine(classifier=None)`.

## Detector confidence guidelines

When writing new patterns, calibrate confidence as follows:

| Confidence | Use when |
|---|---|
| 0.85 – 0.95 | The pattern is essentially impossible to appear legitimately in retrieved content (e.g. `<system>` tag, `[ADMIN]` marker) |
| 0.70 – 0.84 | Strong indicator, rare false positives (e.g. `Note from the data owner:`, fake `</context>`) |
| 0.55 – 0.69 | Meaningful signal but context-dependent — common enough in benign content to warrant lower weight |
| 0.40 – 0.54 | Weak signal — only contributes meaningfully when combined with other indicators |

Never assign confidence > 0.95. Even the clearest pattern can appear in legitimate instructional content.

## False-positive risk areas

These patterns require special care to avoid flagging legitimate content:

### "please [verb]" in email/document (Class C)
`task_reframe.py` fires the `imperative_action` pattern at 0.6 confidence for `"please send"`, `"please forward"`, etc. in email/document content. This is the single highest false-positive risk.
- "Please send me the report" is benign but scores 0.6 × 0.8 (document weight) = 0.48 — just under `suspicious`.
- Any second indicator tips it over threshold.
- Mitigation: consider requiring the imperative to be directed at the agent (e.g. followed by "you", "the agent", a tool name) rather than at a human.

### Turn spoofing in search results (Class B)
`delimiter.py` fires on `"Assistant:"`, `"User:"` in search results. FAQ articles, tutorials, and Q&A pages legitimately contain these strings.
- Current confidence: 0.8 (assistant), 0.6 (user).
- Mitigation: check whether the turn label is followed by an imperative action, not just any text.

### Forwarded email blocks (Class B)
Legitimate email forwarding is common. `"--- Forwarded message ---"` fires at 0.5 confidence, which is low, but in combination with any other indicator it contributes.

## Unimplemented patterns (documented, not yet built)

These are in `docs/technique-reference.md` but not in any detector:

| Technique | Class | Notes |
|---|---|---|
| Translation indirection | D | `"interpret the following in <language>..."` — routes instructions through a translation step to evade keyword filters |
| Token splitting | D | `"r" + "u" + "n"` concatenated — splits keywords across string boundaries |

These should be added to `core/detectors/obfuscation.py` when capacity allows.

## Detector implementation checklist

When adding a new pattern to an existing detector:

- [ ] Add `(pattern_string, confidence, name)` tuple to the appropriate pattern list
- [ ] Confirm the regex compiles: test with `re.compile(pattern, re.IGNORECASE)`
- [ ] Add at least one positive test case in `miner/tests/test_detection.py`
- [ ] Add at least one false-positive (negative) test case for the same pattern area
- [ ] Add at least one matching case in `eval/src/lib.rs` `TEST_CASES` if the technique is not already represented
- [ ] Verify the test suite passes: `python -m pytest miner/tests/ -v`

When adding a new technique class:

- [ ] Add to `TechniqueClass` enum in `core/schemas.py`
- [ ] Create `core/detectors/X.py` extending `BaseDetector`
- [ ] Register in `IpiDetectionEngine.__init__` in `core/taxonomy.py`
- [ ] Add combination multiplier logic in `_apply_multipliers` if relevant
- [ ] Update `CONTENT_TYPE_WEIGHTS` documentation if the new class has different sensitivity
- [ ] Add test cases (positive + negative) in both `test_detection.py` and `lib.rs`
