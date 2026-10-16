"""
tests/test_app.py

Focused tests for app.py summary validation and dynamic geographic note extraction:
- Valid summary data passes without error
- Production summary JSON passes validation
- Missing required sections and non-dictionary section types
- Empty category_profiles rejected
- kpis["total_categories"] matching len(category_profiles) constraint
- Missing KPI fields rejected
- Numeric type validation (booleans rejected, non-numeric types rejected)
- Range validation (zero/negative postings, out-of-range country/category counts, invalid percentages)
- get_geographic_note_data validation (matching counts, sum to 27, uniqueness of codes)
- Profile total_postings type and non-negative integer validation
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict

import pytest

from app import (
    DATA_PATH,
    format_snapshot_date,
    get_footer_text,
    get_geographic_note_data,
    get_intro_text,
    validate_analytics_summary,
)


@pytest.fixture
def valid_summary_data() -> Dict[str, Any]:
    """Provides a minimal, valid analytics summary dictionary."""
    category_ids = [
        "data_engineering",
        "data_analytics",
        "ai_engineering",
        "data_science",
        "ml_ai",
    ]
    return {
        "generated_at": "2026-10-15 12:00:00 UTC",
        "kpis": {
            "total_postings": 23138,
            "total_countries": 27,
            "total_categories": 5,
            "seniority_coverage_pct": 38.8,
        },
        "market_overview": {
            "category_shares": [
                {"category_id": cid, "category_name": cid.replace("_", " ").title(), "count": 2000, "share_pct": 20.0}
                for cid in category_ids
            ],
            "top_skills_overall": [
                {"skill": "Python", "prevalence_pct": 65.0}
            ],
        },
        "category_profiles": {
            cid: {
                "category_id": cid,
                "category_name": cid.replace("_", " ").title(),
                "total_postings": 2000,
                "top_in_demand": [],
                "top_distinctive": [],
            }
            for cid in category_ids
        },
        "geographic": {
            "threshold": 300,
            "eligible_count": 2,
            "excluded_count": 25,
            "composition_eligible": [
                {"iso_code": "ES"},
                {"iso_code": "DE"},
            ],
            "country_map": [],
        },
    }


class TestValidateAnalyticsSummary:
    """Tests for validate_analytics_summary schema and boundary validation."""

    def test_valid_summary_passes_validation(self, valid_summary_data):
        # Should execute without raising ValueError
        validate_analytics_summary(valid_summary_data)

    def test_production_summary_file_passes_validation(self):
        assert DATA_PATH.exists()
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate_analytics_summary(data)

    def test_non_dict_data_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a dictionary"):
            validate_analytics_summary("not-a-dict")  # type: ignore

    @pytest.mark.parametrize(
        "section",
        ["kpis", "market_overview", "category_profiles", "geographic"],
    )
    def test_missing_required_section_raises_value_error(self, valid_summary_data, section):
        del valid_summary_data[section]
        with pytest.raises(ValueError, match=f"missing required section: '{section}'"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "section",
        ["kpis", "market_overview", "category_profiles", "geographic"],
    )
    def test_non_dict_section_raises_value_error(self, valid_summary_data, section):
        valid_summary_data[section] = ["not", "a", "dict"]
        with pytest.raises(ValueError, match=f"Section '{section}' must be a dictionary"):
            validate_analytics_summary(valid_summary_data)

    def test_empty_category_profiles_raises_value_error(self, valid_summary_data):
        valid_summary_data["category_profiles"] = {}
        with pytest.raises(ValueError, match="Section 'category_profiles' cannot be empty"):
            validate_analytics_summary(valid_summary_data)

    def test_total_categories_mismatch_with_category_profiles_raises_value_error(self, valid_summary_data):
        valid_summary_data["kpis"]["total_categories"] = 4
        with pytest.raises(ValueError, match="does not match the number of category profiles"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "kpi_field",
        ["total_postings", "total_countries", "total_categories", "seniority_coverage_pct"],
    )
    def test_missing_kpi_field_raises_value_error(self, valid_summary_data, kpi_field):
        del valid_summary_data["kpis"][kpi_field]
        with pytest.raises(ValueError, match=f"missing required field: '{kpi_field}'"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        ("field", "bad_type_val"),
        [
            ("total_postings", True),       # bool rejected
            ("total_postings", "23138"),     # string rejected
            ("total_postings", 23138.5),     # float rejected for int KPI
            ("total_countries", False),      # bool rejected
            ("total_countries", "27"),
            ("total_countries", 27.0),
            ("total_categories", True),      # bool rejected
            ("total_categories", "5"),
            ("total_categories", 5.0),
            ("seniority_coverage_pct", True), # bool rejected
            ("seniority_coverage_pct", "38.8%"),
            ("seniority_coverage_pct", [38.8]),
        ],
    )
    def test_invalid_kpi_types_raise_value_error(self, valid_summary_data, field, bad_type_val):
        valid_summary_data["kpis"][field] = bad_type_val
        with pytest.raises(ValueError):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "bad_postings",
        [0, -1, -500],
    )
    def test_zero_or_negative_total_postings_raises_value_error(self, valid_summary_data, bad_postings):
        valid_summary_data["kpis"]["total_postings"] = bad_postings
        with pytest.raises(ValueError, match="must be positive"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "bad_countries",
        [0, 28, -1, 100],
    )
    def test_out_of_range_total_countries_raises_value_error(self, valid_summary_data, bad_countries):
        valid_summary_data["kpis"]["total_countries"] = bad_countries
        with pytest.raises(ValueError, match="must be between 1 and 27"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "bad_categories",
        [0, 6, -1, 10],
    )
    def test_out_of_range_total_categories_raises_value_error(self, valid_summary_data, bad_categories):
        valid_summary_data["kpis"]["total_categories"] = bad_categories
        with pytest.raises(ValueError, match="must be between 1 and 5"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "bad_pct",
        [-0.1, 100.1, -10.0, 150.0, float("nan"), float("inf"), float("-inf")],
    )
    def test_out_of_range_or_non_finite_seniority_pct_raises_value_error(self, valid_summary_data, bad_pct):
        valid_summary_data["kpis"]["seniority_coverage_pct"] = bad_pct
        with pytest.raises(ValueError, match="must be a finite number between 0.0 and 100.0"):
            validate_analytics_summary(valid_summary_data)


class TestGetGeographicNoteData:
    """Tests for get_geographic_note_data extraction and validation."""

    def test_valid_geographic_data_returns_expected_tuple(self):
        geo = {
            "threshold": 300,
            "eligible_count": 3,
            "excluded_count": 24,
            "composition_eligible": [
                {"iso_code": "ES"},
                {"iso_code": "FR"},
                {"iso_code": "DE"},
            ],
        }
        threshold, elig_cnt, excl_cnt, codes_str = get_geographic_note_data(geo)
        assert threshold == 300
        assert elig_cnt == 3
        assert excl_cnt == 24
        assert codes_str == "ES, FR, DE"

    def test_non_dict_geographic_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a dictionary"):
            get_geographic_note_data("not-a-dict")  # type: ignore

    @pytest.mark.parametrize("bad_thresh", [0, -300, "300", True, None])
    def test_invalid_threshold_raises_value_error(self, bad_thresh):
        geo = {
            "threshold": bad_thresh,
            "eligible_count": 1,
            "excluded_count": 26,
            "composition_eligible": [{"iso_code": "DE"}],
        }
        with pytest.raises(ValueError, match="threshold"):
            get_geographic_note_data(geo)

    def test_composition_eligible_not_a_list_raises_value_error(self):
        geo = {
            "threshold": 300,
            "eligible_count": 1,
            "excluded_count": 26,
            "composition_eligible": "not-a-list",
        }
        with pytest.raises(ValueError, match="composition_eligible"):
            get_geographic_note_data(geo)

    @pytest.mark.parametrize(
        "bad_record",
        [
            {},
            {"iso_code": ""},
            {"iso_code": "   "},
            {"iso_code": None},
            {"iso_code": 123},
        ],
    )
    def test_composition_record_missing_iso_code_raises_value_error(self, bad_record):
        geo = {
            "threshold": 300,
            "eligible_count": 1,
            "excluded_count": 26,
            "composition_eligible": [bad_record],
        }
        with pytest.raises(ValueError, match="missing valid 'iso_code'"):
            get_geographic_note_data(geo)

    def test_duplicate_eligible_country_codes_raises_value_error(self):
        geo = {
            "threshold": 300,
            "eligible_count": 2,
            "excluded_count": 25,
            "composition_eligible": [
                {"iso_code": "ES"},
                {"iso_code": "ES"},
            ],
        }
        with pytest.raises(ValueError, match="contains duplicate country codes"):
            get_geographic_note_data(geo)

    def test_eligible_count_mismatch_with_composition_eligible_records_raises_value_error(self):
        geo = {
            "threshold": 300,
            "eligible_count": 3,
            "excluded_count": 24,
            "composition_eligible": [
                {"iso_code": "ES"},
                {"iso_code": "FR"},
            ],  # len is 2, not 3
        }
        with pytest.raises(ValueError, match="does not match the number of records in 'composition_eligible'"):
            get_geographic_note_data(geo)

    def test_eligible_and_excluded_counts_not_summing_to_27_raises_value_error(self):
        geo = {
            "threshold": 300,
            "eligible_count": 12,
            "excluded_count": 10,  # 12 + 10 = 22 != 27
            "composition_eligible": [{"iso_code": f"C{i}"} for i in range(12)],
        }
        with pytest.raises(ValueError, match="must sum to 27 EU member states"):
            get_geographic_note_data(geo)

    @pytest.mark.parametrize(
        ("field", "bad_val"),
        [
            ("eligible_count", -1),
            ("eligible_count", True),
            ("eligible_count", "12"),
            ("excluded_count", -1),
            ("excluded_count", False),
            ("excluded_count", "15"),
        ],
    )
    def test_invalid_counts_raise_value_error(self, field, bad_val):
        geo = {
            "threshold": 300,
            "eligible_count": 1,
            "excluded_count": 26,
            "composition_eligible": [{"iso_code": "ES"}],
        }
        geo[field] = bad_val
        with pytest.raises(ValueError, match=field):
            get_geographic_note_data(geo)


class TestCategoryProfileValidation:
    """Verifies that category profiles are properly validated inside validate_analytics_summary."""

    def test_non_dict_category_profile_raises_value_error(self, valid_summary_data):
        valid_summary_data["category_profiles"]["data_engineering"] = "not-a-dict"
        with pytest.raises(ValueError, match="Category profile 'data_engineering' must be a dictionary"):
            validate_analytics_summary(valid_summary_data)

    def test_missing_total_postings_in_category_profile_raises_value_error(self, valid_summary_data):
        del valid_summary_data["category_profiles"]["data_engineering"]["total_postings"]
        with pytest.raises(ValueError, match="must have a non-negative integer 'total_postings'"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize(
        "bad_total",
        [
            True,
            False,
            "100",
            None,
            -1,
            -50,
            [100],
        ],
    )
    def test_invalid_total_postings_in_category_profile_raises_value_error(self, valid_summary_data, bad_total):
        valid_summary_data["category_profiles"]["data_engineering"]["total_postings"] = bad_total
        with pytest.raises(ValueError, match="must have a non-negative integer 'total_postings'"):
            validate_analytics_summary(valid_summary_data)

    @pytest.mark.parametrize("valid_val", [0, 1, 500, 23138])
    def test_valid_zero_and_positive_total_postings_accepted(self, valid_summary_data, valid_val):
        valid_summary_data["category_profiles"]["data_engineering"]["total_postings"] = valid_val
        validate_analytics_summary(valid_summary_data)


class TestSnapshotDateFormatting:
    """Unit tests for format_snapshot_date helper."""

    def test_format_snapshot_date_valid_utc_iso(self):
        assert format_snapshot_date("2026-09-29T18:03:43.554417+00:00") == "29 September 2026"

    def test_format_snapshot_date_utc_calendar_date_conversion(self):
        # 23:30 in UTC-2 is 01:30 next day in UTC
        assert format_snapshot_date("2026-09-29T23:30:00-02:00") == "30 September 2026"
        # 01:00 in UTC+3 is 22:00 previous day in UTC
        assert format_snapshot_date("2026-09-29T01:00:00+03:00") == "28 September 2026"

    def test_format_snapshot_date_rejects_naive_iso_without_timezone(self):
        assert format_snapshot_date("2026-09-29T18:03:43") is None

    def test_format_snapshot_date_single_digit_day(self):
        assert format_snapshot_date("2026-05-04T12:00:00Z") == "4 May 2026"

    @pytest.mark.parametrize(
        "bad_input",
        [
            None,
            "",
            "   ",
            "not-a-date",
            "2026-13-45",
            12345,
            99.9,
            True,
            False,
            [],
            {},
        ],
    )
    def test_format_snapshot_date_invalid_and_missing_inputs(self, bad_input):
        assert format_snapshot_date(bad_input) is None


class TestDynamicPostingCountAndDateRendering:
    """Tests dynamic posting counts and snapshot date labels in introduction and footer."""

    def test_intro_and_footer_renders_dynamic_count_and_snapshot_date(self):
        intro = get_intro_text(24500, "29 September 2026")
        footer = get_footer_text(24500, "29 September 2026")

        assert "24,500" in intro
        assert "Latest snapshot collected: 29 September 2026" in intro
        assert "23,138" not in intro

        assert "24,500" in footer
        assert "Latest snapshot collected: 29 September 2026" in footer
        assert "23,138" not in footer

    def test_intro_and_footer_omits_date_label_when_snapshot_date_none(self):
        intro = get_intro_text(24500, None)
        footer = get_footer_text(24500, None)

        assert "24,500" in intro
        assert "Latest snapshot collected" not in intro
        assert "23,138" not in intro

        assert "24,500" in footer
        assert "Latest snapshot collected" not in footer
        assert "23,138" not in footer

    def test_intro_and_footer_consistent_with_production_count(self):
        intro = get_intro_text(23138, "29 September 2026")
        footer = get_footer_text(23138, "29 September 2026")

        assert "23,138" in intro
        assert "Latest snapshot collected: 29 September 2026" in intro
        assert "23,138" in footer
        assert "Latest snapshot collected: 29 September 2026" in footer

    def test_production_summary_renders_snapshot_collected_date(self):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        snapshot_date = format_snapshot_date(data.get("snapshot_collected_at"))
        assert snapshot_date == "29 September 2026"
        intro = get_intro_text(data["kpis"]["total_postings"], snapshot_date)
        footer = get_footer_text(data["kpis"]["total_postings"], snapshot_date)
        assert "23,138" in intro
        assert "Latest snapshot collected: 29 September 2026" in intro
        assert "23,138" in footer
        assert "Latest snapshot collected: 29 September 2026" in footer


class TestOlderSummaryRenderingWithoutSnapshotDate:
    """Verifies that summaries lacking snapshot_collected_at render cleanly without raw metadata."""

    def test_summary_without_snapshot_date_renders_dynamic_count(self):
        summary = {"kpis": {"total_postings": 23138}}
        snapshot_date = format_snapshot_date(summary.get("snapshot_collected_at"))
        assert snapshot_date is None
        intro = get_intro_text(summary["kpis"]["total_postings"], snapshot_date)
        footer = get_footer_text(summary["kpis"]["total_postings"], snapshot_date)

        assert "23,138" in intro
        assert "Latest snapshot collected" not in intro
        assert "23,138" in footer
        assert "Latest snapshot collected" not in footer


class TestValidationCompatibility:
    """Verifies that validate_analytics_summary remains backwards-compatible and resilient to metadata."""

    def test_validation_passes_with_snapshot_collected_at_present(self, valid_summary_data):
        valid_summary_data["snapshot_collected_at"] = "2026-09-29T18:03:43.554417+00:00"
        validate_analytics_summary(valid_summary_data)

    def test_validation_passes_with_snapshot_collected_at_none(self, valid_summary_data):
        valid_summary_data["snapshot_collected_at"] = None
        validate_analytics_summary(valid_summary_data)

    def test_validation_passes_with_snapshot_collected_at_omitted(self, valid_summary_data):
        valid_summary_data.pop("snapshot_collected_at", None)
        validate_analytics_summary(valid_summary_data)

    def test_validation_does_not_crash_on_malformed_optional_metadata(self, valid_summary_data):
        valid_summary_data["snapshot_collected_at"] = 12345
        validate_analytics_summary(valid_summary_data)
        assert format_snapshot_date(valid_summary_data["snapshot_collected_at"]) is None
