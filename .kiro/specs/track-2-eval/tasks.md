# Track 2 — Eval Script: Tasks

Track 2 opens Aug 17 alongside Track 1. The WASM eval script should be submitted as early as possible — earlier submission means more validator runs, which means more data on whether the ABI is correct.

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — ABI verification (MUST complete before any other work)

This is the highest-risk item. Get it wrong and the script silently scores zero.

- [ ] **1.1 Find the Telegraph WASM eval ABI specification**
  - Check: hackathon.telegraphprotocol.com docs
  - Check: Telegraph Protocol GitHub repos for example eval scripts
  - Check: Telegraph Discord (early access channel) — ask directly what ABI the validator expects
  - Document the answer here: `<!-- ABI: ___ -->`

- [ ] **1.2 Update `evaluate` function signature to match the verified ABI**
  - If pointer+length: rewrite using `unsafe { std::slice::from_raw_parts(ptr, len) }`
  - If wasm-bindgen: add `wasm-bindgen` dependency to `Cargo.toml`, annotate with `#[wasm_bindgen]`
  - If `&str` is confirmed correct: document that explicitly and move on
  - Update `get_test_cases()` and `test_case_count()` if they also need ABI changes

- [ ] **1.3 Verify `wasm32-unknown-unknown` target is installed**
  ```bash
  rustup target add wasm32-unknown-unknown
  ```

- [ ] **1.4 Test the build compiles cleanly**
  ```bash
  cd eval
  cargo build --target wasm32-unknown-unknown --release
  ```
  - Fix any compile errors (common: std types not available in wasm32, networking, file I/O)
  - Confirm binary exists at `eval/target/wasm32-unknown-unknown/release/elcaro_eval.wasm`

---

## Phase 2 — Corpus expansion (complete by Aug 20)

- [ ] **2.1 Add Class D (obfuscation) cases — currently zero in corpus**
  - Add `D001`: base64-encoded instruction decoding to an imperative
  - Add `D002`: zero-width character insertion hiding an instruction
  - Add `D003`: leetspeak imperative (e.g. `s3nd th3 r3p0rt`)
  - See design.md for exact content strings

- [ ] **2.2 Add second placement case (Class E)**
  - Add `E002`: HTML comment with imperative at start of webpage
  - See design.md for content

- [ ] **2.3 Add clean/negative cases to raise false-positive bar**
  - Add `N006`: benign email with "please send" and "forward" — human-directed, not injection
  - Add `N007`: search result quoting `"Assistant:"` in a FAQ — no imperative follows
  - Add `N008`: system maintenance notice — mentions "system" legitimately
  - Target: ≥ 8 total negative cases

- [ ] **2.4 Run native tests after corpus expansion**
  ```bash
  cd eval && cargo test
  ```
  - `test_corpus_has_positives_and_negatives` must pass
  - `test_perfect_responses_score_high` must pass (overall_score ≥ 0.8)
  - `test_all_wrong_scores_low` must pass (overall_score < 0.3)
  - `test_get_test_cases_returns_valid_json` must pass

---

## Phase 3 — Integration test (complete by Aug 22)

- [ ] **3.1 Run the eval script against the live Elcaro miner**
  - Write a small test harness (Python or Rust) that:
    1. Calls `get_test_cases()` to retrieve the corpus
    2. Sends each case to `POST /scan` on the running miner
    3. Collects the responses in order
    4. Calls `evaluate(responses_json)` and prints the `EvalResult`
  - Expected result: Elcaro should score ≥ 0.8 against its own eval script
  - If score is lower, identify which cases fail and fix either the miner or the corpus

- [ ] **3.2 Test against a deliberately bad "miner" (all-dangerous responses)**
  - Confirm `overall_score` < 0.5 — verifies gaming resistance
  - A miner that returns `risk_score: 0.9` for every request must not win

- [ ] **3.3 Test against a deliberately bad "miner" (all-safe responses)**
  - Confirm `overall_score` < 0.5 — verifies detection is required, not just low FPR

---

## Phase 4 — Submission (complete by Aug 24 at latest)

- [ ] **4.1 Final build in release mode**
  ```bash
  cd eval
  cargo build --target wasm32-unknown-unknown --release
  ```

- [ ] **4.2 Pin WASM binary to IPFS via Pinata**
  - Upload `eval/target/wasm32-unknown-unknown/release/elcaro_eval.wasm`
  - Copy the IPFS CID

- [ ] **4.3 Submit eval script to Telegraph**
  - Follow Track 2 submission process at hackathon.telegraphprotocol.com
  - Use the IPFS CID from step 4.2
  - Record submission confirmation

- [ ] **4.4 Verify the script appears in the Telegraph validator network**
  - Confirm it shows as active/pending evaluation
  - Watch for any error feedback from the validator (ABI issues will show up here)

---

## Phase 5 — Visibility

- [ ] **5.1 Post Track 2 announcement on X**
  - Explain the adversarial test corpus concept
  - Show an example: "Here's what a gaming-resistant eval looks like" — demonstrate D-class obfuscation case
  - Explain why technique-level accuracy scoring prevents carpet-bombing

---

## Completion criteria

Track 2 is submission-ready when:
- [ ] `cargo test` passes (native)
- [ ] `cargo build --target wasm32-unknown-unknown --release` succeeds
- [ ] WASM ABI is verified against Telegraph runtime
- [ ] Corpus has ≥ 3 cases per technique class represented, ≥ 8 clean/negative cases
- [ ] Class D (obfuscation) cases are present
- [ ] Elcaro miner scores ≥ 0.8 against the script (self-consistency test)
- [ ] An all-dangerous miner scores < 0.5 (gaming resistance test)
- [ ] Script is submitted to Telegraph and visible in the validator network
