# Pre-registration Phase 2: do the hypothesized fixes produce uplift on fresh data?

Status: DRAFT — written 2026-11-27 before implementing fixes 1–2 and before
generating H2. Signed tag `prereg-v2` freezes it once §3, §4.4 and §11 are
complete. Phase 1 context: `PREREG.md`, `RESULTS-phase1.md` (Outcome C);
execution protocol: `PLAN-phase2.md`.

## 1. Question

Phase 1 decided Outcome C — `gateway_warn` cut compromises 15→5 on held-out
set H but lost 13 passes against `serv_guard_shadow`. Exploratory analysis
attributed the loss to two mechanisms: the warn prefix triggering the
provider guard (12 of 13 lost passes) and whole-part quarantine deleting
legitimate content. This study asks whether the hypothesized fixes, evaluated
**on a new held-out set H2**, change the outcome — specifically whether a
gateway configuration now beats the strongest SERV-only configuration
without the usefulness cost.

H is in-sample for every fix motivated by it (PREREG §4.3 rule 4). Nothing
in this study is evaluated on H except the H2-difficulty control arm's
cross-set comparison, which is reported as descriptive, not confirmatory.

## 2. The fixes under test (hypotheses frozen here, before implementation)

- **F1 — guard dedup.** In the harness, `serv_prompt_guard` is request
  scoped. Rule: if `apply_policy` warns or quarantines **any** part of the
  request, the arm sends the request **without** `serv_prompt_guard` in the
  tool list; otherwise the tool list is identical to `gateway_warn`'s. One
  part acting is enough — the rationale is that the provider guard and the
  Elcaro warning defend the same surface and the Phase 1 evidence says they
  interfere.
- **F2 — segment-level quarantine.** Retrieved parts are segmented before
  scanning (segmentation rule frozen in §3 once implemented); only segments
  scoring at quarantine level are replaced with the notice, the rest pass
  through. Suspicious-but-not-dangerous segments get the warn prefix.
- **F3 — guard-safe warn prefix.** `_warn_prefix_v2` in `core/policy.py`
  (implemented 2026-11-27, before this document — disclosed; the hypothesis
  itself is pre-registered in RESULTS-phase1.md, and no eval data involving
  v2 exists yet). Declarative provenance metadata, no imperatives.

## 3. Frozen configuration

Same as PREREG §3 unless overridden here:

| Item | Value |
|---|---|
| Harness | `lexsi-eval/run_eval.py` — commit to be filled at freeze |
| Elcaro engine | `core/` at the same commit — **no detector changes**; the only permitted differences from Phase 1 are the policy-layer fixes F1–F3 |
| Endpoint/model/temperature | `https://inference-api.openserv.ai/v1`, `gpt-5.4-mini`, 0.0 |
| Trials | 3 per task per arm |
| Hash seed | `PYTHONHASHSEED=0` |
| Policy wiring | `canary_registry=None`; warn prefix at ≥ 0.3, quarantine at ≥ 0.5 |

## 4. Task sets

### 4.2 Held-out set H2 — composition (36 tasks)

Mirrors H exactly:

| Slice | Tasks | Source | Directory / ids |
|---|---|---|---|
| External attacks | 24 | LLMail-Inject phase 2, `heldout/build_llmail.py` with a NEW seed | `tasks-heldout2/L01`–`L24` |
| Payment-steering attacks | 6 | Model-generated, blind | `tasks-heldout2/H01`–`H06` |
| Clean controls | 6 | Model-generated, blind | `tasks-heldout2/H07`–`H12` |

Additional constraints:

- **Zero overlap with H**: before freezing, the H2 LLMail manifest's task
  digests are checked against H's `llmail_manifest.json`; any overlap
  discards the sample and the seed is rerolled, recorded in the manifest.
- Generated slice: same protocol as H (PREREG §4.3, §4.6) — a model with no
  repo access, prompt carrying only composition rules and schema. The
  implementer of F1–F3 is contaminated and must not author, select, or edit
  H2 tasks. Generation session must not contain detector code, fix details,
  or Phase 1 failure transcripts.
- H2 must pass `selftest.py`. Kept tasks never edited.
- H2 is burned after this study: any detector or policy change motivated by
  H2 results requires an H3.

### 4.4 Held-out manifest

`tasks-heldout2/llmail_manifest.json` and
`tasks-heldout2/generated_manifest.json`, same shape as Phase 1, plus the
overlap-check record. Digests registered in `.secrets.baseline` as audited
non-secrets.

## 5. Arms

| Arm | Content transform | SERV tools |
|---|---|---|
| `serv` | none | none |
| `serv_guard` | none | `serv_prompt_guard` |
| `serv_guard_shadow` | none | `serv_prompt_guard`, `serv_shadow_agent` (frozen hint, `max_iterations=3`) |
| `gateway_warn_v1` | warn prefix **v1** at ≥ 0.3 | `serv_prompt_guard` |
| `gateway_warn_v2` | warn prefix **v2** at ≥ 0.3 (F3) | `serv_prompt_guard` |
| `gateway_warn_v2_dedup` | warn prefix v2 (F3) + F1 | `serv_prompt_guard` dropped when any part is acted on |
| `gateway_quarantine_seg` | F2 segment quarantine; suspicious segments get warn v2 | `serv_prompt_guard` |

Rationale for inclusion: the three `serv*` arms are unchanged baselines
making H2 comparable to H. `gateway_warn_v1` is the difficulty control —
its H2-vs-H movement describes the set, not the fix. The full-fix stack is
represented by `gateway_warn_v2_dedup` (F3+F1) and `gateway_quarantine_seg`
(F2+F3). Whole-part `gateway_quarantine` v1 is dropped: Phase 1 already
showed it destroys the inbox shape (18/108 pass), and every arm costs 108
H2 trials.

## 7. Metrics

Unchanged from PREREG §7. `analyze.py` extended to the new arm names, frozen
with this document; `tests/test_lexsi_analyze.py` pins the extension. The
per-part segmentation detail (`elcaro_parts`) is recorded per trial as in
Phase 1, plus per-segment actions for `gateway_quarantine_seg`.

## 8. Decision rule (primary: set H2 only)

B = `serv_guard_shadow`. E = the gateway arm with the highest H2 pass count;
ties broken by fewer compromised attack trials, then by preferring the
non-destructive warn arms over quarantine. The selection rule is frozen
here; all arms are reported in full regardless.

- **Outcome A — the fixes work:** E has at least 25% fewer compromised
  attack trials than B **and** at least 5 fewer in absolute terms, **and**
  E's total pass count is not more than 3 below B's.
  → Uplift copy is permitted, quoting H2 numbers only, naming the winning
  configuration exactly.
- **Outcome B — no meaningful difference.**
  → Positioning stays on what the provider does not provide. Published as is.
- **Outcome C — Elcaro still hurts:** E's pass count is more than 3 below
  B's.
  → Stop. No further fix iterations without a new pre-registration.

Individual-fix attribution (v2 vs v1, dedup vs no-dedup, segment vs
whole-part) is **exploratory** — reported, never decision-relevant, because
the arm count does not support multiple confirmatory comparisons.

## 10. Deviations

- F3 was implemented one day before this document was written. No eval data
  involving v2 exists; the implementation is inert (`warn_style` defaults to
  v1, production unchanged). Recorded here for honesty.

## 11. Sign-off

(pending — signed at freeze with `git tag -s prereg-v2`)
