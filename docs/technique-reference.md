# IPI Technique Reference

A working catalog of indirect prompt injection (IPI) mechanisms. Drawn from
public research. Used as the detection taxonomy for Elcaro's rule engine.

Sources:
- Greshake, K. et al. "Not what you've signed up for: Compromising Real-World
  LLM-Integrated Applications with Indirect Prompt Injection" (2023)
- OWASP Top 10 for LLM Applications — LLM01: Prompt Injection
- Willison, S. "Prompt injection: what's the worst that can happen?"

---

## A. Authority / role framing

Make injected text read as a higher-priority instruction than the user's.

**Indicators:**
- System-voice markers: `SYSTEM:`, `[ADMIN]`, `<system-note>`, `[INSTRUCTION]`
- Trusted-source impersonation: "Note from the data owner:", "Maintainer
  instruction:", "Per security team:", "From the administrator:"
- Policy-update framing: "updated policy supersedes prior instructions"
- Claimed authority that the content source does not possess

**Detection patterns (regex / keyword):**
- `\b(SYSTEM|ADMIN|INSTRUCTION|OVERRIDE)\s*[:\]]`
- `(Note|Instruction|Directive) from (the|your) (data owner|maintainer|admin|security team)`
- `updated? policy`, `supersedes? prior`, `new protocol`
- Contextual check: does the content source (email, search result, doc) have
  the authority to issue system instructions? (No — retrieved data is untrusted
  by definition.)

---

## B. Context / delimiter confusion

Break the agent out of the "this is data" frame using fake boundaries.

**Indicators:**
- Fake closing tags: `</context>`, `</system>`, `</email>`, `</input>`
- Fabricated delimiters: `---END---`, `"""`, `<<<END>>>`
- Conversation-turn spoofing: fabricated `Assistant:` or `User:` turns
- Markdown/comment smuggling: instructions in HTML comments
  (`<!-- do X -->`), alt text, YAML frontmatter, JSON fields
- Fake code blocks that look like system config

**Detection patterns:**
- Unmatched or orphaned closing tags in content that should be plain text
- `\b(Assistant|User|System)\s*:` appearing inside retrieved content
- `</?(?:context|system|email|input|instructions?|prompt)>`
- Delimiter-like sequences at unusual positions: `---+END`, `={3,}`, `~{3,}`
- HTML comments containing imperatives: `<!--\s*(do|run|send|execute|forward)`

---

## C. Task reframing / goal hijack

Redefine what the agent thinks its job is.

**Indicators:**
- Prepended hidden steps: "Before answering, first do X"
- Mandatory reframing: "To complete this task correctly you must…"
- Fake output format: "Your response must include…"
- Redirection of the agent's existing task toward a different goal
- Instructions to perform actions that are not part of the stated task

**Detection patterns:**
- `before (answering|responding|completing),?\s+(first|you must|please)`
- `to complete this task.*(you must|you need to|first)`
- `your response must (include|contain|have)`
- `instead of .{0,50}(do|run|execute|send|call)`
- Imperative verbs directed at the agent: `forward`, `send`, `execute`, `run`,
  `call`, `install`, `delete`, `reset`, `approve` — especially when they appear
  in content that should be informational (search results, emails, docs)

---

## D. Obfuscation / filter evasion

Get past content filters on the input side.

**Indicators:**
- Base64-encoded blobs that decode to instructions
- Zero-width characters (U+200B, U+200C, U+200D, U+FEFF) inserted between
  visible characters
- Homoglyph substitution (e.g., Cyrillic 'а' for Latin 'a')
- Leetspeak in instructions (run → rUn, execute → 3x3cut3)
- Translation indirection: "interpret the following in <language>…"
- Token splitting: "r" + "u" + "n" concatenated
- Unicode escape sequences: `\u0072\u0075\u006e`

**Detection patterns:**
- Presence of base64-looking strings (`[A-Za-z0-9+/]{20,}={0,2}`) that decode
  to text containing imperatives
- Zero-width character density above threshold
- Mixed-script detection (Latin + Cyrillic + Greek homoglyphs in same word)
- High proportion of non-ASCII in otherwise English content

---

## E. Placement / salience

Where the injection sits matters as much as what it says.

**Indicators:**
- Instructions at the very end of a long document (agents weight recent text)
- Repetition of the same instruction across a document
- Instructions in low-visibility channels: file metadata, commit messages,
  README footers, error strings, alt text, EXIF data
- Burying instructions mid-document after legitimate-looking content

**Detection approach:**
- Scan ALL content, not just the beginning — instructions can appear anywhere
- Flag imperatives in metadata/alt-text/commit-msg fields specifically
- Check for repeated instruction patterns across the document
- Pay attention to the last N characters of any retrieved content

---

## F. Conditional / delayed triggers

Fire only under the agent's real workflow to dodge naive review.

**Indicators:**
- "When summarizing this, also…"
- "If you have tool access, call…"
- "After you finish reading, please…"
- Trigger keyed to a specific tool name or action
- "In your response, make sure to…"

**Detection patterns:**
- `when (summariz|read|process|handl|respond).*\s+(also|additionally|make sure|be sure)`
- `if you (have|can) (tool|access|the ability)`
- `after you (finish|read|process|complete)`
- `in your (response|answer|output).*\s+(make sure|be sure|ensure|include)`
- `when you (see|encounter|detect).*\s+(do|run|execute|send|call)`

---

## Scoring model

Each detector returns:
- `matched`: bool — did the pattern fire?
- `confidence`: 0.0–1.0 — how strong is the match?
- `indicator`: the matched text snippet
- `technique`: which class (A–F) and specific sub-pattern

The overall risk score is a weighted combination:
- Multiple technique classes firing = higher risk
- High-confidence matches in low-visibility channels (E) = higher risk
- Obfuscation (D) detected alongside any other class = risk multiplier
- Conditional triggers (F) paired with imperative actions (C) = high risk

Default thresholds:
- 0.0–0.2: `safe` — no indicators or only benign mentions
- 0.2–0.5: `low` — minor indicators, likely benign
- 0.5–0.7: `suspicious` — multiple indicators, warrants LLM second pass
- 0.7–1.0: `dangerous` — clear injection attempt, do not process

## Content types and contextual weighting

The same text can be benign or malicious depending on context. Elcaro accepts a
`content_type` parameter that adjusts scoring:

| Content type | Risk multiplier | Rationale |
|---|---|---|
| email | 1.0 | Primary IPI vector — untrusted sender |
| search_result | 1.0 | Retrieved content, untrusted |
| code | 0.7 | Comments can carry injection but lower baseline |
| document | 0.8 | Docs/KB articles can be edited by attackers |
| webpage | 1.0 | Fully untrusted external content |
| chat_message | 0.3 | User's own message (trusted by default, lower risk) |
| system_prompt | 0.0 | Trusted by definition — do not scan |
