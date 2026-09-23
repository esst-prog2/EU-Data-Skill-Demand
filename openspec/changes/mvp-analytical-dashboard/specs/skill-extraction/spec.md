# Spec Delta: skill-extraction

## Purpose

Defines controlled vocabulary matching and hybrid skill extraction logic across FreeHire native tags and job description text for five target skill domains.

## ADDED Requirements

### Requirement: Controlled Technical Skill Vocabulary
The system SHALL maintain a curated vocabulary of canonical skills and aliases organized into five distinct categories: `Programming languages`, `Databases & data warehouses`, `BI & visualization`, `Cloud & infrastructure`, and `ML/AI frameworks & tools`.

#### Scenario: Alias resolution
- **WHEN** raw skill text contains aliases such as `PowerBI` or `Postgres`
- **THEN** the system normalizes the term to its canonical name `Power BI` or `PostgreSQL`

### Requirement: Hybrid Skill Extraction
The system SHALL extract skills from a job posting using a hybrid priority rule: match canonical terms against native `skills` tags first, and scan the job `description` text for vocabulary skills absent from native tags.

#### Scenario: Description fallback for untagged tools
- **WHEN** a job posting contains no native tags for `Excel` or `R` but mentions them in the description text
- **THEN** the system extracts `Excel` and `R` as present

#### Scenario: Absence of unmentioned skills
- **WHEN** a job posting mentions `SQL` and `Excel` but does not mention `Python`
- **THEN** the system extracts `SQL` and `Excel` as present and marks `Python` as absent

### Requirement: Binary Job-Level Skill Presence
The system SHALL treat skill presence as a binary set per unique posting, counting a detected skill at most once per posting regardless of repeated occurrences in tags or text.

#### Scenario: Deduplicating repeated skill mentions
- **WHEN** a posting mentions `Python` in both its native tags and three times in the text
- **THEN** `Python` is recorded exactly once as present (`True`) for that posting

