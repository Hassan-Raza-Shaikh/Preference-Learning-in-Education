# Project instructions

## Documentation is part of every task
The project lead must be able to explain all work to their supervisor. For **every**
session that changes code, data, experiments or direction:

1. Add a dated entry at the top of `docs/WORKLOG.md` with **What / Findings / Decisions /
   Next**. Include failures and negative results. Copy numbers from the run that produced
   them; never estimate. Label untested ideas as hypotheses.
2. Update milestone status in `docs/01_VISION_AND_PLAN.md` §5 when a milestone moves.
3. Track A (Phase 1 follow-ups) items live in `docs/02_PHASE1_METHOD_CONDITIONED_SOLVING.md` §8.
   Mark them done there and in the worklog.
4. Write for a non-specialist reader first (plain-language summary), then technical detail.

## Project rules
- **Correctness by construction:** maths shown to learners or used as training targets must be
  computed and verified by sympy, never free-form generated. Do not use `sympy.nsimplify`
  for displayed values; use `oatutor_extract.multimethod.exact`.
- Grade answers exactly (substitute back into the original system), not with an LLM judge.
- Personalise on evidence-backed dimensions (method, scaffolding, pacing, context), not
  "learning styles". Measure learning outcomes.
- Simulated-learner results show that the mechanism works, not that children learn more. Say so.
- Run `python -m pytest tests -q` before committing.
