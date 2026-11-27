#!/usr/bin/env python3
"""Audit a train/valid/test split for identical systems that cross splits.

    python -m experiments.check_split_leakage                       # Phase 1 split
    python -m experiments.check_split_leakage --group-by system     # the leakage-free option

Found on 2026-11-27 (paper review): the Phase 1 split was made by OATutor problem_id, and
OATutor reuses some systems across courses. Result for the Phase 1 split: 4 test problems
(24 of 126 test items) have a system identical to a TRAINING problem, and 1 more test
problem (3 items) is identical to a validation problem. The 26 test problems contain 25
distinct systems. Writes data/train/split_leakage.json.
"""
import argparse
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.prepare_data import split_assignments, system_signature  # noqa: E402


def audit(systems, split_of):
    groups = defaultdict(list)
    for sid, rec in systems.items():
        groups[system_signature(rec)].append(sid)
    crossing = []
    for sig, ids in groups.items():
        splits = sorted({split_of[s] for s in ids})
        if len(splits) > 1:
            crossing.append({"problem_ids": sorted(ids), "splits": [split_of[s] for s in sorted(ids)]})
    test_ids = [s for s in systems if split_of[s] == "test"]
    train_sigs = {system_signature(systems[s]) for s in systems if split_of[s] == "train"}
    valid_sigs = {system_signature(systems[s]) for s in systems if split_of[s] == "valid"}
    leak_train = [s for s in test_ids if system_signature(systems[s]) in train_sigs]
    leak_valid = [s for s in test_ids if system_signature(systems[s]) in valid_sigs and s not in leak_train]
    items = lambda ids: sum(len(systems[s]["methods"]) for s in ids)
    return {"distinct_systems": len(groups), "problems": len(systems),
            "test_problems": len(test_ids), "test_items": items(test_ids),
            "distinct_test_systems": len({system_signature(systems[s]) for s in test_ids}),
            "test_problems_identical_to_train": sorted(leak_train), "test_items_identical_to_train": items(leak_train),
            "test_problems_identical_to_valid_only": sorted(leak_valid),
            "test_items_identical_to_valid_only": items(leak_valid),
            "groups_crossing_splits": crossing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mm-dir", default=os.path.join(ROOT, "data", "multimethod_worked"))
    ap.add_argument("--group-by", choices=["problem_id", "system"], default="problem_id")
    a = ap.parse_args()
    systems = {json.loads(l)["source"]["problem_id"]: json.loads(l)
               for l in open(os.path.join(a.mm_dir, "systems_multimethod.jsonl"), encoding="utf-8")}
    split_of = split_assignments(systems, a.group_by)
    if a.group_by == "problem_id":       # confirm this reproduces the committed Phase 1 split
        committed = json.load(open(os.path.join(ROOT, "data", "train", "split_manifest.json")))["system_ids"]
        assert {s: k for k, ids in committed.items() for s in ids} == split_of, "does not match Phase 1 split"
    res = audit(systems, split_of)
    res["group_by"] = a.group_by
    print(json.dumps({k: v for k, v in res.items() if k != "groups_crossing_splits"}, indent=2))
    if a.group_by == "problem_id":
        json.dump(res, open(os.path.join(ROOT, "data", "train", "split_leakage.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
