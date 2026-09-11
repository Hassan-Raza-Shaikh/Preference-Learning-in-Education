#!/usr/bin/env python3
"""Synthesize fresh, verified linear systems to scale the worked-solution dataset.

Each system is built from a KNOWN integer solution (so the answer is certain), then
run through the SAME verified worked-solution generators (oatutor_extract.worked).
Every emitted method is sympy-checked; nothing unverified is written. These are
synthetic *questions* (clearly labelled) used only for training — the held-out test
set stays the real OATutor systems.

Output: data/multimethod_worked_synth/{systems_multimethod,sft_multimethod,preference_pairs}.jsonl
"""
import argparse
import json
import os
import random
from collections import Counter

import sympy as sp

from oatutor_extract import worked
from oatutor_extract.worked import lin


def make_record(rng, idx, coeff=6, sol=8):
    """Build a synthetic OATutor-shaped record with a known unique solution."""
    nvars = 2 if rng.random() < 0.6 else 3
    vars_ = ["x", "y", "z"][:nvars]
    for _ in range(200):
        solution = [rng.randint(-sol, sol) for _ in range(nvars)]
        A = sp.Matrix([[rng.randint(-coeff, coeff) for _ in range(nvars)] for _ in range(nvars)])
        if A.det() == 0:
            continue
        # every variable must appear in at least one equation
        if any(all(A[i, j] == 0 for i in range(nvars)) for j in range(nvars)):
            continue
        b = A * sp.Matrix(solution)
        eqs = [f"$${lin([A[i, j] for j in range(nvars)], vars_, b[i])}$$" for i in range(nvars)]
        return {
            "source": {"dataset": "synthetic", "problem_id": f"synth{idx}",
                       "repo": "generated", "path": "synthetic"},
            "provenance": {"oer": "synthetic (generated)", "oer_url": None,
                           "license": "generated", "license_url": None},
            "taxonomy": {"course": "synthetic", "lesson_id": None, "lesson": "synthetic",
                         "subject": "algebra", "topic": "systems_of_equations",
                         "method": [], "skills": [], "language": "en"},
            "steps": [{"question": "  ".join(eqs)}],
        }
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200, help="number of synthetic systems to emit")
    ap.add_argument("--seed", type=int, default=20260911)
    ap.add_argument("--out-dir", default="data")
    args = ap.parse_args()

    out = os.path.join(args.out_dir, "multimethod_worked_synth")
    os.makedirs(out, exist_ok=True)
    rng = random.Random(args.seed)
    stats = Counter()
    n_mm = n_sft = n_pref = 0
    idx = 0
    with open(os.path.join(out, "systems_multimethod.jsonl"), "w", encoding="utf-8") as fmm, \
         open(os.path.join(out, "sft_multimethod.jsonl"), "w", encoding="utf-8") as fsft, \
         open(os.path.join(out, "preference_pairs.jsonl"), "w", encoding="utf-8") as fpref:
        while n_mm < args.n:
            idx += 1
            rec = make_record(rng, idx)
            if rec is None:
                continue
            mm, pairs, st = worked.build(rec)
            stats.update(st)
            if not mm:
                continue
            fmm.write(json.dumps(mm, ensure_ascii=False, sort_keys=True) + "\n"); n_mm += 1
            for meth in mm["methods"]:
                completion = (f"Method: {meth['method']}\n"
                              + "\n".join(f"{i+1}. {s}" for i, s in enumerate(meth["steps"]))
                              + f"\nSolution: $${meth['final_answer']}$$.")
                fsft.write(json.dumps({"prompt": mm["prompt"], "completion": completion,
                                       "meta": {"problem_id": mm["source"]["problem_id"],
                                                "method": meth["method"]}}, ensure_ascii=False) + "\n")
                n_sft += 1
            for p in pairs:
                fpref.write(json.dumps(p, ensure_ascii=False) + "\n"); n_pref += 1
    manifest = {"synthetic": True, "n_systems": n_mm, "n_sft_examples": n_sft,
                "n_preference_pairs": n_pref, "seed": args.seed,
                "verified_by_method": {k.split(':', 1)[1]: v for k, v in stats.items() if k.startswith('verified:')}}
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
