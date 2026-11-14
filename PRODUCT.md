# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS (vanilla, responsive, zero-dependency, GitHub Pages ready in `/docs`)

## Users

1. **Students & Recent Graduates:** Navigating the transition from university coursework to the job market; looking for realistic entry-level skill expectations and prioritization.
2. **Career Switchers & Junior Professionals:** Weighing specialization tradeoffs across Data Analytics, Data Science, Data Engineering, ML/AI, and AI Engineering.
3. **Academic Evaluators & Recruiters:** Inspecting analytical rigor, transparent methodology, reproducible pipelines, and verified data distributions.

## Product Purpose

The **EU Data Career Compass** is a standalone, evidence-based data career exploration website and interactive tool. It replaces generic *"just learn Python and SQL"* career advice with concrete, empirical distributions of technical skill demand across 24,488 verified European tech job postings.

## Positioning

Unlike typical commercial career portals that aggregate raw keyword counts into undifferentiated lists, the EU Data Career Compass separates **within-occupation skill prevalence** ($P(\text{skill} \mid \text{category})$) from **distinctiveness lift** ($\text{Lift}$ over the European corpus baseline). This reveals why ubiquitous tools like Python can be below baseline parity in certain roles (e.g., Data Analytics) while specialized libraries like XGBoost or PyTorch define role superpowers.

## Operating Context

- Standalone static promotional web experience hosted via GitHub Pages (`/docs`).
- Companion showcase to the interactive single-page Streamlit analytical dashboard (`app.py`).
- Public portfolio showcase linking directly to the open-source GitHub repository (`https://github.com/esst-prog2/EU-Data-Skill-Demand`).

## Capabilities and Constraints

- **Verified Empirical Dataset:** 24,488 unique FreeHire job postings collected across all 27 EU member states up to 7 November 2026.
- **Five Core Occupations:** Data Analytics (3,582 postings), Data Engineering (13,592 postings), Data Science (2,558 postings), ML/AI (1,411 postings), AI Engineering (3,345 postings).
- **Controlled Skill Taxonomy:** 52 canonical technical skills across 5 skill families (Programming languages, Databases & data warehouses, BI & visualization, Cloud & infrastructure, ML/AI frameworks & tools).
- **Tested & Validated:** 397 automated software tests (`pytest`), hybrid tag/regex extraction with delimiter guards, and holdout validation audits (98.8% general precision, 96.7% R precision).
- **Scope Guardrails:** Descriptive seniority reporting (42.9% stated, 57.1% unstated; no algorithmic imputation); geographic cross-country composition comparisons restricted to $N \ge 300$ observed postings (11 member states).
- **Strict Boundary:** The existing Streamlit dashboard (`app.py`), analytical backend (`src/analytics.py`), and test suite must remain untouched.

## Brand Commitments

- **Product Name:** EU Data Career Compass
- **Aesthetic Direction:** High-craft European editorial data product and scholarly portfolio aesthetic; clear typography, intentional whitespace, restrained color, and authentic data graphics.
- **Tone & Voice:** Methodologically honest, statistically precise, empowering for students, free of generic marketing hype or AI-SaaS clichés.

## Evidence on Hand

- `data/processed/analytics_summary.json` (canonical precomputed analytical summary)
- `docs/promo_page.md` (verified narrative copy and verified empirical figures)
- `docs/designs/career-exploration-promo-page.md` (promotional showcase design specifications)
- `README.md` (repository overview, execution instructions, and demo description)

## Product Principles

1. **Truth Before Advice:** Never present anecdotal rules of thumb as market facts; every recommendation must stem from observed data.
2. **Prevalence and Distinctiveness in Tandem:** High popularity without high distinctiveness denotes a table-stakes foundation; high distinctiveness with sufficient volume denotes an occupational superpower.
3. **Transparency over False Certainty:** Explicitly declare sample limits, unstated seniority rates, and platform constraints.
4. **Editorial Restraint:** Prioritize readability, intellectual credibility, and elegant data storytelling over flashy gradients or generic landing-page widgets.
