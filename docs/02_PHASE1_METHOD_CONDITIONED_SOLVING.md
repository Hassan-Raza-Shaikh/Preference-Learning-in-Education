# Phase 1: Method-Conditioned Solving of Linear Systems

*Period: 2026-09-03 → 2026-10-09. Documented 2026-11-03. Status: complete as a study;
continues as **Track A** (see [`01_VISION_AND_PLAN.md`](01_VISION_AND_PLAN.md)).*

Detailed numbers live in [`../RESULTS.md`](../RESULTS.md) and the supervisor report
([`../report_supervisor.md`](../report_supervisor.md) / `.pdf`). This document is the
plain-language record: what was built, why, what we learned, and what carries forward.

---

## 1. Plain-language summary (for the supervisor)

We took real school maths problems (systems of linear equations from the OATutor tutoring
system) and built a pipeline that writes out **step-by-step solutions by six different
methods**. A computer algebra system (sympy) computes and **checks** every solution, so
none of the training data can contain a mistake. We then trained two small AI models
(1.5 billion parameters, one general and one maths-specialised) to solve a system **by the
method we ask for**, and graded them automatically and exactly.

What we found:
- **Showing all the arithmetic in training examples helps** compared with compact
  solutions (statistically clear for the general model).
- **Preference tuning (DPO) made the models worse in every case.** This is the most robust
  result.
- **No trained model clearly beats its untrained starting point.** The maths model reaches
  parity after longer training.
- **Adding thousands of synthetic problems did not help**, even when they were made to
  resemble the real ones.

Why it matters now: the **verified solution engine** is the foundation of the new tutor
proof of concept, because it guarantees the tutor never shows wrong maths. The DPO result
told us that "correct vs. wrong" is the wrong kind of preference. The preference we care
about is the *learner's* (see the vision document, Section 2).

---

## 2. Research question

When a small LLM is trained to solve a linear system by a **specified** method, what moves
accuracy: the base model's prior, the **format** of the solution targets (terse vs.
worked), the training **stage** (SFT vs. DPO), training **length**, or added **synthetic
data**?

---

## 3. What was built

| Component | Files | What it does |
|---|---|---|
| OATutor analysis | `OATUTOR_ANALYSIS_AND_PLAN.md` | Full audit of the source data: 13,287 problems, structure, quality, duplicates |
| Extractor | `oatutor_extract/extract.py`, `taxonomy.py`, `README.md` | Turns OATutor into clean JSONL; deduplication, quality flags, subject/method taxonomy |
| Multi-method generator (terse) | `oatutor_extract/multimethod.py` | For each parseable system: solutions by substitution, elimination, graphing, Cramer's rule, matrix inverse, Gaussian elimination. sympy computes, then verifies by substituting back. Also builds DPO pairs. |
| Worked generator | `oatutor_extract/worked.py` | The same, but every arithmetic step is shown explicitly |
| Synthetic systems | `experiments/synth_systems.py` | Systems built from a known solution, run through the same verified generator; original and distribution-matched variants |
| Data prep | `experiments/prepare_data.py`, `build_scaled.py` | Splits **by system** (no leakage), method-conditioned chat prompts, SFT/DPO files, contamination check |
| Training orchestration | `experiments/run_all.py` | Base → LoRA SFT → DPO for both models (MLX, `mlx-lm-lora`), resumable |
| Generation | `experiments/generate.py` | Greedy decoding, same prompt and chat template for every condition |
| Evaluation | `experiments/evaluate.py` | sympy grading: does the answer satisfy the *original* system exactly; keyword-based method-faithfulness; error modes |
| Statistics | `experiments/analyze_ci.py` | Cluster bootstrap over test systems (B = 10,000), paired contrasts |
| Figures / losses | `experiments/make_figures.py`, `collect_loss.py` | Accuracy chart, train/validation loss curves |
| Tests | `tests/` | 17 tests (extractor + generator); `verify_multimethod.py` re-verifies every solution independently |

### Data funnel
- 13,287 OATutor problems → **751** systems-of-equations problems
- → **164** state a parseable, uniquely solvable linear system in text
  (560 unparsed, mostly word problems or figure-based; 27 without a unique solution)
- → **811** verified method-solutions (substitution 105, elimination 107, graphing 107,
  Cramer's 164, inverse 164, Gaussian 164) and **811** preference pairs
- Split by system (seed 20260909): **114 train / 24 valid / 26 test** (126 test items)
- Synthetic: 5,624 examples per synthetic set (original; distribution-matched), 0 verification failures

### Training setup
- Models: `Qwen2.5-1.5B-Instruct` (general) and `Qwen2.5-Math-1.5B-Instruct` (math), 4-bit, MLX
- LoRA on 8 layers; SFT lr 1e-4, batch 2, 600 or 1500 iterations; DPO lr 5e-5, β = 0.1, on top of SFT
- Single run (one seed) per condition

---

## 4. Timeline

| Date | Step |
|---|---|
| 2026-09-03 | Project start; OATutor analysis |
| 2026-09-05 | Extractor + deterministic multi-method generator |
| 2026-09-09 | Experiment scaffolding: data prep + sympy evaluation harness |
| 2026-09-11 | Two-model base/SFT/DPO grid (terse); worked-solution generator and grid; first synthetic scaling run |
| 2026-09-15 | Study report (HTML), supervisor PDF with loss curves |
| 2026-10-09 | Fixed the `sympy.nsimplify` rendering bug; distribution-matched synthetic data; compute-matched control; 95% CIs; findings revised |

---

## 5. Results (exact answer accuracy, 26 held-out systems, 95% CI)

| Condition | General | Math |
|---|---|---|
| Base (no training) | 0.389 [0.27, 0.50] | 0.381 [0.29, 0.46] |
| Terse SFT (600 it) | 0.087 [0.04, 0.15] | 0.214 [0.11, 0.32] |
| Terse SFT + DPO | 0.016 [0.00, 0.04] | 0.135 [0.08, 0.19] |
| Worked SFT (600 it) | 0.159 [0.09, 0.23] | 0.286 [0.16, 0.41] |
| Worked SFT + DPO | 0.000 [0.00, 0.00] | 0.111 [0.05, 0.17] |
| Worked SFT (1500 it), real only | 0.183 [0.09, 0.27] | 0.389 [0.25, 0.52] |
| + original synthetic | 0.095 [0.04, 0.15] | 0.270 [0.17, 0.37] |
| + distribution-matched synthetic | 0.143 [0.08, 0.21] | 0.238 [0.15, 0.33] |

The full table of paired contrasts is in [`../RESULTS.md`](../RESULTS.md) §6. Raw
numbers are in `data/train/ci_results.json`.

---

## 6. What we learned

1. **DPO on correctness pairs hurts small models**: all four DPO − SFT contrasts are
   significantly negative.
2. **Format matters**: worked > terse for the general model (+0.071, significant). After terse
   SFT the model copies the format but **invents the intermediate arithmetic**.
3. **Training length**: 1500 vs. 600 iterations helps the math model (+0.103, significant).
4. **Synthetic scaling did not help**, even when distribution-matched. Matching summary
   statistics is not enough.
5. **Validation loss misleads**: lower loss did not mean higher accuracy.
6. **Methodological lesson for the whole project**: verify everything, and grade exactly.
   Correctness should be guaranteed by construction, not learned.

---

## 7. Integrity notes

- Every training target (real and synthetic) is independently re-verified: **0 failures**.
- `sympy.nsimplify` was found to rewrite some rationals as strange prime-power products in
  *displayed* steps. It was replaced by an exact converter, with a step-level guard. An
  audit found 0 of ~36k step strings affected, and regenerated data is byte-identical.
- *Checked 2026-11-03:* base, SFT and DPO models are all evaluated with **the same system
  prompt, user prompt, chat template and greedy decoding** (`experiments/generate.py`). So the
  base-vs-trained gap is **not** a prompt mismatch.

---

## 8. Open items (Track A backlog)

| # | Item | Why |
|---|---|---|
| A1 | **Diagnose the DPO failure.** In `multimethod.make_rejected`, the rejected solution is the chosen solution's setup steps with the solving steps removed and a wrong conclusion appended. So pairs share most tokens, differ in length, and are not the model's own outputs (off-policy). Test: on-policy negatives (sample the SFT model, grade with sympy), an SFT loss term during DPO, higher β. | Distinguishes "model too small" from "pair construction". Needed for paper P1. |
| A2 | Real method-faithfulness metric (does the solution perform the requested method's operations?) | Current check is keyword-based |
| A3 | ≥3 seeds per key condition | Single-seed results; intervals ≈ ±0.1 |
| A4 | Parse more of the 751 systems (word problems, matrix-form statements) | Only 164 used; more test systems → tighter CIs |
| A5 | Synthetic data with clean (integer) intermediate arithmetic; vary the real:synthetic ratio | Untested hypotheses from §6 of RESULTS |
| A6 | Choose checkpoints by sympy validation accuracy, not loss | Loss was shown to mislead |
| A7 | Repeat at 7B when a GPU is available | Capacity question |
| A8 | Remove the hard-coded macOS scratch paths in `experiments/run_all.py` and `collect_loss.py` (make them a CLI option / environment variable) | Reproducibility on other machines |

---

## 9. How to reproduce

```bash
pip install sympy numpy pytest           # + mlx, mlx-lm, mlx-lm-lora on Apple Silicon for training
git clone https://github.com/CAHLR/OATutor-Content.git
python -m oatutor_extract.extract --content-root ./OATutor-Content --out-dir data -v
python -m pytest tests/ -q               # 17 tests
python -m experiments.prepare_data
python -m experiments.run_all            # base / SFT / DPO for both models (Apple Silicon)
python experiments/analyze_ci.py         # CIs → data/train/ci_results.json
```
See `oatutor_extract/README.md` for the extractor outputs, and the docstrings at the top of
each `experiments/*.py` file for options.

---

## 10. What carries into the proof of concept

- **Verified explanation engine** (`multimethod.py`, `worked.py`): becomes the tutor's
  correctness guarantee. It will be extended with scaffolding levels.
- **sympy grader** (`evaluate.py`): grades learners' answers to check questions.
- **OATutor extraction**: problems, hints, scaffolds, skill tags and BKT parameters for
  the learner model.
- **DPO pipeline**: reused later on *real learner* preference pairs.
