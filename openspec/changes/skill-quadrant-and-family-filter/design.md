# Design: Interactive Skill Analysis — Prevalence vs. Lift Scatter Plot and Skill-Family Filter

## Context

In Section 2 of the Streamlit dashboard (`app.py`), users select one of five occupational categories to view two side-by-side ranked horizontal bar charts: Top In-Demand Skills (by within-category prevalence %) and Most Distinctive Skills (by lift multiple over corpus baseline).

The committed `data/processed/analytics_summary.json` file precomputes and serializes an `all_skills` list for each occupational category containing all 52 canonical skills with:
- `canonical`: Skill name (e.g., "Python", "Snowflake")
- `skill_group`: One of 5 canonical skill families
- `count`: Observed posting count within the category
- `prevalence`: Proportion within category ($P \in [0, 1]$)
- `prevalence_pct`: Formatted percentage ($P \times 100$)
- `lift`: Ratio over corpus baseline ($P_{\text{cat}} / P_{\text{corpus}}$)

Currently, `app.py` directly binds the precomputed top-10 slices (`cat_profile["top_in_demand"]` and `cat_profile["top_distinctive"]`) to the bar charts. It does not provide a 2D bivariate visualization of prevalence versus lift, nor does it allow filtering or re-ranking by `skill_group`. See `proposal.md` for motivation and background.

## Goals / Non-Goals

**Goals:**
- Render an interactive 2D scatter plot in Section 2 plotting within-category prevalence % on the horizontal axis and lift multiple on the vertical axis.
- Provide a prominent horizontal reference line at $\text{Lift} = 1.0$ (parity with corpus baseline).
- Clearly distinguish observed skills ($N_{\text{cat}} \ge 1$) from verified distinctive skills ($N_{\text{cat}} \ge 20, P_{\text{cat}} \ge 1.5\%, \text{Lift} > 1.0$) in visual styling and hover text.
- Exclude unobserved skills ($N_{\text{cat}} = 0$) from the scatter plot to prevent misleading clustering at the origin.
- Implement a skill-family filter control defaulting to `"All Families"` and supporting the 5 canonical technical domains.
- Harmonize Section 2 views: when `"All Families"` is selected, preserve the precomputed top-10 rankings; when a specific family is selected, filter and re-rank from the complete `all_skills` data for that category.
- Implement pure Python analytical helpers in `src/analytics.py` for data preparation and filtering, enabling deterministic `pytest` coverage without running Streamlit.
- Provide educational, non-inferential interpretation guidance explaining relative lift versus absolute volume and noting that high lift alone does not indicate high overall market demand.

**Non-Goals:**
- Imposing an arbitrary vertical prevalence threshold (e.g., 10%) or rigid quadrant classification unsupported by data.
- Modifying raw data collection (`eu27.py`), preprocessing (`scripts/preprocess.py`), or the JSON schema of `analytics_summary.json`.
- Modifying Section 1 (Overview) or Section 3 (Geographic Distribution).
- Adding new external dependencies or secondary dashboard tools.

## Decisions

### 1. Quadrant Semantics: Objective Parity Line and Continuous Prevalence
- **Decision:** The visualization will display a single, mathematically objective reference line at $\text{Lift} = 1.0$ (parity with overall corpus frequency) and treat the prevalence axis as continuous. Rigid four-quadrant discrete classification is deferred.
- **Rationale:**
  - An arbitrary prevalence cutoff (e.g., $10\%$) has no empirical or statistical foundation across disparate occupational categories.
  - A category-specific median prevalence threshold was evaluated, but produces moving boundaries that shift across categories (e.g., median prevalence in Data Engineering is very different from ML/AI), creating confusing, non-comparable quadrant assignments.
  - The objective parity line ($\text{Lift} = 1.0$) splits skills into above-baseline (characteristic/concentrated) versus below-baseline (diffuse/universal), while the horizontal axis naturally displays penetration from rare to ubiquitous.
  - Contextual text will explain this bivariate space without forcing artificial categorical boxes.
- **Alternatives Considered:**
  - *Hardcoded vertical cutoff at 10% or 15% prevalence:* Rejected as arbitrary and methodologically indefensible.
  - *Category-relative median prevalence line:* Rejected because moving boundaries across occupational categories undermine cross-category comparisons.

### 2. Interaction Model: Synchronized Section 2 Filtering & Full `all_skills` Re-Ranking
- **Decision:** Place a skill-family selector (`st.selectbox`) directly beneath the category selector in Section 2, with options:
  - `"All Families"` (default)
  - `"Programming languages"`
  - `"Databases & data warehouses"`
  - `"BI & visualization"`
  - `"Cloud & infrastructure"`
  - `"ML/AI frameworks & tools"`
  - **When "All Families" is selected**: The dashboard directly renders `cat_profile["top_in_demand"]` and `cat_profile["top_distinctive"]`, preserving 100% of existing behavior and visual outputs.
  - **When a specific family is selected**: Both ranking bar charts and the scatter plot re-filter and re-rank from the complete `cat_profile["all_skills"]` list:
    - *In-Demand within family:* Filter `all_skills` by `skill_group == family`, sort descending by `prevalence` (tie-breaker `count`), take top 10.
    - *Distinctive within family:* Filter `all_skills` by `skill_group == family`, apply the existing eligibility rules (`count >= 20`, `prevalence >= 0.015`, `lift > 1.0`), sort descending by `lift` (tie-breaker `prevalence`), take top 10.
- **Rationale:** Slicing the precomputed overall top-10 list would omit the actual top skills within smaller domains (e.g., if only one Cloud tool made the overall top 10, filtering to Cloud would show only 1 bar). Re-ranking from `all_skills` reveals the true leading skills for that domain, while preserving existing behavior when unfiltered.
- **Alternatives Considered:**
  - *Filtering the precomputed top-10 lists:* Rejected because it produces truncated lists and misses domain-specific leaders.
  - *Filtering only the scatter plot:* Rejected because having adjacent charts in the same section show mismatched filtering causes user confusion.

### 3. Observed vs. Eligible Skills in Scatter Plot
- **Decision:**
  - **Exclusion of zero-count skills:** Skills with $N_{\text{cat}} = 0$ are excluded from the scatter plot. They carry zero prevalence and zero lift, and plotting 15–20 overlapping markers at $(0, 0)$ distorts the visual field.
  - **Visual distinction of eligibility:** All observed skills ($N_{\text{cat}} \ge 1$) with valid finite coordinates are plotted, but markers meeting the verified distinctive eligibility criteria ($N_{\text{cat}} \ge 20$, $P_{\text{cat}} \ge 1.5\%$, $\text{Lift} > 1.0$) are visually highlighted with full opacity ($1.0$) and distinct border styling, whereas sub-threshold skills are styled with reduced opacity ($0.45$).
  - **Hover details:** Tooltips explicitly display the support status:
    - `"Support: Qualified Distinctive (N ≥ 20, Prev ≥ 1.5%)"`
    - `"Support: Sub-threshold (N < 20 or Prev < 1.5%)"`
- **Rationale:** Allows users to see emerging or niche tools while preventing low-count artifacts (e.g., a skill appearing in 2 postings with high lift) from being misinterpreted as robust evidence of specialization.

### 4. Mathematical Edge Cases and Summary Schema Handling
- **Decision:**
  - **Prevalence and lift calculations:** Reuse `src.analytics.compute_prevalence` and `src.analytics.compute_lift` without divergence.
  - **Missing or non-finite lift:** If `lift` is missing, null, or non-finite (e.g. corpus prevalence is 0 or category prevalence is 0), the skill is excluded from scatter coordinates. We never invent coordinates or silently coerce undefined lift into $0.0$.
  - **Empty categories:** If an occupational category has zero total postings or a filtered family has zero observed skills, the dashboard renders an informative `st.info("No postings observed for this selection.")` rather than crashing or dividing by zero.

### 5. Architectural Separation: Pure Helper Functions in `src/analytics.py`
- **Decision:** Implement data transformation and filtering in `src/analytics.py` as pure functions:
  ```python
  def filter_skills_by_family(skills: list[dict], family: str | None = None) -> list[dict]: ...
  def rank_in_demand_skills(skills: list[dict], top_n: int = 10) -> list[dict]: ...
  def rank_distinctive_skills(skills: list[dict], top_n: int = 10, min_count: int = 20, min_prevalence: float = 0.015, min_lift: float = 1.0) -> list[dict]: ...
  def prepare_scatter_data(skills: list[dict]) -> list[dict]: ...
  ```
- **Rationale:** Enables exhaustive, deterministic testing of all edge cases with `pytest` on synthetic fixtures without running Streamlit.

## Risks / Trade-offs

- **[Risk] Small Families in Small Categories Yielding Few Distinctive Skills** → Selecting "ML/AI frameworks & tools" within "Data Analytics" might have few or no skills meeting $N \ge 20$ and $P \ge 1.5\%$.
  - *Mitigation:* Display an informative placeholder ("No skills met the minimum support criteria in this family") instead of a broken chart. The scatter plot still shows all observed skills with clear sub-threshold indicators.
- **[Risk] Visual Crowding** → Up to 52 markers could cluster in dense areas.
  - *Mitigation:* Exclude $N=0$ skills, size markers dynamically by posting count, and provide the skill-family filter to isolate 8–15 skills per domain.
- **[Risk] Misinterpretation of Lift** → Users confusing high lift with high demand.
  - *Mitigation:* Prominent caption and callout box explicitly explaining that lift measures relative distinctiveness against the corpus baseline, not absolute volume.

## Migration Plan

1. Implement pure analytical helpers in `src/analytics.py`.
2. Add deterministic unit tests in `tests/test_analytics.py`.
3. Update `app.py` Section 2 to render the skill-family selector, scatter plot, and family-filtered rankings.
4. Add UI regression tests in `tests/test_app.py`.
5. Update `README.md` documentation during implementation.
6. Verify with `uv run pytest` and `git diff --check`.
Rollback strategy: Changes are isolated to presentation and helper functions; can be reverted without touching datasets or pipeline.

## Open Questions

*(None; all structural decisions regarding parity line demarcation, family re-ranking from `all_skills`, and observed vs. eligible distinction are fully resolved).*
