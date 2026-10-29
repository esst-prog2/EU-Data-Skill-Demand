# Spec Delta

## Purpose

Enables interactive visual exploration of technical skill demand and distinctiveness within occupational categories using a two-dimensional prevalence-versus-lift scatter plot, baseline parity reference line, and domain-specific skill-family filtering with re-ranked companion views.

## ADDED Requirements

### Requirement: Interactive 2D Prevalence vs. Lift Scatter Plot
The dashboard SHALL render an interactive two-dimensional scatter plot within Section 2 for the currently selected occupational category, mapping within-category prevalence percentage on the horizontal axis and corpus lift on the vertical axis.

#### Scenario: Visual rendering of prevalence vs lift coordinates
- **WHEN** a user selects an occupational category in Section 2
- **THEN** the system displays a scatter plot where the X-axis represents within-category prevalence percentage ($P(\text{skill} \mid \text{category}) \times 100$) and the Y-axis represents distinctiveness lift relative to the corpus baseline ($\text{Lift} = P(\text{skill} \mid \text{category}) / P(\text{skill} \mid \text{corpus})$)

#### Scenario: Objective parity reference line at Lift = 1.0
- **WHEN** the scatter plot is displayed
- **THEN** a prominent horizontal dashed or solid reference line is rendered at $\text{Lift} = 1.0$, visually demarcating skills with above-baseline representation from skills with below-baseline representation without imposing arbitrary vertical quadrant divisions

#### Scenario: Continuous prevalence interpretation guidance
- **WHEN** the scatter plot is viewed
- **THEN** the dashboard provides explanatory guidance clarifying that the horizontal axis measures within-category market penetration, the vertical axis measures distinctiveness relative to the overall corpus, and high lift alone does not indicate high absolute market demand

### Requirement: Skill-Family Filter Control and Re-Ranked Companion Views
The dashboard SHALL provide a skill-family filter control in Section 2 allowing users to focus the category analysis on specific technical domains or view all domains simultaneously, dynamically updating both the scatter plot and companion ranking charts.

#### Scenario: Default all-families view preserves precomputed rankings
- **WHEN** Section 2 is loaded with the filter set to "All Families"
- **THEN** the scatter plot displays all observed skills across all 5 skill families, and the companion Top In-Demand and Most Distinctive ranking bar charts display the precomputed overall top-10 lists from the category profile

#### Scenario: Filtering to a specific technical skill family
- **WHEN** the user selects a specific skill family (e.g., "Cloud & infrastructure")
- **THEN** the scatter plot displays only skills assigned to the selected family that have at least one observed posting in the category

#### Scenario: Dynamic re-ranking within selected skill family from complete all_skills
- **WHEN** a specific skill family is selected
- **THEN** the companion Top In-Demand bar chart displays up to the top 10 skills within that family ranked descending by prevalence from the complete `all_skills` dataset, and the Most Distinctive bar chart displays up to the top 10 skills within that family meeting the distinctive eligibility criteria ($N_{\text{cat}} \ge 20$, $P_{\text{cat}} \ge 1.5\%$, $\text{Lift} > 1.0$) ranked descending by lift from `all_skills`

### Requirement: Distinction Between Observed and Eligible Distinctive Skills
The scatter visualization SHALL clearly distinguish skills included for observed visibility from skills meeting the verified distinctive-skill criteria, preventing low-count observations from being misinterpreted as strong evidence of role specialization.

#### Scenario: Exclusion of unobserved skills
- **WHEN** preparing skill data for the scatter plot
- **THEN** any skill with zero observed postings within the selected category ($N_{\text{cat}} = 0$) is excluded from the chart to prevent artificial stacking at origin $(0, 0)$

#### Scenario: Visual and hover indication of distinctive eligibility
- **WHEN** a user hovers over or views a skill marker in the scatter plot
- **THEN** markers meeting the distinctive eligibility criteria ($N_{\text{cat}} \ge 20$, $P_{\text{cat}} \ge 1.5\%$, $\text{Lift} > 1.0$) are visually distinct (via solid styling or higher opacity) from sub-threshold skills, and the hover tooltip explicitly reports support status as either "Qualified Distinctive (N ≥ 20, Prev ≥ 1.5%)" or "Low support (N < 20 or Prev < 1.5%)"

#### Scenario: Complete hover inspection details
- **WHEN** a user hovers over any skill marker in the scatter plot
- **THEN** the tooltip displays the canonical skill name, skill family, observed posting count within the category, within-category prevalence percentage, lift multiple, and eligibility support status

### Requirement: Deterministic Data Handling and Mathematical Edge Cases
The analytical data preparation for the scatter visualization and family filtering SHALL be implemented as standalone, pure Python helper functions that handle missing, empty, or zero-division edge cases safely.

#### Scenario: Safe handling of empty categories or zero counts
- **WHEN** an occupational category has zero total postings or a skill list is empty
- **THEN** the data preparation helper returns an empty list for plotting and rendering displays an informative placeholder message ("No postings observed for this selection") without raising an exception or performing division by zero

#### Scenario: Handling of undefined or missing lift
- **WHEN** a skill has an undefined or non-finite lift value (e.g., corpus prevalence is zero or lift is null)
- **THEN** the helper excludes the record from scatter plot coordinates rather than silently coercing undefined lift into zero or inventing a coordinate

#### Scenario: Input validation for skill-family filtering
- **WHEN** a filter query specifies an unrecognized skill family name
- **THEN** the helper function returns an empty list or raises a descriptive ValueError rather than failing silently or returning corrupted data
