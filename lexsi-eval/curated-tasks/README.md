---
tags:
- curatorkit
configs:
- config_name: sft_alpaca
  default: true
  description: curatorkit sft_alpaca export, sha256 343aa83a9cd4043131ab6c07820d309eddf3bb4a7f89b5d98c40205167405a95
  data_files:
  - split: train
    path: sft_alpaca.jsonl
---

# Dataset Card: ipi-eval-tasks

## Summary

- **Run timestamp**: 2026-11-07T20:43:24.829787Z
- **Wall clock time**: 0.9s
- **Pipeline config hash**: `fd371385df11afc7`

## Source Documents

  - Unknown

## Pipeline Stages

| Step | Input | Passed | Recovered | Rejected | Forward |
|------|-------|--------|-----------|----------|---------|
| JSONLReader | 24 | 24 | — | 0 | 24 |
| SchemaGate | 24 | 24 | 0 | 0 | 24 |
| ExactDeduplicator | 24 | 24 | — | — | 24 |
| MinHashDeduplicator | 24 | 24 | — | — | 24 |
| SecretsGate | 24 | 23 | 0 | 1 | 23 |
| CorpusExporter | — | 23 | — | — | 23 |
| AlpacaExporter | — | 23 | — | — | 23 |

## Gate Pass Rates and Rejection Breakdown

- **JSONLReader**: 24/0 passed (N/A), 0 rejected
- **SchemaGate**: 24/24 passed (100.0%), 0 rejected
- **SecretsGate**: 23/24 passed (95.8%), 1 rejected


**Rejection reasons:**
  - `secret_detected:Base64 High Entropy String`: 1

## Deduplication

  - near_duplicates_removed: 0
  - surviving_count: 24

## Known Limitations

- MinHash threshold used: **0.85** — this is a starting point, not a universal answer. Adjust per domain (legal, medical, and other domain-specific corpora may need a lower threshold to avoid losing structurally similar but semantically valid examples).
- Table extraction requires `extract_tables: true` on the PDF reader and MinerU with GPU support. Disabled by default.
- Token counting uses a whitespace tokenizer by default. For exact LLM context window
  enforcement, enable `use_tiktoken: true` in the SchemaGate config.
- Both within-run (MinHash/Diversity) and cross-run (EmbeddingDeduplicator) deduplication
  are available. Cross-run dedup persists an embedding index across runs; use
  `embedding_reset_index: true` to start fresh.

## Reproduction

```bash
pip install curatorkit
curatorkit run pipeline.yaml --output-dir ./out/
```

## Tool Versions

- **curatorkit**: 0.1.23
- **python**: 3.14.5

## Configs

Load one with `datasets.load_dataset("<this folder or Hub repo>", "<config>")`.

| Config | Splits (rows) | Columns |
|--------|---------------|---------|
| `sft_alpaca` | train (23) | `instruction`: string<br>`input`: string (empty when there is no input)<br>`output`: string |
