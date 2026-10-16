"""
src/analytics.py

Pure-Python analytical logic for skill extraction, prevalence calculation,
skill distinctiveness (lift), support-based noise filtering, and geographic thresholding.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


# ==============================================================================
# Canonical Occupational Categories (Target FreeHire Classifications)
# ==============================================================================

OCCUPATIONAL_CATEGORIES: Dict[str, str] = {
    "data_analytics": "Data Analytics",
    "data_engineering": "Data Engineering",
    "data_science": "Data Science",
    "ml_ai": "ML/AI",
    "ai_engineering": "AI Engineering",
}

CATEGORY_NAMES: Dict[str, str] = OCCUPATIONAL_CATEGORIES


# ==============================================================================
# Canonical EU-27 Member States (ISO-2 Code to English Common Short Name)
# ==============================================================================
# Note on "Czechia": Standardized on the official English short-form name
# "Czechia" in accordance with the EU Interinstitutional Style Guide and
# ISO 3166-1 (matching the short names used for "Slovakia", "Austria", etc.).
# The precomputed data/processed/analytics_summary.json snapshot retains the
# formal name "Czech Republic" from initial preprocessing without breaking.

EU27_COUNTRIES: Dict[str, str] = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GR": "Greece",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
}

EU_COUNTRIES: Dict[str, str] = EU27_COUNTRIES
EU27_COUNTRY_NAMES: Dict[str, str] = EU27_COUNTRIES


class SkillVocabulary:
    """Encapsulates the controlled technical skill vocabulary with normalized aliases and regexes."""

    def __init__(self, vocab_data: Dict[str, Any]):
        self.skills: List[Dict[str, Any]] = vocab_data.get("skills", [])
        self.alias_to_canonical: Dict[str, str] = {}
        self.compiled_regexes: Dict[str, re.Pattern] = {}

        for entry in self.skills:
            canonical = entry["canonical"]

            # Canonical itself as a lookup key
            self.alias_to_canonical[canonical.lower()] = canonical

            for alias in entry.get("aliases", []):
                self.alias_to_canonical[alias.lower()] = canonical

            pattern_str = entry.get("regex")
            if pattern_str:
                self.compiled_regexes[canonical] = re.compile(pattern_str, re.IGNORECASE)

    @classmethod
    def load_from_file(cls, path: Path | str) -> SkillVocabulary:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)


def extract_skills_from_posting(
    posting: Dict[str, Any],
    vocabulary: SkillVocabulary
) -> Set[str]:
    """
    Extracts canonical skills present in a job posting using a hybrid priority approach:
    1. Match native `skills` tags against canonical terms and normalized aliases.
    2. For vocabulary skills not detected in native tags, evaluate regex patterns
       against the job `description` text.
    
    Each detected skill is counted at most once (binary presence set).
    """
    detected_skills: Set[str] = set()

    # Step 1: Scan native skills tags
    native_tags = posting.get("skills") or []
    for tag in native_tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if cleaned in vocabulary.alias_to_canonical:
            detected_skills.add(vocabulary.alias_to_canonical[cleaned])

    # Step 2: Description regex fallback for vocabulary items not yet detected
    description = posting.get("description") or ""
    if description and isinstance(description, str):
        for canonical, pattern in vocabulary.compiled_regexes.items():
            if canonical not in detected_skills:
                if pattern.search(description):
                    detected_skills.add(canonical)

    return detected_skills


def compute_prevalence(skill_count: int, total_postings: int) -> float:
    """
    Computes job-level skill prevalence:
    P(skill | group) = count(skill in group) / total_postings
    Returns 0.0 if total_postings is 0.
    """
    if total_postings <= 0:
        return 0.0
    return skill_count / total_postings


def compute_lift(category_prevalence: float, corpus_prevalence: float) -> float:
    """
    Computes skill distinctiveness (lift):
    Lift = P(skill | category) / P(skill | corpus)
    Returns 0.0 if corpus_prevalence <= 0 or category_prevalence <= 0.
    """
    if corpus_prevalence <= 0.0 or category_prevalence <= 0.0:
        return 0.0
    return category_prevalence / corpus_prevalence


def filter_distinctive_skills(
    skill_stats: List[Dict[str, Any]],
    min_count: int = 20,
    min_prevalence: float = 0.015,
    min_lift: float = 1.0,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Filters and ranks distinctive skills for an occupational category:
    1. Primary eligibility: count >= min_count AND prevalence >= min_prevalence
    2. Lift threshold: lift > min_lift (strictly greater than 1.0)
    3. Sort in descending order by lift (with prevalence as tie-breaker), returning up to top_n.
    """
    eligible: List[Dict[str, Any]] = []

    for stat in skill_stats:
        count = stat.get("count", 0)
        prevalence = stat.get("prevalence", 0.0)
        lift = stat.get("lift", 0.0)

        # Primary support eligibility rule
        if count >= min_count and prevalence >= min_prevalence:
            # Lift threshold rule: lift > 1.0
            if lift > min_lift:
                eligible.append(stat)

    # Sort descending by lift, then prevalence
    eligible.sort(key=lambda s: (s.get("lift", 0.0), s.get("prevalence", 0.0)), reverse=True)
    return eligible[:top_n]


def filter_eligible_countries(
    country_counts: Dict[str, int],
    threshold: int = 300
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Partitions EU member states into eligible (N >= threshold) and excluded (N < threshold)
    sets for occupational composition comparisons.
    """
    eligible: Dict[str, int] = {}
    excluded: Dict[str, int] = {}

    for country, count in country_counts.items():
        if count >= threshold:
            eligible[country] = count
        else:
            excluded[country] = count

    return eligible, excluded


def compute_category_skill_stats(
    vocabulary: SkillVocabulary,
    category_counts: Dict[str, int],
    category_skill_counts: Dict[str, Dict[str, int]],
    corpus_skill_counts: Dict[str, int],
    total_postings: int,
    categories: Iterable[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Computes prevalence, corpus prevalence, and lift for all skills across specified categories.

    Returns a mapping of category_id -> list of skill stat dictionaries with keys:
    canonical, skill_group, count, prevalence, prevalence_pct, lift.
    """
    stats_by_category: Dict[str, List[Dict[str, Any]]] = {}
    for cat_id in categories:
        cat_total = category_counts.get(cat_id, 0)
        skill_stats: List[Dict[str, Any]] = []
        for skill_entry in vocabulary.skills:
            canonical = skill_entry["canonical"]
            cnt = category_skill_counts.get(cat_id, {}).get(canonical, 0)
            prev = compute_prevalence(cnt, cat_total)
            corpus_prev = compute_prevalence(corpus_skill_counts.get(canonical, 0), total_postings)
            lift = compute_lift(prev, corpus_prev)
            skill_stats.append(
                {
                    "canonical": canonical,
                    "skill_group": skill_entry["category"],
                    "count": cnt,
                    "prevalence": prev,
                    "prevalence_pct": round(prev * 100, 1),
                    "lift": round(lift, 2),
                }
            )
        stats_by_category[cat_id] = skill_stats
    return stats_by_category


def atomic_dump_json(
    obj: Any,
    destination: Path | str,
    *,
    indent: int | None = 2,
    ensure_ascii: bool = False,
) -> None:
    """
    Atomically serialize and write a JSON-serializable object to destination.

    1. Ensures destination directory exists.
    2. Writes JSON to a collision-free temporary file in the destination directory.
    3. Flushes, syncs, and closes the temporary file before replacement.
    4. Replaces destination with the temporary file atomically via Path.replace().
    5. On any serialization, write, or replacement error, cleans up the temporary
       file and preserves any existing destination file without truncation.
    """
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(temp_file.name)
    try:
        json.dump(obj, temp_file, indent=indent, ensure_ascii=ensure_ascii)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        temp_path.replace(dest)
    except BaseException:
        try:
            temp_file.close()
        except Exception:
            pass
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise
