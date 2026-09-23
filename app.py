"""
app.py

Interactive single-page Streamlit web dashboard for:
EU Data Jobs & Technical Skill Demand Analysis

Renders precomputed metrics from data/processed/analytics_summary.json:
- KPI summary cards
- Market overview (occupational composition and corpus top skills)
- Category profiles (side-by-side prevalence vs. lift ranked bars)
- Geographic distribution (EU-27 choropleth map & N >= 300 composition comparison)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "data" / "processed" / "analytics_summary.json"

st.set_page_config(
    page_title="EU Data Jobs & Skill Demand",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_analytics_summary() -> Dict[str, Any]:
    """Loads the precomputed analytics summary JSON."""
    if not DATA_PATH.exists():
        st.error(f"Missing precomputed data at `{DATA_PATH}`. Please run `python scripts/preprocess.py` first.")
        st.stop()
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    data = load_analytics_summary()
    kpis = data.get("kpis", {})
    overview = data.get("market_overview", {})
    categories = data.get("category_profiles", {})
    geographic = data.get("geographic", {})

    # =========================================================================
    # Header & Introduction
    # =========================================================================
    st.title("🇪🇺 EU Data Jobs & Technical Skill Demand Analysis")
    st.markdown(
        """
        An empirical analysis of technical skill demand across data-related occupations and EU-27 member states,
        based on an audited snapshot of **22,985 FreeHire job postings**.
        """
    )

    st.markdown("---")

    # =========================================================================
    # High-Level KPI Cards
    # =========================================================================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Total Postings",
            value=f"{kpis.get('total_postings', 0):,}",
            help="Total audited unique job postings across the EU-27 snapshot.",
        )
    with col2:
        st.metric(
            label="EU-27 Member States",
            value=kpis.get("total_countries", 27),
            help="Observed job postings spanning all 27 EU member states.",
        )
    with col3:
        st.metric(
            label="Occupational Categories",
            value=kpis.get("total_categories", 5),
            help="Target FreeHire occupational classifications.",
        )
    with col4:
        st.metric(
            label="Seniority Reported",
            value=f"{kpis.get('seniority_coverage_pct', 0.0)}%",
            help="Native FreeHire seniority metadata coverage (reported descriptively; no imputation or filtering).",
        )

    st.markdown("---")

    # =========================================================================
    # Section 1: Market Overview & Corpus Structure
    # =========================================================================
    st.header("1. Labour Market Overview & Corpus Composition")
    st.caption("Distribution of occupational categories and baseline skill demand across the audited EU corpus.")

    col_overview_left, col_overview_right = st.columns([1, 1])

    with col_overview_left:
        st.subheader("Occupational Composition")
        cat_shares = overview.get("category_shares", [])
        if cat_shares:
            cat_names = [c["category_name"] for c in reversed(cat_shares)]
            cat_counts = [c["count"] for c in reversed(cat_shares)]
            cat_labels = [f"{c['count']:,} ({c['share_pct']}%)" for c in reversed(cat_shares)]

            fig_comp = go.Figure(
                go.Bar(
                    x=cat_counts,
                    y=cat_names,
                    orientation="h",
                    text=cat_labels,
                    textposition="auto",
                    marker=dict(color="#3b82f6"),
                )
            )
            fig_comp.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Observed Postings",
                height=320,
                xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

    with col_overview_right:
        st.subheader("Top Skills Across the Entire Corpus")
        top_corpus = overview.get("top_skills_overall", [])[:10]
        if top_corpus:
            skill_names = [s["skill"] for s in reversed(top_corpus)]
            skill_prev = [s["prevalence_pct"] for s in reversed(top_corpus)]
            skill_labels = [f"{s['prevalence_pct']}%" for s in reversed(top_corpus)]

            fig_corpus = go.Figure(
                go.Bar(
                    x=skill_prev,
                    y=skill_names,
                    orientation="h",
                    text=skill_labels,
                    textposition="auto",
                    marker=dict(color="#64748b"),
                )
            )
            fig_corpus.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Corpus Prevalence (% of all postings)",
                height=320,
                xaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, max(skill_prev) * 1.15 if skill_prev else 100]),
            )
            st.plotly_chart(fig_corpus, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # Section 2: Occupational Skill Profiles & Distinctiveness
    # =========================================================================
    st.header("2. Occupational Skill Profiles: Demand vs. Distinctiveness")
    st.caption("Contrasting high-volume table-stakes skills with role-defining technical markers.")

    # Occupational Category Selector
    category_keys = list(categories.keys())
    category_options = {k: categories[k]["category_name"] for k in category_keys}

    selected_cat_id = st.selectbox(
        "Select Occupational Category:",
        options=category_keys,
        format_func=lambda k: category_options.get(k, k),
        index=0,
    )

    cat_profile = categories.get(selected_cat_id, {})
    total_cat_postings = cat_profile.get("total_postings", 0)

    st.markdown(
        f"**Profile for {cat_profile.get('category_name', selected_cat_id)}** "
        f"(`{total_cat_postings:,}` postings, "
        f"{round((total_cat_postings / kpis.get('total_postings', 1)) * 100, 1)}% of corpus)"
    )

    col_cat_left, col_cat_right = st.columns(2)

    # Left: Top In-Demand Skills (Prevalence)
    with col_cat_left:
        st.subheader("Top In-Demand Skills")
        st.caption("Most frequent technical skills (% of postings in this category).")

        top_in_demand = cat_profile.get("top_in_demand", [])[:10]
        if top_in_demand:
            names = [s["canonical"] for s in reversed(top_in_demand)]
            prevs = [s["prevalence_pct"] for s in reversed(top_in_demand)]
            labels = [f"{s['prevalence_pct']}% ({s['count']:,} jobs)" for s in reversed(top_in_demand)]

            fig_in_demand = go.Figure(
                go.Bar(
                    x=prevs,
                    y=names,
                    orientation="h",
                    text=labels,
                    textposition="auto",
                    marker=dict(color="#2563eb"),
                )
            )
            max_p = max(prevs) if prevs else 100
            fig_in_demand.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Prevalence (%)",
                height=380,
                xaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, max_p * 1.25]),
            )
            st.plotly_chart(fig_in_demand, use_container_width=True)

    # Right: Most Distinctive Skills (Lift)
    with col_cat_right:
        st.subheader("Most Distinctive Skills")
        st.caption("Skills uniquely concentrated here vs. the corpus (Lift > 1.0, N ≥ 20, Prev ≥ 1.5%).")

        top_distinctive = cat_profile.get("top_distinctive", [])[:10]
        if top_distinctive:
            dist_names = [s["canonical"] for s in reversed(top_distinctive)]
            lifts = [s["lift"] for s in reversed(top_distinctive)]
            dist_labels = [f"{s['lift']}× ({s['prevalence_pct']}%)" for s in reversed(top_distinctive)]

            fig_distinctive = go.Figure(
                go.Bar(
                    x=lifts,
                    y=dist_names,
                    orientation="h",
                    text=dist_labels,
                    textposition="auto",
                    marker=dict(color="#059669"),
                )
            )
            max_l = max(lifts) if lifts else 2.0
            fig_distinctive.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="Distinctiveness Lift (× baseline)",
                height=380,
                xaxis=dict(showgrid=True, gridcolor="#e2e8f0", range=[0, max_l * 1.25]),
            )
            st.plotly_chart(fig_distinctive, use_container_width=True)
        else:
            st.info("No skills met the minimum support criteria ($N \\ge 20$ and $P \\ge 1.5\\%$) with Lift > 1.0.")

    st.markdown("---")

    # =========================================================================
    # Section 3: Geographic Distribution (EU-27)
    # =========================================================================
    st.header("3. Geographic Scope & Occupational Composition")
    st.caption("Postings mapped across EU-27 member states and composition comparison for countries with N ≥ 300.")

    col_geo_left, col_geo_right = st.columns([1, 1])

    # Left: EU-27 Choropleth Map
    with col_geo_left:
        st.subheader("EU-27 Job Posting Volume")
        map_records = geographic.get("country_map", [])

        if map_records:
            # Map iso2 to iso3 for plotly choropleth
            iso2_to_iso3 = {
                "AT": "AUT", "BE": "BEL", "BG": "BGR", "CY": "CYP", "CZ": "CZE",
                "DE": "DEU", "DK": "DNK", "EE": "EST", "ES": "ESP", "FI": "FIN",
                "FR": "FRA", "GR": "GRC", "HR": "HRV", "HU": "HUN", "IE": "IRL",
                "IT": "ITA", "LT": "LTU", "LU": "LUX", "LV": "LVA", "MT": "MLT",
                "NL": "NLD", "PL": "POL", "PT": "PRT", "RO": "ROU", "SE": "SWE",
                "SI": "SVN", "SK": "SVK",
            }
            map_data = []
            for r in map_records:
                code = r["iso_code"]
                iso3 = iso2_to_iso3.get(code)
                if iso3:
                    map_data.append({
                        "iso3": iso3,
                        "iso2": code,
                        "country": r["country_name"],
                        "postings": r["postings"],
                        "eligible": "Eligible (N ≥ 300)" if r["eligible"] else "Excluded (< 300)",
                    })

            fig_map = px.choropleth(
                map_data,
                locations="iso3",
                color="postings",
                hover_name="country",
                hover_data={"iso3": False, "postings": ":,", "eligible": True},
                color_continuous_scale="Blues",
                labels={"postings": "Postings"},
            )
            fig_map.update_geos(
                scope="europe",
                showcountries=True,
                countrycolor="#cbd5e1",
                showcoastlines=True,
                coastlinecolor="#cbd5e1",
                center=dict(lat=52.5, lon=14.0),
                projection_scale=3.5,
            )
            fig_map.update_layout(
                margin=dict(l=0, r=0, t=10, b=10),
                height=420,
                coloraxis_colorbar=dict(title="Postings", len=0.7),
            )
            st.plotly_chart(fig_map, use_container_width=True)

    # Right: 100% Stacked Bar Chart for N >= 300 Countries
    with col_geo_right:
        st.subheader("Occupational Composition (Countries with N ≥ 300)")
        comp_records = geographic.get("composition_eligible", [])

        if comp_records:
            countries_order = [r["iso_code"] for r in reversed(comp_records)]
            fig_stacked = go.Figure()

            palette = {
                "data_engineering": "#3b82f6",
                "data_analytics": "#10b981",
                "ai_engineering": "#8b5cf6",
                "data_science": "#f59e0b",
                "ml_ai": "#ec4899",
            }

            for cat_id, cat_name in [
                ("data_engineering", "Data Engineering"),
                ("data_analytics", "Data Analytics"),
                ("ai_engineering", "AI Engineering"),
                ("data_science", "Data Science"),
                ("ml_ai", "ML/AI"),
            ]:
                shares = [
                    r["categories"].get(cat_id, {}).get("share_pct", 0.0)
                    for r in reversed(comp_records)
                ]
                fig_stacked.add_trace(
                    go.Bar(
                        name=cat_name,
                        y=countries_order,
                        x=shares,
                        orientation="h",
                        marker=dict(color=palette.get(cat_id, "#94a3b8")),
                        hovertemplate=f"<b>%{{y}}</b> - {cat_name}: %{{x}}%<extra></extra>",
                    )
                )

            fig_stacked.update_layout(
                barmode="stack",
                xaxis_title="Share of Country's Postings (%)",
                yaxis_title="Member State",
                height=420,
                margin=dict(l=20, r=20, t=10, b=10),
                xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#e2e8f0"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_stacked, use_container_width=True)

    # Contextual note for excluded countries
    st.info(
        "ℹ️ **Geographic Threshold Note:** To prevent small-sample distortions, occupational composition comparisons "
        "are restricted to the **12 member states** with at least 300 observed postings (ES, FR, PL, NL, DE, IT, IE, "
        "DK, PT, SE, FI, BE). The remaining **15 EU countries** appear on the map with their raw counts but are "
        "excluded from the compositional breakdown."
    )

    st.markdown("---")
    st.caption(
        "EU Data Jobs & Skill Demand Analysis • Built with Python & Streamlit • Data Source: FreeHire snapshot (22,985 postings)"
    )


if __name__ == "__main__":
    main()

