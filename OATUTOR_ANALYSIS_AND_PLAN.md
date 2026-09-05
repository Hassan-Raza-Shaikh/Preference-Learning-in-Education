# OATutor-Content — Repository Analysis & Extraction Plan

**Data source:** `CAHLR/OATutor-Content` (GitHub, default branch `main`, ~142 MB)
**Analysis date:** 2026-09-03
**Purpose:** First data source for a math problem → solution-method dataset (SFT + DPO/RLHF for an AI tutor).
**Method:** Full clone inspected locally (52,153 files). All numbers below are measured, not estimated. Where evidence is incomplete it is flagged explicitly.

---

## 0. Executive Summary

- OATutor-Content is a **tutoring content pool**: 13,287 problems, decomposed into 17,761 steps, each step carrying an ordered, dependency-linked **hint + scaffold** pathway that constitutes a scaffolded worked solution.
- **Every step has a stored answer** (0 missing) and **every step has a tutoring file** (0 missing). This is a high-integrity source.
- It covers the systems-of-equations space **completely**: graphing, substitution, elimination, matrices, Gaussian elimination, inverse matrix, and Cramer's Rule — **751 problems** across 28 method-specific lessons in 4 courses.
- **Critical limitation for your goal:** the *solution method is a property of the lesson, not the problem*. Each problem is solved exactly one way (the way its lesson teaches). There are **no multiple solution paths per problem** in this repo — only a single `DefaultPathway`. Multiple-method coverage must come from (a) cross-lesson grouping of equivalent systems, and (b) the LLM-generation phase you already planned.
- **Main cleanup burdens:** ~35% exact-content duplication (same OpenStax problems reused across courses), LaTeX/`$$…$$` normalization, and inline `##figure.gif##` image references.

---

## 1. Repository Structure

```
OATutor-Content/
├── README.md                    # minimal
├── coursePlans.json             # CATALOG: 21 courses → lessons (metadata, skill objectives, chat config)
├── skillModel.json              # MAP: stepId → [skill tags]   (used for Bayesian Knowledge Tracing)
├── bkt-params/
│   ├── defaultBKTParams.json    # per-skill BKT priors (probMastery/Transit/Slip/Guess)
│   └── experimentalBKTParams.json
├── .Rhistory, .DS_Store         # junk, ignore
└── content-pool/                # THE ACTUAL CONTENT — 13,287 problem folders
    └── <problemId>/
        ├── <problemId>.json                                  # problem metadata (the "stem")
        ├── figures/figureN.gif                               # optional images (2,364 gifs, 2,128 referencing files)
        └── steps/
            └── <problemId><a|b|c...>/                         # one folder per sub-step
                ├── <problemId><letter>.json                  # the step question + answer
                └── tutoring/
                    └── <problemId><letter>DefaultPathway.json # ordered hint/scaffold worked solution
```

**What matters vs. what is metadata-only**

| Path | Role | For our dataset |
|---|---|---|
| `content-pool/**/<problem>.json` | Problem stem, title, source, lesson link | **Core** |
| `content-pool/**/steps/**/<step>.json` | Question text + answer + type + choices | **Core** |
| `content-pool/**/tutoring/*DefaultPathway.json` | Scaffolded worked solution (hints + scaffolds) | **Core** |
| `content-pool/**/figures/*.gif` | Figures referenced by `##name.gif##` | Core (for figure-bearing problems) |
| `coursePlans.json` | Course/lesson catalog + method labels via lesson name | **Core metadata** (method inference, subject taxonomy) |
| `skillModel.json` | stepId → skill tags | Useful metadata (skill labels) |
| `bkt-params/*` | Tutor mastery-model params | Not needed (tutor-runtime only) |
| `.Rhistory`, `.DS_Store` | Junk | Ignore |

---

## 2. Data Model

Three linked record types. Linkage is **by filename/path convention and by `lessonId`**, not by explicit foreign keys inside the content files.

### 2.1 Problem (`<problemId>.json`)
```json
{
  "id": "a2a280bgaussian1",
  "title": "Writing the Augmented Matrix for a System of Equations",
  "body": "Write the augmented matrix for the given system of equations.",
  "variabilization": {},                        // template vars — ALWAYS EMPTY in this repo
  "oer": "https://openstax.org/... <OpenStax: College Algebra>",
  "license": "https://creativecommons.org/licenses/by/4.0/ <CC BY 4.0>",
  "lesson": "7.6 Solving Systems with Gaussian Elimination",   // human-readable, encodes METHOD
  "lessonId": "5jWomuQb-zLms-pvKcgRHvn6",       // FK → coursePlans.json lessons[].id
  "courseName": "OpenStax: College Algebra"
}
```
Keys are 100% consistent across the sampled corpus.

### 2.2 Step (`steps/<stepId>/<stepId>.json`)
```json
{
  "id": "a2a280bgaussian1a",
  "stepAnswer": ["$$\\begin{bmatrix}...\\end{bmatrix}$$"],  // ALWAYS present (0 missing)
  "problemType": "MultipleChoice",              // MultipleChoice (7,765) | TextBox (9,996)
  "stepTitle": "$$x+2y-z=3$$ ...",              // the actual question (LaTeX-heavy)
  "stepBody": "",
  "answerType": "string",                       // string (8,600) | arithmetic (9,161)
  "variabilization": {},
  "answerLatex": "$$...$$",                      // present ~78% — rendered answer
  "choices": ["...","...","None of the above"]  // present only for MultipleChoice
}
```

### 2.3 Tutoring pathway (`.../tutoring/<stepId>DefaultPathway.json`)
An **ordered array** of tutoring items forming a DAG (`dependencies` = predecessor item ids). Two item types:

**`hint`** — expository worked-solution step:
```json
{ "id":"...-h1", "type":"hint", "dependencies":[],
  "title":"Definition", "text":"The augmented matrix displays the coefficients...",
  "variabilization":{}, "oer":"...", "license":"..." }
```

**`scaffold`** — an *interactive sub-question* the learner must answer (a mini-problem):
```json
{ "id":"...-h2", "type":"scaffold", "dependencies":["...-h1"],
  "title":"Expected Value", "text":"If our player rolls two dice, how many points...?",
  "problemType":"TextBox", "answerType":"arithmetic",
  "hintAnswer":["$$\\frac{1}{3}$$"],            // scaffold's own answer (0 missing)
  "choices":[...],                              // if scaffold is MultipleChoice
  "subHints":[ { ...nested hint/scaffold... } ] // OPTIONAL recursive children (304 seen)
}
```

Corpus totals: **46,384 hint items, 22,972 scaffold items**; `subHints` present on 304 items (nested one level deep, occasionally more).

### 2.4 Linkage summary
```
coursePlans.json (course → lessons[].id)
        ▲  lessonId
        │
   problem.json ──(path)──▶ steps/<stepId>/ ──(path)──▶ tutoring/<stepId>DefaultPathway.json
        │                        │
   skillModel.json[stepId] ──────┘  (stepId → [skill tags])
```
- **Problem → lesson/course:** `problem.lessonId` matches `coursePlans[].lessons[].id`; `courseName` duplicated on the problem for convenience.
- **Problem → steps:** by directory nesting + id prefix (`<problemId>` + `a/b/c…`). No explicit list inside problem.json — steps are discovered by walking `steps/`.
- **Step → tutoring:** by naming convention `<stepId>DefaultPathway.json`.
- **Step → skills:** `skillModel.json[stepId]`.
- **Text → image:** `##figureN.gif##` token in any `text`/`body`/`stepTitle` resolves to `content-pool/<problemId>/figures/figureN.gif`.

---

## 3. Educational Content (Subjects / Topics / Lessons)

**21 courses** (20 English, 1 Swedish — `Matematik 4`, lang `se`):

| Domain | Courses |
|---|---|
| Algebra | Elementary Algebra (71 lessons), Intermediate Algebra (69), College Algebra (59), Solid Foundations: Algebra (27) |
| Pre-Calc / Trig | OpenStax Pre-Calculus (70), Pre-Calculus Essentials UC Berkeley (10), Solid Foundations: Trigonometry (20) |
| Calculus | OpenStax Calculus Vol 1 (41), SJSU Calculus 1 (28), Solid Foundations: Calculus Part 1 (7) |
| Statistics / Data | Mission College Intro Stats (59), OpenStax Introductory Stats (62), Data 8 Worksheets (7), Combined Data100 Worksheets (12) |
| Physics | OpenStax College Physics (12), University Physics (17), Math Basics for Physics (4) |
| Chemistry | Chemistry 1A Summer Content (7) |
| Developmental (SJSU) | SJSU 1018 (30), SJSU 1019S (27) |

Lessons carry `learningObjectives` = `{skillTag: masteryThreshold}` — **1,238 unique skill tags** across the catalog.

**Most useful lessons for this project:** the Algebra + Pre-Calculus systems chapters (Section 3 of each), enumerated next.

---

## 4. Systems of Equations — Complete Inventory

Method is encoded by the lesson. Every requested method is present. **751 problems** across these 28 lessons:

| Method | Lessons (course · problems) |
|---|---|
| **Graphing** | ElemAlg 5.1 (30) · IntAlg/CollAlg via 2-var lessons |
| **Substitution** | ElemAlg 5.2 (20) |
| **Elimination** | ElemAlg 5.3 (24) |
| **2-variable systems (mixed method)** | IntAlg 4.1 (24) · CollAlg 7.1 (26) · PreCalc 9.1 (29) |
| **3-variable systems** | IntAlg 4.4 (30) · CollAlg 7.2 (27) · PreCalc 9.2 (30) |
| **Matrices / matrix ops** | IntAlg 4.5 (30) · CollAlg 7.5 (30) · PreCalc 9.5 (23) |
| **Gaussian elimination** | CollAlg 7.6 (22) · PreCalc 9.6 (26) |
| **Inverse matrix** | CollAlg 7.7 (24) · PreCalc 9.7 (29) |
| **Cramer's Rule / determinants** | IntAlg 4.6 (30) · CollAlg 7.8 (30) · PreCalc 9.8 (30) |
| **Nonlinear systems** | IntAlg 11.5 (30) · CollAlg 7.3 (29) · PreCalc 9.3 (30) |
| **Applications / mixture** | ElemAlg 5.4 (30), 5.5 (25) · IntAlg 4.2 (30), 4.3 (6) |
| **Systems of inequalities (graphing)** | ElemAlg 5.6 (30) · IntAlg 4.7 (27) |

Named problem-folder families also exist: `a1a538fsystems*`, `a2a280bgaussian*`, `a152fa9gaussian*`, `a1a9374graphExp*`, etc. **332 problem folders** have systems/method keywords in their names — a coarser net than the lessonId mapping (which is authoritative).

> **Evidence gap:** the "Substitution" and "Elimination" method split is clean only in **Elementary Algebra** (dedicated 5.2 / 5.3 lessons). In Intermediate/College/Pre-Calc, the 2-var and 3-var lessons mix methods within one lesson; the specific method per problem must be read from the step/hint text, not the lesson name. Confirm by sampling before relying on lesson-name method labels for those courses.

---

## 5. Dataset Feasibility

| Requirement | Present? | Evidence |
|---|---|---|
| Fully worked solutions | **Yes** | Hint/scaffold pathways = step-by-step derivations (definition → intermediate → answer) |
| Answers only | Yes (as a subset) | `stepAnswer` on every step; `hintAnswer` on every scaffold |
| Tutoring dialogue | **Partial** | Scaffolds are Socratic sub-questions with answers; not free-form multi-turn dialogue |
| Hints | **Yes** | 46,384 hint items |
| Interactive tutoring steps | **Yes** | 22,972 scaffold items (answerable sub-problems, recursively nested via `subHints`) |
| Multiple solution paths **per problem** | **No** | Exactly one `DefaultPathway` per step across the entire corpus (7,142+ files, all `DefaultPathway`) |
| Sufficient for ML training | **Yes, for SFT**; **partially for DPO** | See below |

**SFT:** Directly usable. (problem stem + step question) → (worked hint/scaffold solution + answer) is a clean supervised target, ~17.7k step-level examples.

**DPO/RLHF:** No native preference pairs (no "good vs bad" solutions, no alternate methods to rank). Preference data must be **constructed**: e.g., correct pathway vs. corrupted/omitted-step pathway, or (later) LLM-generated alternate-method solutions ranked against the gold pathway. This repo supplies the *chosen* side; the *rejected* side is future work.

**Multiple-method goal:** Achievable only by combining problems *across* method-lessons (same system, different lesson) or via the planned LLM generation. Flag every extracted record with its single native method so downstream grouping is possible.

---

## 6. Recommended Dataset Schema

Normalize to a **problem-centric JSON** with an ordered step list and a flattened-but-structure-preserving solution tree. One record per problem.

```jsonc
{
  "schema_version": "1.0",
  "source": {
    "dataset": "OATutor-Content",
    "repo": "CAHLR/OATutor-Content",
    "commit": "<git sha>",                    // pin provenance
    "problem_id": "a2a280bgaussian1",
    "path": "content-pool/a2a280bgaussian1"
  },
  "provenance": {
    "oer": "OpenStax: College Algebra",
    "oer_url": "https://openstax.org/...",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/"
  },
  "taxonomy": {
    "course": "OpenStax: College Algebra",
    "lesson_id": "5jWomuQb-zLms-pvKcgRHvn6",
    "lesson": "7.6 Solving Systems with Gaussian Elimination",
    "subject": "algebra",                     // derived
    "topic": "systems_of_equations",          // derived
    "method": ["gaussian_elimination"],       // derived from lesson (+ verified from text)
    "skills": ["..."]                         // from skillModel.json (union over steps)
  },
  "problem": {
    "title": "Writing the Augmented Matrix for a System of Equations",
    "body": "Write the augmented matrix for the given system of equations.",
    "figures": []                             // resolved from ##figure.gif##
  },
  "steps": [
    {
      "step_id": "a2a280bgaussian1a",
      "order": 0,
      "question": "$$x+2y-z=3$$ $$2x-y+2z=6$$ $$x-3y+3z=4$$",
      "problem_type": "MultipleChoice",       // MultipleChoice | TextBox
      "answer_type": "string",                // string | arithmetic
      "choices": ["...","...","None of the above"],
      "answer": ["$$\\begin{bmatrix}...\\end{bmatrix}$$"],
      "answer_latex": "$$...$$",
      "figures": [],
      "solution": [                            // ordered worked solution (tutoring pathway)
        {
          "id": "a2a280bgaussian1a-h1",
          "type": "hint",                      // hint | scaffold
          "depends_on": [],
          "title": "Definition",
          "text": "The augmented matrix displays the coefficients...",
          "scaffold_answer": null,             // set for scaffolds
          "scaffold_choices": null,
          "children": []                       // recursive subHints
        }
      ]
    }
  ],
  "text_format": { "math": "latex_dollar", "image_token": "##name.gif##" },
  "quality_flags": ["empty_tutoring", "figure_missing", "duplicate_of:<id>"]
}
```

**Design rationale**
- **Problem-centric, steps nested:** preserves the problem→step→solution hierarchy the SFT target needs, while keeping each step independently trainable (`step_id`).
- **`solution` keeps the tree** (hints + scaffolds + `children`) rather than collapsing to prose — you can flatten to a linear worked solution for SFT *or* keep scaffolds as interactive turns for tutoring-dialogue SFT. Don't discard structure at extraction time.
- **`method` as a list** so later LLM-generated alternate methods append cleanly to the same problem.
- **`quality_flags`** drive filtering without deleting data.
- Emit **JSONL** (one problem per line) for streaming into training pipelines, plus a small `manifest.json` (counts, commit, schema_version).

**Two derived training views** (generated from the canonical JSONL, not stored twice by hand):
1. `sft_steps.jsonl` — `{prompt: problem+step question, completion: linearized worked solution+answer}`.
2. `sft_dialogue.jsonl` — scaffolds expanded into multi-turn Socratic exchanges.

---

## 7. Extraction Pipeline Architecture

Deterministic, idempotent, commit-pinned. No network at extract time (operate on a pinned clone).

```
[clone@sha] → discover → parse → validate → normalize → link → dedup → assemble → emit → report
```

1. **Discover** — walk `content-pool/*`; for each problem folder, enumerate `steps/*` and tutoring files by convention. Load `coursePlans.json` + `skillModel.json` once into lookup dicts. Ignore `.DS_Store`, `.Rhistory`, `bkt-params/`.
2. **Parse** — strict JSON load with per-file try/except; malformed files → quarantine list, never crash the run.
3. **Validate** — schema check per record type (required keys, types). Assert invariants measured here: step has non-empty `stepAnswer`; MultipleChoice ⇒ non-empty `choices`; tutoring file exists. Downgrade violations to `quality_flags`, don't drop.
4. **Normalize**
   - Math: keep `$$…$$` LaTeX; optionally strip delimiters into a `math`-typed field. Normalize whitespace, unicode (NFC), stray escaped quotes seen in text (e.g. `$$\"2.01...\"$$`).
   - Images: parse `##figureN.gif##`, resolve to `figures/` path, record in `figures[]`, replace token with a stable placeholder.
   - Types: lowercase enums (`problem_type`, `answer_type`).
   - Derive `subject`/`topic`/`method` from a **curated lesson→method map** (start from Section 4; treat mixed-method lessons as `method:["mixed"]` pending text verification).
5. **Link** — attach `lessonId`→lesson/course, `skillModel[stepId]`→skills; build the solution tree from `dependencies` (topological order; detect cycles).
6. **Dedup** — canonical signature = hash of normalized (stepTitle + stepAnswer) sequence. Group duplicates; keep one **primary** (prefer the OpenStax-origin course for stable licensing/provenance), tag the rest `duplicate_of:<primary_id>`. Keep duplicates in a side file; don't hard-delete.
7. **Assemble** — build canonical problem records (Section 6).
8. **Emit** — canonical JSONL + manifest + the two derived training views + a duplicates map + a quarantine file.
9. **Report** — structured log (JSON) with counts at each stage, flag histograms, and a human-readable summary.

**Cross-cutting**
- **Validation:** `pydantic`/`jsonschema` models for the three input types and the output schema.
- **Logging:** structured (`structlog`/stdlib JSON), one line per problem on error, aggregate metrics at end.
- **Error handling:** fail-soft per record, fail-hard on missing top-level catalogs; quarantine + continue.
- **Testing:** unit tests on ~10 hand-picked fixture problems (MC, TextBox, scaffold, nested subHints, figure-bearing, empty-tutoring, cross-course duplicate); golden-output snapshot tests; property tests (every emitted step has an answer; every `depends_on` id exists).
- **Idempotency/provenance:** pin the commit SHA; same input ⇒ byte-identical output. Record SHA in every record.
- **Determinism:** sort keys and problem order; stable hashing.

---

## 8. Risks & Open Questions

| # | Risk | Severity | Evidence / Mitigation |
|---|---|---|---|
| R1 | **~35% duplicate content** — 4,715 problems in 2,180 exact-content groups; 2,059 groups span multiple courses (same OpenStax item reused). | **High** | Measured. Dedup by content signature; keep primary + `duplicate_of`. Affects the systems set too (e.g. `gaussian30` in ElemAlg & SJSU 1019S). |
| R2 | **No multiple solution methods per problem** — single `DefaultPathway` everywhere. | **High** (vs. project goal) | Measured (all 7k+ tutoring files are `DefaultPathway`). Method comes from lesson; multi-method is future LLM work. |
| R3 | **380 empty tutoring arrays** (2.1% of steps): answer present, no worked solution. | Medium | Measured. Flag `empty_tutoring`; exclude from worked-solution SFT, keep for answer-only tasks. |
| R4 | **LaTeX/formatting inconsistency** — `$$…$$` everywhere, plus stray escaped quotes, mixed inline/display, matrices as LaTeX. | Medium | Normalization pass; keep a `math` format tag. Don't attempt to "solve" LaTeX. |
| R5 | **Inline image dependency** — `##figureN.gif##` in 2,128 files; solution may be unreadable without the figure. | Medium | Resolve to `figures/` path; flag `figure_missing` if absent. Graphing lessons especially depend on images. |
| R6 | **Method labels unreliable in mixed lessons** (IntAlg/CollAlg/PreCalc 2-var & 3-var lessons combine methods). | Medium | Verify method from hint text for those; label `mixed` until confirmed. |
| R7 | **46 steps with empty title AND body** (question text missing). | Low | Measured. Flag and exclude. |
| R8 | **Implicit linkage** (path/naming conventions, no FKs inside files); a rename breaks joins. | Low | Pin commit; validate every join; quarantine orphans (0 found now). |
| R9 | **Non-English content** — `Matematik 4` (Swedish). | Low | Tag `language`; filter or route to translation. |
| R10 | **Scaffold recursion depth** (`subHints`) can nest; naive flatteners lose structure. | Low | Recursive parser; cap/measure max depth; preserve tree. |
| R11 | **Cross-domain answer types** — `arithmetic` vs `string`; matrices/inequalities as strings. | Low | Keep `answer_type`; don't coerce. |
| R12 | **License/attribution obligation** — CC BY 4.0 requires attribution; OER field must be preserved. | Low (compliance) | Carry `provenance` in every record; never drop `oer`/`license`. |

**Open questions to resolve before/at implementation (evidence currently missing):**
- Q1: Are `defaultBKTParams.json` and `experimentalBKTParams.json` identical? (Same byte size 195,309 — likely; not needed for the dataset, low priority.)
- Q2: For mixed-method lessons, is the per-problem method recoverable reliably from hint text? (Needs a sampling study — R6.)
- Q3: Do any `subHints` nest deeper than one level? (Seen at 1 level; parser must handle N.)
- Q4: Are there answer-representation edge cases (e.g., multiple acceptable answers, ranges, ordered pairs vs sets)? (Sample `stepAnswer` arrays with length > 1.)

---

## 9. Implementation Roadmap (Milestones)

Ordered by dependency. Complexity: **S** = <½ day, **M** = ~1 day, **L** = 2–3 days.

### M0 — Environment & pinned corpus
- **Objective:** Reproducible access to a fixed snapshot.
- **Output:** Pinned clone at a recorded SHA; `requirements.txt` (pydantic, structlog, pytest); repo README for the pipeline.
- **Dependencies:** none.
- **Complexity:** S.
- **Order:** 1.

### M1 — Corpus census & schema confirmation
- **Objective:** Reproduce and lock the measured facts (counts, key sets, enums) as a machine-checked baseline; resolve Q3/Q4.
- **Output:** `census.json` (all counts in this doc), confirmed input JSON schemas for problem/step/tutoring.
- **Dependencies:** M0.
- **Complexity:** M.
- **Order:** 2.

### M2 — Input models & parser (fail-soft)
- **Objective:** Typed loaders for the 3 record types + catalogs, with quarantine.
- **Output:** `models.py`, `parse.py`, quarantine log; unit tests on fixtures.
- **Dependencies:** M1.
- **Complexity:** M.
- **Order:** 3.

### M3 — Linker (steps, tutoring tree, lessons, skills)
- **Objective:** Assemble problem→steps→solution-tree; join lesson/course/skill; topological ordering of hint DAG incl. recursive `subHints`.
- **Output:** In-memory canonical objects; cycle/orphan detector.
- **Dependencies:** M2.
- **Complexity:** L.
- **Order:** 4.

### M4 — Normalizer (math, images, enums, taxonomy)
- **Objective:** LaTeX/whitespace/unicode normalization; `##figure##` resolution; lesson→subject/topic/method map.
- **Output:** `normalize.py`, `lesson_method_map.yaml`, figure-resolution report.
- **Dependencies:** M3; needs R6 sampling for method map.
- **Complexity:** L.
- **Order:** 5.

### M5 — Deduplication
- **Objective:** Content-signature grouping; choose primaries; tag duplicates.
- **Output:** `duplicates_map.json`; `duplicate_of` flags on records.
- **Dependencies:** M3 (normalized text improves matching → run after M4).
- **Complexity:** M.
- **Order:** 6.

### M6 — Validator & quality flags
- **Objective:** Enforce output invariants; attach `quality_flags` (empty_tutoring, figure_missing, empty_question, language, duplicate).
- **Output:** `validate.py`; flag histogram in the run report.
- **Dependencies:** M3–M5.
- **Complexity:** M.
- **Order:** 7.

### M7 — Emitters (canonical + training views + manifest)
- **Objective:** Write `oatutor.jsonl`, `sft_steps.jsonl`, `sft_dialogue.jsonl`, `manifest.json`, quarantine + duplicates side files.
- **Output:** The dataset artifacts, deterministic & commit-pinned.
- **Dependencies:** M6.
- **Complexity:** M.
- **Order:** 8.

### M8 — Test suite & CI gate
- **Objective:** Lock correctness: golden snapshots, property tests, fixture coverage of every edge case.
- **Output:** `tests/`, CI config; green gate on the fixture set.
- **Dependencies:** M2–M7 (grows alongside).
- **Complexity:** M.
- **Order:** 9 (developed continuously, hardened here).

### M9 — Systems-of-equations focused slice & feasibility report
- **Objective:** Extract the 751-problem systems subset; verify method labels (R6); produce a quality report for the tutoring team.
- **Output:** `systems_of_equations.jsonl` + report (method coverage, dup rate, empty-tutoring rate, figure dependence).
- **Dependencies:** M7, M8.
- **Complexity:** M.
- **Order:** 10.

### M10 — Integration hooks for downstream sources & LLM method-generation
- **Objective:** Freeze the canonical schema as the merge target for other OER sources and for LLM-generated alternate methods (append to `taxonomy.method` + `steps[].solution`).
- **Output:** Schema doc v1.0, `method` extension contract, sample LLM-augmented record.
- **Dependencies:** M7.
- **Complexity:** S–M.
- **Order:** 11.

**Recommended build order:** M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7 → (M8 alongside 2–7) → M9 → M10.
**Critical path:** M3 (linker) and M4 (normalizer) are the two hardest and gate everything downstream — staff them first.

---

## Appendix A — Key measured numbers
- Files: 52,153 total; content-pool JSON: 48,809.
- Problems: 13,287. Steps: 17,761 (~1.34 steps/problem). GIFs: 2,364 (referenced by 2,128 files).
- Tutoring items: 46,384 hint + 22,972 scaffold; 304 with `subHints`.
- problemType: TextBox 9,996 / MultipleChoice 7,765. answerType: arithmetic 9,161 / string 8,600.
- Integrity: 0 steps missing answers, 0 MC missing choices, 0 steps missing tutoring, 0 duplicate ids, 0 problems missing steps.
- Gaps: 380 empty tutoring arrays; 46 empty-question steps; 4 empty title+body problems.
- Duplication: 2,180 exact-content groups / 4,715 problems (~35%); 2,059 groups cross-course.
- Systems-of-equations target subset: 751 problems / 28 lessons / 4 courses.
- Courses: 21 (20 en, 1 se); 1,238 unique skill tags.
