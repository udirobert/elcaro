#!/usr/bin/env python3
"""Lexsi SafeTune arm — run on Kaggle (T4 x2 or L4 accelerator).

Pipeline (phases via --phase):
  baseline : generate naive-arm responses for the 24-task eval corpus
             with base CohereLabs/aya-expanse-8b, grade deterministically.
  train    : LoRA SFT on sft_train.jsonl (36 new IPI tasks, disjoint
             from eval), save adapter to ./adapter.
  eval     : same 24 tasks with base+adapter, grade, compare.
  all      : baseline -> train -> eval in one go.

Setup (Kaggle notebook):
  !git clone --depth 1 https://github.com/udirobert/elcaro /kaggle/working/elcaro
  %cd /kaggle/working/elcaro/lexsi-eval
  !pip install -q "transformers>=4.56" "peft>=0.13" "trl>=0.19" \
      "datasets" "bitsandbytes" "accelerate" "sentencepiece"
  import os; os.environ["HF_TOKEN"] = "<your HF token>"  # Kaggle Secrets: HF_TOKEN
  !python3 kaggle/lexsi_sft_eval.py --phase all

Notes:
- 4-bit NF4 base + LoRA fits a single T4 (16GB). P100 is NOT supported
  by bitsandbytes — use T4 x2 or L4.
- The eval corpus (tasks/) and train corpus (train_tasks/) are disjoint
  by construction — no eval-task leakage into SFT.
"""

import argparse
import json
import os
import sys
from pathlib import Path

WORK = Path("/kaggle/working")
ROOT = Path(__file__).resolve().parent.parent  # lexsi-eval/
sys.path.insert(0, str(ROOT))

MODEL_ID = "CohereLabs/aya-expanse-8b"
EVAL_TASKS = ROOT / "tasks"
SFT_DATA = ROOT / "sft_train.jsonl"
ADAPTER_DIR = WORK / "adapter"
OUT_DIR = WORK / "lexsi_results"


def log(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def load_base(model_id: str = MODEL_ID, for_training: bool = False):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(model_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = not for_training
    return model, tok


def eval_tasks_naive(model, tok, tag: str) -> list[dict]:
    """Generate naive-arm responses for all eval tasks; grade deterministically."""
    import torch
    from grade import grade, load_task
    from run_eval import build_messages

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graded = []
    task_paths = sorted(EVAL_TASKS.glob("T*.json"))
    for i, p in enumerate(task_paths):
        task = load_task(p)
        messages = build_messages(task, "naive")
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=600,
                do_sample=False,
                pad_token_id=tok.pad_token_id,
            )
        response = tok.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        g = grade(task, response)
        graded.append(
            {
                "task_id": task["id"],
                "pass": g["pass"],
                "useful": g["useful"],
                "compromised": g["compromised"],
                "detected": g["injection_detected"],
            }
        )
        (OUT_DIR / f"{tag}_{task['id']}_response.txt").write_text(response)
        print(
            f"[{i + 1}/{len(task_paths)}] {task['id']}: "
            f"pass={g['pass']} compromised={g['compromised']}",
            flush=True,
        )

    summary = {
        "model": MODEL_ID,
        "arm": "naive",
        "tag": tag,
        "n": len(graded),
        "pass": sum(1 for g in graded if g["pass"]),
        "useful": sum(1 for g in graded if g["useful"]),
        "compromised": sum(1 for g in graded if g["compromised"]),
        "per_task": graded,
    }
    (OUT_DIR / f"{tag}_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("n", "pass", "useful", "compromised")}, indent=2))
    return graded


def train() -> None:
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTConfig, SFTTrainer

    log("loading base model for training")
    model, tok = load_base(for_training=True)
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files=str(SFT_DATA), split="train")
    log(f"SFT dataset: {len(ds)} examples")

    args = SFTConfig(
        output_dir=str(WORK / "sft_out"),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        num_train_epochs=3,
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=5,
        save_strategy="no",
        bf16=True,
        gradient_checkpointing=True,
        max_grad_norm=1.0,
        report_to=[],
        packing=False,
    )
    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=ds,
        processing_class=tok,
    )
    trainer.train()
    model.save_pretrained(str(ADAPTER_DIR))
    tok.save_pretrained(str(ADAPTER_DIR))
    log(f"adapter saved to {ADAPTER_DIR}")


def eval_tuned() -> None:
    import torch
    from grade import grade, load_task
    from peft import PeftModel
    from run_eval import build_messages

    log("loading base + adapter for tuned eval")
    model, tok = load_base()
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graded = []
    task_paths = sorted(EVAL_TASKS.glob("T*.json"))
    for i, p in enumerate(task_paths):
        task = load_task(p)
        messages = build_messages(task, "naive")
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=600,
                do_sample=False,
                pad_token_id=tok.pad_token_id,
            )
        response = tok.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        g = grade(task, response)
        graded.append(
            {
                "task_id": task["id"],
                "pass": g["pass"],
                "useful": g["useful"],
                "compromised": g["compromised"],
                "detected": g["injection_detected"],
            }
        )
        (OUT_DIR / f"tuned_{task['id']}_response.txt").write_text(response)
        print(
            f"[{i + 1}/{len(task_paths)}] {task['id']}: "
            f"pass={g['pass']} compromised={g['compromised']}",
            flush=True,
        )

    summary = {
        "model": f"{MODEL_ID}+elcaro-sft-lora",
        "arm": "naive",
        "tag": "tuned",
        "n": len(graded),
        "pass": sum(1 for g in graded if g["pass"]),
        "useful": sum(1 for g in graded if g["useful"]),
        "compromised": sum(1 for g in graded if g["compromised"]),
        "per_task": graded,
    }
    (OUT_DIR / "tuned_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("n", "pass", "useful", "compromised")}, indent=2))

    # before/after comparison
    base_path = OUT_DIR / "baseline_summary.json"
    if base_path.exists():
        base = json.loads(base_path.read_text())
        comp = {
            "baseline": {k: base[k] for k in ("pass", "useful", "compromised")},
            "tuned": {k: summary[k] for k in ("pass", "useful", "compromised")},
            "delta_compromised": base["compromised"] - summary["compromised"],
            "delta_pass": summary["pass"] - base["pass"],
        }
        (OUT_DIR / "comparison.json").write_text(json.dumps(comp, indent=2))
        print("COMPARISON:", json.dumps(comp, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["baseline", "train", "eval", "all"], default="all")
    args = ap.parse_args()

    os.environ.setdefault("HF_TOKEN", "")
    if args.phase in ("baseline", "all"):
        log("phase: baseline eval (base model, naive arm)")
        model, tok = load_base()
        eval_tasks_naive(model, tok, "baseline")
        del model
        import torch

        torch.cuda.empty_cache()
    if args.phase in ("train", "all"):
        log("phase: LoRA SFT")
        train()
        import torch

        torch.cuda.empty_cache()
    if args.phase in ("eval", "all"):
        log("phase: tuned eval")
        eval_tuned()
    log("done — artifacts in /kaggle/working/lexsi_results and /kaggle/working/adapter")


if __name__ == "__main__":
    main()
