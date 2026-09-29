# Elcaro scorer — Telegraph scoring module

A Telegraph scoring module for `CONTENT_MODERATION` and `TEXT_CLASSIFICATION`,
built for the Evaluator track. It is separate from `eval/src/lib.rs`, which is a
benchmark harness bound to Elcaro's `/scan` schema, not something a validator
can register.

It grades the committed verdict first (injection or clean, harmful or benign),
then category labels, then any risk figure. Text overlap only covers what's
left. Rationale: [docs/telegraph-season-2.md](../../docs/telegraph-season-2.md).

## Interface

Zero imports, `no_std`, ~11 KB. Exports what a validator node calls:

| Export | Signature | Returns |
|---|---|---|
| `alloc` | `(i32) -> i32` | pointer for a string the host writes |
| `dealloc` | `(i32, i32)` | no-op (bump heap) |
| `rank_answer` | `(q, q_len, gt, gt_len, answer, answer_len) -> f32` | score in [0, 1] |
| `breakdown_answer` | same `-> i32` | ptr to `f32[5]`: verdict, labels, numeric, text, composite (`-1` = n/a) |

## Anti-gaming rules

| Rule | Effect |
|---|---|
| Wrong-direction verdict | capped at 0.15 however many right words it carries |
| Hedge (asserts both poles, or a keyword dump) | capped at 0.30 |
| Question clauses (`...?`) | cast no verdict, so restating the prompt commits nothing |
| Words/figures copied from the question | earn nothing unless the ground truth has them; a mostly copied answer is ×0.1 |
| Labels | graded on precision and recall, so listing every category costs points |
| Negation | `no`/`not`/`isn't`… flips the next verdict word in the same clause; `, . ; !` end its reach (`"No, it is phishing"` reads unsafe) |

## Build, test, bench

This machine: rustup's default toolchain is broken and Homebrew's cargo has no
wasm target, so run through rustup's `stable` explicitly:

```bash
cd eval/scorer
PATH="$HOME/.cargo/bin:$PATH" rustup run stable cargo test
PATH="$HOME/.cargo/bin:$PATH" rustup run stable cargo build --release --target wasm32-unknown-unknown

python make_bench.py              # regenerate bench.json from eval/corpus.json
node harness.mjs                  # margin / wins / self-match vs text baseline (+ champions/)
node harness.mjs --attacks        # anti-gaming fixtures (attacks.json)
node harness.mjs --agreement target/wasm32-unknown-unknown/release/elcaro_scorer.wasm champions/X.wasm
node harness.mjs --diff    target/wasm32-unknown-unknown/release/elcaro_scorer.wasm champions/X.wasm
node harness.mjs --case "question" "ground truth" "answer"
```

The harness exits non-zero if our module loses a bench pair, scores its own
ground truth below 0.99, or lets an attack through. CI runs all three.

## Current numbers (our corpus, 29 Sep 2026)

Seated champions downloaded from `https://devnode.telegraphprotocol.com/api/wasm`
into `champions/` (gitignored). All three are zkasuran salience scorers. The
`wasm_hash` on chain does not match the downloaded bytes (sha256 or sha3-256) —
consistent with the IPFS re-serialisation issue, so champions are verified by
loading them, not by hash.

| module | margin | wins | worst self-match |
|---|---|---|---|
| elcaro_scorer | 0.6287 | 29/29 | 1.0000 |
| url_c3 (champion, URL_SCAN) | 0.6278 | 27/29 | 1.0000 |
| cmod_r5 (champion, CONTENT_MODERATION) | 0.4828 | 26/29 | 1.0000 |
| tc_pen0 (champion, TEXT_CLASSIFICATION) | 0.4373 | 15/29 | 0.9888 |
| text-baseline (token F1) | 0.1301 | 22/29 | 1.0000 |

Rank agreement (ours vs champion, ladder proxy for the 0.60 registration
gate): cmod_r5 **0.7925**, tc_pen0 **0.7436**, url_c3 **0.9431** — all clear it.

Attacks: elcaro_scorer 10/10 held; champions hold 4/10 (cmod_r5), 2/10
(tc_pen0), 6/10 (url_c3). The champions are salience models: they give 1.0 to
an answer that copies the ground truth verbatim, 0.0 to an honest paraphrase
(`cmod_r5` scores every honest fixture 0.0), and 1.0 to the hedge,
false-positive and restated-score attacks. `text-baseline` stands in for the
network's text-overlap modules; the three champions above are the real thing.

Elcaro miner summaries for the 26 corpus cases average 0.813 under this module
and 0.434 under the text baseline.

## Registration checklist

1. [x] Seated champions downloaded (see `docs/telegraph-season-2.md` W1).
2. [x] `node harness.mjs`: margin and wins at least matching the champion.
3. [x] `--agreement` ≥ 0.60 against the seated champion.

Remaining before sending a registration: widen the bench with answers written
by other people / real miner outputs, then pay the registration bond.
