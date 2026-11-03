#!/usr/bin/env python3
"""Track A item A2: structural method-faithfulness check (replaces keyword matching).

The Phase 1 metric (evaluate.faithful) only searched for keywords, e.g. 'substitut',
which also matches 'Back-substitute' in an elimination solution. This module instead
checks whether the solution PERFORMS the requested method's characteristic operation,
using sympy against the actual system (A, b):

  substitution   a variable is isolated as an expression in the other variable, as a
                 rearrangement of exactly ONE original equation (isolating y in both is
                 graphing); a one-variable equation follows; nothing is scaled by k != +-1
  elimination    an original equation is scaled by a factor other than +-1, or the two
                 original equations are added/subtracted directly into a one-variable
                 equation, without any isolation step
  graphing       every original equation is rewritten as y = m x + c (or x = c)
  cramers_rule   det(A) and at least one det(A_j) appear, with D_x or determinant-bar notation
  inverse_matrix a matrix equal to A^-1 (or adj(A) = det(A) A^-1) appears
  gaussian_elim  an n x (n+1) matrix row-equivalent to [A|b], other than [A|b] itself

Validation (python -m experiments.faithfulness): on verified gold solutions, the check
must accept the requested method (recall) and reject the OTHER methods' gold solutions
(cross-method specificity). Both are reported next to the old keyword metric.
"""
import json
import os
import re
import sys
from collections import defaultdict

import sympy as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.evaluate import faithful as keyword_faithful  # noqa: E402
from oatutor_extract.multimethod import SYMS, extract_system, latex_to_expr_str, system_of  # noqa: E402

MATH = re.compile(r"\$\$(.+?)\$\$|\\\((.+?)\\\)|\\\[(.+?)\\\]", re.S)
MATRIX = re.compile(r"\\begin\{[bpv]?matrix\}(.+?)\\end\{[bpv]?matrix\}", re.S)


def _segments(text):
    segs = [next(g for g in m.groups() if g) for m in MATH.finditer(text)]
    if not segs:   # plain-text fallback: lines with '='
        segs = [l for l in text.splitlines() if "=" in l]
    out = []
    for s in segs:
        out += re.split(r",\s*(?=[a-zA-Z]\s*=)|\\quad|;", s)
    return out


def _parse(s):
    s = s.replace("\\dfrac", "\\frac").replace("\\cdot", "*").strip().rstrip(".,")
    s = re.sub(r"\\text\{[^}]*\}", "", s)
    return sp.sympify(latex_to_expr_str(s), locals=SYMS)


def equations(text):
    """[(lhs_str, rhs_str, expr)] for adjacent sides of every '=' chain that parse."""
    out = []
    for seg in _segments(text):
        if "\\begin" in seg:
            continue
        parts = seg.split("=")
        for L, R in zip(parts, parts[1:]):
            try:
                e = sp.expand(_parse(L) - _parse(R))
            except Exception:  # noqa: BLE001
                continue
            if e.free_symbols and e.free_symbols <= set(SYMS.values()):
                out.append((L.strip(), R.strip(), e))
    return out


def matrices(text):
    mats = []
    for body in MATRIX.findall(text):
        rows = [r for r in re.split(r"\\\\", body) if r.strip()]
        try:
            M = [[_parse(c) for c in r.split("&")] for r in rows]
            if len({len(r) for r in M}) == 1:
                mats.append(sp.Matrix(M))
        except Exception:  # noqa: BLE001
            continue
    return mats


def numbers(text):
    vals = set()
    for m in re.finditer(r"-?\\frac\{(-?\d+)\}\{(-?\d+)\}|-?\d+(?:/\d+)?", text):
        try:
            tok = m.group(0)
            if tok.lstrip("-").startswith("\\frac"):
                v = sp.Rational(int(m.group(1)), int(m.group(2)))
                vals.add(-v if tok.startswith("-") else v)
            else:
                vals.add(sp.Rational(tok))
        except Exception:  # noqa: BLE001
            pass
    return vals


def _vec(expr, vars_):
    return [expr.coeff(v, 1) for v in vars_] + [-expr.subs({v: 0 for v in vars_})]


def _ratio_to(e_vec, o_vec):
    """k if e_vec == k * o_vec (k != 0), else None."""
    k = None
    for a, b in zip(e_vec, o_vec):
        if b == 0:
            if a != 0:
                return None
            continue
        r = sp.nsimplify(a / b) if not isinstance(a / b, sp.Rational) else a / b
        if k is None:
            k = r
        elif sp.simplify(r - k) != 0:
            return None
    return k if k not in (None, 0) else None


def _adds_or_subtracts(e_vec, o1, o2):
    """e = c*(o1 +- o2): the two original equations added or subtracted directly.

    (Any final value such as x = 7 is SOME combination of both equations, so a general
    'combines both' test would accept every method; a direct sum/difference is specific.)
    """
    a, b = sp.symbols("a b")
    sol = sp.solve([sp.Eq(a * p + b * q, r) for p, q, r in zip(o1, o2, e_vec)], [a, b], dict=True)
    return any(s.get(a, 0) != 0 and s.get(b, 0) != 0 and abs(s[a] / s[b]) == 1 for s in sol)


def _is_value_line(L, R, vars_):
    """'x = -4': a stated value. For some systems it coincides with E1 - E2, so it is not
    evidence of elimination on its own."""
    try:
        return L.replace(" ", "") in map(str, vars_) and not _parse(R).free_symbols
    except Exception:  # noqa: BLE001
        return False


def check(method, text, vars_, A, b):
    """Return (faithful: bool, evidence: str)."""
    vars_ = list(vars_)
    n = len(vars_)
    origs = [_vec(sum(A[i, j] * vars_[j] for j in range(n)) - b[i], vars_) for i in range(n)]
    eqs = equations(text)
    vecs = [(L, R, e, _vec(e, vars_)) for L, R, e in eqs]

    def scaled():
        """An original equation multiplied through by k (|k| != 1), not an isolation 'v = ...'."""
        for L, R, e, v in vecs:
            if L.replace(" ", "") in map(str, vars_) or R.replace(" ", "") in map(str, vars_):
                continue
            if len(e.free_symbols) >= 2:
                for o in origs:
                    k = _ratio_to(v, o)
                    if k is not None and abs(k) != 1:
                        return f"scaled equation {L}={R}"
        return None

    def isolation(require_x_rhs=False):
        found = []
        for L, R, e, v in vecs:
            Ls = L.replace(" ", "")
            if Ls in map(str, vars_):
                try:
                    rfs = _parse(R).free_symbols
                except Exception:  # noqa: BLE001
                    continue
                others = rfs - {SYMS[Ls]}
                if others and SYMS[Ls] not in rfs:
                    for i, o in enumerate(origs):
                        if _ratio_to(v, o) is not None:
                            found.append((i, Ls, R))
        return found

    if method == "substitution" and n == 2:
        iso = isolation()
        iso_eqs = {i for i, _, _ in iso}
        both_y = {i for i, L, _ in iso if L == str(vars_[1])} == {0, 1}   # that is graphing
        one_var = any(len(e.free_symbols) == 1 for _, _, e, _ in vecs)
        sc = scaled()
        ok = bool(iso) and len(iso_eqs) == 1 and not both_y and one_var and not sc
        return ok, f"isolated_in_equations={sorted(iso_eqs)} one_var={one_var} scaled={sc}"
    if method == "elimination" and n == 2:
        sc = scaled()
        comb = any(len(e.free_symbols) == 1 and _adds_or_subtracts(v, *origs)
                   and not _is_value_line(L, R, vars_) for L, R, e, v in vecs)
        iso = isolation()
        return bool(sc) or (comb and not iso), f"scaled={sc} combined={comb} isolation={bool(iso)}"
    if method == "graphing" and n == 2:
        x_, y_ = vars_
        covered = set()
        for i, L, R in isolation():
            if L == str(y_):
                covered.add(i)
        for L, R, e, v in vecs:          # vertical lines x = c
            if L.replace(" ", "") == str(x_) and not e.has(y_):
                for i, o in enumerate(origs):
                    if o[1] == 0 and _ratio_to(v, o) is not None:
                        covered.add(i)
        return covered == {0, 1}, f"slope-intercept forms for equations {sorted(covered)}"
    if method == "cramers_rule":
        nums = numbers(text)
        D = A.det()
        Dj = []
        for j in range(n):
            Aj = A.copy()
            Aj[:, j] = b
            Dj.append(Aj.det())
        # D_x-style or determinant-bar notation; '\det(A)' alone also appears in the inverse method
        notation = bool(re.search(r"D_\{?[xyz]|vmatrix", text))
        hits = sum(d in nums for d in Dj)
        return (D in nums) and hits >= 1 and notation, f"det(A) shown={D in nums} det(A_j) shown={hits}/{n} notation={notation}"
    if method == "inverse_matrix":
        if A.det() == 0:
            return False, "singular"
        Ainv, adj = A.inv(), A.adjugate()
        ok = any(M.shape == A.shape and (M == Ainv or M == adj) for M in matrices(text))
        return ok, f"A^-1 or adj(A) shown={ok}"
    if method == "gaussian_elimination":
        aug = A.row_join(b)
        ok = False
        for M in matrices(text):
            if M.shape == aug.shape and M != aug and M.rank() == n and aug.col_join(M).rank() == n:
                ok = True
                break
        return ok, f"row-reduced augmented matrix shown={ok}"
    return False, f"method {method} not applicable to {n} variables"


def validate():
    """Recall on gold + cross-method specificity, for the structural and keyword checks."""
    gold = defaultdict(list)    # system_key -> [(method, text, vars, A, b)]
    for split in ("train", "valid", "test"):
        for line in open(os.path.join(ROOT, "data", "train_worked", "sft", f"{split}.jsonl"), encoding="utf-8"):
            m = json.loads(line)["messages"]
            user, ans = m[1]["content"], m[2]["content"]
            method = re.search(r"Method:\s*([a-z_]+)", ans).group(1)
            si = system_of(extract_system(user.split("\n", 1)[1]))
            if si:
                gold[user.split("\n", 1)[1]].append((method, ans, *si))
    methods = ["substitution", "elimination", "graphing", "cramers_rule", "inverse_matrix", "gaussian_elimination"]
    res = {k: {m: {"recall": [0, 0], "false_accept": [0, 0]} for m in methods} for k in ("structural", "keyword")}
    for items in gold.values():
        for req in methods:
            for meth, text, vars_, A, b in items:
                if req in ("substitution", "elimination", "graphing") and len(vars_) != 2:
                    continue
                s_ok, _ = check(req, text, vars_, A, b)
                k_ok = keyword_faithful(req, text)
                key = "recall" if meth == req else "false_accept"
                for name, ok in (("structural", s_ok), ("keyword", k_ok)):
                    res[name][req][key][0] += int(ok)
                    res[name][req][key][1] += 1
    table = {name: {m: {k: round(v[0] / v[1], 3) if v[1] else None for k, v in d.items()} | {"n_gold": d["recall"][1]}
                    for m, d in r.items()} for name, r in res.items()}
    return table


if __name__ == "__main__":
    t = validate()
    out = os.path.join(ROOT, "data", "train_worked", "faithfulness_validation.json")
    json.dump(t, open(out, "w"), indent=2)
    print("method                 | structural recall / false-accept | keyword recall / false-accept")
    for m in t["structural"]:
        s, k = t["structural"][m], t["keyword"][m]
        print(f"{m:22s} | {s['recall']:.3f} / {s['false_accept']:.3f}               | {k['recall']:.3f} / {k['false_accept']:.3f}   (n={s['n_gold']})")
