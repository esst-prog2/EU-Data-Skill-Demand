# Threshold Sensitivity Analysis: Distinctive-Skill Ranking (`N >= 20`, `Prevalence >= 1.5%`)

## 1. Purpose & Context

In the EU Data Jobs & Skill Demand Analysis dashboard, each occupational category's **Most Distinctive Skills** chart ranks skills by corpus-relative lift:

$$\text{Lift}(\text{skill}, \text{category}) = \frac{P(\text{skill} \mid \text{category})}{P(\text{skill} \mid \text{corpus})}$$

Before ranking skills with $\text{Lift} > 1.0$ and selecting the Top 10 for display (`top_n = 10`), `filter_distinctive_skills` in `src/analytics.py` requires a skill to satisfy two support thresholds within the selected occupational category:
- **Minimum posting count:** `count >= 20`
- **Minimum within-category prevalence:** `prevalence >= 1.5%` (`0.015`)

This report documents the empirical sensitivity analysis across the audited snapshot of **22,985 unique EU-27 FreeHire job postings** (`data/raw/freehire_eu_raw.json`) and the **52-skill controlled vocabulary** (`data/fixtures/skills_vocabulary.json`), showing what changes when these two thresholds are lowered or raised.

---

## 2. Unequal Category Sizes & Complementary Roles of the Two Thresholds

The five FreeHire occupational categories in the observed corpus differ in sample size by more than $13\times$—ranging from **1,132 postings** in `ML/AI` to **15,090 postings** in `Data Engineering` (65.7% of the entire corpus).

Because a skill must satisfy **both** $\text{count} \ge N_{\min}$ and $\text{count} / N_{\text{category}} \ge P_{\min}$, the effective minimum posting count required in a category of size $N_{\text{category}}$ is:

$$\text{Effective Minimum Postings} = \max\!\left(N_{\min}, \; \lceil N_{\text{category}} \times P_{\min} \rceil\right)$$

| Occupational Category | Category ID | Observed Postings ($N$) | Corpus Share | $0.5\%$ in Postings | $1.0\%$ in Postings | $1.5\%$ in Postings | $2.0\%$ in Postings | $3.0\%$ in Postings | Effective Floor at $(20, 1.5\%)$ |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Data Analytics** | `data_analytics` | 2,440 | 10.6% | 12.2 | 24.4 | 36.6 | 48.8 | 73.2 | **1.5% prevalence** ($\ge 37$ postings) |
| **Data Engineering** | `data_engineering` | 15,090 | 65.7% | 75.5 | 150.9 | 226.4 | 301.8 | 452.7 | **1.5% prevalence** ($\ge 227$ postings) |
| **Data Science** | `data_science` | 2,009 | 8.7% | 10.0 | 20.1 | 30.1 | 40.2 | 60.3 | **1.5% prevalence** ($\ge 31$ postings) |
| **ML/AI** | `ml_ai` | 1,132 | 4.9% | 5.7 | 11.3 | 17.0 | 22.6 | 34.0 | **20 postings** ($\ge 20$ postings, $1.77\%$) |
| **AI Engineering** | `ai_engineering` | 2,314 | 10.1% | 11.6 | 23.1 | 34.7 | 46.3 | 69.4 | **1.5% prevalence** ($\ge 35$ postings) |

### Why Both Thresholds Are Used
1. **`1.5%` within-category prevalence scales with category size:** In the four larger occupations (`Data Engineering`, `Data Analytics`, `AI Engineering`, and `Data Science`), $1.5\%$ corresponds to between **31 and 227 postings**. A flat 20-posting cutoff alone would be almost non-binding in `Data Engineering` (where 20 postings is just $0.13\%$ of the category).
2. **`20 postings` provides an absolute minimum support floor for smaller categories:** In the smallest category (`ML/AI`, $N = 1,132$), $1.5\%$ corresponds to **$17.0$ postings**. The `N >= 20` rule guarantees that a skill is backed by at least 20 observed postings ($1.77\%$) before being ranked by lift. *(Note: In the current 52-skill vocabulary, no `ML/AI` skill has a count of 17, 18, or 19—the nearest below 20 are `Elasticsearch` at $N=16$ [$1.41\%$] and `Redis` at $N=15$ [$1.33\%$]. Thus at $P_{\min} = 1.5\%$ the two rules select the same `ML/AI` skills, whereas `N >= 20` actively blocks `Elasticsearch` and `Redis` in `ML/AI` when $P_{\min}$ is lowered to $\le 1.0\%$, and blocks `Go` [$N=18$, $0.78\%$] and `XGBoost` [$N=16$, $0.69\%$] in `AI Engineering` when $P_{\min}$ is lowered to $0.5\%$.)*

---

## 3. Full Sensitivity Grid Across 25 Threshold Combinations

Across all 5 occupations and 52 vocabulary skills ($5 \times 52 = 260$ category-skill pairs), **105 category-skill pairs** have $\text{Lift} > 1.0$ prior to support filtering.

Because `filter_distinctive_skills` caps the dashboard visual at `top_n = 10` skills per category, changing thresholds affects both:
- **Eligible category-skill pairs (uncapped):** Total pairs meeting `count >= Min postings`, `prevalence >= Min prevalence`, and `lift > 1.0`.
- **Displayed Top-10 skills (`[in brackets]`):** Number of bars rendered in the dashboard chart (`max 10` per category, `max 50` across all 5 categories).

| Min postings | Min prevalence | Total skills (`Eligible [Displayed]`) | Data Analytics ($N=2,440$) | Data Engineering ($N=15,090$) | Data Science ($N=2,009$) | ML/AI ($N=1,132$) | AI Engineering ($N=2,314$) |
| ---: | ---: | :---: | :---: | :---: | :---: | :---: | :---: |
| *1 (Unfiltered)* | *0.0%* | *105 [50]* | *10 [10]* | *25 [10]* | *19 [10]* | *26 [10]* | *25 [10]* |
| 5 | 0.5% | 99 [50] | 10 [10] | 25 [10] | 17 [10] | 24 [10] | 23 [10] |
| 5 | 1.0% | 96 [50] | 10 [10] | 24 [10] | 17 [10] | 24 [10] | 21 [10] |
| 5 | 1.5% | 90 [49] | 9 [9] | 22 [10] | 16 [10] | 22 [10] | 21 [10] |
| 5 | 2.0% | 89 [49] | 9 [9] | 22 [10] | 16 [10] | 22 [10] | 20 [10] |
| 5 | 3.0% | 80 [48] | 8 [8] | 19 [10] | 15 [10] | 20 [10] | 18 [10] |
| 10 | 0.5% | 99 [50] | 10 [10] | 25 [10] | 17 [10] | 24 [10] | 23 [10] |
| 10 | 1.0% | 96 [50] | 10 [10] | 24 [10] | 17 [10] | 24 [10] | 21 [10] |
| 10 | 1.5% | 90 [49] | 9 [9] | 22 [10] | 16 [10] | 22 [10] | 21 [10] |
| 10 | 2.0% | 89 [49] | 9 [9] | 22 [10] | 16 [10] | 22 [10] | 20 [10] |
| 10 | 3.0% | 80 [48] | 8 [8] | 19 [10] | 15 [10] | 20 [10] | 18 [10] |
| 20 | 0.5% | 95 [50] | 10 [10] | 25 [10] | 17 [10] | 22 [10] | 21 [10] |
| 20 | 1.0% | 94 [50] | 10 [10] | 24 [10] | 17 [10] | 22 [10] | 21 [10] |
| **20 (Current)** | **1.5%** | **90 [49]** | **9 [9]** | **22 [10]** | **16 [10]** | **22 [10]** | **21 [10]** |
| 20 | 2.0% | 89 [49] | 9 [9] | 22 [10] | 16 [10] | 22 [10] | 20 [10] |
| 20 | 3.0% | 80 [48] | 8 [8] | 19 [10] | 15 [10] | 20 [10] | 18 [10] |
| 30 | 0.5% | 91 [49] | 9 [9] | 25 [10] | 16 [10] | 20 [10] | 21 [10] |
| 30 | 1.0% | 90 [49] | 9 [9] | 24 [10] | 16 [10] | 20 [10] | 21 [10] |
| 30 | 1.5% | 88 [49] | 9 [9] | 22 [10] | 16 [10] | 20 [10] | 21 [10] |
| 30 | 2.0% | 87 [49] | 9 [9] | 22 [10] | 16 [10] | 20 [10] | 20 [10] |
| 30 | 3.0% | 80 [48] | 8 [8] | 19 [10] | 15 [10] | 20 [10] | 18 [10] |
| 50 | 0.5% | 87 [49] | 9 [9] | 25 [10] | 15 [10] | 18 [10] | 20 [10] |
| 50 | 1.0% | 86 [49] | 9 [9] | 24 [10] | 15 [10] | 18 [10] | 20 [10] |
| 50 | 1.5% | 84 [49] | 9 [9] | 22 [10] | 15 [10] | 18 [10] | 20 [10] |
| 50 | 2.0% | 84 [49] | 9 [9] | 22 [10] | 15 [10] | 18 [10] | 20 [10] |
| 50 | 3.0% | 78 [48] | 8 [8] | 19 [10] | 15 [10] | 18 [10] | 18 [10] |

---

## 4. Current Production Baseline (`N >= 20`, `Prevalence >= 1.5%`)

At the current production threshold (`min_count = 20`, `min_prevalence = 1.5%`), **90 category-skill pairs** (spanning **46 unique skills** out of 52) pass eligibility, and **49 skills** are displayed across the five Top-10 charts (`9` in Data Analytics and `10` in each of the other four occupations).

### Data Analytics (`data_analytics`, $N = 2,440$) — 9 Eligible / 9 Displayed (of 10 with $\text{Lift} > 1.0$)

| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |
| ---: | :--- | :--- | ---: | ---: | ---: |
| 1 | **Metabase** | BI & visualization | 63 | 2.58% (2.6%) | **4.95×** |
| 2 | **Looker** | BI & visualization | 315 | 12.91% (12.9%) | **4.42×** |
| 3 | **Excel** | BI & visualization | 78 | 3.20% (3.2%) | **4.40×** |
| 4 | **Tableau** | BI & visualization | 530 | 21.72% (21.7%) | **4.12×** |
| 5 | **Power BI** | BI & visualization | 981 | 40.20% (40.2%) | **2.89×** |
| 6 | **Qlik** | BI & visualization | 100 | 4.10% (4.1%) | **2.77×** |
| 7 | **BigQuery** | Databases & data warehouses | 280 | 11.48% (11.5%) | **1.46×** |
| 8 | **dbt** | Cloud & infrastructure | 423 | 17.34% (17.3%) | **1.44×** |
| 9 | **SQL** | Programming languages | 1,545 | 63.32% (63.3%) | **1.35×** |

- **Excluded skills with $\text{Lift} > 1.0$ (below support threshold):** `Apache Superset` ($N=27$, 1.11%, 3.18×).

### Data Engineering (`data_engineering`, $N = 15,090$) — 22 Eligible / 10 Displayed (of 25 with $\text{Lift} > 1.0$)

| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |
| ---: | :--- | :--- | ---: | ---: | ---: |
| 1 | **Apache Kafka** | Cloud & infrastructure | 1,633 | 10.82% (10.8%) | **1.37×** |
| 2 | **Scala** | Programming languages | 1,483 | 9.83% (9.8%) | **1.37×** |
| 3 | **MS SQL Server** | Databases & data warehouses | 721 | 4.78% (4.8%) | **1.33×** |
| 4 | **Apache Airflow** | Cloud & infrastructure | 2,543 | 16.85% (16.9%) | **1.30×** |
| 5 | **Apache Spark** | Cloud & infrastructure | 4,453 | 29.51% (29.5%) | **1.29×** |
| 6 | **Terraform** | Cloud & infrastructure | 1,499 | 9.93% (9.9%) | **1.29×** |
| 7 | **Databricks** | Cloud & infrastructure | 3,904 | 25.87% (25.9%) | **1.27×** |
| 8 | **Amazon Redshift** | Databases & data warehouses | 595 | 3.94% (3.9%) | **1.27×** |
| 9 | **Bash / Shell** | Programming languages | 425 | 2.82% (2.8%) | **1.27×** |
| 10 | **Snowflake** | Databases & data warehouses | 2,447 | 16.22% (16.2%) | **1.25×** |

- **Eligible skills ranked #11–#22 (outside Top-10 display):** `Oracle DB` (1.24×, 2.94%), `MongoDB` (1.23×, 2.39%), `dbt` (1.22×, 14.70%), `Java` (1.18×, 8.55%), `PostgreSQL` (1.15×, 5.09%), `Azure` (1.14×, 32.68%), `BigQuery` (1.14×, 8.93%), `CI/CD` (1.11×, 23.80%), `SQL` (1.10×, 51.58%), `AWS` (1.07×, 25.53%), `GCP` (1.07×, 19.00%), `Git` (1.01×, 16.24%).
- **Excluded skills with $\text{Lift} > 1.0$ (below support threshold):** `Cassandra` ($N=119$, 0.79%, 1.29×), `MySQL` ($N=215$, 1.42%, 1.16×), `Elasticsearch` ($N=198$, 1.31%, 1.15×).

### Data Science (`data_science`, $N = 2,009$) — 16 Eligible / 10 Displayed (of 19 with $\text{Lift} > 1.0$)

| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |
| ---: | :--- | :--- | ---: | ---: | ---: |
| 1 | **XGBoost** | ML/AI frameworks & tools | 78 | 3.88% (3.9%) | **6.92×** |
| 2 | **Scikit-learn** | ML/AI frameworks & tools | 305 | 15.18% (15.2%) | **5.33×** |
| 3 | **NumPy** | ML/AI frameworks & tools | 167 | 8.31% (8.3%) | **4.24×** |
| 4 | **TensorFlow** | ML/AI frameworks & tools | 269 | 13.39% (13.4%) | **3.74×** |
| 5 | **Pandas** | ML/AI frameworks & tools | 254 | 12.64% (12.6%) | **3.42×** |
| 6 | **PyTorch** | ML/AI frameworks & tools | 308 | 15.33% (15.3%) | **3.31×** |
| 7 | **MLflow** | ML/AI frameworks & tools | 109 | 5.43% (5.4%) | **2.47×** |
| 8 | **R** | Programming languages | 105 | 5.23% (5.2%) | **2.43×** |
| 9 | **Hugging Face** | ML/AI frameworks & tools | 72 | 3.58% (3.6%) | **2.31×** |
| 10 | **LLMs / Generative AI** | ML/AI frameworks & tools | 640 | 31.86% (31.9%) | **1.67×** |

- **Eligible skills ranked #11–#16 (outside Top-10 display):** `LangChain` (1.53×, 5.18%), `Tableau` (1.48×, 7.81%), `C++` (1.45×, 2.14%), `Python` (1.23×, 67.75%), `Docker` (1.09×, 9.76%), `Git` (1.04×, 16.67%).
- **Excluded skills with $\text{Lift} > 1.0$ (below support threshold):** `Julia` ($N=6$, 0.30%, 2.64×), `OpenCV` ($N=6$, 0.30%, 1.63×), `MySQL` ($N=27$, 1.34%, 1.10×).

### ML/AI (`ml_ai`, $N = 1,132$) — 22 Eligible / 10 Displayed (of 26 with $\text{Lift} > 1.0$)

| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |
| ---: | :--- | :--- | ---: | ---: | ---: |
| 1 | **OpenCV** | ML/AI frameworks & tools | 24 | 2.12% (2.1%) | **11.60×** |
| 2 | **PyTorch** | ML/AI frameworks & tools | 434 | 38.34% (38.3%) | **8.27×** |
| 3 | **C++** | Programming languages | 129 | 11.40% (11.4%) | **7.73×** |
| 4 | **Hugging Face** | ML/AI frameworks & tools | 130 | 11.48% (11.5%) | **7.41×** |
| 5 | **TensorFlow** | ML/AI frameworks & tools | 284 | 25.09% (25.1%) | **7.01×** |
| 6 | **MLflow** | ML/AI frameworks & tools | 155 | 13.69% (13.7%) | **6.23×** |
| 7 | **Scikit-learn** | ML/AI frameworks & tools | 143 | 12.63% (12.6%) | **4.43×** |
| 8 | **XGBoost** | ML/AI frameworks & tools | 26 | 2.30% (2.3%) | **4.09×** |
| 9 | **NumPy** | ML/AI frameworks & tools | 58 | 5.12% (5.1%) | **2.61×** |
| 10 | **Docker** | Cloud & infrastructure | 232 | 20.49% (20.5%) | **2.30×** |

- **Eligible skills ranked #11–#22 (outside Top-10 display):** `LLMs / Generative AI` (2.28×, 43.46%), `LangChain` (2.16×, 7.33%), `Kubernetes` (2.08×, 19.17%), `R` (1.97×, 4.24%), `Pandas` (1.67×, 6.18%), `TypeScript` (1.64×, 3.80%), `Python` (1.26×, 68.99%), `AWS` (1.15×, 27.47%), `Git` (1.14×, 18.29%), `CI/CD` (1.13×, 24.12%), `GCP` (1.05×, 18.64%), `Java` (1.01×, 7.33%).
- **Excluded skills with $\text{Lift} > 1.0$ (below support threshold):** `Julia` ($N=3$, 0.27%, 2.34×), `Redis` ($N=15$, 1.33%, 2.02×), `Elasticsearch` ($N=16$, 1.41%, 1.24×), `Apache Superset` ($N=4$, 0.35%, 1.02×).

### AI Engineering (`ai_engineering`, $N = 2,314$) — 21 Eligible / 10 Displayed (of 25 with $\text{Lift} > 1.0$)

| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |
| ---: | :--- | :--- | ---: | ---: | ---: |
| 1 | **LangChain** | ML/AI frameworks & tools | 474 | 20.48% (20.5%) | **6.04×** |
| 2 | **TypeScript** | Programming languages | 267 | 11.54% (11.5%) | **4.99×** |
| 3 | **LLMs / Generative AI** | ML/AI frameworks & tools | 1,737 | 75.06% (75.1%) | **3.93×** |
| 4 | **Hugging Face** | ML/AI frameworks & tools | 135 | 5.83% (5.8%) | **3.77×** |
| 5 | **PyTorch** | ML/AI frameworks & tools | 261 | 11.28% (11.3%) | **2.43×** |
| 6 | **Redis** | Databases & data warehouses | 35 | 1.51% (1.5%) | **2.30×** |
| 7 | **TensorFlow** | ML/AI frameworks & tools | 187 | 8.08% (8.1%) | **2.26×** |
| 8 | **Docker** | Cloud & infrastructure | 445 | 19.23% (19.2%) | **2.16×** |
| 9 | **C++** | Programming languages | 69 | 2.98% (3.0%) | **2.02×** |
| 10 | **Kubernetes** | Cloud & infrastructure | 388 | 16.77% (16.8%) | **1.82×** |

- **Eligible skills ranked #11–#21 (outside Top-10 display):** `MLflow` (1.75×, 3.85%), `Scikit-learn` (1.65×, 4.71%), `CI/CD` (1.35×, 28.87%), `AWS` (1.26×, 29.90%), `Java` (1.25×, 9.03%), `GCP` (1.20×, 21.26%), `R` (1.19×, 2.55%), `Git` (1.16×, 18.63%), `Python` (1.15×, 63.48%), `PostgreSQL` (1.13×, 5.01%), `Azure` (1.12×, 32.02%).
- **Excluded skills with $\text{Lift} > 1.0$ (below support threshold):** `OpenCV` ($N=11$, 0.48%, 2.60×), `Go` ($N=18$, 0.78%, 2.45×), `Julia` ($N=6$, 0.26%, 2.29×), `XGBoost` ($N=16$, 0.69%, 1.23×).

---

## 5. Trade-Off Analysis: Lowering vs. Raising Thresholds

Because corpus-relative lift places $P(\text{skill} \mid \text{corpus})$ in the denominator, skills with small corpus counts can achieve high lift multipliers from relatively few category mentions. Consequently, changing the support cutoffs primarily changes **which skills occupy the Top-10 slots** rather than the length of the chart.

### A. What Happens When Thresholds Are Lowered (Admitting Low-Prevalence / Low-Support Skills)

1. **`Cassandra` vs. `Snowflake` in `Data Engineering` ($N = 15,090$):**
   - At the current `(20, 1.5%)` cutoff, **`Snowflake`** ($N = 2,447$, prevalence **16.22%**, lift **1.25×**) holds Rank #10 in the `Data Engineering` Top 10.
   - When minimum prevalence is lowered to **`0.5%`** (for any $N_{\min} \in \{5, 10, 20, 30, 50\}$), **`Cassandra`** ($N = 119$, prevalence **0.79%**, lift **1.29×**) becomes eligible, enters at **Rank #7** (behind `Apache Spark` [29.51%] and `Terraform` [9.93%], which share `1.29×` rounded lift with higher prevalence), and pushes **`Snowflake`** (present in over $20\times$ as many Data Engineering postings) out of the Top-10 chart to Rank #11.
2. **`Go` vs. `Kubernetes` in `AI Engineering` ($N = 2,314$):**
   - At the current `(20, 1.5%)` cutoff, **`Kubernetes`** ($N = 388$, prevalence **16.77%**, lift **1.82×**) holds Rank #10 in `AI Engineering`.
   - When thresholds are lowered to **`N >= 10, Prevalence >= 0.5%`** (or `N >= 5, Prevalence >= 0.5%`), **`Go`** ($N = 18$, prevalence **0.78%**, lift **2.45×**) enters at **Rank #5** and displaces **`Kubernetes`** out of the Top-10 chart to Rank #11 (while **`XGBoost`** [$N = 16$, $0.69\%$, $1.23\times$] also enters the `AI Engineering` eligible pool outside the Top 10).
3. **Additional Low-Support / Low-Prevalence Admissions:**
   - In `Data Analytics`, lowering minimum prevalence to **`1.0%`** or **`0.5%`** (for $N_{\min} \in \{5, 10, 20\}$, i.e., when the minimum-postings cutoff is at most 20) admits **`Apache Superset`** ($N = 27$, prevalence **1.11%**, lift **3.18×**) at **Rank #5**, expanding the `Data Analytics` chart from 9 to 10 displayed skills.
   - In `ML/AI`, lowering thresholds to **`N >= 10, Prevalence >= 1.0%`** (or `0.5%`) admits **`Redis`** ($N = 15$, $1.33\%$, $2.02\times$) and **`Elasticsearch`** ($N = 16$, $1.41\%$, $1.24\times$) into the eligible pool outside the Top 10 (increasing `ML/AI` eligible skills from 22 to 24 without changing the Top 10).
   - Without support thresholds (`N >= 1, Prevalence >= 0.0%`), sub-10-posting skills such as **`Julia`** in `Data Science` ($N = 6$, prevalence **0.30%**, lift **2.64×**) jump directly into the Top 10 at Rank #7 (displacing **`LLMs / Generative AI`** with $N = 640$, 31.86%).

### B. What Happens When Thresholds Are Raised (Removing Plausible Specialist Skills)

1. **`OpenCV` and `XGBoost` in `ML/AI` ($N = 1,132$):**
   - At `(20, 1.5%)`, **`OpenCV`** ($N = 24$, prevalence **2.12%**, lift **11.60×**) is Rank #1 and **`XGBoost`** ($N = 26$, prevalence **2.30%**, lift **4.09×**) is Rank #8 in `ML/AI`.
   - Raising minimum postings from **`20` to `30`** (even while keeping prevalence at `1.5%`)—or raising minimum prevalence to **`3.0%`**—eliminates **both `OpenCV` and `XGBoost`** from the `ML/AI` ranking (replaced in the Top 10 by `LLMs / Generative AI` [2.28×] and `LangChain` [2.16×]).
2. **`Metabase` in `Data Analytics` ($N = 2,440$):**
   - At `(20, 1.5%)`, **`Metabase`** ($N = 63$, prevalence **2.58%**, lift **4.95×**) is Rank #1 in `Data Analytics`.
   - Raising minimum prevalence to **`3.0%`** removes **`Metabase`**, shrinking the `Data Analytics` chart from 9 to 8 skills.
3. **`Redis` in `AI Engineering` and `Bash / Shell` in `Data Engineering`:**
   - Raising minimum prevalence from **`1.5%` to `2.0%`** (or raising minimum postings to **`50`**) removes **`Redis`** ($N = 35$, prevalence **1.51%**, lift **2.30×**, Rank #6) from `AI Engineering` (replaced in the Top 10 by `MLflow` [1.75×]). Raising minimum prevalence to **`3.0%`** additionally removes `C++` ($N = 69$, **2.98%**, **2.02×**, Rank #9) from the Top 10 and `R` ($N = 59$, **2.55%**, **1.19×**, Rank #17) from the eligible pool.
   - Raising minimum prevalence to **`3.0%`** removes **`Bash / Shell`** ($N = 425$, prevalence **2.82%**, lift **1.27×**, Rank #9) from the `Data Engineering` Top 10, along with **`Oracle DB`** ($N = 444$, **2.94%**, **1.24×**, Rank #11) and **`MongoDB`** ($N = 360$, **2.39%**, **1.23×**, Rank #12) from the eligible pool, bringing #13 **`dbt`** ($N = 2,218$, **14.70%**, **1.22×**) into the Top 10 at Rank #10.

### C. Summary Table of Top-10 and Eligible-Pool Transitions Across Key Regimes

| Occupation | Looser (`N >= 10, P >= 0.5%`) vs. Baseline (`20, 1.5%`) | Stricter Count (`N >= 30, P >= 1.5%`) vs. Baseline | Stricter Prevalence (`N >= 20, P >= 3.0%`) vs. Baseline |
| :--- | :--- | :--- | :--- |
| **Data Analytics** | **Top 10 In:** `Apache Superset` *(display 9 → 10; Pool +1: `Apache Superset`)* | No change | **Top 10 Out:** `Metabase` *(display 9 → 8; Pool -1: `Metabase`)* |
| **Data Engineering** | **Top 10 In:** `Cassandra`; **Top 10 Out:** `Snowflake` *(Pool +3: `Cassandra`, `MySQL`, `Elasticsearch`)* | No change | **Top 10 In:** `dbt`; **Top 10 Out:** `Bash / Shell` *(Pool -3: `Bash / Shell`, `Oracle DB`, `MongoDB`)* |
| **Data Science** | Top 10 unchanged *(Pool +1: `MySQL`)* | No change | Top 10 unchanged *(Pool -1: `C++`)* |
| **ML/AI** | Top 10 unchanged *(Pool +2: `Redis`, `Elasticsearch`)* | **Top 10 In:** `LLMs / Generative AI`, `LangChain`; **Top 10 Out:** `OpenCV`, `XGBoost` *(Pool -2: `OpenCV`, `XGBoost`)* | **Top 10 In:** `LLMs / Generative AI`, `LangChain`; **Top 10 Out:** `OpenCV`, `XGBoost` *(Pool -2: `OpenCV`, `XGBoost`)* |
| **AI Engineering** | **Top 10 In:** `Go`; **Top 10 Out:** `Kubernetes` *(Pool +2: `Go`, `XGBoost`)* | No change | **Top 10 In:** `MLflow`, `Scikit-learn`; **Top 10 Out:** `Redis`, `C++` *(Pool -3: `Redis`, `C++`, `R`)* |

---

## 6. Methodological Caveats & Interpretation

1. **Heuristic Design Choice, Not Statistical Optimality:**
   The `N >= 20` and `prevalence >= 1.5%` thresholds are practical display heuristics chosen to balance minimum sample support against specialist skill coverage in this **observed EU-27 job-posting corpus**. They are not statistically optimal cutoffs and do not represent inferential significance tests.
2. **Low-Support and Low-Prevalence vs. "Noise":**
   All 52 canonical skills in the controlled vocabulary are legitimate technical tools. Skills excluded by the thresholds (such as `Go` with $N=18$ in AI Engineering, `Cassandra` with $0.79\%$ in Data Engineering, or `Apache Superset` with $1.11\%$ in Data Analytics) are **low-support** or **low-prevalence** within those categories—not extraction noise.
3. **`Data Engineering` Corpus Dominance ($65.7\%$) and Lift Compression:**
   Because `Data Engineering` accounts for **15,090 of the 22,985 postings (65.7%)**, the corpus-wide baseline $P(\text{skill} \mid \text{corpus})$ is heavily weighted toward Data Engineering. Mathematically, the maximum possible lift for any skill in `Data Engineering` is bounded at $1 / (15090 / 22985) = 1.52\times$. As a result, `Data Engineering` lift scores cluster tightly between $1.01\times$ and $1.37\times$, whereas smaller categories like `ML/AI` ($4.9\%$ of the corpus) reach lifts up to $11.60\times$.
4. **Non-Representativeness of the Observed Corpus:**
   All prevalence and lift values describe patterns within the audited FreeHire snapshot of 22,985 postings and do not estimate the true occupational or geographic distribution of the broader EU labour market.

---

## 7. Reproducibility

Run the sensitivity analysis script from the repository root:

```bash
uv run python analysis/sensitivity_analysis.py
```
