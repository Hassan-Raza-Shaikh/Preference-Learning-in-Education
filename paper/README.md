# Paper: *Keeping Correctness and Preference Apart in AI Mathematics Tutoring*

The compiled paper is [`Keeping_Correctness_and_Preference_Apart.pdf`](Keeping_Correctness_and_Preference_Apart.pdf).
It is a draft for supervisor review.

## Files

| File | What |
|---|---|
| `main.tex` | Paper source (LaTeX) |
| `refs.bib` | Bibliography. Every entry was checked against Crossref or arXiv on 2026-11-27 |
| `build_assets.py` | Generates every table, figure and number macro in `generated/` from the repository's result files |
| `generated/` | Output of `build_assets.py` (do not edit by hand) |
| `LITERATURE_LOG.md` | Literature search log: queries, what was read and how far, what was blocked |
| `REVIEW.md` | In-project AI review of the draft (not an outside review) and how each finding was handled |
| `check_overlap.py` | Originality check against downloaded source abstracts (with a self-test that must catch a planted copy) |

## Rebuild

```bash
pip install -r requirements.txt
python paper/build_assets.py
cd paper && latexmk -pdf main.tex
```

LaTeX needs `texlive-latex-recommended`, `texlive-latex-extra`, `texlive-fonts-recommended`,
`texlive-bibtex-extra` and `latexmk`. The repository's cloud environment installs these in
its setup script.

## What to know before showing it

- **Novelty.** The paper claims no priority. Its literature search was not systematic,
  several indexes were not searched, and four cited papers could be read only through their
  bibliographic records and search summaries. See `LITERATURE_LOG.md`.
- **Study 1** has one training run per condition and 26 test systems. Its key causal
  experiment (on-policy DPO) is scripted but not run.
- **Study 2** is a simulation with invented parameters. It shows how the policies behave,
  not that pupils learn more.
- **The AI-use statement** in the paper says how Claude Code was used. Keep it.
- **Placeholders.** The author block has an `[Department, Institution]` placeholder. Fill
  it in, and add your supervisor where appropriate.
