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
- 2026-09-29: For the HW4 skill-label validation spike ("How many of the skill labels are true?"), deterministically sample 50 postings total (10 per occupational category) from the refreshed 23,138-posting `data/raw/freehire_eu_raw.json` dataset using random seed `20260929` via `analysis/build_spike_sample.py` into `analysis/spike_sample.json`. (Decided by: User)
- 2026-09-30: Created `analysis/spike_validation.xlsx` from `analysis/spike_sample.json` with 50 annotation rows, 8 identification/text columns (`sample_id`, `category`, `country`, `title`, `company`, `public_slug`, `url`, `description`), 52 initially blank canonical skill columns from `data/fixtures/skills_vocabulary.json`, and an `Instructions` worksheet defining the manual-labeling protocol. (Decided by: User)

## 2026-09-29: HW4 Skill Extraction Validation & Regex Refinement
- 2026-09-29: The refined delimiter-guarded R regex was adopted after HW4 validation. In the 50-posting audit it removed all 5 R false positives while preserving both true positives, giving 100% R precision and 100% recall. (Decided by: User)
- 2026-09-29: The Excel regex negative-lookahead was adopted after HW4 validation. It removed the observed "excel in" false positive while preserving the true Excel detections, giving 100% Excel precision and 100% recall. (Decided by: User)
- 2026-09-29: The LLMs / Generative AI regex was extended to recognize the French phrase "IA générative", resolving the observed false negative. (Decided by: User)
- 2026-09-29: The CI/CD regex was extended with contextual standalone "CI" patterns, resolving the observed "evals in CI" false negative. (Decided by: User)
- 2026-09-29: The HW4 regex update was retained as a hybrid native-tag + description-regex approach rather than deleting regex fallback, because the validated 50-posting audit achieved 98.84% precision and 100.00% recall. (Decided by: User)
- 2026-09-29: After the four regex changes, the 23,138-posting production snapshot showed zero detection-count changes for the other 48 skills; only R, Excel, LLMs / Generative AI, and CI/CD changed. (Decided by: User)
- 2026-09-29: The final HW4 audit results were: 2,548 evaluable skill decisions, 256 human positives, TP=256, FP=3, FN=0, TN=2,289, precision=98.84%, recall=100.00%. (Decided by: User)

## 2026-09-30: HW4 Manual Annotation & Taxonomy Review
- 2026-09-30: In the refreshed 23,138-posting snapshot, 50 of the 52 canonical skills appear in FreeHire's native skill tags, while R and Excel do not appear as native tags and therefore depend entirely on the description-regex fallback for detection. The production extractor retains native FreeHire tags as the primary signal and applies the regex fallback only when a skill was not already detected from native tags. (Decided by: User)
- 2026-09-30: Manual annotation rule: A skill is labelled 1 only when the exact canonical skill is explicitly evidenced in the available posting content; 0 when sufficiently complete evidence does not support it; U when the available content is insufficient to determine it. Required and preferred skills both count. (Decided by: User)
- 2026-09-30: Incomplete sample handling: Sample 19 (Data Engineer MLE - Insud Pharma) is incomplete/truncated, so all 52 skill decisions for that posting are marked U rather than replacing the posting or supplementing it with an external source. (Decided by: User)
- 2026-09-30: External evidence policy: The HW4 sample is evaluated only from the retained FreeHire posting content; no LinkedIn, job-board, or other external source is used to supplement sampled postings. (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat "agentic AI" as evidence for "LLMs / Generative AI" when the context explicitly connects it to generative AI/LLMs. (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat "PySpark" as evidence for "Apache Spark". (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat "Looker Studio" as evidence for "Looker". (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat a job-related GitHub development/version-control mention as evidence for "Git", but do not count incidental GitHub popularity metrics such as repository star counts. (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat French "IA générative" as evidence for "LLMs / Generative AI". (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat standalone "CI" as evidence for "CI/CD" when it is clearly used in a software-engineering, automation, testing, or pipeline context. (Decided by: User)
- 2026-09-30: Taxonomy decision: Treat Google Cloud / Google Cloud Platform as evidence for "GCP" when it is a job-relevant cloud platform/environment mention, but not merely an employer/product-context mention unrelated to the candidate's skill requirements. (Decided by: User)

## 2026-10-03: Independent R Holdout Validation
- 2026-10-03: In response to instructor feedback requesting independent validation of the refined R regex, draw a deterministic holdout sample of exactly 30 postings from the 1,026 current production R matches across the 23,138-posting corpus using seed 20261003 via analysis/build_r_validation_sample.py into analysis/r_validation_sample.json, with the sample frozen before manual inspection. (Decided by: User)
- 2026-10-03: Pre-fix R baseline: Before the R regex refinement, the original HW4 50-posting tuning sample contained 7 extractor-detected R-positive cases, of which only 2 were genuine skill mentions while 5 were false positives (2 of 7 correct, measured on the original HW4 tuning sample, not the independent holdout). (Decided by: User.)
- 2026-10-03: Independent R holdout validation: After the R regex refinement, a fresh deterministic sample of 30 current R-positive corpus postings was frozen before manual inspection from the 1,026 R-positive postings in the 23,138-posting corpus at sampling time; manual validation found 29 true positives, 1 false positive, and 0 U, yielding precision = 29/30 = 96.67%. (Decided by: User.)

## 2026-10-09: Homework 5 — R&D Disambiguation

- **Test promise:** A test would go red if an advertisement mentioning `R&D` (Research & Development), without referring to the R programming language, caused the extractor to report the skill `R`.
- **Expected value and source:** Before running the extractor or creating the test, I manually classified a constructed example: `R` should be absent because `R&D` refers to a department, while `Python` should be present because it is explicitly mentioned as a programming language. This expectation comes from my interpretation of the example, not from program output.
- **Purpose:** Check whether the skill extractor incorrectly treats the `R` in `R&D` as the R programming language.
- **RED run:** Ran `uv run pytest tests/test_analytics.py::TestHybridSkillExtraction::test_rd_department_mention_does_not_extract_r -q` after temporarily removing the `(?!\s*&)` negative lookahead from `data/fixtures/skills_vocabulary.json`. The test failed with `AssertionError: assert "R" not in extracted` because the extractor returned `{'Python', 'R'}` (exit code 1).
- **GREEN run:** Restored the exact `(?!\s*&)` guard in `data/fixtures/skills_vocabulary.json` (verified with zero diff) and reran `uv run pytest tests/test_analytics.py::TestHybridSkillExtraction::test_rd_department_mention_does_not_extract_r -q`. The single test passed (1 passed in 0.07s, exit code 0). (Decided by: User.)

## 2026-10-09: Homework 5 — Real Application Use

- **Analytical question:** In the Data Science occupational category, which technical skill has the highest prevalence, and which has the highest lift over the full corpus? (Decided by: User)
- **Expected result (recorded before running the application):** I expect Python to be the most prevalent skill because it is widely used in data science. I expect the most distinctive skill to be a more specialized data-science or machine-learning skill, rather than a general-purpose tool. (Decided by: User)
- **Source of expectation:** My prior understanding of common data-science tools and the distinction between frequently requested skills and skills disproportionately associated with one occupation. These are hypotheses, not results calculated from the project's output. (Decided by: User)
- **Application and inspection plan:** Launch the existing Streamlit dashboard using `uv run streamlit run app.py`. Select Data Science in Section 2, then record the top skill and displayed prevalence from the “Top In-Demand Skills” chart and the top skill and displayed lift from the “Most Distinctive Skills” chart. (Decided by: User)
- **Actual result:** I launched the Streamlit dashboard using `uv run streamlit run app.py` and inspected Section 2 for Data Science; my direct observation in the running dashboard confirmed that Python was the top in-demand skill and XGBoost was the most distinctive skill for Data Science. The exact prevalence, lift, and posting-count figures were retrieved by Antigravity by inspecting `data/processed/analytics_summary.json`: for the Data Science category (2,142 postings, 9.3% of corpus), Python has 66.4% prevalence (1,422 jobs), and XGBoost has a lift of 5.85× over corpus baseline (3.6% within-category prevalence, 78 jobs). (Decided by: User.)
- **Comparison with expectation:** The actual results confirm both prior expectations: Python was confirmed as the most prevalent skill in Data Science (consistent with the expectation of a foundational table-stakes tool), while XGBoost was confirmed as the most distinctive skill (consistent with the expectation that distinctiveness is driven by specialized machine-learning modeling libraries rather than general-purpose tools). (Decided by: User.)
