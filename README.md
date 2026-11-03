# Preference Learning in Education

An AI tutor that **teaches each learner the way they learn best** and **never shows
wrong maths**, built and studied as both a practical system and a research programme.

- **Correctness** comes from a verified computer-algebra engine (sympy): every
  solution is computed and checked, never free-form generated.
- **Personalisation** comes from the learner: which explanations they choose, how they
  do afterwards, and which skills they have mastered.
- **Starting topic:** systems of linear equations, using problems from
  [OATutor](https://github.com/CAHLR/OATutor-Content). Other subjects come later.

## Where things stand

| Track | What | Status |
|---|---|---|
| **A: Method-conditioned solving** (Phase 1) | Verified multi-method solution data; fine-tuning small LLMs (SFT/DPO) to solve by a requested method | Study complete (Sep–Oct 2026); follow-ups open |
| **B: Personalised tutor proof of concept** | Verified explanations + learner model (mastery + preferences) + interactive prototype | Planned (from Nov 2026); a school has offered data and support if it works |

## Documentation (start here)

| Document | For |
|---|---|
| [`docs/01_VISION_AND_PLAN.md`](docs/01_VISION_AND_PLAN.md) | The idea, the reframing, proof-of-concept milestones, publication plan |
| [`docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md`](docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md) | Everything done in Phase 1, in plain language, plus the open items |
| [`docs/WORKLOG.md`](docs/WORKLOG.md) | Dated log of every step from Nov 2026 on |
| [`RESULTS.md`](RESULTS.md) | Full Phase 1 results with confidence intervals |
| [`report_supervisor.pdf`](report_supervisor.pdf) | Phase 1 supervisor report (Oct 2026) |
| [`OATUTOR_ANALYSIS_AND_PLAN.md`](OATUTOR_ANALYSIS_AND_PLAN.md) | Audit of the OATutor source data |
| [`oatutor_extract/README.md`](oatutor_extract/README.md) | Extractor usage and dataset schema |

## Repository layout

```
oatutor_extract/   OATutor → clean JSONL; verified multi-method solution generators
experiments/       Phase 1: data prep, training (MLX), generation, sympy grading, CIs, figures
tests/             Unit tests + independent re-verification of every generated solution
data/              Manifests, splits, evaluation results, loss logs (large JSONL are git-ignored)
report_assets/     Figures
docs/              Vision, plan, Phase 1 record, work log
```

## Quick start

```bash
pip install sympy numpy pytest
git clone https://github.com/CAHLR/OATutor-Content.git
python -m oatutor_extract.extract --content-root ./OATutor-Content --out-dir data -v
python -m pytest tests/ -q
```
Training runs need Apple Silicon with `mlx`, `mlx-lm` and `mlx-lm-lora`. See
`docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md` §9.
