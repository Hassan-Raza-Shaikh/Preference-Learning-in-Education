# Learning guide: understand and follow everything in this project

*Written 2026-11-04 for the project lead. It explains each idea in plain language,
walks through what was done and why, in order, and gives exercises you can run yourself.
Every "expected output" below was copied from a real run on 2026-11-04.*

**How to use this guide.** Read Part 1 once for the map. Then read Part 2 (concepts) as you
meet each idea in Part 3 (the story). Each idea links back to its concept. Do the
exercises in Part 5 at a computer. They take about an hour together, and they are the
fastest way to make this feel like *your* code. Part 6 is a glossary to keep open.

Contents:
1. The big picture
2. Concepts, explained simply
3. The story: what we did, in order, and why
4. Code tour: what happens when a pupil uses the tutor
5. Hands-on exercises
6. Research habits used throughout (and why)
7. Glossary
8. Reading list

---

## 1. The big picture

```
                ┌─────────────────────────── PROJECT GOAL ───────────────────────────┐
                │ A tutor that teaches each pupil the way that helps them, never      │
                │ shows wrong maths, builds skill over time, and produces research.   │
                └─────────────────────────────────────────────────────────────────────┘
                         │                                          │
          TRACK A (Phase 1, research)                 TRACK B (proof of concept, for the school)
          "Can a small AI model learn to               "A working tutor + a study design"
           solve by a requested method?"
                         │                                          │
   OATutor problems ──► verified solution engine (sympy) ──────────┤ (shared foundation)
                         │                                          │
   fine-tune 1.5B models (SFT, DPO)                problem bank ► help types ► learner model
   grade exactly, confidence intervals             ► web app ► simulation ► pilot package
                         │                                          │
             paper P1 (workshop)                       paper P2 (system) ► school study ► paper P3
```

The single most important idea: **correctness and preference are handled separately.**
Correctness is *guaranteed* by a computer algebra system. Preference only decides *which
correct explanation* a pupil sees. Phase 1 mixed the two up; see §3.2.

Where things live:

| Folder | What |
|---|---|
| `oatutor_extract/` | Reads the OATutor problems; generates and verifies solutions by 6 methods |
| `experiments/` | Phase 1: training the AI models, grading, statistics, follow-ups |
| `tutor/` | The tutor: problem bank, help types, grading, learner model, web app, simulation, study tools |
| `tests/` | 45 automatic checks |
| `docs/` | Everything written for people, including this guide |

---

## 2. Concepts, explained simply

### 2.1 Computer algebra and "verification" (sympy)
**sympy** is a Python library that does exact algebra: fractions stay fractions (1/3, never
0.333…), and it can solve equations. We use it to **compute** every solution and then
**check** it, by substituting the answer back into the original equations. If both
equations hold, the answer is right. There is no judgement involved, so the check can't
"hallucinate". That is why we say *correctness by construction*.

### 2.2 Systems of linear equations and the six methods
A system such as `2x − 6y = 0, 3x − 4y = 5` has one solution, here `x = 3, y = 1`. The six
methods are different routes to the same answer:
- **substitution:** isolate one variable, then plug it into the other equation;
- **elimination:** scale and subtract the equations to cancel a variable;
- **graphing:** where the two lines cross;
- **Cramer's rule:** ratios of determinants;
- **matrix inverse:** v = A⁻¹b;
- **Gaussian elimination:** row-reduce the augmented matrix.

The project's teaching idea is that pupils can reach the answer by different methods, and
the tutor should support the method that suits them or that the teacher asks for.

### 2.3 Fine-tuning an AI model: SFT and LoRA
A **language model** predicts text. **Supervised fine-tuning (SFT)** shows it many
examples (question → ideal answer) and nudges it to produce similar answers. **LoRA**
trains a small add-on instead of all its weights, which is what makes training on a laptop
possible. Phase 1 used two 1.5-billion-parameter Qwen models: a general one and a
maths-specialised one.

### 2.4 Preference optimisation (DPO) vs learner preference
**DPO** (Direct Preference Optimisation) trains a model on *pairs*: for the same question,
a "chosen" answer and a "rejected" one. The model learns to make chosen-like answers more
likely. In Phase 1 the pairs were *correct vs deliberately wrong*. That is really a
**correctness** signal, and sympy already guarantees correctness.

The project's goal is **learner preference**: which explanation a *pupil* prefers, and
which one actually helps them. These are different things that share a name. Seeing that
difference was the turning point of the project (§3.2).

### 2.5 Train / validation / test, and leakage
You train on one set, tune on another (validation), and report on a third you never
touched (test). The splits here are **by system**: all method-solutions of one system go
to the same split. Otherwise the model could see `x = 3, y = 1` for a system during
training (by substitution) and be "tested" on the same system (by elimination). That
would be **leakage**, which makes results look better than they are.

### 2.6 Confidence intervals and the bootstrap
A result like "accuracy 0.389" is one number from 126 test items. The **95% confidence
interval** (for example [0.270, 0.500]) shows how much it could move by chance. The
**bootstrap** estimates this by re-sampling the data many times (10,000 here) and
recomputing the number each time.

- **Cluster bootstrap:** the 126 items are 26 systems × methods. Items from the same
  system are not independent, so we re-sample whole *systems*. Otherwise the interval
  would be too narrow.
- **Paired contrast:** to compare A and B, re-sample the same systems for both, and look at
  A − B. If its interval **excludes 0**, the difference is unlikely to be chance.

### 2.7 Development seed vs held-out seed
A **seed** fixes randomness, so a simulation gives the same result every time. If you try
six designs and keep the best one *on the same seed*, part of its "win" may be luck. That
is overfitting to the seed. So you try designs on a **development** seed, then confirm the
winner **once** on a fresh **held-out** seed. In this project the "winner" (D2) **failed**
the held-out check (§3.6). The protocol caught a false result.

### 2.8 Knowledge tracing (BKT)
**Bayesian Knowledge Tracing** keeps, for each pupil and skill, a probability that the
pupil has mastered it. Four parameters drive it:

| Parameter | Meaning |
|---|---|
| `p_init` | chance they already know it |
| `p_transit` | chance of learning it on each practice |
| `p_slip` | chance of a mistake even when they know it |
| `p_guess` | chance of getting it right without knowing it |

After each answer, Bayes' rule updates the probability: up after correct, down after wrong.
Then the "learning" step adds a little. OATutor ships these parameters as **0.1 for every
skill**. They are placeholders, which is why we built `tutor/fit_bkt.py` (§3.8). See
exercise 5.3 for how fast mastery moves with the placeholders.

### 2.9 Bandits and Thompson sampling
A **multi-armed bandit** is a way to choose between options ("arms") when you learn how
good each one is only by trying them. Here the arms are the four help types. The dilemma:
- **exploit:** use what looks best so far;
- **explore:** try others, in case they are better.

**Thompson sampling** keeps a belief (a Beta distribution) about each arm's success rate,
draws one random guess from each belief, and picks the arm with the highest guess. When
you know little, the guesses are spread out, so you explore. When you know a lot, they
concentrate, so you exploit (exercise 5.6).

### 2.10 Worked examples, fading and the expertise-reversal effect
Two well-supported findings from learning science:
1. **Worked examples** help beginners more than solving problems unaided.
2. **Expertise reversal effect:** as learners improve, full worked examples stop helping
   and can even hurt. Support should **fade**: worked example → partly worked ("faded") →
   just a reminder → on your own.

Our four help types follow that ladder, and the `rule` mode applies it by mastery.

### 2.11 Why not "learning styles"
"Visual / auditory / kinaesthetic learners" is a popular idea. When tested properly,
matching teaching to a person's *stated* style generally **does not** improve learning
(Pashler et al., 2008). That's why we personalise on things with evidence behind them
(method, amount of support, pacing), and why we **measure whether pupils' stated
preferences match what actually helps them** (research question RQ3) instead of assuming
they do.

### 2.12 Study design words
- **Randomised controlled trial:** pupils are randomly assigned to versions (arms), so
  differences in learning can be attributed to the version.
- **Block randomisation:** assign in shuffled blocks (for example one per arm), so the
  arms stay balanced as pupils join.
- **Pre-test / post-test:** measure before and after; **gain** = post − pre.
- **Parallel forms and counterbalancing:** two matched quizzes, A and B. Half the pupils take
  A first, half B first, so a harder form doesn't bias the result.
- **ANCOVA:** compares post-test scores between arms while adjusting for the pre-test. This
  is more precise than comparing raw gains.
- **Power and sample size:** how many pupils you need to reliably detect an effect of a
  given size. For a medium effect (d = 0.4) between two arms, about 99 pupils per arm, or
  about 74 with ANCOVA. A small pilot is for **feasibility**, not for proving effects.
- **Pre-registration:** writing down the analysis plan *before* seeing data, so it can't be
  bent to fit the results.

### 2.13 Privacy words
- **Pseudonymisation:** pupils are codes like `7B-04`, and only the teacher holds the
  code→name list.
- **Data minimisation:** record only what the research needs. For example, we log the
  *parsed numbers* of an answer, never the raw typed text, because a child might type their
  name.

### 2.14 "A check that can fail"
A safeguard is only trustworthy if you have seen it **catch** an error. So many tests
deliberately inject a mistake (a wrong step, a wrong determinant) and assert that the
check flags it. A check that never fails might simply not be checking anything.

### 2.15 Parameter-recovery test
To trust a fitting method (like BKT fitting), generate fake data from parameters **you
chose**, fit, and see whether you get them back. If you can't recover known parameters
from fake data, you can't trust the fit on real data. This is also how we learned how
much data the fit needs (§3.8).

---

## 3. The story: what we did, in order, and why

### 3.1 Phase 1 (Sept–Oct 2026, before this guide)
**Goal:** teach small AI models to solve a system by a *requested* method.

**Steps.**
1. Extracted 13,287 OATutor problems; 751 are systems; 164 parse cleanly.
2. Generated verified solutions by 6 methods, in two formats: *terse* and *worked*
   (every arithmetic step shown).
3. Trained base → SFT → DPO, and graded exactly.

**Results** (`RESULTS.md`):
- Worked > terse (significant for the general model).
- **DPO made both models worse, every time.**
- No trained model clearly beat its untrained starting point.
- Adding thousands of synthetic problems didn't help.

*Concepts: 2.1–2.6. Read: `docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md`.*

### 3.2 The reframing (2026-11-03)
You described the real goal: personalised teaching, all subjects later, building pupils'
ability, and papers. Comparing that with the code showed **why it felt stuck**: Phase 1
optimised *correctness* with a technique called "preference" optimisation, while the goal
was *learner* preference. The fix was to treat correctness as a guaranteed floor (the sympy
engine) and to learn **which correct explanation** suits a pupil.

*Concepts: 2.4, 2.10, 2.11. Read: `docs/01_VISION_AND_PLAN.md` §2–3.*

### 3.3 Building the problem bank (M1)
We re-used the verified generators to build `tutor/data/problem_bank.json`, and added a
**step-level check**: every equation *shown in a step* must be true at the real solution.
Phase 1 only checked final answers.

Building that check found **bugs in the checker itself**:
- `D_x` (a determinant name) was read as a function, giving 57 false alarms;
- `x=3, y=1` was read as one chain.

It also found display issues for learners: Phase 1 shows `x=3y=3=3`, now `x=3y=3(1)=3`.
Phase 1's data was left untouched; only the tutor's copy is tidied.

*Concepts: 2.1, 2.14. Code: `tutor/bank.py` → `check_steps`. Exercise 5.2.*

### 3.4 Help types and grading (M1)
Four help types (`tutor/explanations.py`), following the fading ladder (2.10):
- **example:** a fully worked *similar* problem. Never the pupil's own, so the answer isn't
  given away.
- **faded:** the pupil's own problem with the first steps done, stopping before any step
  that reveals a value.
- **outline:** the method's idea, why it works, and its steps, with no numbers.
- **none:** try alone.

Grading (`tutor/grading.py`) is exact: `0.333` is not accepted for `1/3`. It gives short
specific hints such as "check the sign of x" or "your x and y look swapped".

*Exercise 5.4.*

### 3.5 The learner model and the app (M2–M3)
`tutor/learner_model.py` keeps, per pupil:
- **mastery** per method (BKT, 2.8);
- two separate scores per help type:
  - **efficacy:** did they solve it after that help?
  - **liking:** did they choose it, or rate it useful?

Keeping them apart is the core research idea: we can then *test* whether what pupils like
is what works.

The app's modes:

| Mode | How help is chosen |
|---|---|
| `learner_choice` | the pupil picks from two offered |
| `rule` | the fading ladder, by mastery |
| `adaptive` | Thompson sampling (2.9), experimental |
| `fixed` | always the same help; the control group |

*Code tour: Part 4. Exercise 5.1.*

### 3.6 The simulation (M4), and an honest negative result
Before any child uses it, we tested the *logic* on simulated pupils whose true preferences
we control (`tutor/simulate.py`). There were three scenarios:
- A: pupils don't differ;
- B: they differ, and what they *like* matches what *helps*;
- C: they differ, and what they like doesn't match.

**Findings** (held-out seed):
- The **fading rule** beats "always a worked example" in every scenario (+0.125 to +0.154).
- The **adaptive bandit doesn't beat the simple rule.** It picks a pupil's best help type
  only 28% of the time, against 25% by chance. Likely reason: right/wrong mostly reflects
  what the pupil already knew, so it says little about which help worked, and 30 problems
  are too few.
- **Letting pupils choose** wins only if their preferences match what helps them (B),
  and loses otherwise. So the real question becomes RQ3, which only real pupils can answer.
- One "improved" bandit design (D2) looked best on the development seed and **failed on
  the held-out seed**, so it was rejected (2.7).
- **Sensitivity analysis (2026-11-04):** the same questions over 48 combinations of
  assumptions, on a new seed, with the questions written down before running.
  - The rule beat fixed worked examples everywhere.
  - A deliberate can-fail check passed: with no expertise reversal, the rule *lost*, so the
    simulator isn't rigged.
  - The bandit seemed to win when pupils differ a lot, and so did random help. **Neither
    replicated on a fresh seed.** All 48 cells had reused the same simulated classes, so
    those "8 winning cells" were really one lucky draw seen eight times. Both claims were
    retracted.
  - Learner choice won only where pupils differ *and* their preferences strongly track
    what helps. That did replicate.
  - An idea from the retracted result ("rule + switch help after a wrong answer") was
    tested with criteria set in advance, and **failed**.

  See `docs/04_PROOF_OF_CONCEPT.md` §5b and `tutor/results/sensitivity.md`.

*Read: `docs/04_PROOF_OF_CONCEPT.md` §5. Exercise 5.5.*

### 3.7 The pilot package (M5)
Tools and documents so a school study can run:
- **Quizzes:** pre/post quizzes from problems never used for practice (`tutor/assessment.py`).
- **Randomisation:** block randomisation and counterbalancing (2.12), in the engine.
- **Analysis:** an analysis script (`tutor/analyze_study.py`).
- **Documents:** study design, consent and assent templates, data plan, teacher guide, and
  a 10-minute demo script, all in `docs/pilot/`. They are **drafts** that need supervisor
  and ethics approval.
- **Privacy:** we noticed the logs stored raw typed answers and changed them to store only
  the parsed numbers (2.13).

### 3.8 Track A follow-ups and the pre-merge review
**Track A follow-ups:**

| Item | What was done |
|---|---|
| A1, DPO | Every DPO pair could be told apart by a *surface rule* (the wrong answer always ends "Therefore the solution is…") without checking any maths. That is a plausible reason DPO hurt. The proper test (on-policy pairs) is ready for the Mac. |
| A2, method check | The old keyword check wrongly accepted up to 40% of other methods (for example "Back-substitute" counted as substitution). A structural check now looks at the maths actually performed. It still needs hand-labelled validation. |
| A4, parsing | A second parser recovers more OATutor systems: 178 vs 128 in the tutor bank. |
| A5, clean arithmetic | The "clean intermediate arithmetic" hypothesis was measured and **not supported**, without any training needed. |
| A8, paths | Hard-coded laptop paths removed. |

**Pre-merge review (2026-11-04):**
- The teacher page was open to anyone on the network; it now needs a private key link.
- A pupil could re-submit after seeing the solution; that is now blocked.
- Typos created phantom pupils; there is now a code allow-list.
- Plus smaller fixes, all with tests.

**Also added:**
- **BKT fitting:** it needs about 1,000+ answers per skill to fit each one separately, so a
  single class should use `--pool`.
- **Phase 1 data check:** all 68,309 intermediate equations in the Phase 1 training data
  are correct.
- **Automatic tests (CI)** on GitHub.

*Read: `docs/WORKLOG.md` for the dated details; `docs/05_PAPER_PLAN.md` for where this leads.*

---

## 4. Code tour: what happens when a pupil uses the tutor

```
Browser (tutor/static/index.html)          Server (tutor/app.py → tutor/engine.py)
─────────────────────────────────          ──────────────────────────────────────────────
type code "7B-04", Start ───────────────►  POST /api/start → Tutor.start()
                                             └ learner(): checks code format + allow-list;
                                               new pupil? _assign() → study arm, quiz order
(quiz open?) ── /api/assess/next ───────►  assess_next(): next unanswered quiz item
             ── /api/assess/answer ─────►  assess_answer(): grade() exactly, store, NO feedback
click "Next problem" ───────────────────►  POST /api/next → next_problem()
                                             ├ next_skill(): weakest method by BKT mastery
                                             ├ _pick_problem(): unseen, never a quiz item
                                             ├ band(): low / mid / high mastery
                                             └ by mode: offer_two() | rule_arm() | choose_arm() | fixed
pick one of two offered helps ──────────►  POST /api/choose → choose()
                                             ├ record_choice(): "liking" evidence
                                             └ make_variant(): builds the help (explanations.py)
type "x=3, y=1", Check ─────────────────►  POST /api/answer → answer()
                                             ├ grade(): substitute into the equations (grading.py)
                                             ├ bkt_update(): new mastery
                                             ├ record_outcome(): "efficacy" evidence
                                             └ log "answer" (parsed numbers only) → events.jsonl
                                           ◄ correct?, hint, full worked solution, mastery bars
"Was it useful?" Yes ───────────────────►  POST /api/rate → rate(): more "liking" evidence
Teacher page /teacher?key=… ────────────►  GET /api/teacher (key checked) → teacher_summary()
```

**Files to read first, in this order** (each is short and has a docstring at the top):
1. `tutor/content.py`
2. `tutor/grading.py`
3. `tutor/explanations.py`
4. `tutor/learner_model.py`
5. `tutor/engine.py`
6. `tutor/simulate.py`

---

## 5. Hands-on exercises

Setup, once:

```bash
pip install -r requirements.txt
```

Run every snippet from the repository folder.

### 5.1 Run the tests, then the tutor (10 min)

```bash
python -m pytest tests -q
```

Expected: `45 passed`. Then:

```bash
python -m tutor.app
```

Open the learner page, and the teacher link printed in the terminal, side by side. Use code
`7B-01`. Solve a problem; get one wrong on purpose; rate the help. Watch the teacher table
change. Finally look at the log the tutor wrote in `runs/demo/events.jsonl`: one JSON line
per event. Notice there is no typed text in it, only parsed numbers.

### 5.2 Make the safety check catch an error (5 min)

```python
import sympy as sp
from tutor import bank
B = bank.load()
P = next(p for p in B if "elimination" in p["methods"])
vars_ = [sp.Symbol(v) for v in P["variables"]]
ref = [sp.Rational(r) for r in P["reference"]]
steps = list(P["methods"]["elimination"]["steps"])
print(P["equations_tex"], P["reference_tex"])
print(bank.check_steps(steps, vars_, ref))                       # (checked, unchecked, failures)
i = next(k for k, s in enumerate(steps) if "Subtract" in s)
bad = list(steps); bad[i] = steps[i][:steps[i].rindex("=") + 1] + "999$$."
print(bad[i]); print(bank.check_steps(bad, vars_, ref))
```

Expected output:

```
['2x-6y=0', '3x-4y=5'] x=3, y=1
(10, 0, [])
Subtract equation 2 from equation 1 to eliminate $$y$$: $$10x=999$$.
(10, 0, ['10x=999'])
```

*Lesson: the check caught the planted error (2.14).*

### 5.3 Watch knowledge tracing move (5 min)

```python
from tutor.learner_model import bkt_update, BKTParams
p = 0.1
for correct in [True, True, False, True, True, True]:
    p = bkt_update(p, correct, BKTParams()); print(round(p, 3))
```

Expected: `0.55, 0.925, 0.62, 0.943, 0.994, 0.999`.

*Lesson:* with the placeholder parameters, two correct answers already give 92.5%
"mastery". That's far too generous, which is why `tutor/fit_bkt.py` exists. Try
`BKTParams(p_init=0.1, p_transit=0.05, p_slip=0.1, p_guess=0.3)` and compare.

### 5.4 Grade answers like the tutor does (5 min)

```python
from tutor import bank
from tutor.grading import grade
P = bank.load()[0]; A, b = bank.matrices(P)
for t in ["x=3, y=1", "x=0, y=0", "hello", "y=1, x=3", "(3, 1)"]:
    g = grade(t, P["variables"], A, b, P["reference"]); print(repr(t), g["correct"], g["message"])
```

The first three give, as expected:
- `True … Correct!`
- `False … Not quite.`
- a format message.

Then try `"x=1, y=3"` (swapped) and `"x=-3, y=1"` (sign) to see the specific hints.

### 5.5 Explore the simulation yourself (10 min)

```python
from tutor import simulate as S
for rho in (0.9, 0.0, -0.5):            # how well "what pupils like" matches "what helps them"
    sc = {"sigma": 0.6, "rho": rho}
    r = {pol: round(sum(S.run_class(pol, sc, s)["mastered"] for s in range(5)) / 5, 3)
         for pol in ("rule_by_mastery", "learner_choice")}
    print(rho, r)
```

Expected:

```
0.9 {'rule_by_mastery': 0.728, 'learner_choice': 0.76}
0.0 {'rule_by_mastery': 0.728, 'learner_choice': 0.648}
-0.5 {'rule_by_mastery': 0.728, 'learner_choice': 0.611}
```

*Lesson:* learner choice only pays off when preferences track what helps (2.11). Try
`sigma` 0 (pupils don't differ) and 1.2 (pupils differ a lot), and the policy `"oracle"`.

### 5.6 See Thompson sampling explore and then commit (5 min)

```python
import random; rng = random.Random(0)
print([round(rng.betavariate(1+3, 1+1), 2) for _ in range(5)])     # 3 successes, 1 failure
print([round(rng.betavariate(1+30, 1+10), 2) for _ in range(5)])   # 30 successes, 10 failures
```

Expected:

```
[0.82, 0.49, 0.77, 0.39, 0.85]
[0.79, 0.62, 0.78, 0.7, 0.8]
```

*Lesson:* with little evidence the guesses jump around (exploration); with more they
cluster near 0.75 (exploitation).

### 5.7 Read one result end to end (15 min)
Pick "DPO hurts" in `RESULTS.md` §6 and trace it:
1. The contrast row and its CI.
2. `experiments/analyze_ci.py` (how CIs are computed: cluster bootstrap, paired).
3. `data/train/ci_results.json` (the stored numbers).
4. `data/train/dpo_pair_diagnostics.json` (the A1 clue).

Then write two sentences in your own words: what is known, and what is only a hypothesis.

---

## 6. Research habits used throughout (and why)

| Habit | Why |
|---|---|
| **Copy numbers from the run that produced them** | Memory and rounding drift; reviewers check |
| **Label untested ideas as hypotheses** | Keeps you from defending a guess as a finding |
| **Report negative results** (DPO hurt; the bandit lost; D2 failed) | They save others time, and they changed our design |
| **Dev seed for exploring, held-out seed for confirming** | Stops "best of six" luck being reported as a result |
| **Checks that can fail** | A check never seen failing may check nothing |
| **Verify, don't trust** (sympy, step checks, clean-clone tests) | Correctness can't depend on a model behaving |
| **Pin versions and source commits** | Upstream OATutor changed; pinning made Phase 1 reproducible |
| **Simulation shows mechanism, not learning** | Only real pupils can show that children learn more |
| **Replicate on fresh data before reporting** | A grid of results from one seed is one draw shown many times; our bandit and random-help "wins" vanished on a fresh seed |
| **Write it down as you go** (`WORKLOG.md`) | So you can explain every decision to your supervisor |

---

## 7. Glossary

| Term | Meaning |
|---|---|
| **Arm** | One option a bandit can choose; here, a help type |
| **ANCOVA** | Compares groups' post-test scores, adjusting for the pre-test |
| **BKT** | Bayesian Knowledge Tracing: probability a pupil has mastered a skill (2.8) |
| **Band** | low / mid / high mastery (below 0.4 / 0.4–0.8 / above 0.8), used to choose help |
| **Bootstrap** | Re-sampling data to estimate uncertainty (2.6) |
| **CI** | Confidence interval |
| **CI (GitHub)** | Continuous integration: tests that run automatically on every push |
| **Cluster bootstrap** | Bootstrap that re-samples groups (systems, classes) rather than single items |
| **Counterbalancing** | Half take quiz form A first, half form B (2.12) |
| **DPO** | Direct Preference Optimisation, trained on chosen/rejected pairs (2.4) |
| **Efficacy vs liking** | Did the help *work* (solved afterwards) vs did the pupil *like* it (chose or rated it) |
| **Expertise reversal** | Heavy support helps beginners and can hinder more advanced learners (2.10) |
| **Faded example** | A partly worked solution the pupil completes |
| **Held-out** | Data or seeds kept aside, used once to confirm |
| **Leakage** | Test information sneaking into training |
| **LoRA** | A cheap way to fine-tune a big model |
| **Off-policy / on-policy pairs** | Preference pairs written by us vs sampled from the model itself |
| **OATutor** | Open-source tutoring system whose problems we use (CC BY 4.0) |
| **Pilot** | A small first study, to test feasibility |
| **Pre-registration** | Publishing the analysis plan before collecting data |
| **Pseudonymisation** | Replacing names with codes |
| **SFT** | Supervised fine-tuning (2.3) |
| **Seed** | A number that fixes randomness, for reproducibility |
| **sympy** | Python computer algebra library (2.1) |
| **Thompson sampling** | Choose by drawing from your beliefs about each option (2.9) |
| **Worked / terse targets** | Phase 1 solution formats: every step shown, or compact |

---

## 8. Reading list (start with ★)

- ★ **Pashler, H., McDaniel, M., Rohrer, D., & Bjork, R. (2008).** Learning styles: Concepts
  and evidence. *Psychological Science in the Public Interest*, 9(3). *Why we don't use
  learning styles.*
- ★ **Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003).** The expertise reversal
  effect. *Educational Psychologist*, 38(1). *Why support should fade.*
- **Renkl, A., & Atkinson, R. K. (2003).** Structuring the transition from example study to
  problem solving. *Educational Psychologist*, 38(1). *Faded worked examples.*
- ★ **Corbett, A. T., & Anderson, J. R. (1995).** Knowledge tracing: Modeling the acquisition
  of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4. *BKT.*
- **Pardos, Z. A., et al. (2023).** OATutor: An open-source adaptive tutoring system and
  curated content library for learning sciences research. *CHI 2023.* *Our data source.*
- ★ **Rafailov, R., et al. (2023).** Direct Preference Optimization: Your language model is
  secretly a reward model. *NeurIPS.* *DPO.*
- **Hu, E. J., et al. (2021).** LoRA: Low-rank adaptation of large language models.
  *arXiv:2106.09685.*
- **Russo, D., Van Roy, B., et al. (2018).** A tutorial on Thompson sampling. *Foundations and
  Trends in Machine Learning.*
- **Efron, B., & Tibshirani, R. (1993).** *An Introduction to the Bootstrap.* Chapman & Hall.

When you've finished this guide, the best next step is `docs/05_PAPER_PLAN.md`: it shows
which of these ideas each paper rests on, and what is still missing.
