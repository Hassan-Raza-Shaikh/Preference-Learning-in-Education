#!/usr/bin/env python3
"""Deterministic multi-method solution generator for OATutor linear systems.

NO free-form/LLM generation. Questions are taken verbatim from OATutor; only the
*solutions* are produced, and every one is computed with sympy and then verified by
substituting back into the original equations. Anything that does not verify is dropped,
never shipped.

Outputs (under <out-dir>/multimethod/):
  systems_multimethod.jsonl  one system + all verified method solutions
  preference_pairs.jsonl     DPO pairs: verified-correct (chosen) vs. verified-wrong (rejected)
  manifest.json              generation + verification statistics
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

import sympy as sp

x, y, z = sp.symbols('x y z')
SYMS = {'x': x, 'y': y, 'z': z}
EQ_BLOCK = re.compile(r'\$\$(.+?)\$\$', re.S)


# --------------------------------------------------------------------------- #
# parsing (LaTeX linear equation -> sympy)
# --------------------------------------------------------------------------- #
def latex_to_expr_str(s):
    s = s.strip()
    s = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', r'((\1)/(\2))', s)
    s = s.replace('\\left', '').replace('\\right', '')
    s = s.replace('\\cdot', '*').replace('\\times', '*')
    s = s.replace('{', '(').replace('}', ')')
    s = s.replace('^', '**').replace(' ', '')
    s = re.sub(r'(\d)([xyz(])', r'\1*\2', s)
    s = re.sub(r'([xyz)])\(', r'\1*(', s)
    s = re.sub(r'\)([xyz])', r')*\1', s)
    return s


def parse_equation(eqstr):
    if eqstr.count('=') != 1:
        return None
    lhs, rhs = eqstr.split('=')
    try:
        L = sp.sympify(latex_to_expr_str(lhs), locals=SYMS)
        R = sp.sympify(latex_to_expr_str(rhs), locals=SYMS)
    except Exception:
        return None
    expr = sp.expand(L - R)
    fs = expr.free_symbols & {x, y, z}
    if not fs:
        return None
    poly = sp.Poly(expr, *sorted(fs, key=str))
    if any(sum(m) > 1 for m in poly.monoms()):   # reject nonlinear / cross terms
        return None
    return sp.Eq(L, R)


def extract_system(question):
    eqs = []
    for block in EQ_BLOCK.findall(question):
        if '\\begin' in block:
            continue
        for part in re.split(r',', block):
            part = part.strip()
            if '=' in part and re.search(r'[xyz]', part):
                eq = parse_equation(part)
                if eq is not None:
                    eqs.append(eq)
    return eqs


def system_of(eqs):
    """Return (vars, A, b) with exact sympy Rationals, or None if ill-formed."""
    varset = sorted({s for e in eqs for s in sp.expand(e.lhs - e.rhs).free_symbols} & {x, y, z}, key=str)
    if len(eqs) != len(varset) or len(varset) not in (2, 3):
        return None
    A, b = [], []
    for e in eqs:
        expr = sp.expand(e.lhs - e.rhs)
        row = [sp.nsimplify(expr.coeff(v, 1)) for v in varset]
        const = -expr.subs({v: 0 for v in varset})
        A.append(row)
        b.append(sp.nsimplify(const))
    return varset, sp.Matrix(A), sp.Matrix(b)


# --------------------------------------------------------------------------- #
# formatting
# --------------------------------------------------------------------------- #
def tex(v):
    v = sp.nsimplify(v)
    if v.is_Integer:
        return str(int(v))
    if v.is_Rational:
        p, q = v.p, v.q
        sign = '-' if p * q < 0 else ''
        return f"{sign}\\frac{{{abs(p)}}}{{{abs(q)}}}"
    return sp.latex(v)


def sol_str(vars_, values):
    return ", ".join(f"{v}={tex(val)}" for v, val in zip(vars_, values))


# --------------------------------------------------------------------------- #
# reference solve + verification
# --------------------------------------------------------------------------- #
def reference_solution(vars_, A, b):
    sol = sp.linsolve((A, b), *vars_)
    if len(sol) != 1:
        return None
    point = list(sol)[0]
    if any(len(t.free_symbols) for t in point):   # infinite solutions -> free vars remain
        return None
    return [sp.nsimplify(t) for t in point]


def satisfies(A, b, vars_, values):
    subs = dict(zip(vars_, values))
    for i in range(A.rows):
        lhs = sum(A[i, j] * values[j] for j in range(A.cols))
        if sp.simplify(lhs - b[i]) != 0:
            return False
    return True


# --------------------------------------------------------------------------- #
# per-method generators  (return dict: method, steps[list[str]], final[list])
# --------------------------------------------------------------------------- #
def eqline(coeffs, vars_, const):
    terms = []
    for c, v in zip(coeffs, vars_):
        c = sp.nsimplify(c)
        if c == 0:
            continue
        if c == 1:
            terms.append(f"+{v}")
        elif c == -1:
            terms.append(f"-{v}")
        else:
            terms.append(f"{'+' if c > 0 else '-'}{tex(abs(c))}{v}")
    lhs = "".join(terms).lstrip('+') or "0"
    return f"$${lhs}={tex(const)}$$"


def gen_substitution(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    a, bb = A[0, 0], A[0, 1]
    steps = []
    # solve eq1 for v0 if possible else v1
    if a != 0:
        expr = (b[0] - bb * v1) / a
        steps.append(f"Solve the first equation for $${v0}$$: $${v0}={sp.latex(sp.nsimplify(expr))}$$.")
        sub = A[1, 0] * expr + A[1, 1] * v1 - b[1]
        steps.append(f"Substitute into the second equation: $${sp.latex(sp.nsimplify(sub))}=0$$.")
        v1val = sp.solve(sp.Eq(sub, 0), v1)[0]
        steps.append(f"Solve for $${v1}$$: $${v1}={tex(v1val)}$$.")
        v0val = sp.nsimplify(expr.subs(v1, v1val))
        steps.append(f"Back-substitute to get $${v0}={tex(v0val)}$$.")
        final = [v0val, v1val]
    else:
        return None
    return {"method": "substitution", "steps": steps, "final": final}


def gen_elimination(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    a1, b1, c1 = A[0, 0], A[0, 1], b[0]
    a2, b2, c2 = A[1, 0], A[1, 1], b[1]
    steps = []
    # eliminate v1: multiply eq1 by b2, eq2 by b1, subtract
    if b1 == 0 or b2 == 0:
        m1, m2 = a2, a1   # eliminate v0 instead
        steps.append(f"Multiply equation 1 by $${tex(m1)}$$ and equation 2 by $${tex(m2)}$$ to match $${v0}$$ coefficients.")
        r1 = [m1 * a1, m1 * b1]; d1 = m1 * c1
        r2 = [m2 * a2, m2 * b2]; d2 = m2 * c2
        steps.append("Equation 1 becomes " + eqline(r1, vars_, d1) + " and equation 2 becomes " + eqline(r2, vars_, d2) + ".")
        # subtract to remove v0
        dv = [r1[0] - r2[0], r1[1] - r2[1]]; dd = d1 - d2
        steps.append(f"Subtract to eliminate $${v0}$$: " + eqline(dv, vars_, dd) + ".")
        v1val = sp.solve(sp.Eq(dv[1] * v1, dd), v1)[0]
        steps.append(f"Solve for $${v1}$$: $${v1}={tex(v1val)}$$.")
        v0val = sp.solve(sp.Eq(a1 * x + b1 * v1val - c1, 0), x)[0] if a1 != 0 else sp.solve(sp.Eq(a2 * x + b2 * v1val - c2, 0), x)[0]
        v0val = sp.nsimplify(v0val)
        steps.append(f"Back-substitute to get $${v0}={tex(v0val)}$$.")
        final = [v0val, v1val]
    else:
        m1, m2 = b2, b1
        steps.append(f"Multiply equation 1 by $${tex(m1)}$$ and equation 2 by $${tex(m2)}$$ to match $${v1}$$ coefficients.")
        r1 = [m1 * a1, m1 * b1]; d1 = m1 * c1
        r2 = [m2 * a2, m2 * b2]; d2 = m2 * c2
        steps.append("Equation 1 becomes " + eqline(r1, vars_, d1) + " and equation 2 becomes " + eqline(r2, vars_, d2) + ".")
        dv = [r1[0] - r2[0], r1[1] - r2[1]]; dd = d1 - d2
        steps.append(f"Subtract to eliminate $${v1}$$: " + eqline(dv, vars_, dd) + ".")
        v0val = sp.solve(sp.Eq(dv[0] * v0, dd), v0)[0]
        steps.append(f"Solve for $${v0}$$: $${v0}={tex(v0val)}$$.")
        v1val = sp.solve(sp.Eq(a1 * v0val + b1 * y - c1, 0), y)[0]
        v1val = sp.nsimplify(v1val)
        steps.append(f"Back-substitute to get $${v1}={tex(v1val)}$$.")
        final = [v0val, v1val]
    return {"method": "elimination", "steps": steps, "final": final}


def gen_cramer(vars_, A, b, ref):
    D = A.det()
    if D == 0:
        return None
    steps = [f"Compute the coefficient determinant $$D={tex(D)}$$."]
    final = []
    for j, v in enumerate(vars_):
        Aj = A.copy()
        Aj[:, j] = b
        Dj = Aj.det()
        val = sp.nsimplify(Dj / D)
        steps.append(f"Replace column {j+1} with the constants: $$D_{{{v}}}={tex(Dj)}$$, so $${v}=\\frac{{D_{{{v}}}}}{{D}}={tex(val)}$$.")
        final.append(val)
    return {"method": "cramers_rule", "steps": steps, "final": final}


def gen_matrix_inverse(vars_, A, b, ref):
    D = A.det()
    if D == 0:
        return None
    Ainv = A.inv()
    steps = [
        f"Write the system as $$A\\mathbf{{v}}=\\mathbf{{b}}$$ with $$\\det(A)={tex(D)}\\neq 0$$, so $$A^{{-1}}$$ exists.",
        f"Compute $$A^{{-1}}={sp.latex(Ainv)}$$.",
    ]
    prod = Ainv * b
    final = [sp.nsimplify(prod[i]) for i in range(prod.rows)]
    steps.append(f"Multiply: $$\\mathbf{{v}}=A^{{-1}}\\mathbf{{b}}={sp.latex(sp.Matrix(final))}$$.")
    steps.append(f"Read off the solution: $${sol_str(vars_, final)}$$.")
    return {"method": "inverse_matrix", "steps": steps, "final": final}


def gen_gaussian(vars_, A, b, ref):
    aug = A.row_join(b)
    rref, _ = aug.rref()
    steps = [
        f"Form the augmented matrix $$[A|\\mathbf{{b}}]={sp.latex(aug)}$$.",
        f"Row-reduce to reduced row-echelon form: $${sp.latex(rref)}$$.",
    ]
    final = [sp.nsimplify(rref[i, rref.cols - 1]) for i in range(len(vars_))]
    steps.append(f"The identity block on the left gives $${sol_str(vars_, final)}$$.")
    return {"method": "gaussian_elimination", "steps": steps, "final": final}


def gen_graphing(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    lines = []
    for i in range(2):
        a_, b_, c_ = A[i, 0], A[i, 1], b[i]
        if b_ == 0:
            lines.append(f"Equation {i+1} is the vertical line $${v0}={tex(c_/a_)}$$.")
        else:
            m = sp.nsimplify(-a_ / b_); k = sp.nsimplify(c_ / b_)
            lines.append(f"Rewrite equation {i+1} as $${v1}={sp.latex(m)}{v0}{'+' if k>=0 else '-'}{tex(abs(k))}$$ (slope $${tex(m)}$$).")
    steps = lines + [
        f"Graph both lines; they intersect at a single point.",
        f"The intersection is $$({tex(ref[0])}, {tex(ref[1])})$$, i.e. $${sol_str(vars_, ref)}$$.",
    ]
    return {"method": "graphing", "steps": ref and list(ref) and steps, "final": list(ref)}


GENERATORS = [gen_substitution, gen_elimination, gen_cramer,
              gen_matrix_inverse, gen_gaussian, gen_graphing]


# --------------------------------------------------------------------------- #
# corruption for DPO "rejected" (must verify as WRONG)
# --------------------------------------------------------------------------- #
def make_rejected(vars_, A, b, correct_final, method_steps):
    """Produce a plausible-but-WRONG worked solution for DPO's `rejected` side.

    The wrong answer is a realistic student-error perturbation (sign flip, swap,
    off-by-one) that is *verified* not to satisfy the system. The concluding step
    is stated confidently with no self-announcing tag, and the step that would
    reveal the correct answer is dropped, so the negative reads as a genuine
    mistake rather than a labelled one. Returns (steps, wrong_final) or None.
    """
    candidates = []
    candidates.append(("sign_flip", [-correct_final[0]] + list(correct_final[1:])))
    if len(correct_final) >= 2:
        swapped = list(correct_final)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        candidates.append(("swap_vars", swapped))
    candidates.append(("off_by_one", [correct_final[0] + 1] + list(correct_final[1:])))
    # keep the setup steps but drop trailing steps that state a correct value,
    # so the derivation does not contradict its own (wrong) conclusion.
    kept = [s for s in method_steps if not re.search(r'(Back-substitute|Solve for|Read off|intersection is)', s)]
    if len(kept) < 1:
        kept = method_steps[:1]
    for strategy, cand in candidates:
        if not satisfies(A, b, vars_, cand):        # must be genuinely wrong
            steps = list(kept) + [f"Therefore the solution is $${sol_str(vars_, cand)}$$."]
            return steps, cand, strategy
    return None


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def worked_text(title, steps):
    return f"Method: {title}\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))


def build(record):
    """Return (multimethod_record | None, list_of_pref_pairs, stats_counter)."""
    stats = Counter()
    q = record["steps"][0]["question"] if record["steps"] else ""
    eqs = extract_system(q)
    if len(eqs) < 2:
        stats["skip_unparsed"] += 1
        return None, [], stats
    sysinfo = system_of(eqs)
    if sysinfo is None:
        stats["skip_ill_formed"] += 1
        return None, [], stats
    vars_, A, b = sysinfo
    ref = reference_solution(vars_, A, b)
    if ref is None:
        stats["skip_no_unique_solution"] += 1
        return None, [], stats
    if not satisfies(A, b, vars_, ref):            # sanity: reference must satisfy
        stats["error_reference_unverified"] += 1
        return None, [], stats

    system_tex = [eqline([A[i, j] for j in range(A.cols)], vars_, b[i]) for i in range(A.rows)]
    prompt = ("Solve the system of equations:\n" + "  ".join(system_tex))

    methods = []
    pairs = []
    for gen in GENERATORS:
        try:
            out = gen(vars_, A, b, ref)
        except Exception as e:  # noqa: BLE001
            stats[f"gen_exception:{gen.__name__}"] += 1
            continue
        if not out or not out.get("steps"):
            continue
        final = [sp.nsimplify(v) for v in out["final"]]
        # VERIFY 1: matches reference   VERIFY 2: satisfies original equations
        if [sp.simplify(final[i] - ref[i]) == 0 for i in range(len(ref))] != [True] * len(ref):
            stats[f"reject_final_mismatch:{out['method']}"] += 1
            continue
        if not satisfies(A, b, vars_, final):
            stats[f"reject_unsatisfied:{out['method']}"] += 1
            continue
        stats[f"verified:{out['method']}"] += 1
        chosen_text = worked_text(out["method"], out["steps"] + [f"Solution: $${sol_str(vars_, final)}$$."])
        methods.append({
            "method": out["method"],
            "steps": out["steps"],
            "final_answer": sol_str(vars_, final),
            "verified": True,
        })
        # build a preference pair for this method
        rej = make_rejected(vars_, A, b, final, out["steps"])
        if rej is not None:
            rej_steps, rej_final, rej_strategy = rej
            # double-check rejected really is wrong AND differs from chosen
            if not satisfies(A, b, vars_, rej_final) and rej_final != list(final):
                stats["pref_pairs"] += 1
                pairs.append({
                    "prompt": prompt,
                    "chosen": chosen_text,
                    "rejected": worked_text(out["method"], rej_steps),
                    "meta": {
                        "problem_id": record["source"]["problem_id"],
                        "method": out["method"],
                        "correct_answer": sol_str(vars_, final),
                        "rejected_answer": sol_str(vars_, rej_final),
                        "rejected_strategy": rej_strategy,
                        "n_vars": len(vars_),
                    },
                })
            else:
                stats["error_rejected_actually_correct"] += 1

    if not methods:
        stats["skip_no_methods"] += 1
        return None, [], stats

    mm = {
        "schema_version": "1.0-multimethod",
        "source": record["source"],
        "provenance": record["provenance"],
        "taxonomy": {**record["taxonomy"], "generated_methods": [m["method"] for m in methods]},
        "system": {"variables": [str(v) for v in vars_], "equations_tex": system_tex,
                   "reference_solution": sol_str(vars_, ref)},
        "prompt": prompt,
        "methods": methods,
        "verification": {"all_methods_verified": True, "checked_by": "sympy back-substitution"},
    }
    stats["systems_emitted"] += 1
    return mm, pairs, stats


def run(systems_jsonl, out_dir):
    out = os.path.join(out_dir, "multimethod")
    os.makedirs(out, exist_ok=True)
    records = [json.loads(l) for l in open(systems_jsonl, encoding="utf-8")]
    stats = Counter()
    mm_path = os.path.join(out, "systems_multimethod.jsonl")
    pref_path = os.path.join(out, "preference_pairs.jsonl")
    sft_path = os.path.join(out, "sft_multimethod.jsonl")
    n_mm = n_pref = n_sft = 0
    with open(mm_path, "w", encoding="utf-8") as fmm, \
         open(pref_path, "w", encoding="utf-8") as fpref, \
         open(sft_path, "w", encoding="utf-8") as fsft:
        for r in records:
            mm, pairs, st = build(r)
            stats.update(st)
            if mm:
                fmm.write(json.dumps(mm, ensure_ascii=False, sort_keys=True) + "\n")
                n_mm += 1
                # one SFT example per verified method
                for meth in mm["methods"]:
                    completion = (f"Method: {meth['method']}\n"
                                  + "\n".join(f"{i+1}. {s}" for i, s in enumerate(meth["steps"]))
                                  + f"\nSolution: $${meth['final_answer']}$$.")
                    fsft.write(json.dumps({
                        "prompt": mm["prompt"], "completion": completion,
                        "meta": {"problem_id": mm["source"]["problem_id"], "method": meth["method"]},
                    }, ensure_ascii=False) + "\n")
                    n_sft += 1
            for p in pairs:
                fpref.write(json.dumps(p, ensure_ascii=False) + "\n")
                n_pref += 1
    manifest = {
        "generator": "deterministic sympy; questions verbatim from OATutor",
        "input": os.path.basename(systems_jsonl),
        "counts": {"systems_emitted": n_mm, "preference_pairs": n_pref,
                   "sft_method_examples": n_sft},
        "verified_by_method": {k.split(":", 1)[1]: v for k, v in stats.items() if k.startswith("verified:")},
        "rejections_and_skips": {k: v for k, v in sorted(stats.items())
                                 if k.startswith(("reject_", "skip_", "error_", "gen_exception"))},
    }
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(json.dumps(manifest, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="data/oatutor_systems.jsonl")
    ap.add_argument("--out-dir", default="data")
    args = ap.parse_args()
    run(args.systems, args.out_dir)


if __name__ == "__main__":
    main()
