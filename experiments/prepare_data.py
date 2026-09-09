#!/usr/bin/env python3
"""Prepare training/eval data for the two-model experiment.

Reads the verified multi-method dataset and emits, with SYSTEM-GROUPED splits
(no system leaks across train/val/test):

  data/train/sft_{train,valid,test}.jsonl   MLX-LM chat format for LoRA SFT
  data/train/dpo_{train,valid,test}.jsonl   {prompt, chosen, rejected} for DPO
  data/train/test_systems.jsonl             held-out systems for evaluation
  data/train/split_manifest.json            which system ids fall in which split

The prompt is method-conditioned so ONE model can produce any requested method.
"""
import json
import os
import random
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MM = os.path.join(ROOT, "data", "multimethod")
OUT = os.path.join(ROOT, "data", "train")
SEED = 20260909
SPLIT = (0.70, 0.15, 0.15)   # train / valid / test, by SYSTEM

METHOD_NAME = {
    "substitution": "substitution",
    "elimination": "elimination",
    "graphing": "graphing",
    "cramers_rule": "Cramer's rule",
    "inverse_matrix": "the matrix inverse method",
    "gaussian_elimination": "Gaussian elimination",
}
SYSTEM_INSTR = (
    "You are a math tutor. Solve the system of equations using {method}. "
    "Show the steps for that method and end with a line 'Solution: ...' giving the values."
)


def build_prompt(method, equations_block):
    """A method-conditioned user prompt. `equations_block` is the raw '$$..$$' text."""
    return (f"Solve the system of equations using {METHOD_NAME[method]}.\n{equations_block}")


def system_block_from_prompt(sft_prompt):
    # sft prompts look like "Solve the system of equations:\n$$..$$  $$..$$"
    return sft_prompt.split("\n", 1)[1].strip() if "\n" in sft_prompt else sft_prompt


def main():
    os.makedirs(OUT, exist_ok=True)
    sft = [json.loads(l) for l in open(os.path.join(MM, "sft_multimethod.jsonl"), encoding="utf-8")]
    pref = [json.loads(l) for l in open(os.path.join(MM, "preference_pairs.jsonl"), encoding="utf-8")]
    systems = {json.loads(l)["source"]["problem_id"]: json.loads(l)
               for l in open(os.path.join(MM, "systems_multimethod.jsonl"), encoding="utf-8")}

    # ---- system-grouped split ----
    sys_ids = sorted(systems.keys())
    rng = random.Random(SEED)
    rng.shuffle(sys_ids)
    n = len(sys_ids)
    n_tr = int(n * SPLIT[0])
    n_va = int(n * SPLIT[1])
    split_of = {}
    for i, sid in enumerate(sys_ids):
        split_of[sid] = "train" if i < n_tr else ("valid" if i < n_tr + n_va else "test")

    def bucket(items, keyfn):
        out = defaultdict(list)
        for it in items:
            out[split_of[keyfn(it)]].append(it)
        return out

    # ---- SFT (MLX chat format) ----
    sft_by = bucket(sft, lambda e: e["meta"]["problem_id"])
    for split, items in sft_by.items():
        with open(os.path.join(OUT, f"sft_{split}.jsonl"), "w", encoding="utf-8") as fh:
            for e in items:
                method = e["meta"]["method"]
                block = system_block_from_prompt(e["prompt"])
                user = build_prompt(method, block)
                fh.write(json.dumps({"messages": [
                    {"role": "system", "content": SYSTEM_INSTR.format(method=METHOD_NAME[method])},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": e["completion"]},
                ]}, ensure_ascii=False) + "\n")

    # ---- DPO ----
    pref_by = bucket(pref, lambda p: p["meta"]["problem_id"])
    for split, items in pref_by.items():
        with open(os.path.join(OUT, f"dpo_{split}.jsonl"), "w", encoding="utf-8") as fh:
            for p in items:
                method = p["meta"]["method"]
                block = system_block_from_prompt(p["prompt"])
                user = build_prompt(method, block)
                fh.write(json.dumps({
                    "prompt": user, "chosen": p["chosen"], "rejected": p["rejected"],
                    "meta": p["meta"],
                }, ensure_ascii=False) + "\n")

    # ---- held-out test systems (for eval: prompt the model per method) ----
    with open(os.path.join(OUT, "test_systems.jsonl"), "w", encoding="utf-8") as fh:
        for sid, rec in systems.items():
            if split_of[sid] != "test":
                continue
            fh.write(json.dumps({
                "problem_id": sid,
                "variables": rec["system"]["variables"],
                "equations_tex": rec["system"]["equations_tex"],
                "reference_solution": rec["system"]["reference_solution"],
                "methods": [m["method"] for m in rec["methods"]],
            }, ensure_ascii=False) + "\n")

    manifest = {
        "seed": SEED, "split_ratio": SPLIT,
        "systems": {"train": sum(v == "train" for v in split_of.values()),
                    "valid": sum(v == "valid" for v in split_of.values()),
                    "test": sum(v == "test" for v in split_of.values())},
        "sft_counts": {k: len(v) for k, v in sft_by.items()},
        "dpo_counts": {k: len(v) for k, v in pref_by.items()},
        "prompt_template": build_prompt("elimination", "$$...$$"),
        "system_ids": {s: [sid for sid in sys_ids if split_of[sid] == s]
                       for s in ("train", "valid", "test")},
    }
    with open(os.path.join(OUT, "split_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps({k: v for k, v in manifest.items() if k != "system_ids"}, indent=2))


if __name__ == "__main__":
    main()
