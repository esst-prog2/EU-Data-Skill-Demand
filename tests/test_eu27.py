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
import time

import pytest
import requests

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


class MockResponse:
    """Helper mock response for get_jobs network retry tests."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict | None = None,
        headers: dict | None = None,
    ):
        self.status_code = status_code
        self._json_data = json_data or {"data": [], "meta": {"total": 0}}
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            req = requests.PreparedRequest()
            req.url = eu27.BASE_URL
            resp = requests.Response()
            resp.status_code = self.status_code
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Error",
                request=req,
                response=resp,
            )


class TestGetJobsRetryBehavior:
    """Verifies bounded retries, exponential backoff, and error discrimination in get_jobs()."""

    def test_transient_connection_error_retries_and_succeeds(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise requests.exceptions.ConnectionError("Connection aborted")
            return MockResponse(
                200,
                json_data={
                    "data": [{"id": "job-1", "title": "Data Scientist"}],
                    "meta": {"total": 1},
                },
            )

        monkeypatch.setattr(eu27.session, "get", mock_get)

        jobs = eu27.get_jobs("DE", "data_science", max_retries=3, initial_backoff=1.0)
        assert len(jobs) == 1
        assert jobs[0]["id"] == "job-1"
        assert jobs[0]["_collection_country"] == "DE"
        assert jobs[0]["_collection_category"] == "data_science"
        assert calls == 2
        # First retry sleeps initial_backoff * (2 ** 0) = 1.0
        assert 1.0 in sleep_calls

    def test_transient_timeout_retries_and_succeeds(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise requests.exceptions.Timeout("Read timeout")
            return MockResponse(
                200,
                json_data={
                    "data": [{"id": "job-2", "title": "Data Engineer"}],
                    "meta": {"total": 1},
                },
            )

        monkeypatch.setattr(eu27.session, "get", mock_get)

        jobs = eu27.get_jobs("FR", "data_engineering", max_retries=3, initial_backoff=0.5)
        assert len(jobs) == 1
        assert jobs[0]["id"] == "job-2"
        assert calls == 2
        assert 0.5 in sleep_calls

    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    def test_transient_5xx_server_errors_retry_and_succeed(self, monkeypatch, status_code):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return MockResponse(status_code)
            return MockResponse(
                200,
                json_data={
                    "data": [{"id": f"job-{status_code}"}],
                    "meta": {"total": 1},
                },
            )

        monkeypatch.setattr(eu27.session, "get", mock_get)

        jobs = eu27.get_jobs("NL", "ml_ai", max_retries=3, initial_backoff=0.25)
        assert len(jobs) == 1
        assert jobs[0]["id"] == f"job-{status_code}"
        assert calls == 2
        assert 0.25 in sleep_calls

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404])
    def test_permanent_4xx_raises_immediately_without_retry(self, monkeypatch, status_code):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            return MockResponse(status_code)

        monkeypatch.setattr(eu27.session, "get", mock_get)

        with pytest.raises(requests.exceptions.HTTPError):
            eu27.get_jobs("ES", "data_analytics", max_retries=3)

        assert calls == 1
        assert len(sleep_calls) == 0

    def test_exhausted_retries_on_transient_timeout_raises(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise requests.exceptions.Timeout("Persistent timeout")

        monkeypatch.setattr(eu27.session, "get", mock_get)

        with pytest.raises(requests.exceptions.Timeout):
            eu27.get_jobs("IT", "ai_engineering", max_retries=3, initial_backoff=1.0)

        assert calls == 3
        # Should have slept twice: 1.0 * 2^0 = 1.0, 1.0 * 2^1 = 2.0
        assert sleep_calls == [1.0, 2.0]

    def test_exhausted_retries_on_5xx_raises_http_error(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            return MockResponse(500)

        monkeypatch.setattr(eu27.session, "get", mock_get)

        with pytest.raises(requests.exceptions.HTTPError):
            eu27.get_jobs("SE", "data_science", max_retries=3, initial_backoff=0.5)

        assert calls == 3
        # Should have slept twice: 0.5 * 2^0 = 0.5, 0.5 * 2^1 = 1.0
        assert sleep_calls == [0.5, 1.0]

    def test_rate_limit_429_respects_retry_after(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return MockResponse(429, headers={"Retry-After": "4.5"})
            return MockResponse(
                200,
                json_data={
                    "data": [{"id": "job-429"}],
                    "meta": {"total": 1},
                },
            )

        monkeypatch.setattr(eu27.session, "get", mock_get)

        jobs = eu27.get_jobs("PL", "data_analytics", max_retries=3)
        assert len(jobs) == 1
        assert calls == 2
        assert 4.5 in sleep_calls

    def test_rate_limit_429_exhausted_raises_http_error(self, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(time, "sleep", sleep_calls.append)

        calls = 0

        def mock_get(*args, **kwargs):
            nonlocal calls
            calls += 1
            return MockResponse(429, headers={"Retry-After": "1.0"})

        monkeypatch.setattr(eu27.session, "get", mock_get)

        with pytest.raises(requests.exceptions.HTTPError):
            eu27.get_jobs("IE", "data_engineering", max_retries=3)

        assert calls == 3
