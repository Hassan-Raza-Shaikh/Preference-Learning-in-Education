"""Simulated-learner evaluation of the adaptation loop. Milestone M4.

WHAT THIS CAN AND CANNOT SHOW
  It shows whether the tutor's machinery (knowledge tracing + Thompson sampling over
  explanation types, with class pooling) DETECTS learner differences and adapts to them,
  under a learner model WE wrote. It does NOT show that real children learn more: that
  needs the school study. Every number here is conditional on the simulator's assumptions,
  which are listed in SIM_ASSUMPTIONS and written into the results file.

Simulated learner (hidden from the tutor)
  * level per skill in {0 novice, 1 partial, 2 mastered}; start mostly at 0
  * after an explanation of type `arm`, moves up one level with probability
        min(0.95, BASE[level][arm] * mult[arm])
    BASE encodes the expertise-reversal effect (worked examples help novices most,
    lighter support helps more advanced learners). `mult` is the learner's individual
    efficacy multiplier per arm, log-normal with spread `sigma` (sigma = 0: everyone the same).
  * answers correctly with probability P_CORRECT[level]
  * stated liking per arm = rho * z(log mult) + sqrt(1 - rho^2) * noise
    (rho = how well what a learner LIKES matches what WORKS for them)

The tutor uses the same code as the app (tutor.learner_model): BKT pacing for every policy;
policies differ only in how the explanation type is chosen.

Run:  python -m tutor.simulate            -> tutor/results/sim_results.json (+ .md, figure)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random

from .content import ARMS
from .learner_model import (
    RULE, rule_prior, rule_switch_arm, BKTParams, ClassStats, LearnerState, PolicyConfig, arm_scores, band, bkt_update,
    next_skill, offer_two, record_choice, record_liking, record_outcome,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tutor", "results")

BASE = {0: {"example": 0.30, "faded": 0.18, "outline": 0.08, "none": 0.04},
        1: {"example": 0.12, "faded": 0.25, "outline": 0.22, "none": 0.15}}
P_CORRECT = {0: 0.10, 1: 0.50, 2: 0.92}
INIT_LEVEL = [0.6, 0.3, 0.1]
SKILLS = ["substitution", "elimination", "graphing"]
SIM_ASSUMPTIONS = {
    "learning_prob_base": BASE, "p_correct_by_level": P_CORRECT, "initial_level_dist": INIT_LEVEL,
    "skills": SKILLS, "note": "Invented to encode the expertise-reversal effect qualitatively; "
                              "not fitted to data. Results are conditional on these values.",
}

SCENARIOS = {
    "A_no_individual_differences": {"sigma": 0.0, "rho": 0.8},
    "B_differences_honest_preferences": {"sigma": 0.6, "rho": 0.8},
    "C_differences_misleading_preferences": {"sigma": 0.6, "rho": 0.0},
}
POLICIES = ["fixed_example", "random", "rule_by_mastery", "adaptive_outcomes",
            "adaptive_outcomes+liking", "learner_choice", "oracle",
            "rule_switch"]   # appended last so earlier policies keep their random streams


class SimLearner:
    def __init__(self, rng: random.Random, sigma: float, rho: float, base=None):
        self.base = base or BASE                     # learning-probability table (sensitivity runs vary it)
        self.level = {s: rng.choices([0, 1, 2], INIT_LEVEL)[0] for s in SKILLS}
        logm = {a: rng.gauss(0, 1) for a in ARMS}
        self.mult = {a: math.exp(sigma * logm[a]) for a in ARMS}
        self.like = {a: rho * logm[a] + math.sqrt(1 - rho ** 2) * rng.gauss(0, 1) for a in ARMS}

    def p_learn(self, skill, arm):
        lv = self.level[skill]
        return 0.0 if lv >= 2 else min(0.95, self.base[lv][arm] * self.mult[arm])

    def study(self, skill, arm, rng):
        if rng.random() < self.p_learn(skill, arm):
            self.level[skill] += 1
        return rng.random() < P_CORRECT[self.level[skill]]

    def pick(self, offered, rng):                    # stated preference, with noise
        return max(offered, key=lambda a: self.like[a] + rng.gauss(0, 0.5))

    def rates_helpful(self, arm, rng):
        return self.like[arm] + rng.gauss(0, 0.5) > 0


DEFAULT_DESIGN = {"reward": "immediate", "prior": None, "class_w": 0.2}


def run_class(policy, scen, seed, n_learners=25, T=30, prm=BKTParams(), threshold=0.95, design=None):
    """One class; learners interleaved so class pooling works as in a real classroom.

    `design` (adaptive policies only): reward = 'immediate' (outcome on this problem) or
    'delayed' (outcome on the NEXT problem of the same skill, credited to this explanation);
    prior = None or pseudo-count strength of the rule prior; class_w = class pooling weight.
    """
    design = {**DEFAULT_DESIGN, **(design or {})}
    lrng = random.Random(seed)                         # same learners for every policy (paired)
    learners = [SimLearner(lrng, scen["sigma"], scen["rho"], scen.get("base")) for _ in range(n_learners)]
    rng = random.Random(seed * 7919 + POLICIES.index(policy))
    w = 0.3 if policy in ("adaptive_outcomes+liking", "learner_choice") else 0.0
    cfg = PolicyConfig(preference_weight=w, class_prior_weight=design["class_w"], prior=rule_prior(design["prior"]))
    last = {}                                           # (learner, skill) -> (band, arm) awaiting delayed credit
    fails = {}                                          # (learner, skill) -> consecutive wrong answers
    cs = ClassStats()
    states = [LearnerState(learner_id=str(i)) for i in range(n_learners)]
    start = [dict(sl.level) for sl in learners]
    correct = [0] * n_learners
    steps = [0] * n_learners
    agree = []                                          # did the chosen arm = learner's best arm?
    for _t in range(T):
        for i, (sl, ls) in enumerate(zip(learners, states)):
            skill = next_skill(ls, SKILLS, prm, threshold, rng)
            if skill is None:
                continue
            p = ls.p(skill, prm)
            b = band(p)
            if policy == "fixed_example":
                arm = "example"
            elif policy == "random":
                arm = rng.choice(ARMS)
            elif policy == "rule_by_mastery":
                arm = RULE[b]
            elif policy == "rule_switch":
                arm = rule_switch_arm(b, fails.get((i, skill), 0))
            elif policy == "oracle":
                arm = max(ARMS, key=lambda a: sl.p_learn(skill, a)) if sl.level[skill] < 2 else "none"
            elif policy == "learner_choice":
                offered = offer_two(ls, cs, b, cfg, rng)
                arm = sl.pick(offered, rng)
                record_choice(ls, cs, b, arm, [a for a in offered if a != arm][0])
            else:
                s = arm_scores(ls, cs, b, cfg, rng)
                arm = max(s, key=s.get)
            if sl.level[skill] < 2:
                agree.append(arm == max(ARMS, key=lambda a: sl.p_learn(skill, a)))
            ok = sl.study(skill, arm, rng)
            ls.mastery[skill] = bkt_update(p, ok, prm)
            if design["reward"] == "delayed":
                if (i, skill) in last:
                    pb, pa = last[(i, skill)]
                    record_outcome(ls, cs, pb, pa, ok)
                last[(i, skill)] = (b, arm)
            else:
                record_outcome(ls, cs, b, arm, ok)
            if policy == "adaptive_outcomes+liking" or policy == "learner_choice":
                record_liking(ls, cs, b, arm, sl.rates_helpful(arm, rng))
            fails[(i, skill)] = 0 if ok else fails.get((i, skill), 0) + 1
            correct[i] += ok
            steps[i] += 1
    mastered = [sum(sl.level[s] == 2 for s in SKILLS) / len(SKILLS) for sl in learners]
    gain = [sum(sl.level[s] - st[s] for s in SKILLS) / len(SKILLS) for sl, st in zip(learners, start)]
    return {"mastered": sum(mastered) / n_learners, "gain": sum(gain) / n_learners,
            "accuracy": sum(correct) / max(1, sum(steps)), "steps": sum(steps) / n_learners,
            "best_arm_rate": sum(agree) / max(1, len(agree))}


def boot_ci(vals, B=5000, seed=1):
    rng = random.Random(seed)
    n = len(vals)
    means = sorted(sum(rng.choice(vals) for _ in range(n)) / n for _ in range(B))
    return [means[int(0.025 * B)], means[int(0.975 * B) - 1]]


def run(n_classes=20, n_learners=25, T=30, seed=20261103, design=None, scenarios=None):
    res = {"assumptions": SIM_ASSUMPTIONS, "n_classes": n_classes, "learners_per_class": n_learners,
           "problems_per_learner": T, "seed": seed, "design": {**DEFAULT_DESIGN, **(design or {})},
           "scenarios": {}}
    for sname, scen in SCENARIOS.items():
        if scenarios and sname not in scenarios:
            continue
        per = {}
        for pol in POLICIES:
            runs = [run_class(pol, scen, seed + c, n_learners, T, design=design) for c in range(n_classes)]
            per[pol] = {k: [r[k] for r in runs] for k in runs[0]}
        summary = {}
        for pol in POLICIES:
            m = per[pol]["mastered"]
            summary[pol] = {"mastered": sum(m) / len(m), "mastered_ci": boot_ci(m),
                            "gain": sum(per[pol]["gain"]) / n_classes,
                            "accuracy": sum(per[pol]["accuracy"]) / n_classes,
                            "best_arm_rate": sum(per[pol]["best_arm_rate"]) / n_classes}
        contrasts = {}
        for a, b in [("adaptive_outcomes", "fixed_example"), ("adaptive_outcomes", "rule_by_mastery"),
                     ("adaptive_outcomes+liking", "adaptive_outcomes"), ("learner_choice", "adaptive_outcomes"),
                     ("oracle", "adaptive_outcomes"),
                     # the two contrasts the school pilot will estimate (docs/pilot/STUDY_DESIGN.md)
                     ("rule_by_mastery", "fixed_example"), ("learner_choice", "rule_by_mastery")]:
            d = [x - y for x, y in zip(per[a]["mastered"], per[b]["mastered"])]   # paired by class
            contrasts[f"{a} - {b}"] = {"diff": sum(d) / len(d), "ci": boot_ci(d)}
        res["scenarios"][sname] = {"params": scen, "policies": summary, "contrasts": contrasts}
    return res


def to_markdown(res):
    lines = [f"Simulated learners: {res['n_classes']} classes x {res['learners_per_class']} learners, "
             f"{res['problems_per_learner']} problems each, seed {res['seed']}. "
             "Metric: share of the 3 skills a learner truly mastered (hidden state) at the end; "
             "95% CI from a bootstrap over classes.", ""]
    for sname, s in res["scenarios"].items():
        lines += [f"### {sname} (sigma={s['params']['sigma']}, rho={s['params']['rho']})", "",
                  "| policy | skills mastered | 95% CI | picks learner's best help type |", "|---|---|---|---|"]
        for pol, v in s["policies"].items():
            lines.append(f"| {pol} | {v['mastered']:.3f} | [{v['mastered_ci'][0]:.3f}, {v['mastered_ci'][1]:.3f}] "
                         f"| {v['best_arm_rate']:.2f} |")
        lines += ["", "| contrast (paired by class) | diff | 95% CI |", "|---|---|---|"]
        for k, v in s["contrasts"].items():
            lines.append(f"| {k} | {v['diff']:+.3f} | [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] |")
        lines.append("")
    return "\n".join(lines)


def figure(res, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, axes = plt.subplots(1, len(res["scenarios"]), figsize=(13, 4.2), sharey=True)
    for ax, (sname, s) in zip(axes, res["scenarios"].items()):
        pols = list(s["policies"])
        m = [s["policies"][p]["mastered"] for p in pols]
        lo = [m[i] - s["policies"][p]["mastered_ci"][0] for i, p in enumerate(pols)]
        hi = [s["policies"][p]["mastered_ci"][1] - m[i] for i, p in enumerate(pols)]
        colors = ["#9aa3b5" if p in ("fixed_example", "random", "rule_by_mastery") else
                  ("#c56a3a" if p == "oracle" else "#3a5ba0") for p in pols]
        ax.bar(range(len(pols)), m, yerr=[lo, hi], color=colors, capsize=3)
        ax.set_xticks(range(len(pols)))
        ax.set_xticklabels([p.replace("_", "\n").replace("+", "\n+") for p in pols], fontsize=7)
        ax.set_title(f"{sname.split('_', 1)[1].replace('_', ' ')}\n(sigma={s['params']['sigma']}, rho={s['params']['rho']})",
                     fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("share of skills truly mastered")
    fig.suptitle("Simulated learners (mechanism check, not evidence about real children)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return True


DESIGNS = {   # design search, run on the DEVELOPMENT seed only
    "D0 immediate reward, no prior, class_w 0.2": {},
    "D1 class_w 1.0": {"class_w": 1.0},
    "D2 rule prior 4": {"prior": 4},
    "D3 rule prior 4 + class_w 1.0": {"prior": 4, "class_w": 1.0},
    "D4 delayed reward": {"reward": "delayed"},
    "D5 delayed reward + rule prior 4": {"reward": "delayed", "prior": 4},
}
DEV_SEED, HELDOUT_SEED = 20261103, 20270101
CHOSEN = "D2 rule prior 4"   # picked on the dev seed; did NOT replicate on the held-out seed


def design_search(n_classes=20):
    lines = [f"Design search on the development seed ({DEV_SEED}); scenarios A and B; "
             "metric = share of skills truly mastered; d_rule = adaptive minus rule-by-mastery "
             "(paired by class, 95% bootstrap CI).", "",
             "| T | design | scenario | adaptive | rule | picks best help | d_rule [95% CI] |", "|---|---|---|---|---|---|---|"]
    for T in (30, 60):
        for name, d in DESIGNS.items():
            r = run(n_classes=n_classes, T=T, seed=DEV_SEED, design=d,
                    scenarios=["A_no_individual_differences", "B_differences_honest_preferences"])
            for sname, sc in r["scenarios"].items():
                po, c = sc["policies"], sc["contrasts"]["adaptive_outcomes - rule_by_mastery"]
                lines.append(f"| {T} | {name} | {sname[0]} | {po['adaptive_outcomes']['mastered']:.3f} | "
                             f"{po['rule_by_mastery']['mastered']:.3f} | {po['adaptive_outcomes']['best_arm_rate']:.2f} | "
                             f"{c['diff']:+.3f} [{c['ci'][0]:+.3f}, {c['ci'][1]:+.3f}] |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", type=int, default=20)
    ap.add_argument("--learners", type=int, default=25)
    ap.add_argument("--problems", type=int, default=30)
    ap.add_argument("--design-search", action="store_true", help="run the design search (dev seed)")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.design_search:
        md = design_search(a.classes)
        open(os.path.join(OUT, "design_search.md"), "w").write(md + "\n")
        print(md)
        return
    # confirmation on the HELD-OUT seed: the chosen design, with the original design for reference
    for tag, name in (("D2_heldout", CHOSEN), ("D0_heldout", "D0 immediate reward, no prior, class_w 0.2")):
        res = run(a.classes, a.learners, a.problems, HELDOUT_SEED, design=DESIGNS[name])
        res["design_name"] = name
        json.dump(res, open(os.path.join(OUT, f"sim_results_{tag}.json"), "w"), indent=2)
        md = f"## {name} (held-out seed)\n\n" + to_markdown(res)
        open(os.path.join(OUT, f"sim_results_{tag}.md"), "w").write(md + "\n")
        figure(res, os.path.join(OUT, f"sim_results_{tag}.png"))
        print(md)


if __name__ == "__main__":
    main()
