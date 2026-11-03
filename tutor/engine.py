"""Tutoring session engine. Milestone M3 (logic; the web layer is app.py).

One loop per problem:
  next_problem -> (learner chooses / tutor picks) explanation -> answer (graded exactly)
  -> full worked solution shown -> optional "was this helpful?" -> models updated.

Modes (teacher config `mode`):
  learner_choice  tutor offers two explanation types, learner picks one (stated preference)
  rule            tutor picks by mastery: worked example -> faded -> outline (expertise reversal);
                  the strongest policy in the simulated-learner check (tutor/results/)
  adaptive        tutor picks the explanation type by Thompson sampling (EXPERIMENTAL: did not
                  beat `rule` in simulation)
  fixed           always `fixed_arm`: the NON-ADAPTIVE CONTROL condition for a study

Study mode (config `study`): {"arms": ["fixed", "rule", "learner_choice"], "counterbalance": true}
randomises each NEW learner to one of the arms (block randomisation, so arms stay balanced
as learners join) and, with counterbalancing, half of each arm takes form B as the pre-test.

Everything is logged to <data_dir>/<class_id>/events.jsonl (one JSON event per line) and
state is saved to state.json after every change. Learners are identified only by a
pseudonymous code; no names or other personal data are stored.
"""
from __future__ import annotations

import json
import os
import random
import re
import threading
import time

from . import bank as bank_mod
from .content import ARM_LABEL, ARMS, LABEL, METHODS
from .explanations import full_solution, make_variant
from .grading import grade
from .learner_model import (
    BKTParams, ClassStats, LearnerState, PolicyConfig, band, bkt_update, choose_arm, rule_arm,
    next_skill, offer_two, record_choice, record_liking, record_outcome,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "tutor", "config.json")
DEFAULT_DATA = os.path.join(ROOT, "runs")
LEARNER_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
MODES = ("learner_choice", "rule", "adaptive", "fixed")
MIN_EVIDENCE = 3


class TutorError(ValueError):
    pass


def validate_config(cfg: dict) -> dict:
    c = dict(cfg)
    if not c.get("skills") or any(s not in METHODS for s in c["skills"]):
        raise TutorError(f"skills must be a non-empty subset of {METHODS}")
    if c.get("mode") not in MODES:
        raise TutorError(f"mode must be one of {MODES}")
    if not c.get("allowed_arms") or any(a not in ARMS for a in c["allowed_arms"]):
        raise TutorError(f"allowed_arms must be a non-empty subset of {ARMS}")
    if c["mode"] == "learner_choice" and len(c["allowed_arms"]) < 2:
        raise TutorError("learner_choice mode needs at least two allowed explanation types")
    if c.get("fixed_arm") not in ARMS:
        raise TutorError(f"fixed_arm must be one of {ARMS}")
    if not set(c.get("n_vars", [])) <= {2, 3} or not c.get("n_vars"):
        raise TutorError("n_vars must be a non-empty subset of [2, 3]")
    for k in ("preference_weight", "class_prior_weight"):
        if not 0 <= float(c[k]) <= 1:
            raise TutorError(f"{k} must be between 0 and 1")
    if not 0.5 <= float(c["mastery_threshold"]) < 1:
        raise TutorError("mastery_threshold must be in [0.5, 1)")
    if c.get("assessment_open") not in (None, "pre", "post"):
        raise TutorError("assessment_open must be null, 'pre' or 'post'")
    if c.get("assessment_open") and not c.get("assessment", {}).get(c["assessment_open"]):
        raise TutorError("no assessment form built yet: run python -m tutor.assessment")
    study = c.get("study")
    if study:
        arms = study.get("arms") or []
        if len(arms) < 2 or any(a not in MODES for a in arms) or len(set(arms)) != len(arms):
            raise TutorError(f"study.arms must list at least two different modes from {MODES}")
        if "learner_choice" in arms and len(c["allowed_arms"]) < 2:
            raise TutorError("learner_choice needs at least two allowed explanation types")
    return c


class Tutor:
    def __init__(self, config_path=DEFAULT_CONFIG, bank_path=bank_mod.DEFAULT_BANK,
                 data_dir=DEFAULT_DATA, seed=None):
        self.config_path = config_path
        self.cfg = validate_config(json.load(open(config_path)))
        self.bank = bank_mod.load(bank_path)
        self.by_id = {p["id"]: p for p in self.bank}
        self.dir = os.path.join(data_dir, self.cfg["class_id"])
        os.makedirs(self.dir, exist_ok=True)
        self.rng = random.Random(seed)
        self.lock = threading.RLock()
        self.learners: dict[str, LearnerState] = {}
        self.pending: dict[str, dict] = {}
        self.cls = ClassStats()
        self.study_state = {"block": [], "assigned": 0}
        self._load()

    # ------------------------------------------------------------------ persistence
    @property
    def state_path(self):
        return os.path.join(self.dir, "state.json")

    def _load(self):
        if os.path.exists(self.state_path):
            d = json.load(open(self.state_path))
            self.cls = ClassStats.from_json(d["class"])
            self.learners = {k: LearnerState.from_json(v) for k, v in d["learners"].items()}
            self.pending = d.get("pending", {})
            self.study_state = d.get("study_state", self.study_state)

    def _save(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({"class": self.cls.to_json(),
                       "learners": {k: v.to_json() for k, v in self.learners.items()},
                       "pending": self.pending, "study_state": self.study_state}, fh)
        os.replace(tmp, self.state_path)

    def log(self, event: str, mode=None, **kw):
        rec = {"t": round(time.time(), 3), "event": event, "class_id": self.cfg["class_id"],
               "mode": mode or self.cfg["mode"], **kw}
        with open(os.path.join(self.dir, "events.jsonl"), "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    # ------------------------------------------------------------------ helpers
    @property
    def bkt(self):
        return BKTParams(**self.cfg["bkt"])

    @property
    def policy(self):
        return PolicyConfig(preference_weight=self.cfg["preference_weight"],
                            class_prior_weight=self.cfg["class_prior_weight"],
                            allowed_arms=tuple(self.cfg["allowed_arms"]))

    def skills(self):
        """Enabled skills that have problems for the enabled sizes."""
        nv = set(self.cfg["n_vars"])
        return [s for s in self.cfg["skills"]
                if any(s in p["methods"] and p["features"]["n_vars"] in nv for p in self.bank)]

    def learner(self, lid) -> LearnerState:
        if not isinstance(lid, str) or not LEARNER_ID.match(lid):
            raise TutorError("Learner code must be 1-32 letters, digits, '-' or '_' (no names, please).")
        if lid not in self.learners:
            ls = LearnerState(learner_id=lid)
            self._assign(ls)
            self.learners[lid] = ls
            self.log("learner_created", learner=lid, mode=self.mode_for(ls),
                     study_arm=ls.study_arm, form_order=ls.form_order)
        return self.learners[lid]

    def _assign(self, ls):
        """Block randomisation of a new learner to a study arm (and form order)."""
        study = self.cfg.get("study")
        if not study:
            return
        cb = study.get("counterbalance", True)
        if not self.study_state["block"]:
            block = [(a, o) for a in study["arms"] for o in (("AB", "BA") if cb else ("AB",))]
            self.rng.shuffle(block)
            self.study_state["block"] = block
        ls.study_arm, ls.form_order = self.study_state["block"].pop()
        self.study_state["assigned"] += 1

    def mode_for(self, ls):
        return ls.study_arm or self.cfg["mode"]

    def assessment_ids(self):
        forms = self.cfg.get("assessment") or {}
        return {it["problem_id"] for f in ("pre", "post") for it in forms.get(f, [])}

    def _pick_problem(self, ls, skill):
        nv = set(self.cfg["n_vars"])
        held_out = self.assessment_ids()          # never practise on test items
        cands = [p for p in self.bank if skill in p["methods"] and p["features"]["n_vars"] in nv
                 and p["id"] not in held_out]
        seen = {h["problem_id"] for h in ls.history if h["skill"] == skill}
        fresh = [p for p in cands if p["id"] not in seen]
        return self.rng.choice(fresh or cands)

    def _public_problem(self, p):
        return {"problem_id": p["id"], "variables": p["variables"], "equations_tex": p["equations_tex"],
                "source": {k: p["source"][k] for k in ("course", "lesson", "oer", "oer_url", "license", "license_url")}}

    def mastery_view(self, ls):
        return {s: round(ls.p(s, self.bkt), 3) for s in self.skills()}

    # ------------------------------------------------------------------ API
    def start(self, lid):
        with self.lock:
            ls = self.learner(lid)
            self._save()
            return {"learner_id": lid, "mastery": self.mastery_view(ls),
                    "skills": [{"id": s, "label": LABEL[s]} for s in self.skills()],
                    "can_pick_method": self.cfg["learner_can_pick_method"],
                    "threshold": self.cfg["mastery_threshold"], "pending": self.pending.get(lid),
                    "assessment": self._assessment_status(ls)}

    def next_problem(self, lid, method=None):
        with self.lock:
            ls = self.learner(lid)
            skills = self.skills()
            if method:
                if not self.cfg["learner_can_pick_method"] or method not in skills:
                    raise TutorError("That method is not available.")
                skill = method
                ls.method_choices[skill] = ls.method_choices.get(skill, 0) + 1
            else:
                skill = next_skill(ls, skills, self.bkt, self.cfg["mastery_threshold"], self.rng)
                if skill is None:
                    return {"done": True, "mastery": self.mastery_view(ls),
                            "message": "You have mastered every method your teacher selected!"}
            p = self._pick_problem(ls, skill)
            b = band(ls.p(skill, self.bkt))
            item = {"problem_id": p["id"], "skill": skill, "band": b, "picked_by": "learner" if method else "tutor",
                    "t_start": time.time()}
            mode = self.mode_for(ls)
            out = {"problem": self._public_problem(p), "method": skill, "method_label": LABEL[skill],
                   "mode": mode, "mastery": self.mastery_view(ls)}
            if mode == "learner_choice":
                offered = offer_two(ls, self.cls, b, self.policy, self.rng)
                item["offered"] = offered
                out["offered"] = [{"arm": a, "label": ARM_LABEL[a]} for a in offered]
            else:
                if mode == "adaptive":
                    arm = choose_arm(ls, self.cls, b, self.policy, self.rng)
                elif mode == "rule":
                    arm = rule_arm(b, self.cfg["allowed_arms"])
                else:
                    arm = self.cfg["fixed_arm"]
                item["arm"] = arm
                out["explanation"] = make_variant(p, skill, arm, self.bank, salt=lid)
            self.pending[lid] = item
            self.log("problem_shown", learner=lid, mode=self.mode_for(ls), **{k: v for k, v in item.items() if k != "t_start"})
            self._save()
            return out

    def choose(self, lid, arm):
        with self.lock:
            ls = self.learner(lid)
            item = self.pending.get(lid)
            if not item or "offered" not in item or "arm" in item:
                raise TutorError("No explanation choice is waiting.")
            if arm not in item["offered"]:
                raise TutorError("Please pick one of the offered explanations.")
            other = [a for a in item["offered"] if a != arm][0]
            record_choice(ls, self.cls, item["band"], arm, other)
            item["arm"] = arm
            p = self.by_id[item["problem_id"]]
            self.log("explanation_chosen", learner=lid, mode=self.mode_for(ls), problem_id=p["id"], skill=item["skill"],
                     band=item["band"], chosen=arm, rejected=other)
            self._save()
            return {"explanation": make_variant(p, item["skill"], arm, self.bank, salt=lid)}

    def answer(self, lid, text):
        with self.lock:
            ls = self.learner(lid)
            item = self.pending.get(lid)
            if not item or "arm" not in item:
                raise TutorError("Choose an explanation first.")
            p = self.by_id[item["problem_id"]]
            A, b = bank_mod.matrices(p)
            g = grade(text, p["variables"], A, b, p["reference"])
            if not g["parsed"]:
                self.log("answer_unparsed", learner=lid, mode=self.mode_for(ls), problem_id=p["id"])
                return {"graded": False, "message": g["message"]}
            skill, bd, arm = item["skill"], item["band"], item["arm"]
            before = ls.p(skill, self.bkt)
            ls.mastery[skill] = bkt_update(before, g["correct"], self.bkt)
            record_outcome(ls, self.cls, bd, arm, g["correct"])
            rec = {"problem_id": p["id"], "skill": skill, "band": bd, "arm": arm,
                   "correct": g["correct"], "mastery_before": round(before, 4),
                   "mastery_after": round(ls.mastery[skill], 4),
                   "seconds": round(time.time() - item.get("t_start", time.time()), 1),
                   "picked_by": item.get("picked_by")}
            ls.history.append(rec)
            # privacy: log the parsed numbers only, never the raw typed text
            self.log("answer", learner=lid, mode=self.mode_for(ls), answer_values=g["values"], **rec,
                     per_variable=g.get("per_variable"))
            item["answered"] = True
            self._save()
            return {"graded": True, "correct": g["correct"], "message": g["message"],
                    "per_variable": g["per_variable"], "solution": full_solution(p, skill),
                    "mastery": self.mastery_view(ls), "mastered": ls.mastery[skill] >= self.cfg["mastery_threshold"]}

    def rate(self, lid, helpful: int):
        with self.lock:
            ls = self.learner(lid)
            item = self.pending.get(lid)
            if not item or not item.get("answered"):
                raise TutorError("Nothing to rate yet.")
            if helpful not in (1, 2, 3):
                raise TutorError("Rating must be 1, 2 or 3.")
            record_liking(ls, self.cls, item["band"], item["arm"], helpful >= 2, 1.0 if helpful != 2 else 0.5)
            self.log("rating", learner=lid, mode=self.mode_for(ls), problem_id=item["problem_id"], skill=item["skill"],
                     band=item["band"], arm=item["arm"], helpful=helpful)
            self.pending.pop(lid, None)
            self._save()
            return {"ok": True}

    def skip_rating(self, lid):
        with self.lock:
            self.pending.pop(lid, None)
            self._save()
            return {"ok": True}

    # ------------------------------------------------------------------ assessment (pre/post test)
    def _form_items(self, ls, form):
        """Items for 'pre'/'post' for this learner; BA order swaps the two forms."""
        forms = self.cfg.get("assessment") or {}
        if ls.form_order == "BA":
            form = {"pre": "post", "post": "pre"}[form]
        return forms.get(form, [])

    def _assessment_status(self, ls):
        form = self.cfg.get("assessment_open")
        if not form:
            return None
        items = self._form_items(ls, form)
        done = ls.assessment.get(form, {})
        return {"form": form, "answered": sum(it["problem_id"] in done for it in items), "total": len(items)}

    def assess_next(self, lid):
        with self.lock:
            ls = self.learner(lid)
            form = self.cfg.get("assessment_open")
            if not form:
                raise TutorError("No quiz is open right now.")
            done = ls.assessment.get(form, {})
            for it in self._form_items(ls, form):
                if it["problem_id"] not in done:
                    p = self.by_id[it["problem_id"]]
                    return {"done": False, "form": form, "problem": self._public_problem(p),
                            "method": it["method"], "method_label": LABEL[it["method"]],
                            "status": self._assessment_status(ls)}
            return {"done": True, "form": form, "status": self._assessment_status(ls)}

    def assess_answer(self, lid, problem_id, text):
        """Graded exactly but NOT shown to the learner, and not used to update the learner model."""
        with self.lock:
            ls = self.learner(lid)
            form = self.cfg.get("assessment_open")
            items = {it["problem_id"]: it for it in (self._form_items(ls, form) if form else [])}
            if problem_id not in items:
                raise TutorError("That question is not part of the open quiz.")
            if problem_id in ls.assessment.get(form, {}):
                raise TutorError("You have already answered this question.")
            p = self.by_id[problem_id]
            A, b = bank_mod.matrices(p)
            g = grade(text, p["variables"], A, b, p["reference"])
            if not g["parsed"]:
                return {"recorded": False, "message": g["message"]}
            ls.assessment.setdefault(form, {})[problem_id] = g["correct"]
            self.log("assessment_answer", learner=lid, mode=self.mode_for(ls), form=form,
                     form_order=ls.form_order, problem_id=problem_id,
                     method=items[problem_id]["method"], answer_values=g["values"], correct=g["correct"])
            self._save()
            return {"recorded": True, "status": self._assessment_status(ls)}

    # ------------------------------------------------------------------ teacher
    def teacher_summary(self):
        with self.lock:
            rows = []
            for lid, ls in sorted(self.learners.items()):
                n = len(ls.history)
                acc = sum(h["correct"] for h in ls.history) / n if n else None
                pref = {}
                for b in ("low", "mid", "high"):
                    # only report an arm once it has MIN_EVIDENCE observations in this band
                    means = {a: (1 + ls.efficacy[b][a][0]) / (2 + sum(ls.efficacy[b][a])) for a in self.cfg["allowed_arms"]
                             if sum(ls.efficacy[b][a]) >= MIN_EVIDENCE}
                    likes = {a: (1 + ls.liking[b][a][0]) / (2 + sum(ls.liking[b][a])) for a in self.cfg["allowed_arms"]
                             if sum(ls.liking[b][a]) >= MIN_EVIDENCE}
                    if means or likes:
                        pref[b] = {"works_best": max(means, key=means.get) if means else None,
                                   "liked_most": max(likes, key=likes.get) if likes else None}
                scores = {f: (sum(v.values()), len(v)) for f, v in ls.assessment.items()}
                rows.append({"learner_id": lid, "problems": n, "accuracy": acc, "assessment": scores,
                             "condition": self.mode_for(ls), "form_order": ls.form_order,
                             "mastery": self.mastery_view(ls), "preferences": pref,
                             "method_choices": ls.method_choices})
            return {"config": self.cfg, "learners": rows,
                    "skills": [{"id": s, "label": LABEL[s]} for s in self.skills()]}

    def set_config(self, new: dict):
        with self.lock:
            merged = validate_config({**self.cfg, **new, "class_id": self.cfg["class_id"]})
            self.cfg = merged
            with open(self.config_path, "w") as fh:
                json.dump(merged, fh, indent=2)
            self.log("config_changed", config=merged)
            return merged
