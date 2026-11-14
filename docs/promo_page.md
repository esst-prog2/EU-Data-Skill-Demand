# The EU Data Career Compass: What the Job Market Actually Expects from You

An interactive, evidence-based exploration of **24,488 European tech job postings** across **27 EU member states** and **5 core data professions** — designed to help aspiring analysts, scientists, and engineers navigate real market demand with clarity and empirical perspective.

---

```text
┌────────────────────────────────────────────────────────────────────────┐
│  24,488 Observed Postings │ 27 EU Countries │ 5 Occupations │ 52 Skills│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. The Junior Data Dilemma: Job Description Fatigue

If you are a student, recent graduate, or career switcher exploring the data field, you have likely encountered "job description fatigue."

Open commercial job boards and you will often find entry-level listings presenting exhaustive technology lists: Python, SQL, Spark, Docker, AWS, Tableau, Kubernetes, Airflow, and PyTorch — all within a single vacancy description. At the same time, generic career roadmaps frequently provide broad recommendations such as *"just learn Python and SQL,"* without explaining how technical requirements actually differ across specific data disciplines in practice.

This leaves aspiring professionals trying to answer four fundamental questions:
1. **Role Differentiation:** What skills are most frequently requested in Data Analytics vs. Data Science vs. Data Engineering vs. ML/AI vs. AI Engineering?
2. **Foundational vs. Distinguishing Skills:** Which skills appear broadly across multiple data disciplines, and which ones are uniquely concentrated in a particular role?
3. **Learning Prioritization:** When preparing for a specific career path, which technical skills show the highest concentration in actual postings?
4. **Geographic Variation:** How do technical requirements and hiring volumes vary across European countries within the observed data?

The **EU Data Career Compass** was built to explore these questions using an audited dataset of 24,488 European tech job postings collected from FreeHire, analyzed through a transparent and reproducible analytical pipeline.

---

## 2. The Core Framework: Popularity vs. Distinctiveness

A central analytical insight of this project is that **raw popularity alone provides an incomplete picture of skill demand.** Treating every skill mention as an interchangeable count overlooks how technical requirements differ across specialized roles.

To evaluate technical skill demand across occupations, the dashboard measures two complementary dimensions:

1. **Within-Category Prevalence ($P(\text{skill} \mid \text{category})$):**
   The proportion of unique postings within an occupational category that request a given skill:
   $$P(\text{skill} \mid \text{category}) = \frac{\text{count}(\text{skill} \cap \text{category})}{N_{\text{category}}}$$
   This measures how *frequently* a tool appears within a specific role.

2. **Distinctiveness Lift ($\text{Lift}$):**
   The ratio of a skill's prevalence within an occupation to its baseline prevalence across the entire 24,488-posting European corpus:
   $$\text{Lift} = \frac{P(\text{skill} \mid \text{category})}{P(\text{skill} \mid \text{corpus})}$$
   - **$\text{Lift} > 1.00$:** The skill is over-represented in this occupation relative to the broader data job market.
   - **$\text{Lift} = 1.00$:** Baseline market parity (the skill occurs at the same rate within the category as across the overall corpus).
   - **$\text{Lift} < 1.00$:** The skill is under-represented in this role relative to the broader market baseline.

### The Four-Quadrant Explanatory Framework

The dashboard renders an interactive 2D scatter plot with Within-Category Prevalence on the horizontal axis and Distinctiveness Lift on the vertical axis, featuring an explicit horizontal reference line at **$\text{Lift} = 1.00$ (Corpus Parity)**.

While the application does not formally partition skills into rigid discrete buckets, the continuous bivariate space can be understood through four explanatory quadrants:

```text
       Distinctiveness Lift
          ▲
          │
          │  [Niche Specializations]          │  [Role Superpowers]
     >1.0 │  Lower prevalence, high lift:     │  Higher prevalence, high lift:
          │  Specialized occupational tools   │  Core distinguishing skills
──────────┼───────────────────────────────────┼──────────────────────────────────────────
  Lift=1.0│  ─────── Baseline Parity ─────────┼──────────────────────────────────────────
          │  [Peripheral Skills]              │  [Universal Currency]
     <1.0 │  Lower prevalence, lower lift:    │  Higher prevalence, lower lift:
          │  Occasional or secondary tools    │  Broad foundational tools (e.g., SQL)
          └───────────────────────────────────┴─────────────────────────────────────────►
                                                      Within-Category Prevalence (%)
```

- **Role Superpowers (Higher Prevalence, Lift > 1.00):** Frequently requested skills that are simultaneously disproportionately concentrated within the selected occupation (e.g., `Power BI` in Data Analytics, `Apache Spark` in Data Engineering, `PyTorch` in ML/AI).
- **Universal Currency (Higher Prevalence, Lift ≤ 1.00):** Frequently requested technologies that appear across multiple data disciplines (such as `SQL`). They reflect broad market presence rather than occupational specialization.
- **Niche Specializations (Lower Prevalence, Lift > 1.00):** Tools with lower overall posting volume within the category that nonetheless show strong occupational concentration relative to the rest of the corpus (e.g., `XGBoost` in Data Science, `OpenCV` in ML/AI).
- **Peripheral Skills (Lower Prevalence, Lift ≤ 1.00):** Tools that appear infrequently within the selected occupation and at rates below or near the broader market baseline.

*Methodological Note:* In the dashboard's ranked distinctive skill lists, formal qualification requires meeting explicit support thresholds: at least 20 postings within the category ($N \ge 20$), within-category prevalence of at least 1.5% ($P \ge 1.5\%$), and $\text{Lift} > 1.00$.

---

## 3. Concrete Example: Why Python and Excel Tell Different Stories

To see why prevalence and distinctiveness provide complementary information, consider how technical requirements compare in **Data Analytics**:

| Skill | Observed Postings | Within-Role Prevalence | Distinctiveness Lift | Empirical Interpretation |
|---|---|---|---|---|
| **Python** | 1,510 / 3,582 | **42.2%** | **0.74×** (Below Parity) | **Broad General Tool:** Present in over 40% of Data Analytics postings, but requested less frequently than across the general corpus (57.1%) or in Data Science (73.8%). Python provides versatile utility, but does not distinguish this category from other data roles. |
| **Excel** | 790 / 3,582 | **22.1%** | **4.73×** (High Distinctiveness) | **Occupational Concentration:** Excel appears in 22.1% of Data Analytics postings compared with 4.7% across the entire 24,488-posting corpus (a 4.73× concentration ratio). Although its raw count is roughly half that of Python, it is uniquely characteristic of analytics postings relative to the overall market. |
| **Power BI** | 1,603 / 3,582 | **44.8%** | **2.61×** (Prevalent & Distinct) | **Category Marker:** High prevalence combined with strong distinctiveness makes business intelligence tools the primary technical marker of the Data Analytics category in this dataset. |

**Practical Takeaway:** Looking only at posting counts might lead a candidate to conclude that Python is the primary skill to emphasize for Data Analytics. Examining both dimensions shows that while Python appears in 42.2% of vacancies, Power BI (44.8%, 2.61× lift) and Excel (22.1%, 4.73× lift) exhibit the strongest relative concentration in analytics postings.

---

## 4. The Five Data Disciplines in the Dataset

The 24,488 postings in this snapshot span five occupational categories. Category counts reflect the distribution of the observed FreeHire dataset and show distinct technical patterns:

### 1. Data Engineering (13,592 postings — 55.5% of dataset)
- **Top In-Demand:** SQL (55.8%, 7,591 jobs), Python (53.5%, 7,268 jobs), Azure (35.3%, 4,792 jobs), Apache Spark (30.3%, 4,121 jobs), CI/CD (29.5%, 4,014 jobs).
- **Highest Distinctiveness Lift:** Apache Kafka (1.61× lift, 11.5%), Scala (1.55× lift, 8.9%), Apache Spark (1.47× lift, 30.3%), Apache Airflow (1.46× lift, 17.7%).
- **Observation:** Data Engineering represents the majority of postings in this snapshot. While SQL and Python are the most prevalent requirements, distributed computing frameworks (Spark, Kafka) and orchestration tools (Airflow) exhibit the highest distinctiveness lift.

### 2. Data Analytics (3,582 postings — 14.6% of dataset)
- **Top In-Demand:** SQL (63.7%, 2,283 jobs), Power BI (44.8%, 1,603 jobs), Python (42.2%, 1,510 jobs), Excel (22.1%, 790 jobs), Tableau (21.0%, 754 jobs).
- **Highest Distinctiveness Lift:** Excel (4.73× lift, 22.1%), Looker (3.90× lift, 11.5%), Tableau (3.38× lift, 21.0%), Qlik (2.81× lift, 5.6%), Metabase (2.81× lift, 1.8%).
- **Observation:** SQL exhibits higher prevalence in Data Analytics (63.7%) than in Data Science (46.2%). Combined with high lift for BI and reporting tools, the category centers heavily on data querying, dashboarding, and business reporting.

### 3. AI Engineering (3,345 postings — 13.7% of dataset)
- **Top In-Demand:** LLMs / Generative AI (81.8%, 2,735 jobs), Python (67.7%, 2,264 jobs), Azure (34.6%, 1,157 jobs), CI/CD (32.8%, 1,098 jobs), AWS (28.3%, 946 jobs).
- **Highest Distinctiveness Lift:** LangChain (4.97× lift, 20.9%), TypeScript (4.69× lift, 11.9%), LLMs / Generative AI (3.27× lift, 81.8%), Hugging Face (3.16× lift, 6.5%).
- **Observation:** Postings in this category show heavy demand for modern generative AI and LLM stacks, alongside software engineering practices (CI/CD at 32.8% and TypeScript at 11.9%).

### 4. Data Science (2,558 postings — 10.4% of dataset)
- **Top In-Demand:** Python (73.8%, 1,887 jobs), SQL (46.2%, 1,182 jobs), LLMs / Generative AI (37.9%, 970 jobs), Azure (22.0%, 563 jobs), AWS (20.9%, 535 jobs).
- **Highest Distinctiveness Lift:** XGBoost (5.51× lift, 4.1%), Scikit-learn (4.33× lift, 17.0%), NumPy (4.02× lift, 9.1%), R (3.43× lift, 16.4%), Pandas (3.34× lift, 14.1%).
- **Observation:** Python shows its highest prevalence in Data Science and ML/AI. The category is distinctively characterized by classical machine learning packages (Scikit-learn, XGBoost) and statistical computing in R.

### 5. ML/AI (1,411 postings — 5.8% of dataset)
- **Top In-Demand:** Python (74.4%, 1,050 jobs), LLMs / Generative AI (43.7%, 617 jobs), PyTorch (40.0%, 565 jobs), CI/CD (26.6%, 375 jobs), AWS (26.2%, 370 jobs).
- **Highest Distinctiveness Lift:** OpenCV (9.02× lift, 2.8%), C++ (6.74× lift, 12.7%), PyTorch (6.70× lift, 40.0%), TensorFlow (5.74× lift, 25.2%), MLflow (5.65× lift, 15.5%).
- **Observation:** Deep learning frameworks (PyTorch at 40.0%, TensorFlow at 25.2%) and specialized programming languages (C++ at 12.7%) exhibit substantial concentration in this category.

---

## 5. Guided Tour: How to Explore the Dashboard

The dashboard (`app.py`) is structured as a unified single-page Streamlit interface with a persistent filter bar:

1. **Step 1: Select Your Occupational Lens**
   Use the global filter bar to select an occupation (e.g., *Data Analytics*). Summary KPI cards, prevalence charts, and distinctiveness tables dynamically adjust to that role.
2. **Step 2: Filter by Skill Family**
   Isolate specific technical domains — *Programming languages*, *Databases & data warehouses*, *BI & visualization*, *Cloud & infrastructure*, or *ML/AI frameworks & tools* — to compare related technologies.
3. **Step 3: Inspect the Prevalence-vs-Lift Scatter Plot**
   Hover over data points on the scatter plot to inspect posting counts, within-category percentages, and lift values against the $\text{Lift} = 1.00$ parity line.
4. **Step 4: Examine Geographic Distributions**
   Review the European choropleth map for observed posting counts, and inspect cross-country composition bars for countries meeting the sample-size filter.

---

## 6. Geographic Distribution and the Minimum Sample-Size Filter (N ≥ 300)

The dashboard presents raw posting volumes across all **27 EU member states** on an interactive map. However, for the cross-country occupational composition chart (100% stacked bar chart), the application applies a **practical minimum sample-size filter of N ≥ 300 observed postings**.

This filter is a practical threshold designed to avoid displaying percentage breakdowns from small, volatile samples where a few postings could substantially skew category shares. It is not a guarantee of population representativeness.

Exactly **11 member states** meet this criterion in the dataset:

| Member State | ISO Code | Observed Postings | Observed Occupational Distribution in Snapshot |
|---|---|---|---|
| **France** | `FR` | 4,972 | DE: 55.0%, DA: 15.6%, AI Eng: 14.3%, DS: 10.7%, ML/AI: 4.4% |
| **Netherlands** | `NL` | 3,307 | DE: 66.4%, DA: 11.3%, AI Eng: 9.9%, DS: 8.6%, ML/AI: 3.8% |
| **Poland** | `PL` | 2,826 | DE: 67.6%, AI Eng: 11.2%, DA: 10.5%, DS: 5.7%, ML/AI: 5.0% |
| **Spain** | `ES` | 2,740 | DE: 63.9%, DA: 11.5%, AI Eng: 11.2%, DS: 8.4%, ML/AI: 4.9% |
| **Germany** | `DE` | 2,396 | DE: 30.9%, DS: 20.4%, AI Eng: 20.2%, DA: 18.2%, ML/AI: 10.2% |
| **Italy** | `IT` | 2,129 | DE: 53.1%, DA: 16.5%, DS: 13.9%, AI Eng: 13.2%, ML/AI: 3.2% |
| **Portugal** | `PT` | 1,366 | DE: 61.6%, DA: 14.6%, AI Eng: 11.6%, DS: 7.0%, ML/AI: 5.1% |
| **Belgium** | `BE` | 1,012 | DE: 57.6%, DA: 19.2%, AI Eng: 12.5%, DS: 8.0%, ML/AI: 2.7% |
| **Sweden** | `SE` | 885 | DE: 56.3%, AI Eng: 15.9%, DA: 11.1%, DS: 8.9%, ML/AI: 7.8% |
| **Ireland** | `IE` | 470 | DE: 53.6%, AI Eng: 14.7%, DA: 11.9%, ML/AI: 11.9%, DS: 7.9% |
| **Denmark** | `DK` | 416 | DE: 56.5%, AI Eng: 12.5%, DA: 11.1%, DS: 10.6%, ML/AI: 9.4% |

*Note: Member states with fewer than 300 postings remain visible on the map with their observed posting counts, but are excluded from cross-country composition comparisons to avoid misleading percentage comparisons.*

---

## 7. Data Pipeline, Testing, and Methodological Scope

The EU Data Career Compass is supported by an automated, testable Python pipeline:

- **Dataset Scope:** The dataset consists of an audited snapshot of 24,488 unique FreeHire job postings collected up to 7 November 2026 across 27 EU member states. It represents an observed sample from a specific online job platform, not an exhaustive or statistically balanced census of all European vacancies.
- **Hybrid Skill Extraction:** Skill detection uses a controlled vocabulary of 52 canonical technical skills. It prioritizes platform-level tags and applies delimiter-guarded regex patterns (including negative lookaheads to disambiguate `R` from `R&D` and `Excel` from phrases like `"excel in"`).
- **Automated Software Testing:** The codebase includes **397 automated software tests** (`pytest`) verifying data transformation logic, Lift calculations, support threshold filtering, atomic JSON serialization, and dashboard rendering.
- **Extraction Validation:** In addition to automated unit tests, skill extraction accuracy was evaluated through manual annotation holdouts: a 50-posting deterministic sample audit (achieving 98.8% precision and 100% recall across evaluable decisions) and a 30-posting holdout audit for R (achieving 96.7% precision). These tests validate code execution and regex accuracy on the collected text, but do not imply population-level representativeness.
- **Seniority Reporting:** Seniority information is available for 42.9% of postings in the dataset (10,494 postings; 57.1% unstated). The dashboard reports this as an observed descriptive metric without attempting algorithmic imputation.
- **Reproducibility:** The repository uses committed precomputed analytics (`data/processed/analytics_summary.json`) and isolated CI fixtures, allowing the dashboard and standard test suite to run deterministically without requiring the raw dataset.

---

## 8. Launch the Dashboard

The dashboard can be executed locally in seconds using `uv`:

```bash
# Clone the repository
git clone https://github.com/esst-prog2/EU-Data-Skill-Demand.git
cd EU-Data-Skill-Demand

# Launch the Streamlit application using precomputed analytics
uv run streamlit run app.py
```

### Navigating Career Exploration

1. **Identify Common Technical Foundations:** Review skills with high overall prevalence across multiple roles (such as SQL and Git) to understand shared baseline expectations.
2. **Examine Role-Specific Specializations:** Inspect skills that exhibit strong distinctiveness within your target category — such as Apache Spark and Airflow in Data Engineering, Power BI and Excel in Data Analytics, or Scikit-learn and XGBoost in Data Science.
3. **Use Evidence-Based Market Context:** Rely on observed vacancy counts and distinctiveness metrics across 24,488 postings to inform your technical learning priorities with empirical context.
