"""Lexsi SafeTune arm — aya-expanse-8b LoRA SFT vs indirect prompt injection.

Kaggle port of lexsi-eval/kaggle/lexsi_sft_eval.py: same 24-task eval corpus,
same naive-arm prompts (build_messages(task, "naive")), same deterministic
grader, same sft_train.jsonl, same LoRA config (r=16, alpha=32, 3 epochs,
lr 1e-4, cosine). Training mechanics differ from the repo script in one
respect: fp16 + device_map="auto" + plain HF Trainer with completion-only
labels (the path proven on this Kaggle image) instead of 4-bit
bitsandbytes + TRL SFTTrainer. Effective batch is still 16.

Pipeline: baseline eval (naive arm) -> LoRA SFT -> tuned eval ->
comparison.json. Repo is cloned from GitHub; HF token ships inside the
attached private lexsi-sft-v4 dataset (aya-expanse-8b is auto-gated).

Outputs:
  /kaggle/working/lexsi_results/{baseline,tuned}_summary.json
  /kaggle/working/lexsi_results/comparison.json
  /kaggle/working/lexsi_results/{baseline,tuned}_T*_response.txt
  /kaggle/working/adapter/   (LoRA adapter + tokenizer)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# peft 0.21 crashes on the image's torchao 0.10 (is_torchao_available raises
# instead of returning False). Upgrade it; fall back to removing it — the
# fp16 model doesn't need torchao.
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "torchao>=0.16"],
    check=False,
)
if (
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import torchao; "
            "v=tuple(int(x) for x in torchao.__version__.split('.')[:2]); "
            "assert v >= (0, 16)",
        ],
        capture_output=True,
    ).returncode
    != 0
):
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "torchao"],
        check=False,
    )

subprocess.run(
    [  # noqa: S607
        "git",
        "clone",
        "--depth",
        "1",
        "https://github.com/udirobert/elcaro",
        "/kaggle/working/elcaro",
    ],
    check=True,
)
ROOT = Path("/kaggle/working/elcaro/lexsi-eval")
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from grade import grade, load_task  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from run_eval import build_messages  # noqa: E402
from torch.utils.data import Dataset  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

OUT = Path("/kaggle/working/lexsi_results")
OUT.mkdir(parents=True, exist_ok=True)
ADAPTER = Path("/kaggle/working/adapter")
EVAL_TASKS = sorted((ROOT / "tasks").glob("T*.json"))
MODEL_ID = "CohereLabs/aya-expanse-8b"

# HF token rides in the attached private dataset (same trick as lexsi-sft-v4).
HF_TOKEN = next(Path("/kaggle/input").rglob("hf_token.txt")).read_text().strip()
os.environ["HF_TOKEN"] = HF_TOKEN

# keep the 16GB snapshot OUT of /kaggle/working so the kernel output zip
# stays small (adapter + results only)
MODEL_DIR = "/kaggle/tmp/aya-expanse-8b"
if not Path(MODEL_DIR, "config.json").exists():
    from huggingface_hub import snapshot_download

    snapshot_download(MODEL_ID, token=HF_TOKEN, local_dir=MODEL_DIR)
print(f"[safetune] cuda devices: {torch.cuda.device_count()}", flush=True)

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
tok.padding_side = "left"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    dtype=torch.float16,
    device_map="auto",
    attn_implementation="sdpa",
)


def eval_arm(tag: str) -> dict:
    """Generate naive-arm responses for all 24 eval tasks; grade deterministically."""
    model.config.use_cache = True
    model.eval()
    t0 = time.time()
    graded = []
    for i, p in enumerate(EVAL_TASKS, 1):
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
        (OUT / f"{tag}_{task['id']}_response.txt").write_text(response)
        print(
            f"[{tag} {i}/{len(EVAL_TASKS)}] {task['id']}: "
            f"pass={g['pass']} compromised={g['compromised']}",
            flush=True,
        )

    summary = {
        "model": MODEL_ID + ("+elcaro-sft-lora" if tag == "tuned" else ""),
        "arm": "naive",
        "tag": tag,
        "n": len(graded),
        "pass": sum(1 for g in graded if g["pass"]),
        "useful": sum(1 for g in graded if g["useful"]),
        "compromised": sum(1 for g in graded if g["compromised"]),
        "per_task": graded,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / f"{tag}_summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"[safetune] {tag} summary: "
        + json.dumps({k: summary[k] for k in ("n", "pass", "useful", "compromised")}),
        flush=True,
    )
    return summary


# --- phase 1: baseline eval (naive arm, base model) --------------------------
print("[safetune] === BASELINE EVAL ===", flush=True)
base = eval_arm("baseline")

# --- phase 2: tokenize sft_train.jsonl (completion-only labels) --------------
print("[safetune] === TOKENIZING SFT DATA ===", flush=True)
MAX_LEN = 2560
rows = [
    json.loads(line) for line in (ROOT / "sft_train.jsonl").read_text().splitlines() if line.strip()
]


def encode(row):
    msgs = row["messages"]
    prompt_text = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
    full_text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
    p_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
    f_ids = tok(full_text, add_special_tokens=False)["input_ids"]
    if len(f_ids) > MAX_LEN:
        return None  # dropping beats truncating the completion tail
    n_prompt = min(len(p_ids), len(f_ids))
    return {"input_ids": f_ids, "labels": [-100] * n_prompt + f_ids[n_prompt:]}


encoded = []
dropped = 0
for r in rows:
    e = encode(r)
    if e is None or len(e["input_ids"]) < 20 or all(lbl == -100 for lbl in e["labels"]):
        dropped += 1
        continue
    encoded.append(e)
print(f"[safetune] encoded {len(encoded)}/{len(rows)} examples, dropped {dropped}", flush=True)
lens = [len(e["input_ids"]) for e in encoded]
print(f"[safetune] len p50={sorted(lens)[len(lens) // 2]} max={max(lens)}", flush=True)


class SFTDataset(Dataset):
    def __init__(self, examples):
        self.examples = examples

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, i):
        return self.examples[i]


def collate(batch):
    maxlen = max(len(b["input_ids"]) for b in batch)
    input_ids, labels, attn = [], [], []
    for b in batch:
        n = len(b["input_ids"])
        padn = maxlen - n
        input_ids.append(b["input_ids"] + [tok.pad_token_id] * padn)
        labels.append(b["labels"] + [-100] * padn)
        attn.append([1] * n + [0] * padn)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
        "attention_mask": torch.tensor(attn, dtype=torch.long),
    }


# --- phase 3: LoRA SFT --------------------------------------------------------
print("[safetune] === LORA SFT ===", flush=True)
model.config.use_cache = False
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
model.enable_input_require_grads()
model.print_trainable_parameters()

args = TrainingArguments(
    output_dir="/kaggle/working/sft_out",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,  # effective batch 16, same as repo script
    num_train_epochs=3,
    learning_rate=1e-4,
    lr_scheduler_type="cosine",
    warmup_steps=0.1,  # v5 removed warmup_ratio; float here = ratio
    logging_steps=5,
    save_strategy="no",
    fp16=True,
    gradient_checkpointing=True,
    max_grad_norm=1.0,
    dataloader_num_workers=2,
    report_to=[],
    seed=7,
    remove_unused_columns=False,
)
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=SFTDataset(encoded),
    data_collator=collate,
)
trainer.train()
model.save_pretrained(str(ADAPTER))
tok.save_pretrained(str(ADAPTER))
print(f"[safetune] adapter saved -> {ADAPTER}", flush=True)

# --- phase 4: tuned eval -------------------------------------------------------
print("[safetune] === TUNED EVAL ===", flush=True)
tuned = eval_arm("tuned")

comp = {
    "baseline": {k: base[k] for k in ("pass", "useful", "compromised")},
    "tuned": {k: tuned[k] for k in ("pass", "useful", "compromised")},
    "delta_compromised": base["compromised"] - tuned["compromised"],
    "delta_pass": tuned["pass"] - base["pass"],
}
(OUT / "comparison.json").write_text(json.dumps(comp, indent=2))
print(f"[safetune] DONE. comparison: {json.dumps(comp)}", flush=True)
