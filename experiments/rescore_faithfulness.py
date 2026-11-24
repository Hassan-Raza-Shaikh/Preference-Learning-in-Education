#!/usr/bin/env python3
"""Track A item A2, part 2: re-score existing Phase 1 generations with the structural check,
and export a sample for HAND-LABELLING (the check was only validated on gold solutions).

Needs the generation files data/train/gen_*.jsonl, which are git-ignored and exist only on
the machine that ran the experiments.

  python -m experiments.rescore_faithfulness                 # table + data/train/faithfulness_rescored.json
  python -m experiments.rescore_faithfulness --sample 60     # + data/train/faithfulness_label_sample.csv

Hand-label the CSV's `human_faithful` column (1/0) without looking at the verdict columns
(hide them in the spreadsheet), then:
  python -m experiments.rescore_faithfulness --agreement data/train/faithfulness_label_sample.csv
"""
import argparse
import csv
import glob
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.evaluate import faithful as keyword_faithful, load_systems  # noqa: E402
from experiments.faithfulness import check  # noqa: E402

D = os.path.join(ROOT, "data", "train")


def rescore():
    sysmap = load_systems()
    out, rows = {}, []
    for path in sorted(glob.glob(os.path.join(D, "gen_*.jsonl"))):
        cond = os.path.basename(path)[4:-6]
        n = s_ok = k_ok = 0
        for line in open(path, encoding="utf-8"):
            g = json.loads(line)
            if g["problem_id"] not in sysmap:
                continue
            vars_, A, b = sysmap[g["problem_id"]]
            s, ev = check(g["method"], g.get("output", ""), vars_, A, b)
            k = keyword_faithful(g["method"], g.get("output", ""))
            n += 1
            s_ok += s
            k_ok += k
            rows.append({"condition": cond, "problem_id": g["problem_id"], "method": g["method"],
                         "output": g.get("output", ""), "structural": int(s), "keyword": int(k), "evidence": ev})
        if n:
            out[cond] = {"n": n, "structural_faithfulness": round(s_ok / n, 3), "keyword_faithfulness": round(k_ok / n, 3)}
    return out, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--agreement")
    a = ap.parse_args()
    if a.agreement:
        rows = [r for r in csv.DictReader(open(a.agreement)) if r["human_faithful"].strip() in ("0", "1")]
        for col in ("structural", "keyword"):
            agree = sum(r[col] == r["human_faithful"].strip() for r in rows)
            print(f"{col}: agrees with human on {agree}/{len(rows)} = {agree / max(1, len(rows)):.3f}")
        return
    table, rows = rescore()
    if not table:
        sys.exit("no data/train/gen_*.jsonl files found: run this on the machine that ran Phase 1")
    json.dump(table, open(os.path.join(D, "faithfulness_rescored.json"), "w"), indent=2)
    print(json.dumps(table, indent=2))
    if a.sample:
        rng = random.Random(20261103)
        # stratify: half where the two checks disagree (most informative), half random
        dis = [r for r in rows if r["structural"] != r["keyword"]]
        pick = rng.sample(dis, min(len(dis), a.sample // 2))
        rest = [r for r in rows if r not in pick]
        pick += rng.sample(rest, min(len(rest), a.sample - len(pick)))
        rng.shuffle(pick)
        path = os.path.join(D, "faithfulness_label_sample.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["condition", "problem_id", "method", "output", "human_faithful",
                                               "structural", "keyword", "evidence"])
            w.writeheader()
            for r in pick:
                w.writerow({**r, "human_faithful": ""})
        print("wrote", path)


if __name__ == "__main__":
    main()
