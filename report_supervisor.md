---
title: "Format Over Correctness: Training Small LLMs to Solve Systems of Equations by Method"
author: "Hassan Raza Shaikh · Preference Learning in Education"
date: "September 2026"
geometry: margin=1in
fontsize: 11pt
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
header-includes:
  - \usepackage{booktabs}
  - \usepackage{float}
  - \renewcommand{\arraystretch}{1.15}
---

## 1. Objective

Build a verified dataset of math problems paired with **multiple solution methods**, and
test how to fine-tune a small language model to solve a linear system by a *specified*
method (substitution, elimination, Cramer's rule, matrix inverse, Gaussian elimination,
graphing). The controlled question: what moves accuracy — the base model's prior, the
**format** of the training targets, the training stage (SFT vs. DPO), or data volume?

## 2. Data and verified pipeline

- **Source:** `CAHLR/OATutor-Content` (13,287 problems, 17,761 steps). The
  systems-of-equations slice has 751 problems; **164** state a parseable, uniquely-solvable
  linear system in text.
- **Targets are generated, questions are not.** Questions are taken verbatim from OATutor;
  every *solution* is computed with **sympy** and verified by substituting the answer back
  into the original equations. **No language model produces the maths, so no hallucinated
  arithmetic can enter the data.**
- **Two target formats:** *terse* (compact steps) and *worked* (same maths, every
  computation shown, e.g. $3(3y)-4y=5 \Rightarrow 5y=5$).
- **Preference pairs (for DPO):** a verified-correct solution vs. a deterministically
  corrupted, verified-wrong one.
- **Verification (independent re-check): 0 failures** across 811 real and 5,624 synthetic
  method-solutions and all preference pairs.

## 3. Experimental setup

- **Split by system:** 164 → 114 train / 24 valid / **26 test** (126 method-solutions),
  no leakage, identical across all conditions.
- **Two matched base models (4-bit, MLX, Apple Silicon):**
  `Qwen2.5-1.5B-Instruct` (general) and `Qwen2.5-Math-1.5B-Instruct` (math).
- **Training:** LoRA (8 layers) via `mlx-lm-lora`; SFT then DPO ($\beta=0.1$).
- **Metric:** exact answer accuracy on held-out systems, graded by sympy (no LLM judge).

## 4. Results

Both bases start at essentially the same accuracy (0.389 vs 0.381) but with different
per-method strengths, giving a clean controlled comparison.

\begin{table}[H]
\centering
\begin{tabular}{lcccccc}
\toprule
Model & Base & Terse SFT & Terse DPO & Worked SFT & Worked DPO & Scaled SFT \\
\midrule
general & 0.389 & 0.087 & 0.016 & \textbf{0.159} & 0.000 & 0.095 \\
math    & 0.381 & 0.214 & 0.135 & \textbf{0.286} & 0.111 & 0.270 \\
\bottomrule
\end{tabular}
\caption{Exact answer accuracy on the 26 held-out real systems (126 method-solutions).}
\end{table}

![Overall accuracy by training condition. No trained variant beats the base overall; worked $\geq$ terse everywhere; DPO $\leq$ SFT everywhere.](report_assets/accuracy.pdf){width=95%}

![SFT training loss (train solid, validation dashed) for both models under terse vs. worked targets. Training converges cleanly in every case — the accuracy differences are not a training-stability artifact.](report_assets/loss.pdf){width=95%}

**Mechanism (why terse hurts).** After terse SFT the model imitates the format perfectly
(126/126 outputs end with a clean "Solution:") but stops reasoning and fabricates the
intermediate step: on $2x-6y=0,\ 3x-4y=5$ (answer $x=3,y=1$) it writes $x=3y$ then invents
$15-18y=0$ (should be $5y=5$). Worked targets, which show that step, recover most of the loss
(substitution: terse 0.12 $\to$ worked 0.44 for the general model).

## 5. Key findings

1. **Format $>$ correctness of the target.** Worked targets beat terse at SFT for *both*
   models (general +8pt, math +7pt) — the largest controllable lever here.
2. **SFT $\gg$ DPO at 1.5B/4-bit.** Every DPO run scored below its SFT start (general
   collapsed to $\approx 0$), despite perfectly separable preference pairs — a capacity
   boundary, not a data flaw.
3. **More data $\neq$ better.** Scaling 7$\times$ with verified synthetic systems left the
   math model flat and the general model worse. On inspection the synthetic set is
   0% fractional-solution (vs 37% in real data) and the scaled run used more iterations —
   so **distribution and training budget matter more than raw volume.**
4. **Training helps where the base is weak.** No trained variant beats base *overall*
   (bases already reason well on known methods), but worked SFT **beats the base on methods
   it lacked** — math Cramer's rule 0.00 $\to$ 0.15.

## 6. Limitations and next steps

- Small (1.5B / 4-bit) models on a laptop; the "training net-hurts a capable base" effect
  should shrink at 7B+ with more headroom.
- Clean scaling test needed: a **compute-matched** control (worked-114 at the scaled
  iteration count) to separate data volume from training length.
- Substantive fix: a **distribution-matched** synthetic set (~37% fractional solutions,
  matched coefficients), then re-scale.
- Report **method-faithfulness** (does it use the *requested* method) as a primary metric —
  logged, and where even the strong base has headroom.

\vspace{1.5em}\hrule\vspace{0.8em}
\small\noindent Reproducible pipeline: questions verbatim from OATutor; solutions and grading by sympy;
every target independently re-verified (0 failures).
Repo: \texttt{Hassan-Raza-Shaikh/Preference-Learning-in-Education}.
