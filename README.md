# Preference Learning in Education

An AI tutor that **teaches each learner the way they learn best** and **never shows
wrong maths**, built and studied as both a practical system and a research programme.

- **Correctness** comes from a verified computer-algebra engine (sympy): every
  solution is computed and checked, never free-form generated.
- **Personalisation** comes from the learner: which help they choose, how they do
  afterwards, and which skills they have mastered.
- **Starting topic:** systems of linear equations, using problems from
  [OATutor](https://github.com/CAHLR/OATutor-Content). Other subjects come later.

## Where things stand

| Track | What | Status |
|---|---|---|
| **A: Method-conditioned solving** (Phase 1) | Verified multi-method solution data; fine-tuning small LLMs (SFT/DPO) to solve by a requested method | Study complete (Sep–Oct 2026). Follow-ups: A2/A4/A5/A8 done, A1 part 1 done; GPU steps in the runbook |
| **B: Personalised tutor proof of concept** | Verified explanations + learner model + web app + simulated-learner check + pilot package | Built Nov 2026 (M1–M5). Pilot documents await supervisor review and ethics approval |

## Documentation (start here)

| Document | For |
|---|---|
| [`docs/01_VISION_AND_PLAN.md`](docs/01_VISION_AND_PLAN.md) | The idea, the reframing, milestones, publication plan |
| [`docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md`](docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md) | Everything done in Phase 1, plus the status of each follow-up |
| [`docs/03_MAC_RUNBOOK.md`](docs/03_MAC_RUNBOOK.md) | Track A steps that need the Apple Silicon machine |
| [`docs/04_PROOF_OF_CONCEPT.md`](docs/04_PROOF_OF_CONCEPT.md) | The tutor: what it does, correctness guarantees, simulation results |
| [`docs/05_PAPER_PLAN.md`](docs/05_PAPER_PLAN.md) | Three papers: what each can claim now, what is missing, critical path |
| [`docs/pilot/`](docs/pilot/) | School pilot: demo script, study design, consent templates, data plan, teacher guide |
| [`docs/WORKLOG.md`](docs/WORKLOG.md) | Dated log of every step from Nov 2026 on |
| [`RESULTS.md`](RESULTS.md), [`report_supervisor.pdf`](report_supervisor.pdf) | Phase 1 results and report |
| [`OATUTOR_ANALYSIS_AND_PLAN.md`](OATUTOR_ANALYSIS_AND_PLAN.md), [`oatutor_extract/README.md`](oatutor_extract/README.md) | Source data audit; extractor usage |

## Try the tutor

```bash
pip install sympy
python -m tutor.app
```

Then open http://localhost:8000 (learner) and the private teacher link printed in the
terminal (`/teacher?key=...`).
It works offline.

## Repository layout

```
tutor/             Track B: problem bank, explanations, grading, learner model, web app,
                   simulation, quizzes, study analysis
oatutor_extract/   OATutor → clean JSONL; verified multi-method generators; parser v2
experiments/       Track A: data prep, training (MLX), generation, sympy grading, CIs,
                   DPO diagnostics, structural faithfulness, on-policy DPO
tests/             45 tests, including injected-error checks (CI: .github/workflows/tests.yml)
data/              Manifests, splits, evaluation results (large JSONL are git-ignored)
docs/              Vision, plan, Phase 1 record, runbook, proof of concept, pilot, work log
runs/              Tutor logs and state (git-ignored: contains learner data)
```

## Rebuild the data

```bash
pip install -r requirements.txt
git clone https://github.com/CAHLR/OATutor-Content.git
git -C OATutor-Content checkout 2f27a597268ae5d1826f69083ad91cf8864a0c05
python -m oatutor_extract.extract --content-root ./OATutor-Content --out-dir data -v
python -m oatutor_extract.worked
python -m tutor.bank
python -m pytest tests -q
```

The `git checkout` pins the Phase 1 source commit. `python -m tutor.bank` rebuilds the
tutor's problem bank (it is already committed).
