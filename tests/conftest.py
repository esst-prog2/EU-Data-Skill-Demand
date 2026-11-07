"""
tests/conftest.py

Test configuration and fixtures for EU Data Jobs & Skill Demand analysis.
Ensures standard CI tests run deterministically against tracked fixtures without requiring
the git-ignored 143 MB raw dataset or local processed cache.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
import streamlit as st

import app

PRODUCTION_CACHE_PATH = Path("data/processed/.postings_cache.json")
PRODUCTION_RAW_PATH = Path("data/raw/freehire_eu_raw.json")
FIXTURE_POSTINGS_PATH = Path("data/fixtures/test_postings_fixture.json")


def has_production_data() -> bool:
    """Returns True if the full production dataset (cache or raw) is present locally."""
    return PRODUCTION_CACHE_PATH.exists() or PRODUCTION_RAW_PATH.exists()


@pytest.fixture(autouse=True)
def configure_test_data_environment(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Autouse fixture that configures the appropriate data loading mode:
    - For tests marked with @pytest.mark.production_data:
      Requires production dataset. If missing, fails explicitly (never falls back).
      Configures EU_DATA_MODE='production'.
    - For all other (standard CI) tests:
      Configures EU_DATA_MODE='test_fixture' ensuring deterministic, reproducible execution.
    """
    is_production_test = request.node.get_closest_marker("production_data") is not None

    orig_mode = os.environ.get("EU_DATA_MODE")

    if is_production_test:
        if not has_production_data():
            pytest.fail(
                "Production dataset required: missing data/processed/.postings_cache.json or data/raw/freehire_eu_raw.json. "
                "This production regression test cannot run without the full 24,488-posting dataset."
            )
        os.environ["EU_DATA_MODE"] = "production"
    else:
        os.environ["EU_DATA_MODE"] = "test_fixture"

    try:
        st.cache_data.clear()
    except Exception:
        pass

    yield

    if orig_mode is None:
        os.environ.pop("EU_DATA_MODE", None)
    else:
        os.environ["EU_DATA_MODE"] = orig_mode

    try:
        st.cache_data.clear()
    except Exception:
        pass
