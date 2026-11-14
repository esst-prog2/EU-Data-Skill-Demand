# Design Brief: EU Data Career Compass Promotional Website

<!-- impeccable:surface-brief 1 -->

**Surface Target:** `docs/index.html` (Standalone GitHub Pages Website)  
**Mode:** Persuade / Experience (Academic-grade Data Product Showcase)  
**Status:** PROPOSED FOR CONFIRMATION (Shape Phase)  
**Date:** 14 November 2026  

---

## 1. Executive Summary & Design Direction

The **EU Data Career Compass** promotional website is a standalone, single-page web artifact designed to communicate the analytical authority, empirical findings, and career utility of the project to university graduates, junior data practitioners, and academic evaluators. 

It is **NOT** a dashboard wrapper or a generic AI-SaaS template. It is an editorial data-journalism showcase modeled on high-craft technical publications (such as *The Economist Graphic Detail*, *Financial Times Visual Journalism*, and *Our World in Data*). The design prioritizes intellectual credibility, restrained beauty, generous typographic rhythm, and direct engagement with real European labour-market evidence.

---

## 2. Job, Audience & Visitor Psychology

### Audience Segments & Mindsets
1. **Graduating University Students & Junior Seekers:**
   - *Mindset:* Anxious, overwhelmed by inflated job specifications ("must know 15 tools for entry level").
   - *Need:* Clarity, perspective, and honest prioritization based on real data rather than commercial hype.
2. **Career Switchers & Practicing Juniors:**
   - *Mindset:* Pragmatic; evaluating the trade-offs of specializing in Data Engineering vs. Data Science vs. AI Engineering.
   - *Need:* Empirical distinction between ubiquitous foundations (SQL/Git) and distinctive role markers (Airflow/PyTorch).
3. **Academic Evaluators & Technical Recruiters:**
   - *Mindset:* Skeptical of student portfolio claims and superficial web apps.
   - *Need:* Rigorous methodology, transparent limitations (e.g., $N \ge 300$ sample filter, 42.9% seniority reporting), and verified software quality (397 automated tests).

### Visitor Mode & Success Criteria
- **Mode:** **Persuade & Inform.** The visitor should immediately recognize this as an authoritative research-backed product, understand the core *Prevalence vs. Lift* mechanism within 60 seconds, and be inspired to launch the Streamlit dashboard or inspect the GitHub codebase.
- **Success Definition:** A visitor leaves with a precise understanding of why generic "learn Python" advice is incomplete, quotes the Python vs. Excel comparison, and perceives the project as professional portfolio work.

---

## 3. Visual Identity & Design World

### The Aesthetic: "European Precision Editorial"
- **Tone:** Methodological clarity, calm confidence, scholarly rigor, and intellectual warmth.
- **Anti-References (Strictly Forbidden):**
  - No dark-mode neon glowing borders, floating glassmorphism, or futuristic space meshes.
  - No generic illustrations of people holding oversized bar charts or stock corporate office imagery.
  - No endless grids of identical 3-column cards with generic icons.
  - No fake user quotes, fake testimonials, or marketing countdowns.
- **Visual Hallmarks:**
  - Crisp hairline borders (`1px solid #e2e8f0` / `#e5e7eb`).
  - Warm, breathable background canvases (`#fafaf9` stone or `#f8fafc` slate) paired with crisp white analytical plaques.
  - Subtle micro-grid textures and SVG-rendered data coordinate marks that evoke physical chart paper and European atlas cartography.

---

## 4. Typography System

The typography is built around clean visual contrast between an authoritative editorial display voice, a highly legible body face, and precise tabular numerics.

- **Editorial Headings:** Modern European Sans with structural warmth (e.g., *Plus Jakarta Sans*, *Inter*, or *Cabinet Grotesk*), utilizing tight optical kerning (`letter-spacing: -0.025em`) and strong hierarchy.
- **Analytical & Body Copy:** Clean, neutral system sans-serif (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`) optimized for effortless long-form reading at `16px-17px` with `1.65` line height.
- **Data, Figures & Metrics:** Tabular monospaced numbers (`SF Mono`, `JetBrains Mono`, `Consolas`, or `font-variant-numeric: tabular-nums;`) for all percentages, lift multipliers, and posting counts, ensuring mathematical alignment across comparison rows.

---

## 5. Restrained Color Palette

The color strategy is **Committed & Functional**: a restrained neutral canvas punctuated by purposeful semantic hues derived from the audited 5-category data taxonomy.

| Token | Hex Value | Semantic Role |
|---|---|---|
| **Canvas Ground** | `#f8fafc` (Slate 50) | Main page background; calm, editorial paper tone |
| **Card Surface** | `#ffffff` (White) | Analytical plaques and content containers with hairline borders |
| **Ink Primary** | `#0f172a` (Slate 900) | Major titles, headline typography, and high-contrast metrics |
| **Ink Secondary** | `#475569` (Slate 600) | Explanatory copy, captions, and methodological commentary |
| **Ink Muted** | `#94a3b8` (Slate 400) | Axis labels, table borders, and metadata stamps |
| **Accent Primary** | `#2563eb` (Blue 600) | Primary call-to-action buttons, key data callouts, links |
| **Corpus Parity Red**| `#dc2626` (Red 600) | The critical Lift = 1.00 baseline parity indicator |
| **Category Cyan** | `#0284c7` (Sky 600) | Data Analytics markers |
| **Category Emerald**| `#059669` (Emerald 600)| Data Engineering markers |
| **Category Violet** | `#7c3aed` (Violet 600) | Data Science markers |
| **Category Amber** | `#d97706` (Amber 600) | ML/AI markers & sample-size warning indicators |
| **Category Rose** | `#e11d48` (Rose 600) | AI Engineering markers |

---

## 6. Narrative Structure & Page Layout

The page is structured as a continuous scrolling story in nine deliberate beats:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Hero: The Reality Check (Headline, 24k stat ribbon, Primary CTA)   │
├────────────────────────────────────────────────────────────────────────┤
│ 2. The Problem: The Job Description Fatigue Dilemma                    │
├────────────────────────────────────────────────────────────────────────┤
│ 3. The Core Framework: Bivariate 4-Quadrant Model (Prevalence vs Lift) │
├────────────────────────────────────────────────────────────────────────┤
│ 4. The Empirical Proof: Why Python and Excel Tell Different Stories    │
├────────────────────────────────────────────────────────────────────────┤
│ 5. Five Occupational Profiles: Top Demand vs. Distinctive Markers      │
├────────────────────────────────────────────────────────────────────────┤
│ 6. European Scope & The N ≥ 300 Minimum Sample-Size Guardrail          │
├────────────────────────────────────────────────────────────────────────┤
│ 7. Methodological Rigor: 397 Tests, Validation Holdouts & Seniority    │
├────────────────────────────────────────────────────────────────────────┤
│ 8. Interactive Product Preview: Tour of the Streamlit Experience       │
├────────────────────────────────────────────────────────────────────────┤
│ 9. Access & Action: Launch Dashboard & Inspect GitHub Repository       │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed Section Specifications:

1. **Section 1: Hero — The Reality Check**
   - *Headline:* "What the European Tech Job Market Actually Expects from You."
   - *Subhead:* An evidence-based investigation of **24,488 job postings** across **27 EU member states** and **5 core data professions** — revealing the critical difference between generic skill popularity and true occupational distinctiveness.
   - *Metric Strip:* `24,488 Observed Postings` • `27 EU Member States` • `5 Occupations` • `52 Canonical Skills` • `397 Passing Tests`.
   - *Action Pair:* Primary button "Explore the Live Dashboard" + Secondary button "View on GitHub".

2. **Section 2: The Junior Data Dilemma**
   - The trap of commercial job boards: 20-tool wishlist postings causing exhaustion.
   - The failure of generic advice: Why *"just learn Python and SQL"* ignores specialized career trajectories.
   - Four central questions the project answers.

3. **Section 3: The Four-Quadrant Bivariate Framework**
   - Visual interactive SVG quadrant matrix:
     - Horizontal axis: Within-Category Prevalence ($P(\text{skill} \mid \text{category})$)
     - Vertical axis: Distinctiveness Lift ($\text{Lift}$) with bold Crimson $\text{Lift} = 1.00$ parity line.
   - The 4 Quadrants clearly articulated:
     - **Role Superpowers** (High Prevalence, Lift > 1.00): Tools that define the role.
     - **Universal Currency** (High Prevalence, Lift $\le$ 1.00): Foundational baseline tools.
     - **Niche Specializations** (Lower Prevalence, Lift > 1.00): Specialized libraries.
     - **Peripheral Skills** (Lower Prevalence, Lift $\le$ 1.00): Ancillary technologies.

4. **Section 4: The Empirical Proof — Python vs. Excel in Data Analytics**
   - Side-by-side comparative metric cards with exact figures:
     - `Python`: 42.2% prevalence, **0.74× Lift** (Under-represented vs. corpus baseline of 57.1%).
     - `Power BI`: 44.8% prevalence, **2.61× Lift** (High demand + high distinctiveness).
     - `Excel`: 22.1% prevalence, **4.73× Lift** (High distinctiveness marker).
   - Core takeaway: High raw counts do not necessarily mean high role specialization.

5. **Section 5: The Five Occupational Profiles**
   - Tabbed or structured cards detailing the verified distribution:
     - **Data Engineering** (13,592 postings, 55.5%): SQL (55.8%), Python (53.5%), Kafka (1.61×), Scala (1.55×).
     - **Data Analytics** (3,582 postings, 14.6%): SQL (63.7%), Power BI (44.8%), Excel (22.1%, 4.73×).
     - **AI Engineering** (3,345 postings, 13.7%): LLMs / GenAI (81.8%), LangChain (20.9%, 4.97×), TypeScript (11.9%, 4.69×).
     - **Data Science** (2,558 postings, 10.4%): Python (73.8%), Scikit-learn (17.0%, 4.33×), R (16.4%, 3.43×).
     - **ML/AI** (1,411 postings, 5.8%): Python (74.4%), PyTorch (40.0%, 6.70×), C++ (12.7%, 6.74×).

6. **Section 6: Geographic Scope & The $N \ge 300$ Sample-Size Filter**
   - Explanation of European distribution across all 27 EU nations.
   - Visual breakdown of the **11 qualifying member states** ($N \ge 300$) with observed occupational proportions (France, Netherlands, Poland, Spain, Germany, Italy, Portugal, Belgium, Sweden, Ireland, Denmark).
   - Clear statistical disclaimer: $N \ge 300$ is a practical stability filter, not an assertion of census representativeness.

7. **Section 7: Scientific Rigor & Pipeline Transparency**
   - Three proof pillars:
     - *Testing:* **397 automated pytest tests** covering regex extraction, lift calculations, atomic serialization, and UI state.
     - *Validation Holdouts:* 98.8% precision on 50-posting general audit; 96.7% precision on independent 30-posting R audit.
     - *Seniority Integrity:* Stated in 42.9% of postings, unstated in 57.1%; reported descriptively without speculative imputation.

8. **Section 8: Interactive Dashboard Guided Tour**
   - Walkthrough of the companion Streamlit tool:
     - Unified filter bar & synchronized Role/Skill Family selectors.
     - Hover inspection on bivariate scatter plot.
     - Interactive European choropleth and stacked composition bar charts.

9. **Section 9: Access, Quickstart & Repositories**
   - Primary Call to Action: "Launch Interactive Dashboard".
   - Secondary Call to Action: "Explore GitHub Repository".
   - Transparent local quickstart: `uv run streamlit run app.py` in three simple copyable lines.

---

## 7. Component & Data Graphic Specifications

- **Metric Cards:** Clean rectangular plaques featuring small uppercase kicker labels, prominent tabular numbers (`font-size: 2.25rem`, `font-weight: 700`), exact denominator subtitles (`n = 1,510 / 3,582`), and concise qualitative interpretations.
- **Quadrant Matrix Diagram:** Standalone SVG graphic with interactive hover tooltips explaining the four zones relative to the red dashed `Lift = 1.00` line.
- **Pill Badges:** Subtly tinted badges (`background: #eff6ff`, `color: #1d4ed8`, `border: 1px solid #dbeafe`) denoting skill families and occupational tags.
- **Code Blocks:** Clean dark charcoal (`#1e293b`) terminal cards with subtle copy button and syntax highlighting.

---

## 8. Responsive Behavior & Accessibility

- **Mobile First to Desktop Ultra:**
  - Phone ($< 640\text{px}$): Single-column vertical flow; metric ribbons wrap gracefully; horizontal tables scroll smoothly with subtle fade indicators.
  - Tablet ($640\text{px}-1024\text{px}$): Two-column metric cards; condensed comparison charts.
  - Desktop ($> 1024\text{px}$): Max content container width `1120px` centered with generous margins (`padding: 0 2rem`).
- **Accessibility Standards:**
  - Strict WCAG 2.1 AA compliance: contrast ratios $> 4.5:1$ for all body text and $> 3:1$ for charts/large text.
  - Fully keyboard-navigable interactive controls with explicit `:focus-visible` rings.
  - Semantic HTML5 landmark tags (`<header>`, `<main>`, `<nav>`, `<section>`, `<footer>`).

---

## 9. Explicit Scope Boundaries

- **Zero Changes to Application Code:** `app.py`, `src/analytics.py`, tests, and data files remain completely untouched.
- **No Fabricated Deployment URLs:** If a live web instance is not yet hosted, the CTA is structured to cleanly direct to the repository release and local one-command launch instructions.
- **No Artificial Claims:** All figures strictly match `analytics_summary.json` and the 24,488-posting snapshot.
