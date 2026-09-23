# Spec Delta: dashboard

## Purpose

Renders an interactive, single-page Streamlit web dashboard providing immediate visualization of technical skill demand across data occupations and EU-27 countries.

## ADDED Requirements

### Requirement: Single-Page Presentation Layer
The dashboard SHALL operate as a thin presentation layer on a single scrollable page, consuming precomputed data from `data/processed/analytics_summary.json` without executing heavy data transformations at runtime.

#### Scenario: Single-page rendering
- **WHEN** a user opens the Streamlit application
- **THEN** all summary KPIs, market overview, category profiles, and geographic charts render vertically on one page

### Requirement: Corpus KPI and Seniority Metadata Display
The dashboard SHALL display high-level KPI cards reporting total postings (22,985), EU-27 member states represented (27), occupational categories (5), and native seniority availability (41% descriptive fact without filtering or imputation).

#### Scenario: Seniority reporting
- **WHEN** the dashboard renders corpus metadata
- **THEN** seniority coverage is displayed as 41% without providing a seniority filter

### Requirement: Side-by-Side Occupational Skill Profile
The dashboard SHALL provide an occupational category selector that updates two side-by-side horizontal ranked bar charts:
1. **Top In-Demand Skills**: Top 10 skills by within-category prevalence ($P(\text{skill} \mid \text{category})$).
2. **Most Distinctive Skills**: Top 10 skills meeting the support threshold ($N_{\text{cat}} \ge 20$, $P_{\text{cat}} \ge 1.5\%$) ranked by lift descending with $\text{Lift} > 1.0$.

#### Scenario: Selecting an occupation
- **WHEN** a user selects `Data Science` from the category selector
- **THEN** the left chart displays the top 10 prevalent skills in Data Science and the right chart displays the top 10 distinctive skills with Lift $> 1.0$

### Requirement: Geographic Visualization and Threshold Callout
The dashboard SHALL display an EU-27 choropleth map showing raw posting counts for all 27 member states, accompanied by a 100% stacked bar chart comparing occupational mix across countries with $N \ge 300$ postings, with an explicit note explaining why smaller countries are mapped but excluded from composition comparisons.

#### Scenario: Country comparison eligibility
- **WHEN** viewing the occupational composition comparison
- **THEN** only the 12 qualifying countries with $N \ge 300$ are included, and an explanatory footnote is displayed for the remaining 15 member states

