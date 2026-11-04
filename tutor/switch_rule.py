"""Pre-registered test of the 'rule + switch' policy (hypothesis from the sensitivity analysis).

Background (tutor/results/sensitivity.md): the mastery rule gives every pupil in a mastery
band the same help. When pupils differ a lot (sigma = 1.0), even RANDOM help beat it,
because variety lets some pupils hit a help type that works for them.

HYPOTHESIS: 'rule + switch' (start with the rule's help type; after each consecutive wrong
answer on a skill move to the next-nearest help type; back to the rule's choice after a
right answer; learner_model.rule_switch_arm) keeps the rule's strength when pupils are
similar and gains the variety benefit when they differ.

PROTOCOL, fixed before running (2026-11-04):
  Fresh seed 20280101, used by no earlier run. 20 classes x 25 pupils per cell.
  Grid sigma in {0, 0.3, 0.6, 1.0} x T in {15, 30, 60}; rho = 0.5 (no policy here uses
  stated preference). Contrasts are paired by class, with a 95% bootstrap CI.
  SUCCESS requires BOTH:
    (a) no significant loss vs the rule when pupils are similar: switch − rule is not
        significantly negative in any cell with sigma in {0, 0.3};
    (b) a significant gain when they differ a lot: switch − rule is significantly positive
        in both cells with sigma = 1.0 and T in {30, 60}.
  Also reported, not part of the criteria: switch − random at every cell, and the
  no-expertise-reversal learning table.
  DECISION: pass -> offer 'rule_switch' as an optional app mode (not the default);
  fail -> record as a negative result.

    python -m tutor.switch_rule        # -> tutor/results/switch_rule.{json,md}
"""
from __future__ import annotations

import json
import os

from .sensitivity import BASE_VARIANTS
from .simulate import OUT, boot_ci, run_class

SEED = 20280101
N_CLASSES = 20
SIGMAS = [0.0, 0.3, 0.6, 1.0]
HORIZONS = [15, 30, 60]
RHO = 0.5
POLS = ["fixed_example", "random", "rule_by_mastery", "rule_switch"]


def contrast(per, a, b):
    d = [x["mastered"] - y["mastered"] for x, y in zip(per[a], per[b])]
    ci = boot_ci(d)
    return {"diff": round(sum(d) / len(d), 4), "ci": [round(c, 4) for c in ci],
            "sig": "+" if ci[0] > 0 else ("-" if ci[1] < 0 else "0")}


def cell(scen, T):
    per = {p: [run_class(p, scen, SEED + c, 25, T) for c in range(N_CLASSES)] for p in POLS}
    return {"mastered": {p: round(sum(r["mastered"] for r in v) / N_CLASSES, 4) for p, v in per.items()},
            "switch_minus_rule": contrast(per, "rule_switch", "rule_by_mastery"),
            "switch_minus_random": contrast(per, "rule_switch", "random"),
            "switch_minus_fixed": contrast(per, "rule_switch", "fixed_example")}


def run():
    grid = {f"sigma={s}, T={T}": {"sigma": s, "T": T, **cell({"sigma": s, "rho": RHO}, T)}
            for s in SIGMAS for T in HORIZONS}
    no_rev = cell({"sigma": 0.6, "rho": RHO, "base": BASE_VARIANTS["no reversal"]}, 30)
    a_cells = [c for c in grid.values() if c["sigma"] in (0.0, 0.3)]
    b_cells = [c for c in grid.values() if c["sigma"] == 1.0 and c["T"] in (30, 60)]
    crit_a = all(c["switch_minus_rule"]["sig"] != "-" for c in a_cells)
    crit_b = all(c["switch_minus_rule"]["sig"] == "+" for c in b_cells)
    return {"protocol": {"seed": SEED, "classes_per_cell": N_CLASSES, "sigmas": SIGMAS, "horizons": HORIZONS,
                         "rho": RHO},
            "grid": grid, "no_reversal_table": no_rev,
            "criteria": {"a_no_loss_when_similar": crit_a, "b_gain_when_different": crit_b,
                         "passed": crit_a and crit_b}}


def to_markdown(res):
    c = res["criteria"]
    f = lambda x: f"{x['diff']:+.3f} [{x['ci'][0]:+.3f}, {x['ci'][1]:+.3f}] {x['sig']}"
    L = ["# Pre-registered test: 'rule + switch' vs the mastery rule\n",
         f"Seed {SEED} (fresh), {N_CLASSES} classes x 25 simulated pupils per cell. `+`/`-` = 95% CI excludes 0. "
         "Protocol and success criteria: docstring of `tutor/switch_rule.py`. "
         "**Simulated pupils: this tests the mechanism, not real learning.**\n",
         f"- (a) no significant loss when pupils are similar (sigma 0, 0.3): **{'met' if c['a_no_loss_when_similar'] else 'NOT met'}**",
         f"- (b) significant gain when pupils differ a lot (sigma 1.0, T 30 and 60): **{'met' if c['b_gain_when_different'] else 'NOT met'}**",
         f"- **Overall: {'PASSED' if c['passed'] else 'FAILED'}**\n",
         "| cell | rule | switch | switch − rule | switch − random | switch − fixed |", "|---|---|---|---|---|---|"]
    for k, v in res["grid"].items():
        m = v["mastered"]
        L.append(f"| {k} | {m['rule_by_mastery']:.3f} | {m['rule_switch']:.3f} | {f(v['switch_minus_rule'])} | "
                 f"{f(v['switch_minus_random'])} | {f(v['switch_minus_fixed'])} |")
    n = res["no_reversal_table"]
    L += ["", "No-expertise-reversal learning table (sigma 0.6, T 30), reported, not a criterion: "
          f"switch − rule {f(n['switch_minus_rule'])}; switch − fixed {f(n['switch_minus_fixed'])}."]
    return "\n".join(L) + "\n"


def main():
    res = run()
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "switch_rule.json"), "w"), indent=1)
    md = to_markdown(res)
    open(os.path.join(OUT, "switch_rule.md"), "w").write(md)
    print(md)


if __name__ == "__main__":
    main()
