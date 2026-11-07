# SafeTune arm — Kaggle runbook

Fine-tunes `CohereLabs/aya-expanse-8b` (LoRA SFT) to resist indirect
prompt injection **without** provenance warnings, then re-runs the
24-task eval to produce before/after ASR.

## Why aya-expanse-8b

- Allowed dense open-weight Cohere model (Lexsi rules).
- Weights are auto-gated and accessible with a normal HF token
  (`aya-expanse-32b` is manually gated — 401 for our token).
- `model_type: cohere` is supported by transformers ≥4.56.
- Tinker can't be used: it doesn't support `CohereForCausalLM`.

## Kaggle setup (~30 min hands-on, mostly GPU wait)

1. New Kaggle notebook → **Settings → Accelerator → GPU T4 x2**
   (or L4; P100 won't work — bitsandbytes needs Turing+).
2. **Add-ons → Secrets**: `HF_TOKEN` = your Hugging Face token
   (write access; aya-expanse-8b is auto-gated so it downloads
   immediately).
3. First cell:

```python
!git clone --depth 1 https://github.com/udirobert/elcaro /kaggle/working/elcaro
%cd /kaggle/working/elcaro/lexsi-eval
!pip install -q "transformers>=4.56" "peft>=0.13" "trl>=0.19" datasets bitsandbytes accelerate sentencepiece
import os; os.environ["HF_TOKEN"] = "<paste token or kaggle secrets get>"
```

(In Kaggle you can also use `from kaggle_secrets import UserSecretsClient; os.environ["HF_TOKEN"]=UserSecretsClient().get_secret("HF_TOKEN")`.)

4. Run:

```python
!python3 kaggle/lexsi_sft_eval.py --phase all
```

Expected: ~24 generations ×2 eval phases (few min each on T4),
SFT on 36 examples ×3 epochs (~10-20 min). Total well under an hour.

## Outputs (/kaggle/working/)

- `lexsi_results/baseline_summary.json` — base model naive-arm grades
- `lexsi_results/tuned_summary.json` — tuned model grades
- `lexsi_results/comparison.json` — before/after deltas
- `lexsi_results/*_response.txt` — raw generations (audit trail)
- `adapter/` — LoRA adapter → upload to HF:
  `hf upload Papajams/aya-expanse-8b-elcaro-sft adapter --repo-type model`

## Honesty guardrails

- Train corpus (`train_tasks/TR*.json`, 36 new scenarios) is disjoint
  from eval corpus (`tasks/T*.json`) — verified by construction.
- If tuned ASR doesn't drop, that's a publishable negative result too.
- LoRA SFT on 36 examples is a *proof of concept* repair arm, not a
  claim of robust safety — say so in the write-up.
