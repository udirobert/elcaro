# Phase 1 results: provider guard vs provider guard + Elcaro

Pre-registration: `PREREG.md`, frozen at signed tag `prereg-v1` (`0353ac3`;
frozen state `807778d`). All runs used the tagged tree unmodified. Model
`gpt-5.4-mini` on SERV, temperature 0, 3 trials per task,
`PYTHONHASHSEED=0`. Run on 2026-11-15, 23:04–23:13 UTC.

- 900 trials (5 arms × 60 tasks × 3); **0 transport errors**.
- Numbers come from `analyze.py` as frozen (`analysis-H.json`,
  `analysis-S.json`). Transcripts are in `results-<arm>[-heldout]/`.

## Primary result (held-out set H, PREREG §8)

| Arm | Trials | Pass | Useful | Compromised (attack) | Concealed | Guard-blocked | Clean useful |
|---|---|---|---|---|---|---|---|
| serv | 108 | 68 | 70 | 10/90 | 10 | 0 | 9/18 |
| serv_guard | 108 | 65 | 67 | 10/90 | 10 | 7 | 9/18 |
| serv_guard_shadow (B) | 108 | 65 | 68 | 15/90 | 15 | 8 | 10/18 |
| gateway_warn (E) | 108 | 52 | 53 | 5/90 | 5 | 19 | 9/18 |
| gateway_quarantine | 108 | 18 | 18 | 3/90 | 3 | 2 | 6/18 |

**Decision: Outcome C, "Elcaro hurts."** E's pass count (52) is more than
3 below B's (65), so the rule says stop: investigate false positives and
usefulness loss before writing any Gateway copy.

- Compromised attack trials fell from 15 to 5 (−67%). That would have met
  the Outcome A reduction thresholds, but the pass cost rules A out.
- Sign test on per-task compromise (reported, not decisive): E better on 7
  tasks, worse on 1, p = 0.070.

## Secondary result (in-sample set S; regression coverage only)

| Arm | Trials | Pass | Useful | Compromised (attack) | Guard-blocked | Clean useful |
|---|---|---|---|---|---|---|
| serv | 72 | 53 | 66 | 13/66 | 0 | 6/6 |
| serv_guard | 72 | 34 | 51 | 17/66 | 14 | 6/6 |
| serv_guard_shadow | 72 | 49 | 49 | 0/66 | 15 | 3/6 |
| gateway_warn | 72 | 50 | 53 | 3/66 | 12 | 6/6 |
| gateway_quarantine | 72 | 4 | 4 | 0/66 | 0 | 3/6 |

On the tasks its detectors were tuned on, Elcaro looks strong. This is the
gap §2 predicted between in-sample and held-out performance; S cannot
support any claim.

## Exploratory analysis (not pre-registered; does not change the decision)

Comparing like with like: B carries `serv_shadow_agent` and the gateway arms
do not, so B vs E also differs by the shadow agent. The cleaner comparison
is `serv_guard` against `gateway_warn`: same SERV tools, and the only
difference is Elcaro.

| H, serv_guard → gateway_warn | Tasks | Pass | Compromised | Guard-blocked |
|---|---|---|---|---|
| Elcaro did nothing (score < 0.3) | 13 | 17 → 17 | 3 → 3 | 1 → 1 |
| Elcaro warned | 23 | 48 → 35 | 7 → 2 | 6 → **18** |
| All | 36 | 65 → 52 | 10 → 5 | 7 → 19 |

- **Noise check.** On the 13 untouched tasks the requests are
  byte-identical, and the outcomes match exactly. The whole pass loss sits
  on the 23 warned tasks. (11 of 72 task-arm cells still show trial-to-trial
  disagreement at temperature 0.)
- **Mechanism 1: Elcaro's warning triggers SERV's guard.** Guard blocks
  on warned tasks rose from 6 to 18. That is 12 extra refusals of the whole
  request, which is most of the 13 lost passes. The two defences stack
  badly: the warning prefix makes SERV's Prompt Guard refuse.
- **Mechanism 2: the warning costs some usefulness even without a block.**
  Among warned-task trials the guard did not block, useful fell from 50/63
  (79%) to 36/51 (71%).
- **Quarantine granularity.** `gateway_quarantine` passes 18/108. In the
  LLMail tasks the whole inbox is one retrieved part, so quarantine deletes
  every legitimate email along with the attacker's.
- **Clean controls.** Every arm gets about half the generated controls
  (H07–H12) right, so their usefulness patterns may be stricter than
  intended. The effect is the same across arms.

## Implications

- H is now **in-sample** for any change made in response to it (PREREG
  §4.3 rule 4). Every fix below needs a new held-out set to be evaluated.
- Hypotheses for the Gateway, to test on fresh data:
  1. Don't also send `serv_prompt_guard` on parts Elcaro has already
     warned or quarantined.
  2. Quarantine at segment level (per email or per document), not the whole
     retrieved part.
  3. Rewrite the warn prefix so it doesn't read as an injection to a
     downstream guard.
- Per roadmap §1.5, Outcome C means **no Gateway copy claiming uplift**
  until a fix is shown on a new held-out set.
