# Spec Delta: data-pipeline

## Purpose

Executes offline batch processing on the frozen FreeHire snapshot to generate precalculated analytics artifacts for instant dashboard loading.

## ADDED Requirements

### Requirement: Raw Snapshot Processing
The pipeline SHALL read the frozen, audited dataset of 22,985 EU-27 job postings from `data/raw/freehire_eu_raw.json` without modifying or overwriting raw source files.

#### Scenario: Preserving raw data immutability
- **WHEN** the batch preprocessing script runs
- **THEN** `data/raw/freehire_eu_raw.json` remains unaltered

### Requirement: Precomputed JSON Summary Generation
The pipeline SHALL execute skill extraction and analytical computations via reusable functions from `src/analytics.py` and serialize the precalculated metrics into `data/processed/analytics_summary.json`.

#### Scenario: Serialized metric structure
- **WHEN** the preprocessing pipeline completes
- **THEN** `data/processed/analytics_summary.json` contains corpus totals, category composition shares, corpus top skills, per-category prevalence/lift rankings, and country posting distributions

### Requirement: Fast Load Constraint
The precomputed artifact SHALL enable downstream dashboard loading within 500 milliseconds without running live extraction or aggregate computations over raw postings.

#### Scenario: App startup latency
- **WHEN** the dashboard loads `data/processed/analytics_summary.json`
- **THEN** data ingestion completes in $< 500$ ms

