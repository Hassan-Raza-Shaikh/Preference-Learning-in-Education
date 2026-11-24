#!/usr/bin/env python3
"""Track A item A5: do real textbook systems have cleaner intermediate arithmetic?

Phase 1 hypothesis (RESULTS.md §6): synthetic data matched on marginal statistics still
misses the "joint structure" of curated systems, whose intermediate arithmetic stays
clean. Measured here before generating any new data.

"Clean" = the substitution and elimination worked steps introduce no fraction that is
not already in the equations or the final answer.

Result on 2026-11-03: real train 29/75 = 0.387 clean; distribution-matched synthetic
297/746 = 0.398 clean. The two are essentially the same, so this form of the
hypothesis is NOT supported, and a clean-only synthetic set would move away from the
real distribution. (Other forms of "joint structure" remain untested.)
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FR = re.compile(r"\\frac\{-?\d+\}\{\d+\}")


def extra_fractions(mm):
    allowed = set(FR.findall(" ".join(mm["system"]["equations_tex"]) + mm["system"]["reference_solution"]))
    return sum(len(set(FR.findall(s)) - allowed)
               for m in mm["methods"] if m["method"] in ("substitution", "elimination") for s in m["steps"])


def clean_share(path, only_ids=None):
    n = clean = 0
    for line in open(path, encoding="utf-8"):
        mm = json.loads(line)
        if only_ids is not None and mm["source"]["problem_id"] not in only_ids:
            continue
        if not any(m["method"] in ("substitution", "elimination") for m in mm["methods"]):
            continue
        n += 1
        clean += extra_fractions(mm) == 0
    return {"systems": n, "clean": clean, "share": round(clean / n, 3) if n else None}


def main():
    train = set(json.load(open(os.path.join(ROOT, "data", "train_worked", "split_manifest.json")))["system_ids"]["train"])
    out = {"real_train": clean_share(os.path.join(ROOT, "data", "multimethod_worked", "systems_multimethod.jsonl"), train)}
    for name in ("multimethod_worked_synth", "multimethod_worked_synth_matched"):
        p = os.path.join(ROOT, "data", name, "systems_multimethod.jsonl")
        if os.path.exists(p):
            out[name] = clean_share(p)
    json.dump(out, open(os.path.join(ROOT, "data", "train_worked", "intermediate_stats.json"), "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
