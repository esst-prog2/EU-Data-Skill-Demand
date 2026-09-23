"""
src/analytics.py

Pure-Python analytical logic for skill extraction, prevalence calculation,
skill distinctiveness (lift), support-based noise filtering, and geographic thresholding.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class SkillVocabulary:
    """Encapsulates the controlled technical skill vocabulary with normalized aliases and regexes."""

    def __init__(self, vocab_data: Dict[str, Any]):
        self.skills: List[Dict[str, Any]] = vocab_data.get("skills", [])
        self.alias_to_canonical: Dict[str, str] = {}
        self.canonical_to_entry: Dict[str, Dict[str, Any]] = {}
        self.compiled_regexes: Dict[str, re.Pattern] = {}

        for entry in self.skills:
            canonical = entry["canonical"]
            self.canonical_to_entry[canonical] = entry

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

