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


