# Work Log

A dated record of everything done on this project from 2026-11-03 onward, kept so it can
be explained to the supervisor. Newest entries at the top. Earlier work (2026-09-03 →
2026-10-09) is summarised in
[`02_PHASE1_METHOD_CONDITIONED_SOLVING.md`](02_PHASE1_METHOD_CONDITIONED_SOLVING.md) §4.

Each entry records **what** was done, **why**, the **result** (including failures), and
**decisions** made. Results are copied from the run that produced them, never estimated.

---

## 2026-11-03: Project review, reframing, documentation

**What**
- Reviewed the whole repository (extractor, generators, experiments, results, reports).
- Wrote down the original project idea and compared it with what Phase 1 actually tested.
- Created `docs/`:
  - `01_VISION_AND_PLAN.md`: the vision, the reframing, the proof-of-concept plan, the paper plan
  - `02_PHASE1_METHOD_CONDITIONED_SOLVING.md`: full record of the earlier work
  - `WORKLOG.md`: this file
- Rewrote `README.md` as a project landing page; added `CLAUDE.md` so future AI-assisted
  sessions keep this log and these docs up to date.

**Findings from the review**
- Phase 1 used "preference learning" in the ML sense: DPO with correct-vs-wrong pairs.
  The project's goal is preference in the **learner** sense (how a child prefers to be
  taught). The DPO result is valid but does not address personalisation. This is the main
  reason progress felt off-track.
- Checked: all conditions are evaluated with identical prompts, chat template and greedy
  decoding (`experiments/generate.py`). A prompt mismatch is **ruled out** as a cause of
  the base-vs-trained gap.
- Observed: DPO "rejected" solutions are truncated copies of the chosen solution with a wrong
  final line (`oatutor_extract/multimethod.py: make_rejected`). This is a plausible cause of
  the DPO failure. **Hypothesis, untested**; logged as Track A item A1.
- Test suite: 17/17 pass (`python -m pytest tests -q`).
- Found hard-coded macOS scratch paths in `experiments/run_all.py` and `collect_loss.py`
  (logged as A8).

**Decisions**
- Keep Phase 1 going as **Track A** (correctness backbone + paper P1).
- Start **Track B**: a proof-of-concept personalised tutor for systems of linear equations.
  This is the deliverable that could unlock the school's data and support.
- Personalise on evidence-backed dimensions (method, scaffolding level, pacing, context),
  not on "learning styles", and measure learning outcomes.
- For the prototype, correctness comes from the verified sympy engine, not from a
  fine-tuned small model.

**Next**
- M1: extend the verified generator with scaffolding levels (full worked / hints / check only).
- Confirm with the supervisor: proof-of-concept scope, what the school expects to see, and
  the ethics process.
