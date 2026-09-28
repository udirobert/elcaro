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

- [ ] Fetch seated modules for `CONTENT_MODERATION` / `TEXT_CLASSIFICATION`
      (and any mission-relevant intent) from `devnode…/api/wasm`; store under
      `eval/scorer/champions/` (gitignored — third-party binaries). Blocked
      28 Sep: devnode API timed out.
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
- [ ] Widen fixtures with answers written by other people / real miner
      outputs, so the bench isn't only our own phrasing
- **Done when:** our module beats the seated champion on margin and wins, with
  rank agreement ≥ 0.60, on our harness — then register

### W2 — Miner (Track 1): make answers legible to scorers and contracts

- [x] Prose `summary` leading with a committed verdict: "Verdict: prompt
      injection (dangerous, risk 0.93 of 1). … using <techniques>. Signals: …".
      Deliberately never quotes matched content (summary is relayed to agents).
      No YAML change, so no `updateMiner`; needs a miner redeploy to go live
- [ ] Score our own miner with the seated champion via the W1 harness; iterate
      on `summary` until it ranks well. Against our own scorer: the 26 corpus
      summaries average 0.813 (text baseline 0.434)
- [ ] Evaluate a second intent with real demand where the engine is a
      legitimate fit (e.g. URL/phishing/text-auth intents) — check the live
      intent catalog; do not declare intents we can't answer well
- [ ] Test an ERC-8183 job end-to-end: Amanat found `strings[i]` params arrive
      empty/zeroed, and our `on_chain.request` maps `content` from `strings.0`
- [ ] Any YAML change → `updateMiner` in the same window
      (`scripts/print_update_miner.sh`); note `updateMiner` deregisters the old
      record before the new one validates — have the fix ready before sending
- **Done when:** registered and auto-routable in week 1, not the last week

### W3 — Application (Track 3): Gmail extension on composed Telegraph intelligence

- [ ] Browser extension: one-click scan of the open Gmail message (then Outlook web)
- [ ] Backend routes through auto-routed `POST /engine/v1/ask`
      (`app/telegraph.py`), shows which miner answered
- [ ] Compose ≥ 3 signals from different Telegraph miners (our IPI verdict +
      URL scan + sender/domain reputation or similar, per live catalog) into
      SAFE / CAUTION / BLOCK with evidence attached
- [ ] Target the "agent reads email" user too: same checkpoint as middleware
      / MCP, routed via Telegraph
- [ ] Organic user acquisition from day one; track installs, weekly actives,
      scans — no scripted traffic
- **Done when:** published extension, real users, counted engine traffic

### W4 — Distribution and credibility

- [ ] Publish MCP server (`app/mcp_server.py`) to PyPI/npm; list in the
      official MCP registry
- [ ] Write up protocol findings as a bug report (IPFS re-serialisation hash
      mismatch, missing-`intents` routing no-op, anything W1/W2 surface)
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
- [ ] Current state of ERC-8183 job routing and param mapping on testnet
