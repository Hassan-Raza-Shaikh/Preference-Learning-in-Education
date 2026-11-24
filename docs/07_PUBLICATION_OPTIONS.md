# Publication options: what papers this project can produce

*Written 2026-11-04 for discussion with the supervisor. Companion to
[`05_PAPER_PLAN.md`](05_PAPER_PLAN.md), which tracks each claim's evidence in detail. This
document is the overview: what each paper would say, how strong it is today, what a
reviewer would object to, and what it would take.*

---

## 1. Short answer

**Yes: two papers in the near term, and a stronger third once the school study runs.**
A small pilot paper and a dataset release can come along the way.

| # | Paper | Strength today | Main thing missing | Who / what it needs | Rough effort |
|---|---|---|---|---|---|
| **P1** | Workshop paper: teaching small LLMs to solve by a requested method | Medium; good if the DPO experiment works out | Why DPO hurt (on-policy DPO run), seeds, faithfulness labels | Mac time + about 2 h of hand-labelling | 2–3 weeks of runs + 2 weeks of writing |
| **P2** | System / demo paper: a verified, preference-aware tutor | Medium | Adult dry run, screenshots, write-up | A few adult testers | 2–3 weeks |
| **P3a** | Pilot short paper: feasibility and first look at RQ3 | Not started | School pilot (about 60–90 pupils) | Ethics approval + school | One school term |
| **P3** | Full paper: do pupils' preferences predict what helps them? | Not started; **the strongest idea** | Full study (about 74 pupils per arm) | Several classes | 6–12 months |
| (D) | Dataset / resource release (with P1, or on its own) | Nearly ready | Licence notice, data card | Nothing external | A few days |

**Two cautions apply to every row.**
1. **Novelty is not established.** No literature search has been done. Before claiming
   anything is new, each paper needs a related-work search (§7 lists where to start).
2. **Venues and deadlines** below are suggestions. Check each venue's current call; none
   were checked for this document.

---

## 2. P1: workshop paper (Track A, Phase 1)

**Working title.** *Verified multi-method solutions for small math tutors: worked solutions
help, and preference tuning on correctness pairs hurts. Here is why.*

**Pitch in three sentences.** We built a dataset of real school problems solved by six
methods, where every answer *and every intermediate equation* is checked by a computer
algebra system. Small models trained on it learn the format but not the arithmetic, unless
the solutions show every step. Preference tuning (DPO) on correct-vs-wrong pairs made
every model worse, and we test whether that was caused by how the pairs were built.

**What would be new** (to be checked against the literature):
- a fully verified multi-method solution set, built from real tutoring problems, with
  step-level checks: 68,309 equations, 0 failures;
- a controlled comparison of answer format and training stage, with exact grading and
  cluster-bootstrap confidence intervals;
- a diagnosis of the DPO failure: pairs separable by a surface rule, tested against
  on-policy pairs;
- a structural method-faithfulness check, replacing keyword matching, which wrongly
  accepted up to 40% of other methods' solutions.

**Evidence today.** `RESULTS.md` §6, `data/*/step_check.json`,
`data/train*/dpo_pair_diagnostics.json`, `data/train_worked/faithfulness_validation.json`.

**What a reviewer will say, and our honest answer:**

| Objection | Answer |
|---|---|
| "Only 1.5B models, 4-bit, on a laptop." | True. It's a limitation; frame the paper as a careful small-scale study. A 7B replication (A7) would strengthen it. |
| "26 test systems is tiny." | The CIs are reported (about ±0.1). Parser v2 could add test systems, but that changes the split, so decide before new runs. |
| "One seed per condition." | Fix before submission: runbook §3. |
| "DPO hurting is already known." | Possibly; check the likelihood-displacement literature (§7). Our contribution would be the controlled cause test (on-policy vs offline pairs), not the observation alone. |
| "Is the faithfulness metric valid?" | Only on our gold solutions so far. Hand-labelled agreement on real outputs is needed (runbook §1). |

**The decisive experiment.** The on-policy DPO run (runbook §2) can come out three ways,
and each gives a different paper:
- **on-policy pairs fix DPO:** "pair construction, not model size, caused the failure."
  The strongest version.
- **a stronger KL constraint (β) fixes it:** "the update was too strong."
- **neither fixes it:** "a capacity limit at 1.5B." Weakest, but still publishable as a
  careful negative result.

**Venues to consider.** BEA workshop (Innovative Use of NLP for Building Educational
Applications) at ACL/NAACL; AIED or EDM short / late-breaking tracks; maths-and-AI
workshops at ML conferences.

---

## 3. P2: system / demo paper (Track B)

**Working title.** *A maths tutor that cannot show wrong maths and keeps what pupils like
separate from what helps them.*

**Pitch.** Personalised tutors usually adapt to *something* about the learner. Ours
guarantees correctness by construction (verified engine, step-level checks, exact
grading) and records two separate signals: what a pupil *likes* (choices, ratings) and
what *works* (solving afterwards). That makes it a tool for testing whether preference-based
personalisation actually helps.

**What would be new** (to check):
- correctness by construction for every displayed step, combined with personalisation;
- the explicit "liked vs worked" separation built into the learner model and the logs;
- simulation evidence, replicated on a fresh seed, with a can-fail check:
  - a simple mastery rule beats fixed worked examples;
  - outcome-based per-pupil personalisation (bandit) doesn't beat the rule within one unit;
  - learner choice helps only when preferences strongly track what helps.
- study-ready tooling: randomisation, counterbalanced quizzes, privacy-by-design logging,
  BKT fitting.

**Evidence today.** `docs/04_PROOF_OF_CONCEPT.md` §3–6b, `tutor/results/`, 47 tests.

**What a reviewer will say:**

| Objection | Answer |
|---|---|
| "The simulator's numbers are invented." | Yes. Frame it as a mechanism analysis. Show robustness: 48-cell sensitivity, alternative learning tables, a check where the rule *must* lose, and fresh-seed replication. Never claim learning gains. |
| "No real users." | An adult dry run (usability, timing, errors) before submission; real pupils come in P3. |
| "Only one topic." | True. Argue that the architecture (verified engine + learner model) generalises, and show what a second topic would need. |
| "A mastery rule is old news." | Agreed. The contribution is the testbed and the negative and conditional results, not the rule. |

**Venues to consider.** AIED or EDM demo / late-breaking tracks; Learning@Scale
work-in-progress; ITS (Intelligent Tutoring Systems).

---

## 4. P3a and P3: classroom papers (need the school)

**Working title (P3).** *Do pupils' preferences for help predict what helps them? A
randomised classroom study with a verified maths tutor.*

**Why this is the strongest paper.** It answers the project's original question (does
learning from pupils' preferences help?) with real pupils, under random assignment,
measuring learning rather than satisfaction. The simulations say the answer depends on
two quantities nobody has measured for this setting: how much pupils differ in what helps
them, and whether their stated preferences track it.

**Design** (draft in [`pilot/STUDY_DESIGN.md`](pilot/STUDY_DESIGN.md)):
- three arms: fixed help, mastery rule, learner choice;
- pre/post quiz on parallel forms, counterbalanced;
- RQ1: rule vs fixed. RQ2: learner choice vs rule. RQ3: does "liked most" match "works
  best" for each pupil?

| Stage | Pupils | What it can claim | Paper |
|---|---|---|---|
| Pilot | about 60–90 (20–30 per arm) | Feasibility, completion rates, timing, first effect-size estimates with wide CIs, first RQ3 estimate | **P3a**: short paper or poster (AIED/EDM late-breaking) |
| Full study | about 74 per arm for d = 0.4 with pre-test adjustment (more for three arms) | Learning effects and RQ3 | **P3**: full conference paper or journal (*Computers & Education*, *International Journal of AI in Education*) |

**What a reviewer will say:**

| Objection | Answer |
|---|---|
| "Learning styles are debunked." | Agreed. We don't use them. We personalise on evidence-based dimensions and *test* whether preferences predict benefit. |
| "Short intervention, short quiz." | True. Plan more items and sessions for the full study (the pilot shows what's feasible). |
| "Contamination within classes." | Note it in the pilot. Consider randomising whole classes in the full study. |

**Prerequisites:** supervisor sign-off, ethics approval, school agreement, parent consent
and pupil assent, a teacher content check, an adult dry run, and pre-registration.

---

## 5. (D) Dataset / resource release

The verified multi-method solutions (real OATutor problems; terse and worked formats;
step-checked) could be released with P1, or as a short resource paper. OATutor content is
CC BY 4.0, so attribution is required; check whether redistributing derived solutions needs
anything more. It needs a data card covering source commit, generation, verification
counts, known limitations (systems only, 2–3 variables) and licence. Effort: a few days.

---

## 6. Recommended order

```
now ──► P1 runs on the Mac (2–3 wks) ──► write P1 ──► submit (workshop)
   └──► adult dry run ──► write P2 ──► submit (demo / late-breaking)
   └──► ethics application ──► school pilot ──► P3a ──► full study ──► P3
```

P1 and P2 don't depend on the school, and they build a track record before P3. Start the
ethics application early, because it is usually the slowest step.

**Questions to settle with the supervisor:**
1. Which paper comes first, and what's the target venue and deadline?
2. Authorship and roles for each paper, including the school's contribution to P3.
3. Should P1 enlarge the test set with parser v2 before the new runs (a cleaner paper, but
   it re-runs Phase 1)?
4. Release the dataset with P1 or separately?
5. Pilot arms: is three arms feasible at one school, or is two (rule vs learner choice)
   better for a small pilot?

---

## 7. Related-work search: where to start (to do before writing)

These are starting points, not a review. Read each before relying on it, and record what
it actually says.

| Paper | Topic to search | Starting points to verify |
|---|---|---|
| **P1** | DPO failure modes: the probability of the *chosen* answer falling when pairs differ in only a few tokens ("likelihood displacement") | Rafailov et al. 2023 (DPO); Pal et al. 2024, *Smaug* / DPO-Positive; Razin et al., likelihood displacement in DPO |
| **P1** | Verified or synthetic maths data for small models; worked-solution formats; on-policy vs offline preference data | Search: "on-policy preference data math reasoning", "process supervision", "step-level verification" |
| **P2** | Intelligent tutoring systems with mastery learning; OATutor | Corbett & Anderson 1995; Pardos et al. 2023 (OATutor, CHI) |
| **P2, P3** | Learner control in educational technology | Search: "learner control meta-analysis educational technology" (e.g. Karich, Burns & Maki, 2014, *Review of Educational Research*); verify the findings before citing |
| **P3** | Preferences vs learning; expertise reversal; fading worked examples | Pashler et al. 2008; Kalyuga et al. 2003; Renkl & Atkinson 2003 |
| **All** | Personalisation with bandits in education | Search: "multi-armed bandit intelligent tutoring", "contextual bandit instructional sequencing" |

A systematic search for each paper can be done next; the results would go into
`docs/` with what each source found, not just its title.
