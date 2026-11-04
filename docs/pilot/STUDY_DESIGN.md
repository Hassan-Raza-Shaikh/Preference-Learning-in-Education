# Pilot study design (draft)

*Draft 2026-11-03, for discussion. Pre-register the final version (for example on OSF)
before any data are collected.*

## 1. Plain-language summary

Pupils practise solving systems of linear equations with the tutor over a few lessons.
Each pupil is randomly placed in one of three versions of the tutor, which differ only in
**how help is chosen**:
- the same help every time;
- help chosen by the tutor from the pupil's progress;
- help the pupil chooses.

A short quiz before and after measures learning. The pilot mainly tests whether the study
can run smoothly in a school, and gives first estimates of the effects. It is too small to
prove an effect.

## 2. Research questions

- **RQ1 (does adaptive help add value?)** Does choosing the help type by mastery (`rule`)
  lead to larger pre→post gains than always giving the same help (`fixed`, worked example)?
- **RQ2 (does learner choice add value?)** Does letting pupils choose the help type
  (`learner_choice`) lead to larger gains than `rule`?
- **RQ3 (do stated preferences track what works?)** For each pupil, is the help type they
  choose or rate highest the same one after which they most often solve problems?

  This question matters because of two pieces of earlier evidence. The simulated-learner
  check (tutor/results/) found that learner choice helps when preferences track what
  works, and does not when they don't. The learning-styles literature (Pashler et al.,
  2008) found that matching instruction to stated preferences generally does not improve
  learning.
- **Feasibility.** Recruitment and consent rates, share of pupils completing both quizzes,
  time on task, technical problems, teacher and pupil feedback.

## 3. Design

- **Randomisation:** individual pupils, within classes, to three arms (`fixed`, `rule`,
  `learner_choice`). The tutor does this automatically with block randomisation, so the arms
  stay balanced as pupils log in (`"study"` in `tutor/config.json`).
- **Counterbalancing:** two parallel quiz forms, A and B (`python -m tutor.assessment`).
  Half of each arm takes A as the pre-test and B as the post-test; the other half the reverse.
  Quiz items are never used for practice.
- **Blinding:** pupils are not told their arm. Teachers can see it on the dashboard; for a
  later full study, consider hiding it.
- **Contamination risk:** pupils in the same class may compare versions. Accepted for a
  pilot. Record it, and consider class-level randomisation for the full study.

## 4. Procedure (suggested; adapt to the school timetable)

| Session | Activity | Time |
|---|---|---|
| 1 | Introduction, assent, pre-test quiz | 20 min |
| 2–4 | Practice with the tutor | 30 min each |
| 5 | Post-test quiz, short feedback questionnaire | 20 min |

The teacher opens and closes the quiz from the teacher page. The tutor supplements normal
teaching during the pilot; it does not replace it.

## 5. Measures

| Measure | Source |
|---|---|
| Pre-test and post-test score (exact sympy grading, no partial credit) | quiz, `state.json` |
| Gain = post − pre | `tutor/analyze_study.py` |
| Help type offered / chosen / used; rating of usefulness | `events.jsonl` |
| Correctness and time per practice problem; mastery estimates | `events.jsonl`, `state.json` |
| Feedback (pupils, teacher) | short questionnaire (to draft with the school) |

**Known measurement limits.**
- 2 items per method per form (6 in total) is short and gives low reliability. Use more
  items for the full study.
- The knowledge-tracing parameters are OATutor's placeholders (0.1 for everything).
  `python -m tutor.fit_bkt` fits them from the logs. A single class is enough only for one
  pooled parameter set (`--pool`). In a recovery test, per-method fits had errors up to
  0.17–0.26 with 240–900 answers per method, falling to ≤ 0.09 at about 1,800.

## 6. Sample size (honest version)

To detect a medium effect (d = 0.4) between **two** arms with 80% power at α = 0.05
(two-sided) needs about **99 pupils per arm**, from n = 2(1.96 + 0.84)² / 0.4².

Adjusting for the pre-test (ANCOVA, assuming a pre/post correlation of 0.5) lowers this
to about **74 per arm**, from 99 × (1 − 0.5²). With three arms and two planned contrasts,
more are needed.

A pilot with roughly 60–90 pupils (20–30 per arm) is therefore **not powered to test
effects**. Its purpose is to estimate feasibility, variances and plausible effect sizes
for planning the full study. Report effects with confidence intervals and call them
preliminary.

## 7. Analysis plan

- **Primary (full study):** post-test score by arm, adjusted for pre-test (ANCOVA), with
  form order as a covariate. Planned contrasts: `rule − fixed` (RQ1) and
  `learner_choice − rule` (RQ2).
- **Pilot:** descriptive means, gains and bootstrap CIs per arm
  (`python -m tutor.analyze_study`), plus the feasibility measures.
- **RQ3:** per-pupil agreement between "liked most" and "works best" (≥ 3 observations per
  help type), reported as a proportion. Compare it with chance (1 / number of help types
  used).
- **Missing data:** report how many pupils completed each step. The main analysis uses
  pupils with both quizzes; check whether completion differs by arm.
- **Exploratory, labelled as such:** method choices, time on task, mastery trajectories.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A pupil is upset by wrong answers | Feedback is specific and neutral; the teacher is present |
| Pupils type personal information | Only parsed numbers are logged, never raw text (tested) |
| Technical failure in class | Runs offline on one laptop on the school network; state is saved after every action |
| Maths error shown to a pupil | Every displayed equation is checked at build time; report any suspected error to the team immediately |
| Pressure to participate | Participation is voluntary; non-participants do the same practice on paper or use the tutor without data being kept |

## 9. Before any data collection

1. Ethics approval from the university, plus the school's own approval process.
2. Parent consent and pupil assent ([`CONSENT_TEMPLATES.md`](CONSENT_TEMPLATES.md)).
3. Data-protection review ([`DATA_MANAGEMENT.md`](DATA_MANAGEMENT.md)).
4. A teacher-reviewed content check of the method cards (`tutor/content.py`) and a sample
   of worked solutions.
5. A dry run with adults.
6. Pre-registration of this plan.
