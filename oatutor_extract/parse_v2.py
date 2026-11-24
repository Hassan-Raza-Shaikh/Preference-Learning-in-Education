"""Track A item A4: recover more linear systems from OATutor (parser v2).

Phase 1's `multimethod.extract_system` only reads equations in separate $$...$$ blocks of
step 1, so 560 of 751 systems problems were skipped. This module ADDS three recoveries;
it does not change the Phase 1 parser or data:

  1. plain-text equations with no $$ (e.g. 'Solve: 6x-5y=-1,2x+y=13')
  2. two equations run together in one block ('-3x+y=8-x+2y=-9' -> '-3x+y=8', '-x+2y=-9')
  3. augmented matrices ('\\begin{bmatrix} a & b & c \\\\ ... \\end{bmatrix}' or OATutor's
     'mat({a, b, c}, {...})' -> system)
  4. equations with a trailing ';' or '.' inside the $$ block ('$$3x-4z=-1;$$')

Every recovered system still goes through the same verified generators and checks.
Out of scope: nonlinear systems, inequalities, figure-only problems.
"""
from __future__ import annotations

import re

import sympy as sp

from .multimethod import EQ_BLOCK, SYMS, extract_system, parse_equation

OAT_MAT = re.compile(r"mat\((\{[^()]*\}(?:\s*,\s*\{[^()]*\})*)\)")
MATRIX = re.compile(r"\\begin\{[bpv]?matrix\}(.+?)\\end\{[bpv]?matrix\}", re.S)
PLAIN_EQ = re.compile(r"(-?[\d.]*\s*[xyz](?:\s*[-+]\s*[\d.]*\s*[xyz])*\s*=\s*-?\s*[\d.]+)")


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:  # noqa: BLE001 - sympy raises many types on odd input
        return None


def split_run_together(block: str) -> list[str]:
    """'-3x+y=8-x+2y=-9' -> ['-3x+y=8', '-x+2y=-9'] when the middle side is 'const' + 'linear'."""
    parts = block.split("=")
    if len(parts) != 3:
        return []
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?|-?\\frac\{\d+\}\{\d+\})\s*([-+].*[xyz].*)$", parts[1])
    if not m:
        return []
    return [f"{parts[0]}={m.group(1)}", f"{m.group(2)}={parts[2]}"]


def from_augmented(body: str):
    rows = [r for r in re.split(r"\\\\", body) if r.strip()]
    try:
        M = [[sp.Rational(sp.sympify(c.strip().replace("\\frac{", "(").replace("}{", ")/(").replace("}", ")")))
              for c in r.split("&")] for r in rows]
    except Exception:  # noqa: BLE001
        return []
    n = len(M)
    if n not in (2, 3) or any(len(r) != n + 1 for r in M):
        return []
    vs = [SYMS[v] for v in "xyz"[:n]]
    eqs = [sp.Eq(sum(r[j] * vs[j] for j in range(n)), r[n]) for r in M]
    # an all-zero row gives True (0=0) or False (0=c): not a usable square system
    return eqs if all(isinstance(e, sp.Equality) for e in eqs) else []


def extract_system_v2(question: str, stem: str = ""):
    """Return (equations, how) where how names the recovery used ('v1' = Phase 1 parser)."""
    eqs = _safe(extract_system, question) or []
    if len(eqs) >= 2:
        return eqs, "v1"
    # 4. trailing ';' / '.' inside blocks
    cleaned = re.sub(r"\$\$(.+?)[;.]\s*\$\$", r"$$\1$$", question)
    if cleaned != question:
        eqs = _safe(extract_system, cleaned) or []
        if len(eqs) >= 2:
            return eqs, "trailing_punctuation"
    # 2. run-together equations inside a $$ block
    rec = []
    for block in EQ_BLOCK.findall(question):
        for part in split_run_together(block):
            e = _safe(parse_equation, part)
            if e is not None:
                rec.append(e)
    if len(rec) >= 2:
        return rec, "run_together"
    # 1. plain-text equations (no $$)
    if "$$" not in question:
        rec = [e for e in (_safe(parse_equation, s.replace(" ", "")) for s in PLAIN_EQ.findall(question)) if e is not None]
        if len(rec) >= 2:
            return rec, "plain_text"
    # 3. augmented matrix in the question or the problem stem
    for text in (question, stem):
        bodies = MATRIX.findall(text) + [
            "\\\\".join(" & ".join(r.split(",")) for r in re.findall(r"\{([^{}]*)\}", m))
            for m in OAT_MAT.findall(text)]
        for body in bodies:
            rec = from_augmented(body)
            if len(rec) >= 2:
                return rec, "augmented_matrix"
    return [], "unparsed"
