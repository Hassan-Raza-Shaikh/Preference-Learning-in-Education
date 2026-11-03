"""Scaffolded explanation variants for a (problem, method) pair. Milestone M1.

Four scaffolding levels ("arms"), from most to least support:

  example  A fully worked solution of a DIFFERENT but similar system (same method, same
           number of variables): an example-problem pair. The target's answer is never shown
           before the learner answers.
  faded    The target problem with its first steps worked out; the learner finishes it.
           The shown prefix is cut before any step that would reveal a final value.
  outline  The method's concept card: idea, why it works, generic steps (no numbers).
  none     No help; the learner tries first.

After the learner answers, `full_solution` (the target's verified worked solution) is
shown as feedback.

Every number in a variant comes from the verified bank (see bank.py); this module only
selects and arranges verified steps. It never computes or writes new maths.
"""
from __future__ import annotations

import hashlib
import re

from .content import ARM_LABEL, CONCEPT, LABEL


def _blocks(step: str):
    for blk in re.findall(r"\$\$(.+?)\$\$", step, re.S):
        yield from re.split(r",\s*(?=[a-zA-Z]\s*=)", blk.rstrip(".,"))


def _reveals_answer(step: str, problem: dict) -> bool:
    """True if the step states a final value: a math block 'v = ... = value' whose first
    side is a bare variable and some later side is exactly that variable's value.
    (An equation such as '2x+y=1' is not a reveal even when y=1.)"""
    if "Solution" in step or "intersection" in step:
        return True
    final = problem["methods"][next(iter(problem["methods"]))]["final_answer"]
    values = dict(pair.split("=", 1) for pair in final.split(", "))
    for block in _blocks(step):
        parts = [q.replace(" ", "") for q in block.split("=")]
        if len(parts) >= 2 and parts[0] in values and values[parts[0]].replace(" ", "") in parts[1:]:
            return True
    return False


def faded_prefix(problem: dict, method: str) -> list[str]:
    steps = problem["methods"][method]["steps"]
    cap = max(1, (len(steps) + 1) // 2)
    shown = []
    for st in steps[:cap]:
        if _reveals_answer(st, problem):
            break
        shown.append(st)
    return shown


def similarity_key(target: dict, cand: dict):
    ft, fc = target["features"], cand["features"]
    return (ft["fractional_solution"] != fc["fractional_solution"], abs(ft["max_coef"] - fc["max_coef"]))


def pick_example(problem: dict, method: str, bank: list[dict], salt: str = "") -> dict | None:
    """Choose a similar sibling problem for the worked example (deterministic per salt)."""
    sibs = [p for p in bank if p["id"] != problem["id"] and method in p["methods"]
            and p["features"]["n_vars"] == problem["features"]["n_vars"]
            and p["equations_tex"] != problem["equations_tex"]]
    if not sibs:
        return None
    sibs.sort(key=lambda c: (similarity_key(problem, c), c["id"]))
    top = sibs[:5]
    h = int(hashlib.sha256(f"{problem['id']}|{method}|{salt}".encode()).hexdigest(), 16)
    return top[h % len(top)]


def make_variant(problem: dict, method: str, arm: str, bank: list[dict], salt: str = "") -> dict:
    """Return a JSON-serialisable explanation variant."""
    card = CONCEPT[method]
    base = {"arm": arm, "arm_label": ARM_LABEL[arm], "method": method, "method_label": LABEL[method]}
    if arm == "none":
        return {**base, "blocks": [{"kind": "text", "text": "Have a go on your own. You can see the "
                                     "full worked solution after you answer."}]}
    if arm == "outline":
        return {**base, "blocks": [
            {"kind": "text", "text": f"**Idea.** {card['idea']}"},
            {"kind": "text", "text": f"**Why it works.** {card['why']}"},
            {"kind": "list", "title": "Steps", "items": card["steps"]},
            {"kind": "text", "text": f"**Handy when** {card['handy_when']}"},
        ]}
    if arm == "faded":
        shown = faded_prefix(problem, method)
        if not shown:                        # nothing can be shown without the answer
            return make_variant(problem, method, "outline", bank, salt) | {"fallback_from": "faded"}
        return {**base, "blocks": [
            {"kind": "list", "title": "Here is how this problem starts", "items": shown},
            {"kind": "text", "text": "Now carry on from here and finish the problem."},
        ], "verified_steps": True}
    if arm == "example":
        ex = pick_example(problem, method, bank, salt)
        if ex is None:                       # no sibling: fall back to the outline
            return make_variant(problem, method, "outline", bank, salt) | {"fallback_from": "example"}
        m = ex["methods"][method]
        return {**base, "blocks": [
            {"kind": "text", "text": "Here is a similar system, solved step by step:"},
            {"kind": "math", "items": ex["equations_tex"]},
            {"kind": "list", "title": f"Worked example ({LABEL[method]})",
             "items": m["steps"] + [f"Solution: $${m['final_answer']}$$."]},
            {"kind": "text", "text": "Now solve your system the same way."},
        ], "example_problem_id": ex["id"], "verified_steps": True}
    raise ValueError(f"unknown arm {arm!r}")


def full_solution(problem: dict, method: str) -> dict:
    m = problem["methods"][method]
    return {"method": method, "method_label": LABEL[method],
            "steps": m["steps"] + [f"Solution: $${m['final_answer']}$$."]}
