"""
src/analytics.py

Pure-Python analytical logic for skill extraction, prevalence calculation,
skill distinctiveness (lift), support-based noise filtering, and geographic thresholding.
"""

from __future__ import annotations

from collections import Counter
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple


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


# ==============================================================================
# Canonical Technical Skill Families (Domains)
# ==============================================================================

SKILL_FAMILIES: Tuple[str, ...] = (
    "Programming languages",
    "Databases & data warehouses",
    "BI & visualization",
    "Cloud & infrastructure",
    "ML/AI frameworks & tools",
)


# ==============================================================================
# Canonical Seniority Levels & Display Labels
# ==============================================================================

SENIORITY_LEVELS: Tuple[str, ...] = (
    "senior",
    "middle",
    "junior",
    "lead",
    "staff",
    "principal",
    "intern",
    "c_level",
)

SENIORITY_DISPLAY_NAMES: Dict[str, str] = {
    "senior": "Senior",
    "middle": "Mid-level",
    "junior": "Junior",
    "lead": "Lead",
    "staff": "Staff",
    "principal": "Principal",
    "intern": "Intern",
    "c_level": "C-Level",
}


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


def filter_skills_by_family(
    skills: Iterable[Dict[str, Any]],
    family: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Filters a collection of skill dictionaries by their skill_group.

    If family is None, 'All Families', or 'all' (case-insensitive), returns all valid skills.
    If family is one of SKILL_FAMILIES, returns skills where skill_group matches.
    Raises ValueError if family is unrecognized.
    """
    if skills is None:
        return []

    valid_skills = [s for s in skills if isinstance(s, dict)]
    if family is None or (isinstance(family, str) and family.strip().lower() in ("all families", "all")):
        return valid_skills

    if not isinstance(family, str) or family not in SKILL_FAMILIES:
        raise ValueError(
            f"Unrecognized skill family: {family!r}. Expected one of {SKILL_FAMILIES} or 'All Families'."
        )

    return [s for s in valid_skills if s.get("skill_group") == family]


def rank_in_demand_skills(
    skills: Iterable[Dict[str, Any]],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Ranks skills by within-category demand (prevalence descending, count descending).
    Returns up to top_n skill records.
    """
    if skills is None:
        return []

    valid = [
        s for s in skills
        if isinstance(s, dict) and not isinstance(s.get("prevalence"), bool) and isinstance(s.get("prevalence"), (int, float)) and math.isfinite(s["prevalence"])
    ]
    valid.sort(key=lambda s: (-float(s.get("prevalence", 0.0)), -int(s.get("count") or 0), str(s.get("canonical") or "")))
    return valid[:top_n]


def rank_distinctive_skills(
    skills: Iterable[Dict[str, Any]],
    top_n: int = 10,
    min_count: int = 20,
    min_prevalence: float = 0.015,
    min_lift: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Filters and ranks distinctive skills from a collection of skill dictionaries.
    Enforces count >= min_count, prevalence >= min_prevalence, and lift > min_lift.
    Returns up to top_n skill records ranked descending by lift (then prevalence).
    """
    if skills is None:
        return []
    valid = [s for s in skills if isinstance(s, dict)]
    return filter_distinctive_skills(
        valid,
        min_count=min_count,
        min_prevalence=min_prevalence,
        min_lift=min_lift,
        top_n=top_n,
    )


def prepare_scatter_data(
    skills: Iterable[Dict[str, Any]],
    min_count: int = 1,
    min_distinctive_count: int = 20,
    min_distinctive_prevalence: float = 0.015,
    min_distinctive_lift: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Prepares skill records for the 2D prevalence-versus-lift scatter plot.

    - Excludes unobserved skills (count < min_count, default 1).
    - Excludes records with missing, non-numeric, or non-finite lift.
    - Flags distinctive eligibility (count >= 20, prevalence >= 1.5%, lift > 1.0).
    - Generates human-readable support status strings for tooltips.
    - Computes dynamically scaled marker sizes (8px to 22px) and marker opacity.
    - Returns formatted records sorted descending by lift, then prevalence.
    """
    if skills is None:
        return []

    candidates: List[Dict[str, Any]] = []
    for s in skills:
        if not isinstance(s, dict):
            continue

        count = s.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < min_count:
            continue

        lift = s.get("lift")
        if (
            lift is None
            or isinstance(lift, bool)
            or not isinstance(lift, (int, float))
            or math.isnan(lift)
            or math.isinf(lift)
            or lift < 0.0
        ):
            continue

        prevalence = s.get("prevalence", 0.0)
        if (
            not isinstance(prevalence, (int, float))
            or isinstance(prevalence, bool)
            or math.isnan(prevalence)
            or math.isinf(prevalence)
            or prevalence < 0.0
        ):
            continue

        prevalence_pct = s.get("prevalence_pct")
        if prevalence_pct is None:
            prevalence_pct = round(prevalence * 100.0, 1)
        elif (
            isinstance(prevalence_pct, bool)
            or not isinstance(prevalence_pct, (int, float))
            or not math.isfinite(prevalence_pct)
            or prevalence_pct < 0.0
        ):
            continue
        else:
            prevalence_pct = round(float(prevalence_pct), 1)

        is_eligible = (
            count >= min_distinctive_count
            and prevalence >= min_distinctive_prevalence
            and lift > min_distinctive_lift
        )

        if is_eligible:
            support_status = "Qualified Distinctive (N ≥ 20, Prev ≥ 1.5%)"
        elif count < min_distinctive_count:
            support_status = f"Low support (N < {min_distinctive_count})"
        elif prevalence < min_distinctive_prevalence:
            support_status = f"Sub-threshold prevalence (Prev < {min_distinctive_prevalence * 100:.1f}%)"
        else:
            support_status = f"Below baseline parity (Lift ≤ {min_distinctive_lift:.1f})"

        canonical = str(s.get("canonical", "Unknown"))
        skill_group = str(s.get("skill_group", "Other"))

        candidates.append(
            {
                "canonical": canonical,
                "skill_group": skill_group,
                "count": count,
                "prevalence": float(prevalence),
                "prevalence_pct": prevalence_pct,
                "lift": float(lift),
                "is_eligible_distinctive": is_eligible,
                "support_status": support_status,
            }
        )

    if not candidates:
        return []

    max_count = max(item["count"] for item in candidates)
    if max_count <= 0:
        max_count = 1

    for item in candidates:
        item["marker_size"] = round(8.0 + 14.0 * (item["count"] / max_count), 1)
        item["marker_opacity"] = 1.0 if item["is_eligible_distinctive"] else 0.45

    candidates.sort(key=lambda item: (-item["lift"], -item["prevalence_pct"], item["canonical"]))
    return candidates


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


def extract_posting_record(
    posting: Dict[str, Any],
    vocabulary: SkillVocabulary | None = None,
) -> Dict[str, Any]:
    """
    Extracts a normalized, lightweight posting record containing id, country, category,
    seniority, and canonical skill tags.
    """
    if not isinstance(posting, dict):
        return {"id": "", "country": None, "category": None, "seniority": None, "skills": set()}

    ident = (
        posting.get("id")
        or posting.get("public_slug")
        or posting.get("slug")
        or ""
    )

    country = posting.get("_collection_country")
    category = posting.get("_collection_category")

    sen = posting.get("seniority")
    if not sen and isinstance(posting.get("enrichment"), dict):
        sen = posting["enrichment"].get("seniority")
    if sen and not isinstance(sen, str):
        sen = None
    elif isinstance(sen, str):
        sen = sen.strip().lower()
        if sen not in SENIORITY_LEVELS:
            sen = None

    detected_skills: Set[str] = set()
    if vocabulary is not None:
        detected_skills = extract_skills_from_posting(posting, vocabulary)

    return {
        "id": str(ident) if ident else "",
        "country": country if isinstance(country, str) and country.strip() else None,
        "category": category if isinstance(category, str) and category.strip() else None,
        "seniority": sen,
        "skills": detected_skills,
    }


def filter_postings_population(
    postings: list[Dict[str, Any]],
    country: str | Sequence[str] | None = None,
    category: str | None = None,
    seniority: str | None = None,
) -> Dict[str, Any]:
    """
    Applies global filters to establish the analytical population.

    Computes:
    - pre-seniority baseline (matching country/countries and category)
    - baseline postings count and known seniority coverage with explicit denominator
    - active population (matching country/countries, category, and seniority)

    Returns dictionary with:
    - baseline_postings: list of postings matching country & category
    - baseline_count: total postings in pre-seniority baseline
    - known_seniority_count: postings in baseline with non-null seniority
    - seniority_coverage_pct: percentage of baseline with reported seniority
    - active_postings: postings in final filtered analytical population
    - active_count: count of postings in active population
    """
    country_set: set[str] | None = None
    if country and country not in ("All", "All Countries"):
        if isinstance(country, str):
            country_set = {country}
        elif isinstance(country, (list, tuple, set)):
            country_set = set(c for c in country if c and c not in ("All", "All Countries"))
            if not country_set:
                country_set = None

    baseline: list[Dict[str, Any]] = []
    for p in postings:
        if country_set is not None:
            if p.get("country") not in country_set:
                continue
        if category and category not in ("All", "All Categories"):
            if p.get("category") != category:
                continue
        baseline.append(p)

    baseline_count = len(baseline)
    known_seniority_count = sum(1 for p in baseline if p.get("seniority") is not None)
    seniority_coverage_pct = (
        round((known_seniority_count / baseline_count) * 100, 1)
        if baseline_count > 0
        else 0.0
    )

    if seniority and seniority not in ("All", "All Seniorities"):
        active = [p for p in baseline if p.get("seniority") == seniority]
    else:
        active = baseline

    return {
        "baseline_postings": baseline,
        "baseline_count": baseline_count,
        "known_seniority_count": known_seniority_count,
        "seniority_coverage_pct": seniority_coverage_pct,
        "active_postings": active,
        "active_count": len(active),
    }


def compute_population_kpis(
    active_postings: list[Dict[str, Any]],
    corpus_total: int,
    active_skills_stats: list[Dict[str, Any]],
    selected_countries_count: int | None = None,
) -> Dict[str, Any]:
    """
    Computes four core dashboard KPIs from the active analytical population.
    """
    active_count = len(active_postings)
    represented_countries = len(set(p["country"] for p in active_postings if p.get("country")))
    if active_skills_stats and any("count" in s for s in active_skills_stats):
        distinct_skills_count = sum(1 for s in active_skills_stats if s.get("count", 0) >= 1)
    else:
        distinct_skills_count = len(set(s for p in active_postings for s in p.get("skills", set())))

    qualified_skills_count = sum(
        1 for s in active_skills_stats
        if s.get("is_eligible_distinctive", False)
    )

    corpus_share_pct = (
        round((active_count / corpus_total) * 100, 1)
        if corpus_total > 0
        else 0.0
    )

    return {
        "active_postings_count": active_count,
        "corpus_share_pct": corpus_share_pct,
        "represented_countries_count": represented_countries,
        "selected_countries_count": selected_countries_count if selected_countries_count is not None else 27,
        "detected_skills_count": distinct_skills_count,
        "qualified_distinctive_count": qualified_skills_count,
    }


def compute_population_skill_stats(
    active_postings: list[Dict[str, Any]],
    corpus_skill_counts: Dict[str, int],
    corpus_total: int,
    vocabulary: SkillVocabulary,
) -> list[Dict[str, Any]]:
    """
    Computes frequency, prevalence, corpus baseline comparison, and Lift for all
    canonical skills in the active population.
    """
    active_total = len(active_postings)
    skill_counts: Counter[str] = Counter()
    for p in active_postings:
        for skill in p.get("skills", set()):
            skill_counts[skill] += 1

    stats: list[Dict[str, Any]] = []
    for skill_entry in vocabulary.skills:
        canonical = skill_entry["canonical"]
        group = skill_entry["category"]
        cnt = skill_counts.get(canonical, 0)

        prev = compute_prevalence(cnt, active_total)
        corpus_cnt = corpus_skill_counts.get(canonical, 0)
        corpus_prev = compute_prevalence(corpus_cnt, corpus_total)
        lift = compute_lift(prev, corpus_prev)

        is_eligible = (
            cnt >= 20
            and prev >= 0.015
            and lift > 1.0
        )

        stats.append({
            "canonical": canonical,
            "skill_group": group,
            "count": cnt,
            "prevalence": prev,
            "prevalence_pct": round(prev * 100, 1),
            "lift": round(lift, 2),
            "is_eligible_distinctive": is_eligible,
        })

    stats.sort(key=lambda s: (-s["count"], s["canonical"]))
    return stats
def get_skills_for_family(vocabulary: SkillVocabulary, family: str | None) -> set[str]:
    """
    Returns the set of canonical skill names belonging to the specified technical family.
    If family is None or 'All Families', returns an empty set.
    """
    if not family or family in ("All", "All Families"):
        return set()
    return set(s["canonical"] for s in vocabulary.skills if s.get("category") == family)


def filter_postings_by_skill_family(
    postings: list[Dict[str, Any]],
    family: str | None,
    vocabulary: SkillVocabulary,
) -> list[Dict[str, Any]]:
    """
    Filters postings to those requiring at least one skill from the specified technical family.
    If family is None or 'All Families', returns all postings unchanged.
    Each posting belongs to exactly one occupational category, so category counts sum to total.
    """
    if not family or family in ("All", "All Families"):
        return postings
    target_skills = get_skills_for_family(vocabulary, family)
    if not target_skills:
        return postings
    return [p for p in postings if bool(p.get("skills", set()) & target_skills)]

# ==============================================================================
# Postings Cache & Fingerprint Integrity Management
# ==============================================================================

EXTRACTION_PIPELINE_VERSION: str = "2026-10-30-hybrid-v2"


def compute_file_sha256(path: Path | str) -> str:
    """Computes SHA-256 hexadecimal digest of a file in 1MB chunks. Returns empty string if file missing."""
    p = Path(path)
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def compute_extraction_fingerprint(
    raw_path: Path | str | None,
    vocab_path: Path | str | None,
    pipeline_version: str = EXTRACTION_PIPELINE_VERSION,
) -> Dict[str, str]:
    """Computes a cryptographically strong fingerprint of raw data, vocabulary, and extractor version."""
    return {
        "pipeline_version": str(pipeline_version),
        "raw_sha256": compute_file_sha256(raw_path) if raw_path is not None else "",
        "vocab_sha256": compute_file_sha256(vocab_path) if vocab_path is not None else "",
    }


def validate_postings_cache(
    cache_path: Path | str,
    expected_fingerprint: Dict[str, str],
) -> list[Dict[str, Any]] | None:
    """
    Validates the cached postings against the expected fingerprint.
    Returns the list of posting records if valid, or None if invalid/stale/corrupted.
    """
    p = Path(cache_path)
    if not p.is_file():
        return None

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    cached_fp = data.get("fingerprint")
    if not isinstance(cached_fp, dict):
        return None

    for key, expected_val in expected_fingerprint.items():
        if expected_val and cached_fp.get(key) != expected_val:
            return None

    raw_records = data.get("records")
    if not isinstance(raw_records, list):
        return None

    records: list[Dict[str, Any]] = []
    for r in raw_records:
        if isinstance(r, dict):
            raw_skills = r.get("skills") or []
            records.append({
                "id": str(r.get("id") or ""),
                "country": r.get("country"),
                "category": r.get("category"),
                "seniority": r.get("seniority"),
                "skills": set(raw_skills) if isinstance(raw_skills, (list, tuple, set)) else set(),
            })
    return records


def save_postings_cache(
    cache_path: Path | str,
    records: list[Dict[str, Any]],
    fingerprint: Dict[str, str],
) -> None:
    """Atomically saves extracted posting records and their provenance fingerprint."""
    serializable = {
        "fingerprint": fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "postings_count": len(records),
        "records": [
            {
                "id": str(r.get("id") or ""),
                "country": r.get("country"),
                "category": r.get("category"),
                "seniority": r.get("seniority"),
                "skills": sorted(list(r.get("skills", set()))),
            }
            for r in records
        ],
    }
    atomic_dump_json(serializable, cache_path)


def _extract_posting_records_worker(args: tuple[list[Dict[str, Any]], SkillVocabulary]) -> list[Dict[str, Any]]:
    """Worker function for parallel posting extraction in ProcessPoolExecutor."""
    chunk, vocab = args
    return [extract_posting_record(p, vocab) for p in chunk]


def extract_posting_records_batch(
    postings: list[Dict[str, Any]],
    vocabulary: SkillVocabulary,
    max_workers: int | None = None,
) -> list[Dict[str, Any]]:
    """
    Extracts normalized posting records from raw postings.
    Uses multi-processing for large datasets (>1000 items) when multiple cores are available,
    falling back seamlessly to sequential processing.
    """
    if not postings:
        return []

    workers = max_workers or min(16, os.cpu_count() or 4)
    if len(postings) <= 1000 or workers <= 1:
        return [extract_posting_record(p, vocabulary) for p in postings]

    chunk_size = (len(postings) + workers - 1) // workers
    chunks = [(postings[i:i + chunk_size], vocabulary) for i in range(0, len(postings), chunk_size)]

    try:
        records: list[Dict[str, Any]] = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            for chunk_res in executor.map(_extract_posting_records_worker, chunks):
                records.extend(chunk_res)
        return records
    except Exception:
        # Fallback to single-threaded if process pool fails
        return [extract_posting_record(p, vocabulary) for p in postings]


def load_or_create_postings_cache(
    cache_path: Path | str,
    raw_path: Path | str,
    vocab_path: Path | str,
    max_workers: int | None = None,
) -> list[Dict[str, Any]]:
    """
    Loads posting records from cache if fresh and valid; otherwise extracts from raw data,
    saves the cache atomically with updated fingerprints, and returns the records.
    """
    expected_fingerprint = compute_extraction_fingerprint(raw_path, vocab_path)
    cached_records = validate_postings_cache(cache_path, expected_fingerprint)
    if cached_records is not None:
        return cached_records

    raw_file = Path(raw_path)
    if not raw_file.is_file():
        raise FileNotFoundError(f"Raw postings file not found: {raw_file}")

    with open(raw_file, "r", encoding="utf-8") as f:
        raw_postings = json.load(f)

    vocab = SkillVocabulary.load_from_file(vocab_path) if Path(vocab_path).is_file() else SkillVocabulary({"skills": []})
    records = extract_posting_records_batch(raw_postings, vocab, max_workers=max_workers)

    try:
        save_postings_cache(cache_path, records, expected_fingerprint)
    except Exception:
        pass

    return records
