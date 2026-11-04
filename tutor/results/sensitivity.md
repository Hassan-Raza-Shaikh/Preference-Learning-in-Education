# Simulation sensitivity analysis

Seed 20271201 (new), 20 classes x 25 learners per cell, original adaptive design (D0). Metric: share of the 3 skills truly mastered. Contrasts are paired by class; 95% bootstrap CI. `+` / `-` = CI excludes 0; `0` = it does not. **Simulated learners: this shows how the conclusions depend on the simulator's assumptions, not how real pupils learn.**

## Summary

- **Q1, rule vs always-worked-example** (48 grid cells): better in 48, no difference in 0, worse in 0.
- **Q2, adaptive bandit vs rule:** better in 8, no difference in 28, worse in 12. It picks the learner's best help type in 0.26–0.28 of cases (chance 0.25).
- **Q3, learner choice vs rule:** better in 8, no difference in 18, worse in 22.
- **Q4, can-fail check** (no expertise reversal, rule − fixed): -0.043 [-0.078, -0.012]: **PASSED** (the rule should lose here).

## Learner choice − rule

**T = 15 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | -0.079 - | -0.064 - | -0.061 - | -0.080 - |
| 0.3 | -0.130 - | -0.093 - | -0.028 0 | -0.050 - |
| 0.6 | -0.130 - | -0.071 - | -0.011 0 | +0.027 0 |
| 1.0 | -0.097 - | -0.011 0 | +0.080 + | +0.143 + |

**T = 30 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | -0.077 - | -0.050 - | -0.075 - | -0.082 - |
| 0.3 | -0.111 - | -0.067 - | -0.018 0 | -0.030 - |
| 0.6 | -0.095 - | -0.022 0 | +0.013 0 | +0.047 + |
| 1.0 | -0.080 - | -0.015 0 | +0.071 + | +0.119 + |

**T = 60 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | -0.019 0 | +0.022 0 | -0.012 0 | +0.007 0 |
| 0.3 | -0.048 - | -0.009 0 | +0.015 0 | +0.008 0 |
| 0.6 | -0.050 - | -0.008 0 | +0.028 0 | +0.039 + |
| 1.0 | -0.067 - | -0.009 0 | +0.073 + | +0.099 + |

## Adaptive bandit − rule

**T = 15 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | -0.027 0 | -0.027 0 | -0.027 0 | -0.027 0 |
| 0.3 | -0.072 - | -0.072 - | -0.072 - | -0.072 - |
| 0.6 | -0.069 - | -0.069 - | -0.069 - | -0.069 - |
| 1.0 | +0.031 0 | +0.031 0 | +0.031 0 | +0.031 0 |

**T = 30 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | -0.040 0 | -0.040 0 | -0.040 0 | -0.040 0 |
| 0.3 | -0.034 - | -0.034 - | -0.034 - | -0.034 - |
| 0.6 | -0.016 0 | -0.016 0 | -0.016 0 | -0.016 0 |
| 1.0 | +0.060 + | +0.060 + | +0.060 + | +0.060 + |

**T = 60 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | +0.024 0 | +0.024 0 | +0.024 0 | +0.024 0 |
| 0.3 | -0.005 0 | -0.005 0 | -0.005 0 | -0.005 0 |
| 0.6 | -0.010 0 | -0.010 0 | -0.010 0 | -0.010 0 |
| 1.0 | +0.060 + | +0.060 + | +0.060 + | +0.060 + |

## Rule − always worked example

**T = 15 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | +0.112 + | +0.112 + | +0.112 + | +0.112 + |
| 0.3 | +0.113 + | +0.113 + | +0.113 + | +0.113 + |
| 0.6 | +0.108 + | +0.108 + | +0.108 + | +0.108 + |
| 1.0 | +0.081 + | +0.081 + | +0.081 + | +0.081 + |

**T = 30 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | +0.143 + | +0.143 + | +0.143 + | +0.143 + |
| 0.3 | +0.143 + | +0.143 + | +0.143 + | +0.143 + |
| 0.6 | +0.149 + | +0.149 + | +0.149 + | +0.149 + |
| 1.0 | +0.143 + | +0.143 + | +0.143 + | +0.143 + |

**T = 60 problems per learner** (rows sigma, columns rho)

| sigma \ rho | -0.5 | 0.0 | 0.5 | 0.9 |
|---|---|---|---|---|
| 0.0 | +0.136 + | +0.136 + | +0.136 + | +0.136 + |
| 0.3 | +0.144 + | +0.144 + | +0.144 + | +0.144 + |
| 0.6 | +0.155 + | +0.155 + | +0.155 + | +0.155 + |
| 1.0 | +0.154 + | +0.154 + | +0.154 + | +0.154 + |

## Q4: different learning tables (sigma 0.6, rho 0.8, T 30)

| table | rule − fixed | learner choice − rule | adaptive − rule |
|---|---|---|---|
| reversal (default) | +0.149 [+0.117, +0.181] | +0.048 [+0.019, +0.075] | -0.016 [-0.044, +0.015] |
| weak reversal | +0.078 [+0.045, +0.112] | +0.020 [-0.012, +0.053] | -0.051 [-0.083, -0.017] |
| no reversal | -0.043 [-0.078, -0.012] | -0.061 [-0.099, -0.021] | -0.081 [-0.115, -0.045] |
| perturbed #1 | +0.113 [+0.064, +0.160] | +0.084 [+0.045, +0.121] | +0.024 [-0.017, +0.064] |
| perturbed #2 | +0.176 [+0.148, +0.204] | +0.035 [+0.013, +0.058] | -0.001 [-0.017, +0.016] |
| perturbed #3 | +0.161 [+0.120, +0.203] | +0.101 [+0.062, +0.137] | +0.045 [+0.011, +0.081] |
| perturbed #4 | +0.151 [+0.109, +0.192] | -0.005 [-0.041, +0.034] | -0.058 [-0.091, -0.021] |
| perturbed #5 | +0.251 [+0.205, +0.292] | +0.015 [-0.017, +0.047] | +0.019 [-0.025, +0.061] |

## Exploratory follow-up (added after seeing Q2; not part of the fixed protocol)

Where the bandit beat the rule (sigma 1.0), is it personalising or just varying the help? Comparison with RANDOM help:

| cell | adaptive − random | random − rule |
|---|---|---|
| sigma=1.0, T=30 | +0.013 [-0.015, +0.042] | +0.047 [+0.017, +0.076] |
| sigma=1.0, T=60 | +0.004 [-0.023, +0.030] | +0.056 [+0.028, +0.083] |
