"""
analysis/sensitivity_analysis.py

Reproducible threshold sensitivity analysis for distinctive-skill ranking
in the EU Data Jobs & Skill Demand Analysis project.

This script:
1. Loads the frozen FreeHire EU-27 snapshot (data/raw/freehire_eu_raw.json)
   and the 52-skill controlled vocabulary (data/fixtures/skills_vocabulary.json).
2. Computes category-level and corpus-level skill prevalence and lift using the
   production functions in src/analytics.py (and verifies exact agreement with
   data/processed/analytics_summary.json).
3. Evaluates the 25-combination threshold grid:
   - min_count in [5, 10, 20, 30, 50]
   - min_prevalence in [0.5%, 1.0%, 1.5%, 2.0%, 3.0%]
4. Compares the production baseline (N >= 20, prevalence >= 1.5%) against lower
   and higher cutoffs, identifying which skills enter and leave the eligible
   pool and the Top-10 displayed ranking.
5. Verifies concrete case studies (Cassandra vs. Snowflake in Data Engineering,
   Go vs. Kubernetes in AI Engineering, OpenCV/XGBoost in ML/AI, and Metabase
   in Data Analytics).
6. Prints summary tables to stdout and writes the permanent report to
   analysis/sensitivity_report.md.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.analytics import (
    SkillVocabulary,
    compute_lift,
    compute_prevalence,
    extract_skills_from_posting,
    filter_distinctive_skills,
)

RAW_DATA_PATH = ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json"
VOCAB_PATH = ROOT_DIR / "data" / "fixtures" / "skills_vocabulary.json"
SUMMARY_PATH = ROOT_DIR / "data" / "processed" / "analytics_summary.json"
REPORT_PATH = ROOT_DIR / "analysis" / "sensitivity_report.md"

CATEGORIES: List[Tuple[str, str]] = [
    ("data_analytics", "Data Analytics"),
    ("data_engineering", "Data Engineering"),
    ("data_science", "Data Science"),
    ("ml_ai", "ML/AI"),
    ("ai_engineering", "AI Engineering"),
]

MIN_COUNTS: List[int] = [5, 10, 20, 30, 50]
MIN_PREVALENCES: List[float] = [0.005, 0.010, 0.015, 0.020, 0.030]


def compute_skill_stats_from_raw(
    raw_path: Path, vocab_path: Path
) -> Tuple[int, Dict[str, int], Dict[str, List[Dict[str, Any]]]]:
    """
    Computes skill statistics per category directly from the raw FreeHire snapshot
    using the exact production methodology in src/analytics.py and scripts/preprocess.py.
    """
    vocabulary = SkillVocabulary.load_from_file(vocab_path)
    with open(raw_path, "r", encoding="utf-8") as f:
        postings = json.load(f)

    total_postings = len(postings)
    category_counts: Counter = Counter()
    corpus_skill_counts: Counter = Counter()
    category_skill_counts: Dict[str, Counter] = defaultdict(Counter)

    for posting in postings:
        cat = posting.get("_collection_category") or "unknown"
        category_counts[cat] += 1
        skills = extract_skills_from_posting(posting, vocabulary)
        for skill in skills:
            corpus_skill_counts[skill] += 1
            category_skill_counts[cat][skill] += 1

    all_skills_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for cat_id, _ in CATEGORIES:
        cat_total = category_counts.get(cat_id, 0)
        skill_stats: List[Dict[str, Any]] = []
        for skill_entry in vocabulary.skills:
            canonical = skill_entry["canonical"]
            cnt = category_skill_counts[cat_id].get(canonical, 0)
            prev = compute_prevalence(cnt, cat_total)
            corpus_prev = compute_prevalence(
                corpus_skill_counts.get(canonical, 0), total_postings
            )
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
        all_skills_by_cat[cat_id] = skill_stats

    return total_postings, dict(category_counts), all_skills_by_cat


def verify_against_precomputed_summary(
    all_skills_by_cat: Dict[str, List[Dict[str, Any]]], summary_path: Path
) -> bool:
    """Verifies that raw-computed skill stats match data/processed/analytics_summary.json."""
    if not summary_path.exists():
        return False
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    for cat_id, _ in CATEGORIES:
        precomputed_all = summary["category_profiles"][cat_id]["all_skills"]
        if all_skills_by_cat[cat_id] != precomputed_all:
            raise AssertionError(f"Mismatch in all_skills for {cat_id}")

        prod_top10 = filter_distinctive_skills(
            all_skills_by_cat[cat_id],
            min_count=20,
            min_prevalence=0.015,
            min_lift=1.0,
            top_n=10,
        )
        if prod_top10 != summary["category_profiles"][cat_id]["top_distinctive"]:
            raise AssertionError(f"Mismatch in top_distinctive for {cat_id}")

    return True


def evaluate_grid(
    all_skills_by_cat: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Evaluates all combinations of MIN_COUNTS x MIN_PREVALENCES."""
    rows: List[Dict[str, Any]] = []
    for mc in MIN_COUNTS:
        for mp in MIN_PREVALENCES:
            per_cat_eligible: Dict[str, List[Dict[str, Any]]] = {}
            per_cat_top10: Dict[str, List[Dict[str, Any]]] = {}
            for cat_id, _ in CATEGORIES:
                all_s = all_skills_by_cat[cat_id]
                per_cat_eligible[cat_id] = filter_distinctive_skills(
                    all_s, min_count=mc, min_prevalence=mp, min_lift=1.0, top_n=1000
                )
                per_cat_top10[cat_id] = filter_distinctive_skills(
                    all_s, min_count=mc, min_prevalence=mp, min_lift=1.0, top_n=10
                )
            rows.append(
                {
                    "min_count": mc,
                    "min_prevalence": mp,
                    "total_eligible_pairs": sum(
                        len(v) for v in per_cat_eligible.values()
                    ),
                    "total_displayed_top10": sum(
                        len(v) for v in per_cat_top10.values()
                    ),
                    "eligible": per_cat_eligible,
                    "top10": per_cat_top10,
                }
            )
    return rows


def find_skill(
    skill_stats: List[Dict[str, Any]], canonical_name: str
) -> Dict[str, Any]:
    """Looks up a single skill dictionary by canonical name."""
    for s in skill_stats:
        if s["canonical"] == canonical_name:
            return s
    raise KeyError(f"Skill not found: {canonical_name}")


def build_report_markdown(
    total_postings: int,
    category_counts: Dict[str, int],
    all_skills_by_cat: Dict[str, List[Dict[str, Any]]],
    grid_rows: List[Dict[str, Any]],
) -> str:
    """Generates the complete markdown sensitivity report from computed results."""
    lines: List[str] = []

    def add(line: str = "") -> None:
        lines.append(line)

    # Verify baseline counts
    baseline_row = next(
        r
        for r in grid_rows
        if r["min_count"] == 20 and math.isclose(r["min_prevalence"], 0.015)
    )
    total_lift_gt_1 = sum(
        sum(1 for s in all_skills_by_cat[cid] if s["lift"] > 1.0)
        for cid, _ in CATEGORIES
    )
    unique_passing_baseline = len(
        {
            s["canonical"]
            for cid, _ in CATEGORIES
            for s in baseline_row["eligible"][cid]
        }
    )

    add("# Threshold Sensitivity Analysis: Distinctive-Skill Ranking (`N >= 20`, `Prevalence >= 1.5%`)")
    add()
    add("## 1. Purpose & Context")
    add()
    add(
        "In the EU Data Jobs & Skill Demand Analysis dashboard, each occupational category's "
        "**Most Distinctive Skills** chart ranks skills by corpus-relative lift:"
    )
    add()
    add(
        "$$\\text{Lift}(\\text{skill}, \\text{category}) = "
        "\\frac{P(\\text{skill} \\mid \\text{category})}{P(\\text{skill} \\mid \\text{corpus})}$$"
    )
    add()
    add(
        "Before ranking skills with $\\text{Lift} > 1.0$ and selecting the Top 10 for display (`top_n = 10`), "
        "`filter_distinctive_skills` in `src/analytics.py` requires a skill to satisfy two support thresholds "
        "within the selected occupational category:"
    )
    add("- **Minimum posting count:** `count >= 20`")
    add("- **Minimum within-category prevalence:** `prevalence >= 1.5%` (`0.015`)")
    add()
    add(
        "This report documents the empirical sensitivity analysis across the audited snapshot of "
        f"**{total_postings:,} unique EU-27 FreeHire job postings** (`data/raw/freehire_eu_raw.json`) "
        "and the **52-skill controlled vocabulary** (`data/fixtures/skills_vocabulary.json`), showing "
        "what changes when these two thresholds are lowered or raised."
    )
    add()
    add("---")
    add()
    add("## 2. Unequal Category Sizes & Complementary Roles of the Two Thresholds")
    add()
    add(
        "The five FreeHire occupational categories in the observed corpus differ in sample size by "
        f"more than $13\\times$—ranging from **{category_counts['ml_ai']:,} postings** in `ML/AI` to "
        f"**{category_counts['data_engineering']:,} postings** in `Data Engineering` "
        f"({category_counts['data_engineering'] / total_postings * 100:.1f}% of the entire corpus)."
    )
    add()
    add(
        "Because a skill must satisfy **both** $\\text{count} \\ge N_{\\min}$ and "
        "$\\text{count} / N_{\\text{category}} \\ge P_{\\min}$, the effective minimum posting count required "
        "in a category of size $N_{\\text{category}}$ is:"
    )
    add()
    add(
        "$$\\text{Effective Minimum Postings} = \\max\\!\\left(N_{\\min}, \\; "
        "\\lceil N_{\\text{category}} \\times P_{\\min} \\rceil\\right)$$"
    )
    add()
    add(
        "| Occupational Category | Category ID | Observed Postings ($N$) | Corpus Share | "
        "$0.5\\%$ in Postings | $1.0\\%$ in Postings | $1.5\\%$ in Postings | $2.0\\%$ in Postings | "
        "$3.0\\%$ in Postings | Effective Floor at $(20, 1.5\\%)$ |"
    )
    add("| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |")

    for cid, cname in CATEGORIES:
        n_cat = category_counts[cid]
        share = (n_cat / total_postings) * 100
        req_15 = math.ceil(n_cat * 0.015)
        if req_15 > 20:
            role_str = f"**1.5% prevalence** ($\\ge {req_15}$ postings)"
        else:
            role_str = f"**20 postings** ($\\ge 20$ postings, $1.77\\%$)"
        add(
            f"| **{cname}** | `{cid}` | {n_cat:,} | {share:.1f}% | "
            f"{n_cat * 5 / 1000:.1f} | {n_cat * 10 / 1000:.1f} | {n_cat * 15 / 1000 + 1e-9:.1f} | "
            f"{n_cat * 20 / 1000:.1f} | {n_cat * 30 / 1000:.1f} | {role_str} |"
        )

    add()
    add("### Why Both Thresholds Are Used")
    add(
        "1. **`1.5%` within-category prevalence scales with category size:** In the four larger occupations "
        "(`Data Engineering`, `Data Analytics`, `AI Engineering`, and `Data Science`), $1.5\\%$ corresponds to "
        "between **31 and 227 postings**. A flat 20-posting cutoff alone would be almost non-binding in "
        "`Data Engineering` (where 20 postings is just $0.13\\%$ of the category)."
    )
    add(
        "2. **`20 postings` provides an absolute minimum support floor for smaller categories:** In the smallest "
        "category (`ML/AI`, $N = 1,132$), $1.5\\%$ corresponds to **$17.0$ postings**. The `N >= 20` rule guarantees "
        "that a skill is backed by at least 20 observed postings ($1.77\\%$) before being ranked by lift. "
        "*(Note: In the current 52-skill vocabulary, no `ML/AI` skill has a count of 17, 18, or 19—the nearest below 20 "
        "are `Elasticsearch` at $N=16$ [$1.41\\%$] and `Redis` at $N=15$ [$1.33\\%$]. Thus at $P_{\\min} = 1.5\\%$ "
        "the two rules select the same `ML/AI` skills, whereas `N >= 20` actively blocks `Elasticsearch` and `Redis` "
        "in `ML/AI` when $P_{\\min}$ is lowered to $\\le 1.0\\%$, and blocks `Go` [$N=18$, $0.78\\%$] and `XGBoost` "
        "[$N=16$, $0.69\\%$] in `AI Engineering` when $P_{\\min}$ is lowered to $0.5\\%$.)*"
    )
    add()
    add("---")
    add()
    add("## 3. Full Sensitivity Grid Across 25 Threshold Combinations")
    add()
    add(
        "Across all 5 occupations and 52 vocabulary skills ($5 \\times 52 = 260$ category-skill pairs), "
        f"**{total_lift_gt_1} category-skill pairs** have $\\text{{Lift}} > 1.0$ prior to support filtering."
    )
    add()
    add(
        "Because `filter_distinctive_skills` caps the dashboard visual at `top_n = 10` skills per category, "
        "changing thresholds affects both:"
    )
    add("- **Eligible category-skill pairs (uncapped):** Total pairs meeting `count >= Min postings`, `prevalence >= Min prevalence`, and `lift > 1.0`.")
    add("- **Displayed Top-10 skills (`[in brackets]`):** Number of bars rendered in the dashboard chart (`max 10` per category, `max 50` across all 5 categories).")
    add()
    add(
        "| Min postings | Min prevalence | Total skills (`Eligible [Displayed]`) | Data Analytics ($N=2,440$) | "
        "Data Engineering ($N=15,090$) | Data Science ($N=2,009$) | ML/AI ($N=1,132$) | AI Engineering ($N=2,314$) |"
    )
    add("| ---: | ---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    # Include unfiltered reference row first
    unfiltered_elig = {
        cid: filter_distinctive_skills(
            all_skills_by_cat[cid], min_count=1, min_prevalence=0.0, min_lift=1.0, top_n=1000
        )
        for cid, _ in CATEGORIES
    }
    unfiltered_top10 = {
        cid: filter_distinctive_skills(
            all_skills_by_cat[cid], min_count=1, min_prevalence=0.0, min_lift=1.0, top_n=10
        )
        for cid, _ in CATEGORIES
    }
    add(
        f"| *1 (Unfiltered)* | *0.0%* | *{sum(len(v) for v in unfiltered_elig.values())} "
        f"[{sum(len(v) for v in unfiltered_top10.values())}]* | "
        + " | ".join(
            f"*{len(unfiltered_elig[cid])} [{len(unfiltered_top10[cid])}]*"
            for cid, _ in CATEGORIES
        )
        + " |"
    )

    for row in grid_rows:
        mc = row["min_count"]
        mp = row["min_prevalence"]
        is_current = mc == 20 and math.isclose(mp, 0.015)
        b = "**" if is_current else ""
        label_mc = f"{mc} (Current)" if is_current else f"{mc}"
        cells = [
            f"{b}{len(row['eligible'][cid])} [{len(row['top10'][cid])}]{b}"
            for cid, _ in CATEGORIES
        ]
        add(
            f"| {b}{label_mc}{b} | {b}{mp * 100:.1f}%{b} | "
            f"{b}{row['total_eligible_pairs']} [{row['total_displayed_top10']}]{b} | "
            + " | ".join(cells)
            + " |"
        )

    add()
    add("---")
    add()
    add("## 4. Current Production Baseline (`N >= 20`, `Prevalence >= 1.5%`)")
    add()
    add(
        f"At the current production threshold (`min_count = 20`, `min_prevalence = 1.5%`), "
        f"**{baseline_row['total_eligible_pairs']} category-skill pairs** (spanning **{unique_passing_baseline} unique skills** "
        f"out of 52) pass eligibility, and **{baseline_row['total_displayed_top10']} skills** are displayed across "
        "the five Top-10 charts (`9` in Data Analytics and `10` in each of the other four occupations)."
    )
    add()

    for cid, cname in CATEGORIES:
        n_cat = category_counts[cid]
        elig_list = baseline_row["eligible"][cid]
        top10_list = baseline_row["top10"][cid]
        total_lift_cat = sum(1 for s in all_skills_by_cat[cid] if s["lift"] > 1.0)
        excluded_cat = [
            s
            for s in sorted(
                [x for x in all_skills_by_cat[cid] if x["lift"] > 1.0],
                key=lambda x: (x["lift"], x["prevalence"]),
                reverse=True,
            )
            if s not in elig_list
        ]

        add(
            f"### {cname} (`{cid}`, $N = {n_cat:,}$) — "
            f"{len(elig_list)} Eligible / {len(top10_list)} Displayed (of {total_lift_cat} with $\\text{{Lift}} > 1.0$)"
        )
        add()
        add("| Top-10 Rank | Skill | Domain | Postings ($N$) | Within-Category Prevalence | Lift |")
        add("| ---: | :--- | :--- | ---: | ---: | ---: |")
        for idx, s in enumerate(top10_list, 1):
            add(
                f"| {idx} | **{s['canonical']}** | {s['skill_group']} | "
                f"{s['count']:,} | {s['prevalence'] * 100:.2f}% ({s['prevalence_pct']:.1f}%) | "
                f"**{s['lift']:.2f}×** |"
            )

        if len(elig_list) > 10 or excluded_cat:
            add()

        if len(elig_list) > 10:
            overflow_str = ", ".join(
                f"`{s['canonical']}` ({s['lift']:.2f}×, {s['prevalence'] * 100:.2f}%)"
                for s in elig_list[10:]
            )
            add(f"- **Eligible skills ranked #11–#{len(elig_list)} (outside Top-10 display):** {overflow_str}.")

        if excluded_cat:
            excl_str = ", ".join(
                f"`{s['canonical']}` ($N={s['count']}$, {s['prevalence'] * 100:.2f}%, {s['lift']:.2f}×)"
                for s in excluded_cat
            )
            add(f"- **Excluded skills with $\\text{{Lift}} > 1.0$ (below support threshold):** {excl_str}.")
        add()

    add("---")
    add()
    add("## 5. Trade-Off Analysis: Lowering vs. Raising Thresholds")
    add()
    add(
        "Because corpus-relative lift places $P(\\text{skill} \\mid \\text{corpus})$ in the denominator, "
        "skills with small corpus counts can achieve high lift multipliers from relatively few category mentions. "
        "Consequently, changing the support cutoffs primarily changes **which skills occupy the Top-10 slots** "
        "rather than the length of the chart."
    )
    add()
    add("### A. What Happens When Thresholds Are Lowered (Admitting Low-Prevalence / Low-Support Skills)")
    add()

    # Verify exact stats for concrete examples
    de_stats = all_skills_by_cat["data_engineering"]
    cassandra_de = find_skill(de_stats, "Cassandra")
    snowflake_de = find_skill(de_stats, "Snowflake")

    ai_stats = all_skills_by_cat["ai_engineering"]
    go_ai = find_skill(ai_stats, "Go")
    k8s_ai = find_skill(ai_stats, "Kubernetes")

    da_stats = all_skills_by_cat["data_analytics"]
    superset_da = find_skill(da_stats, "Apache Superset")

    ds_stats = all_skills_by_cat["data_science"]
    julia_ds = find_skill(ds_stats, "Julia")
    llm_ds = find_skill(ds_stats, "LLMs / Generative AI")

    add(
        f"1. **`Cassandra` vs. `Snowflake` in `Data Engineering` ($N = 15,090$):**\n"
        f"   - At the current `(20, 1.5%)` cutoff, **`Snowflake`** ($N = {snowflake_de['count']:,}$, "
        f"prevalence **{snowflake_de['prevalence'] * 100:.2f}%**, lift **{snowflake_de['lift']:.2f}×**) "
        f"holds Rank #10 in the `Data Engineering` Top 10.\n"
        "   - When minimum prevalence is lowered to **`0.5%`** (for any $N_{\\min} \\in \\{5, 10, 20, 30, 50\\}$), "
        f"**`Cassandra`** ($N = {cassandra_de['count']:,}$, prevalence **{cassandra_de['prevalence'] * 100:.2f}%**, "
        f"lift **{cassandra_de['lift']:.2f}×**) becomes eligible, enters at **Rank #7** (behind `Apache Spark` [29.51%] "
        f"and `Terraform` [9.93%], which share `1.29×` rounded lift with higher prevalence), and pushes **`Snowflake`** "
        f"(present in over $20\\times$ as many Data Engineering postings) out of the Top-10 chart to Rank #11."
    )
    add(
        f"2. **`Go` vs. `Kubernetes` in `AI Engineering` ($N = 2,314$):**\n"
        f"   - At the current `(20, 1.5%)` cutoff, **`Kubernetes`** ($N = {k8s_ai['count']:,}$, "
        f"prevalence **{k8s_ai['prevalence'] * 100:.2f}%**, lift **{k8s_ai['lift']:.2f}×**) holds Rank #10 in `AI Engineering`.\n"
        f"   - When thresholds are lowered to **`N >= 10, Prevalence >= 0.5%`** (or `N >= 5, Prevalence >= 0.5%`), "
        f"**`Go`** ($N = {go_ai['count']:,}$, prevalence **{go_ai['prevalence'] * 100:.2f}%**, lift **{go_ai['lift']:.2f}×**) "
        f"enters at **Rank #5** and displaces **`Kubernetes`** out of the Top-10 chart to Rank #11 "
        "(while **`XGBoost`** [$N = 16$, $0.69\\%$, $1.23\\times$] also enters the `AI Engineering` eligible pool outside the Top 10)."
    )
    add(
        f"3. **Additional Low-Support / Low-Prevalence Admissions:**\n"
        "   - In `Data Analytics`, lowering minimum prevalence to **`1.0%`** or **`0.5%`** (for $N_{\\min} \\in \\{5, 10, 20\\}$, "
        "i.e., when the minimum-postings cutoff is at most 20) admits **`Apache Superset`** "
        f"($N = {superset_da['count']}$, prevalence **{superset_da['prevalence'] * 100:.2f}%**, lift **{superset_da['lift']:.2f}×**) "
        "at **Rank #5**, expanding the `Data Analytics` chart from 9 to 10 displayed skills.\n"
        f"   - In `ML/AI`, lowering thresholds to **`N >= 10, Prevalence >= 1.0%`** (or `0.5%`) admits **`Redis`** ($N = 15$, $1.33\\%$, $2.02\\times$) "
        f"and **`Elasticsearch`** ($N = 16$, $1.41\\%$, $1.24\\times$) into the eligible pool outside the Top 10 "
        "(increasing `ML/AI` eligible skills from 22 to 24 without changing the Top 10).\n"
        f"   - Without support thresholds (`N >= 1, Prevalence >= 0.0%`), sub-10-posting skills such as **`Julia`** "
        f"in `Data Science` ($N = {julia_ds['count']}$, prevalence **{julia_ds['prevalence'] * 100:.2f}%**, lift **{julia_ds['lift']:.2f}×**) "
        f"jump directly into the Top 10 at Rank #7 (displacing **`LLMs / Generative AI`** with $N = {llm_ds['count']:,}$, {llm_ds['prevalence'] * 100:.2f}%)."
    )
    add()
    add("### B. What Happens When Thresholds Are Raised (Removing Plausible Specialist Skills)")
    add()

    ml_stats = all_skills_by_cat["ml_ai"]
    opencv_ml = find_skill(ml_stats, "OpenCV")
    xgboost_ml = find_skill(ml_stats, "XGBoost")
    metabase_da = find_skill(da_stats, "Metabase")
    redis_ai = find_skill(ai_stats, "Redis")
    bash_de = find_skill(de_stats, "Bash / Shell")

    add(
        f"1. **`OpenCV` and `XGBoost` in `ML/AI` ($N = 1,132$):**\n"
        f"   - At `(20, 1.5%)`, **`OpenCV`** ($N = {opencv_ml['count']}$, prevalence **{opencv_ml['prevalence'] * 100:.2f}%**, "
        f"lift **{opencv_ml['lift']:.2f}×**) is Rank #1 and **`XGBoost`** ($N = {xgboost_ml['count']}$, "
        f"prevalence **{xgboost_ml['prevalence'] * 100:.2f}%**, lift **{xgboost_ml['lift']:.2f}×**) is Rank #8 in `ML/AI`.\n"
        f"   - Raising minimum postings from **`20` to `30`** (even while keeping prevalence at `1.5%`)—or raising minimum "
        f"prevalence to **`3.0%`**—eliminates **both `OpenCV` and `XGBoost`** from the `ML/AI` ranking (replaced in the Top 10 "
        f"by `LLMs / Generative AI` [2.28×] and `LangChain` [2.16×])."
    )
    add(
        f"2. **`Metabase` in `Data Analytics` ($N = 2,440$):**\n"
        f"   - At `(20, 1.5%)`, **`Metabase`** ($N = {metabase_da['count']}$, prevalence **{metabase_da['prevalence'] * 100:.2f}%**, "
        f"lift **{metabase_da['lift']:.2f}×**) is Rank #1 in `Data Analytics`.\n"
        f"   - Raising minimum prevalence to **`3.0%`** removes **`Metabase`**, shrinking the `Data Analytics` chart from 9 to 8 skills."
    )
    add(
        f"3. **`Redis` in `AI Engineering` and `Bash / Shell` in `Data Engineering`:**\n"
        f"   - Raising minimum prevalence from **`1.5%` to `2.0%`** (or raising minimum postings to **`50`**) removes "
        f"**`Redis`** ($N = {redis_ai['count']}$, prevalence **{redis_ai['prevalence'] * 100:.2f}%**, lift **{redis_ai['lift']:.2f}×**, Rank #6) "
        f"from `AI Engineering` (replaced in the Top 10 by `MLflow` [1.75×]). Raising minimum prevalence to **`3.0%`** additionally removes "
        "`C++` ($N = 69$, **2.98%**, **2.02×**, Rank #9) from the Top 10 and `R` ($N = 59$, **2.55%**, **1.19×**, Rank #17) from the eligible pool.\n"
        f"   - Raising minimum prevalence to **`3.0%`** removes **`Bash / Shell`** ($N = {bash_de['count']}$, "
        f"prevalence **{bash_de['prevalence'] * 100:.2f}%**, lift **{bash_de['lift']:.2f}×**, Rank #9) from the `Data Engineering` Top 10, "
        "along with **`Oracle DB`** ($N = 444$, **2.94%**, **1.24×**, Rank #11) and **`MongoDB`** ($N = 360$, **2.39%**, **1.23×**, Rank #12) "
        "from the eligible pool, bringing #13 **`dbt`** ($N = 2,218$, **14.70%**, **1.22×**) into the Top 10 at Rank #10."
    )
    add()
    add("### C. Summary Table of Top-10 and Eligible-Pool Transitions Across Key Regimes")
    add()
    add(
        "| Occupation | Looser (`N >= 10, P >= 0.5%`) vs. Baseline (`20, 1.5%`) | "
        "Stricter Count (`N >= 30, P >= 1.5%`) vs. Baseline | "
        "Stricter Prevalence (`N >= 20, P >= 3.0%`) vs. Baseline |"
    )
    add("| :--- | :--- | :--- | :--- |")

    regime_specs = [
        (10, 0.005),
        (30, 0.015),
        (20, 0.030),
    ]
    for cid, cname in CATEGORIES:
        base_top10 = [s["canonical"] for s in baseline_row["top10"][cid]]
        base_elig = [s["canonical"] for s in baseline_row["eligible"][cid]]
        cells_diff: List[str] = []
        for mc, mp in regime_specs:
            r_match = next(
                r
                for r in grid_rows
                if r["min_count"] == mc and math.isclose(r["min_prevalence"], mp)
            )
            cur_top10 = [s["canonical"] for s in r_match["top10"][cid]]
            cur_elig = [s["canonical"] for s in r_match["eligible"][cid]]
            entered_10 = [x for x in cur_top10 if x not in base_top10]
            left_10 = [x for x in base_top10 if x not in cur_top10]
            entered_el = [x for x in cur_elig if x not in base_elig]
            left_el = [x for x in base_elig if x not in cur_elig]

            parts: List[str] = []
            if entered_10 or left_10:
                if entered_10:
                    parts.append(f"**Top 10 In:** {', '.join(f'`{x}`' for x in entered_10)}")
                if left_10:
                    parts.append(f"**Top 10 Out:** {', '.join(f'`{x}`' for x in left_10)}")
                pool_notes: List[str] = []
                if len(cur_top10) != len(base_top10):
                    pool_notes.append(f"display {len(base_top10)} → {len(cur_top10)}")
                if entered_el:
                    pool_notes.append(f"Pool +{len(entered_el)}: {', '.join(f'`{x}`' for x in entered_el)}")
                if left_el:
                    pool_notes.append(f"Pool -{len(left_el)}: {', '.join(f'`{x}`' for x in left_el)}")
                cell_str = "; ".join(parts)
                if pool_notes:
                    cell_str += f" *({'; '.join(pool_notes)})*"
                cells_diff.append(cell_str)
            elif entered_el or left_el:
                if entered_el:
                    parts.append(f"Top 10 unchanged *(Pool +{len(entered_el)}: {', '.join(f'`{x}`' for x in entered_el)})*")
                if left_el:
                    parts.append(f"Top 10 unchanged *(Pool -{len(left_el)}: {', '.join(f'`{x}`' for x in left_el)})*")
                cells_diff.append("; ".join(parts))
            else:
                cells_diff.append("No change")

        add(f"| **{cname}** | {cells_diff[0]} | {cells_diff[1]} | {cells_diff[2]} |")

    add()
    add("---")
    add()
    add("## 6. Methodological Caveats & Interpretation")
    add()
    add(
        "1. **Heuristic Design Choice, Not Statistical Optimality:**\n"
        "   The `N >= 20` and `prevalence >= 1.5%` thresholds are practical display heuristics chosen to balance "
        "minimum sample support against specialist skill coverage in this **observed EU-27 job-posting corpus**. "
        "They are not statistically optimal cutoffs and do not represent inferential significance tests."
    )
    add(
        "2. **Low-Support and Low-Prevalence vs. \"Noise\":**\n"
        "   All 52 canonical skills in the controlled vocabulary are legitimate technical tools. Skills excluded by the "
        "thresholds (such as `Go` with $N=18$ in AI Engineering, `Cassandra` with $0.79\\%$ in Data Engineering, or "
        "`Apache Superset` with $1.11\\%$ in Data Analytics) are **low-support** or **low-prevalence** within those categories—"
        "not extraction noise."
    )
    add(
        "3. **`Data Engineering` Corpus Dominance ($65.7\\%$) and Lift Compression:**\n"
        f"   Because `Data Engineering` accounts for **{category_counts['data_engineering']:,} of the {total_postings:,} postings "
        f"({category_counts['data_engineering'] / total_postings * 100:.1f}%)**, the corpus-wide baseline $P(\\text{{skill}} \\mid \\text{{corpus}})$ "
        "is heavily weighted toward Data Engineering. Mathematically, the maximum possible lift for any skill in `Data Engineering` "
        f"is bounded at $1 / ({category_counts['data_engineering']} / {total_postings}) = "
        f"{total_postings / category_counts['data_engineering']:.2f}\\times$. As a result, `Data Engineering` lift scores cluster tightly "
        "between $1.01\\times$ and $1.37\\times$, whereas smaller categories like `ML/AI` ($4.9\\%$ of the corpus) reach lifts up to $11.60\\times$."
    )
    add(
        "4. **Non-Representativeness of the Observed Corpus:**\n"
        "   All prevalence and lift values describe patterns within the audited FreeHire snapshot of 22,985 postings and "
        "do not estimate the true occupational or geographic distribution of the broader EU labour market."
    )
    add()
    add("---")
    add()
    add("## 7. Reproducibility")
    add()
    add("Run the sensitivity analysis script from the repository root:")
    add()
    add("```bash")
    add("uv run python analysis/sensitivity_analysis.py")
    add("```")
    add()

    return "\n".join(lines)


def print_console_summary(
    total_postings: int,
    category_counts: Dict[str, int],
    all_skills_by_cat: Dict[str, List[Dict[str, Any]]],
    grid_rows: List[Dict[str, Any]],
) -> None:
    """Prints a concise verification summary to stdout."""
    print("=" * 96)
    print(f"EU DATA SKILL DEMAND - THRESHOLD SENSITIVITY ANALYSIS (N_corpus = {total_postings:,})")
    print("=" * 96)
    print("\n1. Category Sizes & Effective Minimum Postings at (N >= 20, Prevalence >= 1.5%):")
    for cid, cname in CATEGORIES:
        n_cat = category_counts[cid]
        req_15 = math.ceil(n_cat * 0.015)
        eff = max(20, req_15)
        print(
            f"   - {cname:18} ({cid:16}): N = {n_cat:6,d} ({n_cat/total_postings*100:4.1f}%) | "
            f"1.5% = {n_cat*0.015:5.1f} postings | Effective floor = {eff:3d} postings"
        )

    print("\n2. 25-Combination Sensitivity Grid: Eligible Pairs [Displayed Top-10]")
    header = (
        f"{'Min N':>7} | {'Min Prev':>8} | {'Total':>10} | "
        + " | ".join(f"{cname:>16}" for _, cname in CATEGORIES)
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in grid_rows:
        mc = r["min_count"]
        mp = r["min_prevalence"]
        tot_str = f"{r['total_eligible_pairs']:2d} [{r['total_displayed_top10']:2d}]"
        cat_strs = [
            f"{len(r['eligible'][cid]):2d} [{len(r['top10'][cid]):2d}]"
            for cid, _ in CATEGORIES
        ]
        marker = " <-- CURRENT (20, 1.5%)" if (mc == 20 and math.isclose(mp, 0.015)) else ""
        print(
            f"{mc:7d} | {mp*100:7.1f}% | {tot_str:>10} | "
            + " | ".join(f"{cs:>16}" for cs in cat_strs)
            + marker
        )
    print("-" * len(header))

    print("\n3. Key Verified Case Studies:")
    de_stats = all_skills_by_cat["data_engineering"]
    cass = find_skill(de_stats, "Cassandra")
    snow = find_skill(de_stats, "Snowflake")
    print(
        f"   - Data Engineering: Cassandra (N={cass['count']}, {cass['prevalence']*100:.2f}%, Lift={cass['lift']:.2f}x) "
        f"vs. Snowflake (N={snow['count']}, {snow['prevalence']*100:.2f}%, Lift={snow['lift']:.2f}x)"
    )

    ai_stats = all_skills_by_cat["ai_engineering"]
    go_s = find_skill(ai_stats, "Go")
    k8s_s = find_skill(ai_stats, "Kubernetes")
    print(
        f"   - AI Engineering:   Go (N={go_s['count']}, {go_s['prevalence']*100:.2f}%, Lift={go_s['lift']:.2f}x) "
        f"vs. Kubernetes (N={k8s_s['count']}, {k8s_s['prevalence']*100:.2f}%, Lift={k8s_s['lift']:.2f}x)"
    )

    ml_stats = all_skills_by_cat["ml_ai"]
    ocv = find_skill(ml_stats, "OpenCV")
    xgb = find_skill(ml_stats, "XGBoost")
    print(
        f"   - ML/AI:            OpenCV (N={ocv['count']}, {ocv['prevalence']*100:.2f}%, Lift={ocv['lift']:.2f}x) "
        f"& XGBoost (N={xgb['count']}, {xgb['prevalence']*100:.2f}%, Lift={xgb['lift']:.2f}x)"
    )

    da_stats = all_skills_by_cat["data_analytics"]
    meta = find_skill(da_stats, "Metabase")
    print(
        f"   - Data Analytics:   Metabase (N={meta['count']}, {meta['prevalence']*100:.2f}%, Lift={meta['lift']:.2f}x)"
    )


def main() -> None:
    total_postings, category_counts, all_skills_by_cat = compute_skill_stats_from_raw(
        RAW_DATA_PATH, VOCAB_PATH
    )
    verified = verify_against_precomputed_summary(all_skills_by_cat, SUMMARY_PATH)
    grid_rows = evaluate_grid(all_skills_by_cat)

    print_console_summary(total_postings, category_counts, all_skills_by_cat, grid_rows)
    if verified:
        print("\n[OK] Verified 100% exact match with data/processed/analytics_summary.json.")

    report_md = build_report_markdown(
        total_postings, category_counts, all_skills_by_cat, grid_rows
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"[OK] Wrote sensitivity report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
