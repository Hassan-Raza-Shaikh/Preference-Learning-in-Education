#!/usr/bin/env python3
"""Generate solutions from an MLX model for the held-out test systems.

For each test system and each of its methods, build the same method-conditioned
prompt used in training and generate a solution. Writes JSONL of
{problem_id, method, output} for scoring by evaluate.py.

Usage:
  python experiments/generate.py --model mlx-community/Qwen2.5-1.5B-Instruct-bf16 \
      --out data/train/gen_general_base.jsonl
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments.prepare_data import METHOD_NAME, SYSTEM_INSTR, build_prompt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_SYS = os.path.join(ROOT, "data", "train", "test_systems.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="HF/MLX model id or local adapter-attached path")
    ap.add_argument("--adapter", default=None, help="optional LoRA adapter path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=512)
    args = ap.parse_args()

    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(args.model, adapter_path=args.adapter)
    sampler = make_sampler(temp=0.0)   # greedy: deterministic, reproducible

    systems = [json.loads(l) for l in open(TEST_SYS, encoding="utf-8")]
    n = 0
    with open(args.out, "w", encoding="utf-8") as fh:
        for s in systems:
            block = "  ".join(s["equations_tex"])
            for method in s["methods"]:
                user = build_prompt(method, block)
                messages = [
                    {"role": "system", "content": SYSTEM_INSTR.format(method=METHOD_NAME[method])},
                    {"role": "user", "content": user},
                ]
                prompt = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True, tokenize=False
                )
                out = generate(model, tokenizer, prompt=prompt,
                               max_tokens=args.max_tokens, sampler=sampler, verbose=False)
                fh.write(json.dumps({"problem_id": s["problem_id"], "method": method,
                                     "output": out}, ensure_ascii=False) + "\n")
                n += 1
                if n % 20 == 0:
                    print(f"  ...{n} generations", flush=True)
    print(f"wrote {n} generations to {args.out}")


if __name__ == "__main__":
    main()
