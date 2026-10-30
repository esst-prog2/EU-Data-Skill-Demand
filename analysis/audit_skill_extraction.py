"""
analysis/audit_skill_extraction.py

Full Skill Extraction Audit:
1. Calculates native-tag, description-regex, and hybrid detection counts for all 52 skills.
2. Identifies overlaps, exclusives, and contribution percentages per skill.
3. Compares dynamic extraction with precomputed analytics_summary.json.
4. Generates analysis/skill_extraction_audit.csv.
"""

from __future__ import annotations

import concurrent.futures
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.analytics import (
    OCCUPATIONAL_CATEGORIES,
    SkillVocabulary,
    compute_population_skill_stats,
    extract_skills_from_posting,
)

RAW_PATH = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
VOCAB_PATH = ROOT_DIR / "data" / "fixtures" / "skills_vocabulary.json"
SUMMARY_PATH = ROOT_DIR / "data" / "processed" / "analytics_summary.json"
OUTPUT_CSV = ROOT_DIR / "analysis" / "skill_extraction_audit.csv"


def process_posting_chunk(chunk_data):
    """
    Processes a chunk of postings and returns per-skill detection sets of posting IDs:
    - tag_detections: skill -> set of posting_ids
    - regex_detections: skill -> set of posting_ids
    - hybrid_detections: skill -> set of posting_ids
    - posting_metadata: list of (posting_id, country, category, seniority, hybrid_skills)
    """
    vocab = SkillVocabulary.load_from_file(VOCAB_PATH)
    tag_dets = defaultdict(set)
    regex_dets = defaultdict(set)
    hybrid_dets = defaultdict(set)
    records = []

    for idx, p in chunk_data:
        pid = p.get("id") or p.get("public_slug") or p.get("slug") or f"idx_{idx}"

        # 1. Native tag check
        raw_tags = p.get("skills") or []
        tags_present = set()
        if isinstance(raw_tags, (list, tuple, set)):
            for t in raw_tags:
                if isinstance(t, str):
                    cleaned = t.strip().lower()
                    canonical = vocab.alias_to_canonical.get(cleaned)
                    if canonical:
                        tags_present.add(canonical)
                        tag_dets[canonical].add(pid)

        # 2. Description regex check
        desc = p.get("description") or ""
        regex_present = set()
        if desc and isinstance(desc, str):
            for canonical, pattern in vocab.compiled_regexes.items():
                if pattern.search(desc):
                    regex_present.add(canonical)
                    regex_dets[canonical].add(pid)

        # 3. Hybrid presence (union of tags and regex)
        hybrid_present = tags_present | regex_present
        for canonical in hybrid_present:
            hybrid_dets[canonical].add(pid)

        # Metadata extraction
        country = p.get("_collection_country")
        category = p.get("_collection_category")
        sen = p.get("seniority")
        if not sen and isinstance(p.get("enrichment"), dict):
            sen = p["enrichment"].get("seniority")
        if sen and not isinstance(sen, str):
            sen = None
        elif isinstance(sen, str):
            sen = sen.strip().lower()

        records.append({
            "id": pid,
            "country": country,
            "category": category,
            "seniority": sen,
            "skills": hybrid_present,
        })

    return tag_dets, regex_dets, hybrid_dets, records


def run_audit():
    print(f"Loading vocabulary from {VOCAB_PATH}...")
    vocab = SkillVocabulary.load_from_file(VOCAB_PATH)
    canonical_skills = sorted(list(set(s["canonical"] for s in vocab.skills)))
    skill_categories = {s["canonical"]: s.get("category", "") for s in vocab.skills}
    print(f"Loaded {len(canonical_skills)} canonical skills.")

    print(f"Loading raw postings from {RAW_PATH}...")
    t0 = time.time()
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_postings = json.load(f)
    total_postings = len(raw_postings)
    print(f"Loaded {total_postings} postings in {time.time() - t0:.2f}s.")

    # Check alias overlaps in vocabulary
    print("\n--- Checking for Potential Overlapping Aliases Across Skills ---")
    alias_map = defaultdict(list)
    for s in vocab.skills:
        c = s["canonical"]
        alias_map[c.lower()].append((c, "canonical"))
        for a in s.get("aliases", []):
            alias_map[a.strip().lower()].append((c, "alias"))

    overlapping = {k: v for k, v in alias_map.items() if len(set(c for c, _ in v)) > 1}
    if overlapping:
        print(f"WARNING: Found {len(overlapping)} overlapping aliases!")
        for k, v in overlapping.items():
            print(f"  Alias '{k}': {v}")
    else:
        print("PASS: No overlapping aliases found across different canonical skills.")

    # Chunk postings for multi-processing
    indexed_postings = list(enumerate(raw_postings))
    n_workers = min(16, os.cpu_count() or 4)
    chunk_size = (total_postings + n_workers - 1) // n_workers
    chunks = [indexed_postings[i:i + chunk_size] for i in range(0, total_postings, chunk_size)]

    print(f"\nProcessing {total_postings} postings across {len(chunks)} worker processes...")
    t1 = time.time()
    all_tag_dets = defaultdict(set)
    all_regex_dets = defaultdict(set)
    all_hybrid_dets = defaultdict(set)
    all_records = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as executor:
        for chunk_tags, chunk_regex, chunk_hybrid, chunk_records in executor.map(process_posting_chunk, chunks):
            for k, pids in chunk_tags.items():
                all_tag_dets[k].update(pids)
            for k, pids in chunk_regex.items():
                all_regex_dets[k].update(pids)
            for k, pids in chunk_hybrid.items():
                all_hybrid_dets[k].update(pids)
            all_records.extend(chunk_records)

    print(f"Processed {len(all_records)} unique postings in {time.time() - t1:.2f}s.")

    # 1. Compute 52-Skill Metrics
    audit_rows = []
    for skill in canonical_skills:
        tags = all_tag_dets.get(skill, set())
        regexes = all_regex_dets.get(skill, set())
        hybrid = all_hybrid_dets.get(skill, set())

        both = tags & regexes
        only_tags = tags - regexes
        only_regex = regexes - tags

        n_tag = len(tags)
        n_regex = len(regexes)
        n_hybrid = len(hybrid)
        n_both = len(both)
        n_only_tag = len(only_tags)
        n_only_regex = len(only_regex)

        tag_pct_of_hybrid = round((n_tag / n_hybrid * 100), 2) if n_hybrid else 0.0
        regex_pct_of_hybrid = round((n_regex / n_hybrid * 100), 2) if n_hybrid else 0.0
        tag_exclusive_pct = round((n_only_tag / n_hybrid * 100), 2) if n_hybrid else 0.0
        regex_exclusive_pct = round((n_only_regex / n_hybrid * 100), 2) if n_hybrid else 0.0
        both_pct = round((n_both / n_hybrid * 100), 2) if n_hybrid else 0.0

        diff_hybrid_vs_native = n_hybrid - n_tag

        audit_rows.append({
            "canonical_skill": skill,
            "skill_family": skill_categories.get(skill, ""),
            "native_tag_total": n_tag,
            "regex_total": n_regex,
            "hybrid_total": n_hybrid,
            "both_count": n_both,
            "only_native_tag": n_only_tag,
            "only_regex": n_only_regex,
            "both_pct_of_hybrid": both_pct,
            "native_exclusive_pct": tag_exclusive_pct,
            "regex_exclusive_pct": regex_exclusive_pct,
            "native_coverage_pct_of_hybrid": tag_pct_of_hybrid,
            "regex_coverage_pct_of_hybrid": regex_pct_of_hybrid,
            "hybrid_minus_native": diff_hybrid_vs_native,
        })

    # Sort audit rows descending by hybrid total
    audit_rows.sort(key=lambda r: r["hybrid_total"], reverse=True)

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "canonical_skill",
            "skill_family",
            "hybrid_total",
            "native_tag_total",
            "regex_total",
            "both_count",
            "only_native_tag",
            "only_regex",
            "both_pct_of_hybrid",
            "native_exclusive_pct",
            "regex_exclusive_pct",
            "native_coverage_pct_of_hybrid",
            "regex_coverage_pct_of_hybrid",
            "hybrid_minus_native",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    print(f"\nWrote 52-skill audit report to {OUTPUT_CSV}")

    # 2. Key Categorizations
    print("\n=======================================================")
    print("SKILL DEPENDENCY ANALYSIS (Out of 52 canonical skills)")
    print("=======================================================")

    almost_entirely_regex = [r for r in audit_rows if r["regex_coverage_pct_of_hybrid"] >= 95.0 and r["native_coverage_pct_of_hybrid"] < 10.0]
    almost_entirely_tags = [r for r in audit_rows if r["native_coverage_pct_of_hybrid"] >= 95.0 and r["regex_coverage_pct_of_hybrid"] < 10.0]
    high_both = [r for r in audit_rows if r["both_pct_of_hybrid"] >= 50.0]
    largest_gap = sorted(audit_rows, key=lambda r: r["hybrid_minus_native"], reverse=True)[:10]

    print(f"\n1. Skills almost entirely dependent on regex (Regex >= 95%, Tags < 10%): ({len(almost_entirely_regex)})")
    for r in almost_entirely_regex:
        print(f"   - {r['canonical_skill']}: Hybrid={r['hybrid_total']}, Native={r['native_tag_total']}, Regex={r['regex_total']} (Regex {r['regex_coverage_pct_of_hybrid']}%)")

    print(f"\n2. Skills almost entirely dependent on native tags (Tags >= 95%, Regex < 10%): ({len(almost_entirely_tags)})")
    for r in almost_entirely_tags:
        print(f"   - {r['canonical_skill']}: Hybrid={r['hybrid_total']}, Native={r['native_tag_total']}, Regex={r['regex_total']} (Tags {r['native_coverage_pct_of_hybrid']}%)")

    print(f"\n3. Top 10 skills with largest gain from hybrid over native tags:")
    for r in largest_gap:
        print(f"   - {r['canonical_skill']}: Native={r['native_tag_total']} -> Hybrid={r['hybrid_total']} (+{r['hybrid_minus_native']}, regex exclusive={r['only_regex']})")

    # Low and high volume checks
    low_counts = [r for r in audit_rows if r["hybrid_total"] < 20]
    high_counts = [r for r in audit_rows if r["hybrid_total"] > 5000]
    print(f"\n4. Skills with very low corpus count (< 20 postings, sub-threshold): ({len(low_counts)})")
    for r in low_counts:
        print(f"   - {r['canonical_skill']}: Hybrid={r['hybrid_total']} ({r['skill_family']})")

    print(f"\n5. Skills with very high corpus count (> 5,000 postings): ({len(high_counts)})")
    for r in high_counts:
        pct = round(r['hybrid_total'] / total_postings * 100, 1)
        print(f"   - {r['canonical_skill']}: Hybrid={r['hybrid_total']} ({pct}% of corpus)")

    # 3. Compare with precomputed analytics_summary.json
    print("\n=======================================================")
    print("COMPARISON: PRECOMPUTED ANALYTICS VS DYNAMIC PIPELINE")
    print("=======================================================")

    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Compare corpus totals
    summary_corpus_counts = {}
    for item in summary.get("corpus_top_skills", []):
        summary_corpus_counts[item["skill"]] = item["count"]

    # If corpus_top_skills is empty, pull from category profiles
    if not summary_corpus_counts:
        summary_corpus_counts = defaultdict(int)
        for cat_id, prof in summary.get("category_profiles", {}).items():
            for s in prof.get("all_skills", []):
                # Count in all_skills is category count
                pass

    # Let's check summary kpis
    print(f"Summary total_postings: {summary['kpis']['total_postings']}")
    print(f"Dynamic total_postings: {len(all_records)}")

    # Check category by category
    category_discrepancies = []
    dynamic_cat_counts = defaultdict(Counter)
    dynamic_cat_totals = Counter()
    for r in all_records:
        cat = r["category"]
        dynamic_cat_totals[cat] += 1
        for s in r["skills"]:
            dynamic_cat_counts[cat][s] += 1

    for cat_id, cat_name in OCCUPATIONAL_CATEGORIES.items():
        summary_prof = summary.get("category_profiles", {}).get(cat_id, {})
        summary_cat_total = summary_prof.get("total_postings", 0)
        dyn_cat_total = dynamic_cat_totals.get(cat_id, 0)
        diff_total = dyn_cat_total - summary_cat_total
        print(f"\nCategory '{cat_id}' ({cat_name}): Summary Postings={summary_cat_total}, Dynamic Postings={dyn_cat_total} (Diff={diff_total})")

        summary_skill_map = {s["canonical"]: s["count"] for s in summary_prof.get("all_skills", [])}
        for skill in canonical_skills:
            sum_count = summary_skill_map.get(skill, 0)
            dyn_count = dynamic_cat_counts[cat_id].get(skill, 0)
            diff = dyn_count - sum_count
            diff_pct = round((diff / sum_count * 100), 2) if sum_count else (0.0 if dyn_count == 0 else 100.0)
            if diff != 0:
                category_discrepancies.append({
                    "category": cat_id,
                    "skill": skill,
                    "summary_count": sum_count,
                    "dynamic_count": dyn_count,
                    "diff": diff,
                    "diff_pct": diff_pct,
                })

    if not category_discrepancies:
        print("\nPERFECT PARITY: Zero discrepancies across all 52 skills and all 5 occupational categories!")
    else:
        print(f"\nFound {len(category_discrepancies)} discrepancies between precomputed summary and dynamic pipeline:")
        for d in category_discrepancies[:20]:
            print(f"  {d['category']} - {d['skill']}: Summary={d['summary_count']}, Dynamic={d['dynamic_count']}, Diff={d['diff']} ({d['diff_pct']}%)")


if __name__ == "__main__":
    run_audit()
