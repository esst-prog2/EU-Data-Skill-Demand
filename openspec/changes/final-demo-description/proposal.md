# Proposal: Final Demo Description (Homework 8)

## Why

Section 1 ("The Demo") of `README.md` was originally drafted as a live interactive walkthrough based on an early project snapshot and prior layout iterations. With the dashboard consolidated into a polished single-page application (`app.py`), empirical data refreshed to 24,488 postings across all 27 EU member states, and final university project submission requiring a structured five-minute screenshot presentation (Homework 8), the demo description must be updated. 

The update ensures that the documented demonstration path precisely matches what will be presented using static screenshots, reflects exact current analytical metrics (e.g., Python prevalence and lift across Data Science and Data Analytics), and accurately portrays the production system evaluated by reviewers immediately after the presentation.

## What Changes

- **Presentation-Mode Framing**: Reframe Section 1 of `README.md` from an interactive browser run ("I open the Streamlit web app in the browser...") to a structured 5-minute screenshot walkthrough that guides the audience through concrete screens, visual cards, and analytical insights.
- **Synchronized Empirical Metrics**: Update all specific quantitative callouts to match the audited 24,488 posting snapshot serialized in `data/processed/analytics_summary.json` (e.g., Data Science Python prevalence at 73.8% with 1.29× lift vs. Data Analytics at 42.2% with 0.74× lift; 11 EU countries meeting $N \ge 300$; 42.9% seniority coverage).
- **Concrete UI & Artifact References**: Explicitly cite production artifacts (`app.py`, `data/processed/analytics_summary.json`) and specific visual dashboard features:
  - Dashboard header, persistent sticky filter bar, and four summary KPI cards.
  - Dual-metric comparison (prevalence vs. distinctiveness lift).
  - Bivariate prevalence-versus-lift scatter plot with domain-specific skill-family selector and objective corpus parity baseline ($\text{Lift} = 1.00$).
  - European choropleth posting volume map paired with a 100% stacked occupational composition bar chart for reliable member states ($N \ge 300$).
  - Full uncollapsed skill demand table and methodological seniority reporting.
- **Concise Submission Compliance**: Formulate the demo description in exactly 5 present-tense sentences (satisfying the 3–6 sentence constraint) following a linear, easily understandable visual demonstration path.

## Capabilities

### New Capabilities
- `demo-presentation`: Final demo presentation specification governing the screenshot walkthrough sequence, UI screen mapping, and empirical metric alignment in Section 1 of `README.md`.

### Modified Capabilities
*(None; builds on top of existing analytical dashboard and precomputed summary without changing underlying metric definitions or schema).*

## Impact

- **Documentation**: Updates Section 1 of `README.md`. Preserves all other sections (`Scope Decisions`, `The Shape`, `Data and Reproducibility`, and `Limitations`).
- **Code & Data**: No changes to application code (`app.py`), analytics module (`src/analytics.py`), or dataset (`data/processed/analytics_summary.json`).
- **Dependencies**: No dependency changes.
- **Process & Governance**: Satisfies university submission requirements for Homework 8 and project planning log recording conventions.
