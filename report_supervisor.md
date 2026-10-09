---
title: "Training Small LLMs to Solve Systems of Equations by a Specified Method"
subtitle: "Verified data, solution format, preference tuning, and synthetic scaling"
author: "Hassan Raza Shaikh · Preference Learning in Education"
date: "October 2026 (revised)"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
header-includes:
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{xcolor}
  - \renewcommand{\arraystretch}{1.12}
---

\noindent\colorbox{gray!12}{\parbox{\dimexpr\linewidth-2\fboxsep}{\small
\textbf{Changes since the previous draft.}
(1) All results now carry 95\% confidence intervals (cluster bootstrap over the 26 test
systems). (2) Two new controls were run: a compute-matched control (1500 iterations) and a
distribution-matched synthetic set. (3) Two earlier claims are revised: the worked-vs-terse
format effect is statistically established for the general model only; and the earlier
explanation of the scaling result (``more iterations'') was wrong --- longer training does not
hurt, and synthetic data did not help even when distribution-matched. (4) An integrity bug in a
sympy simplification routine was found and fixed; an audit showed it affected none of the
data used in any result.}}

## 1. Objective

Build a verified dataset of math problems paired with **multiple solution methods**, and
test how to fine-tune a small language model to solve a linear system by a *specified*
method (substitution, elimination, Cramer's rule, matrix inverse, Gaussian elimination,
graphing). Controlled question: what moves accuracy --- the base model's prior, the
**format** of the training targets, the training stage (SFT vs. DPO), training length, or
added synthetic data?

## 2. Data and verified pipeline

- **Source:** `CAHLR/OATutor-Content` (13,287 problems). The systems-of-equations slice has
  751 problems; **164** state a parseable, uniquely-solvable linear system in text.
- **Questions are real; only solutions are generated.** Every solution is computed with
  **sympy** and verified by substituting the answer back into the original equations. No
  language model writes the maths, so no hallucinated arithmetic enters the data.
- **Two target formats:** *terse* (compact steps) and *worked* (every computation shown,
  e.g. $3(3y)-4y=5 \Rightarrow 5y=5$).
- **Preference pairs (DPO):** verified-correct vs. deterministically corrupted, verified-wrong.
- **Synthetic systems** (training only): an original set, and a *distribution-matched* set
  whose coefficients and constants are bootstrapped from the real **training** split, matching
  it on 2/3-variable mix (0.66), small coefficients (0.73 vs 0.71), fractional coefficients
  (0.06) and fractional solutions (0.38). Both sets: 5,624 examples.
- **Verification:** independent re-check, **0 failures** across all real and synthetic
  solutions and preference pairs; displayed steps are additionally screened for irrational
  rendering artifacts (none).

## 3. Experimental setup

- **Split by system:** 164 $\to$ 114 train / 24 valid / **26 test** (126 method-solutions),
  no leakage; the identical test set is used in every condition.
- **Matched base models (4-bit, MLX, Apple Silicon):** `Qwen2.5-1.5B-Instruct` (general)
  and `Qwen2.5-Math-1.5B-Instruct` (math). LoRA (8 layers) via `mlx-lm-lora`.
- **Conditions:** SFT at 600 iterations (terse, worked), DPO on top of SFT ($\beta=0.1$),
  and at 1500 iterations: worked SFT on the 114 real systems (compute-matched control),
  plus the same with 5,624 original or distribution-matched synthetic examples added.
- **Metric:** exact answer accuracy, graded by sympy. **95% CIs** from a cluster bootstrap
  that resamples the 26 test *systems* (items within a system are not independent);
  contrasts use paired resampling (B = 10,000).

## 4. Results

\begin{table}[H]
\centering
\small
\begin{tabular}{lcc}
\toprule
Condition & general & math \\
\midrule
Base (no training)                  & 0.389 [0.27, 0.50] & 0.381 [0.29, 0.46] \\
Terse SFT (600 it)                  & 0.087 [0.04, 0.15] & 0.214 [0.11, 0.32] \\
Terse SFT + DPO                     & 0.016 [0.00, 0.04] & 0.135 [0.08, 0.19] \\
Worked SFT (600 it)                 & 0.159 [0.09, 0.23] & 0.286 [0.16, 0.41] \\
Worked SFT + DPO                    & 0.000 [0.00, 0.00] & 0.111 [0.05, 0.17] \\
\midrule
Worked SFT (1500 it), real only     & \textbf{0.183} [0.09, 0.27] & \textbf{0.389} [0.25, 0.52] \\
\quad + original synthetic          & 0.095 [0.04, 0.15] & 0.270 [0.17, 0.37] \\
\quad + distribution-matched synth. & 0.143 [0.08, 0.21] & 0.238 [0.15, 0.33] \\
\bottomrule
\end{tabular}
\caption{Exact answer accuracy on the 26 held-out real systems, with 95\% cluster-bootstrap CIs.}
\end{table}

![Accuracy by condition with 95% CIs. Runs right of the dotted line use 1500 iterations; the dashed line is the shared base level.](report_assets/accuracy.pdf){width=96%}

\begin{table}[H]
\centering
\small
\begin{tabular}{lcc}
\toprule
Contrast (difference in accuracy) & general & math \\
\midrule
Format: worked $-$ terse (SFT, 600 it)       & \textbf{+0.071} [+0.02, +0.13] & +0.071 [$-$0.01, +0.16] \\
DPO $-$ SFT (terse)                          & \textbf{$-$0.071} [$-$0.12, $-$0.02] & \textbf{$-$0.079} [$-$0.16, $-$0.01] \\
DPO $-$ SFT (worked)                         & \textbf{$-$0.159} [$-$0.23, $-$0.09] & \textbf{$-$0.175} [$-$0.30, $-$0.07] \\
Length: 1500 $-$ 600 it (worked)             & +0.024 [$-$0.04, +0.09] & \textbf{+0.103} [+0.03, +0.17] \\
Add original synthetic (equal compute)       & \textbf{$-$0.087} [$-$0.17, $-$0.01] & \textbf{$-$0.119} [$-$0.22, $-$0.02] \\
Add matched synthetic (equal compute)        & $-$0.040 [$-$0.13, +0.04] & \textbf{$-$0.151} [$-$0.28, $-$0.03] \\
Matched $-$ original synthetic               & \textbf{+0.048} [+0.02, +0.08] & $-$0.032 [$-$0.11, +0.04] \\
Best SFT (1500 it) $-$ base                  & \textbf{$-$0.206} [$-$0.31, $-$0.10] & +0.008 [$-$0.10, +0.12] \\
\bottomrule
\end{tabular}
\caption{Paired contrasts with 95\% CIs. Bold: interval excludes zero.}
\end{table}

![SFT loss at 1500 iterations (train solid, validation dashed; validation = real held-out systems). With real data only, training loss falls to ~0.03 while validation loss drifts up (memorisation). Adding matched synthetic data keeps validation loss flat and lower --- yet exact-answer accuracy does not improve (general) or falls (math).](report_assets/loss_1500.pdf){width=96%}

**Mechanism of the terse failure (observed in outputs).** After terse SFT the model imitates
the format perfectly but fabricates the intermediate step: on $2x-6y=0,\ 3x-4y=5$ it writes
$x=3y$ then invents $15-18y=0$ (should be $5y=5$). Worked targets show that step.

## 5. Findings

1. **DPO hurts at this scale --- the most robust result.** All four DPO-vs-SFT contrasts are
   significantly negative ($-0.07$ to $-0.18$), even though the preference pairs are perfectly
   separable by a rule-based judge.
2. **Worked targets beat terse targets** for the general model (+0.071, significant). The math
   model shows the same point estimate, but its interval includes zero.
3. **Longer training helps the math model** (+0.103, significant) and brings it to parity with
   its base (0.389 vs 0.381). The general model stays significantly below its base.
4. **Synthetic scaling did not help.** At equal compute, adding the original synthetic data
   hurt both models. Distribution matching on four summary statistics removed the harm for
   the general model (matched vs original +0.048, significant) but not for the math model
   (matched synthetic still $-0.151$ vs real-only).
5. **Validation loss is a misleading signal here.** Synthetic data lowered loss on real
   held-out solutions while exact-answer accuracy stayed flat or fell.

## 6. Interpretation and next steps

The following are **hypotheses, not yet tested**:

- *Joint structure.* Matching marginal statistics is not enough; curated textbook systems are
  built so intermediate arithmetic stays clean, while independently sampled coefficients are
  not. Test: constrain synthetic systems to integer intermediate values.
- *Dilution.* Synthetic examples are 91% of the scaled training set. Test: vary the
  real:synthetic ratio / upsample real systems.
- *Loss vs. correctness.* Token loss is dominated by template text; arithmetic tokens are few.
  Test: select checkpoints by sympy accuracy on the validation set rather than by loss.
- *Method-faithfulness* (does the model use the requested method) is logged but currently
  keyword-based; a real check is the next metric to build.
- *Scale.* All results are for 1.5B/4-bit models; repeat at 7B when a GPU is available.

**Limits.** 26 test systems give wide intervals (roughly $\pm 0.1$); differences smaller than
that should not be over-read. Each condition is a single training run (one seed).

\vspace{1em}\hrule\vspace{0.6em}
\small\noindent Reproducible pipeline: questions verbatim from OATutor; solutions and grading by
sympy; every target independently re-verified (0 failures). Code, configs, logs and per-run
results:\\
\texttt{github.com/Hassan-Raza-Shaikh/Preference-Learning-in-Education}
