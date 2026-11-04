# Paper plan: what each paper can claim, and what is missing

*Created 2026-11-04. Extends [`01_VISION_AND_PLAN.md`](01_VISION_AND_PLAN.md) §6. Update the
"Status" columns as items land, and log the changes in [`WORKLOG.md`](WORKLOG.md).*

Rule for every paper: each claim carries its evidence (a file and the run that produced
it). Anything untested is written as a hypothesis.

---

## P1: Workshop / short paper (closest to ready)

**Working title.** *Verified multi-method data for teaching small LLMs to solve by a
requested method: worked solutions help, preference tuning on correctness pairs hurts.*

**Possible venues.** BEA workshop (ACL/NAACL); AIED or EDM short or late-breaking track.
Check deadlines when ready.

| Section | Claim | Evidence now | Missing | Status |
|---|---|---|---|---|
| Data | Questions verbatim from OATutor; solutions by 6 methods, computed and checked by sympy; 0 verification failures | `data/multimethod_worked/manifest.json`, `tests/verify_multimethod.py` | Nothing | ready |
| Data (new) | Step-level checking: every displayed intermediate equation in every training target holds at the solution | `experiments/check_phase1_steps.py`: **68,309 equations checked across all four Phase 1 datasets, 0 failures** (`data/*/step_check.json`) | Nothing | **done 2026-11-04** |
| Result 1 | Worked > terse targets (general model) | `RESULTS.md` §6: +0.071 [+0.024, +0.125] | Seeds (A3) | needs Mac |
| Result 2 | DPO on correctness pairs hurts | all four DPO−SFT contrasts < 0 | Seeds (A3) | needs Mac |
| Result 3 | **Why** DPO hurts: pair construction vs update strength | Diagnostics: pairs separable by a surface rule in 100% of cases | The on-policy DPO 2×2 (A1 part 2) | needs Mac; **this is the paper's most interesting part** |
| Result 4 | Synthetic data did not help, even when matched; validation loss misleads | `RESULTS.md` §6; clean-arithmetic hypothesis ruled out (A5) | Real:synthetic ratio sweep (optional) | mostly ready |
| Metric | Keyword method-faithfulness is unreliable (up to 40% false accepts); a structural check is proposed | `data/train_worked/faithfulness_validation.json` | Agreement with hand labels on real outputs (A2, runbook §1) | needs Mac + ~2 h labelling |
| Limits | 1.5B / 4-bit, 26 test systems | | Parser v2 could add test systems, but that changes the split, so decide before re-running | decision |

**Critical path:** runbook §1 (labels), then §2 (on-policy DPO), then §3 (seeds). Then
write. Estimated 2–3 weeks of Mac time plus writing.

---

## P2: System / demo paper

**Working title.** *A verified, preference-aware maths tutor: correctness by construction,
with pupils' stated preferences and outcomes kept separate.*

**Possible venues.** AIED or EDM demo track; L@S work-in-progress.

| Claim | Evidence now | Missing |
|---|---|---|
| No wrong maths shown, by construction (step-level check, exact grading, no-reveal guarantee) | `tutor/bank.py`, tests with injected errors | Teacher content review |
| Separating "liked" from "worked" is necessary: in simulation, learner choice wins only when preferences track efficacy (+0.033 vs −0.033 vs −0.091) | `tutor/results/sim_results_D0_heldout.md`; **sensitivity done 2026-11-04** (`tutor/results/sensitivity.md`): choice beats the rule only when pupils differ a lot *and* preferences track efficacy (8 of 48 cells) | Nothing for P2 |
| A per-learner bandit does not personalise within one unit (a useful negative result) | design search + held-out results + sensitivity: never beats the rule except at σ = 1.0, where random help does equally well; best-help rate 0.26–0.28 everywhere | Nothing for P2 |
| The rule's advantage depends on the expertise-reversal effect (can-fail check passed: with no reversal the rule loses, −0.043) | `tutor/results/sensitivity.md` Q4 | Nothing for P2 |
| Ready for classroom studies (randomisation, counterbalanced quizzes, privacy-safe logs, teacher key, BKT fitting) | `tutor/`, `docs/pilot/` | Adult dry run; screenshots; usability notes |

**Critical path:** ~~sensitivity analysis~~ (done 2026-11-04), then the dry run, then
writing.

---

## P3: Full conference / journal paper (needs the school)

**Working title.** *Do pupils' preferences for help predict what helps them? A classroom
study with a verified maths tutor.*

**Possible venues.** AIED (full paper), *Computers & Education*, *International Journal of
AI in Education*.

| Research question | Measure | Needs |
|---|---|---|
| RQ1: rule vs fixed | pre/post gain, ANCOVA | ≈ 74 pupils per arm for d = 0.4 (see `pilot/STUDY_DESIGN.md` §6) |
| RQ2: learner choice vs rule | same | same |
| RQ3: do stated preferences track what works? | per-pupil agreement of "liked most" and "works best" | enough answers per pupil per help type (≥ 3 each) |

**Critical path:**
1. Supervisor review.
2. Ethics approval.
3. School pilot (feasibility, about 60–90 pupils).
4. Pre-register.
5. Main study across several classes (also enough data to fit per-skill BKT).
