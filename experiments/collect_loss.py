#!/usr/bin/env python3
"""Re-run the SFT trainings (loss logging only) to recover train/val loss curves.

Faithful to the experiment: same base models, same LoRA config and seed, SFT from
base on the same data. No --fuse (we only need the loss trajectory). Writes one log
per run to data/train/loss/<name>.log and a parsed CSV.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOSS = os.path.join(ROOT, "data", "train", "loss")
SCRATCH = "/private/tmp/claude-501/-Users-hassan-Projects-Preference-Learning-in-Education/b433c465-880e-4032-b765-630e3dc83987/scratchpad/loss_adapters"

MODELS = {"general": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
          "math": "mlx-community/Qwen2.5-Math-1.5B-Instruct-4bit"}
RUNS = [
    ("terse_general",  "general", "data/train/sft"),
    ("terse_math",     "math",    "data/train/sft"),
    ("worked_general", "general", "data/train_worked/sft"),
    ("worked_math",    "math",    "data/train_worked/sft"),
]

TRAIN_RE = re.compile(r"Iter (\d+): loss ([0-9.]+)")
VAL_RE = re.compile(r"Iter (\d+): Val loss ([0-9.]+)")


def parse(logtext, out_csv):
    train = TRAIN_RE.findall(logtext)
    val = VAL_RE.findall(logtext)
    with open(out_csv, "w") as f:
        f.write("kind,iter,loss\n")
        for it, l in train:
            f.write(f"train,{it},{l}\n")
        for it, l in val:
            f.write(f"val,{it},{l}\n")
    return len(train), len(val)


def main():
    os.makedirs(LOSS, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    for name, model_key, data in RUNS:
        csv = os.path.join(LOSS, f"{name}.csv")
        if os.path.exists(csv):
            print(f"skip {name} (csv exists)", flush=True)
            continue
        logf = os.path.join(LOSS, f"{name}.log")
        print(f"=== training {name} ===", flush=True)
        cmd = [sys.executable, "-m", "mlx_lm_lora.train", "--model", MODELS[model_key],
               "--train", "--train-mode", "sft", "--train-type", "lora", "--data", data,
               "--iters", "600", "--batch-size", "2", "--num-layers", "8",
               "--learning-rate", "1e-4", "--max-seq-length", "1024",
               "--steps-per-report", "20", "--val-batches", "10",
               "--adapter-path", os.path.join(SCRATCH, name)]
        with open(logf, "w") as lf:
            subprocess.run(cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT)
        nt, nv = parse(open(logf, encoding="utf-8", errors="ignore").read(), csv)
        print(f"  {name}: {nt} train points, {nv} val points -> {csv}", flush=True)
    print("LOSS_COLLECTION_DONE", flush=True)


if __name__ == "__main__":
    main()
