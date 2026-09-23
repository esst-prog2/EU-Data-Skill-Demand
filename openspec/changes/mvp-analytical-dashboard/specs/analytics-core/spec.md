# Spec Delta: analytics-core

## Purpose

Provides reusable pure-Python mathematical and filtering functions for skill prevalence, distinctiveness lift, support noise thresholds, and geographic sample size criteria.

## ADDED Requirements

### Requirement: Skill Prevalence Calculation
The system SHALL calculate job-level skill prevalence as the proportion of unique job postings containing the skill within a specific occupational category ($P(\text{skill} \mid \text{category})$) and across the overall corpus ($P(\text{skill} \mid \text{corpus})$).

#### Scenario: 100% and 0% prevalence extremes
- **WHEN** a skill appears in every `data_engineering` posting and no `data_analytics` posting
- **THEN** the system calculates prevalence as `1.0` (100%) for `data_engineering` and `0.0` (0%) for `data_analytics`

### Requirement: Skill Lift Calculation
The system SHALL compute skill lift as the ratio of within-category skill prevalence to overall corpus skill prevalence:
$$\text{Lift} = \frac{P(\text{skill} \mid \text{category})}{P(\text{skill} \mid \text{corpus})}$$

#### Scenario: Lift score computation
- **WHEN** a skill has prevalence `0.70` in `data_science` and `0.50` in the overall corpus
- **THEN** the system calculates lift as `1.4`

#### Scenario: Zero prevalence lift
- **WHEN** a skill has `0.0` prevalence in a category
- **THEN** the system returns a lift of `0.0`

### Requirement: Distinctive-Skill Ranking and Noise Filtering
The system SHALL filter candidate distinctive skills using a two-stage support rule:
1. **Primary Eligibility**: A skill MUST appear in at least 20 postings within the selected category ($N_{\text{cat}} \ge 20$) AND have a within-category prevalence of at least 1.5% ($P_{\text{cat}} \ge 0.015$).
2. **Ranking & Lift Cutoff**: Eligible skills SHALL be ranked in descending order of lift, selecting up to the Top 10 skills that have $\text{Lift} > 1.0$. Skills with $\text{Lift} \le 1.0$ SHALL NOT appear in the distinctive-skill ranking.

#### Scenario: Low-frequency skill filtered out
- **WHEN** a skill appears 5 times with Lift `3.5` in a category with 1,132 postings ($N < 20$ and $P < 1.5\%$)
- **THEN** the skill is disqualified from the distinctive-skill ranking despite high lift

#### Scenario: Eligible skill ranking with lift greater than 1
- **WHEN** 15 skills in a category satisfy $N \ge 20$ and $P \ge 1.5\%$, with 12 having Lift $> 1.0$ and 3 having Lift $\le 1.0$
- **THEN** the system returns the top 10 ranked by highest lift among those with Lift $> 1.0$, excluding the skills with Lift $\le 1.0$

### Requirement: Geographic Sample Size Thresholding
The system SHALL separate EU-27 member states into eligible and excluded sets for occupational composition comparisons based on an observed sample size threshold of $N \ge 300$ postings.

#### Scenario: Country with fewer than 300 postings
- **WHEN** a member state has 150 observed postings in the corpus
- **THEN** the system retains it for raw map display but excludes it from the occupational composition comparison

#### Scenario: Country with at least 300 postings
- **WHEN** a member state has 450 observed postings
- **THEN** the system includes it in the occupational composition comparison

