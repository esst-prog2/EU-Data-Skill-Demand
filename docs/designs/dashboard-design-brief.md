# Design Brief: EU Data Career Compass

**Document:** `docs/designs/dashboard-design-brief.md`
**Status:** DRAFT (Shape Phase)
**Surface Mode:** Operate / Read
**Target Application:** Streamlit Dashboard (`app.py`)
**Design Toolkit:** Impeccable (`impeccable.style`)
**Date:** 2026-11-14

---

## Executive Summary

The **EU Data Career Compass** is an interactive, evidence-based data career exploration product built for university students, recent graduates, and junior professionals. Grounded in an audited snapshot of 24,488 European tech job postings across 27 EU member states, it decodes market expectations across five occupational categories: **Data Analytics**, **Data Engineering**, **Data Science**, **ML/AI**, and **AI Engineering**.

Its core analytical differentiator is the distinction between **Within-Category Prevalence** (how frequently a skill appears) and **Distinctiveness Lift** (how uniquely concentrated a skill is relative to the European market baseline).

This design brief establishes the visual identity, component systems, and design rules needed to elevate the existing single-page Streamlit application (`app.py`) into a modern, credible, and visually memorable data product — without modifying underlying analytics, metrics, or scope boundaries.

---

## 1. Overall Visual Direction and Design Identity

### The Archetype: The Precision Data Editorial
The design direction blends the credibility, authority, and calm typography of top-tier visual journalism (*Financial Times*, *Our World in Data*) with the crisp, high-craft precision of modern developer tools (*Linear*, *Stripe*, *Vercel*).

- **Tone & Mood:** Analytical, authoritative, empowering, and clean. It must feel like an audited scientific instrument that a university evaluator respects and a junior candidate genuinely enjoys exploring.
- **The Core Metaphor: The Compass:** The visual language emphasizes coordinates, calibrated axes, orientation marks, and crisp data ink over decorative SaaS dashboard candy.
- **Surface Mode (Impeccable):**
  - **Operate (Primary):** The visitor completes tasks — filtering by role, drilling into skill families, hovering over quadrant coordinates, and comparing countries. Scanability, native expectations, and instant visual feedback outrank decorative expression.
  - **Read (Secondary):** The visitor seeks comprehension — understanding the prevalence-vs-lift framework, interpreting the 11-country benchmark ($N \ge 300$), and reviewing seniority metadata transparency.
- **Explicit Anti-Patterns (Avoid):**
  - No generic "AI SaaS" tropes (no purple-to-blue neon gradients, no glowing cards, no floating glassmorphism).
  - No bloated border radii (`border-radius: 20px+`) that make analytical charts look like mobile widgets.
  - No card-in-card nesting where every minor element is wrapped in another heavy box.
  - No marketing landing page gimmicks (e.g., hero illustrations, decorative floating badges). The interface must remain an authentic analytical tool.

---

## 2. Color Palette and Semantic Color Usage

The color system is organized into a clean neutral canvas, five harmonized categorical hues, and strict semantic markers.

```text
┌────────────────────────────────────────────────────────────────────────┐
│  NEUTRAL CANVAS                                                        │
│  Page Background:   #f8fafc (Slate 50 - warm paper tint)               │
│  Surface Container: #ffffff (Pure White - crisp contrast)              │
│  Borders & Rules:   #e2e8f0 (Slate 200 - hairline 1px dividers)        │
├────────────────────────────────────────────────────────────────────────┤
│  INK HIERARCHY                                                         │
│  High-Emphasis Ink: #0f172a (Slate 900 - titles, metrics, chart ink)   │
│  Secondary Ink:     #334155 (Slate 700 - axis labels, table headers)   │
│  Muted / Note Ink:  #475569 (Slate 600 - captions, denominators)       │
├────────────────────────────────────────────────────────────────────────┤
│  5 CATEGORICAL OCCUPATIONAL HUES (Harmonized & Distinct)               │
│  Data Engineering:  #2563eb (Royal Blue - architecture, plumbing)      │
│  Data Analytics:    #059669 (Deep Emerald - business reporting, BI)    │
│  AI Engineering:    #7c3aed (Deep Violet - LLMs, modern GenAI stack)   │
│  Data Science:      #d97706 (Warm Ochre - modeling, algorithms)        │
│  ML/AI:             #db2777 (Deep Rose - deep learning, computer vision)│
├────────────────────────────────────────────────────────────────────────┤
│  SEMANTIC / ANALYTICAL SIGNALS                                         │
│  Corpus Baseline Parity (Lift = 1.00): #dc2626 (Crimson, dashed line)  │
│  Qualified Distinctive Marker: Saturated categorical color (Opacity 1.0)│
│  Below Parity / Sub-threshold: #94a3b8 (Muted Slate, Opacity 0.45)     │
│  Sample Size Warning (N < 300): #b45309 text on #fef3c7 amber surface  │
└────────────────────────────────────────────────────────────────────────┘
```

### Semantic Rules
- **Categorical Consistency:** Once an occupational category is assigned a color (e.g. Data Engineering = `#2563eb`), that exact hue must represent that category across every visualization: the composition stacked bar, the category dropdown pill, the scatter plot markers, and the country breakdown bars.
- **Corpus Parity Landmark:** The `Lift = 1.00` reference line is consistently rendered in Crimson (`#dc2626`) across all scatter plots. It is an objective benchmark, not a category attribute.
- **De-emphasizing Table Stakes in Distinctiveness Views:** In distinctiveness visualizations, sub-threshold or below-parity skills are muted (`#94a3b8`, 45% opacity), ensuring that distinctive peaks pop immediately while universal baseline tools remain legible on closer inspection.

---

## 3. Typography and Hierarchy

A high-credibility editorial product requires robust, proportional typography paired with monospaced tabular numerals.

### Type Pairing
- **Primary Interface Font:** Clean geometric sans-serif stack (`Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`). Clean, neutral, highly legible at small sizes.
- **Numerical & Tabular Font:** Monospaced tabular numeral stack (`ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`, with CSS `font-variant-numeric: tabular-nums`). Essential for counts, percentages, and lift values to prevent visual jitter during filtering.

### Typographic Hierarchy
| Element | Font Size | Weight | Tracking | Color | Purpose |
|---|---|---|---|---|---|
| **App Title** | 26px (`1.625rem`) | 700 (Bold) | `-0.025em` | `#0f172a` | Clean, commanding dashboard masthead. |
| **Subtitle / Badges** | 13px (`0.8125rem`) | 500 (Medium) | Normal | `#475569` | Snapshot date, corpus total, and scope attribution. |
| **Section Row Headers** | 16px (`1.0rem`) | 600 (Semibold) | `-0.015em` | `#0f172a` | Analytical paired-row anchors. |
| **Metric Big Numbers** | 30px (`1.875rem`) | 700 (Bold) | Tabular | `#0f172a` | Immediate numerical takeaway. |
| **Metric Sub-labels** | 12px (`0.75rem`) | 500 (Medium) | Normal | `#64748b` | Denominators, context, and sample percentages. |
| **Chart Axis Labels** | 11px–12px | 500 (Medium) | Normal | `#475569` | Readable coordinates that meet WCAG AA contrast. |
| **Table Cells** | 13px (`0.8125rem`) | 400 (Regular) | Tabular (nums) | `#1e293b` | Scannable, dense data presentation. |

---

## 4. Page Layout, Spacing, and Visual Rhythm

The dashboard preserves its audited single-page architecture while establishing a disciplined vertical cadence.

```text
┌────────────────────────────────────────────────────────────────────────┐
│  HEADER: App Title & Scope Badge Chips (24,488 Postings | 27 EU States)│
├────────────────────────────────────────────────────────────────────────┤
│  STICKY FILTER TOOLBAR: Country | Role | Seniority | Family | [Reset]  │
├────────────────────────────────────────────────────────────────────────┤
│  KPI STRIP: [Matching Jobs] [Countries] [Detected Skills] [Distinctive]│
├────────────────────────────────────────────────────────────────────────┤
│  ROW 1:  Job Family Composition      │  Top In-Demand Skills (% Jobs)  │
│          (100% Stacked / Role Mix)   │  (Ranked Horizontal Bars)       │
├────────────────────────────────────────────────────────────────────────┤
│  ROW 2:  Most Distinctive Skills     │  Prevalence vs. Lift Scatter    │
│          (Ranked Lift > 1.00)        │  (Bivariate Quadrant Explorer)  │
├────────────────────────────────────────────────────────────────────────┤
│  ROW 3:  European Job Distribution   │  Country Composition (N ≥ 300)  │
│          (Choropleth Map across EU)  │  (100% Stacked Bar across 11)   │
├────────────────────────────────────────────────────────────────────────┤
│  ROW 4:  Complete 52-Skill Table     │  Methodology & Seniority Notes  │
│          (Searchable, Sortable)      │  (Transparent Formulas & Scope) │
└────────────────────────────────────────────────────────────────────────┘
```

### Layout Rules
- **Container Max-Width:** 1440px centered, allowing breathing room on wide monitors while keeping paired 2-column cards scannable.
- **Card Framing:** White background (`#ffffff`), 1px border (`#e2e8f0`), 8px border radius (`border-radius: 8px`), and 16px internal padding.
- **Sticky Filter Alignment:** Positioned at `top: 2.85rem` with `z-index: 99`. Background is solid white with a subtle border and 1px bottom shadow, providing a permanent command deck without obscuring chart headers.
- **Paired Column Symmetry:** Each row contains two cards that share identical heights and aligned title blocks, eliminating ragged vertical edges.

---

## 5. Component-Level Design

### 1. KPI Cards (4-Column Metric Strip)
- Elevate from standard Streamlit `st.metric` widgets into styled analytical cards:
  - Top edge: Hairline 1px border or subtle neutral framing (no heavy colored blocks).
  - Label: Bold uppercase tracking (`11px`, `letter-spacing: 0.05em`, `#64748b`).
  - Value: 30px bold tabular numbers in `#0f172a`.
  - Subtitle: Clear denominator context (e.g. `100% of 24,488 corpus postings` or `11 of 27 EU states meeting N ≥ 300`).

### 2. Filter Command Toolbar
- Single container spanning the full width above the KPI strip.
- Inputs have unified heights (38px) with subtle gray borders (`#cbd5e1`) and clean focus rings (`#3b82f6`).
- Reset button styled as a clean secondary utility button rather than an unaligned afterthought.

### 3. Horizontal Bar Charts
- Standardize all single-series bars with **strictly horizontal outside text labels** (`textangle=0`, `textposition='outside'`) and 35% x-axis headroom (`range=[0, max * 1.35]`), completely preventing label truncation.
- Categorical series use their assigned role color; corpus benchmarks use a distinct muted indigo (`#6366f1`), making comparative gaps immediately visible.

### 4. 100% Stacked Bar Charts (Country Composition)
- Inside labels formatted as clean integers (e.g., `55%`), omitting labels on narrow slices (< 8%) to prevent visual collision.
- Complete counts and percentages are preserved in rich hover tooltips.

### 5. European Choropleth Map
- Bounded framing centered at latitude 54°N, longitude 14°E with `projection_scale: 1.05`.
- Sequential blue scale (`#dbeafe` to `#1e3a8a`) calibrated across discrete count breaks.
- Non-EU European nations rendered in neutral light slate (`#f1f5f9`), ensuring EU-27 borders are crisp and distinct.

### 6. Complete Skill Demand Table
- Clean data grid styling: crisp header row in `#f8fafc`, 1px row dividers in `#f1f5f9`.
- Numeric columns (Prevalence %, Postings Count, Lift Multiplier) are right-aligned with tabular numerals.
- Qualification status rendered with subtle status chips:
  - `🟢 Qualified` (Lift > 1.0, N ≥ 20, Prev ≥ 1.5%)
  - `⚪ Below Parity` (Lift ≤ 1.00)
  - `🔻 Sub-threshold` (Lift > 1.0 but N < 20 or Prev < 1.5%)

---

## 6. Making Prevalence vs. Lift Visualization Clear and Memorable

The bivariate scatter plot is the intellectual heart of the product. To make it intuitive for students without a statistics background, the design applies four specific enhancements:

```text
       Distinctiveness Lift (× baseline)
          ▲
          │
          │  [Niche Specializations]          │  [Role Superpowers]
          │  Lower prevalence, high lift      │  High prevalence, high lift
          │  (e.g., XGBoost in DS)            │  (e.g., Power BI in Analytics)
          │                                   │
──────────┼───────────────────────────────────┼──────────────────────────────────────────
  Lift=1.0│  ─── Corpus Parity (Baseline) ────┼──────────────────────────────────────────
          │                                   │
          │  [Peripheral Skills]              │  [Universal Currency]
          │  Lower prevalence, lower lift     │  High prevalence, lower lift
          │  (e.g., incidental tools)         │  (e.g., SQL across all roles)
          └───────────────────────────────────┴─────────────────────────────────────────►
                                                      Within-Category Prevalence (%)
```

1. **The Parity Horizon Line:**
   The horizontal dashed crimson line at $\text{Lift} = 1.00$ is labeled: `Corpus Parity (Lift = 1.0) — Skills above this line are uniquely characteristic of this role`. This anchors the viewer immediately.
2. **Subtle Quadrant Explanatory Labels:**
   Add faint, elegant corner annotations in the scatter plot background to orient the viewer without cluttering data points:
   - Top-Right: *Role Superpowers (High Prevalence, Distinctive)*
   - Bottom-Right: *Universal Currency (High Prevalence, Market-Wide)*
   - Top-Left: *Niche Specializations (Lower Prevalence, Highly Distinctive)*
   - Bottom-Left: *Peripheral Skills (Lower Prevalence, Secondary)*
3. **Marker Visual Hierarchy:**
   - **Qualified Distinctive Skills:** Rendered with larger markers (size 11px) with solid saturated category fill and a dark slate outline `#0f172a`.
   - **Sub-threshold / Below Parity Skills:** Rendered with smaller markers (size 7px) and 45% opacity.
4. **Narrative Micro-Story Hover Tooltips:**
   Replace raw coordinate displays with an explanatory narrative:
   ```text
   Power BI (BI & visualization)
   • In Data Analytics: 44.8% (1,603 postings)
   • Market Baseline:   17.1% (4,188 postings)
   • Distinctiveness:   2.61× baseline (Over-represented)
   • Status:            Role Superpower
   ```

---

## 7. Accessibility, Readability, and Responsive Behavior

- **Contrast Ratios (WCAG AA Compliance):**
  - All text against surfaces achieves a contrast ratio of at least 4.5:1 (e.g. `#0f172a` against `#ffffff` is 16.1:1; `#475569` against `#ffffff` is 7.0:1).
  - Chart grid lines use `#e2e8f0` (Slate 200), providing clear structural orientation without distracting from data marks.
- **Redundant Information Encoding:**
  - Color is never the sole carrier of meaning. Every bar and scatter marker includes text labels, tooltips, and numerical metrics.
- **Responsive Layout:**
  - **Desktop (>1200px):** Balanced 2-column paired layout across all 4 rows.
  - **Tablet (768px–1199px):** Filter bar collapses into 2 rows; charts scale dynamically to fill available width.
  - **Mobile (<768px):** The 2-column paired grid stacks vertically into a single scannable column flow with minimum 44px touch targets on all interactive selectors.

---

## 8. Current Visual Weaknesses & How the Proposal Resolves Them

| Current Implementation Weakness | Root Cause | Proposed Design Resolution |
|---|---|---|
| **Default Streamlit Prototype Aesthetic** | Reliance on unstyled native Streamlit elements and default font stacks. | Scoped CSS injection applying the *Precision Data Editorial* identity: Slate 50 canvas, custom card containers, hairline borders, and tabular numerals. |
| **Bivariate Scatter Plot Cognitive Friction** | Unannotated scatter plot looks like an abstract statistical test to a junior user. | Faint quadrant explanatory watermarks, prominent Crimson parity line, marker size hierarchy, and narrative hover tooltips. |
| **Horizontal Bar Label Clipping** | In tight columns, bar chart labels can clip or collide with plot borders. | Standardized helper functions enforcing outside horizontal labels (`textangle=0`) with 35% x-axis headroom. |
| **Low-Contrast Caption Text** | Default Streamlit caption text uses `#808495` / `#94a3b8`, failing WCAG AA on white cards. | Shift all secondary and caption typography to `#475569` (Slate 600) and `#334155` (Slate 700), guaranteeing crisp 7:1+ contrast. |
| **Reference Screenshot Divergence** | Reference PNG (`Európai adatástechnológiai álláspiaci irányítópult.png`) had a legacy tabbed sidebar layout from May 2025. | Ground the design 100% in the active single-page 4-row paired grid architecture, adopting the best visual polish from the screenshot while preserving single-page flow. |

---

## Next Steps

This brief completes the **Shape** phase.

Upon your review and approval, we will proceed to the **Generate / Polish** phase, where we will translate these visual design specifications into concrete, scoped CSS and chart-theme improvements in `app.py`.
