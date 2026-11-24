#!/usr/bin/env python3
"""Track A item A1, part 1: describe how the Phase 1 DPO preference pairs differ.

Runs without a GPU. It measures the pairs; it does NOT establish why DPO hurt. That
needs the training runs in experiments/onpolicy_dpo.py (Apple Silicon).

For each pair (chosen, rejected) it reports:
  * shared prefix: share of the rejected text that is identical to the start of chosen
  * length: rejected/chosen characters and steps
  * surface shortcuts: simple rules that separate chosen from rejected WITHOUT checking
    any maths (e.g. "the longer one is chosen", "the one ending in 'Solution:' is chosen").
    If a rule reaches ~100%, a model can lower the DPO loss by learning that rule.
  * on-policy gap: rejected texts are built by the generator, not sampled from the model,
    so their wording is fixed ("Therefore the solution is ..."); reported as a phrase count.

Writes data/<dir>/dpo_pair_diagnostics.json for each dataset.
"""
import json
import os
import re
import statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = {"terse": "data/train/dpo/train.jsonl", "worked": "data/train_worked/dpo/train.jsonl"}


def shared_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def steps(text):
    return [l for l in text.splitlines() if re.match(r"\d+\. ", l)]


def analyse(path):
    pairs = [json.loads(l) for l in open(path, encoding="utf-8")]
    pre, lratio, sratio = [], [], []
    rules = {"longer_is_chosen": 0, "more_steps_is_chosen": 0,
             "ends_with_'Solution:'_is_chosen": 0, "rejected_is_chosen_prefix_plus_one_line": 0}
    phrase = 0
    for p in pairs:
        c, r = p["chosen"], p["rejected"]
        pre.append(shared_prefix(c, r) / max(1, len(r)))
        lratio.append(len(r) / len(c))
        sratio.append(len(steps(r)) / max(1, len(steps(c))))
        rules["longer_is_chosen"] += len(c) > len(r)
        rules["more_steps_is_chosen"] += len(steps(c)) > len(steps(r))
        last_c, last_r = c.strip().splitlines()[-1], r.strip().splitlines()[-1]
        rules["ends_with_'Solution:'_is_chosen"] += ("Solution:" in last_c) and ("Solution:" not in last_r)
        rules["rejected_is_chosen_prefix_plus_one_line"] += c.startswith("\n".join(r.splitlines()[:-1]))
        phrase += "Therefore the solution is" in r
    n = len(pairs)
    q = lambda xs: {"mean": round(st.mean(xs), 3), "min": round(min(xs), 3), "max": round(max(xs), 3)}
    return {"pairs": n, "shared_prefix_share_of_rejected": q(pre), "length_ratio_rejected_over_chosen": q(lratio),
            "step_ratio_rejected_over_chosen": q(sratio),
            "surface_rule_accuracy": {k: round(v / n, 3) for k, v in rules.items()},
            "rejected_using_fixed_phrase_'Therefore the solution is'": round(phrase / n, 3)}


def main():
    out = {}
    for name, rel in SETS.items():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"skip {name}: {rel} missing (run experiments/prepare_data.py first)")
            continue
        out[name] = analyse(path)
        json.dump(out[name], open(os.path.join(os.path.dirname(os.path.dirname(path)), "dpo_pair_diagnostics.json"), "w"),
                  indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
