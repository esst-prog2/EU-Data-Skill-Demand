# Data Jobs & Skill-Gap Finder for Early-Career Professionals

## 1. The Demo
I open the Streamlit web app in the browser, select Data Analyst from a dropdown, and choose Junior. A panel displays skill prevalence pulled from the most recent local and remote data snapshots (e.g., SQL 78%, Python 53%). I paste a sample CV into the text box; the app minimizes direct PII such as my name, phone number, and email in memory, runs the text through an embedding model, and outputs my top 3 skill gaps by priority (e.g., Git: high market demand, but weak evidence in my CV), showing the CV sentence used as evidence where it exists. Below that, it displays postings classified as current in the latest snapshot, ranked by how well my demonstrated skill evidence aligns with their requirements, with a flag if a posting advertised as Junior requests 3+ years of experience. Clicking a link opens the original post in a new tab.

## 2. The Shape
* **in:** A pasted CV + stored snapshots of job postings for 4 roles (Data Analyst, Data Scientist, BI Analyst, Data Engineer), pulled from Budapest via Google Jobs through SerpApi and from CEE-oriented remote sources via RemoteOK
* **out:** A ranked list of the highest-priority skill gaps, plus a sorted list of current job postings with alignment reasons and requirement-intensity flags
* **on screen:** The user selects target role and seniority, views market skill prevalence, pastes their CV to instantly inspect prioritized skill gaps with evidence sentences, and scrolls through eligible, ranked job postings, which contain requirement-intensity flags, such as 3+ years of experience requested for a Junior posting

## 3. The Size
**First useful version does:**
- Retrieves job postings for the 4 target roles from Budapest and CEE-oriented remote sources, saving them locally as dated `.parquet` snapshots so the application does not depend on live APIs during use.
- Extracts skills using spaCy and a controlled skill taxonomy and calculates market-importance percentages per role.
- Accepts a pasted CV, minimizes direct PII in memory, and does not keep user CV data.
- Uses sentence embeddings to estimate the strength of CV evidence for market skills and computes a transparent Gap Priority score. Gap Priority = Market Importance × Missing Evidence.

**Explicitly not this term:**
- Company review ratings or sentiment analysis.
- Complex weighted composite match scores as the primary output.
- Scraping local job boards directly; local collection relies on Google Jobs through SerpApi.
- CV rewriting, automatic applications, or interview preparation.
- Regions outside Hungary and CEE-eligible remote work.

## 4. How we would know it works
- Given a posting whose text mentions SQL and Excel but not Python, skill extraction returns SQL and Excel as present and Python as absent for that posting.
- Given a CV sentence such as "Built dashboards in Power BI using SQL data sources," semantic matching associates it more strongly with Power BI and SQL than with an unrelated skill such as Salesforce.
- Given a posting whose location field says "US only," the eligibility classifier returns FALSE, not UNKNOWN or TRUE.

## 5. What could stop this
- **API Limits:** SerpApi has a strict limit of 250 searches per month. *Mitigation:* cache every raw API response locally into fixture files so debugging and development do not repeatedly consume the monthly quota.
- **Unverified Budapest data volume:** The actual number of entry-level Budapest postings SerpApi returns has not been measured yet. *Mitigation:* This is the first thing to check in Week 1; if volume is too thin to support meaningful analysis, the project narrows to remote-CEE-only rather than forcing a weak local dataset into the analysis.
- **New Tech Stack:** sentence-transformers and APIs are new tools for this project. *Mitigation:* Write small standalone tests in Week 1 to verify API connectivity, returned data structure, and embedding outputs before building the main application.
- **Data Privacy:** Handling user CV text. *Mitigation:* Process CV text in memory without persistent storage, minimize direct identifiers before analysis, and use a synthetic sample CV for the final presentation.
