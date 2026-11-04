"""Exact grading of a learner's typed answer.

The answer is parsed to exact rationals and substituted into the ORIGINAL system
(same rule as experiments/evaluate.py). No LLM, no tolerance.

Accepted forms:  "x=2, y=-1/3"   "x = 2; y = -0.5"   "(2, -1/3)"   "2, -1/3"
Decimals are converted exactly ("0.5" -> 1/2); a rounded repeating decimal such as
"0.333" is therefore (correctly) marked wrong, and the learner is told to use fractions.
"""
from __future__ import annotations

import re

import sympy as sp

NUM = r"-?\s*(?:\d+(?:\.\d+)?|\.\d+)(?:\s*/\s*-?\s*\d+(?:\.\d+)?)?"
NAMED = re.compile(rf"([a-zA-Z])\s*=\s*({NUM})")
BARE = re.compile(NUM)


def to_rational(s: str):
    s = s.replace(" ", "")
    if "/" in s:
        p, q = s.split("/", 1)
        q_r = sp.Rational(q)
        if q_r == 0:
            raise ValueError("division by zero")
        return sp.Rational(p) / q_r
    return sp.Rational(s)


def parse_answer(text: str, variables: list[str]):
    """Return {var: Rational} or raise ValueError with a learner-friendly message."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Please type an answer, for example: x=2, y=-1/3")
    text = text.replace("−", "-").replace("\\frac{", "(").replace("}{", ")/(").replace("}", ")")
    text = re.sub(r"\((-?\d+)\)/\((-?\d+)\)", r"\1/\2", text)
    named = NAMED.findall(text)
    if named:
        vals = {}
        for v, n in named:
            v = v.lower()
            if v not in variables:
                raise ValueError(f"'{v}' is not a variable in this system ({', '.join(variables)}).")
            vals[v] = to_rational(n)
        missing = [v for v in variables if v not in vals]
        if missing:
            raise ValueError(f"Please give a value for {', '.join(missing)}.")
        return vals
    nums = BARE.findall(text)
    if len(nums) == len(variables):
        return {v: to_rational(n) for v, n in zip(variables, nums)}
    raise ValueError(f"Please give {len(variables)} values, for example: "
                     + ", ".join(f"{v}=..." for v in variables))


def grade(text: str, variables: list[str], A, b, reference: list):
    """Grade an answer exactly. Returns a dict safe to send to the learner."""
    try:
        vals = parse_answer(text, variables)
    except (ValueError, TypeError, ZeroDivisionError) as e:
        return {"parsed": False, "correct": False, "message": str(e)}
    vec = [vals[v] for v in variables]
    satisfies = all(sp.simplify(sum(A[i][j] * vec[j] for j in range(len(vec))) - b[i]) == 0
                    for i in range(len(b)))
    per_var = {v: bool(sp.simplify(vals[v] - sp.Rational(r)) == 0)
               for v, r in zip(variables, reference)}
    out = {"parsed": True, "correct": bool(satisfies), "per_variable": per_var,
           "values": {v: str(vals[v]) for v in variables},       # what gets logged (never raw text)
           "message": "Correct! Both equations are satisfied." if satisfies else diagnose(vec, reference, variables)}
    if not satisfies and re.search(r"\d\.\d{3,}", text):
        out["message"] += " Tip: use exact fractions such as 1/3 instead of rounded decimals."
    return out


def diagnose(vec, reference, variables):
    """A short, specific hint about a wrong answer (no new maths is generated)."""
    ref = [sp.Rational(r) for r in reference]
    wrong = [v for v, a, r in zip(variables, vec, ref) if a != r]
    for v, a, r in zip(variables, vec, ref):
        if a != r and a == -r:
            return f"Not quite. Check the sign of {v}."
    if len(vec) >= 2 and vec[0] == ref[1] and vec[1] == ref[0] and ref[0] != ref[1]:
        return f"Not quite. It looks like the values of {variables[0]} and {variables[1]} are swapped."
    if len(wrong) < len(variables):
        return "Not quite. " + ", ".join(wrong) + (" is" if len(wrong) == 1 else " are") + \
               " wrong; the other value is right. Recheck the last steps."
    return "Not quite. Substitute your values into both equations to see which one fails."
