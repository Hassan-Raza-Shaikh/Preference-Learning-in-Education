"""Unit tests for the deterministic multi-method generator."""
import os
import sys

import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oatutor_extract.multimethod import (  # noqa: E402
    parse_equation, extract_system, system_of, reference_solution,
    satisfies, gen_substitution, gen_elimination, gen_cramer,
    gen_matrix_inverse, gen_gaussian, gen_graphing, make_rejected, SYMS,
)

x, y, z = SYMS['x'], SYMS['y'], SYMS['z']


def _sys(question):
    eqs = extract_system(question)
    vars_, A, b = system_of(eqs)
    ref = reference_solution(vars_, A, b)
    return vars_, A, b, ref


def test_parse_rejects_nonlinear():
    assert parse_equation("x*y=1") is None
    assert parse_equation("x^2+y=1") is None
    assert parse_equation("2x+3y=6") is not None


def test_parse_fraction_and_implicit_mult():
    vars_, A, b, ref = _sys("$$x+y=2$$ $$-\\frac{3}{4}x+y=0$$")
    assert ref == [sp.Rational(8, 7), sp.Rational(6, 7)]
    assert satisfies(A, b, vars_, ref)


def test_all_methods_agree_2var():
    vars_, A, b, ref = _sys("$$2x-6y=0$$ $$3x-4y=5$$")
    assert ref == [sp.Integer(3), sp.Integer(1)]
    for gen in (gen_substitution, gen_elimination, gen_cramer,
                gen_matrix_inverse, gen_gaussian, gen_graphing):
        out = gen(vars_, A, b, ref)
        assert out is not None, gen.__name__
        assert [sp.nsimplify(v) for v in out["final"]] == ref, gen.__name__


THREEVAR = "$$5x+3y+9z=-1$$ $$-2x+3y-z=-2$$ $$-x-4y+5z=1$$"  # det = 187, unique


def test_methods_agree_3var():
    vars_, A, b, ref = _sys(THREEVAR)
    assert ref is not None
    for gen in (gen_cramer, gen_matrix_inverse, gen_gaussian):
        out = gen(vars_, A, b, ref)
        assert out is not None
        assert [sp.nsimplify(v) for v in out["final"]] == ref


def test_singular_3var_is_skipped():
    # det = 0 -> no unique solution, and det-based methods must decline
    vars_, A, b = system_of(extract_system("$$x+2y-z=3$$ $$2x-y+2z=6$$ $$x-3y+3z=4$$"))
    assert reference_solution(vars_, A, b) is None
    assert gen_cramer(vars_, A, b, None) is None
    assert gen_matrix_inverse(vars_, A, b, None) is None


def test_2var_only_methods_skip_3var():
    vars_, A, b, ref = _sys(THREEVAR)
    assert gen_substitution(vars_, A, b, ref) is None
    assert gen_elimination(vars_, A, b, ref) is None
    assert gen_graphing(vars_, A, b, ref) is None


def test_rejected_is_verifiably_wrong():
    vars_, A, b, ref = _sys("$$2x-6y=0$$ $$3x-4y=5$$")
    out = gen_elimination(vars_, A, b, ref)
    steps, wrong, strategy = make_rejected(vars_, A, b, out["final"], out["steps"])
    assert not satisfies(A, b, vars_, wrong)      # the whole point
    assert wrong != out["final"]
    assert strategy in ("sign_flip", "swap_vars", "off_by_one")


def test_no_unique_solution_returns_none():
    # dependent system (same line) -> infinite solutions
    vars_, A, b = system_of(extract_system("$$x+y=1$$ $$2x+2y=2$$"))
    assert reference_solution(vars_, A, b) is None
