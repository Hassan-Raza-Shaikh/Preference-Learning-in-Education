"""Fit knowledge-tracing (BKT) parameters per skill from the tutor's own logs.

OATutor ships placeholder parameters (0.1 for all 1,238 skills), so the mastery estimates
are only rough until they are fitted to real answers. Run after a dry run or the pilot:

    python -m tutor.fit_bkt --data-dir runs --class-id demo            # print fitted values
    python -m tutor.fit_bkt --data-dir runs --class-id demo --write    # store in tutor/config.json

Method: maximum likelihood with the standard BKT forward pass (same update as the tutor:
observe, then learn), by a coarse grid search refined by local search. Constraints
p_guess < 0.5 and p_slip < 0.5 avoid the well-known degenerate solutions where "mastered"
and "not mastered" swap meaning. Skills with fewer than `--min-answers` practice answers
keep the default parameters.

Only PRACTICE answers are used (events 'answer'); quiz answers are not.

HOW MUCH DATA (measured 2026-11-04 by refitting simulated learners with known parameters,
5 replications each; the number is the largest error over the four parameters):
  240 answers per skill   errors up to 0.23     450   up to 0.26
  900                     up to 0.17            1,800 up to 0.09
So a single class's pilot is NOT enough to fit each skill separately. Use --pool (one
shared parameter set for all skills, written as the class default) until there are about
1,000+ answers per skill, e.g. from several classes.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from collections import defaultdict

from .learner_model import BKTParams

KEYS = ("p_init", "p_transit", "p_slip", "p_guess")
GRID = {"p_init": [0.05, 0.15, 0.3, 0.5, 0.7], "p_transit": [0.02, 0.08, 0.15, 0.25, 0.4],
        "p_slip": [0.03, 0.1, 0.2, 0.3], "p_guess": [0.03, 0.1, 0.2, 0.3, 0.45]}
BOUNDS = {"p_init": (0.01, 0.99), "p_transit": (0.005, 0.6), "p_slip": (0.005, 0.49), "p_guess": (0.005, 0.49)}


def loglik(seqs, prm: BKTParams) -> float:
    ll = 0.0
    for seq in seqs:
        p = prm.p_init
        for c in seq:
            pc = p * (1 - prm.p_slip) + (1 - p) * prm.p_guess
            ll += math.log(pc if c else 1 - pc)
            post = (p * (1 - prm.p_slip) / pc) if c else (p * prm.p_slip / (1 - pc))
            p = post + (1 - post) * prm.p_transit
    return ll


def fit(seqs, rounds=4):
    """Return (BKTParams, loglik) maximising the likelihood of the 0/1 sequences."""
    best, best_ll = None, -math.inf
    for vals in itertools.product(*(GRID[k] for k in KEYS)):
        prm = BKTParams(*vals)
        ll = loglik(seqs, prm)
        if ll > best_ll:
            best, best_ll = prm, ll
    step = 0.05
    for _ in range(rounds):                   # coordinate refinement around the grid optimum
        improved = True
        while improved:
            improved = False
            for k in KEYS:
                for d in (-step, step):
                    cand = dict(zip(KEYS, (getattr(best, x) for x in KEYS)))
                    lo, hi = BOUNDS[k]
                    cand[k] = min(hi, max(lo, cand[k] + d))
                    prm = BKTParams(**cand)
                    ll = loglik(seqs, prm)
                    if ll > best_ll + 1e-9:
                        best, best_ll, improved = prm, ll, True
        step /= 2
    return best, best_ll


def sequences_from_events(path):
    """skill -> list of per-learner 0/1 sequences, in time order (practice answers only)."""
    per = defaultdict(lambda: defaultdict(list))
    for line in open(path, encoding="utf-8"):
        ev = json.loads(line)
        if ev["event"] == "answer":
            per[ev["skill"]][ev["learner"]].append((ev["t"], int(ev["correct"])))
    return {s: [[c for _, c in sorted(v)] for v in by_l.values()] for s, by_l in per.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="runs")
    ap.add_argument("--class-id", default="demo")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    ap.add_argument("--min-answers", type=int, default=1000)
    ap.add_argument("--pool", action="store_true",
                    help="fit ONE parameter set across all skills (for small pilots); written as 'bkt'")
    ap.add_argument("--write", action="store_true", help="store fitted values as bkt_per_skill in the config")
    a = ap.parse_args()
    seqs = sequences_from_events(os.path.join(a.data_dir, a.class_id, "events.jsonl"))
    if a.pool:
        seqs = {"ALL_SKILLS": [s for ss in seqs.values() for s in ss]}
    out = {}
    for skill, ss in sorted(seqs.items()):
        n = sum(len(s) for s in ss)
        if n < a.min_answers:
            print(f"{skill}: {n} answers from {len(ss)} learners, fewer than {a.min_answers}: keep default")
            continue
        prm, ll = fit(ss)
        out[skill] = {k: round(getattr(prm, k), 3) for k in KEYS}
        print(f"{skill}: {n} answers from {len(ss)} learners -> {out[skill]} (log-likelihood {ll:.1f})")
    if a.write and out:
        cfg = json.load(open(a.config))
        if a.pool:
            cfg["bkt"] = out["ALL_SKILLS"]
        else:
            cfg["bkt_per_skill"] = {**(cfg.get("bkt_per_skill") or {}), **out}
        json.dump(cfg, open(a.config, "w"), indent=2)
        print("written to", a.config)


if __name__ == "__main__":
    main()
