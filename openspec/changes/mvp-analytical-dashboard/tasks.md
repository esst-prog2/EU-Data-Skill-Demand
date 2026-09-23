# Tasks: MVP Analytical Pipeline and Single-Page Dashboard

## 1. Controlled Vocabulary & Environment Setup

- [x] 1.1 Create `data/fixtures/skills_vocabulary.json` containing canonical skills and aliases organized across the 5 domains (Programming languages, Databases & data warehouses, BI & visualization, Cloud & infrastructure, ML/AI frameworks & tools) and verify file validity.
- [x] 1.2 Verify Python test and dashboard dependencies (`pytest`, `streamlit`, `pandas`, `plotly`) in the virtual environment.

## 2. Analytical Core & Test Suite

- [x] 2.1 Implement pure-Python functions in `src/analytics.py` for skill extraction, prevalence, lift, distinctive-skill filtering ($N_{\text{cat}} \ge 20$, $P_{\text{cat}} \ge 1.5\%$, Top 10 with $\text{Lift} > 1.0$), and geographic thresholding ($N \ge 300$).
- [x] 2.2 Implement `tests/test_analytics.py` covering the 4 designated pytest areas (hybrid skill extraction, prevalence/lift math, distinctive-skill filtering, geographic $N \ge 300$ thresholding) and verify that all unit tests pass with `pytest`.

## 3. Offline Batch Preprocessing Pipeline

- [x] 3.1 Implement `scripts/preprocess.py` to load `data/raw/freehire_eu_raw.json`, execute hybrid extraction and analytical calculations via `src/analytics.py`, and format the summary metrics.
- [x] 3.2 Run `python scripts/preprocess.py` to generate `data/processed/analytics_summary.json` and verify that the output artifact contains all corpus KPIs, category metrics, and country breakdowns.

## 4. Single-Page Streamlit Dashboard

- [x] 4.1 Implement `app.py` rendering the single-page dashboard with KPI cards, Section 1 Market Overview, Section 2 Side-by-Side Occupational Profiles (Prevalence vs Distinctiveness), and Section 3 Geographic Distribution (EU-27 map + $N \ge 300$ stacked bar chart).
- [x] 4.2 Run end-to-end smoke verification on the dashboard to ensure fast startup (<500ms) and clean visual rendering.

