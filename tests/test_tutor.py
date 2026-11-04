"""Tests for the tutor proof of concept (Track B).

Several tests are deliberately 'can fail' checks: they inject a known error and assert
that the safeguard catches it, so a passing suite means the safeguard actually works.
"""
import json
import os
import random
import shutil
import threading
import urllib.error
import urllib.request

import pytest
import sympy as sp

from tutor import bank as B
from tutor import explanations as E
from tutor import learner_model as L
from tutor.grading import grade, parse_answer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = B.load()


def _p(pid=None, method="substitution"):
    for p in BANK:
        if (pid is None or p["id"] == pid) and method in p["methods"]:
            return p
    raise LookupError


# ------------------------------------------------------------------ grading
def test_parse_forms():
    v = ["x", "y"]
    assert parse_answer("x=2, y=-1/3", v) == {"x": 2, "y": sp.Rational(-1, 3)}
    assert parse_answer("(2, -1/3)", v) == {"x": 2, "y": sp.Rational(-1, 3)}
    assert parse_answer("y = 0.5; x = -4", v) == {"x": -4, "y": sp.Rational(1, 2)}
    assert parse_answer("x=\\frac{1}{2}, y=3", v) == {"x": sp.Rational(1, 2), "y": 3}
    for bad in ["", "x=1", "z=1, x=2", "hello"]:
        with pytest.raises(ValueError):
            parse_answer(bad, v)


def test_grade_exact_and_diagnosis():
    A, b, ref = [[1, 1], [1, -1]], [3, 1], ["2", "1"]              # x=2, y=1
    assert grade("x=2, y=1", ["x", "y"], A, b, ref)["correct"]
    assert not grade("x=2.0001, y=1", ["x", "y"], A, b, ref)["correct"]   # no tolerance
    assert "swapped" in grade("x=1, y=2", ["x", "y"], A, b, ref)["message"]
    assert "sign" in grade("x=-2, y=1", ["x", "y"], A, b, ref)["message"]
    A, b, ref = [[3, 0], [0, 1]], [1, 1], ["1/3", "1"]              # x=1/3
    r = grade("x=0.333, y=1", ["x", "y"], A, b, ref)
    assert not r["correct"] and "fractions" in r["message"]


# ------------------------------------------------------------------ bank / verification
def test_every_bank_solution_verifies():
    for p in BANK:
        A, b = B.matrices(p)
        for m, sol in p["methods"].items():
            g = grade(sol["final_answer"].replace("\\frac{", "").replace("}{", "/").replace("}", ""),
                      p["variables"], A, b, p["reference"])
            assert g["correct"], (p["id"], m)


def test_step_checker_catches_injected_error():
    """CAN-FAIL CHECK: corrupt one displayed number; the step checker must flag it."""
    p = _p(method="elimination")
    vars_ = [sp.Symbol(v) for v in p["variables"]]
    ref = [sp.Rational(r) for r in p["reference"]]
    steps = list(p["methods"]["elimination"]["steps"])
    ok, _, fails = B.check_steps(steps, vars_, ref)
    assert ok > 0 and not fails
    i = next(k for k, s in enumerate(steps) if "Subtract" in s)
    bad = list(steps)
    bad[i] = steps[i][:steps[i].rindex("=") + 1] + "999$$."     # wrong right-hand side
    _, _, fails = B.check_steps(bad, vars_, ref)
    assert fails, "an injected wrong equation was not detected"


def test_cramer_determinants_checked():
    p = _p(method="cramers_rule")
    A, _ = B.matrices(p)
    vars_ = [sp.Symbol(v) for v in p["variables"]]
    ref = [sp.Rational(r) for r in p["reference"]]
    steps = p["methods"]["cramers_rule"]["steps"]
    ok, _, fails = B.check_steps(steps, vars_, ref, detA=sp.Matrix(A).det())
    assert ok >= len(vars_) and not fails
    _, _, fails = B.check_steps(steps, vars_, ref, detA=sp.Matrix(A).det() + 1)   # CAN-FAIL
    assert fails


# ------------------------------------------------------------------ explanations
def test_faded_never_reveals_answer_and_example_differs():
    for p in BANK:
        for m in p["methods"]:
            for st in E.faded_prefix(p, m):
                assert not E._reveals_answer(st, p)
            ex = E.pick_example(p, m, BANK)
            if ex is not None:
                assert ex["id"] != p["id"] and ex["equations_tex"] != p["equations_tex"]
                assert ex["features"]["n_vars"] == p["features"]["n_vars"]


def test_reveal_detector():
    p = {"methods": {"m": {"final_answer": "x=3, y=1"}}}
    assert E._reveals_answer("Solve for $$y$$: $$y=1$$.", p)
    assert E._reveals_answer("so $$x=3 y=3 \\left(1\\right)=3$$.", p)
    assert not E._reveals_answer("Write the system: $$2x+y=1$$.", p)
    assert not E._reveals_answer("so $$x=3 y$$.", p)
    assert not E._reveals_answer("so $$y=10$$.", p)


def test_variants_render_for_all_arms():
    p = _p()
    for arm in ["example", "faded", "outline", "none"]:
        v = E.make_variant(p, "substitution", arm, BANK)
        assert v["blocks"]
        text = json.dumps(v)
        assert "Solution: $$" + p["methods"]["substitution"]["final_answer"] not in text


# ------------------------------------------------------------------ learner model
def test_bkt_moves_in_the_right_direction():
    prm = L.BKTParams()
    assert L.bkt_update(0.3, True, prm) > 0.3
    assert L.bkt_update(0.3, False, prm) < 0.3 + prm.p_transit


def test_policy_helpers():
    rng = random.Random(0)
    ls, cs, cfg = L.LearnerState("a"), L.ClassStats(), L.PolicyConfig()
    two = L.offer_two(ls, cs, "low", cfg, rng)
    assert len(set(two)) == 2
    assert L.rule_arm("low") == "example" and L.rule_arm("high") == "outline"
    assert L.rule_arm("low", allowed=("outline", "none")) == "outline"
    for _ in range(200):                       # strong evidence should dominate the choice
        L.record_outcome(ls, cs, "low", "faded", True)
        L.record_outcome(ls, cs, "low", "none", False)
    picks = [L.choose_arm(ls, cs, "low", cfg, rng) for _ in range(50)]
    assert picks.count("faded") > 40


# ------------------------------------------------------------------ engine + app
@pytest.fixture
def tutor_env(tmp_path):
    from tutor.engine import Tutor
    cfg = tmp_path / "config.json"
    shutil.copy(os.path.join(ROOT, "tutor", "config.json"), cfg)
    return Tutor(str(cfg), data_dir=str(tmp_path / "runs"), seed=1), tmp_path


def _correct_answer(t, lid):
    p = t.by_id[t.pending[lid]["problem_id"]]
    return ", ".join(f"{v}={r}" for v, r in zip(p["variables"], p["reference"]))


def test_engine_full_loop_and_logging(tutor_env):
    from tutor.engine import TutorError
    t, tmp = tutor_env
    with pytest.raises(TutorError):
        t.start("Ali Khan")                          # names / spaces rejected
    t.start("7B-01")
    r = t.next_problem("7B-01")
    assert r["mode"] == "learner_choice" and len(r["offered"]) == 2
    with pytest.raises(TutorError):
        t.answer("7B-01", "x=1, y=2")                # must choose help first
    t.choose("7B-01", r["offered"][0]["arm"])
    out = t.answer("7B-01", _correct_answer(t, "7B-01"))
    assert out["correct"] and out["mastery"][r["method"]] > 0.1
    t.rate("7B-01", 3)
    log = [json.loads(l) for l in open(tmp / "runs" / "demo" / "events.jsonl")]
    assert [e["event"] for e in log] == ["learner_created", "problem_shown", "explanation_chosen", "answer", "rating"]
    assert "answer" not in log[3] and set(log[3]["answer_values"]) == set(t.by_id[log[3]["problem_id"]]["variables"])
    t.next_problem("7B-01")
    t.choose("7B-01", t.pending["7B-01"]["offered"][0])
    t.answer("7B-01", "my name is Sara")                      # privacy: free text is never logged
    assert "Sara" not in open(tmp / "runs" / "demo" / "events.jsonl").read()
    # state survives a restart
    from tutor.engine import Tutor
    t2 = Tutor(t.config_path, data_dir=str(tmp / "runs"))
    assert t2.learners["7B-01"].history[0]["correct"] is True


def test_engine_modes_and_config_validation(tutor_env):
    from tutor.engine import TutorError
    t, _ = tutor_env
    t.set_config({"mode": "fixed", "fixed_arm": "outline"})
    assert t.next_problem("c1")["explanation"]["arm"] == "outline"
    t.set_config({"mode": "rule"})
    assert t.next_problem("c2")["explanation"]["arm"] == "example"        # new learner = low mastery
    for bad in [{"mode": "magic"}, {"skills": []}, {"preference_weight": 2},
                {"mode": "learner_choice", "allowed_arms": ["none"]}]:
        with pytest.raises(TutorError):
            t.set_config(bad)


def test_app_serves_pages_and_blocks_traversal(tutor_env):
    from http.server import ThreadingHTTPServer
    from tutor.app import make_handler
    t, _ = tutor_env
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(t, "s3cret"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(path, body, headers=None):
        req = urllib.request.Request(base + path, data=body, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            return urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e:
            return e.code

    def get(path, headers=None):
        try:
            return urllib.request.urlopen(urllib.request.Request(base + path, headers=headers or {})).status
        except urllib.error.HTTPError as e:
            return e.code

    try:
        assert b"Maths Tutor" in urllib.request.urlopen(base + "/").read()
        assert get("/static/vendor/katex/katex.min.js") == 200
        assert get("/static/%2e%2e/engine.py") == 404
        assert post("/api/start", b'{"learner_id": "bad id"}') == 400
        assert post("/api/start", b'[1, 2]') == 400                      # non-object body: no crash
        # teacher data and settings need the key (pupils share the network)
        assert get("/api/teacher") == 401
        assert get("/api/teacher", {"X-Teacher-Key": "wrong"}) == 401
        assert get("/api/teacher", {"X-Teacher-Key": "s3cret"}) == 200
        assert post("/api/config", b'{"config": {"mode": "fixed"}}') == 401
        assert t.cfg["mode"] != "fixed"
        assert post("/api/config", b'{"config": {"mode": "fixed"}}', {"X-Teacher-Key": "s3cret"}) == 200
        assert t.cfg["mode"] == "fixed"
    finally:
        srv.shutdown()


def test_review_fixes_double_submit_codes_skips_and_stale_block(tutor_env):
    from tutor.engine import TutorError
    t, tmp = tutor_env
    # 1. a second submission after the solution is shown must not count
    r = t.next_problem("d1")
    t.choose("d1", r["offered"][0]["arm"])
    t.answer("d1", "x=99, y=99")
    with pytest.raises(TutorError):
        t.answer("d1", _correct_answer(t, "d1"))
    assert len(t.learners["d1"].history) == 1 and t.learners["d1"].history[0]["correct"] is False
    # 2. skipping an unanswered problem is logged
    t.next_problem("d1")
    t.next_problem("d1")
    assert any(json.loads(l)["event"] == "problem_skipped" for l in open(tmp / "runs" / "demo" / "events.jsonl"))
    # 3. allow-list: a typo is rejected instead of creating a new pupil
    t.set_config({"learner_codes": ["7B-01", "7B-02"]})
    with pytest.raises(TutorError):
        t.start("7B-0l")
    t.start("7B-02")
    # 4. changing the study arms starts a fresh randomisation block
    t.set_config({"study": {"arms": ["fixed", "rule"], "counterbalance": False}})
    t.start("7B-01")
    t.set_config({"study": {"arms": ["rule", "learner_choice"], "counterbalance": False}})
    assert t.study_state["block"] == []


def test_logged_arm_is_the_help_actually_shown(tutor_env):
    t, _ = tutor_env
    target = None
    for p in t.bank:                      # a problem/method whose faded view must fall back
        for m in p["methods"]:
            if m in t.cfg["skills"] and p["features"]["n_vars"] in t.cfg["n_vars"] and not E.faded_prefix(p, m):
                target = (p, m)
    if target is None:
        pytest.skip("no fallback case in the current bank")
    p, m = target
    t.set_config({"mode": "fixed", "fixed_arm": "faded"})
    t.bank = [p] + [q for q in t.bank if q["id"] != p["id"] and m not in q["methods"]]   # force this problem
    t.next_problem("f1", method=m)
    assert t.pending["f1"]["arm"] == "outline"


# ------------------------------------------------------------------ simulation sanity
def test_simulation_oracle_beats_everyone_and_is_deterministic():
    from tutor import simulate as S
    scen = S.SCENARIOS["B_differences_honest_preferences"]
    a = S.run_class("oracle", scen, 5, n_learners=10, T=20)
    assert a == S.run_class("oracle", scen, 5, n_learners=10, T=20)
    others = [S.run_class(p, scen, 5, n_learners=10, T=20)["mastered"] for p in S.POLICIES if p != "oracle"]
    assert a["mastered"] >= max(others) - 0.05


# ------------------------------------------------------------------ assessment (pre/post)
def test_assessment_forms_are_parallel_and_held_out(tutor_env):
    from tutor.assessment import build_forms
    t, _ = tutor_env
    forms = build_forms(t.bank, t.cfg["skills"], t.cfg["n_vars"], per_method=2)
    pre = {i["problem_id"] for i in forms["pre"]}
    post = {i["problem_id"] for i in forms["post"]}
    assert len(pre) == len(post) == 2 * len(t.cfg["skills"]) and not pre & post
    for a, b in zip(forms["pre"], forms["post"]):              # paired items: same method, similar
        pa, pb = t.by_id[a["problem_id"]], t.by_id[b["problem_id"]]
        assert a["method"] == b["method"]
        assert pa["features"]["n_vars"] == pb["features"]["n_vars"]
    t.set_config({"assessment": forms})
    for _ in range(40):                                         # never practised on test items
        r = t.next_problem("p1")
        assert r["problem"]["problem_id"] not in pre | post
        t.pending.pop("p1")


def test_assessment_flow_hides_feedback_and_skips_learner_model(tutor_env):
    from tutor.assessment import build_forms
    from tutor.engine import TutorError
    t, _ = tutor_env
    t.set_config({"assessment": build_forms(t.bank, t.cfg["skills"], t.cfg["n_vars"], 1),
                  "assessment_open": "pre"})
    q = t.assess_next("s1")
    p = t.by_id[q["problem"]["problem_id"]]
    out = t.assess_answer("s1", p["id"], ", ".join(f"{v}={r}" for v, r in zip(p["variables"], p["reference"])))
    assert out == {"recorded": True, "status": {"form": "pre", "answered": 1, "total": 3}}
    assert "correct" not in out and "solution" not in out                 # no feedback in a test
    assert t.learners["s1"].mastery == {} and t.learners["s1"].history == []
    assert t.learners["s1"].assessment["pre"][p["id"]] is True
    with pytest.raises(TutorError):
        t.assess_answer("s1", p["id"], "x=0, y=0")                         # no second attempt
    assert t.assess_answer("s1", t.assess_next("s1")["problem"]["problem_id"], "hello")["recorded"] is False


# ------------------------------------------------------------------ study randomisation
def test_study_block_randomisation_and_counterbalancing(tutor_env):
    from collections import Counter
    from tutor.assessment import build_forms
    from tutor.engine import TutorError
    t, _ = tutor_env
    with pytest.raises(TutorError):
        t.set_config({"study": {"arms": ["fixed"]}})
    t.set_config({"study": {"arms": ["fixed", "rule", "learner_choice"], "counterbalance": True},
                  "assessment": build_forms(t.bank, t.cfg["skills"], t.cfg["n_vars"], 1), "assessment_open": "pre"})
    for i in range(12):                         # two full blocks of 6
        t.start(f"s{i:02d}")
    cells = Counter((ls.study_arm, ls.form_order) for ls in t.learners.values())
    assert set(cells.values()) == {2} and len(cells) == 6          # perfectly balanced
    a = next(ls for ls in t.learners.values() if ls.form_order == "AB")
    b = next(ls for ls in t.learners.values() if ls.form_order == "BA")
    qa = t.assess_next(a.learner_id)["problem"]["problem_id"]
    qb = t.assess_next(b.learner_id)["problem"]["problem_id"]
    assert qa in {i["problem_id"] for i in t.cfg["assessment"]["pre"]}
    assert qb in {i["problem_id"] for i in t.cfg["assessment"]["post"]}  # BA takes form B first
    fx = next(ls for ls in t.learners.values() if ls.study_arm == "fixed")
    assert t.next_problem(fx.learner_id)["explanation"]["arm"] == t.cfg["fixed_arm"]


def test_study_analysis_end_to_end(tutor_env):
    """A tiny simulated pilot through the real engine, then the analysis script."""
    from tutor.analyze_study import analyse, load
    from tutor.assessment import build_forms
    t, tmp = tutor_env
    t.set_config({"study": {"arms": ["fixed", "learner_choice"], "counterbalance": True},
                  "assessment": build_forms(t.bank, t.cfg["skills"], t.cfg["n_vars"], 1)})
    rng = random.Random(3)
    lids = [f"k{i}" for i in range(8)]

    def quiz(form, p_right):
        t.set_config({"assessment_open": form})
        for lid in lids:
            while not (q := t.assess_next(lid))["done"]:
                p = t.by_id[q["problem"]["problem_id"]]
                right = ", ".join(f"{v}={r}" for v, r in zip(p["variables"], p["reference"]))
                t.assess_answer(lid, p["id"], right if rng.random() < p_right else "x=99, y=99")

    quiz("pre", 0.3)
    t.set_config({"assessment_open": None})
    for lid in lids:
        for _ in range(6):
            r = t.next_problem(lid)
            if "offered" in r:
                t.choose(lid, r["offered"][0]["arm"])
            t.answer(lid, _correct_answer(t, lid) if rng.random() < 0.6 else "x=99, y=99")
            t.rate(lid, rng.choice([1, 2, 3]))
    quiz("post", 0.7)
    out = analyse(*load(str(tmp / "runs"), "demo"), t.cfg["mode"])
    by = out["rq1_rq2_pre_post_by_condition"]
    assert set(by) == {"fixed", "learner_choice"} and sum(v["n"] for v in by.values()) == 8
    assert len(out["gain_contrasts"]) == 1
    assert set(out["usage"]) == {"fixed", "learner_choice"}


# ------------------------------------------------------------------ BKT fitting
def _simulate_bkt(prm, n_learners, n_steps, seed):
    rng = random.Random(seed)
    seqs = []
    for _ in range(n_learners):
        known = rng.random() < prm.p_init
        seq = []
        for _ in range(n_steps):
            seq.append(int(rng.random() < ((1 - prm.p_slip) if known else prm.p_guess)))
            known = known or rng.random() < prm.p_transit
        seqs.append(seq)
    return seqs


def test_bkt_fit_recovers_known_parameters():
    """CAN-FAIL CHECK: data generated from known parameters must be fitted back closely."""
    from tutor.fit_bkt import fit, loglik
    for true in (L.BKTParams(0.2, 0.15, 0.1, 0.2), L.BKTParams(0.5, 0.05, 0.05, 0.3)):
        seqs = _simulate_bkt(true, 400, 12, seed=7)
        est, ll = fit(seqs)
        assert ll >= loglik(seqs, true) - 1e-6                       # at least as good as the truth
        for k in ("p_init", "p_transit", "p_slip", "p_guess"):
            assert abs(getattr(est, k) - getattr(true, k)) < 0.08, (k, est, true)


def test_engine_uses_per_skill_bkt(tutor_env):
    from tutor.engine import TutorError
    t, _ = tutor_env
    t.set_config({"bkt_per_skill": {"elimination": {"p_init": 0.6, "p_transit": 0.1, "p_slip": 0.1, "p_guess": 0.2}}})
    v = t.start("b1")["mastery"]
    assert v["elimination"] == 0.6 and v["substitution"] == 0.1
    assert t.next_problem("b1")["method"] != "elimination"          # weakest skill first
    with pytest.raises(TutorError):
        t.set_config({"bkt_per_skill": {"elimination": {"p_init": 1.5}}})


def test_learner_codes():
    from tutor.codes import make_codes
    assert make_codes("7B", 3) == ["7B-01", "7B-02", "7B-03"]
    assert make_codes("C", 120)[-1] == "C-120"
    with pytest.raises(ValueError):
        make_codes("Mr Smith", 2)


# ------------------------------------------------------------------ sensitivity analysis
def test_simulator_uses_custom_learning_table_and_sensitivity_cell_runs():
    from tutor import simulate as S
    from tutor.sensitivity import BASE_VARIANTS, cell
    sl = S.SimLearner(random.Random(0), 0.0, 0.5, base=BASE_VARIANTS["no reversal"])
    sl.level["substitution"] = 1
    assert max(S.ARMS, key=lambda a: sl.p_learn("substitution", a)) == "example"     # no reversal at level 1
    sl2 = S.SimLearner(random.Random(0), 0.0, 0.5)
    sl2.level["substitution"] = 1
    assert max(S.ARMS, key=lambda a: sl2.p_learn("substitution", a)) == "faded"      # default table: reversal
    out = cell({"sigma": 0.6, "rho": 0.8}, T=5, n_classes=3, seed=1)
    assert set(out["contrasts"]) == {"rule_by_mastery - fixed_example", "adaptive_outcomes - rule_by_mastery",
                                     "learner_choice - rule_by_mastery", "oracle - rule_by_mastery"}
    assert out == cell({"sigma": 0.6, "rho": 0.8}, T=5, n_classes=3, seed=1)            # deterministic
