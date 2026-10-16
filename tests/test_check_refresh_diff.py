"""
tests/test_check_refresh_diff.py

Unit tests for scripts/check_refresh_diff.py idempotency and diff-checking logic:
- Volatile timestamp differences ("generated_at", "collection_timestamp_utc") ignored.
- Substantive KPI, category, or metadata differences detected.
"""

from __future__ import annotations

import pytest

from scripts.check_refresh_diff import (
    has_substantive_metadata_diff,
    has_substantive_summary_diff,
)


class TestSubstantiveSummaryDiff:
    """Verifies that analytics summary comparison detects genuine metric changes and ignores timestamps."""

    def test_identical_summaries_except_timestamp_returns_no_diff(self):
        baseline = {
            "generated_at": "2026-09-29 18:03:43 UTC",
            "kpis": {"total_postings": 23138, "total_countries": 27},
            "market_overview": {"category_shares": []},
            "category_profiles": {"data_science": {"total_postings": 2142}},
            "geographic": {"threshold": 300},
        }
        current = {
            "generated_at": "2026-10-15 03:00:00 UTC",  # Differing timestamp
            "kpis": {"total_postings": 23138, "total_countries": 27},
            "market_overview": {"category_shares": []},
            "category_profiles": {"data_science": {"total_postings": 2142}},
            "geographic": {"threshold": 300},
        }
        has_diff, reason = has_substantive_summary_diff(current, baseline)
        assert not has_diff
        assert "No substantive differences" in reason

    def test_kpi_difference_detected(self):
        baseline = {
            "generated_at": "2026-09-29 18:03:43 UTC",
            "kpis": {"total_postings": 23138},
            "market_overview": {},
            "category_profiles": {},
            "geographic": {},
        }
        current = {
            "generated_at": "2026-10-15 03:00:00 UTC",
            "kpis": {"total_postings": 23500},  # Count changed
            "market_overview": {},
            "category_profiles": {},
            "geographic": {},
        }
        has_diff, reason = has_substantive_summary_diff(current, baseline)
        assert has_diff
        assert "Section 'kpis' differs" in reason

    def test_category_profile_difference_detected(self):
        baseline = {
            "kpis": {},
            "market_overview": {},
            "category_profiles": {"data_science": {"prevalence": 0.66}},
            "geographic": {},
        }
        current = {
            "kpis": {},
            "market_overview": {},
            "category_profiles": {"data_science": {"prevalence": 0.68}},
            "geographic": {},
        }
        has_diff, reason = has_substantive_summary_diff(current, baseline)
        assert has_diff
        assert "Section 'category_profiles' differs" in reason


class TestSubstantiveMetadataDiff:
    """Verifies that collection metadata comparison detects genuine count/distribution changes."""

    def test_identical_metadata_except_timestamp_returns_no_diff(self):
        baseline = {
            "source": "FreeHire",
            "api_endpoint": "https://freehire.me/api/v1/agent/jobs/search",
            "collection_timestamp_utc": "2026-09-29T18:03:43.554417+00:00",
            "geographic_scope": "European Union EU-27",
            "countries": {"DE": "Germany"},
            "categories": ["data_engineering"],
            "country_count": 1,
            "category_count": 1,
            "unique_jobs": 23138,
            "category_distribution": {"data_engineering": 23138},
            "country_distribution": {"DE": 23138},
            "query_summary": [],
        }
        current = dict(baseline)
        current["collection_timestamp_utc"] = "2026-10-15T03:00:00.000000+00:00"  # Differing timestamp

        has_diff, reason = has_substantive_metadata_diff(current, baseline)
        assert not has_diff
        assert "No substantive differences" in reason

    def test_unique_jobs_difference_detected(self):
        baseline = {"unique_jobs": 23138}
        current = {"unique_jobs": 23200}

        has_diff, reason = has_substantive_metadata_diff(current, baseline)
        assert has_diff
        assert "Metadata field 'unique_jobs' differs" in reason
