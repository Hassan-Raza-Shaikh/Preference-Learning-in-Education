# Teacher guide: running the tutor in class (draft)

## 1. Before the first lesson (researcher + teacher)

1. On the laptop that will run the tutor:
   ```bash
   pip install sympy
   python -m tutor.app --host 0.0.0.0 --port 8000
   ```
   `--host 0.0.0.0` lets pupils' devices on the **school network** reach it at
   `http://<laptop-address>:8000`. On a single laptop, leave `--host` out. Everything runs
   offline: the maths renderer is bundled, and no internet connection is needed.

   At start-up the tutor prints a **private teacher link** containing a key
   (`/teacher?key=...`). Only that link opens the teacher page, so pupils on the same
   network cannot see other pupils' data or change settings. The key changes at every
   start unless you fix it with `--teacher-key` or the `TUTOR_TEACHER_KEY` variable.
2. Create **learner codes** and a code sheet:
   ```bash
   python -m tutor.codes --prefix 7B --n 30
   ```
   This prints `7B-01` … `7B-30` and stores them as the allow-list, so a mistyped code is
   rejected instead of creating a new pupil. Write names next to codes **on paper** (or in
   the school's system); never type names into the tutor.
3. Build the quiz forms once, after choosing the methods:
   ```bash
   python -m tutor.assessment --per-method 2
   ```
4. For a study, set the conditions in `tutor/config.json`:
   ```json
   "study": {"arms": ["fixed", "rule", "learner_choice"], "counterbalance": true}
   ```
   Each new learner code is then randomly assigned to a condition.

## 2. The teacher page (`/teacher`)

- **Methods to practise:** for example substitution, elimination and graphing for two-variable systems.
- **Help types allowed:** worked example, faded (first steps done), method outline, no help.
- **Mode:** learner chooses the help / tutor chooses by mastery / tutor learns
  (experimental) / always the same help. If a study is set up, each pupil's condition
  overrides this.
- **Quiz open:** none / pre-test / post-test. While a quiz is open, pupils see it first
  when they log in.
- **Learners table:** quiz scores, problems done, % correct, mastery per method, which help
  "works best" vs is "liked most" (shown after 3 or more uses), and which methods pupils chose.

## 3. Lesson plan

- **Session 1:** open the **pre-test**. Pupils log in with their code and complete 6
  questions (about 10 minutes), then practise. Close the quiz at the end.
- **Sessions 2–4:** practice. Pupils click "Next problem" (the tutor picks the weakest
  method) or pick a method themselves.
- **Last session:** open the **post-test**. Afterwards, run the analysis:
  ```bash
  python -m tutor.analyze_study --data-dir runs --class-id demo
  ```
- **After the pilot (researcher):** fit the mastery-model parameters to the real answers:
  ```bash
  python -m tutor.fit_bkt --data-dir runs --class-id demo --pool --write
  ```
  Use `--pool` for a single class. Fitting each method separately needs about 1,000+
  answers per method; see the note in `tutor/fit_bkt.py`.

## 4. Answer format pupils can use

`x=2, y=-1/3`, or `(2, -1/3)`, or `x = 0.5; y = 4`. Fractions must be exact: `1/3`, not
`0.333`. If the tutor can't read an answer, it says how to type it, and nothing is recorded
except that the answer could not be read.

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| Pupil's code rejected | Check it against the code sheet. Codes may contain only letters, digits, `-` and `_` |
| Teacher page says "open the teacher link" | Use the link with `?key=` printed when the tutor started |
| "You have already answered this problem" | Expected: after the solution is shown, a second answer is not counted. Click "Next problem" |
| Maths shows as `$$...$$` | Reload the page; check the laptop serves `/static/vendor/katex/` |
| A worked step looks wrong | Screenshot it, note the time and code, and tell the researcher the same day |
| Tutor restarted | Nothing is lost; progress is saved after every action |
| Pupil wants to stop | Let them. Note the code if they or their parent withdraw consent |
