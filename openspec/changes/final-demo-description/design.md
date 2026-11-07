# Design: Final Demo Description (Homework 8)

## Context

The repository has completed its core development and data refresh cycle, reaching 24,488 unique FreeHire job postings across all 27 EU member states. The user-facing dashboard is implemented in `app.py` as a unified single-page Streamlit application that renders top-level KPIs, category skill prevalence, distinctiveness lift, an interactive 2D scatter plot, a European choropleth map, and a 100% stacked occupational composition bar chart for countries with $N \ge 300$.

University evaluation requires a five-minute presentation using static screenshots rather than a live demo. Because reviewers evaluate the program immediately following the presentation, the demo description in Section 1 of `README.md` must be rewritten to articulate this screenshot journey accurately and crisply within 3–6 sentences.

## Goals / Non-Goals

**Goals:**
- Provide a coherent 5-sentence narrative in Section 1 of `README.md` that guides the reader through the 5-minute screenshot deck.
- Strictly reflect the current single-page dashboard architecture (`app.py`) and precomputed summary (`data/processed/analytics_summary.json`).
- Align all cited numerical metrics with the refreshed 7 November 2026 data snapshot.
- Maintain full compatibility with existing README sections (`Scope Decisions`, `The Shape`, `Data and Reproducibility`, and `Limitations`).

**Non-Goals:**
- Altering application code (`app.py`), analytical calculations (`src/analytics.py`), or testing harness.
- Presenting offline or experimental work (e.g., the LLM regex audit exploration in `scripts/regex_audit/`) as active production features.
- Re-architecting the dashboard back into a multi-page app or changing visual component layouts.

## Decisions

### 1. Structure as a Sequential 5-Slide Screenshot Narrative
- **Rationale**: A 5-minute presentation cleanly maps to five thematic slides/screenshots:
  1. Application scope, header, and KPI summary cards.
  2. Selected job family skill prevalence vs. distinctiveness lift comparison.
  3. Bivariate prevalence-vs-lift scatter plot with domain filtering and baseline parity line ($\text{Lift} = 1.00$).
  4. Geographic distribution (choropleth map) and cross-country occupational composition (100% stacked bar chart for $N \ge 300$).
  5. Complete uncollapsed skill table, seniority transparency, and reproducible data pipeline.
- **Alternatives considered**:
  - *Feature laundry list*: Enumerates features without a presentation sequence; rejected because it fails to represent how the screenshots will be shown.
  - *User persona story*: Follows a hypothetical analyst persona; rejected because the prompt requires a direct description of what the student will show in five minutes.

### 2. Concrete Empirical Data Callouts
- **Rationale**: Quoting real numbers (e.g., Python at 73.8% in Data Science with 1.29× lift vs. 42.2% in Data Analytics with 0.74× lift; 11 countries with $N \ge 300$) demonstrates analytical depth, confirms pipeline execution, and provides exact claims that can be audited against `analytics_summary.json`.
- **Alternatives considered**:
  - *Vague qualitative phrasing* ("shows which skills are higher or lower"): Fails homework criteria for concrete details.

### 3. Preservation of Historical Context in Scope Decisions
- **Rationale**: Keep the subsections (`### Scope Decisions`, `### Running the Dashboard`, etc.) intact to retain full documentation traceability for the university submission.
- **Alternatives considered**:
  - *Overwriting Section 1 entirely*: Would erase important rationale regarding why CV matching was cut, why FreeHire was chosen, and why seniority is descriptive.

## Risks / Trade-offs

- **[Risk]** Discrepancy between demo text and underlying summary data if data is refreshed again.
  → *Mitigation*: Numerical citations are sourced directly from the committed snapshot in `data/processed/analytics_summary.json` (24,488 postings, committed at `2b7f2b1`).
- **[Risk]** Brevity vs. Completeness: Fitting a multi-faceted dashboard into 5 sentences risks omitting minor UI widgets.
  → *Mitigation*: The 5 sentences strategically cover all major visual sections from top to bottom (KPIs, bar charts, scatter plot, map, composition stacked bar, table, and methodology).
