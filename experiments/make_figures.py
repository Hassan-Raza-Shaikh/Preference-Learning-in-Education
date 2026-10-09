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


CI_ORDER = [  # (label in ci_results.json, x tick label)
    ("base", "Base"),
    ("terse SFT (600)", "Terse\nSFT"),
    ("terse DPO", "Terse\nDPO"),
    ("worked SFT (600)", "Worked\nSFT"),
    ("worked DPO", "Worked\nDPO"),
    ("worked SFT (1500)", "Worked SFT\n1500 it"),
    ("scaled-old SFT (1500)", "+synthetic\n(mismatched)"),
    ("scaled-matched SFT (1500)", "+synthetic\n(matched)"),
]


def fig_accuracy():
    """Accuracy with 95% cluster-bootstrap CIs (from analyze_ci.py)."""
    import numpy as np
    ci = json.load(open(os.path.join(D, "ci_results.json")))
    labels = [lab for lab, _ in CI_ORDER if lab in ci["general"]["conditions"] and lab in ci["math"]["conditions"]]
    ticks = [t for lab, t in CI_ORDER if lab in labels]
    x = np.arange(len(labels)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    for off, m, color, name in [(-w/2, "general", BLUE, "general (Qwen2.5-1.5B-Instruct)"),
                                (w/2, "math", ORANGE, "math (Qwen2.5-Math-1.5B-Instruct)")]:
        c = ci[m]["conditions"]
        vals = np.array([c[l]["acc"] for l in labels])
        lo = vals - np.array([c[l]["ci"][0] for l in labels])
        hi = np.array([c[l]["ci"][1] for l in labels]) - vals
        bars = ax.bar(x + off, vals, w, label=name, color=color,
                      yerr=[lo, hi], error_kw={"elinewidth": 0.8, "capsize": 2, "ecolor": "#333"})
        for r, v, h in zip(bars, vals, hi):
            if v >= 0.045:   # label inside the bar
                ax.annotate(f"{v:.2f}", (r.get_x() + r.get_width()/2, 0.005), ha="center",
                            va="bottom", fontsize=6.5, color="white", fontweight="bold")
            else:            # bar too short: dark label above the error bar
                ax.annotate(f"{v:.2f}", (r.get_x() + r.get_width()/2, v + h + 0.008), ha="center",
                            va="bottom", fontsize=6.5, color="#333")
    base = (ci["general"]["conditions"]["base"]["acc"] + ci["math"]["conditions"]["base"]["acc"]) / 2
    ax.axhline(base, ls="--", lw=1, color="#888")
    ax.axvline(4.5, ls=":", lw=0.8, color="#bbb")
    ax.text(4.55, 0.555, "1500-iteration runs →", ha="left", va="top", fontsize=7.5, color="#777")
    ax.set_xticks(x); ax.set_xticklabels(ticks, fontsize=8)
    ax.set_ylabel("answer accuracy (held-out)"); ax.set_ylim(0, 0.56)
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.13))
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "accuracy.pdf")); fig.savefig(os.path.join(FIG, "accuracy.png"))
    plt.close(fig); print("wrote accuracy figure (with 95% CIs)")


def parse_run_log(path):
    """Split a run_all log into {model_tag: (train[(it,loss)], val[(it,loss)])}."""
    import re
    out, cur = {}, None
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.search(r"MODEL: ([a-z0-9_]+)", line)
        if m:
            cur = m.group(1); out[cur] = ([], []); continue
        if cur is None:
            continue
        v = re.search(r"Iter (\d+): Val loss ([0-9.]+)", line)
        t = re.search(r"Iter (\d+): loss ([0-9.]+)", line)
        if v:
            out[cur][1].append((int(v.group(1)), float(v.group(2))))
        elif t:
            out[cur][0].append((int(t.group(1)), float(t.group(2))))
    return out


def fig_loss_1500():
    """Train/val loss for the 1500-iteration runs: 114 real systems vs +matched synthetic."""
    ctl = os.path.join(D, "logs", "worked1500.log")
    mat = os.path.join(D, "logs", "scaledmatched.log")
    if not (os.path.exists(ctl) and os.path.exists(mat)):
        print("1500-iter logs missing; skipping"); return
    runs = {**parse_run_log(ctl), **parse_run_log(mat)}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, m, color in zip(axes, ("general", "math"), (BLUE, ORANGE)):
        for tag, lab, c in [(f"worked1500_{m}", "real only (114 sys)", "#888"),
                            (f"scaledmatched_{m}", "+ matched synthetic", color)]:
            if tag not in runs or not runs[tag][0]:
                continue
            tr, va = runs[tag]
            ax.plot(*zip(*tr), color=c, lw=1.3, label=f"{lab} train")
            if va:
                ax.plot(*zip(*va), color=c, lw=1.1, ls="--", marker="o", ms=2.5, label=f"{lab} val")
        ax.set_title(f"{m} model", fontsize=10); ax.set_xlabel("iteration")
        ax.legend(frameon=False, fontsize=7)
    axes[0].set_ylabel("SFT loss")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "loss_1500.pdf")); fig.savefig(os.path.join(FIG, "loss_1500.png"))
    plt.close(fig); print("wrote 1500-iter loss figure")


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
    fig_loss_1500()
