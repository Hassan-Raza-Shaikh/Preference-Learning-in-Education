"""Personalised, verified tutor: proof of concept (Track B).

Modules
-------
content         human-authored method concept cards (no numbers)
bank            problem bank built from the verified Phase 1 worked solutions
explanations    scaffolded explanation variants (example / faded / outline / none)
grading         exact grading of learner answers (sympy, substitution into the system)
learner_model   per-skill mastery (BKT) + per-learner explanation preference (Thompson sampling)
engine          one tutoring session: next problem -> explanation -> answer -> update
app             minimal web app (stdlib HTTP server) for learners and teachers
simulate        simulated-learner evaluation of the adaptation loop
"""
