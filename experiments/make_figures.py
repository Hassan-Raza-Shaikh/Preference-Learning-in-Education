#!/usr/bin/env python3
"""Generate publication figures for the supervisor PDF (matplotlib -> PDF/PNG)."""
import json
import os
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "train")
FIG = os.path.join(ROOT, "report_assets")
os.makedirs(FIG, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444", "axes.labelcolor": "#222",
    "xtick.color": "#444", "ytick.color": "#444", "figure.dpi": 150,
})
BLUE, ORANGE = "#3A5BA0", "#C56A3A"


def acc(f):
    p = os.path.join(D, f)
    return json.load(open(p))["answer_accuracy"] if os.path.exists(p) else None


def fig_accuracy():
    conds = ["Base", "Terse\nSFT", "Terse\nDPO", "Worked\nSFT", "Worked\nDPO", "Scaled\nSFT"]
    gen = [acc("eval_general_base.json"), acc("eval_general_sft.json"), acc("eval_general_dpo.json"),
           acc("eval_worked_general_sft.json"), acc("eval_worked_general_dpo.json"), acc("eval_scaled_general_sft.json")]
    mat = [acc("eval_math_base.json"), acc("eval_math_sft.json"), acc("eval_math_dpo.json"),
           acc("eval_worked_math_sft.json"), acc("eval_worked_math_dpo.json"), acc("eval_scaled_math_sft.json")]
    import numpy as np
    x = np.arange(len(conds)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    b1 = ax.bar(x - w/2, gen, w, label="general (Qwen2.5-1.5B-Instruct)", color=BLUE)
    b2 = ax.bar(x + w/2, mat, w, label="math (Qwen2.5-Math-1.5B-Instruct)", color=ORANGE)
    ax.axhline(0.385, ls="--", lw=1, color="#888")
    ax.text(4.0, 0.40, "base ≈ 0.38", ha="center", va="bottom", fontsize=8, color="#777")
    for bars in (b1, b2):
        for r in bars:
            ax.annotate(f"{r.get_height():.2f}", (r.get_x()+r.get_width()/2, r.get_height()),
                        ha="center", va="bottom", fontsize=7.5, color="#333")
    ax.set_xticks(x); ax.set_xticklabels(conds)
    ax.set_ylabel("answer accuracy (held-out)"); ax.set_ylim(0, 0.45)
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.14))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "accuracy.pdf")); fig.savefig(os.path.join(FIG, "accuracy.png"))
    plt.close(fig); print("wrote accuracy figure")


def load_csv(name):
    p = os.path.join(D, "loss", f"{name}.csv")
    if not os.path.exists(p):
        return None
    tr, va = [], []
    for row in csv.DictReader(open(p)):
        (tr if row["kind"] == "train" else va).append((int(row["iter"]), float(row["loss"])))
    return sorted(tr), sorted(va)


def fig_loss():
    runs = {"general": ("terse_general", "worked_general"), "math": ("terse_math", "worked_math")}
    if not all(load_csv(n) for pair in runs.values() for n in pair):
        print("loss CSVs not ready; skipping loss figure")
        return False
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, (model, (terse, worked)) in zip(axes, runs.items()):
        for name, color, lab in [(terse, "#888", "terse"), (worked, BLUE if model=="general" else ORANGE, "worked")]:
            tr, va = load_csv(name)
            xs, ys = zip(*tr); ax.plot(xs, ys, color=color, lw=1.4, label=f"{lab} train")
            if va:
                xv, yv = zip(*va); ax.plot(xv, yv, color=color, lw=1.2, ls="--", marker="o", ms=2.5, label=f"{lab} val")
        ax.set_title(f"{model} model", fontsize=10)
        ax.set_xlabel("iteration"); ax.legend(frameon=False, fontsize=7.5)
    axes[0].set_ylabel("SFT loss")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "loss.pdf")); fig.savefig(os.path.join(FIG, "loss.png"))
    plt.close(fig); print("wrote loss figure"); return True


if __name__ == "__main__":
    fig_accuracy()
    fig_loss()
