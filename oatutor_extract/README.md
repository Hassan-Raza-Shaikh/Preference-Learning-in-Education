# OATutor-Content extractor

Turns a local clone of [`CAHLR/OATutor-Content`](https://github.com/CAHLR/OATutor-Content)
into a clean, ML-ready dataset. Deterministic, fail-soft, and commit-pinned.

## Run

```bash
# 1. get the source content (once)
git clone https://github.com/CAHLR/OATutor-Content.git

# 2. extract
python -m oatutor_extract.extract --content-root ./OATutor-Content --out-dir data -v

# 3. tests
python -m pytest tests/ -q
```

## Outputs (in `--out-dir`)

| File | What |
|---|---|
| `oatutor.jsonl` | Canonical dataset — one problem per line (all 13,287). |
| `oatutor_systems.jsonl` | Systems-of-equations slice (751 problems). |
| `sft_steps.jsonl` | Ready-to-train view: `{prompt, completion, meta}` per step with a worked solution (duplicates excluded). |
| `by_method/<method>.jsonl` | Canonical records split by solution method (`substitution`, `elimination`, `graphing`, `matrices`, `gaussian_elimination`, `inverse_matrix`, `cramers_rule`, `mixed`; `unspecified` = non-systems). Duplicates excluded. |
| `by_step_count/<n>_step.jsonl` | Systems records grouped by number of steps. Duplicates excluded. |
| `manifest.json` | Counts, source commit, quality-flag histogram, per-method + per-step-count counts. |
| `duplicates.json` | `duplicate_problem_id -> primary_problem_id`. |
| `quarantine.json` | Files that failed to parse (currently none). |

## Format choice

**JSONL** for the datasets: one self-contained record per line — streams into training,
shards trivially, filters with `grep`/`jq`, and diffs cleanly in git. `manifest.json`
and `duplicates.json` are plain JSON because they're read whole.

## Canonical schema (v1.0)

Problem-centric, with steps nested and each step's worked solution kept as a tree
(hints + interactive scaffolds, `children` = nested subHints). See
`../OATUTOR_ANALYSIS_AND_PLAN.md` §6 for the annotated schema.

Key conventions:
- Math is LaTeX inside `$$…$$` (`text_format.math = "latex_dollar"`).
- Images are referenced inline as `##name.gif##`; files live in the source
  `content-pool/<id>/figures/`. `problem.figures` lists what's available.
- `taxonomy.method` is a **list** so LLM-generated alternate methods can be appended
  to the same problem later.

## Quality flags (per record)

| Flag | Meaning | Suggested handling |
|---|---|---|
| `figure_dependent` | Question/answer/solution references an image | Filter for text-only training, or route to multimodal/OCR |
| `empty_tutoring` | A step has an answer but no worked solution | Exclude from worked-solution SFT; fine for answer-only |
| `empty_question` | Step has no question text | Exclude |
| `empty_problem_stem` | Problem title+body both empty (question is in steps) | Usually fine |
| `unordered_dependencies` | Tutoring items form a cycle / odd cross-ref | Original order kept, nothing lost |
| `figure_missing` | An `##x.gif##` reference has no file | Inspect (only 3 in corpus) |
| `duplicate_of:<id>` | Exact step-content duplicate of another problem | Excluded from `sft_steps.jsonl` |

## Notes / limits

- **One method per problem.** The source stores a single `DefaultPathway`; the method
  comes from the lesson. Multi-method coverage is future work (LLM generation), and the
  schema is built to accept it.
- **Mixed-method lessons.** For the generic two-/three-variable lessons the method is
  labelled `["mixed"]` — verify from solution text before treating as a hard label.

---

## Multi-method generation (`multimethod.py`)

Generates, for OATutor problems that **state a linear system in text**, a verified
solution by every applicable method, plus DPO preference pairs. Questions are taken
**verbatim** from OATutor — only solutions are generated, and every solution is
computed with sympy and checked by back-substitution. Nothing unverified is written.

```bash
python -m oatutor_extract.multimethod --systems data/oatutor_systems.jsonl --out-dir data
python tests/verify_multimethod.py          # independent 3-way re-verification
```

### Outputs (`data/multimethod/`)
| File | What |
|---|---|
| `systems_multimethod.jsonl` | One system + all verified methods (164 systems). |
| `sft_multimethod.jsonl` | One `{prompt, completion}` per verified method (811). |
| `preference_pairs.jsonl` | DPO `{prompt, chosen, rejected, meta}` (811). |
| `manifest.json` | Per-method verification counts and skip reasons. |

### Methods
`substitution`, `elimination`, `graphing` (2-var); `cramers_rule`, `inverse_matrix`,
`gaussian_elimination` (2- and 3-var). Each system gets every applicable method.

### Correctness guarantees (why it can't hallucinate)
- Equations parsed from the real question → sympy `linsolve`.
- Each method's steps are computed from actual intermediate values (not free text).
- Each final answer is verified (i) == reference solution and (ii) satisfies every
  original equation. `tests/verify_multimethod.py` re-derives everything independently
  (three solvers: sympy linsolve, sympy solve, numpy float) and checks provenance
  against the original OATutor question. Latest run: **2,925 assertions, 0 failures.**
- DPO `rejected` = a realistic student-error perturbation (sign flip / swap / off-by-one),
  **verified not to satisfy the system**. Independent judge separates chosen from
  rejected 811/811 (100%), with chosen/rejected near-equal length (no length artifact).

### Scope / honesty
- Covers the 164 systems (of 751) that state a parseable, uniquely-solvable linear
  system in text. Skipped: figure-only systems (equations in images), matrix-operation
  tasks, word problems, and singular/inconsistent systems (27).
- These are *verified* multi-method solutions — the trustworthy core to build on before
  any broader (and necessarily less certain) generation.
