# Proposal: Interactive Skill Analysis — Prevalence vs. Lift Scatter Plot and Skill-Family Filter

## Why

In the current dashboard, Section 2 presents occupational skill demand through two separate top-10 horizontal bar charts: one for within-category prevalence and one for distinctiveness lift. While mathematically sound, displaying these metrics in isolated lists obscures the dual-dimensional relationship between baseline volume and role specificity. Users cannot easily see which high-prevalence skills are universal table-stakes versus unique role anchors, nor can they examine skill demand within specific technical domains (e.g., Cloud & Infrastructure or Databases).

Adding an interactive 2D Prevalence-versus-Lift scatter plot and a skill-family filter transforms Section 2 into a cohesive exploratory tool. It enables users to visually explore the bivariate distribution of skills against an objective baseline parity reference line ($\text{Lift} = 1.0$) and isolate demand across five canonical skill families using the precomputed data already present in `analytics_summary.json`.

## What Changes

- **Interactive 2D Prevalence vs. Lift Scatter Plot in Section 2 (`app.py`)**:
  - Plots observed canonical skills for the selected occupational category on a continuous two-dimensional coordinate system:
    - **X-axis**: Within-category skill prevalence percentage ($P(\text{skill} \mid \text{category}) \times 100$).
    - **Y-axis**: Distinctiveness lift relative to the corpus baseline ($\text{Lift} = P(\text{skill} \mid \text{category}) / P(\text{skill} \mid \text{corpus})$).
  - Includes a prominent horizontal reference line at $\text{Lift} = 1.0$ representing parity with overall corpus baseline prevalence.
  - Defers rigid four-quadrant categorization in favor of the objective lift parity line ($\text{Lift} = 1.0$) and a continuous prevalence interpretation, avoiding arbitrary vertical prevalence cut-offs.
  - Excludes unobserved skills ($N_{\text{cat}} = 0$) to eliminate uninformative stacking at origin $(0, 0)$.
  - Visually distinguishes qualified distinctive skills ($N_{\text{cat}} \ge 20, P_{\text{cat}} \ge 1.5\%, \text{Lift} > 1.0$) from sub-threshold or below-parity skills via marker styling and hover indicators, making clear that low-count observations do not constitute strong evidence of role specialization.
  - Adds marker point sizing proportional to posting count and point coloring by canonical skill family.
  - Provides rich hover tooltips detailing: canonical skill name, skill family, observed posting count, prevalence percentage, lift multiple, and eligibility support status.
  - Provides concise, non-inferential interpretation guidance explaining relative lift versus absolute volume and explicitly stating that high lift alone does not indicate high market demand.

- **Skill-Family Filter Control with Re-Ranked Views (`app.py`)**:
  - Introduces a filter control (`st.selectbox`) in Section 2 populated by `"All Families"` plus the 5 canonical skill families:
    - *Programming languages*
    - *Databases & data warehouses*
    - *BI & visualization*
    - *Cloud & infrastructure*
    - *ML/AI frameworks & tools*
  - **Preserves existing default behavior**: When `"All Families"` is selected, Section 2 displays the precomputed `top_in_demand` and `top_distinctive` lists exactly as it does today.
  - **Dynamic re-ranking from full `all_skills`**: When a specific skill family is selected, both the scatter plot and the companion ranking bar charts filter and re-rank from the complete `all_skills` dataset for the selected category (not just a subset of the precomputed overall top 10), ensuring the true top-demand and top-distinctive skills of that domain are displayed.

- **Pure Analytical Helpers & Data Formatting (`src/analytics.py`)**:
  - Adds pure Python helper functions for filtering skill records by family, re-ranking skills within a family, and preparing scatter plot coordinates and hover metadata.
  - Fully testable with `pytest` without requiring Streamlit server execution.

- **Deterministic Test Coverage (`tests/test_analytics.py`, `tests/test_app.py`)**:
  - Unit tests for skill-family filtering and within-family re-ranking using synthetic fixtures.
  - Unit tests for scatter data preparation, zero-count filtering, coordinate boundary guards, and zero-division handling.
  - UI regression tests verifying that Section 2 renders cleanly with both default and family-filtered selections without runtime exceptions.
  - All tests remain decoupled from live snapshot dates or specific calendar timestamps.

- **Documentation Updates**:
  - Updates README.md (Sections 1 and 2) to document the scatter plot, interpretation guidelines, and skill-family filtering. (Completed.)

## Capabilities

### New Capabilities
- `skill-quadrant-analysis`: Interactive two-dimensional prevalence-vs-lift scatter plot, baseline parity reference line, and domain-specific skill-family filtering with re-ranked companion views in Section 2 of the Streamlit dashboard.

### Modified Capabilities
*(None; builds on top of existing analytical core and precomputed summary without changing underlying metric definitions or schema).*

## Impact

- **Code Structure**:
  - Extends `app.py` Section 2 with the scatter chart, family selector, and re-ranked companion bar charts.
  - Adds pure helper functions in `src/analytics.py`.
  - Adds unit and UI regression tests in `tests/test_analytics.py` and `tests/test_app.py`.
- **Data & Schema**:
  - Zero changes to raw data collection (`eu27.py`), preprocessing (`scripts/preprocess.py`), or `analytics_summary.json` schema. Reuses `all_skills` already serialized for each category profile.
- **Dependencies**:
  - Uses existing project dependencies (`plotly`, `streamlit`, `pytest`). No new dependencies.
- **Scope & Governance**:
  - Maintains strict observed-sample boundaries: no predictive models, no inference, no CV matching, no per-country skill breakdowns, and no external weights.
