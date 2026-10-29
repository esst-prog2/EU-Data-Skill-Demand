# Tasks: Interactive Skill Analysis — Prevalence vs. Lift Scatter Plot and Skill-Family Filter

## 1. Core Analytical Helpers & Data Transformation

- [x] 1.1 Define canonical skill families constant (`SKILL_FAMILIES`) and implement `filter_skills_by_family(skills, family)` in `src/analytics.py`, verifying behavior with standalone tests covering "All Families", valid families, and invalid family names.
- [x] 1.2 Implement `rank_in_demand_skills(skills, top_n=10)` and `rank_distinctive_skills(skills, top_n=10, min_count=20, min_prevalence=0.015, min_lift=1.0)` in `src/analytics.py` to re-rank filtered skills from complete `all_skills`, verifying sorting and threshold compliance with unit tests.
- [x] 1.3 Implement `prepare_scatter_data(skills)` in `src/analytics.py` to filter out $N=0$ skills, exclude undefined/non-finite lift, format coordinates, assign eligibility support status, and calculate marker sizes, verifying output format with unit tests.

## 2. Unit & Integration Tests for Analytical Helpers

- [x] 2.1 Add unit tests to `tests/test_analytics.py` verifying that `filter_skills_by_family` returns all skills when family is None or "All Families", filters accurately for each of the 5 canonical families, and handles empty lists safely.
- [x] 2.2 Add unit tests to `tests/test_analytics.py` verifying that `rank_in_demand_skills` and `rank_distinctive_skills` correctly re-rank synthetic skill records, enforce the $N \ge 20$, $P \ge 1.5\%$, and $\text{Lift} > 1.0$ distinctive criteria, and return empty lists gracefully when no skills qualify.
- [x] 2.3 Add unit tests to `tests/test_analytics.py` verifying that `prepare_scatter_data` correctly calculates prevalence percentages, excludes zero-count and non-finite lift skills, sets the qualified distinctive flag accurately, and safely handles empty input lists without zero-division errors.
- [x] 2.4 Run `uv run pytest tests/test_analytics.py` to confirm that all analytical helper tests pass.

## 3. Dashboard UI Implementation in Section 2

- [x] 3.1 Add skill-family filter control (`st.selectbox`) below the occupational category selector in Section 2 of `app.py`, defaulting to "All Families".
- [x] 3.2 Update Section 2 companion ranking bar charts so selecting "All Families" preserves the precomputed `top_in_demand` and `top_distinctive` lists, while selecting a specific family renders the re-ranked top skills within that family from `all_skills`.
- [x] 3.3 Implement Plotly 2D scatter plot in Section 2 of `app.py`, displaying prevalence % on X, lift on Y, a horizontal dashed reference line at $\text{Lift} = 1.0$, size-scaled markers, and distinct visual styling for qualified distinctive vs. sub-threshold skills.
- [x] 3.4 Add rich hover tooltips displaying canonical skill name, skill family, posting count, prevalence %, lift multiple, and eligibility support status.
- [x] 3.5 Add non-inferential interpretation callout box in Section 2 of `app.py` explaining the bivariate continuous distribution and clarifying that high lift measures relative distinctiveness rather than absolute market volume.

## 4. UI Testing, Verification, and Documentation

- [x] 4.1 Add deterministic UI tests to `tests/test_app.py` verifying that Section 2 renders the scatter plot, reference line, and family filter cleanly without runtime exceptions across synthetic and production summary fixtures, without hardcoding snapshot dates or posting counts.
- [x] 4.2 Update `README.md` Section 1 (The Demo) and Section 2 (The Shape) to document the new 2D scatter plot, interpretation guide, and skill-family filtering capabilities upon implementation.
- [x] 4.3 Run full test suite (`uv run pytest`) and `git diff --check` to verify that all existing and new tests pass cleanly without regressions or whitespace defects.
