## Planning log
Whenever we decide something about this project – a requirement, a number, a name, a tool – append one line to PLANNING_LOG.md: the date, what was decided, and whether I decided it or you did. Never rewrite an earlier line.

## Project Overview
**EU Data Jobs & Skill Demand Analysis**
An interactive Streamlit web dashboard and testable analytical pipeline examining technical skill demand across data-related occupations and EU-27 countries based on an audited snapshot of 22,985 FreeHire job postings.

### Target Occupational Categories
- Data Analytics (`data_analytics`)
- Data Engineering (`data_engineering`)
- Data Science (`data_science`)
- ML/AI (`ml_ai`)
- AI Engineering (`ai_engineering`)

### Core Analytical Rules
- **Skill Extraction:** Controlled vocabulary with explicit alias normalization (e.g., `PowerBI` → `Power BI`).
- **Prevalence:** Binary presence per unique posting (counted at most once per posting):
  $$P(\text{skill} \mid \text{category}) = \frac{\text{count}(\text{skill} \cap \text{category})}{N_{\text{category}}}$$
- **Skill Lift (Distinctiveness):**
  $$\text{Lift} = \frac{P(\text{skill} \mid \text{category})}{P(\text{skill} \mid \text{corpus})}$$
- **Geographic Scope (EU-27):**
  - Raw posting counts mapped across all EU-27 member states.
  - Occupational composition comparison across countries is restricted to countries with $N \ge 300$ observed postings. Smaller countries are displayed on the map with raw counts but excluded from composition comparisons.
- **Seniority:** Native FreeHire seniority information is reported as a descriptive fact (available for 41% of postings); no filtering or imputation.
- **Code Organization:** Plain Python functions in a core module for analytical logic, testable directly with `pytest`. Streamlit handles presentation and visualization.

### Explicit Scope Boundaries
- No CV matching or personalized skill-gap scoring.
- No custom occupational or seniority classification models or seniority inference.
- No per-skill breakdown by country (no skill $\times$ country matrix).
- No external labour-market weights; snapshot is treated as an observed sample.
- No secondary dashboard tools (Python/Streamlit only).

