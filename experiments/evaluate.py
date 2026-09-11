#!/usr/bin/env python3
"""Automatic evaluation harness for the two-model experiment.

Scores model generations for (system, requested_method) with sympy — no LLM judge:
  * answer_correct   : final answer satisfies the ORIGINAL system (exact rational check)
  * method_faithful  : the worked solution actually uses the requested method
  * error_mode       : correct | wrong_answer | wrong_method | no_answer

Usage:
  # score a generations file: JSONL of {problem_id, method, output}
  python experiments/evaluate.py --generations path.jsonl
  # self-test the grader on gold completions (expect ~100%)
  python experiments/evaluate.py --selftest
"""
import argparse
import json
import os
import re
import sys

import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oatutor_extract.multimethod import extract_system, system_of, SYMS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_SYS = os.path.join(ROOT, "data", "train", "test_systems.jsonl")

ANS = re.compile(r'([xyz])\s*=\s*(-?\\frac\{-?\d+\}\{-?\d+\}|-?\d+/?-?\d*|-?\d+)')

# method signatures for faithfulness (requested method must appear; a competing
# method's signature appearing instead flags wrong_method)
SIGNATURE = {
    "substitution": r"substitut",
    "elimination": r"eliminat|add the equations|subtract the equations|add the two|subtract to",
    "graphing": r"slope|graph|intersect|y-intercept",
    "cramers_rule": r"cramer|determinant|d_\{?[xyz]|\\det|d_x|d_y|d_z",
    "inverse_matrix": r"inverse|a\^\{?-1|a\^-1|a\^\{-1\}",
    "gaussian_elimination": r"augmented|row.?reduc|echelon|rref|row operation",
}


def parse_answer(text):
    """Extract the model's stated final answer.

    Scans the whole text and keeps the LAST value stated for each variable
    (the final answer, after any intermediate lines). Robust to the many
    formats models use: `x=3`, `x = 3`, `\\(x = 3\\)`, `\\[x = 3\\]`,
    `$$x=3, y=1$$`, and values on separate lines.
    """
    out = {}
    for var, val in ANS.findall(text):
        m = re.match(r'(-?)\\frac\{(-?\d+)\}\{(-?\d+)\}', val)
        if m:
            sign = -1 if m.group(1) == '-' else 1
            out[var] = sign * sp.Rational(int(m.group(2)), int(m.group(3)))
        elif '/' in val:
            try:
                p, q = val.split('/'); out[var] = sp.Rational(int(p), int(q))
            except Exception:
                pass
        else:
            try:
                out[var] = sp.Rational(int(val))
            except Exception:
                pass
    return out


def satisfies(A, b, vars_, valmap):
    try:
        values = [valmap[str(v)] for v in vars_]
    except KeyError:
        return False
    for i in range(A.rows):
        lhs = sum(A[i, j] * values[j] for j in range(A.cols))
        if sp.simplify(lhs - b[i]) != 0:
            return False
    return True


def faithful(method, text):
    return re.search(SIGNATURE[method], text, re.I) is not None


def load_systems():
    sysmap = {}
    for line in open(TEST_SYS, encoding="utf-8"):
        r = json.loads(line)
        eqs = extract_system(" ".join(r["equations_tex"]))
        si = system_of(eqs)
        if si:
            sysmap[r["problem_id"]] = si   # (vars, A, b)
    return sysmap


def score(generations, sysmap):
    from collections import Counter, defaultdict
    n = 0
    correct = faithful_n = 0
    err = Counter()
    per_method = defaultdict(lambda: {"n": 0, "correct": 0, "faithful": 0})
    for g in generations:
        pid, method, out = g["problem_id"], g["method"], g.get("output", "")
        if pid not in sysmap:
            continue
        vars_, A, b = sysmap[pid]
        n += 1
        ans = parse_answer(out)
        ok = bool(ans) and satisfies(A, b, vars_, ans)
        ff = faithful(method, out)
        pm = per_method[method]; pm["n"] += 1
        if ok:
            correct += 1; pm["correct"] += 1
        if ff:
            faithful_n += 1; pm["faithful"] += 1
        if ok and ff:
            err["correct"] += 1
        elif not ans:
            err["no_answer"] += 1
        elif not ok:
            err["wrong_answer"] += 1
        else:
            err["wrong_method"] += 1
    return {
        "n": n,
        "answer_accuracy": round(correct / n, 4) if n else None,
        "method_faithfulness": round(faithful_n / n, 4) if n else None,
        "error_modes": dict(err),
        "per_method": {m: {"n": v["n"],
                           "acc": round(v["correct"] / v["n"], 3) if v["n"] else None,
                           "faithful": round(v["faithful"] / v["n"], 3) if v["n"] else None}
                       for m, v in sorted(per_method.items())},
    }


def selftest():
    """Feed the gold completions from sft_test back through the grader."""
    sysmap = load_systems()
    gens = []
    for line in open(os.path.join(ROOT, "data", "train", "sft", "test.jsonl"), encoding="utf-8"):
        msgs = json.loads(line)["messages"]
        user = next(m["content"] for m in msgs if m["role"] == "user")
        gold = next(m["content"] for m in msgs if m["role"] == "assistant")
        method = re.search(r"Method:\s*([a-z_]+)", gold)
        method = method.group(1) if method else None
        # recover problem_id by matching the equations to a test system
        pid = None
        eqblock = user.split("\n", 1)[1]
        for sid, (vars_, A, b) in sysmap.items():
            gg = extract_system(eqblock)
            si = system_of(gg)
            if si and si[1] == A and si[2] == b:
                pid = sid; break
        if pid and method:
            gens.append({"problem_id": pid, "method": method, "output": gold})
    print(f"self-test on {len(gens)} gold completions:")
    print(json.dumps(score(gens, sysmap), indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    sysmap = load_systems()
    gens = [json.loads(l) for l in open(args.generations, encoding="utf-8")]
    result = score(gens, sysmap)
    print(json.dumps(result, indent=2))
    if args.out:
        json.dump(result, open(args.out, "w"), indent=2)


if __name__ == "__main__":
    main()
