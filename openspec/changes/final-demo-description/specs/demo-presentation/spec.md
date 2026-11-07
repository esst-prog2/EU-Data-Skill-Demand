# Spec Delta

## Purpose

Defines the presentation structure, content criteria, and empirical fidelity standards for Section 1 ("The Demo") of README.md to support a five-minute screenshot walkthrough of the production Streamlit application.

## ADDED Requirements

### Requirement: Screenshot Walkthrough Alignment
The demo description in Section 1 of README.md SHALL describe a five-minute visual presentation structured around static screenshots rather than an interactive runtime command or browser session.

#### Scenario: Presentation framing
- **WHEN** a reviewer reads Section 1 of README.md
- **THEN** the narrative explicitly frames the demo as a five-minute screenshot presentation of the single-page Streamlit application (`app.py`) rather than a live terminal or browser execution

### Requirement: Concise Sentence and Tense Compliance
The demo description SHALL consist of between 3 and 6 sentences written in the present tense describing existing, operational dashboard capabilities.

#### Scenario: Sentence count and tense verification
- **WHEN** evaluating the demo description paragraph in Section 1
- **THEN** the text contains between 3 and 6 grammatical sentences, uses present-tense verbs throughout, and references only verified production features without hypothetical, aspirational, or experimental extensions

### Requirement: Concrete Artifact and Layout Specification
The demo description SHALL cite concrete codebase filenames and visual layout components that structure the presentation slides.

#### Scenario: Explicit artifact and layout mentions
- **WHEN** reading the demo description
- **THEN** it explicitly names `app.py` and `data/processed/analytics_summary.json`, and identifies concrete UI components including the persistent sticky filter bar, aggregate KPI cards, prevalence vs distinctiveness charts, bivariate 2D scatter plot with Lift = 1.00 reference line, European choropleth map, cross-country 100% stacked occupational composition bar chart, and complete skill demand table

### Requirement: Empirical Metrics Synchronization
The demo description SHALL cite exact empirical statistics matching the refreshed 24,488 posting snapshot serialized in `data/processed/analytics_summary.json`.

#### Scenario: Exact metric verification
- **WHEN** inspecting numerical claims in Section 1
- **THEN** the text quotes Python prevalence at 73.8% (1.29× lift) for Data Science and 42.2% (0.74× lift) for Data Analytics, cites the 11 EU member states meeting the $N \ge 300$ reliability threshold, and notes descriptive seniority reporting coverage at 42.9%
