# Tasks: Final Demo Description (Homework 8)

## 1. Demo Narrative Formulation & Alignment

- [x] 1.1 Verify exact empirical metrics in `data/processed/analytics_summary.json` (corpus size, category sizes, Python prevalence and lift in Data Science vs. Data Analytics, country threshold counts, seniority coverage) and confirm values match proposed narrative.
- [x] 1.2 Draft the 5-sentence screenshot presentation narrative in present tense incorporating concrete filenames (`app.py`, `data/processed/analytics_summary.json`), visual UI components, and verified statistics.

## 2. Documentation Update

- [x] 2.1 Update Section 1 ("The Demo") in `README.md` with the verified 5-sentence presentation description while preserving `### Scope Decisions` and all subsequent sections.
- [x] 2.2 Record the demo description revision in `PLANNING_LOG.md` following project convention.

## 3. Verification & OpenSpec Validation

- [x] 3.1 Validate the OpenSpec change artifacts using `npx openspec validate final-demo-description` and verify zero errors.
- [x] 3.2 Run test suite (`uv run pytest tests/test_app.py`) to confirm zero regressions in dashboard rendering tests.
- [x] 3.3 Verify git diff and working tree status, confirming no unexpected modifications or unintended staged files exist.
