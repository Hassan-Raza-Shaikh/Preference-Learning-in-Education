# Track B: personalised tutor proof of concept

*Built 2026-11-03. Covers milestones M1–M5 of [`01_VISION_AND_PLAN.md`](01_VISION_AND_PLAN.md) §5.
Code: [`../tutor/`](../tutor/). Pilot documents: [`pilot/`](pilot/).*

---

## 1. Plain-language summary (for the supervisor)

We built a working maths tutor for systems of linear equations that:

- **never shows wrong maths:** every worked step comes from the verified Phase 1 engine,
  and a new check confirms that every displayed equation is true;
- **offers four kinds of help** (a worked example on a similar problem, the first steps
  done, a reminder of the method, or no help), and lets the pupil choose, or picks for them;
- **tracks mastery** of each method and gives the next problem in the weakest one;
- **lets teachers configure it** without code, and shows each pupil's progress;
- **is ready for a study:** pre/post quizzes, random assignment of pupils to conditions,
  privacy-safe logging, and an analysis script.

We also tested the *personalisation logic* with simulated pupils, before any child uses it.
The honest results:

- **What worked:** changing the type of help as a pupil's mastery grows (worked example →
  first steps done → reminder) clearly beat always giving worked examples (+0.125 to +0.154
  in the share of skills mastered, in every scenario).
- **What did not:** the tutor's "learn what works for each pupil from right/wrong answers"
  algorithm did **not** identify each pupil's best kind of help within 30 problems. It
  picked it 28–31% of the time, close to chance (25%), and never beat the simple rule above.
  One attempted fix looked good on development data but **failed on held-out data**, and
  is reported as such.
- **What depends on the pupils:** letting pupils choose their help beat the rule only when
  their stated preferences matched what actually helped them (+0.033). It was worse when
  preferences were unrelated to what helped (−0.033), or when pupils did not really differ
  (−0.091).

  Whether real pupils' preferences track what helps them is exactly what the school study
  can measure (research question RQ3). It is the core of the "preference learning" idea.

These are **simulation results under assumptions we wrote**. They show the machinery
works and suggest what to test. They are not evidence about real children.

---

## 2. What was built

| Milestone | Component | Files | Status |
|---|---|---|---|
| M1 | Verified problem bank + explanation variants | `tutor/bank.py`, `tutor/explanations.py`, `tutor/content.py` | done |
| M2 | Learner model: mastery (BKT) + help-type preferences (Thompson sampling) + mastery rule | `tutor/learner_model.py` | done |
| M3 | Web app: learner page, teacher page, exact grading, logging | `tutor/engine.py`, `tutor/app.py`, `tutor/grading.py`, `tutor/static/` | done |
| M4 | Simulated-learner evaluation | `tutor/simulate.py`, `tutor/results/` | done (negative result for the bandit) |
| M5 | Pilot package: quizzes, randomisation, analysis, study design, consent, data plan, teacher guide | `tutor/assessment.py`, `tutor/analyze_study.py`, `docs/pilot/` | drafts done; approvals needed |

Run it:

```bash
python -m tutor.app
```

Then open `http://localhost:8000` (learner) and `/teacher`. Tests:

```bash
python -m pytest tests -q
```

45 pass, including deliberately injected errors that the safeguards must catch.

---

## 3. Correctness guarantees (M1)

- **Problem bank:** 178 unique systems from OATutor (103 with 2 variables, 75 with 3), with
  verified solutions by every applicable method. Up from 128 with the Phase 1 parser; see
  Track A item A4.
- **New step-level check:** every equation displayed in a worked step must hold when the
  true solution is substituted. Cramer's-rule determinants are checked against det(A).
  - **5,983** displayed equations checked, **0 failures**.
  - 1,261 matrix-style displays can't be parsed by the checker; their values are still
    computed by sympy.
  - Built-in self-test: corrupting a step or a determinant must be detected (tests).
- **Display fixes for learners,** without changing Phase 1 data:
  - back-substitution shows the plugged-in value (`x=3y=3(1)=3`, not `x=3y=3=3`);
  - `+1y` is shown as `+y`.
- **Faded examples never reveal the answer:** steps are cut before any line that states a
  final value. Checked on every problem and method.
- **Grading is exact:** answers are substituted into the original equations, and `0.333`
  is not accepted for `1/3`. Short diagnoses are given: wrong sign, swapped values, one value
  right.

## 4. Learner model and modes (M2–M3)

- **Mastery:** Bayesian Knowledge Tracing per method. The parameters are OATutor's defaults,
  which are **placeholders (0.1 for every skill)** and should be fitted to pilot data.
- **Two signals are kept separate on purpose:**
  - *efficacy:* did the pupil solve the problem after that help?
  - *liking:* did they choose it, or rate it useful?

  The teacher sets how much liking counts.
- **Modes:**
  - `learner_choice`: two help types are offered and the pupil picks.
  - `rule`: by mastery, worked example → faded → outline.
  - `adaptive`: Thompson sampling. **Experimental**; it did not beat `rule`.
  - `fixed`: the control condition.
- **Study mode:** block-randomises each new pupil to a condition and counterbalances the
  quiz forms.

## 5. Simulated-learner evaluation (M4)

**Setup.**
- 20 classes × 25 simulated pupils, 30 problems each, 3 methods.
- Each pupil has a hidden skill level per method. How much each kind of help teaches them
  follows the expertise-reversal effect (worked examples help beginners most), multiplied
  by an individual factor.
- Three scenarios:
  - A: no individual differences;
  - B: individual differences, and stated preferences track them;
  - C: individual differences, and stated preferences don't track them.
- Metric: share of skills truly mastered at the end. 95% CIs come from a bootstrap over
  classes.

**Protocol.**
1. Six variants of the adaptive algorithm were tried on a *development* seed
   (`tutor/results/design_search.md`).
2. The best-looking one (D2, rule prior) was confirmed on a *held-out* seed.
3. **It did not replicate:** in scenario A it was worse than the plain rule (−0.066
   [−0.093, −0.038]), and worse than the original design.

The app therefore keeps the original algorithm as an experimental option and offers the
rule as its own mode.

**Held-out results** (original algorithm D0, seed 20270101; `tutor/results/sim_results_D0_heldout.md`):

| policy | A: no differences | B: honest preferences | C: misleading preferences |
|---|---|---|---|
| always worked example | 0.588 | 0.569 | 0.569 |
| random help | 0.638 | 0.689 | 0.689 |
| **mastery rule** | **0.713** | 0.723 | **0.723** |
| adaptive (outcomes) | 0.680 | 0.713 | 0.713 |
| adaptive (outcomes + liking) | 0.669 | 0.703 | 0.697 |
| **learner chooses** | 0.623 | **0.756** | 0.690 |
| oracle (knows the hidden truth) | 0.790 | 0.870 | 0.870 |

| contrast (paired by class) | A | B | C |
|---|---|---|---|
| rule − always worked example | +0.125 [+0.097, +0.155] | +0.154 [+0.119, +0.189] | +0.154 [+0.119, +0.189] |
| learner chooses − rule | −0.091 [−0.131, −0.051] | +0.033 [+0.006, +0.061] | −0.033 [−0.065, +0.000] |
| adaptive − rule | −0.033 [−0.061, −0.006] | −0.011 [−0.042, +0.022] | −0.011 [−0.042, +0.022] |
| how often adaptive picks the pupil's best help | 0.28 | 0.28 | 0.28 |

**Interpretation.**
- Varying support with mastery is the robust win.
- Per-pupil learning from right/wrong answers needs more data than one unit provides: the
  answer mostly reflects what the pupil already knew, not which help they just got.
- Learner choice is a gamble whose payoff depends on RQ3, which only real pupils can
  answer.

**Limits.**
- The simulator's numbers were invented to encode the expertise-reversal effect
  qualitatively; they were not fitted to data.
- One curriculum unit, three methods.

## 6. Pilot readiness (M5)

- Pre/post quiz: two parallel 6-item forms, never used for practice, with no feedback
  during the quiz.
- Random assignment and counterbalancing, built in.
- Privacy by design: only parsed numbers are logged, never typed text. Codes, not names.
  The logs folder is git-ignored.
- Analysis script: gains by condition with bootstrap CIs, and RQ3 agreement.
- Drafts: study design (with an honest power calculation: a pilot of 60–90 pupils is for
  feasibility, not for testing effects), consent and assent templates, data-management
  plan, teacher guide, and a 10-minute demo script for the school.

**Still needed before any pupil uses it:**
1. Ethics approval.
2. A teacher review of the method cards and a sample of solutions.
3. A dry run with adults.
4. Pre-registration.

## 6b. Review fixes (2026-11-04)

A full code review before the merge found these problems. All are fixed, each with a
regression test.

| Problem | Why it mattered | Fix |
|---|---|---|
| Teacher page and settings API had no access control | On the school network, any pupil could see all pupils' data, open the post-test, or change study conditions | Teacher key: private link printed at start-up; 401 without it |
| An answer could be submitted again after the full solution was shown | The second, copied answer counted, inflating mastery and the study data | A second submission is rejected |
| A mistyped code silently created a new pupil | Phantom pupils, and wasted randomisation slots | Optional allow-list (`python -m tutor.codes`) |
| Changing the study arms kept the old randomisation block | Pupils could be assigned to an arm that no longer exists | The block is reset when the arms change |
| Skipped problems were not logged | Missing data for the analysis | `problem_skipped` event |
| When "faded" or "example" fell back to the outline, the log recorded the type that was chosen | Outcomes credited to help that was never shown | The help type actually shown is recorded |
| A request body that was not a JSON object crashed the request | Robustness | Returns 400 |

**Also added:**
- **`tutor/fit_bkt.py`:** fits the mastery-model parameters from the logs. Recovery test:
  parameters within 0.08 with 400 simulated pupils. A single class supports only a pooled
  fit (`--pool`).
- **Per-skill parameters** in the engine.
- **Pinned `requirements.txt`, and CI** that runs the tests on every push and pull
  request.

## 7. Next steps (Track B)

1. A supervisor review of this document and the pilot drafts.
2. The school demo (`pilot/README.md`).
3. An adult dry run, to fix usability problems.
4. Fitting the BKT parameters on the dry-run and pilot data.
5. Extending the help types with **context personalisation:** word problems themed on
   pupil interests, keeping the verified maths identical.
6. Later: other topics, reusing the same "verified engine + learner model" pattern.
