#!/usr/bin/env python3
"""Track A item A1, part 2: does DPO still hurt with ON-POLICY, sympy-graded pairs?

Phase 1 DPO pairs were built by the generator: the rejected text is the chosen text cut
short plus a fixed wrong conclusion (see experiments/dpo_pair_diagnostics.py). This
experiment separates two explanations of the DPO failure:
  (1) PAIR CONSTRUCTION (offline, near-identical, surface-separable pairs), versus
  (2) STRENGTH OF THE UPDATE (beta).

Design (worked targets, both base models, on top of the existing worked SFT model):
                      beta 0.1                 beta 0.5
  offline pairs       Phase 1 (exists)         run here
  on-policy pairs     run here                 run here

On-policy pairs: sample K solutions per training prompt from the SFT model itself
(temperature 0.8), grade each with the same sympy rule as evaluate.py, and pair a
correct sample (or the verified gold solution if none is correct) against an incorrect
sample. Prompts where every sample is correct give no pair.

REQUIRES Apple Silicon + mlx, mlx-lm, mlx-lm-lora, and the fused worked SFT models from
`python -m experiments.run_all --data-dir data/train_worked --tag worked_`
(set PLE_SCRATCH to the folder that holds models/). NOT YET RUN: written 2026-11-03 in a
cloud container without MLX; the pair-building logic is unit-tested (tests/test_track_a.py).

Usage:
  python -m experiments.onpolicy_dpo sample  --only math        # step 1: K samples per prompt
  python -m experiments.onpolicy_dpo pairs                       # step 2: grade + build pairs
  python -m experiments.onpolicy_dpo train   --only math        # step 3: 3 DPO runs + eval
"""
import argparse
import json
import os
import random
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.evaluate import parse_answer, satisfies  # noqa: E402
from oatutor_extract.multimethod import extract_system, system_of  # noqa: E402

SRC = os.path.join(ROOT, "data", "train_worked")
OUT = os.path.join(ROOT, "data", "train_worked_onpolicy")
K, TEMP, SEED = 4, 0.8, 20261103


def grade(user_prompt, completion):
    """True/False by the evaluate.py rule; None if the system cannot be parsed."""
    block = user_prompt.split("\n", 1)[1] if "\n" in user_prompt else user_prompt
    si = system_of(extract_system(block))
    if si is None:
        return None
    vars_, A, b = si
    ans = parse_answer(completion)
    return bool(ans) and satisfies(A, b, vars_, ans)


def build_pairs(records, rng):
    """records: [{prompt, gold, samples:[str]}] -> (pairs, stats). Pure; unit-tested."""
    pairs, stats = [], {"prompts": 0, "all_correct": 0, "all_wrong": 0, "mixed": 0, "unparsed": 0}
    for r in records:
        stats["prompts"] += 1
        graded = [(s, grade(r["prompt"], s)) for s in r["samples"]]
        if any(g is None for _, g in graded):
            stats["unparsed"] += 1
            continue
        good = [s for s, g in graded if g]
        bad = [s for s, g in graded if not g]
        if not bad:
            stats["all_correct"] += 1
            continue
        stats["mixed" if good else "all_wrong"] += 1
        chosen = rng.choice(good) if good else r["gold"]
        pairs.append({"prompt": r["prompt"], "chosen": chosen, "rejected": rng.choice(bad),
                      "chosen_source": "own_sample" if good else "gold"})
    return pairs, stats


def _load_sft(split):
    rows = []
    for line in open(os.path.join(SRC, "sft", f"{split}.jsonl"), encoding="utf-8"):
        m = json.loads(line)["messages"]
        rows.append({"system": m[0]["content"], "prompt": m[1]["content"], "gold": m[2]["content"]})
    return rows


def cmd_sample(args):
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler
    from experiments.run_all import MODELS, MODELS_DIR
    for name in ([args.only] if args.only else list(MODELS)):
        model, tok = load(os.path.join(MODELS_DIR, f"worked_{name}_sft"))
        sampler = make_sampler(temp=TEMP)
        for split in ("train", "valid"):
            path = os.path.join(OUT, f"samples_{name}_{split}.jsonl")
            os.makedirs(OUT, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                for r in _load_sft(split):
                    msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["prompt"]}]
                    prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
                    r["samples"] = [generate(model, tok, prompt=prompt, max_tokens=1024, sampler=sampler,
                                             verbose=False) for _ in range(K)]
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("wrote", path)


def cmd_pairs(args):
    from experiments.run_all import MODELS
    rng = random.Random(SEED)
    summary = {}
    for name in ([args.only] if args.only else list(MODELS)):
        d = os.path.join(OUT, name, "dpo")
        os.makedirs(d, exist_ok=True)
        for split in ("train", "valid"):
            recs = [json.loads(l) for l in open(os.path.join(OUT, f"samples_{name}_{split}.jsonl"), encoding="utf-8")]
            pairs, stats = build_pairs(recs, rng)
            with open(os.path.join(d, f"{split}.jsonl"), "w", encoding="utf-8") as fh:
                for p in pairs:
                    fh.write(json.dumps({k: p[k] for k in ("prompt", "chosen", "rejected")}, ensure_ascii=False) + "\n")
            summary[f"{name}_{split}"] = {**stats, "pairs": len(pairs)}
        shutil.copy(os.path.join(SRC, "dpo", "test.jsonl"), os.path.join(d, "test.jsonl"))
    json.dump(summary, open(os.path.join(OUT, "pairs_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))


def cmd_train(args):
    from experiments import run_all as R
    results = {}
    for name in ([args.only] if args.only else list(R.MODELS)):
        sft_dir = os.path.join(R.MODELS_DIR, f"worked_{name}_sft")
        runs = {
            f"onpolicy_b01_{name}_dpo": (os.path.join(OUT, name), 0.1),
            f"onpolicy_b05_{name}_dpo": (os.path.join(OUT, name), 0.5),
            f"offline_b05_{name}_dpo": (SRC, 0.5),
        }
        for tag, (data_dir, beta) in runs.items():
            dargs = R.dpo_args(data_dir)
            dargs[dargs.index("--beta") + 1] = str(beta)
            out_dir = os.path.join(R.MODELS_DIR, tag)
            R.train(sft_dir, dargs, out_dir)
            gen = os.path.join(R.EVAL_DIR, f"gen_{tag}.jsonl")
            ev = os.path.join(R.EVAL_DIR, f"eval_{tag}.json")
            R.generate(out_dir, gen)
            results[tag] = R.evaluate(gen, ev)
    json.dump(results, open(os.path.join(R.EVAL_DIR, "results_onpolicy_summary.json"), "w"), indent=2)
    print(json.dumps({k: v["answer_accuracy"] for k, v in results.items()}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["sample", "pairs", "train"])
    ap.add_argument("--only", choices=["general", "math"])
    a = ap.parse_args()
    {"sample": cmd_sample, "pairs": cmd_pairs, "train": cmd_train}[a.step](a)


if __name__ == "__main__":
    main()
