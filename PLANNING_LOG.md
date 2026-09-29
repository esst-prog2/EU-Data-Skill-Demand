# Planning Log

## 2026-09-22: OpenSpec Propose Changes for the MVP
- 2026-09-22: Skill extraction uses a hybrid approach (native tags prioritized, description regex fallback) across 5 categories: Programming languages, Databases & data warehouses, BI & visualization, Cloud & infrastructure, ML/AI frameworks & tools. (Decided by: User)
- 2026-09-22: Distinctive skill ranking requires at least 20 postings and at least 1.5% within-category prevalence (N_cat >= 20, P_cat >= 1.5%). (Decided by: User, proposed by Agent)
- 2026-09-22: Data pipeline uses offline batch preprocessing to produce processed artifacts for dashboard loading. (Decided by: User)
- 2026-09-22: Dashboard is a single-page Streamlit application with all sections and visuals displayed on one page rather than multiple tabs. (Decided by: User)
- 2026-09-22: Category skill profile was initially planned as side-by-side ranked bar charts with a 2D quadrant matrix and skill-family filter. Superseded by the MVP decision below: both additions are deferred. (Decided by: User, proposed by Agent)
- 2026-09-22: For the MVP, category skill profiles will include only the side-by-side ranked bar charts.
- 2026-09-22: Analytical functions remain in `src/analytics.py` (called by preprocessing and test suites), keeping Streamlit as a thin presentation layer. (Decided by: User)
- 2026-09-22: Distinctive-skill ranking eligibility is strictly N >= 20 postings AND within-category prevalence >= 1.5%; eligible skills are ranked by lift and display Top 10 with lift > 1. (Decided by: User)
- 2026-09-22: Test suite covers 4 distinct pytest areas: hybrid skill extraction, prevalence/lift calculation, distinctive-skill filtering, and geographic N >= 300 thresholding. (Decided by: User)
- 2026-09-23: Documented potential post-MVP candidate change requests in proposal.md (e.g., 2D quadrant scatter plot, regional filtering, and metadata breakdowns). (Decided by: User)

## 2026-09-29: Sensitivity Analysis Changes
- 2026-09-29: Evaluated distinctive-skill ranking sensitivity across a 25-combination grid (`min_count` in `[5, 10, 20, 30, 50]` and `min_prevalence` in `[0.5%, 1.0%, 1.5%, 2.0%, 3.0%]`) on the 22,985-posting EU-27 snapshot and retained the `N >= 20` and `prevalence >= 1.5%` heuristic cutoffs without changing the MVP methodology. (Decided by: User)
- 2026-09-29: Added reproducible sensitivity-analysis artifacts (`analysis/sensitivity_analysis.py` and `analysis/sensitivity_report.md`) documenting the empirical trade-offs of lowering vs. raising the support thresholds across unequal category sizes. (Decided by: User, proposed by Agent)

## 2026-09-29: Data Collection Refresh
- 2026-09-29: The FreeHire collector was switched from `/api/v1/jobs/search` to `/api/v1/agent/jobs/search` so the refreshed snapshot contains the full available job descriptions rather than the approximately 1,000-character search-preview descriptions. (Decided by: User, proposed by Agent)
- 2026-09-29: `description_format=text` was selected to retain complete descriptions without the large HTML overhead; request delay was increased to 0.25 seconds and HTTP 429 responses now respect `Retry-After` before retrying. (Decided by: User, proposed by Agent)
- 2026-09-29: The refreshed EU-27 five-category snapshot contains 23,138 unique postings, matching the live FreeHire facet total after completing the initially timed-out NL/Data Analytics query. (Decided by: User)
- 2026-09-29: The retained project snapshot contains only the fields required by the current preprocessing, analytics, sensitivity-analysis, tests, and validation workflows, keeping the full-text dataset below GitHub's 100 MiB single-file limit while preserving the existing `data/raw/freehire_eu_raw.json` path. (Decided by: User)
- 2026-09-29: Updated the general project description in `AGENTS.md` from the previous 22,985-posting snapshot to the refreshed 23,138-posting snapshot. (Decided by: User)
- 2026-09-29: Updated the Streamlit app's user-facing snapshot references in `app.py` from 22,985 to 23,138 after the dataset refresh. (Decided by: User)