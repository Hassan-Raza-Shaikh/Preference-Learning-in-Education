# Preference Learning in Education — Experimental Results

**Question.** When you train a small LLM to solve systems of equations by a *specified*
method, what matters: the base model's prior, the **format** of the solution targets
(terse vs. worked), or the training stage (SFT vs. DPO)? And does scaling verified data help?

Everything below is **auto-graded by sympy** (answer substituted back into the original
system — exact rational check), so there is no LLM-judge noise. All training data is
**verified at generation time and independently re-verified** (0 failures); questions are
taken verbatim from OATutor or synthesized from known solutions — no free-form generation,
so no hallucinated math enters the pipeline.

---

## 1. Setup

- **Data source.** OATutor-Content (13,287 problems). 751 are systems-of-equations
  problems; 164 state a parseable, uniquely-solvable linear system in text.
- **Targets.** For each system we generate a verified solution by every applicable method
  — substitution, elimination, graphing (2-var); Cramer's rule, matrix inverse, Gaussian
  elimination (2- and 3-var). Two target *formats*:
  - **terse** — compact steps (the original generator).
  - **worked** — the same steps but showing the arithmetic explicitly
    (e.g. substitution renders `3(3y) − 4y = 5 → 5y = 5`, not a compressed jump).
- **Split.** 164 systems → 114 train / 24 valid / **26 test**, grouped by system
  (no leakage), identical across all conditions. Test = 126 method-solutions.
- **Models (matched 1.5B, 4-bit, MLX).**
  - `general` = Qwen2.5-1.5B-Instruct
  - `math` = Qwen2.5-Math-1.5B-Instruct
- **Training.** LoRA (8 layers) via mlx-lm-lora. SFT then DPO (verified preference pairs:
  correct vs. a deterministically-corrupted, verified-wrong solution).
- **Metric.** Answer accuracy (exact) on the held-out test set. Method-faithfulness and
  error-mode breakdown also logged.

---

## 2. Baselines

Both bases land at essentially the **same overall accuracy (~38%)** but with different
per-method strengths — a clean controlled starting point.

| method | general | math |
|---|---|---|
| substitution | 0.94 | 0.88 |
| elimination | 0.56 | **0.75** |
| Gaussian | 0.04 | **0.42** |
| inverse | 0.39 | 0.39 |
| Cramer's | **0.39** | 0.00 |
| graphing | **0.25** | 0.06 |
| **overall** | **0.389** | **0.381** |

The math prior is stronger on core algorithmic methods (elimination, Gaussian); the general
prior is stronger on formula-recall methods (Cramer's, graphing).

---

## 3. Main result — terse targets (2×3)

| model | base | +SFT | +SFT+DPO |
|---|---|---|---|
| general | 0.389 | 0.087 | 0.016 |
| math | 0.381 | 0.214 | 0.135 |

**Finding.** Training on terse verified solutions *degraded* both models, monotonically.
The mechanism is verified, not inferred: SFT outputs are perfectly formatted (126/126 end
with a clean "Solution:") but the model **stops doing chain-of-thought and fabricates the
intermediate arithmetic** — e.g. it correctly writes `x = 3y`, then invents `15 − 18y = 0`
(should be `5y = 5`). The math prior is consistently more robust than the general one.

---

## 4. Format matters — worked vs. terse

Re-running the identical experiment with **worked** targets (same math, arithmetic shown):

| model | format | base | SFT | DPO |
|---|---|---|---|---|
| general | terse | 0.389 | 0.087 | 0.016 |
| general | **worked** | 0.389 | **0.159** | 0.000 |
| math | terse | 0.381 | 0.214 | 0.135 |
| math | **worked** | 0.381 | **0.286** | 0.111 |

**Findings.**
1. **Worked beats terse at SFT** — general +7pts (0.087→0.159), math +7pts (0.214→0.286).
   Showing the arithmetic reduces the "imitate-format, fabricate-arithmetic" failure.
   Clearest on substitution (general): terse 0.12 → worked 0.44.
   *[Revised, §6: with 95% CIs this is significant for the general model only; the math
   model's interval includes zero.]*
2. **DPO hurts at this scale** — every DPO cell is below its SFT cell, catastrophic for the
   small general model (→0). The verified preference pairs separate perfectly (a rule-based
   judge prefers chosen 811/811), so this is a model-capacity boundary, not a data problem.
3. **Training helps where the base is weak.** No trained variant beats base *overall* — the
   bases already reason well on methods they know, and LoRA taxes those slightly — but
   worked SFT **beats the base on methods the base lacked**: math Cramer's 0.00 → 0.15,
   and recovers elimination to 0.69.
   *[Revised, §6: at 1500 iterations the math model reaches parity with its base, 0.389 vs
   0.381.]*

**Takeaway (at 600 iterations).** Solution format matters (firmly for the general model);
SFT ≫ DPO; gains concentrate on methods the base can't already do.

---

## 5. Scaling verified data

Synthetic systems (built from known solutions, run through the same verified worked
generators, independently re-checked: 1,200 systems / 5,624 method-solutions, 0 failures)
were combined with the real worked train set → **6,189 SFT examples** (0 contamination with
the held-out set). SFT re-run for both models (1500 iters); evaluation on the same 26 real
test systems.

| model | base | worked SFT (114 sys, 600 it) | scaled SFT (6,189 ex, 1500 it) |
|---|---|---|---|
| general | 0.389 | 0.159 | **0.095** |
| math | 0.381 | 0.286 | **0.270** |

**Finding: naive scaling did not help.** The math model was flat (0.286→0.270, within
noise); the general model regressed. So *more verified data alone did not improve accuracy.*

Two caveats, established by inspection (this is where honest analysis matters):
1. **Not a difficulty effect.** The synthetic systems are not harder — similar coefficient
   sizes (max-coef 5.4 vs 6.0) — but they are **0% fractional-solution vs 37% in real data**,
   a solution-distribution mismatch.
2. **An iteration confound.** The scaled run used 1500 iters vs the worked-114 run's 600.
   *[Refuted, §6: the compute-matched control shows longer training does not hurt — it
   helps the math model significantly. Compared at equal compute, the original synthetic
   data significantly hurt **both** models; "math flat" was an artifact of comparing against
   the 600-iteration run.]*

*[The takeaway originally here — that distribution-matched data would fix scaling — was
tested in §6. It removed the harm for the general model but did not help either model.]*

---

## 6. Controls, distribution-matched data, and confidence intervals (Oct 2026)

Two runs were added to resolve the scaling question, and every result now carries a 95%
confidence interval.

- **Compute-matched control.** Worked SFT on the 114 real systems at **1500** iterations
  (same budget as the scaled runs), isolating training length from data volume.
- **Distribution-matched synthetic set.** Coefficients and constants bootstrapped from the
  real **train** split only; 2/3-variable mix, coefficient sizes, fractional coefficients and
  fractional-solution share (0.38) all match. Same volume as the original synthetic set
  (5,624 examples; 1,136 systems). 0 verification failures; 0 overlap with valid/test.
- **Statistics.** The 126 test items are 26 systems × methods, so items are not independent.
  Intervals come from a cluster bootstrap that resamples **systems**; contrasts resample both
  conditions with the same draws (paired). B = 10,000, seed 20261009
  (`experiments/analyze_ci.py`; point estimates reproduce every stored eval exactly).

#### General model (Qwen2.5-1.5B-Instruct)

| condition | acc | 95% CI |
|---|---|---|
| base | 0.389 | [0.270, 0.500] |
| terse SFT (600) | 0.087 | [0.036, 0.145] |
| terse DPO | 0.016 | [0.000, 0.039] |
| worked SFT (600) | 0.159 | [0.085, 0.232] |
| worked DPO | 0.000 | [0.000, 0.000] |
| worked SFT (1500) | 0.183 | [0.094, 0.271] |
| scaled-old SFT (1500) | 0.095 | [0.043, 0.152] |
| scaled-matched SFT (1500) | 0.143 | [0.079, 0.209] |

| contrast | diff | 95% CI | CI excludes 0? |
|---|---|---|---|
| format: worked - terse (SFT@600) | +0.071 | [+0.024, +0.125] | yes |
| DPO - SFT (terse) | -0.071 | [-0.123, -0.023] | yes |
| DPO - SFT (worked) | -0.159 | [-0.232, -0.085] | yes |
| steps: 1500 - 600 (worked) | +0.024 | [-0.039, +0.094] | no |
| volume, mismatched: scaled-old - worked (@1500) | -0.087 | [-0.171, -0.009] | yes |
| volume, matched: scaled-matched - worked (@1500) | -0.040 | [-0.127, +0.041] | no |
| distribution: matched - old (@1500) | +0.048 | [+0.016, +0.081] | yes |
| best SFT - base | -0.206 | [-0.311, -0.095] | yes |

#### Math model (Qwen2.5-Math-1.5B-Instruct)

| condition | acc | 95% CI |
|---|---|---|
| base | 0.381 | [0.286, 0.459] |
| terse SFT (600) | 0.214 | [0.109, 0.319] |
| terse DPO | 0.135 | [0.075, 0.194] |
| worked SFT (600) | 0.286 | [0.163, 0.407] |
| worked DPO | 0.111 | [0.051, 0.174] |
| worked SFT (1500) | 0.389 | [0.248, 0.519] |
| scaled-old SFT (1500) | 0.270 | [0.167, 0.371] |
| scaled-matched SFT (1500) | 0.238 | [0.148, 0.326] |

| contrast | diff | 95% CI | CI excludes 0? |
|---|---|---|---|
| format: worked - terse (SFT@600) | +0.071 | [-0.008, +0.159] | no |
| DPO - SFT (terse) | -0.079 | [-0.159, -0.008] | yes |
| DPO - SFT (worked) | -0.175 | [-0.295, -0.067] | yes |
| steps: 1500 - 600 (worked) | +0.103 | [+0.032, +0.171] | yes |
| volume, mismatched: scaled-old - worked (@1500) | -0.119 | [-0.217, -0.017] | yes |
| volume, matched: scaled-matched - worked (@1500) | -0.151 | [-0.283, -0.029] | yes |
| distribution: matched - old (@1500) | -0.032 | [-0.108, +0.044] | no |
| best SFT - base | +0.008 | [-0.103, +0.117] | no |

(cluster bootstrap over 26 test systems, B=10000, seed=20261009)

**Findings.**
1. **DPO hurts — the most robust result.** All four DPO-vs-SFT contrasts exclude zero.
2. **Format (worked − terse)** is significant for the general model (+0.071); the math model
   has the same point estimate but its interval includes zero.
3. **Training length.** 1500 vs 600 iterations helps the math model significantly (+0.103) and
   brings it to parity with its base (+0.008, n.s.). No significant effect for the general model.
4. **Synthetic scaling did not help.** At equal compute, the original synthetic data hurt both
   models. Distribution matching removed the harm for the general model (matched vs original
   +0.048, significant; matched vs real-only n.s.) but not for the math model (matched still
   −0.151 vs real-only, significant).
5. **Validation loss misleads.** Adding matched synthetic data kept validation loss (on real
   held-out solutions) flat and lower than real-only training, which drifts upward from
   memorisation — yet exact-answer accuracy stayed flat (general) or fell (math). See
   `report_assets/loss_1500.png`.

**Untested hypotheses** (labelled as such): matching marginal statistics misses the *joint*
structure of curated textbook systems (clean intermediate arithmetic); 91% synthetic dilutes
the real distribution; token loss is dominated by template text, not arithmetic.

**Integrity note.** While building the matched set, `sympy.nsimplify` was found to rewrite
some ordinary rationals as products of fractional prime powers (1387/50 →
5·2^(7/19)·3^(518/589)·…). Final answers were always protected by exact back-substitution,
but displayed steps were not. All call sites were replaced with an exact converter and a
step-level guard was added. An audit found **0 of ~36k** existing step strings affected, and
regenerating all prior datasets with the fix is **byte-identical** — no earlier result changes.

---

## 7. What makes this a clean study

- **Verifiable eval.** sympy grades every answer exactly — no judge model, no ambiguity.
- **No hallucination anywhere.** Every training target (real and synthetic) is
  independently verified; questions are never model-generated arithmetic.
- **Controlled grid.** model (general/math) × format (terse/worked) × stage (base/SFT/DPO),
  same test set throughout, matched 1.5B/4-bit/LoRA settings.
- **Mechanistic, not just numeric.** Each trend is explained by inspecting the actual
  generations (format-imitation vs. reasoning-suppression, per-method headroom).

## 8. Limits and next steps

- **Limits.** 1.5B / 4-bit models on a laptop; one training run (one seed) per condition;
  26 test systems give intervals of roughly ±0.1, so smaller differences should not be
  over-read.
- **Test the scaling hypotheses** from §6: constrain synthetic systems to clean (integer)
  intermediate arithmetic; vary the real:synthetic mixing ratio; select checkpoints by sympy
  accuracy on the validation set instead of by loss.
- **DPO** was harmful throughout; revisit with KL regularisation, on-policy pairs, or harder
  multi-step negatives — or at larger scale.
- **Method-faithfulness** is logged but keyword-based; a real check (does the solution execute
  the requested method's operations) is the next metric to build.
- **Scale** to a 7B base when a GPU is available.
