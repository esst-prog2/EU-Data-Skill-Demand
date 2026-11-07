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

from collections import Counter
import json
import plotly.graph_objects as go
import math
from pathlib import Path
from typing import Any, Dict

import io
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import app
from src.analytics import SKILL_FAMILIES

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

        raw_ts = data.get("snapshot_collected_at")
        assert isinstance(raw_ts, str) and raw_ts.strip()

        snapshot_date = format_snapshot_date(raw_ts)
        assert snapshot_date is not None

        total_postings = data["kpis"]["total_postings"]
        total_str = f"{total_postings:,}"

        intro = get_intro_text(total_postings, snapshot_date)
        footer = get_footer_text(total_postings, snapshot_date)

        assert total_str in intro
        assert f"Latest snapshot collected: {snapshot_date}" in intro
        assert total_str in footer
        assert f"Latest snapshot collected: {snapshot_date}" in footer


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


APP_FILE = str(Path(__file__).resolve().parent.parent / "app.py")


class TestSection2SkillQuadrantAndFamilyFilter:
    """UI regression tests for bivariate scatter plot and skill-family filtering."""

    def test_production_section2_controls_and_scatter_rendering(self):
        """Verifies selectboxes, scatter plot, parity line, and interpretation guide on single page."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)
        assert len(at.exception) == 0

        # Verify selectors
        labels = [sb.label for sb in at.selectbox]
        assert any("Category" in l or "Job Family" in l for l in labels)
        assert "Filter by Technical Skill Family:" in labels

        family_sb = next(sb for sb in at.selectbox if sb.label == "Filter by Technical Skill Family:")
        assert family_sb.value == "All Families"
        assert set(SKILL_FAMILIES).issubset(set(family_sb.options))

        # In default state (All Categories), verify guidance annotation is present explaining Lift = 1.00
        charts = at.get("plotly_chart")
        assert any("Lift = 1.00 by definition" in str(ch.proto.spec) for ch in charts)

        # Select an occupational role (e.g. Data Science) to activate bivariate markers
        role_sb = next(sb for sb in at.selectbox if "Occupational Role (for Scatter Plot)" in sb.label)
        role_sb.select("data_science").run(timeout=15)
        assert len(at.exception) == 0

        # Verify scatter plot with markers
        scatter_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            yaxis_title = str(spec.get("layout", {}).get("yaxis", {}).get("title", {}).get("text", ""))
            if "Distinctiveness Lift" in yaxis_title and any(t.get("mode") == "markers+text" for t in spec.get("data", [])):
                scatter_chart = el
                break

        assert scatter_chart is not None, "Scatter plot chart not found on dashboard"
        scatter_spec = json.loads(scatter_chart.proto.spec)

        # Parity line at Lift = 1.0
        shapes = scatter_spec.get("layout", {}).get("shapes", [])
        parity_lines = [s for s in shapes if s.get("y0") == 1.0 and s.get("y1") == 1.0]
        assert len(parity_lines) >= 1
        assert parity_lines[0].get("line", {}).get("dash") == "dash"

        # Annotation
        annotations = scatter_spec.get("layout", {}).get("annotations", [])
        assert any("Corpus Parity (Lift = 1.0)" in a.get("text", "") for a in annotations)

        # Interpretation callout
        info_texts = [inf.value for inf in at.info]
        assert any("Interpreting Prevalence vs. Distinctiveness" in t for t in info_texts)

    def test_section2_family_filter_interaction(self):
        """Verifies selecting a specific skill family updates the view without exceptions."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)
        assert len(at.exception) == 0

        # Select occupational role to activate scatter plot
        role_sb = next(sb for sb in at.selectbox if "Occupational Role (for Scatter Plot)" in sb.label)
        role_sb.select("data_science").run(timeout=15)
        assert len(at.exception) == 0

        family_sb = next(sb for sb in at.selectbox if sb.label == "Filter by Technical Skill Family:")
        target_family = "Cloud & infrastructure"
        family_sb.select(target_family).run(timeout=15)

        assert len(at.exception) == 0
        updated_family_sb = next(sb for sb in at.selectbox if sb.label == "Filter by Technical Skill Family:")
        assert updated_family_sb.value == target_family

        # Verify scatter plot reflects only selected family
        scatter_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            yaxis_title = str(spec.get("layout", {}).get("yaxis", {}).get("title", {}).get("text", ""))
            if "Distinctiveness Lift" in yaxis_title and any(t.get("mode") == "markers+text" for t in spec.get("data", [])):
                scatter_chart = el
                break

        assert scatter_chart is not None
        scatter_spec = json.loads(scatter_chart.proto.spec)
        trace_names = [t.get("name") for t in scatter_spec.get("data", [])]
        assert trace_names == [target_family]

    def test_section2_synthetic_empty_and_subthreshold_handling(self):
        """Verifies synthetic summary with sub-threshold and empty category handles gracefully."""
        synth_data = {
            "kpis": {
                "total_postings": 1000,
                "total_countries": 27,
                "total_categories": 2,
                "seniority_coverage_pct": 40.0,
            },
            "market_overview": {
                "category_shares": [
                    {"category_id": "active_cat", "category_name": "Active Role", "count": 1000, "share_pct": 100.0},
                    {"category_id": "empty_cat", "category_name": "Empty Role", "count": 0, "share_pct": 0.0},
                ],
                "top_skills_overall": [],
            },
            "category_profiles": {
                "active_cat": {
                    "category_id": "active_cat",
                    "category_name": "Active Role",
                    "total_postings": 1000,
                    "top_in_demand": [
                        {"canonical": "Spark", "skill_group": "ML/AI frameworks & tools", "count": 100, "prevalence_pct": 10.0}
                    ],
                    "top_distinctive": [
                        {"canonical": "Spark", "skill_group": "ML/AI frameworks & tools", "count": 100, "prevalence_pct": 10.0, "lift": 2.5}
                    ],
                    "all_skills": [
                        {"canonical": "Spark", "skill_group": "ML/AI frameworks & tools", "count": 100, "prevalence": 0.10, "prevalence_pct": 10.0, "lift": 2.5},
                        {"canonical": "NicheTool", "skill_group": "Programming languages", "count": 5, "prevalence": 0.005, "prevalence_pct": 0.5, "lift": 3.0},
                    ],
                },
                "empty_cat": {
                    "category_id": "empty_cat",
                    "category_name": "Empty Role",
                    "total_postings": 0,
                    "top_in_demand": [],
                    "top_distinctive": [],
                    "all_skills": [],
                },
            },
            "geographic": {
                "threshold": 300,
                "eligible_count": 0,
                "excluded_count": 27,
                "composition_eligible": [],
                "country_map": [],
            },
        }

        orig_open = open

        def mock_open(file, *args, **kwargs):
            if "analytics_summary.json" in str(file):
                return io.StringIO(json.dumps(synth_data))
            return orig_open(file, *args, **kwargs)

        try:
            with patch("builtins.open", side_effect=mock_open):
                st.cache_data.clear()
                at = AppTest.from_file(APP_FILE).run(timeout=15)
                assert len(at.exception) == 0

                cat_sb = next(sb for sb in at.selectbox if "Category" in sb.label or "Job Family" in sb.label)
                assert len(at.exception) == 0
        finally:
            st.cache_data.clear()


class TestSinglePageDashboardAndGlobalFilters:
    """UI regression tests for the single-page Power BI style dashboard and global filters."""

    def test_default_dashboard_layout_and_kpis(self):
        """Verifies default dashboard renders 4 global filters (including country multiselect), 4 KPI cards, and charts."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)
        assert len(at.exception) == 0

        # Title
        assert any("EU Data Jobs & Skill Demand" in t.value for t in at.title)

        # Country Searchable Multi-Select
        assert len(at.multiselect) >= 1
        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        assert country_ms.value == []  # default empty signifies All Countries

        # 3 Other Selectboxes
        sb_labels = [sb.label for sb in at.selectbox]
        assert any("Job Family" in l for l in sb_labels)
        assert any("Seniority" in l for l in sb_labels)
        assert any("Skill Family" in l for l in sb_labels)

        # 4 KPI cards
        metric_labels = [m.label for m in at.metric]
        assert "Matching Postings" in metric_labels
        assert "Countries with Postings" in metric_labels
        assert "Detected Technical Skills" in metric_labels
        assert "Qualified Distinctive Skills" in metric_labels

        # Europe Map reframing parameters
        charts = at.get("plotly_chart")
        assert len(charts) >= 4

        map_chart = None
        for ch in charts:
            spec = json.loads(ch.proto.spec)
            geo = spec.get("layout", {}).get("geo", {})
            if geo.get("scope") == "europe":
                map_chart = ch
                break

        assert map_chart is not None, "Europe choropleth map not found"
        map_geo = json.loads(map_chart.proto.spec).get("layout", {}).get("geo", {})
        assert map_geo.get("scope") == "europe"
        assert map_geo.get("center", {}).get("lat") == 54.0
        assert map_geo.get("center", {}).get("lon") == 14.0
        assert map_geo.get("projection", {}).get("scale") == 1.05

        # Complete Skill Demand Table is visible by default (not in expander)
        assert len(at.dataframe) >= 1

    @pytest.mark.production_data
    def test_interconnected_filtering_country_category_seniority(self):
        """Verifies selecting Country (multiselect), Category, and Seniority updates KPIs, table, and banners on production data."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("HU").run(timeout=15)

        cat_sb = next(sb for sb in at.selectbox if "Job Family" in sb.label)
        cat_sb.select("Data Science").run(timeout=15)

        sen_sb = next(sb for sb in at.selectbox if "Seniority" in sb.label)
        sen_sb.select("Senior").run(timeout=15)

        assert len(at.exception) == 0

        # Matching postings for Hungarian Senior Data Scientists is 8 in refreshed dataset
        metrics_dict = {m.label: m.value for m in at.metric}
        assert metrics_dict["Matching Postings"] == "8"
        assert metrics_dict["Countries with Postings"] == "1 / 27"

        # Explicit denominator and dynamic coverage banner
        info_texts = [inf.value for inf in at.info]
        assert any("Seniority Coverage" in t and "13 of 21" in t for t in info_texts)

        # Small sample size warning banner (N < 300)
        warning_texts = [w.value for w in at.warning]
        assert any("Small Sample Size Warning" in w for w in warning_texts)

        # Traceability: Detected skills KPI matches the rows in complete table
        detected_kpi_val = int(metrics_dict["Detected Technical Skills"])
        table_df = at.dataframe[0].value
        assert len(table_df) == detected_kpi_val

    def test_interconnected_filtering_with_test_fixture(self):
        """Verifies Country, Category, and Seniority filtering updates KPIs, banners, and table using deterministic test fixture."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("HU").run(timeout=15)

        cat_sb = next(sb for sb in at.selectbox if "Job Family" in sb.label)
        cat_sb.select("Data Science").run(timeout=15)

        sen_sb = next(sb for sb in at.selectbox if "Seniority" in sb.label)
        sen_sb.select("Senior").run(timeout=15)

        assert len(at.exception) == 0

        metrics_dict = {m.label: m.value for m in at.metric}
        # In test fixture, HU Senior Data Science has matching postings
        assert int(metrics_dict["Matching Postings"]) > 0
        assert metrics_dict["Countries with Postings"] == "1 / 27"

        # Explicit denominator and dynamic coverage banner
        info_texts = [inf.value for inf in at.info]
        assert any("Seniority Coverage" in t for t in info_texts)

        # Small sample size warning banner (N < 300)
        warning_texts = [w.value for w in at.warning]
        assert any("Small Sample Size Warning" in w for w in warning_texts)

        # Traceability: Detected skills KPI matches the rows in complete table
        detected_kpi_val = int(metrics_dict["Detected Technical Skills"])
        table_df = at.dataframe[0].value
        assert len(table_df) == detected_kpi_val

    def test_multi_country_selection_and_denominator(self):
        """Verifies selecting multiple countries updates the Represented Countries KPI denominator."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("HU").select("DE").run(timeout=15)

        metrics_dict = {m.label: m.value for m in at.metric}
        assert metrics_dict["Countries with Postings"] == "2 / 27"

    def test_reset_button_restores_defaults(self):
        """Clicking Reset restores global filters, local chart selectors, dense view, and charts to defaults."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)
        assert len(at.exception) == 0

        # 1. Modify global filters
        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("DE").run(timeout=15)

        cat_sb = next(sb for sb in at.selectbox if "Job Family" in sb.label or "Category" in sb.label)
        cat_sb.select("data_science").run(timeout=15)

        sen_sb = next(sb for sb in at.selectbox if "Seniority" in sb.label)
        sen_sb.select("senior").run(timeout=15)

        fam_sb = next(sb for sb in at.selectbox if "Technical Skill Family" in sb.label)
        fam_sb.select("Programming languages").run(timeout=15)

        # 2. Modify chart-specific local selectors & dense checkbox
        dist_sb = next(sb for sb in at.selectbox if "for Distinctive Ranking" in sb.label)
        dist_sb.select("data_engineering").run(timeout=15)

        scatter_sb = next(sb for sb in at.selectbox if "for Scatter Plot" in sb.label)
        scatter_sb.select("ai_engineering").run(timeout=15)

        dense_cb = next(cb for cb in at.checkbox if "unqualified" in cb.label.lower())
        dense_cb.check().run(timeout=15)

        # Verify altered state before reset
        assert at.session_state["filter_countries"] == ["DE"]
        assert at.session_state["filter_category"] == "data_science"
        assert at.session_state["filter_seniority"] == "senior"
        assert at.session_state["filter_family"] == "Programming languages"
        assert at.session_state["local_dist_cat"] == "data_engineering"
        assert at.session_state["local_scatter_cat"] == "ai_engineering"

        # 3. Click Reset button
        reset_btn = next(b for b in at.button if "Reset" in b.label)
        reset_btn.click().run(timeout=15)
        assert len(at.exception) == 0

        # 4. Verify all widgets and session state restored to initial defaults
        updated_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        assert updated_ms.value == []
        assert at.session_state["filter_countries"] == []

        updated_cat = next(sb for sb in at.selectbox if "Job Family" in sb.label or "Category" in sb.label)
        assert updated_cat.value == "All Categories"
        assert at.session_state["filter_category"] == "All Categories"

        updated_sen = next(sb for sb in at.selectbox if "Seniority" in sb.label)
        assert updated_sen.value == "All Seniorities"
        assert at.session_state["filter_seniority"] == "All Seniorities"

        updated_fam = next(sb for sb in at.selectbox if "Technical Skill Family" in sb.label)
        assert updated_fam.value == "All Families"
        assert at.session_state["filter_family"] == "All Families"

        updated_dist = next(sb for sb in at.selectbox if "for Distinctive Ranking" in sb.label)
        assert updated_dist.value == "-- Select a Job Family for Distinctiveness --"
        assert at.session_state["local_dist_cat"] == "-- Select a Job Family for Distinctiveness --"

        updated_scatter = next(sb for sb in at.selectbox if "for Scatter Plot" in sb.label)
        assert updated_scatter.value == "-- Select a Job Family for Distinctiveness --"
        assert at.session_state["local_scatter_cat"] == "-- Select a Job Family for Distinctiveness --"

        updated_dense = next(cb for cb in at.checkbox if "unqualified" in cb.label.lower())
        assert updated_dense.value is False

        # 5. Verify visualizations reflect the unselected reset state
        charts = at.get("plotly_chart")
        # Scatter plot shows baseline parity guidance annotation
        assert any("Lift = 1.00 by definition" in str(ch.proto.spec) for ch in charts)

    def test_r_skill_demand_in_analytical_summary(self):
        """
        Verifies deterministic R skill demand directly from tracked data/processed/analytics_summary.json.
        Covers:
        - Data Analytics: 3,582 total, 364 R postings, 10.2% prevalence
        - Data Engineering: 13,592 total, 278 R postings, 2.0% prevalence
        - Data Science: 2,558 total, 420 R postings, 16.4% prevalence
        - ML/AI: 1,411 total, 43 R postings, 3.0% prevalence
        - AI Engineering: 3,345 total, 67 R postings, 2.0% prevalence
        - Total corpus postings = 24,488
        - Derived total R postings = 1,172
        """
        summary = app.load_analytics_summary()
        profiles = summary["category_profiles"]

        expected_r_by_category = {
            "data_analytics": {"total": 3582, "r_count": 364, "r_prev_pct": 10.2},
            "data_engineering": {"total": 13592, "r_count": 278, "r_prev_pct": 2.0},
            "data_science": {"total": 2558, "r_count": 420, "r_prev_pct": 16.4},
            "ml_ai": {"total": 1411, "r_count": 43, "r_prev_pct": 3.0},
            "ai_engineering": {"total": 3345, "r_count": 67, "r_prev_pct": 2.0},
        }

        derived_total_postings = 0
        derived_total_r = 0
        for cat_id, expected in expected_r_by_category.items():
            profile = profiles[cat_id]
            cat_total = profile["total_postings"]
            assert cat_total == expected["total"], f"Mismatch for {cat_id} total: got {cat_total}, expected {expected['total']}"
            derived_total_postings += cat_total

            r_skill = next((s for s in profile["all_skills"] if s["canonical"] == "R"), None)
            assert r_skill is not None, f"R skill not found in {cat_id} profile"
            assert r_skill["count"] == expected["r_count"], f"Mismatch in R count for {cat_id}: got {r_skill['count']}, expected {expected['r_count']}"

            # Calculate and validate prevalence using actual category denominator
            calculated_prev = r_skill["count"] / cat_total
            calculated_prev_pct = round(calculated_prev * 100, 1)
            assert math.isclose(r_skill["prevalence"], calculated_prev, rel_tol=1e-4), (
                f"Mismatch in R raw prevalence for {cat_id}: got {r_skill['prevalence']}, calculated {calculated_prev}"
            )
            assert math.isclose(r_skill["prevalence_pct"], calculated_prev_pct, abs_tol=0.1), (
                f"Mismatch in R prevalence_pct for {cat_id}: got {r_skill['prevalence_pct']}, calculated {calculated_prev_pct}"
            )
            assert math.isclose(r_skill["prevalence_pct"], expected["r_prev_pct"], abs_tol=0.1), (
                f"Mismatch in R expected prevalence_pct for {cat_id}: got {r_skill['prevalence_pct']}, expected {expected['r_prev_pct']}"
            )
            derived_total_r += r_skill["count"]

        assert summary["kpis"]["total_postings"] == 24488
        assert derived_total_postings == 24488
        assert derived_total_r == 1172

    def test_r_skill_extraction_logic(self):
        """Verifies that extraction logic recognizes genuine R mentions and prevents false positives."""
        from src.analytics import extract_skills_from_posting, SkillVocabulary

        vocab = SkillVocabulary.load_from_file(app.VOCAB_PATH)

        # True positives
        tp_posting = {"title": "Data Scientist", "skills": [], "description": "Requires strong skills in Python and R for statistical modeling."}
        extracted_tp = extract_skills_from_posting(tp_posting, vocab)
        assert "R" in extracted_tp
        assert "Python" in extracted_tp

        # False positives prevented (e.g. R&D)
        fp_posting = {"title": "Analyst", "skills": [], "description": "Works within the global R&D department on financial metrics."}
        extracted_fp = extract_skills_from_posting(fp_posting, vocab)
        assert "R" not in extracted_fp

    @pytest.mark.production_data
    def test_r_skill_extraction_and_market_demand_in_dashboard(self):
        """Verifies R has substantial detected market demand across Data Science and Data Analytics on production dataset."""
        postings = app.load_postings_dataset()
        r_postings = sum(1 for p in postings if "R" in p.get("skills", set()))
        assert r_postings > 1000, f"Expected >1000 R postings across corpus, got {r_postings}"

        # In Data Science
        ds_postings = [p for p in postings if p.get("category") == "data_science"]
        ds_r = sum(1 for p in ds_postings if "R" in p.get("skills", set()))
        assert ds_r >= 300, f"Expected >=300 R postings in Data Science, got {ds_r}"
        ds_prev = ds_r / len(ds_postings)
        assert ds_prev >= 0.12, f"Expected >=12% R prevalence in Data Science, got {ds_prev:.1%}"

        # In Data Analytics
        da_postings = [p for p in postings if p.get("category") == "data_analytics"]
        da_r = sum(1 for p in da_postings if "R" in p.get("skills", set()))
        assert da_r >= 250, f"Expected >=250 R postings in Data Analytics, got {da_r}"
        da_prev = da_r / len(da_postings)
        assert da_prev >= 0.08, f"Expected >=8% R prevalence in Data Analytics, got {da_prev:.1%}"

    def test_chart_expansion_dialog_triggers(self):
        """Clicking expand buttons on charts opens modal dialogs without exceptions."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        expand_btns = [b for b in at.button if "Expand" in b.label]
        assert len(expand_btns) >= 1

        expand_btns[0].click().run(timeout=15)
        assert len(at.exception) == 0
    def test_job_family_composition_responds_to_skill_family_filter(self):
        """Verifies Job-Family Composition chart data changes when Technical Skill Family changes."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        # Retrieve initial chart spec for Job-Family Composition
        comp_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            xaxis_title = str(spec.get("layout", {}).get("xaxis", {}).get("title", {}).get("text", ""))
            if "Matching Postings" in xaxis_title or "Observed Postings" in xaxis_title:
                comp_chart = el
                break

        assert comp_chart is not None
        initial_counts = json.loads(comp_chart.proto.spec)["data"][0]["x"]

        # Select 'BI & visualization' skill family
        fam_sb = next(sb for sb in at.selectbox if "Skill Family" in sb.label)
        fam_sb.select("BI & visualization").run(timeout=15)
        assert len(at.exception) == 0

        # Retrieve updated chart spec
        updated_comp_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            xaxis_title = str(spec.get("layout", {}).get("xaxis", {}).get("title", {}).get("text", ""))
            if "Matching Postings" in xaxis_title or "Observed Postings" in xaxis_title:
                updated_comp_chart = el
                break

        assert updated_comp_chart is not None
        updated_counts = json.loads(updated_comp_chart.proto.spec)["data"][0]["x"]

        # Category counts must be different when filtered by BI & visualization
        assert updated_counts != initial_counts

    def test_multi_country_austria_and_spain_selection(self):
        """Verifies selecting Austria (N < 300) and Spain (N >= 300) together displays both with small-sample warning."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("AT").select("ES").run(timeout=15)
        assert len(at.exception) == 0

        metrics_dict = {m.label: m.value for m in at.metric}
        assert metrics_dict["Countries with Postings"] == "2 / 27"

        # Check that stacked composition chart contains Austria and Spain
        stacked_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            barmode = spec.get("layout", {}).get("barmode")
            if barmode == "stack":
                stacked_chart = el
                break

        assert stacked_chart is not None
        stacked_spec = json.loads(stacked_chart.proto.spec)
        y_labels = stacked_spec["data"][0]["y"]
        assert any("Austria" in y or "AT" in y for y in y_labels)
        assert any("Spain" in y or "ES" in y for y in y_labels)
        # Austria has N < 300, so must be marked with warning indicator
        assert any("⚠️" in y and "AT" in y for y in y_labels)

    def test_scatter_plot_top10_default_and_dense_view_toggle(self):
        """Verifies scatter plot shows top 10 qualified by default and dense view when toggled."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        # Select occupational role via local selector
        role_sb = next(sb for sb in at.selectbox if "Occupational Role (for Scatter Plot)" in sb.label)
        role_sb.select("data_science").run(timeout=15)
        assert len(at.exception) == 0

        # Find scatter plot
        scatter_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            yaxis_title = str(spec.get("layout", {}).get("yaxis", {}).get("title", {}).get("text", ""))
            if "Distinctiveness Lift" in yaxis_title and any(t.get("mode") == "markers+text" for t in spec.get("data", [])):
                scatter_chart = el
                break

        assert scatter_chart is not None
        scatter_spec = json.loads(scatter_chart.proto.spec)
        total_points_default = sum(len(t.get("x", [])) for t in scatter_spec.get("data", []))
        # Top 10 view by default
        assert total_points_default <= 10

        # Toggle dense view checkbox ("Include all detected skills (including unqualified skills)")
        dense_cb = next(cb for cb in at.checkbox if "detected skills" in cb.label or "unqualified" in cb.label)
        dense_cb.check().run(timeout=15)
        assert len(at.exception) == 0

        # Re-inspect scatter plot in dense view
        scatter_chart_dense = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            yaxis_title = str(spec.get("layout", {}).get("yaxis", {}).get("title", {}).get("text", ""))
            if "Distinctiveness Lift" in yaxis_title and any(t.get("mode") == "markers+text" for t in spec.get("data", [])):
                scatter_chart_dense = el
                break

        assert scatter_chart_dense is not None
        scatter_spec_dense = json.loads(scatter_chart_dense.proto.spec)
        total_points_dense = sum(len(t.get("x", [])) for t in scatter_spec_dense.get("data", []))
        assert total_points_dense > total_points_default

    def test_corpus_benchmark_uses_indigo_visual_encoding(self):
        """Verifies Corpus Baseline Benchmark uses distinct indigo color and not neutral gray."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        bench_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            xaxis_title = str(spec.get("layout", {}).get("xaxis", {}).get("title", {}).get("text", ""))
            if "Corpus" in xaxis_title and "Prevalence" in xaxis_title:
                bench_chart = el
                break

        assert bench_chart is not None
        spec = json.loads(bench_chart.proto.spec)
        bar_color = spec["data"][0]["marker"]["color"]
        # Must be distinct Indigo (#6366f1) and not gray (#64748b)
        assert bar_color == "#6366f1"

    def test_complete_skill_demand_table_transparent_status(self):
        """Verifies table displays detailed qualification status explaining low N, low P, or parity."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        table_df = at.dataframe[0].value
        assert len(table_df) > 0
        statuses = set(table_df["Qualification Status"].tolist())
        # Default all-categories view should explain Baseline Parity
        assert any("Baseline Parity" in s or "Qualified" in s or "Sub-threshold" in s for s in statuses)

    def test_local_role_selector_independence(self):
        """Verifies changing local role selector in Section 2 does NOT alter global filter or other charts."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        # Global category is All Categories
        cat_sb = next(sb for sb in at.selectbox if "Job Family / Category:" in sb.label)
        assert cat_sb.value == "All Categories"

        # Change local role selector in Most Distinctive Skills
        dist_sb = next(sb for sb in at.selectbox if "Occupational Role (for Distinctive Ranking):" in sb.label)
        dist_sb.select("data_science").run(timeout=15)
        assert len(at.exception) == 0

        # Global category MUST remain All Categories
        updated_cat_sb = next(sb for sb in at.selectbox if "Job Family / Category:" in sb.label)
        assert updated_cat_sb.value == "All Categories"

        # Job-Family Composition must continue showing all 5 data occupations (not just data_science)
        comp_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            xaxis_title = str(spec.get("layout", {}).get("xaxis", {}).get("title", {}).get("text", ""))
            if "Matching Postings" in xaxis_title or "Observed Postings" in xaxis_title:
                comp_chart = el
                break
        assert comp_chart is not None
        comp_spec = json.loads(comp_chart.proto.spec)
        assert len(comp_spec["data"][0]["y"]) == 5

    def test_scatter_plot_unselected_default_guidance(self):
        """Verifies default unselected state guides user about Lift = 1.00 baseline parity."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        # Find scatter chart annotation
        charts = at.get("plotly_chart")
        annotations_text = []
        for ch in charts:
            spec = json.loads(ch.proto.spec)
            for a in spec.get("layout", {}).get("annotations", []):
                annotations_text.append(a.get("text", ""))

        assert any("Lift = 1.00 by definition" in t for t in annotations_text)

    @pytest.mark.production_data
    def test_cross_country_composition_czechia_denmark_single_category_filter(self):
        """Verifies Czechia and Denmark with Data Analytics selected exhibits valid shares summing to ~100% on production data."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        # Select Czechia and Denmark
        country_ms = next(ms for ms in at.multiselect if "Country" in ms.label)
        country_ms.select("CZ").select("DK").run(timeout=15)
        assert len(at.exception) == 0

        # Select Data Analytics globally
        cat_sb = next(sb for sb in at.selectbox if "Job Family / Category:" in sb.label)
        cat_sb.select("data_analytics").run(timeout=15)
        assert len(at.exception) == 0

        # Retrieve Cross-Country Composition stacked bar chart
        stacked_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            if spec.get("layout", {}).get("barmode") == "stack":
                stacked_chart = el
                break

        assert stacked_chart is not None, "Stacked country composition chart not found"
        stacked_spec = json.loads(stacked_chart.proto.spec)
        traces = stacked_spec.get("data", [])

        # Must display all 5 categories as traces
        assert len(traces) == 5
        trace_names = [t.get("name") for t in traces]
        assert set(trace_names) == {
            "Data Engineering",
            "Data Analytics",
            "Data Science",
            "AI Engineering",
            "ML/AI",
        }

        # Check each country's occupational shares
        y_labels = traces[0]["y"]
        assert any("Czechia" in y and "CZ" in y for y in y_labels)
        assert any("Denmark" in y and "DK" in y for y in y_labels)
        # Czechia has N < 300, must be marked with warning badge
        assert any("⚠️" in y and "CZ" in y for y in y_labels)

        for country_idx, y_label in enumerate(y_labels):
            shares = [t["x"][country_idx] for t in traces]
            # No share can exceed 100%
            assert all(0.0 <= s <= 100.0 for s in shares), f"Share exceeded 100% in {y_label}: {shares}"
            # Sum of shares must equal ~100.0% within rounding
            assert 99.5 <= sum(shares) <= 100.5, f"Shares do not sum to 100% in {y_label}: {shares}"
            # Specific regression checks: Denmark DE is ~56.5% (not 654%), Czechia DE is ~31.3% (not 154%)
            if "Denmark" in y_label:
                de_share = next(t["x"][country_idx] for t in traces if t["name"] == "Data Engineering")
                assert 50.0 <= de_share <= 65.0, f"Expected DK DE ~55-65%, got {de_share}"
            if "Czechia" in y_label:
                de_share = next(t["x"][country_idx] for t in traces if t["name"] == "Data Engineering")
                assert 30.0 <= de_share <= 35.0, f"Expected CZ DE ~31-34%, got {de_share}"

        # In-bar labels must be horizontal (textangle == 0) and constrained inside
        for t in traces:
            assert t.get("textangle") == 0
            assert t.get("constraintext") == "inside"

    @pytest.mark.production_data
    def test_cross_country_composition_unfiltered_view_all_shares_sum_to_100(self):
        """Verifies unfiltered EU-wide view includes N>=300 countries with valid 100% shares and horizontal text on production data."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        stacked_chart = None
        for el in at.get("plotly_chart"):
            spec = json.loads(el.proto.spec)
            if spec.get("layout", {}).get("barmode") == "stack":
                stacked_chart = el
                break

        assert stacked_chart is not None
        stacked_spec = json.loads(stacked_chart.proto.spec)
        traces = stacked_spec.get("data", [])
        assert len(traces) == 5

        y_labels = traces[0]["y"]
        # Exactly 11 EU member states have N >= 300 in refreshed dataset (Romania is 277 < 300)
        assert len(y_labels) == 11

        # Check every country's shares sum to 100%
        for country_idx, y_label in enumerate(y_labels):
            shares = [t["x"][country_idx] for t in traces]
            assert all(0.0 <= s <= 100.0 for s in shares), f"Share exceeded 100% in {y_label}: {shares}"
            assert 99.5 <= sum(shares) <= 100.5, f"Shares do not sum to 100% in {y_label}: {shares}"

        # Layout must specify uniformtext hide to prevent rotated/sideways labels
        assert stacked_spec.get("layout", {}).get("uniformtext", {}).get("mode") == "hide"

    def test_lift_formula_rendering_and_interpretation(self):
        """Verifies explanatory text renders balanced Lift formula and explains over/under-representation."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)

        info_texts = [inf.value for inf in at.info]
        assert any("Interpreting Prevalence vs. Distinctiveness" in t for t in info_texts)
        distinctiveness_info = next(t for t in info_texts if "Interpreting Prevalence vs. Distinctiveness" in t)

        # Check formula with balanced delimiters
        assert "P(\\text{skill} \\mid \\text{selection}) / P(\\text{skill} \\mid \\text{corpus})" in distinctiveness_info
        # Check explanatory interpretations
        assert "Lift > 1.00" in distinctiveness_info
        assert "over-representation" in distinctiveness_info
        assert "Lift = 1.00" in distinctiveness_info
        assert "baseline parity" in distinctiveness_info
        assert "Lift < 1.00" in distinctiveness_info
        assert "under-representation" in distinctiveness_info

    def test_data_loading_modes_and_source_identification(self, monkeypatch):
        """Verifies that load_postings_dataset distinguishes production vs test fixture vs error when missing."""
        # 1. Test fixture mode
        monkeypatch.setenv("EU_DATA_MODE", "test_fixture")
        app.load_postings_dataset.clear()
        fixture_postings = app.load_postings_dataset()
        assert len(fixture_postings) > 0
        assert app.get_active_data_source() == app.DATA_SOURCE_TEST_FIXTURE

        # 2. Production mode when files missing raises FileNotFoundError (does NOT fall back to synthetic)
        monkeypatch.setenv("EU_DATA_MODE", "production")
        monkeypatch.setattr(app, "POSTINGS_CACHE_PATH", Path("non_existent_cache.json"))
        monkeypatch.setattr(app, "RAW_POSTINGS_PATH", Path("non_existent_raw.json"))
        app.load_postings_dataset.clear()
        with pytest.raises(FileNotFoundError, match="Requested production data mode but production dataset is missing"):
            app.load_postings_dataset()


class TestDashboardBarChartLabelPolicy:
    """Comprehensive tests verifying dashboard-wide bar chart label orientation, readability, and overflow prevention."""

    def test_horizontal_bar_helper_trace_properties(self):
        """Verifies create_horizontal_bar_trace enforces horizontal, outside labels with cliponaxis protection."""
        trace = app.create_horizontal_bar_trace(
            x=[10, 20],
            y=["A", "B"],
            text=["10% (100 jobs)", "20% (200 jobs)"],
            color="#2563eb",
            hovertemplate="<b>%{y}</b>: %{x}%<extra></extra>",
        )
        assert trace.orientation == "h"
        assert trace.textposition == "outside"
        assert trace.textangle == 0
        assert trace.cliponaxis is False

    def test_standard_bar_layout_properties(self):
        """Verifies apply_standard_bar_layout configures generous headroom and uniformtext hiding."""
        fig = go.Figure()
        fig = app.apply_standard_bar_layout(
            fig,
            height=380,
            xaxis_title="Test Title",
            max_val=100.0,
            headroom_factor=1.35,
            min_range=10.0,
            margin_right=45,
        )
        layout = fig.layout
        assert layout.height == 380
        assert layout.xaxis.title.text == "Test Title"
        assert layout.xaxis.range[1] == 135.0  # 100 * 1.35
        assert layout.margin.r == 45
        assert layout.uniformtext.mode == "hide"
        assert layout.uniformtext.minsize == 9

    def test_job_family_composition_bar_label_policy(self):
        """Verifies Job-Family Composition uses horizontal outside labels, headroom, and hovertemplate."""
        cat_counts = Counter({
            "data_engineering": 500,
            "data_analytics": 300,
            "data_science": 200,
            "ai_engineering": 100,
            "ml_ai": 50,
        })
        fig = app.build_category_composition_bar(cat_counts, total_postings=1150)
        spec = fig.to_dict()
        trace = spec["data"][0]

        assert trace["orientation"] == "h"
        assert trace["textposition"] == "outside"
        assert trace["textangle"] == 0
        assert trace["cliponaxis"] is False
        assert spec["layout"]["xaxis"]["range"][1] >= 500 * 1.35
        assert spec["layout"]["uniformtext"]["mode"] == "hide"
        assert "Postings:" in trace["hovertemplate"]
        assert "Share:" in trace["hovertemplate"]

    def test_top_in_demand_bar_label_policy(self):
        """Verifies Top In-Demand Skills bar chart uses horizontal outside labels with headroom."""
        sample_stats = [
            {"canonical": "SQL", "prevalence_pct": 55.0, "count": 12000},
            {"canonical": "Python", "prevalence_pct": 50.0, "count": 11000},
        ]
        fig = app.build_top_in_demand_bar(sample_stats)
        spec = fig.to_dict()
        trace = spec["data"][0]

        assert trace["orientation"] == "h"
        assert trace["textposition"] == "outside"
        assert trace["textangle"] == 0
        assert trace["cliponaxis"] is False
        assert spec["layout"]["xaxis"]["range"][1] >= 55.0 * 1.35
        assert spec["layout"]["uniformtext"]["mode"] == "hide"
        assert "Prevalence:" in trace["hovertemplate"]

    def test_most_distinctive_bar_label_policy(self):
        """Verifies Most Distinctive Skills bar chart uses horizontal outside labels with headroom."""
        sample_stats = [
            {"canonical": "PyTorch", "lift": 3.42, "prevalence_pct": 8.5, "count": 1234, "is_eligible_distinctive": True},
            {"canonical": "TensorFlow", "lift": 2.15, "prevalence_pct": 5.2, "count": 800, "is_eligible_distinctive": True},
        ]
        fig = app.build_most_distinctive_bar(sample_stats, is_unselected_category=False)
        spec = fig.to_dict()
        trace = spec["data"][0]

        assert trace["orientation"] == "h"
        assert trace["textposition"] == "outside"
        assert trace["textangle"] == 0
        assert trace["cliponaxis"] is False
        assert spec["layout"]["xaxis"]["range"][1] >= 3.42 * 1.35
        assert spec["layout"]["uniformtext"]["mode"] == "hide"
        assert "Distinctiveness Lift:" in trace["hovertemplate"]

    def test_corpus_benchmark_bar_label_policy(self):
        """Verifies Corpus Baseline Benchmark uses deep indigo, horizontal outside labels, and headroom."""
        sample_skills = [
            {"skill": "Python", "prevalence_pct": 55.2, "count": 14013},
            {"skill": "SQL", "prevalence_pct": 48.6, "count": 12341},
        ]
        fig = app.build_corpus_benchmark_bar(sample_skills)
        spec = fig.to_dict()
        trace = spec["data"][0]

        assert trace["orientation"] == "h"
        assert trace["textposition"] == "outside"
        assert trace["textangle"] == 0
        assert trace["cliponaxis"] is False
        assert trace["marker"]["color"] == "#6366f1"
        assert spec["layout"]["xaxis"]["range"][1] >= 55.2 * 1.35
        assert spec["layout"]["uniformtext"]["mode"] == "hide"
        assert "Corpus Baseline Prevalence:" in trace["hovertemplate"]

    def test_country_volume_comparison_bar_label_policy(self):
        """Verifies Country Posting Volumes uses horizontal outside labels and headroom."""
        records = [
            {"country_name": "Germany", "iso_code": "DE", "total_postings": 5241, "is_subthreshold": False},
            {"country_name": "Estonia", "iso_code": "EE", "total_postings": 150, "is_subthreshold": True},
        ]
        fig = app.build_country_volume_comparison_bar(records)
        spec = fig.to_dict()
        trace = spec["data"][0]

        assert trace["orientation"] == "h"
        assert trace["textposition"] == "outside"
        assert trace["textangle"] == 0
        assert trace["cliponaxis"] is False
        assert spec["layout"]["xaxis"]["range"][1] >= 5241 * 1.35
        assert spec["layout"]["uniformtext"]["mode"] == "hide"
        assert "Observed Postings:" in trace["hovertemplate"]

    def test_cross_country_composition_stacked_bar_label_policy(self):
        """Verifies 100% stacked bar chart uses inside horizontal text, omits <8% slices, and retains hover exactness."""
        records = [
            {
                "country_name": "Denmark",
                "iso_code": "DK",
                "total_postings": 530,
                "is_subthreshold": False,
                "shares": {
                    "data_engineering": 61.7,
                    "data_analytics": 9.4,
                    "data_science": 8.7,
                    "ai_engineering": 12.8,
                    "ml_ai": 7.4,  # Under 8% threshold: label must be omitted
                },
            }
        ]
        fig = app.build_cross_country_composition_stacked_bar(records)
        spec = fig.to_dict()
        assert spec["layout"]["barmode"] == "stack"
        assert spec["layout"]["uniformtext"]["mode"] == "hide"

        traces = spec["data"]
        assert len(traces) == 5
        for t in traces:
            assert t["orientation"] == "h"
            assert t["textposition"] == "inside"
            assert t["textangle"] == 0
            assert t["constraintext"] == "inside"
            assert "%{x:.1f}%" in t["hovertemplate"]

        # ML/AI is 7.4% (< 8.0%), so its in-bar text must be omitted ("")
        ml_trace = next(t for t in traces if t["name"] == "ML/AI")
        assert ml_trace["text"] == [""]

        # Data Engineering is 61.7% (>= 8.0%), so its in-bar text must be shown ("62%")
        de_trace = next(t for t in traces if t["name"] == "Data Engineering")
        assert de_trace["text"] == ["62%"]

    def test_app_integration_all_bar_traces_adhere_to_policy(self):
        """Integration test on live dashboard: verifies NO bar trace has vertical rotation across the entire app."""
        app.load_analytics_summary.clear()
        at = AppTest.from_file(APP_FILE).run(timeout=15)
        assert len(at.exception) == 0

        charts = at.get("plotly_chart")
        bar_chart_count = 0

        for ch in charts:
            spec = json.loads(ch.proto.spec)
            data = spec.get("data", [])
            bar_traces = [t for t in data if t.get("type") == "bar"]
            if not bar_traces:
                continue

            bar_chart_count += 1
            layout = spec.get("layout", {})
            barmode = layout.get("barmode")

            for t in bar_traces:
                # Rule 1: No numeric labels configured for vertical rotation anywhere
                assert t.get("textangle") == 0, f"Bar trace in chart {spec.get('layout', {}).get('title', {})} has rotated text!"

                # Rule 2: Single-series horizontal bars use outside placement with cliponaxis=False
                if barmode != "stack":
                    assert t.get("textposition") == "outside"
                    assert t.get("cliponaxis") is False
                else:
                    # Rule 3: 100% stacked bars use inside placement with constraintext=inside
                    assert t.get("textposition") == "inside"
                    assert t.get("constraintext") == "inside"

                # Rule 4: Hover template is always present and informative
                assert t.get("hovertemplate") is not None

            # Rule 5: Uniformtext hide protection is enabled on layout
            assert layout.get("uniformtext", {}).get("mode") == "hide"

        # Ensure all available bar charts were found and verified
        if app.get_active_data_source() == app.DATA_SOURCE_PRODUCTION:
            assert bar_chart_count >= 5
        else:
            # Under test fixture without N >= 300 countries, 4 bar charts have active bar traces,
            # and the 5th (cross-country composition) verifies the subthreshold empty annotation.
            assert bar_chart_count >= 4
            empty_composition_chart = next(
                (
                    ch for ch in charts
                    if any("No countries with matching postings" in a.get("text", "")
                           for a in json.loads(ch.proto.spec).get("layout", {}).get("annotations", []))
                ),
                None
            )
            assert empty_composition_chart is not None
