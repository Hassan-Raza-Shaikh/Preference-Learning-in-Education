# School pilot package (milestone M5)

*Drafted 2026-11-03. These are **drafts** for discussion with the supervisor, the school and
the ethics board. Nothing here has been approved, and no child should use the tutor until
it has.*

| Document | For |
|---|---|
| [`STUDY_DESIGN.md`](STUDY_DESIGN.md) | Research questions, conditions, measures, sample size, analysis plan |
| [`CONSENT_TEMPLATES.md`](CONSENT_TEMPLATES.md) | Parent information sheet and consent, child assent, teacher information |
| [`DATA_MANAGEMENT.md`](DATA_MANAGEMENT.md) | Exactly what is recorded, where it lives, who sees it, when it is deleted |
| [`TEACHER_GUIDE.md`](TEACHER_GUIDE.md) | Running the tutor in class: setup, codes, quiz, dashboard, troubleshooting |

## Showing the proof of concept to the school (about 10 minutes)

Before the meeting, on a laptop:

```bash
python -m tutor.app
```

Then open `http://localhost:8000` (learner) and the **teacher link printed in the
terminal** (`/teacher?key=...`) side by side.

1. **Never wrong.** Solve a problem and get it wrong on purpose. The tutor grades exactly
   and gives a specific hint (for example "check the sign of x"), then shows a full worked
   solution. Say that every step shown has been checked by a computer algebra system: in the
   current bank, 5,983 displayed equations were checked with 0 failures.
2. **Learner preference.** Choose between the two help types offered (worked example,
   "start me off", method reminder, or try alone), then rate how useful it was. On the
   teacher page, point out "works best" vs "liked most" for that learner.
3. **Builds skill.** Answer a few correctly and watch the mastery bars rise. The next
   problem targets the weakest method.
4. **Teacher control.** Change which methods to practise, which help types are allowed,
   and the mode (learner chooses / tutor chooses by mastery / always the same help), then save.
5. **Measurable.** Open the pre-test quiz (no help, no answers shown) and show that
   scores appear per learner. Explain the study design: random assignment to conditions,
   pre/post test, analysis script.

**Be upfront about what is not shown yet.** The only evaluation so far is with simulated
learners. It showed that the machinery works and that the simple mastery rule is a strong
baseline. It did **not** show that children learn more; that is what the pilot is for.
