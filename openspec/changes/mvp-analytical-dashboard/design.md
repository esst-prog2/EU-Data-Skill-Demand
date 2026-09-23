# Design: MVP Analytical Pipeline and Single-Page Dashboard

## Context

See `proposal.md` for background motivation and high-level scope.
The project operates on an audited, frozen snapshot of 22,985 EU-27 job postings (`data/raw/freehire_eu_raw.json`). In its raw state, 94.2% of postings have native `skills` arrays, but critical tools like `Excel` and single-letter `R` are unrepresented in native tags and reside only in raw `description` text. Furthermore, category sizes vary by more than an order of magnitude (from 15,090 in `data_engineering` to 1,132 in `ml_ai`).

## Goals / Non-Goals

**Goals:**
- Implement reusable, pure-Python analytical logic in `src/analytics.py` for prevalence, lift, support-based distinctive skill filtering, and geographic thresholding.
- Implement an offline batch preprocessing script (`scripts/preprocess.py`) producing `data/processed/analytics_summary.json`.
- Provide an interactive, single-page Streamlit dashboard (`app.py`) as a thin presentation layer consuming the precomputed artifact.
- Implement automated unit tests across 4 targeted pytest suites validating mathematical and filtering behaviors.

**Non-Goals:**
- Interactive 2D quadrant scatter plot (deferred to post-MVP phase).
- On-the-fly regex extraction or heavy metric computations during Streamlit startup.
- Machine learning models for custom occupational or seniority classification.
- Per-skill breakdown by country (no skill $\times$ country matrix).
- Personalized skill-gap scoring or CV matching.

## Decisions

### Decision 1: Architecture & Separation of Concerns
- **Approach**: Pure Python analytical functions live in `src/analytics.py`. The offline batch script `scripts/preprocess.py` imports these functions to process raw data and produce `data/processed/analytics_summary.json`. The Streamlit app `app.py` serves strictly as a presentation layer reading the summary JSON.
- **Rationale**: Decoupling analytical math from Streamlit ensures the core logic is 100% testable via `pytest` without spinning up a browser or web server.
- **Alternatives considered**: Embedding analytical computations directly into `scripts/preprocess.py` or inside Streamlit `@st.cache_data`. Rejected because it impairs testability and bloats the UI layer.

### Decision 2: Distinctive-Skill Rule & Noise Filtering
- **Approach**: Two-stage rule:
  1. Primary eligibility: $N_{\text{cat}} \ge 20$ postings AND $P(\text{skill} \mid \text{category}) \ge 1.5\%$.
  2. Ranking: Eligible skills are sorted by $\text{Lift}$ descending; up to Top 10 with $\text{Lift} > 1.0$ are selected.
- **Rationale**: Eliminates spurious high-lift anomalies from rare single-mention skills in smaller categories (e.g. `ml_ai` with $N=1,132$) while ensuring only true distinctive drivers ($\text{Lift} > 1.0$) appear in the ranking.
- **Alternatives considered**: Filtering strictly on $\text{Lift} > 1.0$ without sample support checks. Rejected because a skill appearing 3 times in ML/AI could otherwise falsely top the distinctiveness chart with an artificial $20\times$ lift.

### Decision 3: Hybrid Skill Extraction
- **Approach**: Maintain a curated JSON vocabulary in `data/fixtures/skills_vocabulary.json` spanning 5 categories (*Programming languages*, *Databases & data warehouses*, *BI & visualization*, *Cloud & infrastructure*, *ML/AI frameworks & tools*). Match canonical names and aliases against native tags first; if a vocabulary item has no native tag match, evaluate bounded regex against `description`.
- **Rationale**: Matches 94% of skills instantly via native tags while capturing essential tools like Excel and R that lack native tags.
- **Alternatives considered**: Running regex scanning exclusively across all 23,000 descriptions. Rejected due to slower execution and higher false-positive risk.

### Decision 4: Single-Page Dashboard Experience
- **Approach**: Streamlit dashboard renders all sections top-to-bottom:
  1. Header and 4 KPI cards (22,985 postings, 27 EU member states, 5 occupations, 41% seniority metadata coverage).
  2. Section 1 (Overview): Occupational category composition horizontal bar and corpus top skills.
  3. Section 2 (Category Profiles): Category selector updating side-by-side Top 10 In-Demand (% prevalence) vs. Top 10 Distinctive (Lift) horizontal bar charts.
  4. Section 3 (Geographic View): EU-27 Choropleth map with raw counts + 100% stacked bar chart for qualifying countries ($N \ge 300$), with a clear callout explaining that countries with $N < 300$ are shown on the map but excluded from composition comparisons.

### Decision 5: Test Suite Organization
- **Approach**: Organize tests in `tests/test_analytics.py` across 4 core areas:
  1. Hybrid skill extraction (native tags, description regex, alias normalization, binary deduplication).
  2. Prevalence and lift math (formula verification, boundary cases 0% and 100%).
  3. Distinctive-skill filtering (enforcing $N \ge 20$, $P \ge 1.5\%$, and $\text{Lift} > 1.0$).
  4. Geographic thresholding ($N \ge 300$ partition).

## Risks / Trade-offs

- **[Risk] Regex false positives for single-letter or common words (e.g., `R` or `Go`)**
  $\to$ *Mitigation*: Restrict regex pattern for `R` to unambiguous token boundaries (`\b[Rr]\b|\b[Rr]\s*(?:programming|scripting|studio)\b`) and test extensively.
- **[Risk] Preprocessed JSON payload size and browser latency**
  $\to$ *Mitigation*: Pre-aggregate metrics in `scripts/preprocess.py` so `analytics_summary.json` contains only final chart arrays and tables (~100–200 KB), guaranteeing $<100$ ms load times in Streamlit.
- **[Risk] Discrepancies between offline summary and analytical formulas**
  $\to$ *Mitigation*: `scripts/preprocess.py` directly calls functions from `src/analytics.py`, maintaining a single source of truth for all mathematical logic.

