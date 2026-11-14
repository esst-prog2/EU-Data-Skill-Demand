# Impeccable Critique: EU Data Career Compass Promotional Website

<!-- impeccable:critique-report 1 -->

**Target:** `docs/designs/promo-website-variants-preview.html` (Option A — European Precision Atlas)  
**Evaluation Date:** 14 November 2026  
**Auditors:** Impeccable Design Reviewer & Multi-Perspective Synthesis  

---

## 1. Executive Summary & Verdict

Option A (*European Precision Atlas*) is the strongest conceptual direction for the EU Data Career Compass promotional website. Its restrained slate palette, crisp hairline borders, and calm editorial typography establish immediate intellectual authority. It feels like an independent data journalism publication (*Financial Times* or *Our World in Data*) rather than a generic tech startup or a student course submission.

However, the critique identified five concrete weaknesses that must be addressed before final implementation in `docs/index.html`:
1. **Hero Metric Focus:** The 397-test metric in the hero dilutes the dataset narrative; software testing belongs in the methodology section, keeping the hero focused strictly on the four primary empirical dimensions (postings, countries, roles, skills).
2. **Dashboard vs. Website Role Confusion:** The hero and navigation must make it crystal clear that this website is the *promotional research showcase*, while the Streamlit dashboard is the *interactive analytical tool*.
3. **Formulaic Micro-Kickers (Detector Warning):** The repeated uppercase kickers above every section heading feel like a template pattern. Replacing them with an authentic European editorial indexing system (`01 / THE CORE MECHANISM`) significantly elevates the craft.
4. **Card Border Clashes & WCAG Contrast (Detector Warning):** The 3px top colored border on rounded cards clashes with the corner radius. Contrast on certain muted category labels (#059669 and #0284c7 on light slate) needs to be deepened to exceed WCAG AA 4.5:1.
5. **Dashboard Visual Preview:** The tour section needs an authentic visual representation of the Streamlit dashboard interface (filter bar, bivariate scatter, and choropleth map) so visitors can see the actual tool before launching.

---

## 2. Evaluation from Three Target Perspectives

### Perspective 1: The University Classmate
- **First Impression:** Highly engaging. It immediately looks like a real-world data science portfolio rather than a standard university homework assignment.
- **The "Aha!" Moment:** The side-by-side comparison of **Python vs. Excel & Power BI in Data Analytics** is the core lightbulb moment. Every data student knows Python and SQL, but seeing that Python has a **0.74× lift** in Data Analytics while Excel has a **4.73× lift** immediately cuts through generic advice.
- **Classmate Friction Points:**
  - *"Can I just click and play with this on my phone?"* If the dashboard is a local Streamlit app, the website must gracefully explain how to try it without making visitors feel like they must clone a repository just to read the findings.
  - The occupational cards currently show bulleted lists. Adding compact horizontal prevalence/lift mini-bars would make comparing the five disciplines vastly more intuitive at a glance.

### Perspective 2: The Academic Evaluator
- **First Impression:** Methodologically credible and serious. Avoids commercial tech hype, hyperbolic claims ("100% employment guarantee"), or speculative AI buzzwords.
- **Methodological Strengths:**
  - Explicit definition of both Within-Category Prevalence ($P(\text{skill} \mid \text{category})$) and Distinctiveness Lift ($\text{Lift}$).
  - Highlighting the **$\text{Lift} = 1.00$ Corpus Parity** reference line anchors the scatter plot objectively.
  - The $N \ge 300$ minimum sample-size restriction for cross-country comparisons (11 qualifying member states) shows statistical discipline.
  - Reporting the 42.9% stated seniority rate (57.1% unstated) descriptively without attempting unverified algorithmic imputation.
- **Evaluator Friction Points:**
  - Putting "397 automated software tests" in the hero stat ribbon felt like conflating software engineering metrics with dataset sample size. Moving it to Section 7 (Methodology & Testing) where it sits alongside holdout validation audits (98.8% general precision, 96.7% R precision) restores scientific coherence.
  - The dataset disclaimer should explicitly reiterate that FreeHire is an observed online job-posting platform snapshot, not an exhaustive census of all European labour contracts.

### Perspective 3: The First-Time Career Explorer
- **First Impression:** Calming and refreshing. After browsing dozens of 20-bullet job descriptions, the concept of "Job Description Fatigue" directly validates their lived experience.
- **The Four-Quadrant Clarity:**
  - The distinction between **Universal Currency** (table-stakes skills like SQL and Git) and **Role Superpowers** (defining markers like Spark or PyTorch) provides an immediate mental framework for interview prep and resume tailoring.
- **Visitor Friction Points:**
  - The Call-to-Action needs a clearer two-tier distinction: a primary action to **Launch/Explore the Interactive Dashboard** and a secondary action to **Inspect the Open-Source Code on GitHub**.

---

## 3. Automated Detector & Technical Quality Findings

The deterministic Impeccable detector scan on `docs/designs/promo-website-variants-preview.html` flagged:

| Issue Type | File Location | Severity | Resolution in Final Blueprint |
|---|---|---|---|
| `kicker-above-heading` | Section headers | Warning | Delete repetitive uppercase kicker spans; replace with editorial section numbers (`01`, `02`, etc.) embedded in the layout. |
| `border-accent-on-rounded` | `.proof-card` (Python/PowerBI/Excel) | Warning | Eliminate clashing `border-top: 3px`; use refined hairline borders with colored skill badge tags inside the card. |
| `low-contrast` | Category text on light grounds | Warning | Deepen emerald from `#059669` to `#047857` (5.2:1) and sky from `#0284c7` to `#0369a1` (4.9:1) to satisfy WCAG AA 4.5:1. |
| `skipped-heading` | Section 5 (Occupational Profiles) | Warning | Fix heading outline hierarchy: `h2` (Page Title) $\rightarrow$ `h3` (Sections) $\rightarrow$ `h4` (Profile Titles). |
| `em-dash-overuse` | Body prose | Advisory | Replace redundant em-dashes with colons, parentheses, or periods to create a natural editorial rhythm. |

---

## 4. Priority Refinements & Final Implementation Blueprint

Based on the three-perspective critique and detector scan, the final promotional website implementation (`docs/index.html`) will adopt the following refined blueprint:

### 1. Refined Hero Banner
- **Primary 4 Dataset Metrics Only:**
  - `24,488` Observed Postings
  - `27` EU Member States
  - `5` Data Professions
  - `52` Canonical Technical Skills
- Relocate `397 Automated Tests` exclusively into Section 7 (Engineering Rigor & Methodology).

### 2. Standalone Identity Clarification
- Clear top badge: `"A Research Showcase & Career Guide • Companion to the EU Data Career Compass Dashboard"`.
- Dedicated "About the Product Ecosystem" note explaining that this web page hosts the permanent research findings, while the Streamlit application provides real-time interactive filtering and slicing.

### 3. Elevated Editorial Layout & Heading Hierarchy
- Eliminate formulaic kicker pills.
- Introduce elegant editorial index numbering:
  - `01 / THE JUNIOR DATA DILEMMA`
  - `02 / POPULARITY VS. DISTINCTIVENESS`
  - `03 / THE EMPIRICAL EVIDENCE`
  - `04 / FIVE OCCUPATIONAL PROFILES`
  - `05 / GEOGRAPHIC SCOPE & N ≥ 300 FILTER`
  - `06 / METHODOLOGICAL RIGOR & QUALITY`
  - `07 / INTERACTIVE DASHBOARD TOUR`
  - `08 / ACCESS & REPOSITORY`

### 4. Polished Component Cards & Contrast
- Clean hairline cards with no clashing top borders.
- Verified WCAG AA contrast on all badges and data labels.
- Structured comparative mini-bars for the 5 occupational profiles.

### 5. Clear Call-to-Action Hierarchy
- Primary CTA: **"Explore the Live Dashboard"** (configured to cleanly link to deployed instance or launch modal).
- Secondary CTA: **"View Source on GitHub"** (`https://github.com/esst-prog2/EU-Data-Skill-Demand`).
- Tertiary block: Local quickstart in three copyable terminal lines for technical visitors.
