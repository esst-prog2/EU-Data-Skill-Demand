"""
analysis/build_spike_sample.py

Builds a deterministic 50-posting validation sample (10 postings per FreeHire
occupational category) from data/raw/freehire_eu_raw.json using seed 20260929
for the HW4 skill-label validation spike ("How many of the skill labels are true?").
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
SAMPLE_OUTPUT_PATH = ROOT_DIR / "analysis" / "spike_sample.json"

CATEGORIES: List[str] = [
    "data_analytics",
    "data_engineering",
    "data_science",
    "ml_ai",
    "ai_engineering",
]
SAMPLE_PER_CATEGORY: int = 10
RANDOM_SEED: int = 20260929


def build_sample(
    raw_path: Path = RAW_DATA_PATH,
    output_path: Path = SAMPLE_OUTPUT_PATH,
    seed: int = RANDOM_SEED,
    per_category: int = SAMPLE_PER_CATEGORY,
) -> List[Dict[str, Any]]:
    with open(raw_path, "r", encoding="utf-8") as f:
        postings: List[Dict[str, Any]] = json.load(f)

    by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for posting in postings:
        cat = posting.get("_collection_category")
        if cat in CATEGORIES:
            by_category[cat].append(posting)

    rng = random.Random(seed)
    sampled: List[Dict[str, Any]] = []

    for category in CATEGORIES:
        pool = by_category[category]
        if len(pool) < per_category:
            raise ValueError(
                f"Category '{category}' has only {len(pool)} postings (need {per_category})."
            )
        selected = rng.sample(pool, per_category)
        sampled.extend(selected)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sampled, f, ensure_ascii=False, indent=2)

    return sampled


def main() -> None:
    sampled = build_sample()
    counts = Counter(p["_collection_category"] for p in sampled)
    desc_lengths = [len(p.get("description") or "") for p in sampled]
    missing_urls = sum(1 for p in sampled if not p.get("url"))

    print(f"Saved {len(sampled)} sampled postings to {SAMPLE_OUTPUT_PATH}")
    print("Category counts:", dict(counts))
    print(
        f"Description lengths (chars): min={min(desc_lengths)}, "
        f"median={sorted(desc_lengths)[len(desc_lengths)//2]}, max={max(desc_lengths)}"
    )
    print(f"Missing URLs: {missing_urls}")


if __name__ == "__main__":
    main()
