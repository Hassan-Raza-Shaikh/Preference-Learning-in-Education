"""Problem bank for the tutor, built from the verified Phase 1 worked-solution generators.

Build (needs the OATutor extraction in data/oatutor_systems.jsonl):
    python -m tutor.bank --systems data/oatutor_systems.jsonl --out tutor/data/problem_bank.json  # parser v2 (default)

Guarantees, checked at build time (a problem or method is dropped if any check fails):
  1. final answer == sympy reference solution and satisfies the original system;
  2. no irrational rendering artifacts in any displayed step;
  3. STEP-LEVEL CHECK: every equation displayed in a step that can be parsed must hold
     when the true solution is substituted (any equation derived from a linear system
     holds at its solution). Unparseable blocks (matrices, determinants) are counted as
     'unchecked' and reported; their values are still computed by sympy.
Duplicate systems (same equations, e.g. reused across OATutor courses) are kept once.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

import sympy as sp

from oatutor_extract import worked
from oatutor_extract.multimethod import (
    EQ_BLOCK, SYMS, exact, extract_system, has_irrational_artifact,
    latex_to_expr_str, reference_solution, satisfies, sol_str, system_of, tex,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BANK = os.path.join(ROOT, "tutor", "data", "problem_bank.json")


# --------------------------------------------------------------------------- #
# tutor-specific rendering fix (Phase 1 data is left byte-identical)
# --------------------------------------------------------------------------- #
def gen_substitution_tutor(vars_, A, b, ref):
    """worked.gen_substitution, but the back-substitution shows the plugged-in value.

    Phase 1 renders e.g. 'x=3 y=3=3' (sympy evaluates 3*1 immediately). For learners we
    show 'x=3 y=3\\left(1\\right)=3'. Only the display of that last step changes.
    """
    out = worked.gen_substitution(vars_, A, b, ref)
    if not out:
        return out
    v0, v1 = vars_
    a1, b1, c1 = A[0, 0], A[0, 1], b[0]
    x_expr = exact((c1 - b1 * v1) / a1)
    v0val, v1val = out["final"]
    plug = sp.Symbol(f"\\left({tex(v1val)}\\right)")
    shown = sp.latex(x_expr.subs(v1, plug))
    out["steps"][-1] = (f"Back-substitute $${v1}={tex(v1val)}$$: "
                        f"$${v0}={sp.latex(x_expr)}={shown}={tex(v0val)}$$.")
    return out


def tidy(step: str) -> str:
    """Display clean-up only: '+1y' -> '+y', '-1x' -> '-x' (re-verified by check_steps)."""
    return re.sub(r"(?<=[+\-=(])1(?=[xyz](?![a-z]))", "", step)


GENERATORS = [gen_substitution_tutor] + [g for g in worked.GENERATORS if g is not worked.gen_substitution]


# --------------------------------------------------------------------------- #
# step-level verification
# --------------------------------------------------------------------------- #
def _parse_side(s):
    s = s.replace("\\dfrac", "\\frac")
    s = re.sub(r"\\left\((-?\\frac\{\d+\}\{\d+\}|-?\d+)\\right\)", r"(\1)", s)
    return sp.sympify(latex_to_expr_str(s), locals=SYMS)


def _numeric_parts(parts, at):
    """Parse each '='-separated part and substitute the solution; keep fully numeric ones."""
    vals = []
    for p in parts:
        if "\\begin" in p or "\\mathbf" in p:
            continue
        try:
            v = sp.simplify(_parse_side(p).subs(at))
        except Exception:  # noqa: BLE001 - unparseable display
            continue
        if v.free_symbols or v.atoms(sp.core.function.AppliedUndef):
            continue           # e.g. D_{x} or D still symbolic
        vals.append(v)
    return vals


DET_BLOCK = re.compile(r"^D(?:_\{?([xyz])\}?)?=")


def check_steps(steps, vars_, ref, detA=None):
    """Return (n_checked, n_unchecked, failures) for equations shown in the steps.

    Generic rule: every numeric side of a displayed equation must agree once the true
    solution is substituted. Cramer blocks 'D=...' / 'D_{v}=...' are checked against
    det(A) and det(A)*v (Cramer's rule: v = D_v / D).
    """
    at = {SYMS[str(v)]: r for v, r in zip(vars_, ref)}
    refmap = dict(zip(map(str, vars_), ref))
    checked = unchecked = 0
    failures = []
    for st in steps:
        blocks = [b for blk in EQ_BLOCK.findall(st)
                  for b in re.split(r",\s*(?=[a-zA-Z]\s*=)", blk.rstrip(".,"))]  # 'x=3, y=1'
        for block in blocks:
            if "=" not in block or "\\neq" in block:
                continue
            block = block.rstrip(".,")
            parts = block.split("=")
            m = DET_BLOCK.match(block)
            if m and detA is not None:
                target = detA if m.group(1) is None else detA * refmap[m.group(1)]
                vals = _numeric_parts(parts[1:], at)
                if not vals:
                    unchecked += 1
                    continue
                checked += 1
                if any(sp.simplify(v - target) != 0 for v in vals):
                    failures.append(block)
                continue
            vals = _numeric_parts(parts, at)
            if len(vals) < 2:
                unchecked += 1
                continue
            checked += 1
            if any(sp.simplify(v - vals[0]) != 0 for v in vals[1:]):
                failures.append(block)
    return checked, unchecked, failures


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def features(A, b, ref):
    coefs = [abs(exact(c)) for c in list(A) + list(b)]
    return {"n_vars": len(ref),
            "fractional_solution": any(not exact(r).is_Integer for r in ref),
            "max_coef": int(max(sp.ceiling(c) for c in coefs)) if coefs else 0}


def build_problem(record, stats, parser="v1"):
    q = record["steps"][0]["question"] if record["steps"] else ""
    if parser == "v2":
        from oatutor_extract.parse_v2 import extract_system_v2
        stem = (record["problem"].get("title") or "") + " " + (record["problem"].get("body") or "")
        eqs, how = extract_system_v2(q, stem)
        stats[f"parsed_by:{how}"] += 1
    else:
        eqs = extract_system(q)
    if len(eqs) < 2:
        stats["skip_unparsed"] += 1
        return None
    si = system_of(eqs)
    if si is None:
        stats["skip_ill_formed"] += 1
        return None
    vars_, A, b = si
    ref = reference_solution(vars_, A, b)
    if ref is None or not satisfies(A, b, vars_, ref):
        stats["skip_no_unique_solution"] += 1
        return None
    methods = {}
    for gen in GENERATORS:
        try:
            out = gen(vars_, A, b, ref)
        except Exception:  # noqa: BLE001
            stats[f"gen_exception:{gen.__name__}"] += 1
            continue
        if not out or not out.get("steps"):
            continue
        out["steps"] = [tidy(st) for st in out["steps"]]
        final = [exact(v) for v in out["final"]]
        m = out["method"]
        if any(sp.simplify(final[i] - ref[i]) != 0 for i in range(len(ref))) or not satisfies(A, b, vars_, final):
            stats[f"reject_unverified:{m}"] += 1
            continue
        if has_irrational_artifact(out["steps"]):
            stats[f"reject_irrational:{m}"] += 1
            continue
        n_ok, n_unc, fails = check_steps(out["steps"], vars_, ref, detA=A.det())
        stats["step_eq_checked"] += n_ok
        stats["step_eq_unchecked"] += n_unc
        if fails:
            stats[f"reject_step_check:{m}"] += 1
            stats.setdefault("_step_failures", []).append({"problem": record["source"]["problem_id"],
                                                           "method": m, "blocks": fails})
            continue
        stats[f"verified:{m}"] += 1
        methods[m] = {"steps": out["steps"], "final_answer": sol_str(vars_, final)}
    if not methods:
        stats["skip_no_methods"] += 1
        return None
    tax, prov = record["taxonomy"], record["provenance"]
    return {
        "id": record["source"]["problem_id"],
        "source": {"problem_id": record["source"]["problem_id"], "course": tax.get("course"),
                   "lesson": tax.get("lesson"), "oer": prov.get("oer"), "oer_url": prov.get("oer_url"),
                   "license": prov.get("license"), "license_url": prov.get("license_url"),
                   "repo": record["source"]["repo"], "commit": record["source"]["commit"]},
        "variables": [str(v) for v in vars_],
        "A": [[str(A[i, j]) for j in range(A.cols)] for i in range(A.rows)],
        "b": [str(b[i]) for i in range(b.rows)],
        "reference": [str(r) for r in ref],
        "reference_tex": sol_str(vars_, ref),
        "equations_tex": [worked.lin([A[i, j] for j in range(A.cols)], vars_, b[i]) for i in range(A.rows)],
        "methods": methods,
        "features": features(A, b, ref),
    }


def build(systems_jsonl, out_path, parser="v2"):
    stats = Counter()
    bank, seen = [], {}
    for line in open(systems_jsonl, encoding="utf-8"):
        rec = json.loads(line)
        p = build_problem(rec, stats, parser)
        if p is None:
            continue
        sig = (tuple(map(tuple, p["A"])), tuple(p["b"]))
        if sig in seen:
            stats["duplicate_system"] += 1
            continue
        seen[sig] = p["id"]
        bank.append(p)
    failures = stats.pop("_step_failures", [])
    by_method = Counter(m for p in bank for m in p["methods"])
    manifest = {"problems": len(bank), "by_method": dict(sorted(by_method.items())),
                "by_n_vars": dict(Counter(p["features"]["n_vars"] for p in bank)),
                "stats": dict(sorted(stats.items())), "step_check_failures": failures,
                "source_systems": os.path.relpath(systems_jsonl, ROOT), "parser": parser}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"manifest": manifest, "problems": bank}, fh, ensure_ascii=False, indent=1)
    return manifest


def load(path=DEFAULT_BANK):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["problems"]


def matrices(problem):
    """Exact sympy-ready A (list of lists) and b (list) for grading."""
    A = [[sp.Rational(c) for c in row] for row in problem["A"]]
    b = [sp.Rational(c) for c in problem["b"]]
    return A, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default=os.path.join(ROOT, "data", "oatutor_systems.jsonl"))
    ap.add_argument("--out", default=DEFAULT_BANK)
    ap.add_argument("--parser", choices=["v1", "v2"], default="v2",
                    help="v2 = oatutor_extract.parse_v2 (more formats; Track A item A4)")
    a = ap.parse_args()
    print(json.dumps(build(a.systems, a.out, a.parser), indent=2))


if __name__ == "__main__":
    main()
