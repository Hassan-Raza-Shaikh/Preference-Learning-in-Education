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


def build_pools(root):
    """Empirical pools from the REAL TRAIN split only (never valid/test)."""
    from oatutor_extract.multimethod import extract_system, system_of, reference_solution
    train = set(json.load(open(os.path.join(root, "data", "train_worked", "split_manifest.json")))
                ["system_ids"]["train"])
    coefs, consts, int_sols = [], [], []
    n2 = n3 = n_frac = 0
    for line in open(os.path.join(root, "data", "multimethod_worked", "systems_multimethod.jsonl")):
        r = json.loads(line)
        if r["source"]["problem_id"] not in train:
            continue
        eqs = extract_system(" ".join("$$" + e + "$$" for e in r["system"]["equations_tex"]))
        vars_, A, b = system_of(eqs)
        n2 += len(vars_) == 2
        n3 += len(vars_) == 3
        coefs += [A[i, j] for i in range(A.rows) for j in range(A.cols)]
        consts += list(b)
        ref = reference_solution(vars_, A, b)
        if all(v.is_Integer for v in ref):
            int_sols += [int(v) for v in ref]
        else:
            n_frac += 1
    return {"coefs": coefs, "consts": consts, "int_sols": int_sols,
            "p2": n2 / (n2 + n3), "frac_share": n_frac / (n2 + n3)}


def make_record_matched(rng, idx, pools, want_frac, max_den=10):
    """Synthetic system whose coefficients/constants are bootstrapped from the real train
    pools. want_frac selects a fractional-solution (denominator <= max_den) or an
    integer-solution system, so the overall fractional share can be held at the real value."""
    nvars = 2 if rng.random() < pools["p2"] else 3
    vars_ = ["x", "y", "z"][:nvars]
    for _ in range(2000):
        A = sp.Matrix(nvars, nvars, lambda i, j: rng.choice(pools["coefs"]))
        if A.det() == 0:
            continue
        if any(all(A[i, j] == 0 for i in range(nvars)) for j in range(nvars)):
            continue
        if want_frac:
            b = sp.Matrix([rng.choice(pools["consts"]) for _ in range(nvars)])
            sol = list(A.LUsolve(b))   # exact Rationals (pools are exact)
            if not all(s.is_Rational for s in sol):
                continue
            if all(s.is_Integer for s in sol) or max(s.q for s in sol) > max_den:
                continue
        else:
            sol = [rng.choice(pools["int_sols"]) for _ in range(nvars)]
            b = A * sp.Matrix(sol)
        eqs = [f"$${lin([A[i, j] for j in range(nvars)], vars_, b[i])}$$" for i in range(nvars)]
        return {
            "source": {"dataset": "synthetic-matched", "problem_id": f"synthm{idx}",
                       "repo": "generated", "path": "synthetic"},
            "provenance": {"oer": "synthetic (distribution-matched to real train split)",
                           "oer_url": None, "license": "generated", "license_url": None},
            "taxonomy": {"course": "synthetic", "lesson_id": None, "lesson": "synthetic",
                         "subject": "algebra", "topic": "systems_of_equations",
                         "method": [], "skills": [], "language": "en"},
            "steps": [{"question": "  ".join(eqs)}],
        }
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1200, help="number of synthetic systems to emit")
    ap.add_argument("--target-examples", type=int, default=None,
                    help="stop once this many SFT examples are emitted (overrides --n)")
    ap.add_argument("--match-real", action="store_true",
                    help="bootstrap coefficients/constants from the real train split and "
                         "hold the real fractional-solution share")
    ap.add_argument("--seed", type=int, default=20260911)
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--out-name", default="multimethod_worked_synth")
    args = ap.parse_args()

    out = os.path.join(args.out_dir, args.out_name)
    os.makedirs(out, exist_ok=True)
    rng = random.Random(args.seed)
    pools = build_pools(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) if args.match_real else None
    stats = Counter()
    n_mm = n_sft = n_pref = n_frac = 0
    idx = 0

    def done():
        if args.target_examples is not None:
            return n_sft >= args.target_examples
        return n_mm >= args.n

    with open(os.path.join(out, "systems_multimethod.jsonl"), "w", encoding="utf-8") as fmm, \
         open(os.path.join(out, "sft_multimethod.jsonl"), "w", encoding="utf-8") as fsft, \
         open(os.path.join(out, "preference_pairs.jsonl"), "w", encoding="utf-8") as fpref:
        while not done():
            idx += 1
            if pools:
                want_frac = n_frac < pools["frac_share"] * (n_mm + 1)
                rec = make_record_matched(rng, idx, pools, want_frac)
            else:
                want_frac = False
                rec = make_record(rng, idx)
            if rec is None:
                continue
            mm, pairs, st = worked.build(rec)
            stats.update(st)
            if not mm:
                continue
            n_frac += "\\frac" in mm["system"]["reference_solution"]
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
    manifest = {"synthetic": True, "matched_to_real_train": bool(pools),
                "n_systems": n_mm, "n_sft_examples": n_sft,
                "n_preference_pairs": n_pref, "seed": args.seed,
                "fractional_solution_share": round(n_frac / max(n_mm, 1), 3),
                "target_fractional_share": round(pools["frac_share"], 3) if pools else None,
                "verified_by_method": {k.split(':', 1)[1]: v for k, v in stats.items() if k.startswith('verified:')}}
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
