"""Sensitivity analysis of the simulated-learner results (for paper P2).

The M4 results (tutor/results/sim_results_D0_heldout.md) used three hand-picked scenarios.
This asks whether the conclusions survive when the simulator's assumptions change.

PROTOCOL, fixed before running (2026-11-04):
  Seed 20271201: new, used by no earlier run. Grid and questions are fixed in this file.
  Algorithm: the original design D0 (the app's `adaptive` mode). 20 classes x 25 learners per cell.

  Q1  Does "rule beats always-worked-example" hold across the whole grid?
  Q2  Does the adaptive bandit ever beat the rule? (expected: only, if at all, with large
      individual differences sigma and a long horizon T)
  Q3  How strongly must stated preferences track efficacy (rho) before learner choice beats
      the rule, and does that depend on sigma or T?
  Q4  CAN-FAIL CHECK: is the simulator rigged toward the rule? With NO expertise reversal
      (worked example best at every level), the rule must LOSE to always-worked-example.
      Also: random perturbations of the learning table.

Grid: sigma (individual differences) x rho (preference-efficacy match) x T (problems per
learner). Contrasts are paired by class, with a 95% bootstrap CI over classes.

    python -m tutor.sensitivity          # -> tutor/results/sensitivity.{json,md}, figures
"""
from __future__ import annotations

import itertools
import json
import math
import os
import random
import time

from .content import ARMS
from .simulate import BASE, OUT, boot_ci, run_class

SEED = 20271201
N_CLASSES = 20
SIGMAS = [0.0, 0.3, 0.6, 1.0]
RHOS = [-0.5, 0.0, 0.5, 0.9]
HORIZONS = [15, 30, 60]
POLICIES = ["fixed_example", "rule_by_mastery", "adaptive_outcomes", "learner_choice", "oracle"]
CONTRASTS = [("rule_by_mastery", "fixed_example"), ("adaptive_outcomes", "rule_by_mastery"),
             ("learner_choice", "rule_by_mastery"), ("oracle", "rule_by_mastery")]

BASE_VARIANTS = {
    "reversal (default)": BASE,
    "weak reversal": {0: BASE[0], 1: {"example": 0.18, "faded": 0.22, "outline": 0.20, "none": 0.15}},
    "no reversal": {0: BASE[0], 1: dict(BASE[0])},        # worked example best at every level
}
N_PERTURB, PERTURB_SD = 5, 0.4                           # random log-normal perturbations of BASE


def perturbed_tables():
    rng = random.Random(SEED + 99)
    return {f"perturbed #{i + 1}": {lv: {a: min(0.9, BASE[lv][a] * math.exp(rng.gauss(0, PERTURB_SD))) for a in ARMS}
                                    for lv in BASE} for i in range(N_PERTURB)}


def cell(scen, T, n_classes=N_CLASSES, seed=SEED):
    per = {p: [run_class(p, scen, seed + c, 25, T) for c in range(n_classes)] for p in POLICIES}
    out = {"mastered": {p: round(sum(r["mastered"] for r in rs) / n_classes, 4) for p, rs in per.items()},
           "adaptive_picks_best": round(sum(r["best_arm_rate"] for r in per["adaptive_outcomes"]) / n_classes, 3),
           "contrasts": {}}
    for a, b in CONTRASTS:
        d = [x["mastered"] - y["mastered"] for x, y in zip(per[a], per[b])]
        ci = boot_ci(d)
        out["contrasts"][f"{a} - {b}"] = {"diff": round(sum(d) / len(d), 4), "ci": [round(c, 4) for c in ci],
                                         "sig": "+" if ci[0] > 0 else ("-" if ci[1] < 0 else "0")}
    return out


def run_grid():
    grid = {}
    for sigma, rho, T in itertools.product(SIGMAS, RHOS, HORIZONS):
        grid[f"sigma={sigma}|rho={rho}|T={T}"] = {"sigma": sigma, "rho": rho, "T": T,
                                                  **cell({"sigma": sigma, "rho": rho}, T)}
    return grid


def run_base_variants():
    out = {}
    for name, table in {**BASE_VARIANTS, **perturbed_tables()}.items():
        out[name] = {"table": {str(k): v for k, v in table.items()},
                     **cell({"sigma": 0.6, "rho": 0.8, "base": table}, 30)}
    return out


def exploratory_random_check():
    """EXPLORATORY (added after seeing Q2, not part of the fixed protocol).

    Q2 found the bandit beats the rule only at sigma = 1.0, while still picking the best help
    type at chance level. Does it win by personalising, or just by varying the help? Compare
    it with RANDOM help in those cells.
    """
    out = {}
    for T in (30, 60):
        sc = {"sigma": 1.0, "rho": 0.0}             # rho does not affect these three policies
        per = {p: [run_class(p, sc, SEED + c, 25, T) for c in range(N_CLASSES)]
               for p in ("random", "rule_by_mastery", "adaptive_outcomes")}
        row = {}
        for a, b in (("adaptive_outcomes", "random"), ("random", "rule_by_mastery")):
            d = [x["mastered"] - y["mastered"] for x, y in zip(per[a], per[b])]
            ci = boot_ci(d)
            row[f"{a} - {b}"] = {"diff": round(sum(d) / len(d), 4), "ci": [round(c, 4) for c in ci]}
        out[f"sigma=1.0|T={T}"] = row
    return out


REPLICATION_SEED = 20280101   # the fresh seed of tutor/switch_rule.py


def replicate_on_fresh_seed():
    """Re-test the headline claims on a FRESH seed (added 2026-11-04 after the exploratory
    'random beats the rule at sigma 1.0' result failed to replicate).

    All cells of the grid above share one set of simulated classes (one seed), so they are
    not independent replications; this re-runs the key cells with new classes.
    """
    pols = ["fixed_example", "random", "rule_by_mastery", "adaptive_outcomes", "learner_choice"]
    pairs = [("rule_by_mastery", "fixed_example"), ("adaptive_outcomes", "rule_by_mastery"),
             ("random", "rule_by_mastery"), ("learner_choice", "rule_by_mastery")]
    cells = [(sg, rho, T) for T in (30, 60) for sg, rho in
             ((0.0, 0.9), (0.6, -0.5), (0.6, 0.9), (1.0, -0.5), (1.0, 0.5), (1.0, 0.9))]
    out = {}
    for sg, rho, T in cells:
        per = {p: [run_class(p, {"sigma": sg, "rho": rho}, REPLICATION_SEED + c, 25, T) for c in range(N_CLASSES)]
               for p in pols}
        row = {}
        for a, b in pairs:
            d = [x["mastered"] - y["mastered"] for x, y in zip(per[a], per[b])]
            ci = boot_ci(d)
            row[f"{a} - {b}"] = {"diff": round(sum(d) / len(d), 4), "ci": [round(c, 4) for c in ci],
                                 "sig": "+" if ci[0] > 0 else ("-" if ci[1] < 0 else "0")}
        out[f"sigma={sg}, rho={rho}, T={T}"] = row
    return out


# --------------------------------------------------------------------------- reporting
def summarise(grid, variants):
    def count(key, sign):
        return sum(c["contrasts"][key]["sig"] == sign for c in grid.values())
    n = len(grid)
    k1, k2, k3 = ("rule_by_mastery - fixed_example", "adaptive_outcomes - rule_by_mastery",
                  "learner_choice - rule_by_mastery")
    adapt_wins = [k for k, c in grid.items() if c["contrasts"][k2]["sig"] == "+"]
    choice_wins = sorted({(c["sigma"], c["rho"]) for c in grid.values() if c["contrasts"][k3]["sig"] == "+"})
    no_rev = variants["no reversal"]["contrasts"][k1]
    return {
        "cells": n,
        "Q1_rule_beats_fixed": {"better": count(k1, "+"), "no_difference": count(k1, "0"), "worse": count(k1, "-")},
        "Q2_adaptive_vs_rule": {"better": count(k2, "+"), "no_difference": count(k2, "0"), "worse": count(k2, "-"),
                                "cells_where_adaptive_better": adapt_wins,
                                "adaptive_picks_best_range": [min(c["adaptive_picks_best"] for c in grid.values()),
                                                              max(c["adaptive_picks_best"] for c in grid.values())]},
        "Q3_choice_vs_rule": {"better": count(k3, "+"), "no_difference": count(k3, "0"), "worse": count(k3, "-"),
                              "(sigma, rho) where choice better at some T": choice_wins},
        "Q4_no_reversal_rule_minus_fixed": no_rev,
        "Q4_check_passed": no_rev["sig"] == "-",
        "Q4_other_tables_rule_minus_fixed": {k: v["contrasts"][k1] for k, v in variants.items()},
    }


def to_markdown(res):
    s = res["summary"]
    L = [f"# Simulation sensitivity analysis\n",
         f"Seed {SEED} (new), {N_CLASSES} classes x 25 learners per cell, original adaptive design (D0). "
         "Metric: share of the 3 skills truly mastered. Contrasts are paired by class; 95% bootstrap CI. "
         "`+` / `-` = CI excludes 0; `0` = it does not. **Simulated learners: this shows how the conclusions "
         "depend on the simulator's assumptions, not how real pupils learn.**\n",
         "## Summary\n",
         f"- **Q1, rule vs always-worked-example** ({s['cells']} grid cells): better in "
         f"{s['Q1_rule_beats_fixed']['better']}, no difference in {s['Q1_rule_beats_fixed']['no_difference']}, "
         f"worse in {s['Q1_rule_beats_fixed']['worse']}.",
         f"- **Q2, adaptive bandit vs rule:** better in {s['Q2_adaptive_vs_rule']['better']}, no difference in "
         f"{s['Q2_adaptive_vs_rule']['no_difference']}, worse in {s['Q2_adaptive_vs_rule']['worse']}. "
         f"It picks the learner's best help type in {s['Q2_adaptive_vs_rule']['adaptive_picks_best_range'][0]:.2f}–"
         f"{s['Q2_adaptive_vs_rule']['adaptive_picks_best_range'][1]:.2f} of cases (chance 0.25).",
         f"- **Q3, learner choice vs rule:** better in {s['Q3_choice_vs_rule']['better']}, no difference in "
         f"{s['Q3_choice_vs_rule']['no_difference']}, worse in {s['Q3_choice_vs_rule']['worse']}.",
         f"- **Q4, can-fail check** (no expertise reversal, rule − fixed): "
         f"{s['Q4_no_reversal_rule_minus_fixed']['diff']:+.3f} "
         f"[{s['Q4_no_reversal_rule_minus_fixed']['ci'][0]:+.3f}, {s['Q4_no_reversal_rule_minus_fixed']['ci'][1]:+.3f}]: "
         f"**{'PASSED' if s['Q4_check_passed'] else 'FAILED'}** (the rule should lose here).",
         "- **Read with the replication section at the end.** All grid cells share one set of simulated classes. "
         "On a fresh seed, Q1 and the learner-choice pattern replicated, but the bandit's gains at sigma 1.0 and "
         "the exploratory 'random help beats the rule' result did **not**.\n"]
    for key, title in (("learner_choice - rule_by_mastery", "Learner choice − rule"),
                       ("adaptive_outcomes - rule_by_mastery", "Adaptive bandit − rule"),
                       ("rule_by_mastery - fixed_example", "Rule − always worked example")):
        L.append(f"## {title}\n")
        for T in HORIZONS:
            L += [f"**T = {T} problems per learner** (rows sigma, columns rho)\n",
                  "| sigma \\ rho | " + " | ".join(str(r) for r in RHOS) + " |",
                  "|---|" + "---|" * len(RHOS)]
            for sg in SIGMAS:
                row = []
                for rho in RHOS:
                    c = res["grid"][f"sigma={sg}|rho={rho}|T={T}"]["contrasts"][key]
                    row.append(f"{c['diff']:+.3f} {c['sig']}")
                L.append(f"| {sg} | " + " | ".join(row) + " |")
            L.append("")
    L += ["## Q4: different learning tables (sigma 0.6, rho 0.8, T 30)\n",
          "| table | rule − fixed | learner choice − rule | adaptive − rule |", "|---|---|---|---|"]
    for name, v in res["base_variants"].items():
        c = v["contrasts"]
        f = lambda k: f"{c[k]['diff']:+.3f} [{c[k]['ci'][0]:+.3f}, {c[k]['ci'][1]:+.3f}]"
        L.append(f"| {name} | {f('rule_by_mastery - fixed_example')} | {f('learner_choice - rule_by_mastery')} | "
                 f"{f('adaptive_outcomes - rule_by_mastery')} |")
    L += ["", "## Exploratory follow-up (added after seeing Q2; not part of the fixed protocol)\n",
          "Where the bandit beat the rule (sigma 1.0), is it personalising or just varying the help? "
          "Comparison with RANDOM help:\n", "| cell | adaptive − random | random − rule |", "|---|---|---|"]
    for k, v in res["exploratory_random_check"].items():
        a, b = v["adaptive_outcomes - random"], v["random - rule_by_mastery"]
        L.append(f"| {k.replace('|', ', ')} | {a['diff']:+.3f} [{a['ci'][0]:+.3f}, {a['ci'][1]:+.3f}] | "
                 f"{b['diff']:+.3f} [{b['ci'][0]:+.3f}, {b['ci'][1]:+.3f}] |")
    if "replication_fresh_seed" in res:
        L += ["", f"## Replication on a fresh seed ({REPLICATION_SEED})\n",
              "The grid's cells share one set of simulated classes, so they are not independent. These key cells "
              "were re-run with new classes. `+`/`-` = 95% CI excludes 0.\n",
              "| cell | rule − fixed | adaptive − rule | random − rule | choice − rule |", "|---|---|---|---|---|"]
        for k, v in res["replication_fresh_seed"].items():
            g = lambda key: f"{v[key]['diff']:+.3f} {v[key]['sig']}"
            L.append(f"| {k} | {g('rule_by_mastery - fixed_example')} | {g('adaptive_outcomes - rule_by_mastery')} | "
                     f"{g('random - rule_by_mastery')} | {g('learner_choice - rule_by_mastery')} |")
    return "\n".join(L) + "\n"


def figures(res, path):
    """Diverging heatmaps (blue = first policy better, red = worse, gray = no difference)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#256abf"])
    ink, muted = "#1d1d1b", "#6b6b66"
    rows = [("learner_choice - rule_by_mastery", "Learner choice − rule"),
            ("adaptive_outcomes - rule_by_mastery", "Adaptive bandit − rule")]
    vals = [res["grid"][k]["contrasts"][key]["diff"] for k in res["grid"] for key, _ in rows]
    lim = max(abs(v) for v in vals)
    fig, axes = plt.subplots(len(rows), len(HORIZONS), figsize=(11, 6.6), constrained_layout=True)
    for i, (key, title) in enumerate(rows):
        for j, T in enumerate(HORIZONS):
            ax = axes[i][j]
            M = [[res["grid"][f"sigma={sg}|rho={rho}|T={T}"]["contrasts"][key] for rho in RHOS] for sg in SIGMAS]
            im = ax.imshow([[c["diff"] for c in r] for r in M], cmap=cmap,
                           norm=TwoSlopeNorm(vcenter=0, vmin=-lim, vmax=lim), origin="lower", aspect="auto")
            for a, r in enumerate(M):
                for b, c in enumerate(r):
                    ax.text(b, a, f"{c['diff']:+.2f}" + ("" if c["sig"] == "0" else "*"), ha="center", va="center",
                            fontsize=8.5, color=ink, fontweight="bold" if c["sig"] != "0" else "normal")
            ax.set_xticks(range(len(RHOS)), [str(r) for r in RHOS], fontsize=8, color=muted)
            ax.set_yticks(range(len(SIGMAS)), [str(s) for s in SIGMAS], fontsize=8, color=muted)
            ax.set_title(f"{title}, T = {T}", fontsize=9.5, color=ink)
            if i == len(rows) - 1:
                ax.set_xlabel("rho: how well stated preference tracks what helps", fontsize=8, color=muted)
            if j == 0:
                ax.set_ylabel("sigma: individual differences", fontsize=8, color=muted)
            for sp in ax.spines.values():
                sp.set_visible(False)
            ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=axes, shrink=0.6)
    cb.set_label("difference in share of skills mastered\n(blue: first policy better; * = 95% CI excludes 0)",
                 fontsize=8, color=muted)
    cb.outline.set_visible(False)
    fig.suptitle("Sensitivity of the simulated-learner results (simulated pupils, not real ones)", fontsize=10.5,
                 color=ink)
    fig.savefig(path, dpi=150, facecolor="#fcfcfb")


def main():
    t0 = time.time()
    grid = run_grid()
    variants = run_base_variants()
    res = {"protocol": {"seed": SEED, "classes_per_cell": N_CLASSES, "learners_per_class": 25,
                        "sigmas": SIGMAS, "rhos": RHOS, "horizons": HORIZONS, "design": "D0",
                        "perturbation_sd": PERTURB_SD, "n_perturbed_tables": N_PERTURB},
           "grid": grid, "base_variants": variants}
    res["summary"] = summarise(grid, variants)
    res["exploratory_random_check"] = exploratory_random_check()
    res["replication_fresh_seed"] = replicate_on_fresh_seed()
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "sensitivity.json"), "w"), indent=1)
    md = to_markdown(res)
    open(os.path.join(OUT, "sensitivity.md"), "w").write(md)
    figures(res, os.path.join(OUT, "sensitivity.png"))
    print(md.split("## Learner choice")[0])
    print(json.dumps(res["summary"], indent=1)[:3000])
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
