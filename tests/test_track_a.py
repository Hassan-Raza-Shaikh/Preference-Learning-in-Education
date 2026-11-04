"""Tests for Track A follow-ups (A1 pair builder, A2 faithfulness, A4 parser v2)."""
import random

import sympy as sp

from experiments.dpo_pair_diagnostics import shared_prefix
from experiments.faithfulness import check
from experiments.onpolicy_dpo import build_pairs
from oatutor_extract.parse_v2 import extract_system_v2, from_augmented, split_run_together

x, y = sp.symbols("x y")
A = sp.Matrix([[2, -6], [3, -4]])
b = sp.Matrix([0, 5])                     # solution x=3, y=1
V = [x, y]

SUB = """Method: substitution
1. Write the system: $$2x-6y=0$$ and $$3x-4y=5$$.
2. Solve equation 1 for $$x$$: $$2x=0+6y$$, so $$x=3 y$$.
3. Substitute $$x=3 y$$ into equation 2: $$3\\left(3 y\\right)-4y=5$$.
4. Combine like terms: $$5y=5$$.
5. Solve for $$y$$: $$y=1$$.
6. Back-substitute $$y=1$$: $$x=3 y=3=3$$.
Solution: $$x=3, y=1$$."""
ELIM = """Method: elimination
1. Write the system: $$2x-6y=0$$ and $$3x-4y=5$$.
2. Make the $$y$$ coefficients match: multiply equation 1 by $$-4$$ and equation 2 by $$-6$$.
3. Equation 1 becomes $$-8x+24y=0$$; equation 2 becomes $$-18x+24y=-30$$.
4. Subtract equation 2 from equation 1 to eliminate $$y$$: $$10x=30$$.
5. Solve for $$x$$: $$x=3$$.
6. Back-substitute $$x=3$$ into equation 1: $$2x-6y=0$$ gives $$6-6y=0$$, so $$y=1$$.
Solution: $$x=3, y=1$$."""


# ------------------------------------------------------------------ A2
def test_structural_faithfulness_separates_methods():
    assert check("substitution", SUB, V, A, b)[0]
    assert not check("elimination", SUB, V, A, b)[0]
    assert check("elimination", ELIM, V, A, b)[0]
    # the keyword metric accepted this ('Back-substitute'); the structural check must not
    assert not check("substitution", ELIM, V, A, b)[0]
    assert not check("graphing", SUB, V, A, b)[0]


def test_structural_faithfulness_matrix_methods():
    inv = "$$A^{-1}=\\begin{bmatrix}-\\frac{2}{5} & \\frac{3}{5}\\\\-\\frac{3}{10} & \\frac{1}{5}\\end{bmatrix}$$"
    assert check("inverse_matrix", inv, V, A, b)[0]
    assert not check("inverse_matrix", inv.replace("\\frac{3}{5}", "\\frac{4}{5}"), V, A, b)[0]   # CAN-FAIL
    gauss = "$$\\begin{bmatrix}2 & -6 & 0\\\\0 & 5 & 5\\end{bmatrix}$$"
    assert check("gaussian_elimination", gauss, V, A, b)[0]
    assert not check("gaussian_elimination", "$$\\begin{bmatrix}2 & -6 & 0\\\\3 & -4 & 5\\end{bmatrix}$$", V, A, b)[0]
    cr = "$$D=10$$, $$D_{x}=30$$, so $$x=3$$"
    assert check("cramers_rule", cr, V, A, b)[0]
    assert not check("cramers_rule", "$$\\det(A)=10$$ and 30", V, A, b)[0]


# ------------------------------------------------------------------ A1
def test_onpolicy_pairs_use_own_samples_and_gold_fallback():
    prompt = "Solve the system of equations using substitution.\n$$2x-6y=0$$  $$3x-4y=5$$"
    recs = [
        {"prompt": prompt, "gold": SUB, "samples": ["... Solution: x=3, y=1", "... Solution: x=1, y=3"]},
        {"prompt": prompt, "gold": SUB, "samples": ["x=0, y=0", "x=5, y=5"]},
        {"prompt": prompt, "gold": SUB, "samples": ["x=3, y=1", "x=3, y=1"]},
    ]
    pairs, stats = build_pairs(recs, random.Random(0))
    assert stats == {"prompts": 3, "all_correct": 1, "all_wrong": 1, "mixed": 1, "unparsed": 0}
    assert pairs[0]["chosen_source"] == "own_sample" and "x=1, y=3" in pairs[0]["rejected"]
    assert pairs[1]["chosen_source"] == "gold" and pairs[1]["chosen"] == SUB


def test_shared_prefix():
    assert shared_prefix("abcdef", "abcxyz") == 3
    assert shared_prefix("", "abc") == 0


# ------------------------------------------------------------------ A4
def test_parse_v2_formats():
    assert split_run_together("-3x+y=8-x+2y=-9") == ["-3x+y=8", "-x+2y=-9"]
    assert split_run_together("x=3y=3") == []
    eqs, how = extract_system_v2("Solve the systems of equations: 6x-5y=-1,2x+y=13")
    assert how == "plain_text" and len(eqs) == 2
    eqs, how = extract_system_v2("Solve $$3x-4z=-1;$$ $$2y+3z=2;$$ $$2x+3y=6$$")
    assert how == "trailing_punctuation" and len(eqs) == 3
    eqs, how = extract_system_v2("$$mat({1, -2, 2, 3}, {2, 1, -2, 1}, {4, -1, 2, 0})$$")
    assert how == "augmented_matrix" and len(eqs) == 3
    assert from_augmented("0 & 0 & 0 \\\\ 1 & 1 & 2") == []          # degenerate row rejected
    assert extract_system_v2("Find the determinant of $$\\begin{bmatrix}1 & 2\\\\3 & 4\\end{bmatrix}$$")[1] == "unparsed"
