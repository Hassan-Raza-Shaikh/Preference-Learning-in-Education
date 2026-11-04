"""Learner model: per-skill mastery + per-learner explanation preference. Milestone M2.

Two separate things are learned about each learner, on purpose:

1. MASTERY per skill (here: one skill per solution method), via standard Bayesian
   Knowledge Tracing (BKT; Corbett & Anderson, 1995). Parameters default to OATutor's
   (bkt-params/defaultBKTParams.json, currently 0.1 for every skill: placeholders that
   should later be fitted to school data).

2. WHICH SCAFFOLDING LEVEL WORKS for this learner, at their current mastery. "Arms" are
   example / faded / outline / none (see explanations.py). Two signals are kept apart:
     * efficacy: did the learner solve the problem after that explanation? (outcome)
     * liking:   did the learner choose / rate that explanation highly? (stated preference)
   Each is a Beta posterior per (mastery band, arm). Selection uses Thompson sampling on
       score = (1 - w) * efficacy + w * liking,     w = teacher's `preference_weight`.
   Keeping both lets us study whether stated preferences agree with what works,
   rather than assume they do (cf. the "learning styles" literature).

   Pooling: a new learner starts from the CLASS-level counts, down-weighted by
   `class_prior_weight`, so the tutor is sensible from the first problem and becomes
   individual as evidence accumulates.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .content import ARMS

BANDS = ["low", "mid", "high"]


def band(p_mastery: float) -> str:
    return "low" if p_mastery < 0.4 else ("mid" if p_mastery < 0.8 else "high")


# --------------------------------------------------------------------------- #
# Bayesian Knowledge Tracing
# --------------------------------------------------------------------------- #
@dataclass
class BKTParams:
    p_init: float = 0.1
    p_transit: float = 0.1
    p_slip: float = 0.1
    p_guess: float = 0.1


def bkt_update(p: float, correct: bool, prm: BKTParams) -> float:
    """Posterior after observing one answer, then the learning transition."""
    if correct:
        num = p * (1 - prm.p_slip)
        den = num + (1 - p) * prm.p_guess
    else:
        num = p * prm.p_slip
        den = num + (1 - p) * (1 - prm.p_guess)
    post = num / den if den > 0 else p
    return post + (1 - post) * prm.p_transit


# --------------------------------------------------------------------------- #
# Beta counts
# --------------------------------------------------------------------------- #
def _zero():
    return {b: {a: [0.0, 0.0] for a in ARMS} for b in BANDS}   # [successes, failures]


@dataclass
class ClassStats:
    """Pooled counts across all learners in a class (the prior for new learners)."""
    efficacy: dict = field(default_factory=_zero)
    liking: dict = field(default_factory=_zero)

    def to_json(self):
        return {"efficacy": self.efficacy, "liking": self.liking}

    @classmethod
    def from_json(cls, d):
        return cls(efficacy=d["efficacy"], liking=d["liking"])


@dataclass
class LearnerState:
    learner_id: str
    mastery: dict = field(default_factory=dict)          # skill -> P(mastered)
    efficacy: dict = field(default_factory=_zero)
    liking: dict = field(default_factory=_zero)
    method_choices: dict = field(default_factory=dict)   # skill -> times chosen by learner
    history: list = field(default_factory=list)          # compact per-problem records
    assessment: dict = field(default_factory=dict)       # form -> {problem_id: correct}
    study_arm: str | None = None                         # condition, when a study randomises learners
    form_order: str = "AB"                               # AB: pre=form A, post=form B; BA: swapped

    def p(self, skill, prm: BKTParams):
        return self.mastery.get(skill, prm.p_init)

    def to_json(self):
        return {"learner_id": self.learner_id, "mastery": self.mastery, "efficacy": self.efficacy,
                "liking": self.liking, "method_choices": self.method_choices, "history": self.history,
                "assessment": self.assessment, "study_arm": self.study_arm, "form_order": self.form_order}

    @classmethod
    def from_json(cls, d):
        return cls(**d)


# --------------------------------------------------------------------------- #
# Policy
# --------------------------------------------------------------------------- #
# Textbook expertise-reversal rule: most support for novices, least for advanced learners.
RULE = {"low": "example", "mid": "faded", "high": "outline"}


def rule_prior(strength, arms=ARMS):
    """Pseudo-counts encoding RULE as a soft starting belief that evidence can override.

    Experimental, NOT a default: in the simulated-learner design search (docs/WORKLOG.md,
    2026-11-03) it looked helpful on the development seed but did not replicate on the
    held-out seed.
    """
    if not strength:
        return None
    return {b: {a: ([0.6 * strength, 0.4 * strength] if RULE[b] == a else [0.4 * strength, 0.6 * strength])
                for a in arms} for b in RULE}


@dataclass
class PolicyConfig:
    preference_weight: float = 0.3     # w: 0 = outcomes only, 1 = stated preference only
    class_prior_weight: float = 0.2    # how much class evidence counts for a new learner
    prior: dict | None = None          # optional {band: {arm: [succ, fail]}} pseudo-counts
    allowed_arms: tuple = tuple(ARMS)


def _posterior(own, cls, prior, b, a, cw):
    s = 1.0 + own[b][a][0] + cw * cls[b][a][0]
    f = 1.0 + own[b][a][1] + cw * cls[b][a][1]
    if prior:
        s += prior.get(b, {}).get(a, [0, 0])[0]
        f += prior.get(b, {}).get(a, [0, 0])[1]
    return s, f


def arm_scores(ls: LearnerState, cs: ClassStats, b: str, cfg: PolicyConfig, rng: random.Random,
               sample: bool = True) -> dict:
    """Thompson sample (or posterior mean) of the combined score for every allowed arm."""
    out = {}
    for a in cfg.allowed_arms:
        es, ef = _posterior(ls.efficacy, cs.efficacy, cfg.prior, b, a, cfg.class_prior_weight)
        ks, kf = _posterior(ls.liking, cs.liking, None, b, a, cfg.class_prior_weight)
        e = rng.betavariate(es, ef) if sample else es / (es + ef)
        k = rng.betavariate(ks, kf) if sample else ks / (ks + kf)
        out[a] = (1 - cfg.preference_weight) * e + cfg.preference_weight * k
    return out


def switch_order(b: str, allowed=ARMS) -> list:
    """Allowed help types ordered by closeness (in support level) to RULE's choice for band b."""
    want = ARMS.index(RULE[b])
    return sorted(allowed, key=lambda a: (abs(ARMS.index(a) - want), ARMS.index(a)))


def rule_arm(b: str, allowed=ARMS) -> str:
    """RULE's help type for this mastery band, or the nearest allowed one by support level."""
    return switch_order(b, allowed)[0]


def rule_switch_arm(b: str, consecutive_failures: int, allowed=ARMS) -> str:
    """'Rule + switch': RULE's help type, moving to the next-nearest type after each
    consecutive wrong answer on this skill (back to RULE's choice after a right answer)."""
    order = switch_order(b, allowed)
    return order[consecutive_failures % len(order)]


def choose_arm(ls, cs, b, cfg, rng) -> str:
    s = arm_scores(ls, cs, b, cfg, rng)
    return max(s, key=s.get)


def offer_two(ls, cs, b, cfg, rng) -> list[str]:
    """Two distinct arms to offer for learner choice (top-2 by Thompson sample)."""
    s = arm_scores(ls, cs, b, cfg, rng)
    ranked = sorted(s, key=s.get, reverse=True)
    return ranked[:2]


def record_outcome(ls: LearnerState, cs: ClassStats, b: str, arm: str, correct: bool):
    i = 0 if correct else 1
    ls.efficacy[b][arm][i] += 1
    cs.efficacy[b][arm][i] += 1


def record_liking(ls: LearnerState, cs: ClassStats, b: str, arm: str, liked: bool, weight: float = 1.0):
    i = 0 if liked else 1
    ls.liking[b][arm][i] += weight
    cs.liking[b][arm][i] += weight


def record_choice(ls, cs, b, chosen: str, rejected: str):
    """A pairwise choice: chosen gets a 'liked', the other a 'not liked' (half weight)."""
    record_liking(ls, cs, b, chosen, True, 1.0)
    record_liking(ls, cs, b, rejected, False, 0.5)


# --------------------------------------------------------------------------- #
# What to practise next
# --------------------------------------------------------------------------- #
def next_skill(ls: LearnerState, skills: list[str], prm, threshold: float,
               rng: random.Random) -> str | None:
    """Least-mastered enabled skill that is not yet mastered; None if all are mastered.

    `prm` is one BKTParams for every skill, or a function skill -> BKTParams.
    """
    get = prm if callable(prm) else (lambda _s: prm)
    p = {s: ls.p(s, get(s)) for s in skills}
    open_ = [s for s in skills if p[s] < threshold]
    if not open_:
        return None
    low = min(p[s] for s in open_)
    return rng.choice([s for s in open_ if p[s] == low])
