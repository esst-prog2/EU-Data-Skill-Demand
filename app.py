"""
app.py

Interactive single-page Streamlit web dashboard for:
EU Data Jobs & Technical Skill Demand Analysis

Empirical technical skill intelligence across 27 EU member states and
5 target data occupations based on FreeHire job postings.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    CATEGORY_NAMES,
    EU27_COUNTRIES,
    OCCUPATIONAL_CATEGORIES,
    SENIORITY_DISPLAY_NAMES,
    SENIORITY_LEVELS,
    SKILL_FAMILIES,
    SkillVocabulary,
    compute_lift,
    compute_population_kpis,
    compute_population_skill_stats,
    compute_prevalence,
    extract_posting_record,
    filter_postings_by_skill_family,
    filter_postings_population,
    filter_skills_by_family,
    get_skills_for_family,
    load_or_create_postings_cache,
    prepare_scatter_data,
    rank_distinctive_skills,
    rank_in_demand_skills,
    validate_postings_cache,
)

# Paths
SUMMARY_PATH = Path(__file__).resolve().parent / "data" / "processed" / "analytics_summary.json"
DATA_PATH = SUMMARY_PATH
RAW_POSTINGS_PATH = Path(__file__).resolve().parent / "data" / "raw" / "freehire_eu_raw.json"
VOCAB_PATH = Path(__file__).resolve().parent / "data" / "fixtures" / "skills_vocabulary.json"
POSTINGS_CACHE_PATH = Path(__file__).resolve().parent / "data" / "processed" / ".postings_cache.json"
FIXTURE_POSTINGS_PATH = Path(__file__).resolve().parent / "data" / "fixtures" / "test_postings_fixture.json"

# Data Source Identifiers
DATA_SOURCE_PRODUCTION = "production"
DATA_SOURCE_TEST_FIXTURE = "test_fixture"
DATA_SOURCE_SYNTHETIC = "synthetic"

_ACTIVE_DATA_SOURCE: str = DATA_SOURCE_PRODUCTION


def get_active_data_source() -> str:
    """Returns the identifier of the active postings data source ('production', 'test_fixture', or 'synthetic')."""
    return _ACTIVE_DATA_SOURCE

st.set_page_config(
    page_title="EU Data Jobs & Skill Demand",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# Color Palettes (Precision Editorial Console Specification)
# =============================================================================

CATEGORY_PALETTE: Dict[str, str] = {
    "data_engineering": "#1e40af",  # Deep Cobalt
    "data_analytics": "#047857",    # Deep Emerald
    "ai_engineering": "#6d28d9",    # Royal Violet
    "data_science": "#b45309",      # Warm Amber / Sienna
    "ml_ai": "#be185d",             # Deep Berry Rose
}

# Differentiated, restrained skill-family palette to decouple from occupational roles
FAMILY_PALETTE: Dict[str, str] = {
    "Programming languages": "#334155",        # Slate 700 / Charcoal Navy
    "Databases & data warehouses": "#0f766e",   # Deep Teal
    "BI & visualization": "#d97706",            # Warm Ochre / Amber 600
    "Cloud & infrastructure": "#4338ca",        # Indigo 700
    "ML/AI frameworks & tools": "#701a75",      # Deep Plum / Fuchsia 900
}

# Accessible marker shapes for skill families (non-color visual encoding)
FAMILY_MARKER_SHAPES: Dict[str, str] = {
    "Programming languages": "circle",
    "Databases & data warehouses": "square",
    "BI & visualization": "diamond",
    "Cloud & infrastructure": "triangle-up",
    "ML/AI frameworks & tools": "hexagon",
}

ISO2_TO_ISO3: Dict[str, str] = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DK": "DNK", "EE": "EST", "ES": "ESP", "FI": "FIN",
    "FR": "FRA", "GR": "GRC", "HR": "HRV", "HU": "HUN", "IE": "IRL",
    "IT": "ITA", "LT": "LTU", "LU": "LUX", "LV": "LVA", "MT": "MLT",
    "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU", "SE": "SWE",
    "SI": "SVN", "SK": "SVK",
}
ISO3_TO_ISO2: Dict[str, str] = {v: k for k, v in ISO2_TO_ISO3.items()}


# =============================================================================
# Data Loading & Validation Helpers
# =============================================================================

def format_snapshot_date(iso_str: Any) -> str | None:
    """
    Validates and formats an ISO-8601 timestamp string into a human-readable UTC date,
    e.g. '2026-09-29T18:03:43.554417+00:00' -> '29 September 2026'.
    """
    if not isinstance(iso_str, str) or not iso_str.strip():
        return None
    try:
        dt = datetime.fromisoformat(iso_str.strip())
        if dt.tzinfo is None:
            return None
        dt_utc = dt.astimezone(timezone.utc)
        return f"{dt_utc.day} {dt_utc.strftime('%B %Y')}"
    except (ValueError, TypeError, OverflowError):
        return None


def get_geographic_note_data(geographic: Dict[str, Any]) -> tuple[int, int, int, str]:
    """
    Extracts and validates values needed for the geographic threshold note.
    """
    if not isinstance(geographic, dict):
        raise ValueError(f"Geographic section must be a dictionary, got {type(geographic).__name__}.")

    threshold = geographic.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold <= 0:
        raise ValueError(f"Geographic 'threshold' must be a positive integer, got {threshold!r}.")

    comp_eligible = geographic.get("composition_eligible")
    if not isinstance(comp_eligible, list):
        raise ValueError(f"Geographic 'composition_eligible' must be a list, got {type(comp_eligible).__name__}.")

    eligible_codes: list[str] = []
    for idx, record in enumerate(comp_eligible):
        if not isinstance(record, dict) or not isinstance(record.get("iso_code"), str) or not record["iso_code"].strip():
            raise ValueError(f"Invalid record at composition_eligible index {idx}: missing valid 'iso_code'.")
        eligible_codes.append(record["iso_code"].strip())

    if len(set(eligible_codes)) != len(eligible_codes):
        raise ValueError("Geographic 'composition_eligible' contains duplicate country codes.")

    eligible_count = geographic.get("eligible_count")
    if isinstance(eligible_count, bool) or not isinstance(eligible_count, int) or eligible_count < 0:
        raise ValueError(f"Geographic 'eligible_count' must be a non-negative integer, got {eligible_count!r}.")

    if eligible_count != len(comp_eligible):
        raise ValueError(
            f"Geographic 'eligible_count' ({eligible_count}) does not match "
            f"the number of records in 'composition_eligible' ({len(comp_eligible)})."
        )

    excluded_count = geographic.get("excluded_count")
    if isinstance(excluded_count, bool) or not isinstance(excluded_count, int) or excluded_count < 0:
        raise ValueError(f"Geographic 'excluded_count' must be a non-negative integer, got {excluded_count!r}.")

    if eligible_count + excluded_count != 27:
        raise ValueError(
            f"Geographic eligible count ({eligible_count}) and excluded count ({excluded_count}) "
            f"must sum to 27 EU member states, got {eligible_count + excluded_count}."
        )

    codes_str = ", ".join(eligible_codes)
    return threshold, eligible_count, excluded_count, codes_str


def get_intro_text(total_postings: int, snapshot_date: str | None = None) -> str:
    total_str = f"{total_postings:,}"
    if snapshot_date:
        return (
            f"An empirical analysis of technical skill demand across data-related occupations and EU-27 member states, "
            f"based on an audited snapshot of **{total_str} FreeHire job postings** (Latest snapshot collected: {snapshot_date})."
        )
    return (
        f"An empirical analysis of technical skill demand across data-related occupations and EU-27 member states, "
        f"based on an audited snapshot of **{total_str} FreeHire job postings**."
    )


def get_footer_text(total_postings: int, snapshot_date: str | None = None) -> str:
    total_str = f"{total_postings:,}"
    if snapshot_date:
        return (
            f"EU Data Jobs & Skill Demand Analysis • Built with Python & Streamlit • "
            f"Data Source: FreeHire snapshot ({total_str} postings) • Latest snapshot collected: {snapshot_date}"
        )
    return (
        f"EU Data Jobs & Skill Demand Analysis • Built with Python & Streamlit • "
        f"Data Source: FreeHire snapshot ({total_str} postings)"
    )


def validate_analytics_summary(data: Dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"Summary data must be a dictionary, got {type(data).__name__}.")

    for section in ("kpis", "market_overview", "category_profiles", "geographic"):
        if section not in data:
            raise ValueError(f"Summary data is missing required section: '{section}'.")
        if not isinstance(data[section], dict):
            raise ValueError(f"Section '{section}' must be a dictionary, got {type(data[section]).__name__}.")

    if not data["category_profiles"]:
        raise ValueError("Section 'category_profiles' cannot be empty.")

    for cat_id, profile in data["category_profiles"].items():
        if not isinstance(profile, dict):
            raise ValueError(f"Category profile '{cat_id}' must be a dictionary, got {type(profile).__name__}.")
        tot_cat = profile.get("total_postings")
        if isinstance(tot_cat, bool) or not isinstance(tot_cat, int) or tot_cat < 0:
            raise ValueError(
                f"Category profile '{cat_id}' must have a non-negative integer 'total_postings', got {tot_cat!r}."
            )

    kpis = data["kpis"]
    for req_kpi in ("total_postings", "total_countries", "total_categories", "seniority_coverage_pct"):
        if req_kpi not in kpis:
            raise ValueError(f"KPI section is missing required field: '{req_kpi}'.")

    tot_postings = kpis["total_postings"]
    if isinstance(tot_postings, bool) or not isinstance(tot_postings, int):
        raise ValueError(f"KPI 'total_postings' must be an integer, got {type(tot_postings).__name__}.")
    if tot_postings <= 0:
        raise ValueError(f"KPI 'total_postings' must be positive, got {tot_postings}.")

    tot_countries = kpis["total_countries"]
    if isinstance(tot_countries, bool) or not isinstance(tot_countries, int):
        raise ValueError(f"KPI 'total_countries' must be an integer, got {type(tot_countries).__name__}.")
    if not (1 <= tot_countries <= 27):
        raise ValueError(f"KPI 'total_countries' must be between 1 and 27, got {tot_countries}.")

    tot_categories = kpis["total_categories"]
    if isinstance(tot_categories, bool) or not isinstance(tot_categories, int):
        raise ValueError(f"KPI 'total_categories' must be an integer, got {type(tot_categories).__name__}.")
    if not (1 <= tot_categories <= 5):
        raise ValueError(f"KPI 'total_categories' must be between 1 and 5, got {tot_categories}.")
    if tot_categories != len(data["category_profiles"]):
        raise ValueError(
            f"KPI 'total_categories' ({tot_categories}) does not match "
            f"the number of category profiles ({len(data['category_profiles'])})."
        )

    sen_pct = kpis["seniority_coverage_pct"]
    if isinstance(sen_pct, bool) or not isinstance(sen_pct, (int, float)):
        raise ValueError(f"KPI 'seniority_coverage_pct' must be a numeric percentage, got {type(sen_pct).__name__}.")
    if not math.isfinite(sen_pct) or not (0.0 <= sen_pct <= 100.0):
        raise ValueError(f"KPI 'seniority_coverage_pct' must be a finite number between 0.0 and 100.0, got {sen_pct}.")

    get_geographic_note_data(data["geographic"])


@st.cache_data
def load_analytics_summary() -> Dict[str, Any]:
    """Loads and validates precomputed summary metrics."""
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(f"Missing summary file: {SUMMARY_PATH}")
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_analytics_summary(data)
    return data


def load_fixture_postings(path: Path) -> list[Dict[str, Any]]:
    """Loads and normalizes postings from a deterministic test fixture JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Fixture postings file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_list = data.get("postings", data) if isinstance(data, dict) else data
    if not isinstance(raw_list, list):
        raise ValueError(f"Invalid fixture format in {path}: expected list or dict with 'postings' key")

    postings: list[Dict[str, Any]] = []
    for p in raw_list:
        postings.append({
            "id": str(p.get("id", "")),
            "country": p.get("country"),
            "category": p.get("category"),
            "seniority": p.get("seniority"),
            "skills": set(p.get("skills", [])),
        })
    return postings


@st.cache_data
def load_postings_dataset(data_mode: str | None = None, source: str | None = None) -> list[Dict[str, Any]]:
    """
    Loads the postings dataset distinguishing between:
    1. Explicit file path / override via source argument or POSTINGS_DATA_PATH env var.
    2. Explicit mode via data_mode argument or EU_DATA_MODE env var ('production' or 'test_fixture').
    3. Production dataset from .postings_cache.json or freehire_eu_raw.json.
    4. Deterministic test fixture fallback (data/fixtures/test_postings_fixture.json).
    """
    global _ACTIVE_DATA_SOURCE

    # 1. Explicit override via argument or env var
    env_path = os.environ.get("POSTINGS_DATA_PATH")
    target_path = Path(source) if source else (Path(env_path) if env_path else None)

    if target_path and target_path.exists():
        if "fixture" in target_path.name.lower():
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_TEST_FIXTURE
            return load_fixture_postings(target_path)
        else:
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_PRODUCTION
            cached = validate_postings_cache(target_path, expected_fingerprint={})
            if cached:
                return cached
            return load_fixture_postings(target_path)

    # 2. Explicit mode via argument or env var
    effective_mode = (data_mode or os.environ.get("EU_DATA_MODE", "")).lower().strip()
    if effective_mode == "test_fixture":
        if FIXTURE_POSTINGS_PATH.exists():
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_TEST_FIXTURE
            return load_fixture_postings(FIXTURE_POSTINGS_PATH)
        raise FileNotFoundError(f"Requested test_fixture mode but fixture not found: {FIXTURE_POSTINGS_PATH}")

    if effective_mode == "production":
        # Strictly require production data; DO NOT silently fall back!
        if POSTINGS_CACHE_PATH.exists():
            cached = validate_postings_cache(POSTINGS_CACHE_PATH, expected_fingerprint={})
            if cached:
                _ACTIVE_DATA_SOURCE = DATA_SOURCE_PRODUCTION
                return cached
        if RAW_POSTINGS_PATH.exists() and VOCAB_PATH.exists():
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_PRODUCTION
            return load_or_create_postings_cache(
                cache_path=POSTINGS_CACHE_PATH,
                raw_path=RAW_POSTINGS_PATH,
                vocab_path=VOCAB_PATH,
            )
        raise FileNotFoundError(
            f"Requested production data mode but production dataset is missing. "
            f"Expected {POSTINGS_CACHE_PATH} or {RAW_POSTINGS_PATH}."
        )

    # 3. Default auto-discovery: Prefer production data if available locally
    if RAW_POSTINGS_PATH.exists() and VOCAB_PATH.exists():
        try:
            records = load_or_create_postings_cache(
                cache_path=POSTINGS_CACHE_PATH,
                raw_path=RAW_POSTINGS_PATH,
                vocab_path=VOCAB_PATH,
            )
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_PRODUCTION
            return records
        except Exception:
            pass

    if POSTINGS_CACHE_PATH.exists():
        cached_records = validate_postings_cache(POSTINGS_CACHE_PATH, expected_fingerprint={})
        if cached_records:
            _ACTIVE_DATA_SOURCE = DATA_SOURCE_PRODUCTION
            return cached_records

    # 4. Deterministic test fixture fallback when production files are absent (e.g. CI / clean checkout)
    if FIXTURE_POSTINGS_PATH.exists():
        _ACTIVE_DATA_SOURCE = DATA_SOURCE_TEST_FIXTURE
        return load_fixture_postings(FIXTURE_POSTINGS_PATH)

    raise FileNotFoundError(
        "No postings data available: neither production dataset nor test fixture "
        f"({FIXTURE_POSTINGS_PATH}) was found."
    )


# =============================================================================
# Modal Dialog Helper
# =============================================================================

@st.dialog("Chart View", width="large")
def render_expanded_chart_dialog(title: str, fig: go.Figure, description: str) -> None:
    """Renders a chart in a full-screen modal dialog."""
    st.subheader(title)
    st.caption(description)
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Visualization Builders
# =============================================================================

def build_europe_map_figure(
    country_counts: Counter[str],
    selected_countries: Sequence[str] | None = None,
    height: int = 400,
) -> go.Figure:
    """
    Builds a reframed European choropleth map.
    When countries are explicitly selected, highlights all selected countries
    prominently while subduing unselected countries, preserving exact posting counts in hovers.
    """
    selected_set = set(selected_countries) if selected_countries else None
    fig = go.Figure()

    # Case A: Default view (All Countries) -> continuous Blues choropleth
    if not selected_set:
        map_data = []
        for code, country_name in EU27_COUNTRIES.items():
            iso3 = ISO2_TO_ISO3.get(code)
            if not iso3:
                continue
            cnt = country_counts.get(code, 0)
            map_data.append({
                "iso3": iso3,
                "iso2": code,
                "country": country_name,
                "postings": cnt,
            })

        if map_data:
            fig = px.choropleth(
                map_data,
                locations="iso3",
                color="postings",
                hover_name="country",
                hover_data={"iso3": False, "iso2": True, "postings": ":,"},
                color_continuous_scale="Blues",
                labels={"postings": "Matching Postings", "iso2": "Code"},
            )
    else:
        # Case B: Explicit country selection -> prominent highlight for selected, subdued for unselected
        unselected_iso3 = []
        unselected_names = []
        for code, country_name in EU27_COUNTRIES.items():
            if code not in selected_set:
                iso3 = ISO2_TO_ISO3.get(code)
                if iso3:
                    unselected_iso3.append(iso3)
                    unselected_names.append(f"<b>{country_name}</b> ({code})<br>Status: Not selected<extra></extra>")

        # Unselected background trace
        if unselected_iso3:
            fig.add_trace(
                go.Choropleth(
                    locations=unselected_iso3,
                    z=[0] * len(unselected_iso3),
                    colorscale=[[0, "#f1f5f9"], [1, "#f1f5f9"]],
                    showscale=False,
                    hovertemplate="%{text}",
                    text=unselected_names,
                    marker=dict(line=dict(color="#cbd5e1", width=0.5)),
                    name="Unselected",
                )
            )

        # Selected countries trace
        sel_iso3 = []
        sel_counts = []
        sel_texts = []
        for code in selected_set:
            iso3 = ISO2_TO_ISO3.get(code)
            if not iso3:
                continue
            cnt = country_counts.get(code, 0)
            c_name = EU27_COUNTRIES.get(code, code)
            sel_iso3.append(iso3)
            sel_counts.append(cnt)
            status_note = f"Matching Postings: {cnt:,}" if cnt > 0 else "Matching Postings: 0 (No matching jobs)"
            sel_texts.append(f"<b>{c_name}</b> ({code}) [Selected]<br>{status_note}<extra></extra>")

        if sel_iso3:
            max_c = max(sel_counts) if sel_counts else 100
            sel_colorscale = [
                [0.0, "#60a5fa"],
                [0.5, "#2563eb"],
                [1.0, "#1e3a8a"],
            ]
            fig.add_trace(
                go.Choropleth(
                    locations=sel_iso3,
                    z=sel_counts,
                    colorscale=sel_colorscale,
                    zmin=0,
                    zmax=max(max_c, 10),
                    colorbar=dict(title="Postings", len=0.6, thickness=12),
                    hovertemplate="%{text}",
                    text=sel_texts,
                    marker=dict(line=dict(color="#1e3a8a", width=2.2)),
                    name="Selected",
                )
            )

    fig.update_geos(
        scope="europe",
        showcountries=True,
        countrycolor="#cbd5e1",
        showcoastlines=True,
        coastlinecolor="#cbd5e1",
        center=dict(lat=54.0, lon=14.0),
        projection_scale=1.05,
    )
    apply_editorial_chart_theme(fig, height=height, margin=dict(l=0, r=0, t=10, b=10))
    return fig


def apply_editorial_chart_theme(
    fig: go.Figure,
    height: int = 380,
    margin: dict | None = None,
) -> go.Figure:
    """
    Applies shared Precision Editorial Console styling to Plotly figures:
    clean white canvas, Slate 200 gridlines, and clean sans-serif typography.
    """
    default_margin = dict(l=20, r=20, t=15, b=15)
    fig.update_layout(
        height=height,
        margin=margin or default_margin,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            size=11,
            color="#334155",
        ),
    )
    return fig


def create_horizontal_bar_trace(
    x: Sequence[float | int],
    y: Sequence[str],
    text: Sequence[str],
    color: str | Sequence[str],
    hovertemplate: str,
    customdata: Any = None,
    name: str | None = None,
) -> go.Bar:
    """
    Standardizes horizontal single-series bar traces with strictly horizontal outside labels.
    Prevents vertical rotation, inside-bar crowding, and label clipping at boundaries.
    """
    kwargs: Dict[str, Any] = dict(
        x=x,
        y=y,
        orientation="h",
        text=text,
        textposition="outside",
        textangle=0,
        cliponaxis=False,
        marker=dict(color=color),
        hovertemplate=hovertemplate,
    )
    if customdata is not None:
        kwargs["customdata"] = customdata
    if name is not None:
        kwargs["name"] = name
    return go.Bar(**kwargs)


def apply_standard_bar_layout(
    fig: go.Figure,
    height: int,
    xaxis_title: str,
    max_val: float | int,
    headroom_factor: float = 1.35,
    min_range: float = 10.0,
    margin_right: int = 45,
) -> go.Figure:
    """
    Applies consistent horizontal bar layout styling, generous headroom, and uniformtext protection.
    Ensures outside text labels have sufficient margin space and never rotate sideways.
    """
    upper_bound = max(float(max_val) * headroom_factor, min_range) if max_val else min_range
    apply_editorial_chart_theme(fig, height=height, margin=dict(l=20, r=margin_right, t=10, b=10))
    fig.update_layout(
        xaxis_title=xaxis_title,
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, upper_bound]),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#1e293b")),
        uniformtext=dict(mode="hide", minsize=9),
    )
    return fig


def build_category_composition_bar(
    category_counts: Counter[str],
    total_postings: int,
    family_filter: str = "All Families",
    height: int = 380,
) -> go.Figure:
    """
    Builds horizontal bar chart comparing all 5 occupational categories.
    Accurately reflects postings requiring skills from the selected technical family.
    Uses strictly horizontal outside labels with generous rightward headroom.
    """
    cats_sorted = [
        "data_engineering",
        "data_analytics",
        "data_science",
        "ai_engineering",
        "ml_ai",
    ]
    names = []
    counts = []
    shares = []
    labels = []
    colors = []

    for cat_id in reversed(cats_sorted):
        cnt = category_counts.get(cat_id, 0)
        share = round((cnt / total_postings) * 100, 1) if total_postings > 0 else 0.0
        names.append(OCCUPATIONAL_CATEGORIES.get(cat_id, cat_id))
        counts.append(cnt)
        shares.append(share)
        labels.append(f"{cnt:,} ({share}%)" if cnt > 0 else "0 (0.0%)")
        colors.append(CATEGORY_PALETTE.get(cat_id, "#3b82f6"))

    trace = create_horizontal_bar_trace(
        x=counts,
        y=names,
        text=labels,
        color=colors,
        hovertemplate="<b>%{y}</b><br>Postings: %{x:,}<br>Share: %{customdata}%<extra></extra>",
        customdata=shares,
    )
    fig = go.Figure(trace)
    max_c = max(counts) if counts else 100
    return apply_standard_bar_layout(
        fig,
        height=height,
        xaxis_title="Matching Postings",
        max_val=max_c,
        headroom_factor=1.35,
        min_range=10.0,
        margin_right=45,
    )


def build_top_in_demand_bar(
    active_skills_stats: list[Dict[str, Any]],
    family_filter: str = "All Families",
    top_n: int = 10,
    height: int = 380,
) -> go.Figure:
    """Builds horizontal bar chart of top in-demand skills in active population with outside labels."""
    top_skills = active_skills_stats[:top_n]
    if not top_skills:
        fig = go.Figure()
        fig.add_annotation(
            text=f"No detected skills in '{family_filter}' for this selection.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        fig.update_layout(height=height, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    names = [s["canonical"] for s in reversed(top_skills)]
    prevs = [s["prevalence_pct"] for s in reversed(top_skills)]
    labels = [f"{s['prevalence_pct']}% ({s['count']:,} jobs)" for s in reversed(top_skills)]

    trace = create_horizontal_bar_trace(
        x=prevs,
        y=names,
        text=labels,
        color="#2563eb",
        hovertemplate="<b>%{y}</b><br>Prevalence: %{x}%<extra></extra>",
    )
    fig = go.Figure(trace)
    max_p = max(prevs) if prevs else 100.0
    return apply_standard_bar_layout(
        fig,
        height=height,
        xaxis_title="Prevalence in Active Selection (%)",
        max_val=max_p,
        headroom_factor=1.35,
        min_range=10.0,
        margin_right=45,
    )


def build_most_distinctive_bar(
    active_skills_stats: list[Dict[str, Any]],
    is_unselected_category: bool = False,
    top_n: int = 10,
    height: int = 380,
) -> go.Figure:
    """
    Builds horizontal bar chart of top qualified distinctive skills (Lift > 1.0, N>=20, P>=1.5%).
    When is_unselected_category is True, informs the user to select an occupational category.
    """
    fig = go.Figure()

    if is_unselected_category:
        fig.add_annotation(
            text=(
                "<b>Select an Occupational Category Above</b><br><br>"
                "Distinctiveness Lift measures concentration relative to the full EU corpus baseline.<br>"
                "Select a specific role above (e.g. <b>Data Science</b>, <b>Data Analytics</b>, or <b>Data Engineering</b>)<br>"
                "to calculate role-defining skills."
            ),
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=12, color="#475569"),
            align="center",
        )
        fig.update_layout(height=height, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    eligible = [s for s in active_skills_stats if s.get("is_eligible_distinctive")]
    eligible.sort(key=lambda s: (-s["lift"], -s["count"], s["canonical"]))
    top_distinctive = eligible[:top_n]

    if not top_distinctive:
        fig.add_annotation(
            text="No skills met qualification criteria (N ≥ 20, Prev ≥ 1.5%, Lift > 1.00)",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=12, color="#64748b"),
        )
        fig.update_layout(height=height, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    names = [s["canonical"] for s in reversed(top_distinctive)]
    lifts = [s["lift"] for s in reversed(top_distinctive)]
    labels = [f"{s['lift']}× ({s['prevalence_pct']}%, {s['count']:,} jobs)" for s in reversed(top_distinctive)]

    trace = create_horizontal_bar_trace(
        x=lifts,
        y=names,
        text=labels,
        color="#059669",
        hovertemplate="<b>%{y}</b><br>Distinctiveness Lift: %{x}× baseline<extra></extra>",
    )
    fig.add_trace(trace)
    max_l = max(lifts) if lifts else 2.0
    return apply_standard_bar_layout(
        fig,
        height=height,
        xaxis_title="Distinctiveness Lift (× baseline)",
        max_val=max_l,
        headroom_factor=1.35,
        min_range=2.0,
        margin_right=45,
    )


def build_corpus_benchmark_bar(
    overview_top_skills: list[Dict[str, Any]],
    top_n: int = 10,
    height: int = 400,
    corpus_total: int | None = None,
) -> go.Figure:
    """
    Builds horizontal bar chart of top skills across entire corpus (unfiltered benchmark).
    Uses a distinct, intentional deep indigo color (#6366f1) to distinguish from filtered results.
    """
    top_corpus = overview_top_skills[:top_n]
    fig = go.Figure()
    if not top_corpus:
        fig.add_annotation(
            text="Corpus baseline data unavailable",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(height=height, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    names = [s.get("skill", s.get("canonical", "")) for s in reversed(top_corpus)]
    prevs = [s.get("prevalence_pct", 0.0) for s in reversed(top_corpus)]
    labels = [f"{p}% ({s.get('count', 0):,} jobs)" for s, p in zip(reversed(top_corpus), prevs)]

    trace = create_horizontal_bar_trace(
        x=prevs,
        y=names,
        text=labels,
        color="#6366f1",  # Distinct Indigo
        hovertemplate="<b>%{y}</b><br>Corpus Baseline Prevalence: %{x}%<extra></extra>",
    )
    fig.add_trace(trace)
    max_p = max(prevs) if prevs else 100.0
    xaxis_desc = f"% of all {corpus_total:,} EU postings" if corpus_total else "% of all EU postings"
    return apply_standard_bar_layout(
        fig,
        height=height,
        xaxis_title=f"Corpus Baseline Prevalence ({xaxis_desc})",
        max_val=max_p,
        headroom_factor=1.35,
        min_range=10.0,
        margin_right=45,
    )


def build_country_volume_comparison_bar(
    country_records: list[Dict[str, Any]],
    height: int = 400,
) -> go.Figure:
    """
    Builds horizontal bar chart of matching postings per country for selected countries.
    Clearly shows sample sizes to interpret small-sample risks with outside horizontal labels.
    """
    fig = go.Figure()
    if not country_records:
        fig.add_annotation(
            text="No matching postings in selected countries",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(height=height)
        return fig

    sorted_records = sorted(country_records, key=lambda r: r["total_postings"])
    names = [f"{r['country_name']} ({r['iso_code']})" for r in sorted_records]
    counts = [r["total_postings"] for r in sorted_records]
    labels = [f"{c:,} jobs" for c in counts]
    # WCAG AA compliant dark amber (#b45309) for subthreshold countries vs deep royal blue
    colors = ["#b45309" if r.get("is_subthreshold") else "#2563eb" for r in sorted_records]

    trace = create_horizontal_bar_trace(
        x=counts,
        y=names,
        text=labels,
        color=colors,
        hovertemplate="<b>%{y}</b><br>Observed Postings: %{x:,}<extra></extra>",
    )
    fig.add_trace(trace)
    max_c = max(counts) if counts else 100
    return apply_standard_bar_layout(
        fig,
        height=height,
        xaxis_title="Observed Postings (Sample Size N)",
        max_val=max_c,
        headroom_factor=1.35,
        min_range=10.0,
        margin_right=45,
    )


def build_cross_country_composition_stacked_bar(
    country_records: list[Dict[str, Any]],
    height: int = 400,
) -> go.Figure:
    """
    Builds 100% stacked bar chart of category percentage breakdown across countries.
    Includes small countries with small-sample badges and displays percentage values inside bars.
    Strictly forces horizontal text (never sideways), constrains inside bar slices, and hides
    in-bar text when slices are too narrow to be legibly rendered (hover retains exact percentage).
    """
    fig = go.Figure()
    if not country_records:
        fig.add_annotation(
            text="No countries with matching postings in current selection",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        fig.update_layout(height=height)
        return fig

    sorted_records = sorted(country_records, key=lambda r: r["total_postings"])
    y_labels = []
    for r in sorted_records:
        tag = f"{r['country_name']} ({r['iso_code']})"
        if r.get("is_subthreshold"):
            tag += f" ⚠️ (N={r['total_postings']:,})"
        y_labels.append(tag)

    categories = [
        ("data_engineering", "Data Engineering"),
        ("data_analytics", "Data Analytics"),
        ("data_science", "Data Science"),
        ("ai_engineering", "AI Engineering"),
        ("ml_ai", "ML/AI"),
    ]

    for cat_id, cat_name in categories:
        shares = [r.get("shares", {}).get(cat_id, 0.0) for r in sorted_records]
        # Only show in-bar text when there is sufficient room (>= 8.0%), always horizontal
        texts = [f"{s:.0f}%" if s >= 8.0 else "" for s in shares]
        fig.add_trace(
            go.Bar(
                name=cat_name,
                y=y_labels,
                x=shares,
                orientation="h",
                text=texts,
                textposition="inside",
                insidetextanchor="middle",
                textangle=0,            # Strictly horizontal orientation: never sideways
                constraintext="inside", # Constrain inside the bar slice
                marker=dict(color=CATEGORY_PALETTE.get(cat_id, "#94a3b8")),
                hovertemplate=f"<b>%{{y}}</b><br>{cat_name}: %{{x:.1f}}%<extra></extra>",
            )
        )

    apply_editorial_chart_theme(fig, height=height, margin=dict(l=20, r=20, t=10, b=10))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Share of Country's Postings (% Composition)",
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        uniformtext=dict(mode="hide", minsize=9), # Hide text if it cannot fit horizontally at >=9pt
    )
    return fig


def build_scatter_figure(
    scatter_data: list[Dict[str, Any]],
    is_unselected_category: bool = False,
    show_dense: bool = False,
    selected_family: str = "All Families",
    height: int = 380,
) -> go.Figure:
    """
    Builds bivariate prevalence-vs-lift scatter plot.
    Default view shows top 10 most distinctive qualified skills with prominent labels.
    Generous vertical spacing ensures legend and x-axis labels never overlap.
    """
    fig_scatter = go.Figure()

    if is_unselected_category:
        fig_scatter.add_annotation(
            text=(
                "<b>Select an Occupational Category Above</b><br><br>"
                "When comparing the entire corpus to itself, all skills sit at Lift = 1.00 by definition.<br>"
                "Select a specific role above (e.g. <b>Data Science</b> or <b>Data Analytics</b>)<br>"
                "to reveal its distinctive skill quadrant."
            ),
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=12, color="#475569"),
            align="center",
        )
        apply_editorial_chart_theme(fig_scatter, height=height, margin=dict(l=20, r=20, t=20, b=60))
        fig_scatter.update_layout(
            xaxis_title="Within-Selection Prevalence (%)",
            yaxis_title="Distinctiveness Lift (× baseline)",
        )
        return fig_scatter

    if not scatter_data:
        fig_scatter.add_annotation(
            text=f"No observed skills in '{selected_family}' with count ≥ 1.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        apply_editorial_chart_theme(fig_scatter, height=height, margin=dict(l=20, r=20, t=20, b=60))
        return fig_scatter

    # Filter to top 10 qualified distinctive skills by default, unless dense view is requested
    if not show_dense:
        eligible_items = [d for d in scatter_data if d.get("is_eligible_distinctive")]
        eligible_items.sort(key=lambda d: (-d["lift"], -d["count"], d["canonical"]))
        display_data = eligible_items[:10]
        if not display_data:
            display_data = sorted(scatter_data, key=lambda d: (-d["lift"], -d["count"]))[:10]
    else:
        display_data = scatter_data

    families_present = sorted(set(d["skill_group"] for d in display_data))

    for fam in families_present:
        fam_items = [d for d in display_data if d["skill_group"] == fam]
        text_labels = [
            d["canonical"] if (not show_dense or d["is_eligible_distinctive"]) else ""
            for d in fam_items
        ]
        # Restrained opacity: 1.0 for distinctive, reduced to 0.25 in dense mode to avoid clutter
        opacities = [
            1.0 if d["is_eligible_distinctive"] else (0.25 if show_dense else 0.40)
            for d in fam_items
        ]
        # Controlled point sizes: 7.5px/5.0px in dense mode, 10.5px/6.5px in default top-10 mode
        marker_sizes = [
            (7.5 if show_dense else 10.5) if d["is_eligible_distinctive"]
            else (5.0 if show_dense else 6.5)
            for d in fam_items
        ]
        line_widths = [
            (1.2 if show_dense else 1.5) if d["is_eligible_distinctive"]
            else 0.5
            for d in fam_items
        ]

        fig_scatter.add_trace(
            go.Scatter(
                x=[d["prevalence_pct"] for d in fam_items],
                y=[d["lift"] for d in fam_items],
                mode="markers+text",
                name=fam,
                text=text_labels,
                textposition="top center",
                textfont=dict(size=11, color="#1e293b"),
                marker=dict(
                    symbol=FAMILY_MARKER_SHAPES.get(fam, "circle"),
                    size=marker_sizes,
                    color=FAMILY_PALETTE.get(fam, "#64748b"),
                    opacity=opacities,
                    line=dict(
                        width=line_widths,
                        color="#0f172a",
                    ),
                ),
                customdata=[
                    [
                        d["canonical"],
                        d["skill_group"],
                        d["count"],
                        d["prevalence_pct"],
                        d["lift"],
                        d["support_status"],
                    ]
                    for d in fam_items
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                    "Prevalence: %{customdata[3]}% (%{customdata[2]:,} postings)<br>"
                    "Lift: %{customdata[4]}× baseline<br>"
                    "Status: %{customdata[5]}<extra></extra>"
                ),
            )
        )

    max_prev = max(d["prevalence_pct"] for d in display_data) if display_data else 100.0
    max_lift = max(d["lift"] for d in display_data) if display_data else 2.0
    x_upper = max(max_prev * 1.18, 10.0)
    y_upper = max(max_lift * 1.18, 2.0)

    fig_scatter.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="#b91c1c",
        line_width=1.5,
        annotation_text="Corpus Parity (Lift = 1.0)",
        annotation_position="top right",
        annotation_font=dict(color="#b91c1c", size=11, family="Inter, -apple-system, sans-serif"),
    )

    # Subtle Quadrant Watermark Annotations (Framing the Bivariate Landscape)
    if y_upper > 1.2:
        fig_scatter.add_annotation(
            text="<b>ROLE SUPERPOWERS</b><br><span style='font-size:9px'>High Demand · High Distinctiveness</span>",
            xref="x", yref="y",
            x=x_upper * 0.96, y=y_upper * 0.95,
            xanchor="right", yanchor="top",
            showarrow=False,
            font=dict(size=9.5, color="rgba(4, 120, 87, 0.38)", family="Inter, -apple-system, sans-serif"),
            align="right",
        )
        fig_scatter.add_annotation(
            text="<b>NICHE SPECIALIZATIONS</b><br><span style='font-size:9px'>Lower Demand · High Distinctiveness</span>",
            xref="x", yref="y",
            x=x_upper * 0.03, y=y_upper * 0.95,
            xanchor="left", yanchor="top",
            showarrow=False,
            font=dict(size=9.5, color="rgba(100, 116, 139, 0.38)", family="Inter, -apple-system, sans-serif"),
            align="left",
        )
        fig_scatter.add_annotation(
            text="<b>UNIVERSAL CURRENCY</b><br><span style='font-size:9px'>High Demand · Market Parity</span>",
            xref="x", yref="y",
            x=x_upper * 0.96, y=0.15,
            xanchor="right", yanchor="bottom",
            showarrow=False,
            font=dict(size=9.5, color="rgba(30, 64, 175, 0.35)", family="Inter, -apple-system, sans-serif"),
            align="right",
        )
        fig_scatter.add_annotation(
            text="<b>PERIPHERAL SKILLS</b><br><span style='font-size:9px'>Lower Demand · Sub-Parity</span>",
            xref="x", yref="y",
            x=x_upper * 0.03, y=0.15,
            xanchor="left", yanchor="bottom",
            showarrow=False,
            font=dict(size=9.5, color="rgba(148, 163, 184, 0.35)", family="Inter, -apple-system, sans-serif"),
            align="left",
        )

    apply_editorial_chart_theme(fig_scatter, height=height, margin=dict(l=20, r=20, t=20, b=70))
    fig_scatter.update_layout(
        xaxis_title="Within-Selection Prevalence (%)",
        yaxis_title="Distinctiveness Lift (× baseline)",
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, x_upper]),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, y_upper]),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(size=10.5),
        ),
    )
    return fig_scatter


# =============================================================================
# Main Application
# =============================================================================

def main() -> None:
    # 1. Load Data
    summary = load_analytics_summary()
    postings = load_postings_dataset(data_mode=os.environ.get("EU_DATA_MODE", "").lower().strip())
    kpis_summary = summary.get("kpis", {})
    corpus_total = kpis_summary.get("total_postings", len(postings) or 24488)
    snapshot_date = format_snapshot_date(summary.get("snapshot_collected_at"))

    # Vocabulary & Corpus Skill Counts
    vocab = SkillVocabulary.load_from_file(VOCAB_PATH) if VOCAB_PATH.exists() else SkillVocabulary({"skills": []})
    corpus_skill_counts: Counter[str] = Counter()
    for p in postings:
        for s in p.get("skills", set()):
            corpus_skill_counts[s] += 1

    # 2. Header
    st.title("🇪🇺 EU Data Jobs & Skill Demand")
    st.caption(
        f"Empirical European technical skill intelligence across 27 EU member states and 5 target data occupations. "
        f"Audited snapshot of {corpus_total:,} job postings • Snapshot date: {snapshot_date or 'Recent'}"
    )

    if get_active_data_source() == DATA_SOURCE_TEST_FIXTURE:
        st.info(
            f"🧪 **Test Fixture Mode Active:** The dashboard is running with a deterministic test fixture "
            f"(`data/fixtures/test_postings_fixture.json`, {len(postings)} postings). "
            "To view the full 24,488-posting production analysis, provide the audited production dataset."
        )

    # 3. Session State Initialization
    if "filter_version" not in st.session_state:
        st.session_state["filter_version"] = 0
    if "filter_countries" not in st.session_state:
        st.session_state["filter_countries"] = []
    if "filter_category" not in st.session_state:
        st.session_state["filter_category"] = "All Categories"
    if "filter_seniority" not in st.session_state:
        st.session_state["filter_seniority"] = "All Seniorities"
    if "filter_family" not in st.session_state:
        st.session_state["filter_family"] = "All Families"
    if "_last_clicked_map_country" not in st.session_state:
        st.session_state["_last_clicked_map_country"] = None

    ver = st.session_state["filter_version"]

    # 4. Persistent Global Filter Bar (Compact Sticky Container)
    country_codes = sorted(list(EU27_COUNTRIES.keys()))
    cat_options = ["All Categories"] + list(OCCUPATIONAL_CATEGORIES.keys())
    cat_labels = {"All Categories": "All Job Families (Corpus)"}
    cat_labels.update(OCCUPATIONAL_CATEGORIES)

    sen_options = ["All Seniorities"] + list(SENIORITY_LEVELS)
    sen_labels = {"All Seniorities": "All Seniorities"}
    sen_labels.update(SENIORITY_DISPLAY_NAMES)

    family_options = ["All Families"] + list(SKILL_FAMILIES)

    # Global Precision Editorial Console Styles
    st.markdown(
        """
        <style>
        /* Canvas background */
        .stApp {
            background-color: #f8fafc;
        }

        /* Editorial serif typography selectively for main title and section headings */
        h1, h2, h3, [data-testid="stHeader"] h1 {
            font-family: "Newsreader", "Charter", "Georgia", "Cambria", "Times New Roman", serif !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            color: #0f172a !important;
        }

        /* Clean, readable sans-serif for UI controls, body text, tables, and captions */
        html, body, [data-testid="stAppViewContainer"], .stMarkdown p, .stMarkdown span, .stCaption, label, .stSelectbox, .stMultiSelect, button, input {
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }

        /* Tabular numerals for all metrics and data tables to prevent layout jitter */
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"], .tabular-nums, table, td, th {
            font-variant-numeric: tabular-nums !important;
        }

        /* KPI Card styling: Clean hairline borders, subtle elevation, generous padding */
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 0.85rem 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
            transition: border-color 0.15s ease;
        }

        div[data-testid="stMetric"]:hover {
            border-color: #cbd5e1;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: #64748b !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            color: #0f172a !important;
            line-height: 1.2 !important;
        }

        /* Sticky Filter Command Bar */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div.sticky-filter-marker) {
            position: sticky;
            top: 2.85rem;
            z-index: 99;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.8rem;
        }

        /* Card containers for chart sections */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }

        /* Data Table refinement */
        div[data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }

        /* Button refinement */
        div.stButton > button {
            border-radius: 5px;
            font-weight: 500;
            border: 1px solid #cbd5e1;
            transition: all 0.15s ease;
        }

        div.stButton > button:hover {
            border-color: #94a3b8;
            background-color: #f1f5f9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="sticky-filter-marker"></div>', unsafe_allow_html=True)
        f_col1, f_col2, f_col3, f_col4, f_col_btn = st.columns([2.5, 2.0, 1.8, 2.2, 0.8])

        with f_col1:
            sel_countries = st.multiselect(
                "Country:",
                options=country_codes,
                default=st.session_state["filter_countries"],
                format_func=lambda c: f"{EU27_COUNTRIES.get(c, c)} ({c})",
                placeholder="All EU-27 Countries (default)",
                key=f"ms_countries_{ver}",
                help="Search and select one, multiple, or all EU-27 member states.",
            )
            st.session_state["filter_countries"] = sel_countries

        with f_col2:
            sel_category = st.selectbox(
                "Job Family / Category:",
                options=cat_options,
                format_func=lambda k: cat_labels.get(k, k),
                index=cat_options.index(st.session_state["filter_category"]) if st.session_state["filter_category"] in cat_options else 0,
                key=f"sb_cat_{ver}",
            )
            if st.session_state.get("_last_global_category") != sel_category:
                st.session_state["_last_global_category"] = sel_category
                if sel_category != "All Categories":
                    st.session_state[f"local_dist_cat_{ver}"] = sel_category
                    st.session_state[f"local_scatter_cat_{ver}"] = sel_category
                else:
                    st.session_state[f"local_dist_cat_{ver}"] = "-- Select a Job Family for Distinctiveness --"
                    st.session_state[f"local_scatter_cat_{ver}"] = "-- Select a Job Family for Distinctiveness --"
            st.session_state["filter_category"] = sel_category

        with f_col3:
            sel_seniority = st.selectbox(
                "Seniority:",
                options=sen_options,
                format_func=lambda s: sen_labels.get(s, s),
                index=sen_options.index(st.session_state["filter_seniority"]) if st.session_state["filter_seniority"] in sen_options else 0,
                key=f"sb_sen_{ver}",
            )
            st.session_state["filter_seniority"] = sel_seniority

        with f_col4:
            sel_family = st.selectbox(
                "Filter by Technical Skill Family:",
                options=family_options,
                index=family_options.index(st.session_state["filter_family"]) if st.session_state["filter_family"] in family_options else 0,
                key=f"sb_fam_{ver}",
                help="Filter skills across the analysis by technical domain.",
            )
            st.session_state["filter_family"] = sel_family

        with f_col_btn:
            st.write("")
            st.write("")
            if st.button("🔄 Reset", help="Reset all filters to default"):
                st.session_state["filter_version"] += 1
                st.session_state["filter_countries"] = []
                st.session_state["filter_category"] = "All Categories"
                st.session_state["filter_seniority"] = "All Seniorities"
                st.session_state["filter_family"] = "All Families"
                st.session_state["local_dist_cat"] = "-- Select a Job Family for Distinctiveness --"
                st.session_state["local_scatter_cat"] = "-- Select a Job Family for Distinctiveness --"
                st.session_state["_last_global_category"] = "All Categories"
                st.session_state["_last_clicked_map_country"] = None
                st.rerun()

    # Active Filter Context Caption
    active_c_list = st.session_state["filter_countries"]
    if not active_c_list:
        c_summary = "All EU-27 Countries"
    elif len(active_c_list) == 1:
        c_summary = f"{EU27_COUNTRIES.get(active_c_list[0], active_c_list[0])} ({active_c_list[0]})"
    elif len(active_c_list) <= 4:
        c_summary = ", ".join(EU27_COUNTRIES.get(c, c) for c in active_c_list)
    else:
        c_summary = f"{len(active_c_list)} countries selected ({', '.join(active_c_list[:3])}...)"

    # 5. Apply Global Filters
    filter_res = filter_postings_population(
        postings,
        country=active_c_list,
        category=st.session_state["filter_category"],
        seniority=st.session_state["filter_seniority"],
    )

    baseline_count = filter_res["baseline_count"]
    known_seniority_count = filter_res["known_seniority_count"]
    seniority_coverage_pct = filter_res["seniority_coverage_pct"]
    active_postings = filter_res["active_postings"]
    active_count = filter_res["active_count"]

    # Calculate Population Skill Stats
    all_skills_stats = compute_population_skill_stats(
        active_postings=active_postings,
        corpus_skill_counts=corpus_skill_counts,
        corpus_total=corpus_total,
        vocabulary=vocab,
    )

    # Synchronized Family Filtering for Skill-level Views & KPIs
    active_family = st.session_state["filter_family"]
    if active_family != "All Families":
        active_skills_stats = filter_skills_by_family(all_skills_stats, active_family)
    else:
        active_skills_stats = all_skills_stats

    # Compute KPIs
    selected_c_count = len(active_c_list) if active_c_list else 27
    pop_kpis = compute_population_kpis(
        active_postings=active_postings,
        corpus_total=corpus_total,
        active_skills_stats=active_skills_stats,
        selected_countries_count=selected_c_count,
    )

    # Dynamic Seniority Coverage Banner
    is_specific_seniority = st.session_state["filter_seniority"] != "All Seniorities"
    sen_name = sen_labels.get(st.session_state["filter_seniority"], st.session_state["filter_seniority"])

    if is_specific_seniority:
        st.info(
            f"ℹ️ **Seniority Coverage:** Seniority is available for **{seniority_coverage_pct}%** of postings "
            f"in the current country/job-family selection ({known_seniority_count:,} of {baseline_count:,}). "
            f"The statistics below reflect the **{active_count:,}** postings matching **{sen_name}** level."
        )
    else:
        st.caption(
            f"ℹ️ **Population Scope:** {c_summary} • "
            f"{cat_labels.get(st.session_state['filter_category'])} • "
            f"All postings included ({active_count:,} total). "
            f"Seniority metadata is reported for **{seniority_coverage_pct}%** of postings in this selection "
            f"({known_seniority_count:,} of {baseline_count:,})."
        )

    # Sample-Size Warning ($N < 300$)
    if active_count < 300:
        st.warning(
            f"⚠️ **Small Sample Size Warning:** Only **{active_count:,}** observed postings match the active filter selection ($N < 300$). "
            f"Occupational breakdowns, category distributions, and distinctiveness lift estimates should be interpreted with caution."
        )

    # 6. KPI Cards (4 Compact Metric Containers with Mathematically Meaningful Subtitles)
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)

    with k_col1:
        st.metric(
            label="Matching Postings",
            value=f"{pop_kpis['active_postings_count']:,}",
            help=f"{pop_kpis['corpus_share_pct']}% of the total EU data corpus ({corpus_total:,} postings).",
        )
        st.caption(f"{pop_kpis['corpus_share_pct']}% of {corpus_total:,} corpus postings")

    with k_col2:
        # Clear, unambiguous metric: Countries with Postings out of 27 EU member states
        obs_c = pop_kpis["represented_countries_count"]
        sel_c_len = len(active_c_list)
        if sel_c_len > 0:
            c_help = f"{obs_c} of 27 EU member states ({obs_c} of {sel_c_len} selected countries have matching postings)."
            denom_text = f"Across {sel_c_len} selected EU states"
        else:
            c_help = f"{obs_c} of 27 EU member states have matching job postings in this selection."
            denom_text = "Across all 27 EU member states"
        st.metric(
            label="Countries with Postings",
            value=f"{obs_c} / 27",
            help=c_help,
        )
        st.caption(denom_text)

    with k_col3:
        fam_note = f"within '{active_family}'" if active_family != "All Families" else "across all families"
        if active_family != "All Families":
            family_skills = get_skills_for_family(vocab, active_family)
            denom_skills = len(family_skills)
            skill_sub = f"Of {denom_skills} '{active_family}' skills"
        else:
            total_vocab_skills = len(vocab.skills) if hasattr(vocab, "skills") and vocab.skills else 52
            denom_skills = total_vocab_skills
            skill_sub = f"Of {denom_skills} canonical controlled skills"

        st.metric(
            label="Detected Technical Skills",
            value=pop_kpis["detected_skills_count"],
            help=f"Distinct technical skills observed in the active selection ({fam_note}). Traceable in the complete table below.",
        )
        st.caption(skill_sub)

    with k_col4:
        detected_kpi_val = pop_kpis["detected_skills_count"]
        st.metric(
            label="Qualified Distinctive Skills",
            value=pop_kpis["qualified_distinctive_count"],
            help="Skills meeting primary support thresholds (N ≥ 20, Prev ≥ 1.5%) with Lift > 1.0 vs corpus parity.",
        )
        st.caption(f"Of {detected_kpi_val} detected skills in selection")

    st.markdown("---")

    # =========================================================================
    # ROW 1: Job-Family Composition + Top In-Demand Skills
    # =========================================================================
    st.subheader("1. Occupational Structure & High-Demand Skills")
    r1_col_comp, r1_col_skills = st.columns(2)

    # Left: Job-Family Composition (Compares all 5 occupational categories)
    with r1_col_comp:
        head_c, btn_c = st.columns([4, 1])
        with head_c:
            st.markdown("**Job-Family Composition**")
            if active_family != "All Families":
                st.caption(f"Comparing data job families for postings requiring at least one '{active_family}' skill.")
            else:
                st.caption("Comparing occupational share across all 5 data job families in active country & seniority slice.")

        # Population for category composition: ignores single global category selection to preserve 5-way comparison
        country_sen_postings = filter_postings_population(
            postings,
            country=active_c_list,
            category=None,
            seniority=st.session_state["filter_seniority"],
        )["active_postings"]

        comp_postings = filter_postings_by_skill_family(country_sen_postings, active_family, vocab)
        category_counts: Counter[str] = Counter()
        for p in comp_postings:
            cat = p.get("category")
            if cat:
                category_counts[cat] += 1

        fig_comp = build_category_composition_bar(
            category_counts,
            total_postings=len(comp_postings),
            family_filter=active_family,
            height=380,
        )

        with btn_c:
            if st.button("⛶ Expand", key="expand_comp"):
                render_expanded_chart_dialog(
                    "Job-Family Composition",
                    fig_comp,
                    "Distribution across the 5 target data occupations.",
                )

        st.plotly_chart(fig_comp, use_container_width=True)

    # Right: Top In-Demand Skills (Universal prevalence ranking)
    with r1_col_skills:
        head_s, btn_s = st.columns([4, 1])
        with head_s:
            st.markdown("**Top In-Demand Skills**")
            if active_family == "All Families":
                st.caption("Most frequent technical skills in active selection (% prevalence).")
            else:
                st.caption(f"Most frequent {active_family} skills in active selection (% prevalence).")

        fig_skills = build_top_in_demand_bar(
            active_skills_stats,
            family_filter=active_family,
            top_n=10,
            height=380,
        )

        with btn_s:
            if st.button("⛶ Expand", key="expand_skills"):
                render_expanded_chart_dialog(
                    "Top In-Demand Skills",
                    fig_skills,
                    "Most frequent technical skills in active selection.",
                )

        st.plotly_chart(fig_skills, use_container_width=True)

    # =========================================================================
    # ROW 2: Most Distinctive Skills + Prevalence vs. Distinctiveness (Lift)
    # =========================================================================
    st.markdown("---")
    st.subheader("2. Role Distinctiveness & Skill Quadrant Analysis")
    st.caption("Contrasting role-defining technical markers (Lift > 1.00 vs corpus baseline) with bivariate quadrant positioning.")

    # In-situ Lift explainer (collapsible, educational guidance)
    with st.expander("ℹ️ How to Interpret Distinctiveness Lift and the Four Quadrants", expanded=False):
        st.markdown(
            "**Distinctiveness Lift** quantifies how much more (or less) frequently a technical skill is demanded\n"
            "within a specific occupational role compared to the overall European data job market baseline:\n\n"
            r"$$\text{Lift} = \frac{P(\text{skill} \mid \text{occupation})}{P(\text{skill} \mid \text{corpus})}" + "\n\n"
            "- **Occupational Skill Prevalence ($P_{\\text{role}}$):** The percentage of unique job postings for the selected occupation that explicitly list the skill.\n"
            "- **Corpus Baseline Prevalence ($P_{\\text{corpus}}$):** The percentage of postings across the entire European data corpus ($N = 23{,}138$) mentioning the skill.\n"
            "- **Interpretation of Lift values:**\n"
            "  - **Lift $> 1.00$ (Over-indexed):** The skill is concentrated in this profession relative to the overall market (e.g. **Power BI** in *Data Analytics*: $44.8\\% / 17.1\\% = 2.61\\times$ Lift).\n"
            "  - **Lift $= 1.00$ (Corpus Parity):** The skill appears at the exact same rate as the general data market baseline.\n"
            "  - **Lift $< 1.00$ (Under-indexed):** The skill appears less often than across data jobs generally, even if common (e.g. **Python** in *Data Analytics*: $42.2\\% / 57.1\\% = 0.74\\times$ Lift, because it is even more dominant in Engineering and Science).\n\n"
            "**The Four Quadrant Landscape:**\n"
            "1. **Role Superpowers (Top-Right):** High prevalence ($> 20\\%$) and high distinctiveness ($\\text{Lift} > 1.00$). Defining technical signatures of the role.\n"
            "2. **Niche Specializations (Top-Left):** Lower prevalence ($< 20\\%$) but high distinctiveness ($\\text{Lift} > 1.00$). Specialized tools unique to this field.\n"
            "3. **Universal Currency (Bottom-Right):** High prevalence ($> 20\\%$) but parity or sub-parity distinctiveness ($\\text{Lift} \\le 1.00$). Baseline skills expected across all data roles.\n"
            "4. **Peripheral Skills (Bottom-Left):** Lower prevalence ($< 20\\%$) and lower distinctiveness ($\\text{Lift} \\le 1.00$). Ancillary or secondary tools.\n\n"
            "*Note: Distinctive qualifications require $N \\ge 20$ postings and $P \\ge 1.5\\%$ to protect against small-sample lift inflation.*"
        )

    cat_choice_keys = ["-- Select a Job Family for Distinctiveness --"] + list(OCCUPATIONAL_CATEGORIES.keys())
    cat_choice_display = {"-- Select a Job Family for Distinctiveness --": "🔍 Select a Job Family for Distinctiveness..."}
    cat_choice_display.update(OCCUPATIONAL_CATEGORIES)

    # Resolve defaults based on global filter
    if st.session_state["filter_category"] != "All Categories":
        default_dist_cat = st.session_state["filter_category"]
        default_scatter_cat = st.session_state["filter_category"]
    else:
        default_dist_cat = st.session_state.get("local_dist_cat", "-- Select a Job Family for Distinctiveness --")
        default_scatter_cat = st.session_state.get("local_scatter_cat", "-- Select a Job Family for Distinctiveness --")

    # Unified Row 2 Control Deck Container
    with st.container(border=True):
        r2_ctrl1, r2_ctrl2, r2_ctrl3 = st.columns([2.5, 2.5, 2.0])
        with r2_ctrl1:
            sel_dist_cat = st.selectbox(
                "Occupational Role (for Distinctive Ranking):",
                options=cat_choice_keys,
                format_func=lambda k: cat_choice_display.get(k, k),
                index=cat_choice_keys.index(default_dist_cat) if default_dist_cat in cat_choice_keys else 0,
                key=f"local_dist_cat_{ver}",
                help="Select an occupational role to benchmark distinctive skills against the full corpus baseline.",
            )
            st.session_state["local_dist_cat"] = sel_dist_cat
        with r2_ctrl2:
            sel_scatter_cat = st.selectbox(
                "Occupational Role (for Scatter Plot):",
                options=cat_choice_keys,
                format_func=lambda k: cat_choice_display.get(k, k),
                index=cat_choice_keys.index(default_scatter_cat) if default_scatter_cat in cat_choice_keys else 0,
                key=f"local_scatter_cat_{ver}",
                help="Select an occupational role to visualize prevalence vs. distinctiveness lift in the quadrant scatter plot.",
            )
            st.session_state["local_scatter_cat"] = sel_scatter_cat
        with r2_ctrl3:
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
            show_dense = st.checkbox(
                "Include all detected skills (including unqualified skills)",
                value=False,
                key=f"scatter_dense_{ver}",
                help="Unchecked: Top 10 qualified distinctive skills. Checked: All detected skills in this population.",
            )

    # Determine effective roles for tandem synchronization:
    # If a role is selected in either selector while the other remains at the default prompt,
    # both Row 2 visualizations synchronize to that role.
    effective_dist_cat = sel_dist_cat
    effective_scatter_cat = sel_scatter_cat
    if effective_dist_cat == "-- Select a Job Family for Distinctiveness --" and effective_scatter_cat != "-- Select a Job Family for Distinctiveness --":
        effective_dist_cat = effective_scatter_cat
    elif effective_scatter_cat == "-- Select a Job Family for Distinctiveness --" and effective_dist_cat != "-- Select a Job Family for Distinctiveness --":
        effective_scatter_cat = effective_dist_cat

    r2_col_dist, r2_col_scatter = st.columns(2)

    # Left: Most Distinctive Skills (Ranked by Lift)
    with r2_col_dist:
        d_head_col, d_btn_col = st.columns([4, 1])
        with d_head_col:
            st.markdown("##### Most Distinctive Technical Skills")
        with d_btn_col:
            expand_dist_clicked = st.button("⛶ Expand", key="expand_dist")

        is_unselected_dist = effective_dist_cat == "-- Select a Job Family for Distinctiveness --"
        if not is_unselected_dist:
            dist_pop = filter_postings_population(
                postings,
                country=active_c_list,
                category=effective_dist_cat,
                seniority=st.session_state["filter_seniority"],
            )["active_postings"]

            dist_stats = compute_population_skill_stats(
                dist_pop, corpus_skill_counts, corpus_total, vocab
            )
            if active_family != "All Families":
                dist_stats = filter_skills_by_family(dist_stats, active_family)

            st.caption(
                f"**Active Population:** {OCCUPATIONAL_CATEGORIES.get(effective_dist_cat)} in {c_summary} ({len(dist_pop):,} postings) • "
                f"**Baseline:** Entire EU Corpus ({corpus_total:,} postings)"
            )
            fig_dist = build_most_distinctive_bar(
                dist_stats,
                is_unselected_category=False,
                top_n=10,
                height=380,
            )
        else:
            st.caption("Select an occupational role above to benchmark distinctive skills against the corpus baseline.")
            fig_dist = build_most_distinctive_bar(
                [],
                is_unselected_category=True,
                top_n=10,
                height=380,
            )

        if expand_dist_clicked:
            render_expanded_chart_dialog(
                "Most Distinctive Skills",
                fig_dist,
                "Skills uniquely concentrated in the selected occupation relative to the corpus baseline.",
            )

        st.plotly_chart(fig_dist, use_container_width=True)

    # Right: Prevalence vs. Distinctiveness (Lift) Scatter Plot
    with r2_col_scatter:
        s_head_col, s_btn_col = st.columns([4, 1])
        with s_head_col:
            st.markdown("##### Bivariate Demand & Lift Landscape")
        with s_btn_col:
            expand_scatter_clicked = st.button("⛶ Expand", key="expand_scatter")

        is_unselected_scatter = effective_scatter_cat == "-- Select a Job Family for Distinctiveness --"
        if not is_unselected_scatter:
            scatter_pop = filter_postings_population(
                postings,
                country=active_c_list,
                category=effective_scatter_cat,
                seniority=st.session_state["filter_seniority"],
            )["active_postings"]

            scatter_stats = compute_population_skill_stats(
                scatter_pop, corpus_skill_counts, corpus_total, vocab
            )
            if active_family != "All Families":
                scatter_stats = filter_skills_by_family(scatter_stats, active_family)

            scatter_items = prepare_scatter_data(scatter_stats, min_count=1)
            st.caption(
                f"**Active Population:** {OCCUPATIONAL_CATEGORIES.get(effective_scatter_cat)} in {c_summary} ({len(scatter_pop):,} postings) • "
                f"Showing {'all ' + str(len(scatter_items)) + ' detected skills' if show_dense else 'Top 10 qualified distinctive skills'}"
            )
            fig_scatter = build_scatter_figure(
                scatter_items,
                is_unselected_category=False,
                show_dense=show_dense,
                selected_family=active_family,
                height=380,
            )
        else:
            st.caption("Select an occupational role above to explore its bivariate demand-versus-distinctiveness landscape.")
            fig_scatter = build_scatter_figure(
                [],
                is_unselected_category=True,
                show_dense=show_dense,
                selected_family=active_family,
                height=380,
            )

        if expand_scatter_clicked:
            render_expanded_chart_dialog(
                "Bivariate Skill Landscape: Prevalence vs. Distinctiveness",
                fig_scatter,
                "Prevalence on X against role distinctiveness (Lift) on Y relative to corpus parity.",
            )

        st.plotly_chart(fig_scatter, use_container_width=True)

    # =========================================================================
    # ROW 3: European Map + Country Posting Volumes
    # =========================================================================
    st.markdown("---")
    st.subheader("3. European Geographic Distribution & Posting Volumes")
    st.caption("Interactive European job density map paired with country-level posting volume sample sizes.")

    r3_col_map, r3_col_vol = st.columns(2)

    # Calculate active postings per country
    country_counts: Counter[str] = Counter()
    for p in active_postings:
        c = p.get("country")
        if c:
            country_counts[c] += 1

    # Left: European Job Distribution Map
    with r3_col_map:
        head_m, btn_m = st.columns([4, 1])
        with head_m:
            st.markdown("**European Job Distribution Map**")
            st.caption("Click any country on the map to toggle it in the Country multi-select filter.")

        fig_map = build_europe_map_figure(country_counts, selected_countries=active_c_list, height=400)

        with btn_m:
            if st.button("⛶ Expand", key="expand_map"):
                render_expanded_chart_dialog(
                    "European Job Distribution Map",
                    fig_map,
                    "Geographic distribution of postings across EU-27 member states.",
                )

        map_selection = st.plotly_chart(
            fig_map,
            on_select="rerun",
            selection_mode="points",
            key=f"europe_map_{ver}",
            use_container_width=True,
        )

        # Synchronize Map Clicks with Searchable Multi-Select
        if map_selection and map_selection.get("selection", {}).get("points"):
            clicked_pt = map_selection["selection"]["points"][0]
            loc = clicked_pt.get("location")
            clicked_iso2 = ISO3_TO_ISO2.get(loc)
            if clicked_iso2 and clicked_iso2 in EU27_COUNTRIES:
                if st.session_state["_last_clicked_map_country"] != clicked_iso2:
                    st.session_state["_last_clicked_map_country"] = clicked_iso2
                    current_c = list(st.session_state["filter_countries"])
                    if clicked_iso2 in current_c:
                        current_c.remove(clicked_iso2)
                    else:
                        current_c.append(clicked_iso2)
                    st.session_state["filter_countries"] = current_c
                    st.session_state["filter_version"] += 1
                    st.rerun()

    # Right: Country Posting Volume Comparison
    with r3_col_vol:
        head_v, btn_v = st.columns([4, 1])
        with head_v:
            st.markdown("**Country Posting Volumes (Sample Sizes)**")
            st.caption("Matching postings per country (amber bars indicate sample size N < 300).")

        # Build records for selected countries (or top EU countries if all selected)
        if active_c_list:
            vol_country_codes = [c for c in active_c_list if country_counts[c] > 0]
        else:
            vol_country_codes = [c for c, cnt in country_counts.most_common(12)]

        vol_records = []
        for c in vol_country_codes:
            cnt = country_counts[c]
            vol_records.append({
                "iso_code": c,
                "country_name": EU27_COUNTRIES.get(c, c),
                "total_postings": cnt,
                "is_subthreshold": cnt < 300,
            })

        fig_vol = build_country_volume_comparison_bar(vol_records, height=400)

        with btn_v:
            if st.button("⛶ Expand", key="expand_vol"):
                render_expanded_chart_dialog(
                    "Country Posting Volumes",
                    fig_vol,
                    "Observed postings per country across active filter selection.",
                )

        st.plotly_chart(fig_vol, use_container_width=True)

    # =========================================================================
    # ROW 4: Cross-Country Occupational Composition + Corpus Baseline Benchmark
    # =========================================================================
    st.markdown("---")
    st.subheader("4. Cross-Country Composition & Whole-Market Baseline")
    st.caption("Comparing cross-country occupational composition alongside the permanent full-corpus market benchmark.")

    r4_col_comp, r4_col_bench = st.columns(2)

    # Left: Cross-Country Occupational Composition (100% stacked bar)
    with r4_col_comp:
        head_cc, btn_cc = st.columns([4, 1])
        with head_cc:
            st.markdown("**Cross-Country Occupational Composition (% Shares)**")
            st.caption("Preserves the full 5-way occupational mix across countries. Countries with N < 300 are marked with ⚠️.")

        # Compute country composition records across all 5 occupational categories.
        # This chart deliberately ignores global category selection to preserve full 5-way comparison.
        country_postings_all_cats = filter_postings_population(
            postings,
            country=active_c_list,
            category=None,
            seniority=st.session_state["filter_seniority"],
        )["active_postings"]

        # Respect technical skill family filter across the full 5-way occupational mix
        comp_postings = filter_postings_by_skill_family(country_postings_all_cats, active_family, vocab)

        cats_by_country: Dict[str, Counter[str]] = {}
        for p in comp_postings:
            c = p.get("country")
            cat = p.get("category")
            if c and cat:
                cats_by_country.setdefault(c, Counter())[cat] += 1

        country_all_cat_counts = Counter(p.get("country") for p in comp_postings if p.get("country"))

        if active_c_list:
            comp_country_codes = [c for c in active_c_list if country_all_cat_counts.get(c, 0) > 0]
        else:
            comp_country_codes = [c for c, cnt in country_all_cat_counts.items() if cnt >= 300]

        comp_records = []
        for c in comp_country_codes:
            c_counts = cats_by_country.get(c, Counter())
            # Denominator MUST include postings across all 5 job families for this country
            tot = sum(c_counts.values())
            shares = {
                cat_id: round((c_counts[cat_id] / tot) * 100, 1) if tot > 0 else 0.0
                for cat_id in OCCUPATIONAL_CATEGORIES
            }
            comp_records.append({
                "iso_code": c,
                "country_name": EU27_COUNTRIES.get(c, c),
                "total_postings": tot,
                "is_subthreshold": tot < 300,
                "shares": shares,
                "counts": c_counts,
            })

        fig_stacked = build_cross_country_composition_stacked_bar(comp_records, height=400)

        with btn_cc:
            if st.button("⛶ Expand", key="expand_stacked"):
                render_expanded_chart_dialog(
                    "Cross-Country Occupational Composition",
                    fig_stacked,
                    "Percentage breakdown of postings across data occupations by country.",
                )

        st.plotly_chart(fig_stacked, use_container_width=True)
        st.caption(
            "💡 **Why all 5 job families are shown:** A 100% stacked composition chart is designed to compare each country's "
            "internal distribution across all occupational categories. Restricting this chart to a single globally selected job family "
            "would eliminate the cross-occupational comparison and reduce every country to a trivial 100% single-color bar, "
            "making the chart uninformative. Country, seniority, and technical-skill-family filters remain active."
        )

    # Right: Corpus Baseline Benchmark (Unfiltered Market Reference in Indigo)
    with r4_col_bench:
        head_b, btn_b = st.columns([4, 1])
        with head_b:
            st.markdown("**Corpus Baseline Benchmark: Top 10 Skills**")
            st.caption(f"Fixed across all {corpus_total:,} postings in the audited EU data corpus (ignores active filters).")

        market_overview = summary.get("market_overview", {})
        top_corpus = market_overview.get("top_skills_overall", [])
        fig_bench = build_corpus_benchmark_bar(top_corpus, top_n=10, height=400, corpus_total=corpus_total)

        with btn_b:
            if st.button("⛶ Expand", key="expand_bench"):
                render_expanded_chart_dialog(
                    "Corpus Baseline Benchmark",
                    fig_bench,
                    "Top technical skills across the entire EU data corpus baseline.",
                )

        st.plotly_chart(fig_bench, use_container_width=True)

    # =========================================================================
    # 9. Complete Skill Demand Table & Explanatory Notes
    # =========================================================================
    st.markdown("---")

    # A. Complete Skill Demand Table (Clearly visible, full-width)
    st.subheader("📋 Complete Filtered Skill Demand Table")
    st.caption(
        "Comprehensive skill inventory of all detected technical skills in the active selection, "
        "including volume, prevalence, lift, and specific qualification criteria status."
    )

    detected_rows = [s for s in active_skills_stats if s.get("count", 0) >= 1]
    detected_rows.sort(key=lambda s: (-s["count"], s["canonical"]))

    if detected_rows:
        table_records = []
        is_all_cat = st.session_state["filter_category"] == "All Categories"
        for s in detected_rows:
            cnt = s["count"]
            prev_pct = s["prevalence_pct"]
            lift_val = s["lift"]
            is_qual = s.get("is_eligible_distinctive", False)

            if is_qual:
                status_str = "✅ Qualified Distinctive"
            elif is_all_cat and math.isclose(lift_val, 1.0, abs_tol=0.01):
                status_str = "⚪ Baseline Parity (Lift = 1.00)"
            elif lift_val < 1.0:
                status_str = "🔻 Below Corpus Parity (Lift < 1.0)"
            else:
                # Lift >= 1.0 but not qualified: identify exact failed support criterion
                failed_n = cnt < 20
                failed_p = prev_pct < 1.5
                if failed_n and failed_p:
                    status_str = "⚪ Sub-threshold (Low N < 20 & Low P < 1.5%)"
                elif failed_n:
                    status_str = "⚪ Sub-threshold (Low N < 20)"
                elif failed_p:
                    status_str = "⚪ Sub-threshold (Low P < 1.5%)"
                else:
                    status_str = "⚪ Sub-threshold"

            table_records.append({
                "Skill": s["canonical"],
                "Technical Family": s["skill_group"],
                "Postings (N)": cnt,
                "Prevalence (%)": f"{prev_pct:.1f}%",
                "Distinctiveness Lift": f"{lift_val:.2f}×" if lift_val is not None else "—",
                "Qualification Status": status_str,
            })

        st.dataframe(
            table_records,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"Showing all **{len(detected_rows)}** detected technical skills matching the active filter selection. "
            f"The total rows match the **Detected Technical Skills** KPI ({pop_kpis['detected_skills_count']}), "
            f"and skills marked '✅ Qualified Distinctive' ({pop_kpis['qualified_distinctive_count']}) match the "
            f"**Qualified Distinctive Skills** KPI. "
            f"Distinctive qualification requires: **N ≥ 20 postings**, **Prevalence ≥ 1.5%**, and **Lift > 1.00**."
        )
    else:
        st.info("No technical skills detected in the current filter selection.")

    # B. Interpreting Prevalence, Lift, and Support Thresholds
    st.markdown("---")
    st.markdown("### 💡 Interpreting Prevalence, Lift, and Support Thresholds")
    st.info(
        "💡 **Interpreting Prevalence vs. Distinctiveness:**\n\n"
        "- **Within-Selection Prevalence ($P$):** Reflects within-group market demand "
        "(% of postings in the filtered selection requiring the skill):\n"
        "  $$P(\\text{skill} \\mid \\text{selection}) = \\frac{\\text{count}(\\text{skill} \\cap \\text{selection})}{N_{\\text{selection}}}$$\n"
        "- **Distinctiveness Lift:** Measures relative concentration compared to the overall EU data corpus baseline:\n"
        "  $$\\text{Lift} = \\frac{P(\\text{skill} \\mid \\text{selection})}{P(\\text{skill} \\mid \\text{corpus})} = P(\\text{skill} \\mid \\text{selection}) / P(\\text{skill} \\mid \\text{corpus})$$\n"
        "  Lift compares the prevalence of a skill in the selected population with its prevalence in the full EU corpus. "
        "**Lift > 1.00** indicates over-representation (disproportionately characteristic of this role); "
        "**Lift = 1.00** indicates baseline parity with the broader market; "
        "**Lift < 1.00** indicates under-representation relative to the broader data job market. "
        "*(Note: In the All Job Families view, all skills sit at Lift = 1.00 by construction because the active population matches the corpus baseline).*\n"
        "- **Distinctive Eligibility Thresholds:** Solid high-opacity markers indicate qualified distinctive skills "
        "($N \\ge 20$, $P \\ge 1.5\\%$, and $\\text{Lift} > 1.00$). Muted markers indicate sub-threshold skills; "
        "**high lift on a low-count skill indicates uniqueness, not high market demand**.\n"
        "- **Quadrant Classification:**\n"
        "  - *High Prevalence + High Lift (Top-Right):* Role-defining core technologies.\n"
        "  - *High Prevalence + Low Lift (Bottom-Right):* Foundational table-stakes skills (ubiquitous across all data jobs).\n"
        "  - *Low Prevalence + High Lift (Top-Left):* Specialized niche tools (high distinctiveness, narrow volume).\n"
        "  - *Low Prevalence + Low Lift (Bottom-Left):* Peripheral / secondary tools."
    )

    # C. Geographic Scope & N >= 300 Small-Sample Methodology
    st.markdown("### 🌍 Geographic Scope & N ≥ 300 Small-Sample Methodology")
    geo_data = summary.get("geographic", {})
    threshold, eligible_count, excluded_count, eligible_codes_str = get_geographic_note_data(geo_data)
    st.info(
        f"ℹ️ **Geographic Methodology Note:** To prevent small-sample distortions, occupational composition comparisons "
        f"are restricted to the **{eligible_count} EU member states** with at least {threshold} observed postings "
        f"({eligible_codes_str}). The remaining **{excluded_count} EU member states** appear on the European map with their "
        f"raw counts but are flagged with small-sample warnings (⚠️) when inspected in compositional comparisons. When any filter combination "
        f"results in fewer than {threshold} matching postings, a small-sample warning is surfaced to signal caution."
    )

    # 10. Footer
    st.markdown("---")
    st.caption(get_footer_text(corpus_total, snapshot_date))


if __name__ == "__main__":
    main()
