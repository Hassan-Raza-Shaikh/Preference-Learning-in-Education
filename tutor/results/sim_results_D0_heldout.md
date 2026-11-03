## D0 immediate reward, no prior, class_w 0.2 (held-out seed)

Simulated learners: 20 classes x 25 learners, 30 problems each, seed 20270101. Metric: share of the 3 skills a learner truly mastered (hidden state) at the end; 95% CI from a bootstrap over classes.

### A_no_individual_differences (sigma=0.0, rho=0.8)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.588 | [0.565, 0.611] | 0.33 |
| random | 0.638 | [0.614, 0.665] | 0.25 |
| rule_by_mastery | 0.713 | [0.694, 0.734] | 0.56 |
| adaptive_outcomes | 0.680 | [0.663, 0.700] | 0.28 |
| adaptive_outcomes+liking | 0.669 | [0.645, 0.693] | 0.28 |
| learner_choice | 0.623 | [0.587, 0.659] | 0.25 |
| oracle | 0.790 | [0.766, 0.815] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.092 | [+0.065, +0.122] |
| adaptive_outcomes - rule_by_mastery | -0.033 | [-0.061, -0.006] |
| adaptive_outcomes+liking - adaptive_outcomes | -0.011 | [-0.040, +0.017] |
| learner_choice - adaptive_outcomes | -0.057 | [-0.096, -0.017] |
| oracle - adaptive_outcomes | +0.110 | [+0.079, +0.139] |

### B_differences_honest_preferences (sigma=0.6, rho=0.8)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.569 | [0.537, 0.605] | 0.26 |
| random | 0.689 | [0.661, 0.719] | 0.25 |
| rule_by_mastery | 0.723 | [0.695, 0.753] | 0.37 |
| adaptive_outcomes | 0.713 | [0.683, 0.742] | 0.28 |
| adaptive_outcomes+liking | 0.703 | [0.676, 0.730] | 0.28 |
| learner_choice | 0.756 | [0.731, 0.781] | 0.36 |
| oracle | 0.870 | [0.849, 0.890] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.143 | [+0.110, +0.179] |
| adaptive_outcomes - rule_by_mastery | -0.011 | [-0.042, +0.022] |
| adaptive_outcomes+liking - adaptive_outcomes | -0.010 | [-0.049, +0.026] |
| learner_choice - adaptive_outcomes | +0.043 | [+0.019, +0.066] |
| oracle - adaptive_outcomes | +0.157 | [+0.120, +0.195] |

### C_differences_misleading_preferences (sigma=0.6, rho=0.0)

| policy | skills mastered | 95% CI | picks learner's best help type |
|---|---|---|---|
| fixed_example | 0.569 | [0.537, 0.605] | 0.26 |
| random | 0.689 | [0.661, 0.719] | 0.25 |
| rule_by_mastery | 0.723 | [0.695, 0.753] | 0.37 |
| adaptive_outcomes | 0.713 | [0.683, 0.742] | 0.28 |
| adaptive_outcomes+liking | 0.697 | [0.668, 0.729] | 0.29 |
| learner_choice | 0.690 | [0.667, 0.713] | 0.24 |
| oracle | 0.870 | [0.849, 0.890] | 1.00 |

| contrast (paired by class) | diff | 95% CI |
|---|---|---|
| adaptive_outcomes - fixed_example | +0.143 | [+0.110, +0.179] |
| adaptive_outcomes - rule_by_mastery | -0.011 | [-0.042, +0.022] |
| adaptive_outcomes+liking - adaptive_outcomes | -0.016 | [-0.049, +0.017] |
| learner_choice - adaptive_outcomes | -0.023 | [-0.053, +0.007] |
| oracle - adaptive_outcomes | +0.157 | [+0.120, +0.195] |

