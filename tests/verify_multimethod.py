#!/usr/bin/env python3
"""INDEPENDENT re-verification of the multi-method dataset.

Does not trust the generator. Re-derives the truth from scratch and cross-checks with
multiple independent methods:

  A. equations_tex round-trip: parse the stored equations, solve them THREE ways
     (sympy.linsolve, sympy.solve, numpy float lstsq) and require agreement.
  B. Provenance: the stored system must match the ORIGINAL OATutor question
     (re-parsed independently from oatutor_systems.jsonl by problem_id).
  C. Every method's final_answer must (i) equal the reference and (ii) satisfy every
     original equation by exact substitution.
  D. Every preference pair: chosen answer MUST satisfy the system; rejected answer
     MUST NOT. Chosen and rejected must differ.

Exit code 0 only if ZERO failures.
"""
import json
import os
import re
import sys

import numpy as np
import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oatutor_extract.multimethod import extract_system, system_of, SYMS  # noqa: E402

x, y, z = SYMS['x'], SYMS['y'], SYMS['z']
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MM = os.path.join(DATA, "multimethod", "systems_multimethod.jsonl")
PREF = os.path.join(DATA, "multimethod", "preference_pairs.jsonl")
SYS = os.path.join(DATA, "oatutor_systems.jsonl")

ANS = re.compile(r'([xyz])\s*=\s*(-?\\frac\{-?\d+\}\{-?\d+\}|-?\d+)')


def parse_answer(text):
    """Parse 'x=..., y=...' (LaTeX fractions ok) into {var: Rational}."""
    out = {}
    for var, val in ANS.findall(text):
        m = re.match(r'(-?)\\frac\{(-?\d+)\}\{(-?\d+)\}', val)
        if m:
            sign = -1 if m.group(1) == '-' else 1
            out[var] = sign * sp.Rational(int(m.group(2)), int(m.group(3)))
        else:
            out[var] = sp.Rational(int(val))
    return out


def solve_three_ways(vars_, A, b):
    """Return exact solution list, requiring linsolve == solve == numpy(float)."""
    ls = sp.linsolve((A, b), *vars_)
    if len(ls) != 1:
        return None
    p1 = list(list(ls)[0])
    if any(t.free_symbols for t in p1):
        return None
    eqs = [sp.Eq(sum(A[i, j] * vars_[j] for j in range(A.cols)), b[i]) for i in range(A.rows)]
    s2 = sp.solve(eqs, vars_, dict=True)
    if len(s2) != 1:
        return None
    p2 = [sp.nsimplify(s2[0][v]) for v in vars_]
    if any(sp.simplify(p1[i] - p2[i]) != 0 for i in range(len(vars_))):
        return None
    # numpy float cross-check
    An = np.array([[float(A[i, j]) for j in range(A.cols)] for i in range(A.rows)])
    bn = np.array([float(b[i]) for i in range(A.rows)])
    try:
        pn = np.linalg.solve(An, bn)
        if any(abs(float(p1[i]) - pn[i]) > 1e-6 for i in range(len(vars_))):
            return None
    except np.linalg.LinAlgError:
        return None
    return p1


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


def main():
    failures = []
    checks = 0

    # index original questions by problem_id
    original = {}
    for line in open(SYS, encoding="utf-8"):
        r = json.loads(line)
        original[r["source"]["problem_id"]] = r["steps"][0]["question"] if r["steps"] else ""

    mm = [json.loads(l) for l in open(MM, encoding="utf-8")]
    for rec in mm:
        pid = rec["source"]["problem_id"]
        vars_ = sp.symbols(" ".join(rec["system"]["variables"]))
        vars_ = list(vars_) if isinstance(vars_, tuple) else [vars_]

        # A. round-trip on stored equations
        eqs = extract_system(" ".join(rec["system"]["equations_tex"]))
        si = system_of(eqs)
        if si is None:
            failures.append(f"{pid}: stored equations_tex did not re-parse to a well-formed system")
            continue
        rvars, A, b = si
        ref = solve_three_ways(rvars, A, b)
        checks += 1
        if ref is None:
            failures.append(f"{pid}: stored system not uniquely solvable under 3 independent solvers")
            continue
        refmap = {str(v): ref[i] for i, v in enumerate(rvars)}

        # B. provenance: original OATutor question yields the same system/solution
        oeqs = extract_system(original.get(pid, ""))
        osi = system_of(oeqs)
        checks += 1
        if osi is None:
            failures.append(f"{pid}: ORIGINAL question no longer parses (provenance mismatch)")
        else:
            ovars, oA, ob = osi
            oref = solve_three_ways(ovars, oA, ob)
            if oref is None or {str(v): oref[i] for i, v in enumerate(ovars)} != refmap:
                failures.append(f"{pid}: stored system solution != original question solution")

        # stored reference string must match recomputed reference
        stored_ref = parse_answer(rec["system"]["reference_solution"])
        checks += 1
        if any(sp.simplify(stored_ref.get(str(v), sp.nan) - ref[i]) != 0 for i, v in enumerate(rvars)):
            failures.append(f"{pid}: stored reference_solution != independently recomputed solution")

        # C. every method
        for meth in rec["methods"]:
            checks += 1
            ans = parse_answer(meth["final_answer"])
            if any(sp.simplify(ans.get(str(v), sp.nan) - ref[i]) != 0 for i, v in enumerate(rvars)):
                failures.append(f"{pid}/{meth['method']}: final_answer != reference")
            if not satisfies(A, b, rvars, ans):
                failures.append(f"{pid}/{meth['method']}: final_answer does not satisfy the equations")

    # D. preference pairs
    pref = [json.loads(l) for l in open(PREF, encoding="utf-8")]
    for i, p in enumerate(pref):
        pid = p["meta"]["problem_id"]
        eqs = extract_system(" ".join(re.findall(r'\$\$.+?\$\$', p["prompt"])))
        si = system_of(eqs)
        if si is None:
            failures.append(f"pref[{i}] {pid}: prompt system unparseable")
            continue
        rvars, A, b = si
        chosen = parse_answer(p["meta"]["correct_answer"])
        rejected = parse_answer(p["meta"]["rejected_answer"])
        checks += 2
        if not satisfies(A, b, rvars, chosen):
            failures.append(f"pref[{i}] {pid}: CHOSEN answer does not satisfy the system")
        if satisfies(A, b, rvars, rejected):
            failures.append(f"pref[{i}] {pid}: REJECTED answer actually satisfies the system (not wrong!)")
        if chosen == rejected:
            failures.append(f"pref[{i}] {pid}: chosen == rejected")
        # the answer strings must actually appear in the respective texts
        if p["meta"]["correct_answer"] not in p["chosen"]:
            failures.append(f"pref[{i}] {pid}: correct answer not present in chosen text")
        if p["meta"]["rejected_answer"] not in p["rejected"]:
            failures.append(f"pref[{i}] {pid}: rejected answer not present in rejected text")

    print(f"systems checked: {len(mm)}   preference pairs checked: {len(pref)}")
    print(f"total assertions run: {checks}")
    if failures:
        print(f"\nFAILURES: {len(failures)}")
        for f in failures[:50]:
            print("  -", f)
        sys.exit(1)
    print("\nALL INDEPENDENT CHECKS PASSED (0 failures)")
    sys.exit(0)


if __name__ == "__main__":
    main()
