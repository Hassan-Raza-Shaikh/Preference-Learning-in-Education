# Literature search log for the paper

*All searches were run on 2026-11-27 by Claude Code (an AI assistant), in a cloud session.
This log is what the paper's novelty and related-work statements rest on. It is not a
systematic review.*

## 1. What was searched

The tool was a general web search engine (US results). All queries were run once, in
"standard" mode.

| # | Query (exact) | What it found that matters |
|---|---|---|
| 1 | Pardos Bhandari ChatGPT generated algebra hints learning gains errors OATutor | Pardos & Bhandari 2023 (arXiv) and 2024 (PLOS ONE) |
| 2 | Doroudi Aleven Brunskill "Where's the reward" review reinforcement learning instructional sequencing | Doroudi et al. 2019 |
| 3 | Salden Aleven Schwonke Renkl expertise reversal effect worked examples adaptive fading tutored problem solving | Salden et al. 2010 |
| 4 | learner control meta-analysis educational technology achievement Karich Burns Maki | Karich et al. 2014 |
| 5 | Kirschner van Merriënboer "Do learners really know best" urban legends in education | Kirschner & van Merriënboer 2013 |
| 6 | multi-armed bandit select hints or explanations intelligent tutoring system personalization student | Schmucker et al. 2025; bandit hint-selection work |
| 7 | Schmucker contextual bandit hints one million students personalization population policy results arXiv 2508.00270 | Schmucker et al. 2025 |
| 8 | Doroudi robust evaluation matrix offline evaluation instructional policies simulated students learning at scale 2017 | Doroudi et al. 2017 |
| 9 | LLM math tutor computer algebra system verify solution steps hallucination sympy hints correctness | SymPy-verification preprints (SymCode; stepwise verification); not cited |
| 10 | learner choice worked examples versus problems self-regulated selection learning outcomes experiment | Foster et al. 2018, van Harsel et al. 2022 (search summaries only; not cited) |
| 11 | student preference for type of help hints versus learning effectiveness intelligent tutoring system study | No study directly comparing stated preference and learning gains was surfaced |
| 12 | OATutor open-source adaptive tutoring system curated content library Pardos CHI 2023 | Pardos et al. 2023 |
| 13 | Smaug DPO-Positive Pal 2024 failure mode DPO reduces likelihood of preferred response small edit distance math | Pal et al. 2024 |
| 14 | iterative reasoning preference optimization Pang 2024 DPO NLL term math reasoning correct incorrect pairs | Pang et al. 2024 |
| 15 | simulation model when does learner control help individual differences accuracy of learner self-assessment choice | Mihalca et al. 2017; no simulation paper surfaced |
| 16 | language model solve system of linear equations requested method substitution elimination Cramer fine-tuning multiple solution methods | Nothing on LLMs; only textbook pages |
| 17 | "learner control" versus adaptive system choice of instructional support meta-analysis intelligent tutoring 2025 student choice | Meta-analyses referenced only in snippets; not cited |
| 18 | verified worked solutions computer algebra generated step-by-step explanations intelligent tutoring correct by construction LLM hints | LLM-accuracy studies; LeanTutor (title only); not cited |
| 19 | learner control effectiveness moderated by absolute accuracy metacognitive judgments genetics problem solving 86 undergraduates full restricted learner control | Mihalca et al. 2017 |
| 20 | Qwen2.5-Math technical report math expert model self-improvement 2024 arXiv | Yang et al. 2024 |

## 2. What was opened, and how far each cited source was read

**Bibliographic check.** Every journal or proceedings entry in `refs.bib` was checked
against its Crossref record (title, authors, venue, year, volume, issue, pages, DOI). Every
arXiv entry was checked against its arXiv abstract page. The one exception is the page
range of Thompson (1933), which Crossref gives only as "285", so `refs.bib` omits pages.

| Source | How far it was read | Used in the paper for |
|---|---|---|
| Pardos & Bhandari 2024 (PLOS ONE) | **abstract** (Crossref abstract field) | 32% of problems failed quality checks; self-consistency reduces this to nearly 0% for algebra; N = 274 |
| Pardos & Bhandari 2023 (arXiv) | **abstract** | 70% of ChatGPT hints passed manual quality checks |
| Karich, Burns & Maki 2014 | **abstract** (Crossref) | overall learner-control effect "almost zero (g = 0.05)" |
| Schmucker et al. 2025 | **abstract** (arXiv) | personalised (contextual-bandit) policies often no better than well-optimised population policies |
| Pal et al. 2024 | **abstract** (arXiv) | DPO can reduce the likelihood of preferred responses, especially when pairs have low edit distance |
| Pang et al. 2024 | **abstract** (arXiv) | an added NLL term was "crucial" for DPO on reasoning |
| Rafailov et al. 2023; Hu et al. 2021; Yang et al. 2024; Qwen Team 2024 | **abstract** | method and model descriptions only |
| Russo et al. 2018; Meurer et al. 2017 | **abstract** (Crossref) | method and software descriptions only |
| Pashler et al. 2008 | **abstract**, partial (Crossref) | the meshing hypothesis and the evidence criterion |
| Salden et al. 2010 | **bibliographic record + search summaries only** (Springer page blocked) | adaptive vs fixed fading of worked examples in a tutor (general description only) |
| Doroudi et al. 2019 | **bibliographic record + search summaries only** (Springer page blocked) | review of RL for instructional sequencing (general description only) |
| Doroudi et al. 2017 | **bibliographic record + search summaries only** | mismatch between the student model used to derive a policy and the one used to evaluate it |
| Mihalca et al. 2017 | **bibliographic record + search summaries only** (Springer page blocked) | metacognitive accuracy moderating learner-control effectiveness (general description only) |
| Kirschner & van Merriënboer 2013 | **bibliographic record + repository page (no abstract) + search summaries** | "learners know best" legends (general description only) |
| Kalyuga et al. 2003; Renkl & Atkinson 2003 | **bibliographic record only** | the expertise-reversal effect and fading (textbook-level background) |
| Corbett & Anderson 1995 | **bibliographic record only** | the BKT model (standard background) |
| Pardos et al. 2023 (OATutor) | **bibliographic record + search summaries + the OATutor content repository itself** | the data source |

## 3. What could not be searched or opened

- **Blocked:**
  - Springer article pages (a JavaScript "client challenge" page);
  - PubMed Central (a reCAPTCHA page);
  - Taylor & Francis and SAGE full texts (not attempted: not on the network allowlist).
- **Not searched:** Google Scholar, ERIC, ACM Digital Library, IEEE Xplore, Semantic Scholar,
  and the AIED / EDM / L@S / BEA proceedings indexes.
- **Not complete:** the search was not systematic, and no forward or backward citation
  chasing was done.

## 4. Conclusions, within what was opened

- **Consistent with prior work (not claimed as new):**
  - **DPO harming small models on near-identical correct/incorrect pairs** is consistent
    with the failure mode described by Pal et al. 2024 and with Pang et al. 2024.
  - **Personalised bandits failing to beat population policies** agrees with the
    large-scale, real-student evidence of Schmucker et al. 2025.
  - **Mastery-based fading beating fixed worked examples** re-finds, in simulation, the
    direction reported for real students by Salden et al. 2010.
  - **Learner choice depending on whether preferences track what helps** is a formal
    version of the moderator reported by Mihalca et al. 2017, and fits the near-zero
    average effect in Karich et al. 2014.
- **Not found in the sources that loaded:**
  1. Fine-tuning language models to solve linear systems by a requested method, with
     computer-algebra-verified multi-method targets (query 16 found nothing relevant).
  2. A tutor design that records stated preference ("liked") and efficacy ("worked") as
     separate signals and uses a simulation to map when learner choice should help.

  Absence from this search is **not** evidence of novelty: several major indexes were not
  searched, and some sources could not be opened (section 3).
