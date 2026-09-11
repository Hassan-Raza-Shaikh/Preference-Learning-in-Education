#!/usr/bin/env python3
"""Build the scaled SFT training set: real worked train + synthetic worked systems.

valid/test are copied unchanged from data/train_worked (the real held-out systems),
so the scaling comparison uses the identical evaluation set. Includes a contamination
check ensuring no synthetic system coincides with a valid/test system.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.prepare_data import (  # noqa: E402
    METHOD_NAME, SYSTEM_INSTR, build_prompt, system_block_from_prompt,
)

WORKED = os.path.join(ROOT, "data", "train_worked")
SYNTH = os.path.join(ROOT, "data", "multimethod_worked_synth", "sft_multimethod.jsonl")
OUT = os.path.join(ROOT, "data", "train_scaled")


def sys_signature(prompt_block):
    """Normalized set of equation strings, for contamination checks."""
    eqs = re.findall(r'\$\$(.+?)\$\$', prompt_block)
    return frozenset(re.sub(r'\s+', '', e) for e in eqs)


def to_messages(example):
    method = example["meta"]["method"]
    block = system_block_from_prompt(example["prompt"])
    user = build_prompt(method, block)
    return {"messages": [
        {"role": "system", "content": SYSTEM_INSTR.format(method=METHOD_NAME[method])},
        {"role": "user", "content": user},
        {"role": "assistant", "content": example["completion"]},
    ]}


def main():
    os.makedirs(os.path.join(OUT, "sft"), exist_ok=True)

    # held-out signatures (valid + test) from the real worked splits
    heldout = set()
    for split in ("valid", "test"):
        for line in open(os.path.join(WORKED, "sft", f"{split}.jsonl"), encoding="utf-8"):
            user = next(m["content"] for m in json.loads(line)["messages"] if m["role"] == "user")
            heldout.add(sys_signature(user))

    # copy real worked train, then append synthetic (skipping any contamination)
    train_out = os.path.join(OUT, "sft", "train.jsonl")
    n_real = n_synth = n_skip = 0
    with open(train_out, "w", encoding="utf-8") as fo:
        for line in open(os.path.join(WORKED, "sft", "train.jsonl"), encoding="utf-8"):
            fo.write(line); n_real += 1
        for line in open(SYNTH, encoding="utf-8"):
            ex = json.loads(line)
            if sys_signature(ex["prompt"]) in heldout:
                n_skip += 1
                continue
            fo.write(json.dumps(to_messages(ex), ensure_ascii=False) + "\n")
            n_synth += 1

    # copy valid/test unchanged
    for split in ("valid", "test"):
        shutil.copy(os.path.join(WORKED, "sft", f"{split}.jsonl"),
                    os.path.join(OUT, "sft", f"{split}.jsonl"))

    print(json.dumps({"train_real": n_real, "train_synth": n_synth,
                      "contamination_skipped": n_skip,
                      "train_total": n_real + n_synth}, indent=2))


if __name__ == "__main__":
    main()
