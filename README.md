# EU Data Jobs & Skill Demand Analysis

## 1. The Demo

I open the Streamlit web app in the browser and select one of five FreeHire occupational categories: Data Analytics, Data Engineering, Data Science, ML/AI, or AI Engineering.
The app shows the category's most prevalent skills, then highlights which of those skills are *distinctive* to it rather than simply common across the observed corpus — e.g., "Python appears in 78% of Data Science postings, 1.4× its overall corpus prevalence, versus 45% in Data Analytics (0.8×)."
A map shows where the 22,985 postings are located across the EU-27. A separate comparison shows how the occupational composition of countries with at least 300 observed postings differs across the five categories.
The overview also shows the relative size of the five occupational categories, providing context for the overall skill-prevalence results.

### Scope Decisions

- **Project focus:** I cut the CV-matching and personalized skill-gap component from the original concept and focused the project on the market-analysis side, measuring technical skill demand across data-related occupations and geographic contexts in an observed EU-27 job-posting corpus.
- **Data source:** I moved from SerpAPI and RemoteOK to FreeHire because FreeHire provides a larger, more consistently structured EU-wide job-posting corpus with occupational categories and country-level enrichment, making systematic comparison across occupations and countries more feasible.
- **Geographic scope:** I expanded from a Hungary-focused analysis to the EU-27 because the broader corpus provides enough geographic and occupational variation to study how technical skill demand differs across both occupations and labour-market contexts.
- **Seniority:** I moved away from using seniority as a primary analytical dimension because seniority information is missing for 59% of the corpus, making it too incomplete for a reliable comparison.


## 2. The Shape

- **In:** A fixed local snapshot of **22,985 unique EU-27 job postings** from FreeHire, with job category, country, and partial seniority information from FreeHire's own enrichment.
- **Out:** Overall and category-specific skill prevalence, a skill-distinctiveness (lift) score per skill per category, a posting-count map by country, the occupational composition of the corpus, and an occupational-composition comparison across countries with sufficient sample size.
- **On screen:** The user selects an occupational category to see its skill profile and most distinctive skills; the overview shows the composition of the five categories and overall skill demand; a separate geographic view shows the EU map and, for sufficiently represented countries, how their occupational mix compares.
The project describes patterns in an observed EU-27 job-posting corpus. For example, it can estimate the proportion of observed Data Science postings containing Python, but not the proportion of all Data Science jobs in the EU requiring Python.


## 3. The Size

### First Useful Version Does
- Uses the fixed, audited **snapshot of 22,985** unique FreeHire postings across the EU-27.
- **Extracts skills** via a controlled vocabulary with alias normalization (e.g., `PowerBI` → `Power BI`).
- Measures **job-level skill prevalence**: a skill counts once per posting, regardless of how many times it is mentioned.
- Compares **skill prevalence** across the five occupational categories.
- Calculates **skill lift** per category — `P(skill | category) / P(skill | overall corpus)` — to distinguish skills that are relatively characteristic of a category from skills that are simply common across the observed corpus.
- Shows the relative size/**composition of the five job categories** to provide context for corpus-level skill prevalence.
- Shows a **posting-count map** by country using raw observed counts only.
- Compares **occupational composition** across countries with at least 300 observed postings; smaller countries remain visible on the map but are excluded from this comparison.
- Reports FreeHire's **seniority** information as a descriptive fact (seniority is available for 41% of postings), without a dedicated seniority filter and without inferring missing values.
- Treats each **unique posting** as one observation. No external country, occupation, or market-size weights are applied.
- Implements skill extraction, lift calculation, and the category/geographic comparisons as **plain Python functions** in a small module, so the behaviors in Section 4 can be tested directly without running the app; Streamlit only calls these functions and renders their output.

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

- **Snapshot/data provenance:** The FreeHire dataset may change over time or differ between collection runs.  
  *Mitigation:* Freeze the audited 22,985-posting snapshot locally; all analysis runs from the saved data.
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
- **Incomplete seniority metadata:** Native FreeHire seniority information is available for only 41% of postings.  
  *Mitigation:* Report seniority coverage as a descriptive fact only; no filter or imputation is used.
