"""Generate learner codes for a class and store them as the tutor's allow-list.

    python -m tutor.codes --prefix 7B --n 30            # 7B-01 ... 7B-30, saved to tutor/config.json

The teacher writes each pupil's name next to a code ON PAPER (or in the school's own
system). Names never go into the tutor. With `learner_codes` set, a mistyped code is
rejected instead of silently creating a new pupil.
"""
from __future__ import annotations

import argparse
import json
import os

from .engine import DEFAULT_CONFIG, LEARNER_ID


def make_codes(prefix: str, n: int) -> list[str]:
    width = max(2, len(str(n)))
    codes = [f"{prefix}-{i:0{width}d}" for i in range(1, n + 1)]
    if not all(LEARNER_ID.match(c) for c in codes):
        raise ValueError("prefix may contain only letters, digits, '-' or '_'")
    return codes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--append", action="store_true", help="add to existing codes instead of replacing them")
    a = ap.parse_args()
    codes = make_codes(a.prefix, a.n)
    cfg = json.load(open(a.config))
    if a.append and cfg.get("learner_codes"):
        codes = list(dict.fromkeys(cfg["learner_codes"] + codes))
    cfg["learner_codes"] = codes
    json.dump(cfg, open(a.config, "w"), indent=2)
    print(f"{len(codes)} codes saved to {os.path.relpath(a.config)}. Code sheet (add names on paper):")
    for c in codes:
        print(f"  {c}   ____________________")


if __name__ == "__main__":
    main()
