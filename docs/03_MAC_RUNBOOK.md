# Runbook: Track A steps that need the Apple Silicon machine

*Created 2026-11-03. The cloud environment used for the November work has no MLX/GPU, so
these steps were prepared and unit-tested there but **not run**. Run them on the Mac that
produced Phase 1, then record results in [`WORKLOG.md`](WORKLOG.md).*

## 0. Setup

```bash
git pull
pip install sympy numpy pytest mlx mlx-lm mlx-lm-lora
python -m pytest tests -q
```

Fused models now live in `$PLE_SCRATCH/models` (default `../ple_scratch`). To reuse the
Phase 1 models, point it at the old scratchpad folder that contains `models/`:

```bash
export PLE_SCRATCH=/path/to/old/scratchpad
```

If the OATutor data must be regenerated, pin the source to the Phase 1 commit (upstream
has changed since; regenerating from the newer commit changes the counts):

```bash
git -C OATutor-Content checkout 2f27a597268ae5d1826f69083ad91cf8864a0c05
```

## 1. A2: structural method-faithfulness on the real generations (about 10 min + labelling)

```bash
python -m experiments.rescore_faithfulness --sample 60
```

This re-scores every `data/train/gen_*.jsonl` with the new structural check and writes
`data/train/faithfulness_label_sample.csv`.

Then hand-label it. Hide the `structural`, `keyword` and `evidence` columns first, and fill
`human_faithful` with 1 or 0 for "did this solution actually use the requested method?".
Then run:

```bash
python -m experiments.rescore_faithfulness --agreement data/train/faithfulness_label_sample.csv
```

**Why:** the check was only validated on our own gold solutions (recall ≥ 0.972,
false-accept ≤ 0.007), and its rules were refined on that same set, so we need its
agreement with a human on real model outputs before reporting it.

## 2. A1: is the DPO failure caused by how the pairs were built? (several hours)

```bash
python -m experiments.onpolicy_dpo sample --only math
python -m experiments.onpolicy_dpo pairs  --only math
python -m experiments.onpolicy_dpo train  --only math
```

This runs three new DPO conditions on top of the existing worked SFT model:
on-policy pairs at β = 0.1 and β = 0.5, and the original offline pairs at β = 0.5.
Compare them with Phase 1's offline β = 0.1 result (math worked DPO = 0.111). Repeat with
`--only general`.

To read the results, compare each new condition with that offline β = 0.1 baseline:
- **On-policy pairs ≈ SFT or better:** pair construction was the problem.
- **Offline β = 0.5 recovers:** the update was too strong.
- **Neither helps:** this supports the capacity explanation.

Add the new conditions to `CONDS` in `experiments/analyze_ci.py` and recompute CIs.

## 3. A3: seeds (the single largest gap for a paper)

Re-run the key conditions with 3 seeds each: worked SFT@1500 and worked DPO, for both models.
`mlx_lm_lora.train` takes a `--seed` option; check `python -m mlx_lm_lora.train --help`
for the exact flag name in your installed version. Then add it to `sft_args`/`dpo_args`
in `experiments/run_all.py` and use a different `--tag` per seed.

## 4. A6: choose checkpoints by sympy accuracy, not by loss

Save adapters periodically during SFT. The flag name varies by version; see
`--help` for an option such as `--save-every`. Then run `experiments/generate.py` with
`--adapter <checkpoint>` on the **validation** systems and keep the checkpoint with the
best sympy accuracy. (`generate.py` currently reads the test systems; point `TEST_SYS` at a
validation-systems file for this step and never select on test.)

## 5. Not here

- **A7 (7B models):** needs a larger GPU.
- **A5 (clean intermediate arithmetic):** no longer planned. Measured on 2026-11-03, real
  and matched synthetic systems have the same share of fraction-free intermediate steps
  (0.387 vs 0.398), so that version of the hypothesis is not supported.
