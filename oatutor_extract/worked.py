#!/usr/bin/env python3
"""Worked-solution variant of the multi-method generator.

Same guarantees as multimethod.py (questions verbatim from OATutor, every answer
sympy-verified), but the solution steps SHOW THE ARITHMETIC explicitly instead of
compressing it. Motivation: terse targets taught models to imitate the format and
fabricate intermediate arithmetic; worked targets demonstrate each computation so
the model learns to reason, not just format.

Outputs (data/multimethod_worked/):
  systems_multimethod.jsonl  one system + all verified worked methods
  sft_multimethod.jsonl      {prompt, completion} per verified method
  preference_pairs.jsonl     {prompt, chosen, rejected, meta}
  manifest.json
"""
from __future__ import annotations

import json
import os
from collections import Counter

import sympy as sp

from .multimethod import (
    extract_system, system_of, reference_solution, satisfies, tex, sol_str,
    make_rejected, SYMS,
)

x, y, z = SYMS['x'], SYMS['y'], SYMS['z']


# --------------------------------------------------------------------------- #
# rendering helpers (explicit, signed arithmetic)
# --------------------------------------------------------------------------- #
def term(c, v):
    """Render a signed coefficient*variable term, e.g. (3,'x')->'+3x', (-1,'y')->'-y'."""
    c = sp.nsimplify(c)
    if c == 0:
        return ""
    sign = "+" if c > 0 else "-"
    mag = abs(c)
    body = v if mag == 1 else f"{tex(mag)}{v}"
    return f"{sign}{body}"


def lin(coeffs, vars_, const):
    """'a x + b y = c' with clean leading sign."""
    s = "".join(term(c, v) for c, v in zip(coeffs, vars_))
    s = s.lstrip("+") or "0"
    return f"{s}={tex(const)}"


def signed(c):
    c = sp.nsimplify(c)
    return f"+{tex(c)}" if c >= 0 else f"-{tex(abs(c))}"


# --------------------------------------------------------------------------- #
# worked 2-variable methods
# --------------------------------------------------------------------------- #
def gen_substitution(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    a1, b1, c1 = A[0, 0], A[0, 1], b[0]
    a2, b2, c2 = A[1, 0], A[1, 1], b[1]
    if a1 == 0:
        return None
    steps = []
    steps.append(f"Write the system: $${lin([a1, b1], vars_, c1)}$$ and $${lin([a2, b2], vars_, c2)}$$.")
    # isolate v0 in eq1
    x_expr = sp.nsimplify((c1 - b1 * v1) / a1)
    steps.append(f"Solve equation 1 for $${v0}$$: $${tex(a1)}{v0}={tex(c1)}{signed(-b1)}{v1}$$, so $${v0}={sp.latex(x_expr)}$$.")
    # substitute into eq2 (show the plug-in literally)
    steps.append(
        f"Substitute $${v0}={sp.latex(x_expr)}$$ into equation 2: "
        f"$${tex(a2)}\\left({sp.latex(x_expr)}\\right){signed(b2)}{v1}={tex(c2)}$$."
    )
    # simplify to a single-variable linear equation (sympy-computed, correct)
    L = sp.expand(a2 * x_expr + b2 * v1)          # = p*v1 + q
    p = sp.nsimplify(L.coeff(v1, 1))
    q = sp.nsimplify(L.subs(v1, 0))
    steps.append(f"Combine like terms: $${lin([p], [v1], sp.nsimplify(c2 - q))}$$.")
    v1val = sp.nsimplify((c2 - q) / p)
    steps.append(f"Solve for $${v1}$$: $${v1}={tex(v1val)}$$.")
    # back-substitute with explicit arithmetic
    v0val = sp.nsimplify(x_expr.subs(v1, v1val))
    steps.append(
        f"Back-substitute $${v1}={tex(v1val)}$$: "
        f"$${v0}={sp.latex(x_expr)}={sp.latex(x_expr.subs(v1, v1val, simultaneous=True))}={tex(v0val)}$$."
    )
    return {"method": "substitution", "steps": steps, "final": [v0val, v1val]}


def gen_elimination(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    a1, b1, c1 = A[0, 0], A[0, 1], b[0]
    a2, b2, c2 = A[1, 0], A[1, 1], b[1]
    steps = [f"Write the system: $${lin([a1, b1], vars_, c1)}$$ and $${lin([a2, b2], vars_, c2)}$$."]
    # eliminate v1 if possible, else v0
    if b1 != 0 and b2 != 0:
        m1, m2 = b2, b1
        elim, keep = v1, v0
        r1 = [a1 * m1, b1 * m1]; d1 = c1 * m1
        r2 = [a2 * m2, b2 * m2]; d2 = c2 * m2
    else:
        m1, m2 = a2, a1
        elim, keep = v0, v1
        r1 = [a1 * m1, b1 * m1]; d1 = c1 * m1
        r2 = [a2 * m2, b2 * m2]; d2 = c2 * m2
    steps.append(
        f"Make the $${elim}$$ coefficients match: multiply equation 1 by $${tex(m1)}$$ and "
        f"equation 2 by $${tex(m2)}$$."
    )
    steps.append(f"Equation 1 becomes $${lin(r1, vars_, d1)}$$; equation 2 becomes $${lin(r2, vars_, d2)}$$.")
    # subtract
    dr = [sp.nsimplify(r1[0] - r2[0]), sp.nsimplify(r1[1] - r2[1])]
    dd = sp.nsimplify(d1 - d2)
    steps.append(f"Subtract equation 2 from equation 1 to eliminate $${elim}$$: $${lin(dr, vars_, dd)}$$.")
    keep_idx = 0 if keep == v0 else 1
    kcoef = dr[keep_idx]
    kval = sp.nsimplify(dd / kcoef)
    steps.append(f"Solve for $${keep}$$: $${keep}={tex(kval)}$$.")
    # back-substitute into equation 1
    other = v1 if keep == v0 else v0
    # a1*v0 + b1*v1 = c1  -> solve for the other with keep known
    if keep == v0:
        oval = sp.nsimplify((c1 - a1 * kval) / b1) if b1 != 0 else sp.nsimplify((c2 - a2 * kval) / b2)
        steps.append(
            f"Back-substitute $${keep}={tex(kval)}$$ into equation 1: "
            f"$${term(a1, v0).lstrip('+')}{signed(b1)}{v1}={tex(c1)}$$ gives "
            f"$${tex(sp.nsimplify(a1*kval))}{signed(b1)}{v1}={tex(c1)}$$, so $${other}={tex(oval)}$$."
        )
        final = [kval, oval]
    else:
        oval = sp.nsimplify((c1 - b1 * kval) / a1) if a1 != 0 else sp.nsimplify((c2 - b2 * kval) / a2)
        steps.append(
            f"Back-substitute $${keep}={tex(kval)}$$ into equation 1: "
            f"$${other}={tex(oval)}$$."
        )
        final = [oval, kval]
    return {"method": "elimination", "steps": steps, "final": final}


def gen_graphing(vars_, A, b, ref):
    if len(vars_) != 2:
        return None
    v0, v1 = vars_
    steps = []
    for i in range(2):
        a_, b_, c_ = A[i, 0], A[i, 1], b[i]
        if b_ == 0:
            steps.append(f"Equation {i+1} is the vertical line $${v0}={tex(sp.nsimplify(c_/a_))}$$.")
        else:
            m = sp.nsimplify(-a_ / b_); k = sp.nsimplify(c_ / b_)
            steps.append(
                f"Rewrite equation {i+1} in slope-intercept form: from $${lin([a_, b_], vars_, c_)}$$, "
                f"$${tex(b_)}{v1}={tex(c_)}{signed(-a_)}{v0}$$, so $${v1}={sp.latex(m*v0 + k)}$$ "
                f"(slope $${tex(m)}$$, intercept $${tex(k)}$$)."
            )
    steps.append(
        f"The two lines meet where the $${v1}$$-values are equal; solving gives the intersection "
        f"$$({tex(ref[0])},\\ {tex(ref[1])})$$."
    )
    return {"method": "graphing", "steps": steps, "final": list(ref)}


def gen_cramer(vars_, A, b, ref):
    D = A.det()
    if D == 0:
        return None
    n = len(vars_)
    if n == 2:
        steps = [
            f"Cramer's rule uses determinants. The coefficient determinant is "
            f"$$D=\\begin{{vmatrix}}{tex(A[0,0])}&{tex(A[0,1])}\\\\{tex(A[1,0])}&{tex(A[1,1])}\\end{{vmatrix}}"
            f"=({tex(A[0,0])})({tex(A[1,1])})-({tex(A[0,1])})({tex(A[1,0])})={tex(D)}.$$"
        ]
    else:
        steps = [f"Cramer's rule uses determinants. The coefficient determinant is $$D={tex(D)}$$ "
                 f"(from $$A={sp.latex(A)}$$)."]
    final = []
    for j, v in enumerate(vars_):
        Aj = A.copy(); Aj[:, j] = b
        Dj = Aj.det()
        val = sp.nsimplify(Dj / D)
        if n == 2:
            steps.append(
                f"Replace column {j+1} with the constants: "
                f"$$D_{{{v}}}=\\begin{{vmatrix}}{tex(Aj[0,0])}&{tex(Aj[0,1])}\\\\{tex(Aj[1,0])}&{tex(Aj[1,1])}\\end{{vmatrix}}={tex(Dj)}$$, "
                f"so $${v}=\\dfrac{{D_{{{v}}}}}{{D}}=\\dfrac{{{tex(Dj)}}}{{{tex(D)}}}={tex(val)}$$."
            )
        else:
            steps.append(f"Replace column {j+1} with the constants: $$D_{{{v}}}={tex(Dj)}$$, "
                         f"so $${v}=\\dfrac{{{tex(Dj)}}}{{{tex(D)}}}={tex(val)}$$.")
        final.append(val)
    return {"method": "cramers_rule", "steps": steps, "final": final}


def gen_gaussian(vars_, A, b, ref):
    aug = A.row_join(b)
    steps = [f"Form the augmented matrix $$[A\\,|\\,\\mathbf{{b}}]={sp.latex(aug)}.$$"]
    # do explicit forward elimination to row-echelon, narrating each pivot
    M = aug.copy().as_mutable()
    rows = M.rows
    for col in range(len(vars_)):
        if M[col, col] == 0:
            for r in range(col + 1, rows):
                if M[r, col] != 0:
                    M.row_swap(col, r)
                    steps.append(f"Swap rows to get a nonzero pivot in column {col+1}: $${sp.latex(M)}.$$")
                    break
        piv = M[col, col]
        if piv == 0:
            continue
        for r in range(col + 1, rows):
            if M[r, col] != 0:
                factor = sp.nsimplify(M[r, col] / piv)
                M[r, :] = M[r, :] - factor * M[col, :]
                steps.append(
                    f"Eliminate column {col+1} in row {r+1} (R{r+1} \\u2192 R{r+1} - "
                    f"({tex(factor)})R{col+1}): $${sp.latex(M)}.$$".replace("\\u2192", "→")
                )
    # back-substitution from the echelon form
    rref, _ = aug.rref()
    final = [sp.nsimplify(rref[i, rref.cols - 1]) for i in range(len(vars_))]
    steps.append(f"Back-substitute from the echelon form to obtain $${sol_str(vars_, final)}$$.")
    return {"method": "gaussian_elimination", "steps": steps, "final": final}


def gen_matrix_inverse(vars_, A, b, ref):
    D = A.det()
    if D == 0:
        return None
    Ainv = A.inv()
    steps = [
        f"Write the system as $$A\\mathbf{{v}}=\\mathbf{{b}}$$ with $$A={sp.latex(A)},\\ \\mathbf{{b}}={sp.latex(b)}.$$",
        f"Since $$\\det(A)={tex(D)}\\neq 0$$, $$A^{{-1}}$$ exists: $$A^{{-1}}={sp.latex(Ainv)}.$$",
    ]
    prod = Ainv * b
    final = [sp.nsimplify(prod[i]) for i in range(prod.rows)]
    steps.append(f"Then $$\\mathbf{{v}}=A^{{-1}}\\mathbf{{b}}={sp.latex(Ainv)}{sp.latex(b)}={sp.latex(sp.Matrix(final))},$$ "
                 f"i.e. $${sol_str(vars_, final)}$$.")
    return {"method": "inverse_matrix", "steps": steps, "final": final}


GENERATORS = [gen_substitution, gen_elimination, gen_graphing,
              gen_cramer, gen_matrix_inverse, gen_gaussian]


# --------------------------------------------------------------------------- #
# assembly (mirrors multimethod.build but with worked generators)
# --------------------------------------------------------------------------- #
def worked_text(title, steps):
    return f"Method: {title}\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))


def build(record):
    stats = Counter()
    q = record["steps"][0]["question"] if record["steps"] else ""
    eqs = extract_system(q)
    if len(eqs) < 2:
        stats["skip_unparsed"] += 1
        return None, [], stats
    si = system_of(eqs)
    if si is None:
        stats["skip_ill_formed"] += 1
        return None, [], stats
    vars_, A, b = si
    ref = reference_solution(vars_, A, b)
    if ref is None or not satisfies(A, b, vars_, ref):
        stats["skip_no_unique_solution"] += 1
        return None, [], stats

    system_tex = [f"$${lin([A[i, j] for j in range(A.cols)], vars_, b[i])}$$" for i in range(A.rows)]
    prompt = "Solve the system of equations:\n" + "  ".join(system_tex)

    methods, pairs = [], []
    for gen in GENERATORS:
        try:
            out = gen(vars_, A, b, ref)
        except Exception:
            stats[f"gen_exception:{gen.__name__}"] += 1
            continue
        if not out or not out.get("steps"):
            continue
        final = [sp.nsimplify(v) for v in out["final"]]
        if any(sp.simplify(final[i] - ref[i]) != 0 for i in range(len(ref))) or not satisfies(A, b, vars_, final):
            stats[f"reject_unverified:{out['method']}"] += 1
            continue
        stats[f"verified:{out['method']}"] += 1
        chosen = worked_text(out["method"], out["steps"] + [f"Solution: $${sol_str(vars_, final)}$$."])
        methods.append({"method": out["method"], "steps": out["steps"],
                        "final_answer": sol_str(vars_, final), "verified": True})
        rej = make_rejected(vars_, A, b, final, out["steps"])
        if rej:
            rsteps, rfinal, rstrat = rej
            if not satisfies(A, b, vars_, rfinal) and rfinal != list(final):
                pairs.append({"prompt": prompt, "chosen": chosen,
                              "rejected": worked_text(out["method"], rsteps),
                              "meta": {"problem_id": record["source"]["problem_id"],
                                       "method": out["method"],
                                       "correct_answer": sol_str(vars_, final),
                                       "rejected_answer": sol_str(vars_, rfinal),
                                       "rejected_strategy": rstrat, "n_vars": len(vars_)}})
    if not methods:
        stats["skip_no_methods"] += 1
        return None, [], stats

    mm = {"schema_version": "1.0-worked", "source": record["source"],
          "provenance": record["provenance"],
          "taxonomy": {**record["taxonomy"], "generated_methods": [m["method"] for m in methods]},
          "system": {"variables": [str(v) for v in vars_], "equations_tex": [s.strip("$") for s in system_tex],
                     "reference_solution": sol_str(vars_, ref)},
          "prompt": prompt, "methods": methods,
          "verification": {"all_methods_verified": True, "checked_by": "sympy back-substitution"}}
    stats["systems_emitted"] += 1
    return mm, pairs, stats


def run(systems_jsonl, out_dir):
    out = os.path.join(out_dir, "multimethod_worked")
    os.makedirs(out, exist_ok=True)
    records = [json.loads(l) for l in open(systems_jsonl, encoding="utf-8")]
    stats = Counter()
    n_mm = n_pref = n_sft = 0
    with open(os.path.join(out, "systems_multimethod.jsonl"), "w", encoding="utf-8") as fmm, \
         open(os.path.join(out, "preference_pairs.jsonl"), "w", encoding="utf-8") as fpref, \
         open(os.path.join(out, "sft_multimethod.jsonl"), "w", encoding="utf-8") as fsft:
        for r in records:
            mm, pairs, st = build(r)
            stats.update(st)
            if mm:
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
    manifest = {"generator": "deterministic sympy WORKED solutions; questions verbatim from OATutor",
                "counts": {"systems_emitted": n_mm, "sft_method_examples": n_sft, "preference_pairs": n_pref},
                "verified_by_method": {k.split(":", 1)[1]: v for k, v in stats.items() if k.startswith("verified:")},
                "skips": {k: v for k, v in sorted(stats.items()) if k.startswith(("skip_", "reject_", "gen_"))}}
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    print(json.dumps(manifest, indent=2))
    return manifest


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default="data/oatutor_systems.jsonl")
    ap.add_argument("--out-dir", default="data")
    a = ap.parse_args()
    run(a.systems, a.out_dir)


if __name__ == "__main__":
    main()
