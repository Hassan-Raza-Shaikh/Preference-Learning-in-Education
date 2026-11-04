# Work Log

A dated record of everything done on this project from 2026-11-03 onward, kept so it can
be explained to the supervisor. Newest entries at the top. Earlier work (2026-09-03 →
2026-10-09) is summarised in
[`02_PHASE1_METHOD_CONDITIONED_SOLVING.md`](02_PHASE1_METHOD_CONDITIONED_SOLVING.md) §4.

Each entry records **what** was done, **why**, the **result** (including failures), and
**decisions** made. Results are copied from the run that produced them, never estimated.

---

## 2026-11-04 (night): "Rule + switch" test failed; replication corrects the sensitivity analysis

**Plain-language summary.** We tested the idea from the sensitivity analysis (switch help
type after a wrong answer) with success criteria set in advance, on a fresh seed. It
**failed**.

While checking why, we found that two results from the evening entry **do not
replicate** with new simulated classes:
- the bandit beating the rule when pupils differ a lot;
- random help beating the rule there too.

Both are retracted. The main conclusions *did* replicate:
- the mastery rule beats fixed worked examples;
- learner choice helps only when pupils differ and their preferences strongly track
  what helps;
- misleading preferences hurt.

**What**
- `learner_model.rule_switch_arm` and the simulation policy `rule_switch` (appended last,
  so earlier policies' random streams and results are unchanged; checked).
- `tutor/switch_rule.py`: the pre-registered test, with its protocol in the docstring.
  Results: `tutor/results/switch_rule.md`.
- `tutor/sensitivity.py: replicate_on_fresh_seed()`: 12 key cells re-run on seed 20280101.
  Added to `sensitivity.json/md`, with a note in the summary.
- Docs corrected: `04_PROOF_OF_CONCEPT.md` §5b rewritten, `05_PAPER_PLAN.md`, learning
  guide §3.6 and §6.
- 47 tests pass (new: switch-policy test).

**Findings (copied from the result files)**
- **Rule + switch vs rule:** (a) loses when pupils are identical: −0.040 [−0.075, −0.007]
  at T = 15 and −0.041 [−0.065, −0.013] at T = 30; (b) at σ = 1.0, +0.007 (T = 30) and
  +0.023 (T = 60), n.s. **FAILED.** It does beat random help in 11/12 cells and fixed
  worked examples in 12/12, but neither was a criterion.
- **Replication (seed 20280101):**

  | claim | result | verdict |
  |---|---|---|
  | rule − fixed | +0.139 to +0.191 in 12/12 cells | replicates |
  | bandit − rule at σ = 1.0 | −0.011 (T = 30), +0.001 (T = 60), n.s. | **does not replicate** |
  | random − rule at σ = 1.0 | −0.030 [−0.065, +0.005], −0.011, n.s. | **does not replicate** |
  | choice − rule, ρ = 0.9 and σ ≥ 0.6 | +0.057 to +0.079 in 4/4 cells | replicates |
  | choice − rule, ρ = −0.5 | worse in 4/4 cells | replicates |
  | choice − rule, σ = 1.0 and ρ = 0.5 | +0.006, +0.018, n.s. | not robust |

**Cause of the error (method lesson).** All 48 grid cells on one seed reuse the same
simulated classes. The bandit's "8 winning cells" were one class draw, shown across 4 ρ
values that the bandit ignores and 2 horizons. They were not 8 independent results.

**Decisions**
- `rule_switch` is **not** added to the app (pre-stated decision on failure).
- Headline simulation claims now need a fresh-seed replication before they are reported.

**Next**
- Open the PR for the sensitivity-analysis work.
- P2's remaining blockers: the adult dry run and the write-up.

---

## 2026-11-04 (evening): Simulation sensitivity analysis (for paper P2)

> **Correction (see the "night" entry above):** the Q2 bandit gains at σ = 1.0 and the
> exploratory "random help beats the rule" result did not replicate on a fresh seed and
> are retracted. Q1, Q4 and the learner-choice pattern stand.

**Plain-language summary.** We re-ran the simulated-pupil comparison under 48
combinations of assumptions and 8 different "how pupils learn" tables, to see whether the
earlier conclusions were just artefacts of our chosen numbers.
- The fading rule's advantage held everywhere.
- A deliberate check showed that the simulator *can* make the rule lose. It does when the
  expertise-reversal effect is absent, so it isn't rigged.
- The learning (bandit) tutor never really personalised. Where it looked better, random
  help was equally good.
- Letting pupils choose paid off only when pupils differ a lot *and* their stated
  preferences track what helps them. The pilot must therefore measure both.

**What**
- `tutor/sensitivity.py`: the protocol (4 questions, grid, expected outcomes) written
  before running. New seed 20271201; 20 classes × 25 pupils per cell; original adaptive
  design D0.
- `tutor/simulate.py`: `SimLearner` accepts an alternative learning table. The earlier
  held-out results were re-checked and are unchanged.
- Results: `tutor/results/sensitivity.{md,json,png}`.
- Test: custom-table behaviour and determinism (46 tests pass).
- Docs: `04_PROOF_OF_CONCEPT.md` §5b, `05_PAPER_PLAN.md` (P2 rows), learning guide §3.6.

**Findings (copied from `tutor/results/sensitivity.md`)**
- **Q1:** rule > always-worked-example in 48/48 cells.

  | learning table | rule − fixed |
  |---|---|
  | default | +0.149 |
  | weak reversal | +0.078 |
  | 5 random perturbations | +0.113 to +0.251 |

- **Q4, can-fail check:** with no expertise reversal, rule − fixed = −0.043
  [−0.078, −0.012]. **Passed.**
- **Q2, bandit − rule:**

  | outcome | cells |
  |---|---|
  | better | 8 (all at σ = 1.0, T ≥ 30) |
  | no difference | 28 |
  | worse | 12 |

  It picks the pupil's best help in 0.26–0.28 of cases (chance 0.25). The results are
  identical across ρ, as expected, since the bandit does not use liking.
- **Q3, choice − rule:**

  | outcome | cells |
  |---|---|
  | better | 8 (σ = 1.0 with ρ ≥ 0.5; σ = 0.6 with ρ = 0.9 at T ≥ 30) |
  | no difference | 18 |
  | worse | 22 |

  With ρ = −0.5 it is worse in 11 of 12 cells.
- **Exploratory, added after seeing Q2:** at σ = 1.0, random − rule = +0.047
  [+0.017, +0.076] (T = 30) and +0.056 [+0.028, +0.083] (T = 60); adaptive − random =
  +0.013 and +0.004, both n.s. So the bandit's wins come from variety, not
  personalisation.

**Decisions**
- No change to the app's defaults. `rule` stays the recommended tutor-chooses mode; the
  bandit stays experimental.
- Pilot analysis should estimate how much pupils differ in what helps them (σ-like
  heterogeneity) as well as RQ3 (ρ). Both decide whether learner choice can pay off.

**Next**
- Hypothesis to test on a fresh seed: "rule + switch help type after a failure".
- The P2 paper's remaining blockers are the adult dry run and the write-up.

---

## 2026-11-04 (later): Learning guide

**What:** `docs/06_LEARNING_GUIDE.md`, a guide for the project lead to learn the concepts
and follow the work. It contains:
- the big picture;
- 15 concepts explained simply (verification, SFT/DPO, leakage, bootstrap CIs, dev vs
  held-out seeds, BKT, Thompson sampling, expertise reversal, learning styles, study
  design, privacy, can-fail checks, parameter recovery);
- the story of the project in order;
- a code tour of one tutor interaction;
- 7 hands-on exercises;
- research habits, a glossary and a reading list.

**Findings:** every exercise snippet was run on 2026-11-04, and the expected outputs in the
guide are copied from those runs. Code was not changed; 45 tests still pass.

**Next:** unchanged.

---

## 2026-11-04: Full review before merge; fixes; next steps that could be done here

**Plain-language summary.** Before merging, we reviewed all the new code as if a school
were about to use it. We found and fixed seven problems. The two most serious: anyone on
the school network could open the teacher page, and a pupil could re-submit an answer
after seeing the solution and have it counted. We also built the remaining next steps
that need no GPU and no school, and wrote a concrete plan for the three papers. A new
integrity result: every intermediate equation in all Phase 1 training data (68,309
equations) is correct.

**What**
- **Review fixes** (details and reasons in `04_PROOF_OF_CONCEPT.md` §6b):
  - teacher key for the teacher page and API;
  - no second graded attempt;
  - learner-code allow-list;
  - stale randomisation block reset;
  - `problem_skipped` events;
  - the help type actually shown is logged;
  - non-object JSON bodies return 400 instead of crashing.
- **`tutor/fit_bkt.py`:** maximum-likelihood BKT fitting from the logs (grid search plus
  local refinement), per skill or pooled. The engine now supports `bkt_per_skill`.
- **`tutor/codes.py`:** generates a code sheet and stores the allow-list.
- **`experiments/check_phase1_steps.py`:** step-level check of all Phase 1 training targets.
- **`requirements.txt`** (pinned) and **`.github/workflows/tests.yml`** (pytest on every
  push and PR).
- **Docs:** `05_PAPER_PLAN.md` (new); teacher guide, data plan, study design and demo
  script updated for the teacher key, codes and BKT fitting.

**Findings**
- **Phase 1 step check:** 0 failures in all four datasets:

  | dataset | equations checked |
  |---|---|
  | terse | 3,087 |
  | worked | 4,462 |
  | original synthetic | 29,948 |
  | matched synthetic | 30,812 |
  | **total** | **68,309** |

  Matrix-style displays the parser cannot read were left unchecked (656 / 877 / 6,509 /
  6,070).
- **BKT fitting needs more data than one class provides.** Recovery from simulated pupils
  with known parameters, as the largest error over the four parameters, 5 replications each:

  | answers per skill | largest error |
  |---|---|
  | 240 | up to 0.23 |
  | 450 | up to 0.26 |
  | 900 | up to 0.17 |
  | 1,800 | up to 0.09 |

  So the default minimum is 1,000 answers per skill, and single-class pilots should use
  `--pool`.
- **Tests:** 45/45 pass, including in a clean clone with no generated data (as CI will run
  them).
- **Browser check:** the teacher page refuses access without the key, and works and saves
  with it.

**Decisions**
- The teacher key is regenerated at each start by default; set `--teacher-key` /
  `TUTOR_TEACHER_KEY` for a fixed link.
- Pupil impersonation (using another pupil's code) is accepted for a supervised pilot and
  documented as a limitation in the data plan.

**Next** (unchanged priorities, plus):
- P2 sensitivity analysis of the simulation (σ, ρ, horizon). Can be done in the cloud.
- Everything in the 2026-11-03 session 2 "Next" list.

---

## 2026-11-03 (session 2): All next phases started; tutor proof of concept built

**Plain-language summary.** We built a working proof-of-concept tutor and everything a
school pilot needs. We also worked through the Phase 1 follow-ups that don't need a GPU.
The most important *finding*: in a simulation, the tutor's "learn what helps each pupil"
algorithm did **not** beat a simple textbook rule (more help for beginners, less as they
improve). The rule is now its own mode, and the pilot is designed to test whether pupils'
*own preferences* point to what helps them. See `04_PROOF_OF_CONCEPT.md`.

**What: Track B (tutor), milestones M1–M5**
- `tutor/bank.py`: problem bank from the verified generators.
  - New **step-level check**: every displayed equation must hold at the true solution, and
    Cramer determinants are checked against det(A).
  - Result: 178 systems, 5,983 equations checked, 0 failures; 1,261 matrix displays
    unchecked by the parser.
- `tutor/explanations.py`: four help types (worked example on a similar system, faded,
  outline, none). Faded steps never reveal the answer (checked on every problem).
- `tutor/grading.py`: exact grading with short diagnoses (sign, swap, one value right).
- `tutor/learner_model.py`: BKT mastery, plus Thompson sampling with efficacy and liking
  kept separate, plus the mastery rule.
- `tutor/engine.py`, `tutor/app.py`, `tutor/static/`: stdlib web app (learner + teacher
  pages).
  - Modes: learner_choice / rule / adaptive / fixed.
  - KaTeX is bundled locally, because the CDN was unreachable here and school networks
    may block it too.
  - Driven end to end in a headless browser.
- `tutor/simulate.py`: simulated-learner check (see Findings).
- `tutor/assessment.py`: parallel pre/post quiz forms, kept out of practice.
  - Engine study mode: block randomisation of pupils to conditions, plus counterbalanced
    forms.
  - `tutor/analyze_study.py`: gains by condition and RQ3 agreement.
- `docs/pilot/`: demo script, study design, consent/assent templates, data-management
  plan, teacher guide (all drafts).

**What: Track A (Phase 1 follow-ups)**
- **A8 done:** scratch paths now come from `PLE_SCRATCH`.
- **A1 part 1:** `experiments/dpo_pair_diagnostics.py`.
- **A1 part 2:** `experiments/onpolicy_dpo.py`, written and unit-tested, **not run** (no
  MLX here).
- **A2:** `experiments/faithfulness.py` (structural check), and
  `experiments/rescore_faithfulness.py` for re-scoring on the Mac plus a hand-label sample.
- **A4:** `oatutor_extract/parse_v2.py`.
- **A5:** `experiments/intermediate_stats.py`.
- `docs/03_MAC_RUNBOOK.md`: exact commands for the GPU steps.

**Findings (numbers copied from the runs)**
- **Reproducibility.** OATutor upstream has changed (13,371 vs 13,287 problem folders).
  Pinning commit `2f27a59` reproduces the Phase 1 manifests and splits byte-for-byte,
  and both synthetic sets with identical counts. The original synthetic manifest gains 3
  fields from the newer manifest format; that change was reverted, not committed.
- **Display issues found.** Phase 1 worked solutions show `x=3 y=3=3` and `+1y`. Fixed for
  the tutor only (`x=3y=3(1)=3`, `+y`), and re-verified. Phase 1 data was left unchanged.
- **Checker bugs found and fixed during the build** (each would have hidden or invented
  problems):
  - `D_{x}` was parsed as a function call: 57 false failures.
  - `x=3, y=1` was read as one chain.
  - `2x+y=1` counted as revealing `y=1`.
  - `x=3y=3(1)=3` was not detected as a reveal.
- **Simulation (M4).**
  - **Design search** on the development seed (`tutor/results/design_search.md`): of six
    variants, D2 (rule prior) looked best.
  - **Held-out confirmation (seed 20270101): D2 did NOT replicate.** In scenario A it was
    worse than the rule (−0.066 [−0.093, −0.038]) and worse than the original design. Kept
    as experimental only.
  - **Robust results (held-out, original design):**

    | contrast | result |
    |---|---|
    | rule − always worked example | +0.125 to +0.154, all scenarios, all CIs exclude 0 |
    | adaptive − rule | −0.033 [−0.061, −0.006] in A; n.s. in B and C |
    | how often adaptive picks the pupil's best help | 0.28 (chance 0.25) |
    | learner choice − rule | +0.033 [+0.006, +0.061] when preferences are honest (B) |
    | | −0.033 [−0.065, +0.000] when misleading (C) |
    | | −0.091 [−0.131, −0.051] when pupils don't differ (A) |

  - **Interpretation (hypothesis):** within 30 problems, right/wrong answers mostly reflect
    prior knowledge, so they say little about which help worked.
- **A1, DPO pairs.** 100% of pairs are separable by a surface rule: the rejected text always
  ends "Therefore the solution is…" and the chosen ends "Solution:". The rejected shares
  84.5% (terse) / 89.4% (worked) of its text with the start of the chosen. This is a
  **description**, consistent with a "pair construction" explanation of the DPO failure.
  **Not yet tested.**
- **A2, faithfulness.** The keyword metric wrongly accepts up to 40.0% of other methods'
  gold solutions (substitution). The structural check: recall ≥ 0.972, false-accept ≤ 0.007
  on gold, after 3 refinement rounds on that same set. Real model outputs still need
  hand-labelling.
- **A4, parsing.** Parser v2 gives 178 vs 128 unique verified systems. 473 problems remain
  unparsed: mostly word problems, determinant or matrix-arithmetic exercises, nonlinear
  systems, inequalities, figures.
- **A5, clean arithmetic.** Fraction-free intermediate steps: real train 0.387, matched
  synthetic 0.398, original synthetic 0.556. The clean-arithmetic hypothesis is **not
  supported**.
- **Privacy issue found and fixed.** Answers were logged as raw typed text, so a child
  could type a name. Now only parsed numbers are logged (tested).
- **OATutor BKT parameters** are placeholders: 0.1 for all 1,238 skills.
- **Tests:** 40/40 pass (`python -m pytest tests -q`).

**Decisions**
- The app's `adaptive` (bandit) mode is labelled experimental. The new `rule` mode is the
  recommended tutor-chooses option.
- Pilot arms: `fixed` (control) vs `rule` vs `learner_choice`. RQ3 asks whether stated
  preferences track what works, the question the simulation says everything hinges on.
- Phase 1 ML data and splits are **not** changed; parser v2 is used only by the tutor
  bank.
- A5 "clean-only synthetic" is dropped based on the measurement.

**Next**
- **Supervisor:** review `04_PROOF_OF_CONCEPT.md` and `docs/pilot/`; agree the pilot arms
  and timeline.
- **Before the school demo:** a teacher reviews `tutor/content.py` (method cards) and a
  sample of worked solutions; then an adult dry run.
- **On the Mac:** runbook §1 (faithfulness on real outputs + hand labels), then §2
  (on-policy DPO), then §3 (seeds).
- **Ethics application.**

---

## 2026-11-03: Project review, reframing, documentation

**What**
- Reviewed the whole repository (extractor, generators, experiments, results, reports).
- Wrote down the original project idea and compared it with what Phase 1 actually tested.
- Created `docs/`:
  - `01_VISION_AND_PLAN.md`: the vision, the reframing, the proof-of-concept plan, the paper plan
  - `02_PHASE1_METHOD_CONDITIONED_SOLVING.md`: full record of the earlier work
  - `WORKLOG.md`: this file
- Rewrote `README.md` as a project landing page; added `CLAUDE.md` so future AI-assisted
  sessions keep this log and these docs up to date.

**Findings from the review**
- Phase 1 used "preference learning" in the ML sense: DPO with correct-vs-wrong pairs.
  The project's goal is preference in the **learner** sense (how a child prefers to be
  taught). The DPO result is valid but does not address personalisation. This is the main
  reason progress felt off-track.
- Checked: all conditions are evaluated with identical prompts, chat template and greedy
  decoding (`experiments/generate.py`). A prompt mismatch is **ruled out** as a cause of
  the base-vs-trained gap.
- Observed: DPO "rejected" solutions are truncated copies of the chosen solution with a wrong
  final line (`oatutor_extract/multimethod.py: make_rejected`). This is a plausible cause of
  the DPO failure. **Hypothesis, untested**; logged as Track A item A1.
- Test suite: 17/17 pass (`python -m pytest tests -q`).
- Found hard-coded macOS scratch paths in `experiments/run_all.py` and `collect_loss.py`
  (logged as A8).

**Decisions**
- Keep Phase 1 going as **Track A** (correctness backbone + paper P1).
- Start **Track B**: a proof-of-concept personalised tutor for systems of linear equations.
  This is the deliverable that could unlock the school's data and support.
- Personalise on evidence-backed dimensions (method, scaffolding level, pacing, context),
  not on "learning styles", and measure learning outcomes.
- For the prototype, correctness comes from the verified sympy engine, not from a
  fine-tuned small model.

**Next**
- M1: extend the verified generator with scaffolding levels (full worked / hints / check only).
- Confirm with the supervisor: proof-of-concept scope, what the school expects to see, and
  the ethics process.
