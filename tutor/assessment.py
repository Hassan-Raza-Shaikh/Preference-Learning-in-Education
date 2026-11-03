"""Pre/post assessment forms for a study (supports milestone M5).

Builds two PARALLEL forms (pre and post) from the problem bank: for each enabled method,
problems are paired by difficulty features (number of variables, fractional solution,
coefficient size), and one of each pair goes to each form. Assessment problems are then
excluded from practice, so a post-test score is not inflated by having practised the
same system.

    python -m tutor.assessment --per-method 2            # writes forms into tutor/config.json
"""
from __future__ import annotations

import argparse
import json
import random

from . import bank as bank_mod
from .engine import DEFAULT_CONFIG


def build_forms(bank, skills, n_vars, per_method=2, seed=20261103):
    rng = random.Random(seed)
    used, pre, post = set(), [], []
    for m in skills:
        cands = [p for p in bank if m in p["methods"] and p["features"]["n_vars"] in n_vars and p["id"] not in used]
        cands.sort(key=lambda p: (p["features"]["n_vars"], p["features"]["fractional_solution"],
                                  p["features"]["max_coef"], p["id"]))
        # adjacent problems in this order are similar: take pairs and split them across forms
        pairs = [cands[i:i + 2] for i in range(0, len(cands) - 1, 2)]
        rng.shuffle(pairs)
        for a, b in pairs[:per_method]:
            if rng.random() < 0.5:
                a, b = b, a
            pre.append({"problem_id": a["id"], "method": m})
            post.append({"problem_id": b["id"], "method": m})
            used |= {a["id"], b["id"]}
    return {"pre": pre, "post": post, "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--per-method", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261103)
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    forms = build_forms(bank_mod.load(), cfg["skills"], cfg["n_vars"], a.per_method, a.seed)
    cfg["assessment"] = forms
    json.dump(cfg, open(a.config, "w"), indent=2)
    print(json.dumps(forms, indent=2))


if __name__ == "__main__":
    main()
