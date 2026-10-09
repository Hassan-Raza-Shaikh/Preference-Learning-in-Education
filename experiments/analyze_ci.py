#!/usr/bin/env python3
"""Confidence intervals for every condition and every key contrast.

Items are not independent: the 126 test items are 26 systems x their methods. So we
use a cluster bootstrap that resamples SYSTEMS (with replacement), and for contrasts a
PAIRED version (the same resampled systems for both conditions). Correctness uses the
exact same rule as evaluate.score(): parsed answer satisfies the system exactly.

Writes data/train/ci_results.json and prints a markdown table.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.evaluate import load_systems, parse_answer, satisfies  # noqa: E402

D = os.path.join(ROOT, "data", "train")
B = 10_000
SEED = 20261009

CONDS = {  # label -> gen-file stem (per model)
    "base": "{m}_base",
    "terse SFT (600)": "{m}_sft",
    "terse DPO": "{m}_dpo",
    "worked SFT (600)": "worked_{m}_sft",
    "worked DPO": "worked_{m}_dpo",
    "worked SFT (1500)": "worked1500_{m}_sft",
    "scaled-old SFT (1500)": "scaled_{m}_sft",
    "scaled-matched SFT (1500)": "scaledmatched_{m}_sft",
}
CONTRASTS = [  # (name, A, B)  -> reports A - B
    ("format: worked - terse (SFT@600)", "worked SFT (600)", "terse SFT (600)"),
    ("DPO - SFT (terse)", "terse DPO", "terse SFT (600)"),
    ("DPO - SFT (worked)", "worked DPO", "worked SFT (600)"),
    ("steps: 1500 - 600 (worked)", "worked SFT (1500)", "worked SFT (600)"),
    ("volume, mismatched: scaled-old - worked (@1500)", "scaled-old SFT (1500)", "worked SFT (1500)"),
    ("volume, matched: scaled-matched - worked (@1500)", "scaled-matched SFT (1500)", "worked SFT (1500)"),
    ("distribution: matched - old (@1500)", "scaled-matched SFT (1500)", "scaled-old SFT (1500)"),
    ("best SFT - base", "worked SFT (1500)", "base"),
]


def per_system(gen_path, sysmap, order):
    """Return (correct[s], n[s]) arrays over systems in `order`, or None if incomplete."""
    corr = {pid: 0 for pid in order}
    cnt = {pid: 0 for pid in order}
    for line in open(gen_path, encoding="utf-8"):
        g = json.loads(line)
        pid = g["problem_id"]
        if pid not in sysmap:
            continue
        vars_, A, b = sysmap[pid]
        ans = parse_answer(g.get("output", ""))
        cnt[pid] += 1
        corr[pid] += int(bool(ans) and satisfies(A, b, vars_, ans))
    return np.array([corr[p] for p in order]), np.array([cnt[p] for p in order])


def main():
    sysmap = load_systems()
    order = sorted(sysmap)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(order), size=(B, len(order)))   # shared draws -> paired
    out = {}
    lines = []
    for m in ("general", "math"):
        data = {}
        for label, stem in CONDS.items():
            p = os.path.join(D, f"gen_{stem.format(m=m)}.jsonl")
            if not os.path.exists(p):
                continue
            c, n = per_system(p, sysmap, order)
            if n.sum() < 120:          # generation still in progress
                continue
            data[label] = (c, n)
        res = {"conditions": {}, "contrasts": {}}
        lines.append(f"\n### {m} model\n")
        lines.append("| condition | acc | 95% CI |")
        lines.append("|---|---|---|")
        for label, (c, n) in data.items():
            boot = c[idx].sum(1) / n[idx].sum(1)
            lo, hi = np.percentile(boot, [2.5, 97.5])
            res["conditions"][label] = {"acc": c.sum() / n.sum(), "ci": [lo, hi], "n_items": int(n.sum())}
            lines.append(f"| {label} | {c.sum()/n.sum():.3f} | [{lo:.3f}, {hi:.3f}] |")
        lines.append("")
        lines.append("| contrast | diff | 95% CI | CI excludes 0? |")
        lines.append("|---|---|---|---|")
        for name, a, bb in CONTRASTS:
            if a not in data or bb not in data:
                continue
            (ca, na), (cb, nb) = data[a], data[bb]
            assert (na == nb).all(), f"item sets differ for {a} vs {bb}"
            diff = ca.sum() / na.sum() - cb.sum() / nb.sum()
            boot = ca[idx].sum(1) / na[idx].sum(1) - cb[idx].sum(1) / nb[idx].sum(1)
            lo, hi = np.percentile(boot, [2.5, 97.5])
            sig = "yes" if (lo > 0 or hi < 0) else "no"
            res["contrasts"][name] = {"diff": diff, "ci": [lo, hi], "excludes_zero": sig == "yes"}
            lines.append(f"| {name} | {diff:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {sig} |")
        out[m] = res
    json.dump(out, open(os.path.join(D, "ci_results.json"), "w"), indent=2, default=float)
    print("\n".join(lines))
    print(f"\n(cluster bootstrap over {len(order)} test systems, B={B}, seed={SEED})")


if __name__ == "__main__":
    main()
