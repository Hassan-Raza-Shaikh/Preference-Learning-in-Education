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
2. Prepare **learner codes**, one per pupil, such as `7B-01` … `7B-30`. Keep the code↔name
   list on paper or in the school's system; never type names into the tutor.
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

## 4. Answer format pupils can use

`x=2, y=-1/3`, or `(2, -1/3)`, or `x = 0.5; y = 4`. Fractions must be exact: `1/3`, not
`0.333`. If the tutor can't read an answer, it says how to type it, and nothing is recorded
except that the answer could not be read.

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| Pupil's code rejected | Codes may contain only letters, digits, `-` and `_` (no spaces) |
| Maths shows as `$$...$$` | Reload the page; check the laptop serves `/static/vendor/katex/` |
| A worked step looks wrong | Screenshot it, note the time and code, and tell the researcher the same day |
| Tutor restarted | Nothing is lost; progress is saved after every action |
| Pupil wants to stop | Let them. Note the code if they or their parent withdraw consent |
