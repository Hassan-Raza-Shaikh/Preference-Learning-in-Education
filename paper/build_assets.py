#!/usr/bin/env python3
"""Build every number, table and figure used in paper/main.tex from the repository's
result files. Nothing in the paper's tables is typed by hand.

    python paper/build_assets.py        # -> paper/generated/{numbers.tex, tab_*.tex, fig_*.pdf}

Each macro and table cell is read from a named field of a committed result file (the
source file is noted next to each block below). Rounding: values are printed to 3
decimals as stored in the result files (which themselves round to 3-4 decimals).
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paper", "generated")
os.makedirs(OUT, exist_ok=True)


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def f3(x):
    return f"{x:.3f}"


def sgn(x):
    return f"{x:+.3f}".replace("-", "$-$")


def ci(c):
    return f"[{c[0]:.2f}, {c[1]:.2f}]"


def sci(c):
    return f"[{c[0]:+.2f}, {c[1]:+.2f}]".replace("-", "$-$")


macros = {}

# ---------------------------------------------------------------- data and verification
bank = load("tutor/data/problem_bank.json")["manifest"]
macros.update(BankProblems=bank["problems"], BankTwoVar=bank["by_n_vars"]["2"], BankThreeVar=bank["by_n_vars"]["3"],
              BankStepChecked=f"{bank['stats']['step_eq_checked']:,}", BankStepUnchecked=f"{bank['stats']['step_eq_unchecked']:,}",
              BankStepFailures=len(bank["step_check_failures"]))
total_checked = total_unchecked = total_fail = 0
for name in ("multimethod", "multimethod_worked", "multimethod_worked_synth", "multimethod_worked_synth_matched"):
    sc = load(f"data/{name}/step_check.json")
    total_checked += sc["equations_checked"]
    total_unchecked += sc["equations_unchecked"]
    total_fail += len(sc["failures"])          # the list of failing solutions (empty when all pass)
macros.update(PhaseOneStepChecked=f"{total_checked:,}", PhaseOneStepUnchecked=f"{total_unchecked:,}",
              PhaseOneStepFailures=total_fail)
lk = load("data/train/split_leakage.json")      # experiments/check_split_leakage.py
macros.update(LeakTestProblems=len(lk["test_problems_identical_to_train"]), LeakTestItems=lk["test_items_identical_to_train"],
              LeakValidProblems=len(lk["test_problems_identical_to_valid_only"]),
              LeakValidItems=lk["test_items_identical_to_valid_only"], DistinctTestSystems=lk["distinct_test_systems"],
              LeakTestShare=f"{100 * lk['test_items_identical_to_train'] / lk['test_items']:.0f}")
mm = load("data/multimethod_worked/manifest.json")
macros.update(SystemsEmitted=mm["counts"]["systems_emitted"], MethodSolutions=mm["counts"]["sft_method_examples"],
              SkipUnparsed=mm["skips"]["skip_unparsed"], SkipNoUnique=mm["skips"]["skip_no_unique_solution"])
split = load("data/train/split_manifest.json")
macros.update(SplitTrain=split["systems"]["train"], SplitValid=split["systems"]["valid"], SplitTest=split["systems"]["test"],
              TestItems=split["sft_counts"]["test"])

# ---------------------------------------------------------------- Study 1 (data/train/ci_results.json)
cir = load("data/train/ci_results.json")
rows = [("base", "Base model (no training)"), ("terse SFT (600)", "SFT, terse targets, 600 it."),
        ("terse DPO", "SFT + DPO, terse targets"), ("worked SFT (600)", "SFT, worked targets, 600 it."),
        ("worked DPO", "SFT + DPO, worked targets"), ("worked SFT (1500)", "SFT, worked targets, 1500 it."),
        ("scaled-old SFT (1500)", "\\quad + original synthetic data"),
        ("scaled-matched SFT (1500)", "\\quad + distribution-matched synthetic")]
with open(os.path.join(OUT, "tab_study1.tex"), "w") as fh:
    for key, label in rows:
        g, m = cir["general"]["conditions"][key], cir["math"]["conditions"][key]
        fh.write(f"{label} & {f3(g['acc'])} & {ci(g['ci'])} & {f3(m['acc'])} & {ci(m['ci'])} \\\\\n")
        if key in ("worked DPO",):
            fh.write("\\midrule\n")
crows = [("format: worked - terse (SFT@600)", "Worked $-$ terse targets (SFT, 600 it.)"),
         ("DPO - SFT (terse)", "DPO $-$ SFT (terse)"), ("DPO - SFT (worked)", "DPO $-$ SFT (worked)"),
         ("steps: 1500 - 600 (worked)", "1500 $-$ 600 iterations (worked)"),
         ("volume, mismatched: scaled-old - worked (@1500)", "Add original synthetic (equal compute)"),
         ("volume, matched: scaled-matched - worked (@1500)", "Add matched synthetic (equal compute)"),
         ("best SFT - base", "Best SFT (1500 it.) $-$ base")]


def bold_if(c, s):
    return f"\\textbf{{{s}}}" if (c["ci"][0] > 0 or c["ci"][1] < 0) else s


with open(os.path.join(OUT, "tab_study1_contrasts.tex"), "w") as fh:
    for key, label in crows:
        g, m = cir["general"]["contrasts"][key], cir["math"]["contrasts"][key]
        fh.write(f"{label} & {bold_if(g, sgn(g['diff']))} & {sci(g['ci'])} & {bold_if(m, sgn(m['diff']))} & {sci(m['ci'])} \\\\\n")
for mdl, tag in (("general", "Gen"), ("math", "Math")):
    c = cir[mdl]["conditions"]
    macros[f"Base{tag}"] = f3(c["base"]["acc"])
    macros[f"WorkedSFT{tag}"] = f3(c["worked SFT (600)"]["acc"])
    macros[f"WorkedSFTLong{tag}"] = f3(c["worked SFT (1500)"]["acc"])
    macros[f"WorkedDPO{tag}"] = f3(c["worked DPO"]["acc"])
    k = cir[mdl]["contrasts"]
    macros[f"FormatDiff{tag}"] = sgn(k["format: worked - terse (SFT@600)"]["diff"])
    macros[f"FormatCI{tag}"] = sci(k["format: worked - terse (SFT@600)"]["ci"])
    macros[f"DpoWorkedDiff{tag}"] = sgn(k["DPO - SFT (worked)"]["diff"])
    macros[f"DpoWorkedCI{tag}"] = sci(k["DPO - SFT (worked)"]["ci"])
    macros[f"DpoTerseDiff{tag}"] = sgn(k["DPO - SFT (terse)"]["diff"])
    macros[f"BestMinusBase{tag}"] = sgn(k["best SFT - base"]["diff"])
    macros[f"BestMinusBaseCI{tag}"] = sci(k["best SFT - base"]["ci"])

# per-method base accuracy (data/train/eval_*_base.json)
mnames = [("substitution", "Substitution"), ("elimination", "Elimination"), ("graphing", "Graphing"),
          ("cramers_rule", "Cramer's rule"), ("inverse_matrix", "Matrix inverse"), ("gaussian_elimination", "Gaussian elim.")]
eg, em = load("data/train/eval_general_base.json"), load("data/train/eval_math_base.json")
with open(os.path.join(OUT, "tab_base_methods.tex"), "w") as fh:
    for k, lab in mnames:
        fh.write(f"{lab} & {eg['per_method'][k]['n']} & {f3(eg['per_method'][k]['acc'])} & {f3(em['per_method'][k]['acc'])} \\\\\n")

# DPO pair diagnostics (data/train*/dpo_pair_diagnostics.json)
dt, dw = load("data/train/dpo_pair_diagnostics.json"), load("data/train_worked/dpo_pair_diagnostics.json")
macros.update(DpoPairs=dw["pairs"], PrefixTerse=f"{dt['shared_prefix_share_of_rejected']['mean']*100:.1f}",
              PrefixWorked=f"{dw['shared_prefix_share_of_rejected']['mean']*100:.1f}",
              SurfaceRuleTerse=f"{dt['surface_rule_accuracy'][chr(101)+'nds_with_' + chr(39) + 'Solution:' + chr(39) + '_is_chosen']*100:.0f}",
              SurfaceRuleWorked=f"{dw['surface_rule_accuracy'][chr(101)+'nds_with_' + chr(39) + 'Solution:' + chr(39) + '_is_chosen']*100:.0f}",
              LongerChosenTerse=f"{dt['surface_rule_accuracy']['longer_is_chosen']:.3f}",
              LongerChosenWorked=f"{dw['surface_rule_accuracy']['longer_is_chosen']:.3f}")

# faithfulness (data/train_worked/faithfulness_validation.json)
fv = load("data/train_worked/faithfulness_validation.json")
with open(os.path.join(OUT, "tab_faithfulness.tex"), "w") as fh:
    for k, lab in mnames:
        s, w = fv["structural"][k], fv["keyword"][k]
        fh.write(f"{lab} & {s['n_gold']} & {f3(w['recall'])} & {f3(w['false_accept'])} & {f3(s['recall'])} & {f3(s['false_accept'])} \\\\\n")
macros["KeywordWorstFA"] = f3(max(v["false_accept"] for v in fv["keyword"].values()))
macros["StructWorstFA"] = f3(max(v["false_accept"] for v in fv["structural"].values()))
macros["StructMinRecall"] = f3(min(v["recall"] for v in fv["structural"].values()))

# intermediate arithmetic (data/train_worked/intermediate_stats.json)
it = load("data/train_worked/intermediate_stats.json")
macros.update(CleanReal=f3(it["real_train"]["share"]), CleanMatched=f3(it["multimethod_worked_synth_matched"]["share"]),
              CleanOrig=f3(it["multimethod_worked_synth"]["share"]))

# ---------------------------------------------------------------- Study 2 simulation
ho = load("tutor/results/sim_results_D0_heldout.json")
macros.update(SimSeed=ho["seed"], SimClasses=ho["n_classes"], SimLearners=ho["learners_per_class"], SimT=ho["problems_per_learner"])
pol_labels = [("fixed_example", "Always worked example"), ("random", "Random help type"),
              ("rule_by_mastery", "Mastery rule (fading)"), ("adaptive_outcomes", "Bandit, outcomes"),
              ("adaptive_outcomes+liking", "Bandit, outcomes + liking"), ("learner_choice", "Learner choice"),
              ("oracle", "Oracle (knows hidden state)")]
scen = list(ho["scenarios"])
with open(os.path.join(OUT, "tab_sim_heldout.tex"), "w") as fh:
    for p, lab in pol_labels:
        cells = []
        for s in scen:
            v = ho["scenarios"][s]["policies"][p]
            cells.append(f"{f3(v['mastered'])} {ci(v['mastered_ci'])}")
        best = f3(ho["scenarios"][scen[1]]["policies"][p]["best_arm_rate"])
        fh.write(f"{lab} & " + " & ".join(cells) + f" & {best} \\\\\n")
with open(os.path.join(OUT, "tab_sim_contrasts.tex"), "w") as fh:
    for key, lab in (("rule_by_mastery - fixed_example", "Mastery rule $-$ always worked example"),
                     ("adaptive_outcomes - rule_by_mastery", "Bandit $-$ mastery rule"),
                     ("learner_choice - rule_by_mastery", "Learner choice $-$ mastery rule")):
        cells = []
        for s in scen:
            c = ho["scenarios"][s]["contrasts"][key]
            cells.append(f"{bold_if(c, sgn(c['diff']))} {sci(c['ci'])}")
        fh.write(f"{lab} & " + " & ".join(cells) + " \\\\\n")
best_rates = [ho["scenarios"][s]["policies"]["adaptive_outcomes"]["best_arm_rate"] for s in scen]
macros.update(BanditBestLo=f"{min(best_rates):.2f}", BanditBestHi=f"{max(best_rates):.2f}")

# design search: D2 failure on held-out (tutor/results/sim_results_D2_heldout.json)
d2 = load("tutor/results/sim_results_D2_heldout.json")
c = d2["scenarios"][scen[0]]["contrasts"]["adaptive_outcomes - rule_by_mastery"]
macros.update(DTwoHeldoutDiff=sgn(c["diff"]), DTwoHeldoutCI=sci(c["ci"]))

# sensitivity (tutor/results/sensitivity.json)
sen = load("tutor/results/sensitivity.json")
ssum = sen["summary"]
macros.update(SensSeed=sen["protocol"]["seed"], SensCells=ssum["cells"],
              QOneBetter=ssum["Q1_rule_beats_fixed"]["better"],
              QTwoBetter=ssum["Q2_adaptive_vs_rule"]["better"], QTwoSame=ssum["Q2_adaptive_vs_rule"]["no_difference"],
              QTwoWorse=ssum["Q2_adaptive_vs_rule"]["worse"],
              QThreeBetter=ssum["Q3_choice_vs_rule"]["better"], QThreeSame=ssum["Q3_choice_vs_rule"]["no_difference"],
              QThreeWorse=ssum["Q3_choice_vs_rule"]["worse"],
              NoRevDiff=sgn(ssum["Q4_no_reversal_rule_minus_fixed"]["diff"]),
              NoRevCI=sci(ssum["Q4_no_reversal_rule_minus_fixed"]["ci"]),
              SensBestLo=f"{ssum['Q2_adaptive_vs_rule']['adaptive_picks_best_range'][0]:.2f}",
              SensBestHi=f"{ssum['Q2_adaptive_vs_rule']['adaptive_picks_best_range'][1]:.2f}")
tabs = ssum["Q4_other_tables_rule_minus_fixed"]
pert = [v["diff"] for k, v in tabs.items() if k.startswith("perturbed")]
macros.update(WeakRevDiff=sgn(tabs["weak reversal"]["diff"]), PertLo=sgn(min(pert)), PertHi=sgn(max(pert)))
rep = sen["replication_fresh_seed"]
with open(os.path.join(OUT, "tab_replication.tex"), "w") as fh:
    for cell, v in rep.items():
        sg, rho, T = [x.split("=")[1] for x in cell.split(", ")]
        def g(k):
            c = v[k]
            mark = "$^{+}$" if c["sig"] == "+" else ("$^{-}$" if c["sig"] == "-" else "")
            return sgn(c["diff"]) + mark
        rho_tex = rho.replace("-", "$-$")
        fh.write(f"{sg} & {rho_tex} & {T} & {g('rule_by_mastery - fixed_example')} & {g('adaptive_outcomes - rule_by_mastery')} & "
                 f"{g('random - rule_by_mastery')} & {g('learner_choice - rule_by_mastery')} \\\\\n")
expl = sen["exploratory_random_check"]
macros.update(RandRuleGridThirty=sgn(expl["sigma=1.0|T=30"]["random - rule_by_mastery"]["diff"]),
              RandRuleGridSixty=sgn(expl["sigma=1.0|T=60"]["random - rule_by_mastery"]["diff"]))
rr = {k: v["random - rule_by_mastery"]["diff"] for k, v in rep.items() if k.startswith("sigma=1.0, rho=0.5")}
macros.update(RandRuleRepThirty=sgn(rr["sigma=1.0, rho=0.5, T=30"]), RandRuleRepSixty=sgn(rr["sigma=1.0, rho=0.5, T=60"]))
ar = {k: v["adaptive_outcomes - rule_by_mastery"]["diff"] for k, v in rep.items() if k.startswith("sigma=1.0, rho=0.5")}
macros.update(BanditRuleRepThirty=sgn(ar["sigma=1.0, rho=0.5, T=30"]), BanditRuleRepSixty=sgn(ar["sigma=1.0, rho=0.5, T=60"]))
rf = [v["rule_by_mastery - fixed_example"]["diff"] for v in rep.values()]
macros.update(RepRuleFixedLo=sgn(min(rf)), RepRuleFixedHi=sgn(max(rf)))
ch = [v["learner_choice - rule_by_mastery"]["diff"] for k, v in rep.items() if "rho=0.9" in k and not k.startswith("sigma=0.0")]
macros.update(RepChoiceLo=sgn(min(ch)), RepChoiceHi=sgn(max(ch)))

# pre-registered rule + switch (tutor/results/switch_rule.json)
sw = load("tutor/results/switch_rule.json")
g0 = sw["grid"]
macros.update(SwitchSeed=sw["protocol"]["seed"],
              SwitchSimFifteen=sgn(g0["sigma=0.0, T=15"]["switch_minus_rule"]["diff"]),
              SwitchSimThirty=sgn(g0["sigma=0.0, T=30"]["switch_minus_rule"]["diff"]),
              SwitchDiffThirty=sgn(g0["sigma=1.0, T=30"]["switch_minus_rule"]["diff"]),
              SwitchDiffSixty=sgn(g0["sigma=1.0, T=60"]["switch_minus_rule"]["diff"]),
              SwitchPassed="passed" if sw["criteria"]["passed"] else "failed")

with open(os.path.join(OUT, "numbers.tex"), "w") as fh:
    fh.write("% Generated by paper/build_assets.py from committed result files. Do not edit.\n")
    for k, v in macros.items():
        fh.write(f"\\newcommand{{\\num{k}}}{{{v}}}\n")

# ---------------------------------------------------------------- figures (print, light surface)
INK, MUTED, GRID = "#1d1d1b", "#6b6b66", "#e4e2dc"
BLUE, ORANGE = "#2a78d6", "#eb6834"          # categorical slots 1-2 of the reference palette
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})

# Figure: Study 1 accuracy with 95% CIs
fig, ax = plt.subplots(figsize=(6.6, 3.1))
labels = ["Base", "Terse\nSFT", "Terse\nDPO", "Worked\nSFT", "Worked\nDPO", "Worked SFT\n1500 it.", "+orig.\nsynth.", "+matched\nsynth."]
keys = [r[0] for r in rows]
for off, mdl, col, name in ((-0.13, "general", BLUE, "Qwen2.5-1.5B-Instruct (general)"),
                            (0.13, "math", ORANGE, "Qwen2.5-Math-1.5B-Instruct (math)")):
    ys = [cir[mdl]["conditions"][k]["acc"] for k in keys]
    lo = [y - cir[mdl]["conditions"][k]["ci"][0] for y, k in zip(ys, keys)]
    hi = [cir[mdl]["conditions"][k]["ci"][1] - y for y, k in zip(ys, keys)]
    xs = [i + off for i in range(len(keys))]
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", ms=5, color=col, ecolor=col, elinewidth=1.2, capsize=0, label=name)
ax.axhline(cir["general"]["conditions"]["base"]["acc"], color=GRID, lw=1, zorder=0)
ax.axvline(4.5, color=GRID, lw=1, ls=":", zorder=0)
ax.set_xticks(range(len(keys)), labels, fontsize=7.5)
ax.set_ylabel("exact answer accuracy (126 test items)")
ax.set_ylim(-0.02, 0.6)
ax.yaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
ax.text(4.55, 0.565, "1500 iterations \u2192", fontsize=7, color=MUTED)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_study1.pdf"))
plt.close(fig)

# Figure: simulation, held-out seed, dot plot with CIs per scenario (small multiples)
titles = {scen[0]: "A: no differences", scen[1]: "B: honest preferences", scen[2]: "C: misleading preferences"}
fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.6), sharey=True)
for ax, s in zip(axes, scen):
    for i, (p, lab) in enumerate(pol_labels):
        v = ho["scenarios"][s]["policies"][p]
        col = MUTED if p == "oracle" else INK
        ax.errorbar(v["mastered"], i, xerr=[[v["mastered"] - v["mastered_ci"][0]], [v["mastered_ci"][1] - v["mastered"]]],
                    fmt="o", ms=4.5, color=col, ecolor=col, elinewidth=1.1, capsize=0)
    ax.set_title(titles[s], fontsize=8, color=INK)
    ax.set_xlim(0.5, 0.92)
    ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("share of skills mastered", fontsize=7.5)
axes[0].set_yticks(range(len(pol_labels)), [l for _, l in pol_labels], fontsize=7.5)
axes[0].invert_yaxis()
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig_sim_heldout.pdf"))
plt.close(fig)

# Figure: sensitivity heatmap, learner choice - rule (grid seed), T = 30 and 60
SIG, RHO = sen["protocol"]["sigmas"], sen["protocol"]["rhos"]
cmap = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
key = "learner_choice - rule_by_mastery"
vals = [sen["grid"][k]["contrasts"][key]["diff"] for k in sen["grid"]]
lim = max(abs(v) for v in vals)
fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.7), constrained_layout=True)
for ax, T in zip(axes, (30, 60)):
    M = [[sen["grid"][f"sigma={s}|rho={r}|T={T}"]["contrasts"][key] for r in RHO] for s in SIG]
    im = ax.imshow([[c["diff"] for c in row] for row in M], cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim), origin="lower", aspect="auto")
    for a, row in enumerate(M):
        for b, c in enumerate(row):
            ax.text(b, a, f"{c['diff']:+.2f}" + ("*" if c["sig"] != "0" else ""), ha="center", va="center", fontsize=7.5,
                    color=INK, fontweight="bold" if c["sig"] != "0" else "normal")
    ax.set_xticks(range(len(RHO)), [str(r) for r in RHO])
    ax.set_yticks(range(len(SIG)), [str(s) for s in SIG])
    ax.set_xlabel(r"$\rho$: preference tracks efficacy", fontsize=7.5)
    ax.set_title(f"Learner choice $-$ mastery rule, T = {T}", fontsize=8, color=INK)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
axes[0].set_ylabel(r"$\sigma$: individual differences", fontsize=7.5)
cb = fig.colorbar(im, ax=axes, shrink=0.85)
cb.set_label("difference in share of skills mastered", fontsize=7)
cb.outline.set_visible(False)
fig.savefig(os.path.join(OUT, "fig_sensitivity.pdf"))
plt.close(fig)

print(f"wrote {len(macros)} macros and tables/figures to {os.path.relpath(OUT, ROOT)}")
