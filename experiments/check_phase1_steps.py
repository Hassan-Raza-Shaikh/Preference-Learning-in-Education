#!/usr/bin/env python3
"""Run the tutor's step-level check (tutor/bank.py:check_steps) on the Phase 1 TRAINING
TARGETS: every equation displayed in every worked/terse solution must hold at the true
solution (Cramer determinants are checked against det(A)).

Phase 1 verified only final answers (plus irrational-artifact screening). This extends the
guarantee to intermediate steps, for paper P1. Writes data/<set>/step_check.json.

    python -m experiments.check_phase1_steps
"""
import json
import os
import sys
from collections import Counter

import sympy as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from oatutor_extract.multimethod import extract_system, system_of  # noqa: E402
from tutor.bank import check_steps  # noqa: E402

SETS = ["multimethod", "multimethod_worked", "multimethod_worked_synth", "multimethod_worked_synth_matched"]


def run(name):
    path = os.path.join(ROOT, "data", name, "systems_multimethod.jsonl")
    if not os.path.exists(path):
        return None
    c, fails = Counter(), []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        eqs = extract_system(" ".join(e if e.startswith("$$") else f"$${e}$$" for e in r["system"]["equations_tex"]))
        vars_, A, b = system_of(eqs)
        ref = list(A.LUsolve(b))
        for m in r["methods"]:
            ok, unc, f = check_steps(m["steps"], vars_, ref, detA=A.det())
            c["solutions"] += 1
            c["equations_checked"] += ok
            c["equations_unchecked"] += unc
            if f:
                c["solutions_with_failure"] += 1
                fails.append({"problem_id": r["source"]["problem_id"], "method": m["method"], "blocks": f})
    out = {**c, "failures": fails[:50]}
    json.dump(out, open(os.path.join(ROOT, "data", name, "step_check.json"), "w"), indent=2)
    return out


if __name__ == "__main__":
    for s in SETS:
        r = run(s)
        print(s, "missing" if r is None else {k: v for k, v in r.items() if k != "failures"})
