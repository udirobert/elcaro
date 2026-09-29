# Telegraph Season II — Retro and Plan

Season I (H1) closed 7 Sep 2026. Elcaro placed in no track. Season II runs
~30 days with a $10,000 pool across the same three tracks (Miner, Evaluator,
Application/Agent). Final rules, prize split and the 15 commercial missions
are not yet published — see [Open questions](#open-questions-resolve-when-rules-drop).

## Season I result

| Track | Winners (score) | What they had in common |
|---|---|---|
| 1 Miner | TXlens (97.9), Chainsight Oracle (86.9), Oathcast Weather (85.4) | Existing, demanded intents with objectively checkable answers (tx status, prices, weather) |
| 2 Evaluator | @zkasuran, @hyadav42774, @BangDropID | Scoring modules that seated on live intents |
| 3 App | Scam Shield (0.69), Truvian Shield (0.59), ProofPact (0.45) | Real user surfaces; multiple Telegraph miners composed into one decision; Telegraph inside a workflow |

Reference repo reviewed: [PugarHuda/amanat](https://github.com/PugarHuda/amanat)
(all three tracks from one codebase; not confirmed to be one of the named winners).

## Why we didn't place

1. **Track 2 was likely never scored.** Telegraph scoring modules export
   `rank_answer(q, gt, answer) -> f32` (plus `alloc`/`dealloc`) and register
   against an intent, where they must beat the seated champion on margin *and*
   rank agreement (~0.60). Our `eval/` exports `evaluate_ptr` /
   `get_test_cases_ptr` / `test_case_count` — a benchmark harness bound to our
   own `/scan` schema. No scoring-module registration exists in
   [SUBMISSIONS.md](../SUBMISSIONS.md).
2. **Track 1 had no scorer shaped for us.** Most seated modules compare text;
   Amanat measured 31 of 40 intents with no miner above 0.05 because answers
   were numeric. Our `summary` is a one-liner; the rest is JSON the scorer
   likely ignores. Being the only `CONTENT_MODERATION` miner meant no ranking
   competition and little routed demand.
3. **Late routing.** Registered 20 Aug, but `/scan` had no endpoint `intents`
   so auto-routed traffic couldn't land until registration 406 on 1 Sep.
4. **Track 3 didn't count.** The web app and middleware call `POST /scan`
   directly — our own log says that doesn't satisfy "must use Telegraph miners".
   Scam Shield won with our own stated wedge (email scanning) shipped as a
   Gmail extension + SMS app.
5. **Scope spread.** Red-team, SERV, Jev, AgentMail, Tenki, Wasmer and WebMCP
   were built for other events and are not what Telegraph judges.

## Principles for Season II

- **Build for the scorer that exists.** Read the seated module for each target
  intent before shaping miner output; benchmark our module against champions
  before paying to register.
- **Only counted traffic counts.** Auto-routed `POST /engine/v1/ask`, organic
  users only. Scripted/scheduled calls are explicitly not counted (Telegraph
  co-founder, Discord, 6 Sep) and loaded the facilitator.
- **Compose, don't monopolise.** The winning app pattern buys several kinds of
  intelligence from different miners and combines them (Truvian: SAFE / CAUTION / BLOCK).
- **Measure, then claim.** Every number in README / posts reproducible by a
  script in the repo, including results where we lose.
- **One domain through all three tracks:** untrusted-message safety
  (email/SMS/web content), aligned to whichever of the 15 missions fits.

## Workstreams

### W1 — Evaluator (Track 2): rewrite `eval/` as a real scoring module

- [x] Fetch seated modules for `CONTENT_MODERATION` / `TEXT_CLASSIFICATION`
      (and any mission-relevant intent) from `devnode…/api/wasm`; store under
      `eval/scorer/champions/` (gitignored — third-party binaries).
      **29 Sep: done.** Devnode responded (2417 intents; the 28 Sep timeout was
      transient). Seated champions are all zkasuran salience scorers:
      `cmod_r5` (CONTENT_MODERATION, eval 0.80), `tc_pen0`
      (TEXT_CLASSIFICATION, eval 1.0), and `url_c3` (URL_SCAN, eval 0.948 —
      candidate for W2's second intent). On our 29-case bench ours beats all
      three on margin and wins (0.6287/29 vs 0.4828/26, 0.4373/15, 0.6278/27)
      and rank agreement clears the 0.60 gate against each (0.79 / 0.74 / 0.94).
      Caveat: the downloaded bytes do not reproduce the on-chain `wasm_hash`
      under sha256 or sha3-256 — consistent with the known IPFS
      re-serialisation mismatch, so champions are verified by loading and
      running them, not by hash.
- [x] Scoring module at `eval/scorer/` (own crate): `no_std`, zero imports,
      exports `alloc`, `dealloc`, `rank_answer`, `breakdown_answer`; ~11 KB;
      deterministic float ops only
- [x] Grade verdicts, not vocabulary: committed verdict (with negation and
      yes/no-by-question-polarity), category labels, risk figure, then text
- [x] Anti-gaming rules, each with a test: question clauses cast no verdict
      and copied answers ×0.1; hedges/keyword dumps cap at 0.30; wrong verdict
      caps at 0.15; labels graded on precision; restated figures earn 0
- [x] Node harness (`eval/scorer/harness.mjs`): bench, `--attacks`,
      `--agreement` (ladder proxy for the ~0.60 gate), `--diff`, `--case`;
      runs in CI
- [x] Bench from the IPI corpus (`make_bench.py` → 29 cases, rotating
      prose / terse / JSON / paraphrase styles) + 10 attack fixtures.
      28 Sep: margin 0.6287, 29/29 wins, 10/10 attacks held; token-F1 text
      baseline 0.1301, 22/29, 4/10
- [x] Widen fixtures with answers written by other people / real miner
      outputs, so the bench isn't only our own phrasing. **29 Sep:
      `bench_wide.json` (79 cases) via `make_bench_wide.py` — 26 real miner
      outputs fetched live from prod and cached in `miner_outputs.json`, plus
      24 independent-voice verdict pairs written by the configured LLM
      (llama-3.3-70b) without seeing our ground truth.** Ours wins **75/75**
      at margin 0.577 (text baseline 0.156, 63/75); the champions collapse on
      realistic answers — cmod_r5 0.280/64, tc_pen0 0.263/29, url_c3 0.408/61
      — while rank agreement still clears the gate (0.79 / 0.74 / 0.91).
      Generation-side filter rejects uncommitted LLM verdict pairs (hedges,
      double negations) — 6 of 26 failed, echoing the Laya calibration
      finding. Champion calls are ~0.5 s each on this set, so `bench_wide.mjs`
      caches scores in `champions/score-cache.json` (first run ~15 min, then
      ~0.1 s).
- **Done when:** our module beats the seated champion on margin and wins, with
  rank agreement ≥ 0.60, on our harness — then register

### W2 — Miner (Track 1): make answers legible to scorers and contracts

- [x] Prose `summary` leading with a committed verdict: "Verdict: prompt
      injection (dangerous, risk 0.93 of 1). … using <techniques>. Signals: …".
      Deliberately never quotes matched content (summary is relayed to agents).
      No YAML change, so no `updateMiner`. **Live since the 28 Sep redeploy**
      — verdict-first summaries confirmed in production via the web UI.
- [ ] Score our own miner with the seated champion via the W1 harness; iterate
      on `summary` until it ranks well. Against our own scorer: the 26 corpus
      summaries average 0.813 (text baseline 0.434)
- [ ] Evaluate a second intent with real demand where the engine is a
      legitimate fit (e.g. URL/phishing/text-auth intents) — check the live
      intent catalog; do not declare intents we can't answer well
- [ ] Test an ERC-8183 job end-to-end: Amanat found `strings[i]` params arrive
      empty/zeroed, and our `on_chain.request` maps `content` from `strings.0`.
      **29 Sep: harness ready — `scripts/erc8183_job_test.sh` (preflight / fund /
      create / watch / cancel), blocked only on a funded signer.** Facts
      established: registration 406 is active and its registration-pinned
      intentId is `0x8b47bf24…5981` (field 5 of `getMiner(406)`); jobBasePrice
      is 1 USDC + demand multiplier, paid from Diamond escrow (0 today); the
      registering wallet `0x1e17…5D40` is an EOA holding nothing and its key is
      not scripted anywhere, so a funded test key is needed. Diagnostic: empty
      `content` is valid per our schema and returns a normal `safe, 0.00`
      verdict — so if the node delivers empty strings, the job still settles
      Terminal with a safe verdict, which IS the smoking gun. A healthy run
      shows 0.664/suspicious for the default fixture. Note: CONTENT_MODERATION
      now has competition (TxLens 9002, ChainSight 302) — the broadcast
      (intent-name-hash) mode may route to them, so prefer the pinned intentId
      for this test.
- [ ] Any YAML change → `updateMiner` in the same window
      (`scripts/print_update_miner.sh`); note `updateMiner` deregisters the old
      record before the new one validates — have the fix ready before sending
- **Done when:** registered and auto-routable in week 1, not the last week

### W3 — Application (Track 3): Gmail extension on composed Telegraph intelligence

- [x] Browser extension: one-click scan of the open Gmail message (then
      Outlook web). **29 Sep: at `app/extension/gmail-scan/` — MV3, no build
      step, loads unpacked; tested in jsdom from `app/extension/tests/`.**
      Floating Scan button in the thread toolbar → overlay with band / risk
      score / summary / techniques; re-injection guard; rail preference
      persisted. UX pass landed 29 Sep: the overlay opens instantly with a
      progress state (no silent spinner), each band carries a one-line *next
      action* ("Don't act on this message…"), the risk score has a
      proportional meter, techniques are chips, SAFE auto-dismisses after 8s,
      Escape/click-outside dismiss, and the toolbar badge carries the verdict
      when the overlay is off-screen. Re-scans are cached 5 min in the SW
      (one $0.01 ask, not two). Failures render a human headline + explanation
      with the infra code behind a **Details** disclosure and a **Scan again**
      retry — a test asserts no env var name or protocol jargon reaches the
      overlay. The popup's status card polls the bridge so a user learns the
      service is down *before* clicking. Also fixed: the manifest never
      granted `elcaro.trustfall.xyz`, so the engine rail's fetch would have
      been denied outright. Extraction heuristics (`.ii.gt` / `.a3s`) still
      need hardening against Gmail DOM churn — test with plain, quoted and
      HTML-heavy mail. Outlook: not started.
- [ ] Backend routes through auto-routed `POST /engine/v1/ask`
      (`app/telegraph.py`), shows which miner answered. **29 Sep: payment path
      built — `app/web/src/app/api/engine-ask/route.ts` forwards to the engine
      rail and answers the x402 challenge server-side** (exact scheme,
      EIP-3009 TransferWithAuthorization over Base Sepolia USDC, header
      `PAYMENT-SIGNATURE`, x402Version 2, accepts[] echoed — shape from
      telegraph-examples `src/lib/x402.ts`, validated against the live devnode:
      well-formed-but-unfunded returns upstream "payment required" while
      malformed headers get "Invalid payment"). The extension's engine rail
      now goes through the bridge; it needs no wallet. **29 Sep hardening pass:**
      extension origins are pinned to `TELEGRAPH_BRIDGE_EXTENSION_IDS` instead
      of "any `chrome-extension://`" (the GET status reports
      `extensionPinned:false` when unset, and `ALLOW_ANY_EXTENSION=0` /
      `ALLOW_NO_ORIGIN=1` are the kill switches); gate order is origin → token
      → cap so a stranger can't burn the budget; `GET /api/engine-ask` returns
      operator status (payer configured? cap left? pinned?) with no secrets;
      every failure path returns a stable `code` the UI renders copy from; a
      second 402 after signing is translated to `PAYMENT_REJECTED` (unfunded
      wallet) instead of shipping the challenge to the overlay; 30s upstream
      + 20s client timeouts. Gated by origin allowlist + optional
      `TELEGRAPH_BRIDGE_TOKEN` + per-instance daily cap
      `TELEGRAPH_BRIDGE_DAILY_CAP` (default 40). **Remaining: fund a testnet
      payer wallet and set `TELEGRAPH_X402_KEY` (and
      `TELEGRAPH_BRIDGE_EXTENSION_IDS` once published) in Netlify** — the rail
      is inert until then (502 PAYER_NOT_CONFIGURED). The 402 challenge also
      offers an `escrow` scheme (depositUSDC once, EIP-191 personal_sign per
      ask) — probed and mapped, not yet fully cracked: the node's recovered
      signer never matches any reconstruction of the template message, so
      the bridge uses `exact` where the reference client pins the contract.
      Also surfaced: direct `/engine/v1/ask/8848` (NOT counted) uses a
      different body — `{method, endpoint, payload}`.
- [ ] Compose ≥ 3 signals from different Telegraph miners (our IPI verdict +
      URL scan + sender/domain reputation or similar, per live catalog) into
      SAFE / CAUTION / BLOCK with evidence attached
- [ ] Target the "agent reads email" user too: same checkpoint as middleware
      / MCP, routed via Telegraph
- [ ] Organic user acquisition from day one; track installs, weekly actives,
      scans — no scripted traffic
- [x] Multi-model comparison rails on gray-zone scans: alongside Jev
      (TypeSafe), added Laya (Convai via Runware, `core/laya_reasoner.py`) —
      a Noul "is this injection?" probability shown beside the rule verdict,
      comparison-only, never moves the score. Cheaper/lower-latency than Jev,
      Apache-2.0 (self-hostable). Groundwork for the Truvian-style "compose
      several decision sources" checkpoint
- [x] Calibrate Laya on `eval/corpus.json` before surfacing it —
      `scripts/laya_calibration.py`. **Result (28 Sep, live Runware, 26/26
      calls OK, ~375ms):** Laya is a *weak* injection signal off the shelf —
      Brier 0.32 (worse than a 0.25 coin flip), TPR 0.11 / TNR 1.0 at 0.5. It
      is not calibrated for this task, exactly as the launch note warned. Only
      notable hits are D004/D005 (translation indirection, token-splitting) —
      the obfuscation cases our rule engine misses. **Decision: keep Laya a
      comparison rail only; do not let it near the verdict.** Re-run before
      any promotion.
- [x] Wire Laya into the web `/scan` UI (types, form toggle, result panel,
      session pill, `MinerConfig.laya_available`, `/api/scan` laya query
      override) and deploy the miner config (`LAYA_ENABLED=1` + Runware key in
      the pm2 process env). **Verified end-to-end 28 Sep:**
      `/config` → `laya_available: true` on api.elcaro.trustfall.xyz; a
      gray-zone scan with `laya_enabled: true` returned `laya_used: true`
      with a live comparison (rules 0.664 vs Laya 0.36, $0.0000035); card
      renders with the disagreement badge. Calibration re-run same day:
      Brier 0.3206 — consistent with the first run.
- **Done when:** published extension, real users, counted engine traffic

### W4 — Distribution and credibility

- [ ] Publish MCP server (`app/mcp_server.py`) to PyPI/npm; list in the
      official MCP registry
- [ ] Write up protocol findings as a bug report (IPFS re-serialisation hash
      mismatch — 29 Sep: champions' on-chain `wasm_hash` ≠ the bytes served by
      their `wasm_url`, three modules confirmed under sha256 and sha3-256;
      missing-`intents` routing no-op, anything W1/W2 surface)
- [ ] X cadence: kickoff, scorer benchmark table, miner live, app launch,
      weekly usage numbers

## Timeline (30 days, relative to Season II start)

| Days | Focus |
|---|---|
| Pre-start | Resolve open questions; W1 harness + champion download; W2 on-chain job test |
| 1–7 | W2 `summary` + `updateMiner`; W1 scorer core + anti-gaming tests; W3 extension skeleton |
| 8–14 | W1 register once it beats champion; W3 composed checkpoint live, first users |
| 15–24 | W3 user growth; W2 second intent if justified; W4 MCP publish + bug report |
| 25–30 | Freeze; reproducible numbers in README; submission forms; final posts |

## Open questions (resolve when rules drop)

- [ ] Prize split, judging criteria, qualification rules per track
- [ ] The 15 commercial missions — which one is untrusted-message safety under?
- [ ] Which scoring module (if any) is seated on `CONTENT_MODERATION` /
      `TEXT_CLASSIFICATION` now, and its current bar
- [ ] Whether Season I registrations (miner 8848 / reg 406) carry over
- [ ] How app usage is measured (engine traffic only? installs? on-chain jobs?)
- [ ] Current state of ERC-8183 job routing and param mapping on testnet.
      29 Sep: docs read (erc8183-jobs, onchain-miner-requests). Two separate
      rails — jobs target an intent (~1 USDC from escrow, callback optional,
      failed jobs sit in Funded forever → `cancelJob` refunds); miner requests
      target a miner+endpoint (gas only, callback mandatory, one outstanding
      protocol-wide). The old `strings[i]` bug may be a listener/params issue
      on the job rail; our miner-side mapping (`strings.0` → content) is
      declared in `miner/telegraph.yaml`. Live test pending funded signer
      (`scripts/erc8183_job_test.sh`).
