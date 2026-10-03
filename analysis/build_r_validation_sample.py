"""
analysis/build_r_validation_sample.py

Draws a deterministic holdout validation sample of 30 postings from the 1,026
postings currently detected with the 'R' skill in the 23,138-posting EU-27 snapshot.
Used for independent post-fix validation of the R regex following instructor feedback.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.analytics import SkillVocabulary, extract_skills_from_posting

RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
VOCAB_PATH = ROOT_DIR / "data" / "fixtures" / "skills_vocabulary.json"
OUTPUT_SAMPLE_PATH = ROOT_DIR / "analysis" / "r_validation_sample.json"

RANDOM_SEED: int = 20261003
SAMPLE_SIZE: int = 30
EXPECTED_R_MATCHES: int = 1026


def build_r_sample(
    raw_path: Path = RAW_DATA_PATH,
    vocab_path: Path = VOCAB_PATH,
    output_path: Path = OUTPUT_SAMPLE_PATH,
    seed: int = RANDOM_SEED,
    sample_size: int = SAMPLE_SIZE,
) -> List[Dict[str, Any]]:
    print(f"Loading raw postings from {raw_path}...")
    with open(raw_path, "r", encoding="utf-8") as f:
        postings: List[Dict[str, Any]] = json.load(f)

    print(f"Loading vocabulary from {vocab_path}...")
    vocab = SkillVocabulary.load_from_file(vocab_path)

    print(f"Scanning {len(postings)} postings for current production R matches...")
    r_matches: List[Dict[str, Any]] = []
    for p in postings:
        skills = extract_skills_from_posting(p, vocab)
        if "R" in skills:
            r_matches.append(p)

    r_count = len(r_matches)
    print(f"Total current R matches found: {r_count} (expected: {EXPECTED_R_MATCHES})")
    if r_count != EXPECTED_R_MATCHES:
        raise ValueError(
            f"Expected exactly {EXPECTED_R_MATCHES} R matches, but found {r_count}."
        )

    # Deterministic sampling
    rng = random.Random(seed)
    sampled: List[Dict[str, Any]] = rng.sample(r_matches, sample_size)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sampled, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(sampled)} frozen sample postings to {output_path}")
    return sampled


def main() -> None:
    sampled = build_r_sample()

    slugs = [p.get("public_slug") for p in sampled]
    unique_slugs = len(set(slugs))
    categories = Counter(p.get("_collection_category") for p in sampled)
    countries = Counter(p.get("_collection_country") for p in sampled)

    print("\n--- SAMPLE VALIDATION SUMMARY ---")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Sample size: {len(sampled)}")
    print(f"Unique slugs: {unique_slugs}/{len(sampled)}")
    print(f"Category breakdown: {dict(categories)}")
    print(f"Country breakdown: {dict(countries)}")
    print("\nSampled posting slugs (in order):")
    for idx, slug in enumerate(slugs, 1):
        print(f"  {idx:2d}. {slug}")


if __name__ == "__main__":
    main()
