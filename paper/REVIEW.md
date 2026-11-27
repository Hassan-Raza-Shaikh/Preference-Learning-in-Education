# In-project review of the draft paper

*These are in-project readings by separate AI sessions (Claude Code subagents), each briefed
only with the paper, the repository and the literature log. They are **not** outside or peer
review.*

## Round 1: adversarial review (2026-11-27)

The first reading was told to find errors. It regenerated `paper/generated/` independently
and found that it matched the committed version. It raised 25 findings: 4 must-fix,
13 should-fix and 8 minor.

The drafting session checked the two highest-stakes findings itself before acting:
- **#1:** re-derived from `data/multimethod_worked/systems_multimethod.jsonl` and the split
  manifest. Confirmed.
- **#11:** counted from `preference_pairs.jsonl`. Confirmed.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | must-fix | Study 1 split was by OATutor problem, not by system: 4 test problems (24/126 items) duplicate training systems | Confirmed (`experiments/check_split_leakage.py`). Disclosed in the paper (setup, abstract, limitations). "No leakage" corrected in `RESULTS.md`, `report_supervisor.md`, the Phase 1 doc and the learning guide. Leakage-free `--group-by system` split added, with a test. Re-run queued (A9) |
| 2 | must-fix | Abstract: rule beat fixed "in every setting tested" contradicts the no-reversal result | Abstract now states both |
| 3 | must-fix | Classroom study called "pre-registered" | Now "draft design, to be pre-registered" |
| 4 | must-fix | "Every displayed equation" ignored unparsed displays; Phase 1 count covers all generated solutions; unchecked count missing | Reworded; 14,112 unchecked now reported |
| 5 | should-fix | Pre-specification is self-attested | Labelled "self-reported; not externally registered" |
| 6 | should-fix | "Worst case" DPO wording | Corrected (largest drop: math, worked) |
| 7 | should-fix | Table variants and can-fail check run at one cell; "eight" counted the default | Stated; "seven alternatives" |
| 8 | should-fix | Salden result claim from summaries; contrast mismatch | Kept general; contrast difference stated |
| 9 | should-fix | Doroudi 2019 specific conclusion | Removed |
| 10 | should-fix | Schmucker hedge firmed up | Quoted with hedge; log updated |
| 11 | should-fix | DPO corruption mix | 769/811 sign flip stated |
| 12 | should-fix | "A few tokens" | "Near-identical; 12–16% fewer steps" |
| 13 | should-fix | Appendix D incomplete | Completed |
| 14 | should-fix | `build_assets.py` read a nonexistent failure field | Fixed (counts the `failures` list) |
| 15 | should-fix | Bug attribution (checker vs reveal detector) | Corrected |
| 16 | should-fix | Step check described as a Phase 1 filter | Described as post hoc; display blemishes noted |
| 17 | should-fix | Power-analysis caveat; "medium" for d = 0.4 | Caveat restored; wording corrected |
| 18–25 | minor | Plural seeds; band boundary; policy details; figure vs counts; missing method details; CI width; Kirschner and "active harm" wording; interpretation of the choice gain | All addressed |

## Round 2: confirmation of fixes (2026-11-27)

A second, separate session checked each Round 1 correction against the repository, at
commit `b0f5752`.

**Result.** 17 findings were confirmed fixed. Six were only partly fixed:
- #1: a table caption still said "26 test systems";
- #5: "self-reported" was missing in the abstract, contributions and discussion;
- #6: a new wording error, "fell furthest in absolute terms";
- #8: a residual Salden result claim, in the contributions, discussion and literature log;
- #20: the faded-help cap is "half, rounded up";
- #23: the CI width is about ±0.14.

It also found leftover "pre-registered" wording in `tutor/switch_rule.py`,
`tutor/results/switch_rule.md`, `docs/04`, `docs/05` and the `analyze_ci.py` docstring. It
noted that two of the five perturbed tables do not make worked examples best for novices,
and that the DPO training pairs use sign flips in 529 of 565 cases (94%).

**Action.** The drafting session re-checked the two factual points itself and confirmed
both: `tutor.sensitivity.perturbed_tables()`, and the training-pair counts in
`preference_pairs.jsonl`. It then fixed every item above.

**Not done:** the Round 2 fixes were not read by a third separate session. They are small
wording corrections, listed in the commit that follows this file's update.

**Checks after Round 2:**
- the paper builds with no unresolved references (17 pages);
- the originality check gives a longest shared run of 8 words, the quoted and cited phrase
  from Schmucker et al.;
- 48 tests pass.
