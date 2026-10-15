"""
tests/test_preprocess.py

Focused unit and regression tests for preprocessing provenance validation:
- Missing _collection_category (omitted, None, empty string)
- Invalid _collection_category (unknown strings, non-canonical categories)
- Missing _collection_country (omitted, None, empty string)
- Invalid _collection_country (non-EU codes, unknown strings)
- Diagnostic error reporting without dumping posting descriptions
- Synthetic end-to-end preprocess() behavior
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.preprocess import (
    CATEGORY_NAMES,
    EU27_COUNTRY_NAMES,
    preprocess,
    validate_posting_provenance,
)


class TestValidatePostingProvenance:
    """Tests for individual posting category and country provenance validation."""

    def test_category_names_matches_canonical_occupational_categories(self):
        from src.analytics import OCCUPATIONAL_CATEGORIES

        assert CATEGORY_NAMES == OCCUPATIONAL_CATEGORIES

    def test_valid_posting_returns_category_and_country(self):
        posting = {
            "id": "job-101",
            "title": "Data Engineer",
            "_collection_category": "data_engineering",
            "_collection_country": "DE",
        }
        cat, country = validate_posting_provenance(posting, index=0)
        assert cat == "data_engineering"
        assert country == "DE"

    @pytest.mark.parametrize(
        "cat_val",
        [None, ""],
    )
    def test_missing_category_value_raises_value_error(self, cat_val):
        posting = {
            "id": "job-102",
            "_collection_category": cat_val,
            "_collection_country": "FR",
        }
        with pytest.raises(ValueError, match="missing required '_collection_category'"):
            validate_posting_provenance(posting, index=1)

    def test_omitted_category_key_raises_value_error(self):
        posting = {
            "id": "job-103",
            "_collection_country": "ES",
        }
        with pytest.raises(ValueError, match="missing required '_collection_category'"):
            validate_posting_provenance(posting, index=2)

    @pytest.mark.parametrize(
        "invalid_cat",
        ["unknown", "software_engineering", "data_science_lead", "DATA_SCIENCE", "other"],
    )
    def test_invalid_category_raises_value_error(self, invalid_cat):
        posting = {
            "id": "job-104",
            "_collection_category": invalid_cat,
            "_collection_country": "IT",
        }
        with pytest.raises(ValueError, match="invalid '_collection_category'"):
            validate_posting_provenance(posting, index=3)

    @pytest.mark.parametrize(
        "country_val",
        [None, ""],
    )
    def test_missing_country_value_raises_value_error(self, country_val):
        posting = {
            "id": "job-105",
            "_collection_category": "data_science",
            "_collection_country": country_val,
        }
        with pytest.raises(ValueError, match="missing required '_collection_country'"):
            validate_posting_provenance(posting, index=4)

    def test_omitted_country_key_raises_value_error(self):
        posting = {
            "id": "job-106",
            "_collection_category": "ai_engineering",
        }
        with pytest.raises(ValueError, match="missing required '_collection_country'"):
            validate_posting_provenance(posting, index=5)

    @pytest.mark.parametrize(
        "invalid_country",
        ["US", "GB", "CH", "unknown", "de", "XX"],
    )
    def test_invalid_country_raises_value_error(self, invalid_country):
        posting = {
            "id": "job-107",
            "_collection_category": "ml_ai",
            "_collection_country": invalid_country,
        }
        with pytest.raises(ValueError, match="invalid '_collection_country'"):
            validate_posting_provenance(posting, index=6)

    def test_non_dict_posting_raises_value_error(self):
        with pytest.raises(ValueError, match="not a valid dictionary"):
            validate_posting_provenance("not-a-dict", index=7)

    @pytest.mark.parametrize(
        "non_string_cat",
        [
            ["data_science"],
            [],
            {"name": "data_science"},
            {},
            123,
            True,
        ],
    )
    def test_non_string_category_raises_value_error_without_type_error(self, non_string_cat):
        posting = {
            "id": "job-type-cat",
            "_collection_category": non_string_cat,
            "_collection_country": "DE",
        }
        with pytest.raises(ValueError, match="invalid '_collection_category'"):
            validate_posting_provenance(posting, index=8)

    @pytest.mark.parametrize(
        "non_string_country",
        [
            ["DE"],
            [],
            {"iso": "DE"},
            {},
            42,
            False,
        ],
    )
    def test_non_string_country_raises_value_error_without_type_error(self, non_string_country):
        posting = {
            "id": "job-type-country",
            "_collection_category": "data_science",
            "_collection_country": non_string_country,
        }
        with pytest.raises(ValueError, match="invalid '_collection_country'"):
            validate_posting_provenance(posting, index=9)

    def test_diagnostic_context_includes_id_and_omits_description(self):
        posting = {
            "id": "job-secret-999",
            "title": "Machine Learning Engineer",
            "description": "TOP_SECRET_PROPRIETARY_DESCRIPTION_TEXT " * 50,
            "_collection_country": "PL",
            # missing _collection_category
        }
        with pytest.raises(ValueError) as exc_info:
            validate_posting_provenance(posting, index=42)

        err_msg = str(exc_info.value)
        assert "Posting at index 42" in err_msg
        assert "job-secret-999" in err_msg
        assert "missing required '_collection_category'" in err_msg
        assert "TOP_SECRET_PROPRIETARY_DESCRIPTION_TEXT" not in err_msg


@pytest.fixture
def minimal_vocabulary_file(tmp_path: Path) -> Path:
    vocab = {
        "skills": [
            {
                "canonical": "Python",
                "category": "Programming languages",
                "aliases": ["python"],
                "regex": r"\bpython\b",
            }
        ]
    }
    vocab_file = tmp_path / "vocab.json"
    vocab_file.write_text(json.dumps(vocab), encoding="utf-8")
    return vocab_file


class TestPreprocessPipelineWithProvenanceValidation:
    """Tests the preprocess() function handling of synthetic inputs."""

    def test_preprocess_succeeds_on_valid_synthetic_data(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        raw_postings = [
            {
                "id": "synth-1",
                "title": "Python Developer",
                "description": "Looking for Python experience.",
                "_collection_category": "data_engineering",
                "_collection_country": "DE",
            },
            {
                "id": "synth-2",
                "title": "Data Analyst",
                "description": "SQL and dashboards.",
                "_collection_category": "data_analytics",
                "_collection_country": "FR",
            },
        ]
        raw_file = tmp_path / "raw.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")
        output_file = tmp_path / "summary.json"

        preprocess(raw_file, minimal_vocabulary_file, output_file)

        assert output_file.exists()
        with open(output_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert summary["kpis"]["total_postings"] == 2
        assert summary["kpis"]["total_countries"] == 2
        assert summary["kpis"]["total_categories"] == 2

    def test_preprocess_aborts_on_corrupted_category(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        raw_postings = [
            {
                "id": "synth-bad-cat",
                "title": "Unknown Role",
                "description": "Some text",
                "_collection_category": "unknown",  # Must not silently pass
                "_collection_country": "DE",
            }
        ]
        raw_file = tmp_path / "raw_bad_cat.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")
        output_file = tmp_path / "summary_bad.json"

        with pytest.raises(ValueError, match="invalid '_collection_category'"):
            preprocess(raw_file, minimal_vocabulary_file, output_file)

        assert not output_file.exists()

    def test_preprocess_aborts_on_missing_country(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        raw_postings = [
            {
                "id": "synth-missing-country",
                "title": "Data Scientist",
                "description": "Python, ML",
                "_collection_category": "data_science",
                # missing _collection_country
            }
        ]
        raw_file = tmp_path / "raw_missing_country.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")
        output_file = tmp_path / "summary_bad.json"

        with pytest.raises(ValueError, match="missing required '_collection_country'"):
            preprocess(raw_file, minimal_vocabulary_file, output_file)

        assert not output_file.exists()


class TestSensitivityAnalysisProvenance:
    """Verifies that compute_skill_stats_from_raw strictly enforces provenance validation."""

    def test_compute_skill_stats_aborts_on_corrupted_category(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        from analysis.sensitivity_analysis import compute_skill_stats_from_raw

        raw_postings = [
            {
                "id": "bad-cat-1",
                "title": "Data Role",
                "_collection_category": "unknown",  # Must not silently pass to 'unknown'
                "_collection_country": "DE",
            }
        ]
        raw_file = tmp_path / "raw_bad_cat.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")

        with pytest.raises(ValueError, match="invalid '_collection_category'"):
            compute_skill_stats_from_raw(raw_file, minimal_vocabulary_file)

    def test_compute_skill_stats_aborts_on_missing_category(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        from analysis.sensitivity_analysis import compute_skill_stats_from_raw

        raw_postings = [
            {
                "id": "missing-cat-1",
                "title": "Data Role",
                "_collection_country": "DE",
            }
        ]
        raw_file = tmp_path / "raw_missing_cat.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")

        with pytest.raises(ValueError, match="missing required '_collection_category'"):
            compute_skill_stats_from_raw(raw_file, minimal_vocabulary_file)

    def test_compute_skill_stats_aborts_on_missing_country(
        self, tmp_path: Path, minimal_vocabulary_file: Path
    ):
        from analysis.sensitivity_analysis import compute_skill_stats_from_raw

        raw_postings = [
            {
                "id": "missing-country-1",
                "title": "Data Role",
                "_collection_category": "data_science",
            }
        ]
        raw_file = tmp_path / "raw_missing_country.json"
        raw_file.write_text(json.dumps(raw_postings), encoding="utf-8")

        with pytest.raises(ValueError, match="missing required '_collection_country'"):
            compute_skill_stats_from_raw(raw_file, minimal_vocabulary_file)

