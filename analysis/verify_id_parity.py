"""
analysis/verify_id_parity.py

Compares posting-ID-level extraction parity between:
1. Precomputed hybrid extraction (offline batch preprocessor logic).
2. Dynamic dashboard extraction pipeline (extract_posting_record / cache).

Total comparisons: 312:
- 52 canonical skills for corpus-wide postings.
- 52 canonical skills across each of the 5 occupational categories (52 * 5 = 260).

Reports:
- Precomputed count
- Dynamic count
- Precomputed-only IDs
- Dynamic-only IDs
- Exact match status (PASS / FAIL)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.analytics import (
    OCCUPATIONAL_CATEGORIES,
    SkillVocabulary,
    extract_skills_from_posting,
    load_or_create_postings_cache,
)


def run_id_parity_verification():
    raw_path = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
    vocab_path = ROOT_DIR / "data" / "fixtures" / "skills_vocabulary.json"
    cache_path = ROOT_DIR / "data" / "processed" / ".postings_cache.json"
    summary_path = ROOT_DIR / "data" / "processed" / "analytics_summary.json"

    print("1. Loading vocabulary...")
    vocab = SkillVocabulary.load_from_file(vocab_path)
    canonical_skills = [s["canonical"] for s in vocab.skills]
    categories = list(OCCUPATIONAL_CATEGORIES.keys())
    print(f"   Loaded {len(canonical_skills)} canonical skills and {len(categories)} categories.")

    print("\n2. Extracting precomputed posting IDs using offline preprocessor logic...")
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_postings = json.load(f)

    pre_corpus_ids: dict[str, set[str]] = defaultdict(set)
    pre_cat_ids: dict[str, dict[str, set[str]]] = {cat: defaultdict(set) for cat in categories}

    for idx, p in enumerate(raw_postings):
        cat = p.get("_collection_category")
        ident = p.get("id") or p.get("public_slug") or p.get("slug") or f"unknown_{idx}"
        skills = extract_skills_from_posting(p, vocab)
        for skill in skills:
            pre_corpus_ids[skill].add(ident)
            if cat in pre_cat_ids:
                pre_cat_ids[cat][skill].add(ident)

    print(f"   Precomputed extraction complete across {len(raw_postings)} raw postings.")

    print("\n3. Loading dynamic pipeline records (from cache / extract_posting_record)...")
    dynamic_records = load_or_create_postings_cache(cache_path, raw_path, vocab_path)
    print(f"   Dynamic pipeline loaded {len(dynamic_records)} records.")

    dyn_corpus_ids: dict[str, set[str]] = defaultdict(set)
    dyn_cat_ids: dict[str, dict[str, set[str]]] = {cat: defaultdict(set) for cat in categories}

    for r in dynamic_records:
        ident = r.get("id")
        cat = r.get("category")
        skills = r.get("skills", set())
        for skill in skills:
            dyn_corpus_ids[skill].add(ident)
            if cat in dyn_cat_ids:
                dyn_cat_ids[cat][skill].add(ident)

    print(f"   Dynamic extraction aggregated across {len(dynamic_records)} records.")

    # Cross-reference with analytics_summary.json if available
    summary_counts: dict[str, dict[str, int]] = {"corpus": {}}
    if summary_path.is_file():
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        for s in summary.get("category_profiles", {}).values():
            cat_id = None
            for cat_key, cat_val in OCCUPATIONAL_CATEGORIES.items():
                if summary.get("category_profiles", {}).get(cat_key) == s:
                    cat_id = cat_key
                    break
        for cat in categories:
            cat_skills = summary.get("category_profiles", {}).get(cat, {}).get("all_skills", [])
            summary_counts[cat] = {cs["canonical"]: cs["count"] for cs in cat_skills}

    print("\n4. Running 312 posting-ID set comparisons...")
    results = []
    total_comparisons = 0
    passed_comparisons = 0
    failed_comparisons = 0

    # A) Corpus level (52 comparisons)
    for skill in canonical_skills:
        total_comparisons += 1
        s_pre = pre_corpus_ids.get(skill, set())
        s_dyn = dyn_corpus_ids.get(skill, set())
        pre_only = s_pre - s_dyn
        dyn_only = s_dyn - s_pre
        is_pass = (len(pre_only) == 0 and len(dyn_only) == 0)

        if is_pass:
            passed_comparisons += 1
            status = "PASS"
        else:
            failed_comparisons += 1
            status = "FAIL"

        results.append({
            "scope": "Corpus (All Roles)",
            "category": "all",
            "skill": skill,
            "precomputed_count": len(s_pre),
            "dynamic_count": len(s_dyn),
            "precomputed_only_count": len(pre_only),
            "dynamic_only_count": len(dyn_only),
            "precomputed_only_sample": ";".join(list(pre_only)[:3]),
            "dynamic_only_sample": ";".join(list(dyn_only)[:3]),
            "status": status,
        })

    # B) Category level (52 * 5 = 260 comparisons)
    for cat in categories:
        for skill in canonical_skills:
            total_comparisons += 1
            s_pre = pre_cat_ids[cat].get(skill, set())
            s_dyn = dyn_cat_ids[cat].get(skill, set())
            pre_only = s_pre - s_dyn
            dyn_only = s_dyn - s_pre
            is_pass = (len(pre_only) == 0 and len(dyn_only) == 0)

            if is_pass:
                passed_comparisons += 1
                status = "PASS"
            else:
                failed_comparisons += 1
                status = "FAIL"

            results.append({
                "scope": f"Category: {cat}",
                "category": cat,
                "skill": skill,
                "precomputed_count": len(s_pre),
                "dynamic_count": len(s_dyn),
                "precomputed_only_count": len(pre_only),
                "dynamic_only_count": len(dyn_only),
                "precomputed_only_sample": ";".join(list(pre_only)[:3]),
                "dynamic_only_sample": ";".join(list(dyn_only)[:3]),
                "status": status,
            })

    output_csv = ROOT_DIR / "analysis" / "posting_id_parity_report.csv"
    with open(output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scope", "category", "skill",
            "precomputed_count", "dynamic_count",
            "precomputed_only_count", "dynamic_only_count",
            "precomputed_only_sample", "dynamic_only_sample",
            "status",
        ])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n========================================================")
    print(f"POSTING-ID EXTRACTION PARITY VERIFICATION SUMMARY")
    print(f"========================================================")
    print(f"Total Comparisons:  {total_comparisons} (52 corpus + 260 category)")
    print(f"Passed Comparisons: {passed_comparisons}")
    print(f"Failed Comparisons: {failed_comparisons}")
    print(f"Pass Rate:          {(passed_comparisons / total_comparisons) * 100:.2f}%")
    print(f"Detailed CSV Report: {output_csv}")
    print(f"========================================================")

    if failed_comparisons > 0:
        print("\nFAILURES DETECTED:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  [{r['scope']}] {r['skill']}: Pre={r['precomputed_count']}, Dyn={r['dynamic_count']}, PreOnly={r['precomputed_only_count']}, DynOnly={r['dynamic_only_count']}")
        return False
    else:
        print("\nAll 312 comparisons achieved EXACT ID-LEVEL SET EQUALITY (0 precomputed-only, 0 dynamic-only).")
        return True


if __name__ == "__main__":
    success = run_id_parity_verification()
    sys.exit(0 if success else 1)
