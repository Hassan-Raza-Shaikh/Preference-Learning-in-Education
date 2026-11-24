## D2 rule prior 4 (held-out seed)

Simulated learners: 20 classes x 25 learners, 30 problems each, seed 20270101. Metric: share of the 3 skills a learner truly mastered (hidden state) at the end; 95% CI from a bootstrap over classes.

### A_no_individual_differences (sigma=0.0, rho=0.8)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.588 | [0.565, 0.611] | 0.33 |
| random | 0.638 | [0.614, 0.665] | 0.25 |
| rule_by_mastery | 0.713 | [0.694, 0.734] | 0.56 |
| adaptive_outcomes | 0.647 | [0.621, 0.674] | 0.31 |
| adaptive_outcomes+liking | 0.651 | [0.619, 0.682] | 0.31 |
| learner_choice | 0.654 | [0.634, 0.674] | 0.28 |
| oracle | 0.790 | [0.766, 0.815] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.059 | [+0.022, +0.095] |
| adaptive_outcomes - rule_by_mastery | -0.066 | [-0.093, -0.038] |
| adaptive_outcomes+liking - adaptive_outcomes | +0.003 | [-0.029, +0.038] |
| learner_choice - adaptive_outcomes | +0.007 | [-0.024, +0.036] |
| oracle - adaptive_outcomes | +0.143 | [+0.116, +0.171] |
| rule_by_mastery - fixed_example | +0.125 | [+0.097, +0.155] |
| learner_choice - rule_by_mastery | -0.059 | [-0.089, -0.030] |

### B_differences_honest_preferences (sigma=0.6, rho=0.8)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.569 | [0.537, 0.605] | 0.26 |
| random | 0.689 | [0.661, 0.719] | 0.25 |
| rule_by_mastery | 0.723 | [0.695, 0.753] | 0.37 |
| adaptive_outcomes | 0.701 | [0.681, 0.723] | 0.29 |
| adaptive_outcomes+liking | 0.740 | [0.712, 0.766] | 0.32 |
| learner_choice | 0.763 | [0.743, 0.785] | 0.38 |
| oracle | 0.870 | [0.849, 0.890] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.132 | [+0.096, +0.167] |
| adaptive_outcomes - rule_by_mastery | -0.022 | [-0.049, +0.006] |
| adaptive_outcomes+liking - adaptive_outcomes | +0.039 | [+0.011, +0.065] |
| learner_choice - adaptive_outcomes | +0.062 | [+0.037, +0.087] |
| oracle - adaptive_outcomes | +0.169 | [+0.142, +0.196] |
| rule_by_mastery - fixed_example | +0.154 | [+0.119, +0.189] |
| learner_choice - rule_by_mastery | +0.040 | [+0.014, +0.065] |

### C_differences_misleading_preferences (sigma=0.6, rho=0.0)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.569 | [0.537, 0.605] | 0.26 |
| random | 0.689 | [0.661, 0.719] | 0.25 |
| rule_by_mastery | 0.723 | [0.695, 0.753] | 0.37 |
| adaptive_outcomes | 0.701 | [0.681, 0.723] | 0.29 |
| adaptive_outcomes+liking | 0.707 | [0.680, 0.734] | 0.29 |
| learner_choice | 0.689 | [0.662, 0.715] | 0.25 |
| oracle | 0.870 | [0.849, 0.890] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.132 | [+0.096, +0.167] |
| adaptive_outcomes - rule_by_mastery | -0.022 | [-0.049, +0.006] |
| adaptive_outcomes+liking - adaptive_outcomes | +0.005 | [-0.029, +0.040] |
| learner_choice - adaptive_outcomes | -0.012 | [-0.042, +0.015] |
| oracle - adaptive_outcomes | +0.169 | [+0.142, +0.196] |
| rule_by_mastery - fixed_example | +0.154 | [+0.119, +0.189] |
| learner_choice - rule_by_mastery | -0.034 | [-0.069, -0.001] |

