#!/usr/bin/env python3
"""End-to-end two-model experiment orchestrator (resumable).

For each base model {general, math}, runs three states and scores each with the
sympy harness on the held-out test systems:

    base            0-shot (no training)
    sft             LoRA SFT on the method-conditioned solutions
    dpo             DPO on the verified preference pairs, on top of SFT

Everything is resumable: a stage is skipped if its eval JSON already exists.
Fused models live in the scratchpad (large); eval JSONs live in data/train/ (small).

Run:  python -m experiments.run_all           # do everything
      python -m experiments.run_all --only general
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = "/private/tmp/claude-501/-Users-hassan-Projects-Preference-Learning-in-Education/b433c465-880e-4032-b765-630e3dc83987/scratchpad"
MODELS_DIR = os.path.join(SCRATCH, "models")
EVAL_DIR = os.path.join(ROOT, "data", "train")
GEN_MAX_TOKENS = "1280"

MODELS = {
    "general": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
    "math": "mlx-community/Qwen2.5-Math-1.5B-Instruct-4bit",
}

def sft_args(data_dir, iters=600):
    return ["--train-mode", "sft", "--train-type", "lora", "--data", os.path.join(data_dir, "sft"),
            "--iters", str(iters), "--batch-size", "2", "--num-layers", "8",
            "--learning-rate", "1e-4", "--max-seq-length", "1024",
            "--steps-per-report", "50", "--fuse"]


def dpo_args(data_dir):
    return ["--train-mode", "dpo", "--train-type", "lora", "--data", os.path.join(data_dir, "dpo"),
            "--iters", "400", "--batch-size", "1", "--num-layers", "8",
            "--learning-rate", "5e-5", "--beta", "0.1", "--max-seq-length", "1024",
            "--steps-per-report", "25", "--fuse"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd):
    log("RUN " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(cmd)}")


def train(base_model, mode_args, out_dir):
    if os.path.exists(os.path.join(out_dir, "model.safetensors")) or \
       os.path.exists(os.path.join(out_dir, "model.safetensors.index.json")):
        log(f"skip training (exists): {out_dir}")
        return
    os.makedirs(out_dir, exist_ok=True)
    run([sys.executable, "-m", "mlx_lm_lora.train", "--model", base_model, "--train",
         *mode_args, "--adapter-path", out_dir])


def generate(model_path, out_jsonl, adapter=None):
    if os.path.exists(out_jsonl) and sum(1 for _ in open(out_jsonl)) >= 120:
        log(f"skip generation (exists): {out_jsonl}")
        return
    cmd = [sys.executable, "-m", "experiments.generate", "--model", model_path,
           "--out", out_jsonl, "--max-tokens", GEN_MAX_TOKENS]
    if adapter:
        cmd += ["--adapter", adapter]
    run(cmd)


def evaluate(gen_jsonl, eval_json):
    if os.path.exists(eval_json):
        log(f"skip eval (exists): {eval_json}")
        return json.load(open(eval_json))
    run([sys.executable, "experiments/evaluate.py", "--generations", gen_jsonl, "--out", eval_json])
    return json.load(open(eval_json))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(MODELS), help="run just one base model")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data", "train"),
                    help="dir containing sft/ and dpo/ subdirs")
    ap.add_argument("--tag", default="", help="prefix for eval/gen/model artifacts, e.g. 'worked_'")
    ap.add_argument("--no-dpo", action="store_true", help="run base+SFT only (skip DPO)")
    ap.add_argument("--sft-iters", type=int, default=600)
    args = ap.parse_args()
    os.makedirs(MODELS_DIR, exist_ok=True)
    targets = [args.only] if args.only else list(MODELS)
    tag = args.tag
    SFT_ARGS, DPO_ARGS = sft_args(args.data_dir, args.sft_iters), dpo_args(args.data_dir)
    results = {}

    for name in targets:
        base = MODELS[name]
        log(f"===== MODEL: {tag}{name} ({base}) =====")

        # --- base ---  (0-shot; independent of training data, so no tag)
        gen = os.path.join(EVAL_DIR, f"gen_{name}_base.jsonl")
        ev = os.path.join(EVAL_DIR, f"eval_{name}_base.json")
        generate(base, gen)
        results[f"{name}_base"] = evaluate(gen, ev)

        # --- SFT ---
        sft_dir = os.path.join(MODELS_DIR, f"{tag}{name}_sft")
        train(base, SFT_ARGS, sft_dir)
        gen = os.path.join(EVAL_DIR, f"gen_{tag}{name}_sft.jsonl")
        ev = os.path.join(EVAL_DIR, f"eval_{tag}{name}_sft.json")
        generate(sft_dir, gen)
        results[f"{tag}{name}_sft"] = evaluate(gen, ev)

        # --- DPO (on top of SFT) ---
        if args.no_dpo:
            continue
        dpo_dir = os.path.join(MODELS_DIR, f"{tag}{name}_dpo")
        train(sft_dir, DPO_ARGS, dpo_dir)
        gen = os.path.join(EVAL_DIR, f"gen_{tag}{name}_dpo.jsonl")
        ev = os.path.join(EVAL_DIR, f"eval_{tag}{name}_dpo.json")
        generate(dpo_dir, gen)
        results[f"{tag}{name}_dpo"] = evaluate(gen, ev)

    # --- results table ---
    summary = os.path.join(EVAL_DIR, f"results_{tag or 'terse'}summary.json")
    json.dump(results, open(summary, "w"), indent=2)
    log("===== RESULTS (answer accuracy / method faithfulness) =====")
    hdr = f"{'state':16s} {'acc':>8s} {'faithful':>9s}  error_modes"
    print(hdr); print("-" * len(hdr))
    for k, v in results.items():
        print(f"{k:16s} {v['answer_accuracy']:>8.3f} {v['method_faithfulness']:>9.3f}  {v.get('error_modes')}")
    log(f"saved {summary}")


if __name__ == "__main__":
    main()
