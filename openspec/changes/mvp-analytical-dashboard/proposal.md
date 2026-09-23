# Proposal: MVP Analytical Pipeline and Single-Page Dashboard

## Why

Technical skill demand across data occupations and EU-27 labor markets exhibits substantial variation, but raw skill counts conflate universal baseline tools (e.g., SQL) with role-defining skills (e.g., PyTorch). Building an end-to-end MVP pipeline and single-page dashboard provides an immediate, empirically grounded demonstration of skill prevalence, distinctiveness (lift), and geographic distribution across an audited snapshot of 22,985 EU-27 FreeHire job postings.

## What Changes

- **Controlled Vocabulary & Hybrid Extraction**: Establish canonical technical skills and aliases organized across 5 domains (*Programming languages*, *Databases & data warehouses*, *BI & visualization*, *Cloud & infrastructure*, *ML/AI frameworks & tools*). Extract skills via hybrid precedence (FreeHire native tags first, with regex fallback on descriptions for untagged tools such as Excel and R), recording binary presence per posting.
- **Pure Python Analytical Core (`src/analytics.py`)**: Implement reusable, standalone mathematical functions for:
  - Job-level skill prevalence: $P(\text{skill} \mid \text{category})$ and $P(\text{skill} \mid \text{corpus})$.
  - Skill lift calculation: $\text{Lift} = P(\text{skill} \mid \text{category}) / P(\text{skill} \mid \text{corpus})$.
  - Distinctive-skill filtering: Filter eligibility by $N_{\text{cat}} \ge 20$ postings and $P_{\text{cat}} \ge 1.5\%$; rank eligible skills by lift descending and select the Top 10 with $\text{Lift} > 1.0$.
  - Geographic eligibility threshold: Country composition comparisons restricted to member states with $N \ge 300$ observed postings.
- **Offline Batch Pipeline (`scripts/preprocess.py`)**: Execute an offline batch run using `src/analytics.py` functions to process the 22,985 raw postings and serialize a precomputed `data/processed/analytics_summary.json` artifact for instantaneous app loading.
- **Single-Page Streamlit Dashboard (`app.py`)**: Build a clean, vertically integrated single-page dashboard acting as a thin presentation layer:
  - Top KPI cards: 22,985 postings, 27 EU member states, 5 occupations, 41% seniority metadata coverage.
  - Section 1 (Overview): Occupational composition bar chart and corpus-wide top skills.
  - Section 2 (Category Skill Profiles): Interactive category selector displaying side-by-side ranked horizontal bar charts: Top In-Demand Skills (% prevalence) vs. Most Distinctive Skills (Lift).
  - Section 3 (Geographic Distribution): EU-27 Choropleth map with raw counts across all 27 member states, paired with a 100% stacked bar chart of category composition for qualifying countries ($N \ge 300$) and explicit sample-size context notes.
- **Test Suite (`tests/test_analytics.py`)**: Implement targeted unit tests covering four core areas: hybrid skill extraction, prevalence/lift math, distinctive-skill support/noise filtering, and geographic $N \ge 300$ thresholding.

## Capabilities

### New Capabilities
- `skill-extraction`: Hybrid controlled-vocabulary extraction matching native tags and regex on descriptions across 5 skill categories, recording binary presence per posting.
- `analytics-core`: Pure Python analytical functions for prevalence, lift, distinctive-skill filtering ($N \ge 20, P \ge 1.5\%, \text{Lift} > 1$), and geographic sample-size thresholding ($N \ge 300$).
- `data-pipeline`: Offline batch processing that applies `analytics-core` logic to raw data and outputs `data/processed/analytics_summary.json`.
- `dashboard`: Single-page Streamlit web dashboard rendering precomputed metrics with side-by-side category charts and EU geographic distribution.

### Modified Capabilities
*(None; initial implementation of capabilities)*

## Impact

- **Code structure**: Introduces `src/analytics.py`, `scripts/preprocess.py`, `app.py`, `data/fixtures/skills_vocabulary.json`, and `tests/test_analytics.py`.
- **Data artifacts**: Creates `data/processed/analytics_summary.json`. The raw data file `data/raw/freehire_eu_raw.json` remains frozen and read-only.
- **Dependencies**: Python dependencies include `streamlit`, `pandas`, `plotly`, and `pytest`.

## Future Levels (Post-MVP Change Requests)

The following candidate extensions represent natural follow-up phases that build on the MVP foundation while respecting the project's explicit scope boundaries:

- **2D Quadrant Matrix Scatter Plot (Prevalence vs. Lift)**:
  An interactive scatter plot in the Category Profiles view plotting within-category prevalence against lift, segmented by a reference line at $\text{Lift} = 1.0$. This visual categorizes skills into four archetypes: *Core Pillars* (high prevalence, high lift), *Specialized Drivers* (moderate prevalence, high lift), *Universal Table-Stakes* (high prevalence, low lift), and *Peripheral/Niche* tools.
- **Skill Family Drilldown Filters**:
  Interactive filter controls within the Category Profiles section allowing users to isolate specific technical skill families (*Programming languages*, *Databases & data warehouses*, *BI & visualization*, *Cloud & infrastructure*, *ML/AI frameworks & tools*) to explore within-family prevalence and lift rankings.
- **Regional Grouping & Comparison (EU Geographic Clusters)**:
  Aggregating EU-27 member states into recognized geographic clusters (e.g., Western Europe, Southern Europe, Central & Eastern Europe, Nordics) to analyze occupational composition across larger regional sample sizes alongside individual country figures.
- **Observed Metadata & Seniority Explorations**:
  Descriptive sub-analyses of the 41% observed seniority metadata (e.g., senior vs. mid vs. junior category distributions where present) and remote vs. on-site distributions across occupations, strictly as observed sample summaries without classification modeling or inference.
- **Curated Vocabulary Expansion**:
  Systematically expanding the controlled vocabulary to include emerging libraries, frameworks, or cloud-native tools identified in ongoing corpus audits, maintaining explicit alias normalization and validation.

