"""Analyse a pilot from the tutor's own records (supports milestone M5).

    python -m tutor.analyze_study --data-dir runs --class-id demo

Reads <data_dir>/<class_id>/state.json and events.jsonl and reports:
  RQ1/RQ2  pre-test, post-test and gain per condition (mean, n), using only learners who
           completed both tests; plus a gain contrast vs the first study arm with a 95%
           bootstrap CI (resampling learners). PILOT numbers: descriptive, not confirmatory.
  RQ3      stated preference vs outcome: for each learner, is the help type they chose or
           rated highest also the one after which they solved most problems?
  Usage    problems attempted, time on task, help-type usage per condition.

No personal data is involved: learners are pseudonymous codes.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter, defaultdict


def load(data_dir, class_id):
    d = os.path.join(data_dir, class_id)
    state = json.load(open(os.path.join(d, "state.json")))
    events = [json.loads(l) for l in open(os.path.join(d, "events.jsonl"))]
    return state, events


def score(ls, form):
    a = ls.get("assessment", {}).get(form, {})
    return (sum(a.values()) / len(a)) if a else None


def boot_diff(xs, ys, B=5000, seed=1):
    rng = random.Random(seed)
    m = lambda v: sum(v) / len(v)
    ds = sorted(m([rng.choice(xs) for _ in xs]) - m([rng.choice(ys) for _ in ys]) for _ in range(B))
    return [round(ds[int(0.025 * B)], 3), round(ds[int(0.975 * B) - 1], 3)]


def analyse(state, events, default_mode):
    learners = state["learners"]
    by_cond = defaultdict(list)
    for lid, ls in learners.items():
        cond = ls.get("study_arm") or default_mode
        pre, post = score(ls, "pre"), score(ls, "post")
        if pre is not None and post is not None:
            by_cond[cond].append({"learner": lid, "pre": pre, "post": post, "gain": post - pre})
    rq12 = {c: {"n": len(v), "pre": round(sum(r["pre"] for r in v) / len(v), 3),
                "post": round(sum(r["post"] for r in v) / len(v), 3),
                "gain": round(sum(r["gain"] for r in v) / len(v), 3)} for c, v in by_cond.items() if v}
    conds = list(rq12)
    contrasts = {}
    if len(conds) >= 2:
        ref = conds[0]
        for c in conds[1:]:
            g1 = [r["gain"] for r in by_cond[c]]
            g0 = [r["gain"] for r in by_cond[ref]]
            if len(g1) >= 2 and len(g0) >= 2:
                contrasts[f"{c} - {ref}"] = {"diff": round(sum(g1) / len(g1) - sum(g0) / len(g0), 3),
                                             "ci95": boot_diff(g1, g0)}
    # RQ3: liked-most vs works-best, per learner (all mastery bands pooled, >= 3 observations each)
    agree = total = 0
    for ls in learners.values():
        eff, lik = Counter(), Counter()
        n_eff, n_lik = Counter(), Counter()
        for band in ls["efficacy"]:
            for arm, (s, f) in ls["efficacy"][band].items():
                eff[arm] += s
                n_eff[arm] += s + f
            for arm, (s, f) in ls["liking"][band].items():
                lik[arm] += s
                n_lik[arm] += s + f
        e = {a: eff[a] / n_eff[a] for a in n_eff if n_eff[a] >= 3}
        k = {a: lik[a] / n_lik[a] for a in n_lik if n_lik[a] >= 3}
        if e and k:
            total += 1
            agree += max(e, key=e.get) == max(k, key=k.get)
    usage = defaultdict(Counter)
    secs = defaultdict(list)
    for ev in events:
        if ev["event"] == "answer":
            usage[ev["mode"]][ev["arm"]] += 1
            secs[ev["mode"]].append(ev.get("seconds", 0))
    return {"rq1_rq2_pre_post_by_condition": rq12, "gain_contrasts": contrasts,
            "rq3_liked_most_equals_works_best": {"learners_with_enough_data": total, "agree": agree},
            "usage": {m: {"answers": sum(c.values()), "help_types": dict(c),
                          "median_seconds": sorted(secs[m])[len(secs[m]) // 2] if secs[m] else None}
                      for m, c in usage.items()},
            "note": "Pilot data: descriptive. Do not read small differences as effects."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="runs")
    ap.add_argument("--class-id", default="demo")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    a = ap.parse_args()
    state, events = load(a.data_dir, a.class_id)
    mode = json.load(open(a.config))["mode"]
    print(json.dumps(analyse(state, events, mode), indent=2))


if __name__ == "__main__":
    main()
