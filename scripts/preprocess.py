"""
scripts/preprocess.py

Offline batch preprocessing script that:
1. Loads the frozen FreeHire snapshot (data/raw/freehire_eu_raw.json).
2. Executes controlled hybrid skill extraction via src/analytics.py.
3. Computes corpus-wide, category-specific, and geographic metrics.
4. Serializes the final precomputed artifact to data/processed/analytics_summary.json.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.analytics import (
    EU27_COUNTRIES,
    OCCUPATIONAL_CATEGORIES,
    SkillVocabulary,
    atomic_dump_json,
    compute_category_skill_stats,
    compute_lift,
    compute_prevalence,
    extract_skills_from_posting,
    filter_distinctive_skills,
    filter_eligible_countries,
)

CATEGORY_NAMES: Dict[str, str] = OCCUPATIONAL_CATEGORIES
EU27_COUNTRY_NAMES: Dict[str, str] = EU27_COUNTRIES


def validate_posting_provenance(
    posting: dict,
    index: int | None = None,
) -> tuple[str, str]:
    """
    Validates that a posting contains valid _collection_category and _collection_country
    provenance matching canonical CATEGORY_NAMES and EU27_COUNTRY_NAMES.

    Raises ValueError with diagnostic context if provenance is missing or invalid.
    Returns (category, country).
    """
    if not isinstance(posting, dict):
        prefix = f"Posting at index {index}" if index is not None else "Posting"
        raise ValueError(f"{prefix} is not a valid dictionary (type: {type(posting).__name__}).")

    ident = (
        posting.get("id")
        or posting.get("public_slug")
        or posting.get("slug")
        or (posting.get("title")[:50] if isinstance(posting.get("title"), str) else None)
        or "unknown_id"
    )
    prefix = f"Posting at index {index} (id: {ident!r})" if index is not None else f"Posting (id: {ident!r})"

    cat = posting.get("_collection_category")
    if cat is None or cat == "":
        raise ValueError(f"{prefix} is missing required '_collection_category'.")
    if not isinstance(cat, str):
        raise ValueError(
            f"{prefix} has invalid '_collection_category': {cat!r}. "
            f"Expected one of: {sorted(CATEGORY_NAMES.keys())}."
        )
    if cat not in CATEGORY_NAMES:
        raise ValueError(
            f"{prefix} has invalid '_collection_category': {cat!r}. "
            f"Expected one of: {sorted(CATEGORY_NAMES.keys())}."
        )

    country = posting.get("_collection_country")
    if country is None or country == "":
        raise ValueError(f"{prefix} is missing required '_collection_country'.")
    if not isinstance(country, str):
        raise ValueError(
            f"{prefix} has invalid '_collection_country': {country!r}. "
            f"Expected one of: {sorted(EU27_COUNTRY_NAMES.keys())}."
        )
    if country not in EU27_COUNTRY_NAMES:
        raise ValueError(
            f"{prefix} has invalid '_collection_country': {country!r}. "
            f"Expected one of: {sorted(EU27_COUNTRY_NAMES.keys())}."
        )

    return cat, country


def extract_snapshot_timestamp(
    metadata_path: Path | str | None,
    total_postings: int,
) -> str | None:
    """
    Extracts and validates collection_timestamp_utc from collection metadata.
    Ensures metadata['unique_jobs'] is an integer equal to total_postings and that
    the timestamp contains an explicit timezone offset.

    Returns the ISO-8601 timestamp string if valid, or None if missing, mismatched,
    naive, or malformed.
    """
    if metadata_path is None:
        return None
    path = Path(metadata_path)
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if not isinstance(metadata, dict):
            return None

        # Validate unique_jobs integer matching total_postings (reject booleans)
        unique_jobs = metadata.get("unique_jobs")
        if isinstance(unique_jobs, bool) or not isinstance(unique_jobs, int):
            return None
        if unique_jobs != total_postings:
            return None

        ts = metadata.get("collection_timestamp_utc")
        if not isinstance(ts, str) or not ts.strip():
            return None

        dt = datetime.fromisoformat(ts.strip())
        if dt.tzinfo is None:
            return None  # Reject timestamps without explicit timezone information
        if not (1900 <= dt.year <= 2100):
            return None
        return ts.strip()
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return None


def preprocess(
    raw_data_path: Path | str,
    vocab_path: Path | str,
    output_path: Path | str,
    metadata_path: Path | str | None = None,
) -> None:
    raw_data_path = Path(raw_data_path)
    vocab_path = Path(vocab_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading vocabulary from {vocab_path}...")
    vocabulary = SkillVocabulary.load_from_file(vocab_path)
    print(f"Loaded {len(vocabulary.skills)} canonical skills across 5 domains.")

    print(f"Loading raw snapshot from {raw_data_path}...")
    start_time = time.time()
    with open(raw_data_path, "r", encoding="utf-8") as f:
        postings = json.load(f)
    total_postings = len(postings)
    print(f"Loaded {total_postings} postings in {time.time() - start_time:.2f}s.")

    meta_file = Path(metadata_path) if metadata_path is not None else raw_data_path.parent / "collection_metadata_eu.json"
    snapshot_collected_at = extract_snapshot_timestamp(meta_file, total_postings=total_postings)

    # Counters
    seniority_count = 0
    category_counts = Counter()
    country_counts = Counter()
    country_category_counts = defaultdict(Counter)
    corpus_skill_counts = Counter()
    category_skill_counts = defaultdict(Counter)

    print("Executing hybrid skill extraction across postings...")
    extract_start = time.time()
    for i, posting in enumerate(postings):
        cat, country = validate_posting_provenance(posting, index=i)

        category_counts[cat] += 1
        country_counts[country] += 1
        country_category_counts[country][cat] += 1

        # Check seniority metadata
        sen = posting.get("seniority")
        if not sen and isinstance(posting.get("enrichment"), dict):
            sen = posting["enrichment"].get("seniority")
        if sen:
            seniority_count += 1

        # Extract skills
        skills = extract_skills_from_posting(posting, vocabulary)
        for skill in skills:
            corpus_skill_counts[skill] += 1
            category_skill_counts[cat][skill] += 1

        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{total_postings} postings...")

    print(f"Extraction completed in {time.time() - extract_start:.2f}s.")

    # 1. Corpus KPIs
    seniority_coverage_pct = (seniority_count / total_postings) * 100 if total_postings else 0.0

    kpis = {
        "total_postings": total_postings,
        "total_countries": len([c for c in country_counts if c in EU27_COUNTRY_NAMES]),
        "total_categories": len([c for c in category_counts if c in CATEGORY_NAMES]),
        "seniority_coverage_count": seniority_count,
        "seniority_coverage_pct": round(seniority_coverage_pct, 1),
    }

    # 2. Market Overview: Category shares and Corpus Top Skills
    category_shares = []
    for cat_id, cat_name in CATEGORY_NAMES.items():
        cnt = category_counts.get(cat_id, 0)
        category_shares.append({
            "category_id": cat_id,
            "category_name": cat_name,
            "count": cnt,
            "share_pct": round((cnt / total_postings) * 100, 1) if total_postings else 0.0,
        })
    category_shares.sort(key=lambda x: x["count"], reverse=True)

    corpus_top_skills = []
    for skill_entry in vocabulary.skills:
        canonical = skill_entry["canonical"]
        cnt = corpus_skill_counts.get(canonical, 0)
        prev = compute_prevalence(cnt, total_postings)
        corpus_top_skills.append({
            "skill": canonical,
            "skill_group": skill_entry["category"],
            "count": cnt,
            "prevalence": prev,
            "prevalence_pct": round(prev * 100, 1),
        })
    corpus_top_skills.sort(key=lambda x: x["prevalence"], reverse=True)

    # 3. Category Profiles (Prevalence and Lift per Category)
    all_skills_by_cat = compute_category_skill_stats(
        vocabulary=vocabulary,
        category_counts=category_counts,
        category_skill_counts=category_skill_counts,
        corpus_skill_counts=corpus_skill_counts,
        total_postings=total_postings,
        categories=CATEGORY_NAMES.keys(),
    )

    category_profiles = {}
    for cat_id, cat_name in CATEGORY_NAMES.items():
        cat_total = category_counts.get(cat_id, 0)
        skill_stats = all_skills_by_cat[cat_id]

        # Top In-Demand: Top 10 by prevalence
        in_demand = sorted(skill_stats, key=lambda s: s["prevalence"], reverse=True)[:10]

        # Top Distinctive: Filtered by N >= 20 and Prev >= 1.5%, ranked by Lift > 1.0
        distinctive = filter_distinctive_skills(
            skill_stats,
            min_count=20,
            min_prevalence=0.015,
            min_lift=1.0,
            top_n=10,
        )

        category_profiles[cat_id] = {
            "category_id": cat_id,
            "category_name": cat_name,
            "total_postings": cat_total,
            "top_in_demand": in_demand,
            "top_distinctive": distinctive,
            "all_skills": skill_stats,
        }

    # 4. Geographic Scope
    eligible_countries, excluded_countries = filter_eligible_countries(country_counts, threshold=300)

    # Map dataset (all 27 EU member states)
    country_map_data = []
    for code, full_name in EU27_COUNTRY_NAMES.items():
        cnt = country_counts.get(code, 0)
        country_map_data.append({
            "iso_code": code,
            "country_name": full_name,
            "postings": cnt,
            "eligible": code in eligible_countries,
        })
    country_map_data.sort(key=lambda x: x["postings"], reverse=True)

    # Composition dataset for eligible countries (N >= 300)
    composition_data = []
    for code in sorted(eligible_countries.keys(), key=lambda c: country_counts[c], reverse=True):
        c_total = country_counts[code]
        cat_breakdown = {}
        for cat_id, cat_name in CATEGORY_NAMES.items():
            cnt = country_category_counts[code].get(cat_id, 0)
            cat_breakdown[cat_id] = {
                "category_name": cat_name,
                "count": cnt,
                "share_pct": round((cnt / c_total) * 100, 1) if c_total else 0.0,
            }
        composition_data.append({
            "iso_code": code,
            "country_name": EU27_COUNTRY_NAMES[code],
            "total_postings": c_total,
            "categories": cat_breakdown,
        })

    # Assemble summary document
    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "snapshot_collected_at": snapshot_collected_at,
        "kpis": kpis,
        "market_overview": {
            "category_shares": category_shares,
            "top_skills_overall": corpus_top_skills[:15],
        },
        "category_profiles": category_profiles,
        "geographic": {
            "threshold": 300,
            "eligible_count": len(eligible_countries),
            "excluded_count": len(excluded_countries),
            "country_map": country_map_data,
            "composition_eligible": composition_data,
            "excluded_countries": [
                {"iso_code": c, "country_name": EU27_COUNTRY_NAMES.get(c, c), "postings": country_counts[c]}
                for c in sorted(excluded_countries.keys(), key=lambda x: country_counts[x], reverse=True)
            ],
        },
    }

    print(f"Serializing analytics summary to {output_path}...")
    atomic_dump_json(summary, output_path, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"Successfully generated {output_path} ({size_kb:.1f} KB).")


if __name__ == "__main__":
    raw_path = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
    fixtures_path = ROOT_DIR / "data" / "fixtures" / "skills_vocabulary.json"
    processed_path = ROOT_DIR / "data" / "processed" / "analytics_summary.json"
    metadata_path = ROOT_DIR / "data" / "raw" / "collection_metadata_eu.json"

    preprocess(raw_path, fixtures_path, processed_path, metadata_path=metadata_path)

