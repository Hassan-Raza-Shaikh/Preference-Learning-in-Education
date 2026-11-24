# Data management plan (draft)

*Draft 2026-11-03. Check it against the data-protection law that applies to the school and
university (for example GDPR in the EU/UK, or the relevant national law) and against the
university's data-management requirements.*

## 1. Principles

- **Data minimisation:** record only what the research questions need.
- **Pseudonymisation:** pupils are codes. The code↔name list stays with the teacher, at
  the school.
- **No free text:** the tutor logs only the *parsed numbers* of an answer, never what was
  typed. This is enforced in code (`tutor/engine.py`) and tested
  (`tests/test_tutor.py::test_engine_full_loop_and_logging`).

## 2. What is recorded

The tutor writes two files per class, in `runs/<class_id>/`. That folder is git-ignored
and must never be committed.

| Field | Example | Why |
|---|---|---|
| learner code | `7B-04` | link records for one pupil |
| timestamps, seconds per problem | `1793709572.7`, `41.2` | time on task |
| condition, quiz form order | `rule`, `AB` | study design |
| problem id, method, mastery band | `a372017cramer12`, `elimination`, `low` | what was practised |
| help offered / chosen / used | `["example", "faded"]`, `faded` | RQ2, RQ3 |
| answer as parsed numbers; correct or not | `{"x": "3", "y": "1"}`, `true` | learning measures |
| usefulness rating | `1`–`3` | RQ3 |
| mastery estimate before and after | `0.10 → 0.31` | knowledge tracing |
| quiz answers (parsed numbers) and scores | | RQ1, RQ2 |
| teacher configuration changes | | reproducibility |

**Not recorded:** names, dates of birth, photos, audio, IP addresses (the tutor does not
log them), raw typed text, or device identifiers.

**Learner-code format:** letters, digits, `-` or `_` only. Names with spaces are rejected,
but a pupil could still type a first name as a code. The teacher guide asks teachers to
pre-assign codes.

## 3. Storage and access

**Access control in the app.** The teacher page and its data/settings API require a
teacher key: a private link printed at start-up. Requests without it get "401 teacher key
required" (tested in `tests/test_tutor.py`). Pupils can only reach their own practice
through their code.

**Known limitation:** a pupil who knows another pupil's code could log in as them. This is
acceptable for a supervised pilot; a full deployment would need proper accounts.

| Stage | Where | Who |
|---|---|---|
| During the pilot | the laptop running the tutor (encrypted disk, password-protected account) | researcher, teacher |
| Code↔name list | at the school only | teacher |
| After each session | copy `runs/<class_id>/` to [university-approved encrypted storage] | researcher, supervisor |
| Analysis | university-approved machine | researcher, supervisor |

## 4. Retention and deletion

- **Withdrawal:** possible until [date]. Delete that code's records from `state.json` and
  `events.jsonl`, and note the deletion (but not the code) in the study log.
- **Anonymisation:** on [date], the teacher destroys the code↔name list, after which the
  data are anonymous.
- **Raw logs:** kept until [date, e.g. publication + N years, per university policy], then
  deleted.
- **Sharing:** only aggregated or anonymised data may be shared (for example with a paper),
  and only if consent covered it.

## 5. Breach procedure

If a device holding data is lost, or data are exposed: tell the supervisor and the
university's data-protection officer within [24 hours]; follow the university procedure.
