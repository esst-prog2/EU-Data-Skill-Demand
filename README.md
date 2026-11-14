# EU Data Jobs & Skill Demand Analysis

## 1. Product Showcase & Demo

> **Interactive Career Exploration Showcase:** For the complete evidence-based career guide, the 4-quadrant skill framework (*Universal Currency*, *Role Superpowers*, *Niche Specializations*, *Peripheral Skills*), and detailed breakdowns across all five data professions, see [**docs/promo_page.md**](docs/promo_page.md).

In a five-minute screenshot presentation, I introduce the single-page Streamlit dashboard (`app.py`), which analyses 24,488 job postings across all 27 EU member states and five data-related occupations as an evidence-based career exploration tool. I start with the dashboard header, sticky filter bar and four summary KPI cards, then show different job-family filter states to illustrate how skill demand varies across occupations, highlighting Python's prevalence of 73.8% in Data Science compared with 42.2% in Data Analytics (0.74× lift). Next, I explore the prevalence-versus-lift scatter plot, demonstrating how the technical skill-family filter changes the displayed skills and how the Lift = 1.00 reference line distinguishes skills with average occupational representation from those that are particularly characteristic of specific occupations. I then present the European choropleth map and the 100% stacked occupational composition chart, comparing the 11 countries with at least 300 job postings. Finally, I show the complete skill demand table and methodological notes, including seniority information available for 42.9% of postings, and explain how the dashboard uses precomputed analytics stored in `data/processed/analytics_summary.json`.

### Scope Decisions

- **Project focus:** I cut the CV-matching and personalized skill-gap component from the original concept and focused the project on the market-analysis side, measuring technical skill demand across data-related occupations and geographic contexts in an observed EU-27 job-posting corpus.
- **Data source:** I moved from SerpAPI and RemoteOK to FreeHire because FreeHire provides a larger, more consistently structured EU-wide job-posting corpus with occupational categories and country-level enrichment, making systematic comparison across occupations and countries more feasible.
- **Geographic scope:** I expanded from a Hungary-focused analysis to the EU-27 because the broader corpus provides enough geographic and occupational variation to study how technical skill demand differs across both occupations and labour-market contexts.
- **Seniority:** I moved away from using seniority as a primary analytical dimension because seniority information is missing for 57.1% of the corpus (available for only 42.9%), making it too incomplete for a reliable comparison.
- **Snapshot refresh:** Refreshed the EU-27 five-category dataset on 7 November 2026 using FreeHire's agent job-search endpoint, which provides full available descriptions. The refreshed collection contains 24,488 unique postings across all 27 EU member states.


## 2. The Shape

- **In:** A fixed snapshot of unique EU-27 job postings from FreeHire (`data/raw/freehire_eu_raw.json`), retained locally and excluded from Git due to file size, containing only the fields needed for analysis and validation (`_collection_category`, `_collection_country`, `public_slug`, `url`, `title`, `company`, `posted_at`, `skills`, `description`, and `enrichment.seniority`) rather than a complete raw API dump. The precomputed summary (`data/processed/analytics_summary.json`) is committed to the repository so the dashboard runs directly without requiring the local raw data.
- **Out:** Overall and category-specific skill prevalence, a skill-distinctiveness (lift) score per skill per category, a bivariate prevalence-versus-lift skill landscape with baseline parity reference, technical skill family filtering with domain-level re-ranking, a posting-count map by country, the occupational composition of the corpus, and an occupational-composition comparison across countries with sufficient sample size.
- **On screen:** The user selects an occupational category and can filter by technical skill family to see its skill profile, most distinctive skills, and an interactive 2D prevalence-versus-lift scatter plot with hover inspection and an objective corpus parity line (Lift = 1.0); the overview shows the composition of the five categories and overall skill demand; a separate geographic view shows the EU map and, for sufficiently represented countries, how their occupational mix compares.
The project describes patterns in an observed EU-27 job-posting corpus. For example, it can estimate the proportion of observed Data Science postings containing Python, but not the proportion of all Data Science jobs in the EU requiring Python.


## Data and Reproducibility

### Running the Dashboard

The dashboard can run immediately using the committed precomputed analysis in `data/processed/analytics_summary.json`, allowing the dashboard to run without recollecting the raw data:

```bash
uv run streamlit run app.py
```

Regenerating the processed summary or running the preprocessing pipeline requires a local raw snapshot (`data/raw/freehire_eu_raw.json`), which is retained locally and excluded from Git due to file size.

Collection parameters and audit information for the historical snapshot are recorded in the collection metadata file (`data/raw/collection_metadata_eu.json`). To collect a fresh snapshot from FreeHire, regenerate the analytics summary, and run the test suite:

```bash
uv run python eu27.py
uv run python scripts/preprocess.py
uv run pytest
```

Because FreeHire job postings and search results change continuously over time, running a new collection with `eu27.py` will pull live postings from the API and will not reproduce the historical 24,488-posting snapshot exactly; counts, category shares, and skill rankings in the charts may differ accordingly.

### Local Weekly Data Refresh

Data refreshes are performed locally via a single command to ensure human oversight, prevent unreviewed changes, and comply with organization permissions:

```bash
uv run python scripts/refresh_weekly.py
```

- **Weekly Maintenance:** Run `uv run python scripts/refresh_weekly.py` manually every Sunday. After a successful run, review the updated data and dashboard, then commit and push the approved changes the same day. This process is currently manual: GitHub Actions runs CI tests on pushes, pull requests, and manual workflow dispatch; it does not schedule data collection or automatically publish refreshed data. The raw snapshot `data/raw/freehire_eu_raw.json` is Git-ignored, so it remains local. The processed analytics summary and collection metadata are tracked.
- **Pipeline Execution:** Runs `eu27.py` to collect fresh postings from FreeHire, `scripts/preprocess.py` to regenerate `data/processed/analytics_summary.json`, non-destructively checks for substantive diffs against `HEAD` with `scripts/check_refresh_diff.py`, and validates the outputs against the complete test suite (`uv run pytest`).
- **Resilience and Retries:** `eu27.py` includes bounded exponential backoff retries for transient connection errors, timeouts, and 5xx server responses, while respecting HTTP 429 `Retry-After` headers and raising immediately on permanent client errors.
- **Safety and Rollback:** Before execution, existing managed dataset files are backed up. If a pipeline step fails, the script attempts to restore the previous files. If rollback also fails, inspect the reported errors and recover the files manually before continuing.
- **Diff Inspection:** After a successful refresh, inspect the substantive changes (`git diff data/processed/analytics_summary.json`), verify the dashboard locally (`uv run streamlit run app.py`), and manually commit and push when satisfied.
- **Continuous Integration:** A lightweight GitHub Actions CI workflow (`.github/workflows/weekly-data-refresh.yml`) automatically runs tests on push, pull requests, and manual dispatch.

### Test Suite and CI Execution

The test suite separates fast, deterministic CI execution from full production-data validation:

- **Standard CI Tests (`uv run pytest`):** Run by default on clean checkouts (such as GitHub Actions) without downloading or requiring the large raw dataset. Streamlit UI and dashboard interactions are tested deterministically against a tracked test fixture (`data/fixtures/test_postings_fixture.json`), while analytical regressions validate corpus-wide statistics (24,488 postings, category counts, R skill demand) directly against the tracked `data/processed/analytics_summary.json`.
- **Production Regression Tests (`uv run pytest -m production_data`):** Verify exact production behavior across the complete 24,488-posting dataset (interactive multi-filter slices, cross-country composition distributions, and raw R skill extraction). These require the local raw snapshot (`data/raw/freehire_eu_raw.json`, ~143 MB, excluded from Git due to size) or the processed postings cache (`data/processed/.postings_cache.json`). If executed without production data, they fail explicitly with a clear explanatory error rather than silently falling back.


## 3. The Size

### First Useful Version Does
- Uses the fixed, audited **snapshot of 24,488** unique FreeHire postings across the EU-27 (collected on 7 November 2026).
- **Extracts skills** via a controlled vocabulary with alias normalization (e.g., `PowerBI` → `Power BI`).
- Measures **job-level skill prevalence**: a skill counts once per posting, regardless of how many times it is mentioned.
- Compares **skill prevalence** across the five occupational categories.
- Calculates **skill lift** per category — `P(skill | category) / P(skill | overall corpus)` — to distinguish skills that are relatively characteristic of a category from skills that are simply common across the observed corpus.
- Uses **support thresholds** of at least 20 postings and 1.5% prevalence for the distinctive-skill display. These were chosen as practical criteria to avoid rankings being driven by very rare skills. A sensitivity analysis across 25 threshold combinations showed that lower thresholds mainly add low-support, highly distinctive skills, while higher thresholds remove less-prevalent or lower-support skills; the full results are documented in `analysis/sensitivity_report.md`.
- Shows the relative size/**composition of the five job categories** to provide context for corpus-level skill prevalence.
- Shows a **posting-count map** by country using raw observed counts only.
- Compares **occupational composition** across countries with at least 300 observed postings; smaller countries remain visible on the map but are excluded from this comparison.
- Reports FreeHire's **seniority** information as a descriptive fact (seniority is available for 42.9% of postings), without a dedicated seniority filter and without inferring missing values.
- Treats each **unique posting** as one observation. No external country, occupation, or market-size weights are applied.
- Implements skill extraction, lift calculation, and the category/geographic comparisons as **plain Python functions** in a small module (`src/analytics.py`), so the behaviors in Section 4 can be tested directly without running the app; `scripts/preprocess.py` uses these functions to generate `data/processed/analytics_summary.json`, and `app.py` loads that precomputed summary and renders the dashboard.

### Explicitly Not This Term
- CV matching or personalized skill-gap scoring.
- Custom occupational or seniority classification models, or any seniority inference.
- A skill × country matrix, or any per-skill breakdown by country.
- A country selector that drives skill lift views across the dashboard.
- Job recommendation, automatic application, or salary/hiring prediction.
- Sentiment analysis or company reviews.
- Combining additional job sources beyond FreeHire.
- A second dashboard tool (e.g., Tableau) alongside the Python/Streamlit build.
- Treating the FreeHire snapshot as a representative census of the EU labour market.
- Applying external labour-market or country-size weights that cannot be justified from the observed dataset.


## 4. How We Would Know It Works

- Given a posting whose description mentions SQL and Excel but not Python, skill extraction returns SQL and Excel as present and Python as absent.
- Given a skill that appears in every Data Engineering posting but no Data Analytics posting, category comparison shows 100% prevalence for Data Engineering and 0% for Analytics, with lift > 1 for Data Engineering and lift = 0 for Data Analytics.
- Given a country with fewer than 300 observed postings, it appears on the map with its raw count but is excluded from the occupational-composition comparison.


## 5. What Could Stop This

- **Snapshot/data provenance:** FreeHire data can change over time and differ between collection runs; a new collection will not reproduce the historical 24,488-posting snapshot exactly.
  *Mitigation:* Retain the audited snapshot locally (`data/raw/freehire_eu_raw.json`), document collection parameters in the collection metadata file (`data/raw/collection_metadata_eu.json`), and commit the precomputed processed summary (`data/processed/analytics_summary.json`) so the dashboard and baseline analysis run reliably without recollecting raw data.
- **Uneven category sizes:** The snapshot is heavily concentrated in Data Engineering.
  *Mitigation:* Report the occupational composition explicitly and use both counts and within-category prevalence/lift rather than raw skill frequency alone.
- **Skill extraction and vocabulary coverage:** Inconsistent terminology can cause false positives/negatives, while skills outside the controlled vocabulary cannot be detected.
  *Mitigation:* Use a controlled vocabulary with explicit aliases, document the vocabulary and extraction rules, and manually validate the extraction on a sample.
- **FreeHire occupational classification:** The project relies on FreeHire's occupational labels rather than building an independent classifier.
  *Mitigation:* Manually reviewed 50 postings across all five categories to assess whether the labels were broadly consistent with the posting content.
- **Small-country noise in the geographic comparison:** Country sample sizes range from 25 to nearly 5,000.
  *Mitigation:* Apply the 300-posting threshold specifically to the occupational-composition comparison; smaller countries remain visible as raw counts on the map.
- **Source limitations:** FreeHire is one job-posting source, not a labour-market census.
  *Mitigation:* Describe all findings as patterns within the observed FreeHire EU-27 corpus and avoid claims about the true size or structure of the entire EU labour market.
- **Incomplete seniority metadata:** Native FreeHire seniority information is available for only 42.9% of postings.
  *Mitigation:* Report seniority coverage as a descriptive fact only; no filter or imputation is used.
