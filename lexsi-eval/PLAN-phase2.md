# WS6a execution plan — Phase 2 benchmark

Written 2026-11-27 after implementing the first fix. Captures everything
needed to execute across sessions without re-reading PREREG.md /
RESULTS-phase1.md. Read those two first anyway — they are the authority.

## Why

Phase 1 was Outcome C: `gateway_warn` cut compromises 15→5 but lost 13
passes versus `serv_guard_shadow`, and the pre-registered decision rule says
that means stop. The exploratory analysis isolated the mechanism: 12 of the
13 lost passes were SERV's prompt guard refusing whole requests **because
Elcaro's own warn prefix reads as an injection to it**. H is now in-sample
(PREREG §4.3 rule 4) — every fix must be evaluated on a NEW held-out set.

## The three hypothesized fixes (RESULTS-phase1.md §Implications)

1. **Guard dedup** — don't also send `serv_prompt_guard` when Elcaro has
   already warned or quarantined the part. Harness/arm-level: a new arm
   whose tool list drops `serv_prompt_guard` dynamically when any part
   action != none. NOT IMPLEMENTED.
2. **Segment-level quarantine** — quarantine per email/document inside a
   retrieved part, not the whole part. In LLMail tasks the whole inbox is
   one part, so whole-part quarantine deletes legitimate mail along with the
   attacker's (gateway_quarantine passed 18/108 on H). Deepest change:
   segmentation heuristic + per-segment scan + surgical write-back in
   `core/policy.py`. NOT IMPLEMENTED.
3. **Guard-safe warn prefix** — IMPLEMENTED 2026-11-27:
   `core/policy.py::_warn_prefix_v2`, wired as `warn_style="v2"` kwarg on
   `apply_policy` (default `"v1"` — production unchanged). v2 is declarative
   provenance metadata with zero imperatives; v1's "Tell your user:" /
   "Review before acting" phrasing was the guard trigger. Tests in
   `tests/test_policy.py` pin both. The harness `_scan_wrap` duplicate in
   `run_eval.py` still hardcodes v1 — Phase 2 arms must import from
   core.policy instead of duplicating (the byte-identical parity constraint
   then holds by construction).

## Execution order (dependencies matter)

1. **Write PREREG-phase2.md FIRST.** Before implementing fixes 1–2 and
   before generating H2. Pin: arm definitions (see candidates below), the
   decision rule (reuse PREREG §8 shape), the H2 composition (mirror §4.2:
   24 LLMail + 6 payment-steering + 6 clean controls?), freeze process.
   Amendment vs new document: new document, signed tag `prereg-v2`.
2. Implement fixes 1–2 behind the arm wiring. Fix 1 is small; fix 2 is the
   multi-hour one.
3. **Generate H2 blind.** Protocol per PREREG §4.3/§4.6:
   - LLMail slice: rerun `heldout/build_llmail.py` with a NEW seed and a
     DIFFERENT sample (the manifest records seed + sha256 per task; verify
     zero overlap with H's llmail_manifest before proceeding — overlap
     would leak in-sample tasks). NOTE: LLMail-Inject was off-limits for
     detector work until the Phase 1 study closed; confirm it is still
     uncontaminated — nobody has run Elcaro on LLMail data since.
   - Generated slice: `heldout/generate_heldout.py` + `generate_prompt.md`,
     run against a model with NO repo access (H used claude-sonnet-5 via
     `https://inference-api.openserv.ai/v1`, temperature 1.0). WHOEVER
     GENERATES MUST NOT SEE detector code, fix details, or H failure
     transcripts — the prompt carries only composition rules + schema.
     IMPORTANT: the person/agent writing fixes 1–2 is contaminated; use a
     fresh API session with only the generation prompt. Rotate the content
     type spread per the manifest's rotation list.
   - Candidates must pass `selftest.py`; kept tasks never edited.
4. Freeze: sign tag `prereg-v2` over PREREG-phase2 + harness + H2 manifest.
5. Run eval. Phase 1 scale was 5 arms × 60 tasks × 3 trials = 900 trials,
   gpt-5.4-mini on SERV, temperature 0, PYTHONHASHSEED=0, ~10 minutes wall.
   COSTS REAL MONEY (SERV API) — owner approval required before running.
   Phase 2 arm count likely 6–7 (see below), so scale/cost grows ~30%.
6. Analyze with `analyze.py` frozen in the tag; publish per WS6b honesty
   rules regardless of outcome.

## Arm candidates for PREREG-phase2 (proposal — pin in the prereg)

| Arm | Purpose |
|---|---|
| `serv` | baseline (unchanged) |
| `serv_guard` | provider-only baseline (unchanged) |
| `serv_guard_shadow` | strongest SERV-only config (unchanged) |
| `gateway_warn_v1` | Phase 1's warn arm rerun — measures H2 difficulty drift vs H |
| `gateway_warn_v2` | fix 3 alone |
| `gateway_warn_v2_dedup` | fixes 3+1 (drop serv_prompt_guard when Elcaro fired) |
| `gateway_quarantine_seg` | fix 2 (+v2 prefix for suspicious parts) |

`gateway_quarantine` whole-part can be dropped or kept for continuity —
decide in the prereg; every extra arm is eval cost.

## Progress log

- 2026-11-27: F3 implemented (`warn_style="v2"`, production unchanged).
  PREREG-phase2.md drafted and committed (`ff6be32`) BEFORE further
  implementation per protocol. F1 + Phase 2 arm wiring done in
  `run_eval.py` — verified offline both directions (warned part drops the
  guard; clean content retains it).
- Freeze-time TODO not yet done: extend `analyze.py` ARMS for the new
  names; add the `-heldout2` result-dir suffix in both `run_eval.py` and
  `analyze.py` (H2 results must not collide with the immutable H dirs);
  implement F2 (segment quarantine) + wire `gateway_quarantine_seg`;
  `--task-set H2` support with the `prereg-v2` tag check mirroring the
  `prereg-v1` one. The signed tag itself is an owner action (GPG key).

## Decisions needed from the owner

- **Eval spend approval** — one full run at Phase 1 scale plus a likely
  pilot; order tens of USDC, exact number depends on arm count. H2
  generation itself is small (dozens of model calls).
- **Which model generates H2** — same OpenServ inference endpoint, or a
  different provider for diversity. Must not be a session with repo access.
- Whether `gateway_quarantine` v1 is kept as an arm (cost vs continuity).

## Hard rules not to slip on

- NEVER run Elcaro (any interface) on H2 before the freeze.
- H stays frozen; it is in-sample for everything derived from Phase 1
  analysis. Do not tune detectors on H2 either — one shot, then H2 is also
  burned.
- No uplift marketing until the preregistered decision rule passes on H2
  (roadmap §1.5). The conversion plan already enforces this.
- The warn prefix byte-parity constraint: production stays v1 until the
  eval picks a winner; then production switches and the harness imports
  from core (never duplicate again).
