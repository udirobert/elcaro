# Track 1 — Miner: Tasks

Track 1 opens Aug 17. Today is Aug 8. Use Aug 8–16 to complete all pre-launch tasks so the miner can go live on day one.

## Status key
- [ ] Not started
- [~] In progress
- [x] Done

---

## Phase 1 — Code fixes (complete before Aug 17)

- [x] **1.1 Fix engine singleton in `miner/api.py`**
  - `_engine = IpiDetectionEngine()` is module-level in `miner/api.py`
  - Both `/scan` and `/v1/infer` share the singleton
  - Verified: `python -m pytest tests/ -v` passes; `test_latency_is_reasonable` green

- [x] **1.2 Tighten "please [verb]" false-positive (Class C)**
  - `core/detectors/task_reframe.py` uses a negative lookahead excluding human-directed objects ("me", "us", "him", "her", "them")
  - Test added and passing: `test_clean_please_send_email` scores < 0.3
  - Existing tests still pass

- [x] **1.3 Narrow turn-spoofing false-positive (Class B)**
  - `core/detectors/delimiter.py` requires an imperative verb within a window of the `"Assistant:"` match
  - Test added and passing: `test_clean_faq_assistant_reference` scores < 0.3
  - Existing tests still pass

- [x] **1.4 Verify `deep_analysis_used` is always accurate**
  - `deep_analysis_used` is `true` only when a configured classifier actually answered; provider failures fall back to `false` with the rule score unchanged (never silently `true`)
  - Since Aug 17 there is an optional real LLM second pass (env-keyed `ELCARO_LLM_*`, off by default); without configuration behavior is identically rules-only
  - Tests: `test_deep_analysis_stub_returns_false` plus `tests/test_deep_analysis.py` (9 tests covering gray-zone triggering, fallback, rules floor)

- [x] **1.5 Run full test suite and confirm clean**
  - `python -m pytest tests/ -v` — 54 passing, no warnings
  - Includes new obfuscation coverage (`test_obfuscation.py`) and API-level coverage (`test_api.py`)

---

## Phase 2 — Deployment (complete by Aug 17)

- [x] **2.1 Choose and set up deployment platform**
  - Live at `https://api.elcaro.trustfall.xyz` — Coolify-managed Traefik (not nginx + PM2 as originally planned)
  - `deploy/ecosystem.config.cjs` (PM2), `deploy/nginx.conf`, `deploy/traefik-elcaro.yaml` all present as reference configs
  - 18/18 smoke checks passing at ~15ms (documented in `SUBMISSIONS.md`)

- [x] **2.2 ~~Create `Procfile` in repo root~~** *(obsolete — deployment uses PM2 via `deploy/ecosystem.config.cjs`, not Heroku-style Procfile)*

- [x] **2.3 Deploy to platform and verify**
  - `GET /health` → `{"status": "healthy"}` ✓
  - `GET /` → miner metadata JSON ✓
  - `POST /scan` with injection payload → risk_score > 0.7 ✓
  - All 18 smoke checks in `deploy/verify-live.sh` passing

- [x] **2.4 Set `api.base_url` in `miner/config.yaml`**
  - Set to `"https://api.elcaro.trustfall.xyz"`

---

## Phase 3 — Telegraph registration (complete by Aug 17)

- [x] **3.1 Pin `miner/config.yaml` to IPFS via Pinata**
  - IPFS abandoned after console wizard caused YAML hash mismatch
  - Config self-hosted at `GET /telegraph.yaml` on the miner — plain HTTPS is a supported option
  - `yaml_hash: "0x213b88c646efd4d39bddaa16b3adb93402dff3ba9cd8215affa73c8f1e5adb8e"` set in config

- [x] **3.2 Register on Base Sepolia**
  - Registered as miner ID 145 on `2026-08-20`
  - Tx: `0x79a908a6ac0b45dad82048e25cb148dc3daf8a841510fbef31b4ad5c006f9d3f`
  - `registration.registry_contract: "0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8"`
  - Full paper trail in `SUBMISSIONS.md`

- [x] **3.3 Verify miner appears in Telegraph network**
  - `activation_status: active`
  - Verifiable: `curl -s https://devnode.telegraphprotocol.com/api/miners/145`

---

## Phase 4 — Detection quality (ongoing, Aug 17 – Sep 7)

- [ ] **4.1 Implement translation indirection detector (Class D)**
  - Pattern: `"interpret the following in <language>"`, `"translate this to <language> and execute"`
  - Add to `core/detectors/obfuscation.py`
  - Confidence: 0.65 (context-dependent)
  - Add positive test + negative test (legitimate translation requests)

- [ ] **4.2 Implement token splitting detector (Class D)**
  - Pattern: characters separated by spaces/symbols that concatenate to an imperative keyword
  - e.g. `"r u n"`, `"s-e-n-d"`, `"e.x.e.c.u.t.e"`
  - Add to `core/detectors/obfuscation.py`
  - Confidence: 0.7 (splitting is almost never legitimate in instructional content)

- [ ] **4.3 Expand eval corpus coverage for new patterns**
  - Add `D001`–`D003` (base64, zero-width, homoglyph) plus `D004` (translation indirection) and `D005` (token splitting) to `eval/src/lib.rs`
  - Note: currently zero D-class cases in the corpus — obfuscation is entirely unrepresented
  - Add at least 2 more clean/negative cases (target: ≥ 8 total negative cases)

- [ ] **4.4 Monitor false-positive rate on real traffic**
  - Once live, log all scans with score ≥ 0.3 that are flagged by only one technique
  - Review weekly; tune confidence values if benign content is regularly scoring 0.3–0.5

---

## Phase 5 — Visibility (ongoing, Aug 17 – Sep 7)

- [x] **5.1 Post Track 1 announcement on X**
  - What Elcaro does, why IPI matters for agents, link to miner
  - Include a real detection example (screenshot of the API response)

- [x] **5.2 Post "miner live" update on X**
  - Show the `/scan` endpoint working against a real injection payload
  - Include risk score, flagged techniques, indicator explanation

- [ ] **5.3 Weekly progress posts**
  - Leaderboard position, request count, detection examples
  - Tag Telegraph Protocol account

---

## Completion criteria

Track 1 is submission-ready when:
- [x] Miner is live at a stable HTTPS URL (`https://api.elcaro.trustfall.xyz`)
- [x] GET /health returns 200
- [x] POST /scan returns correct risk scores for known injection payloads
- [x] Miner is registered on Base Sepolia and visible in Telegraph network (ID 145)
- [x] config.yaml has all fields filled (base_url, yaml_hash, registry_contract)
- [x] Full test suite passes: `python -m pytest tests/ -v` (54 passing)
- [x] At least one X post published with engagement
