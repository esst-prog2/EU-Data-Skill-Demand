"""
tests/test_eu27.py

Focused tests for eu27.py stable job key extraction and collection error handling:
- get_job_key candidate priority (public_slug -> slug -> id -> external_id)
- Empty and whitespace-only fall-through
- Stripping of leading/trailing whitespace
- Non-string candidate values ignored (no stringification)
- Return None when all candidates are unusable
- Collection aborts with descriptive RuntimeError on unidentifiable posting
"""

from __future__ import annotations

from pathlib import Path

import pytest

import eu27
from eu27 import get_job_key


class TestGetJobKeyPriority:
    """Verifies that candidate fields are evaluated in the specified priority order."""

    def test_public_slug_takes_precedence_over_all_other_fields(self):
        job = {
            "public_slug": "pub-slug-1",
            "slug": "slug-1",
            "id": "id-1",
            "external_id": "ext-1",
        }
        assert get_job_key(job) == "pub-slug-1"

    def test_slug_takes_precedence_when_public_slug_missing(self):
        job = {
            "slug": "slug-2",
            "id": "id-2",
            "external_id": "ext-2",
        }
        assert get_job_key(job) == "slug-2"

    def test_id_takes_precedence_when_slugs_missing(self):
        job = {
            "id": "id-3",
            "external_id": "ext-3",
        }
        assert get_job_key(job) == "id-3"

    def test_external_id_used_when_higher_priority_fields_missing(self):
        job = {
            "external_id": "ext-4",
        }
        assert get_job_key(job) == "ext-4"


class TestGetJobKeyWhitespaceAndFallthrough:
    """Verifies that empty and whitespace-only candidates fall through to the next candidate."""

    def test_whitespace_and_empty_fallthrough_to_external_id(self):
        job = {
            "public_slug": "",
            "slug": "   ",
            "id": "\t\n",
            "external_id": "valid-ext-id",
        }
        assert get_job_key(job) == "valid-ext-id"

    def test_strips_leading_and_trailing_whitespace(self):
        job = {"public_slug": "   clean-me-slug   "}
        assert get_job_key(job) == "clean-me-slug"

    def test_empty_public_slug_falls_through_to_slug(self):
        job = {
            "public_slug": "",
            "slug": "   fallback-slug   ",
        }
        assert get_job_key(job) == "fallback-slug"


class TestGetJobKeyNonStringIgnored:
    """Verifies that non-string values are ignored and never stringified."""

    @pytest.mark.parametrize(
        "non_string_val",
        [
            12345,
            99.9,
            True,
            False,
            ["list-val"],
            {"dict": "val"},
        ],
    )
    def test_non_string_candidates_do_not_stringify_and_fall_through(self, non_string_val):
        job = {
            "public_slug": non_string_val,
            "slug": non_string_val,
            "id": non_string_val,
            "external_id": "valid-fallback",
        }
        assert get_job_key(job) == "valid-fallback"

    def test_integer_id_alone_returns_none(self):
        # Must not stringify 12345 to "12345"
        job = {"id": 12345}
        assert get_job_key(job) is None


class TestGetJobKeyReturnsNone:
    """Verifies that None is returned when no candidate is usable."""

    def test_all_none_returns_none(self):
        job = {"public_slug": None, "slug": None, "id": None, "external_id": None}
        assert get_job_key(job) is None

    def test_all_empty_or_whitespace_returns_none(self):
        job = {"public_slug": "", "slug": "  ", "id": "\t", "external_id": "\n"}
        assert get_job_key(job) is None

    def test_empty_dict_returns_none(self):
        assert get_job_key({}) is None

    @pytest.mark.parametrize("invalid_arg", [None, "not-a-dict", [1, 2], 42])
    def test_non_dict_input_returns_none(self, invalid_arg):
        assert get_job_key(invalid_arg) is None


class TestCollectionAbortsOnMissingID:
    """Verifies that the collection loop raises RuntimeError on an unidentifiable posting."""

    def test_collection_loop_raises_runtime_error_and_aborts_before_save(
        self, monkeypatch, tmp_path: Path
    ):
        mock_jobs = [
            {
                "title": "Unidentifiable Senior Data Engineer",
                "description": "Valid job content but missing all slug and id fields",
            }
        ]

        # Intercept network call get_jobs
        monkeypatch.setattr(eu27, "get_jobs", lambda country_code, category: mock_jobs)

        # Restrict loop scope to 1 country and 1 category for rapid, isolated execution
        monkeypatch.setattr(eu27, "EU_COUNTRIES", {"DE": "Germany"})
        monkeypatch.setattr(eu27, "CATEGORIES", ["data_engineering"])

        # Direct outputs to temporary paths to verify they are never written
        temp_jobs_out = tmp_path / "raw.json"
        temp_meta_out = tmp_path / "meta.json"
        monkeypatch.setattr(eu27, "JOBS_OUTPUT", temp_jobs_out)
        monkeypatch.setattr(eu27, "METADATA_OUTPUT", temp_meta_out)

        with pytest.raises(RuntimeError) as exc_info:
            eu27.main()

        err_msg = str(exc_info.value)
        assert "Collection failed: posting without stable ID encountered" in err_msg
        assert "DE/data_engineering" in err_msg
        assert "Unidentifiable Senior Data Engineer" in err_msg

        # Crucially: verify no files were written
        assert not temp_jobs_out.exists()
        assert not temp_meta_out.exists()


class TestTargetCategories:
    """Verifies that eu27.py targets the canonical occupational categories."""

    def test_categories_match_canonical_occupational_categories(self):
        from src.analytics import OCCUPATIONAL_CATEGORIES

        assert eu27.CATEGORIES == list(OCCUPATIONAL_CATEGORIES.keys())
        assert len(eu27.CATEGORIES) == 5
        assert eu27.CATEGORIES[0] == "data_analytics"


class TestEUCountryMapping:
    """Verifies that eu27.py uses the canonical EU-27 country mapping."""

    def test_eu_countries_matches_canonical_eu27_countries(self):
        from src.analytics import EU27_COUNTRIES

        assert eu27.EU_COUNTRIES == EU27_COUNTRIES
        assert len(eu27.EU_COUNTRIES) == 27
        assert eu27.EU_COUNTRIES["CZ"] == "Czechia"
