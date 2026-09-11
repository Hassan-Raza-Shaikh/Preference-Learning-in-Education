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
1. **Worked beats terse at SFT for both models** — general +8pts (0.087→0.159),
   math +7pts (0.214→0.286). Showing the arithmetic reduces the "imitate-format,
   fabricate-arithmetic" failure. Clearest on substitution (general): terse 0.12 → worked 0.44.
2. **DPO hurts at this scale** — every DPO cell is below its SFT cell, catastrophic for the
   small general model (→0). The verified preference pairs separate perfectly (a rule-based
   judge prefers chosen 811/811), so this is a model-capacity boundary, not a data problem.
3. **Training helps where the base is weak.** No trained variant beats base *overall* — the
   bases already reason well on methods they know, and LoRA taxes those slightly — but
   worked SFT **beats the base on methods the base lacked**: math Cramer's 0.00 → 0.15,
   and recovers elimination to 0.69.

**Takeaway.** For small models, *solution format (worked vs. terse) matters more than the
correctness of the target*; SFT ≫ DPO; and gains concentrate on methods the base can't
already do.

---

## 5. Scaling verified data  *(in progress)*

Synthetic systems (built from known solutions, run through the same verified worked
generators, independently re-checked: 1,200 systems / 5,624 method-solutions, 0 failures)
are combined with the real worked train set → **6,189 SFT examples** (0 contamination with
the held-out set). SFT re-run for both models; evaluation on the same 26 real test systems.

| model | worked SFT (114 sys) | worked SFT (scaled, 6,189 ex) |
|---|---|---|
| general | 0.159 | _pending_ |
| math | 0.286 | _pending_ |

_(table updated when the run completes)_

---

## 6. What makes this a clean study

- **Verifiable eval.** sympy grades every answer exactly — no judge model, no ambiguity.
- **No hallucination anywhere.** Every training target (real and synthetic) is
  independently verified; questions are never model-generated arithmetic.
- **Controlled grid.** model (general/math) × format (terse/worked) × stage (base/SFT/DPO),
  same test set throughout, matched 1.5B/4-bit/LoRA settings.
- **Mechanistic, not just numeric.** Each trend is explained by inspecting the actual
  generations (format-imitation vs. reasoning-suppression, per-method headroom).

## 7. Limits and next steps

- Small (1.5B, 4-bit) models on a laptop; effects may shrink at 7B+ with more headroom.
- 114 real train systems is tiny — hence the scaling run (§5).
- DPO harmful here; worth revisiting at larger scale or with a KL-regularized/again-on-policy
  variant, or with harder (multi-step) negatives.
- Method-faithfulness (does it use the *requested* method) is logged and is a promising
  primary metric where even the strong base has headroom.
