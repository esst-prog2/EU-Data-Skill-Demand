"""
tests/test_analytics.py

Unit tests for analytical core logic across four designated pytest areas:
1. Hybrid skill extraction
2. Prevalence and lift calculation
3. Distinctive-skill support and noise filtering
4. Geographic N >= 300 thresholding
"""

from pathlib import Path

import pytest
from src.analytics import (
    CATEGORY_NAMES,
    EU_COUNTRIES,
    EU27_COUNTRIES,
    EU27_COUNTRY_NAMES,
    OCCUPATIONAL_CATEGORIES,
    SkillVocabulary,
    compute_category_skill_stats,
    compute_lift,
    compute_prevalence,
    extract_skills_from_posting,
    filter_distinctive_skills,
    filter_eligible_countries,
)


@pytest.fixture
def vocabulary():
    """Provides a controlled test vocabulary with aliases and regexes."""
    vocab_data = {
        "skills": [
            {
                "canonical": "Python",
                "category": "Programming languages",
                "aliases": ["python", "python3"],
                "regex": r"\bpython(?:3)?\b",
            },
            {
                "canonical": "SQL",
                "category": "Programming languages",
                "aliases": ["sql", "t-sql", "plsql"],
                "regex": r"\bsql\b",
            },
            {
                "canonical": "R",
                "category": "Programming languages",
                "aliases": ["r-project", "r-lang"],
                "regex": r"\b[Rr]\b|\b[Rr]\s*(?:programming|scripting|studio)\b",
            },
            {
                "canonical": "Excel",
                "category": "BI & visualization",
                "aliases": ["excel", "ms-excel"],
                "regex": r"\b(?:ms\s*)?excel\b",
            },
            {
                "canonical": "Power BI",
                "category": "BI & visualization",
                "aliases": ["powerbi", "power-bi", "power bi"],
                "regex": r"\bpower\s*bi\b",
            },
            {
                "canonical": "PyTorch",
                "category": "ML/AI frameworks & tools",
                "aliases": ["pytorch", "torch"],
                "regex": r"\bpytorch\b",
            },
            {
                "canonical": "Apache Spark",
                "category": "Cloud & infrastructure",
                "aliases": ["spark", "apache-spark", "pyspark"],
                "regex": r"\b(?:pyspark|apache\s+spark|spark)\b",
            },
        ]
    }
    return SkillVocabulary(vocab_data)


@pytest.fixture
def production_vocabulary():
    """Provides the actual production technical skill vocabulary."""
    vocab_path = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "skills_vocabulary.json"
    return SkillVocabulary.load_from_file(vocab_path)


# ==============================================================================
# Area 1: Hybrid Skill Extraction
# ==============================================================================

class TestHybridSkillExtraction:
    def test_readme_specification_sql_excel_present_python_absent(self, vocabulary):
        """
        README requirement: Given a posting whose description mentions SQL and Excel
        but not Python, skill extraction returns SQL and Excel as present and Python as absent.
        """
        posting = {
            "title": "Data Specialist",
            "skills": [],  # No native tags
            "description": "Candidates should have strong knowledge of SQL and advanced Excel skills.",
        }
        extracted = extract_skills_from_posting(posting, vocabulary)
        assert "SQL" in extracted
        assert "Excel" in extracted
        assert "Python" not in extracted

    def test_native_tag_alias_normalization(self, vocabulary):
        """Native tags with aliases normalize to canonical form."""
        posting = {
            "title": "BI Analyst",
            "skills": ["powerbi", "python3", "spark"],
            "description": "",
        }
        extracted = extract_skills_from_posting(posting, vocabulary)
        assert "Power BI" in extracted
        assert "Python" in extracted
        assert "Apache Spark" in extracted

    def test_description_fallback_for_untagged_tools(self, vocabulary):
        """Untagged tools like Excel or single-letter R are extracted from description."""
        posting = {
            "title": "Statistician",
            "skills": ["python"],  # Excel and R missing from tags
            "description": "Must be proficient in R programming and Microsoft Excel.",
        }
        extracted = extract_skills_from_posting(posting, vocabulary)
        assert "Python" in extracted
        assert "R" in extracted
        assert "Excel" in extracted

    def test_binary_deduplication(self, vocabulary):
        """Repeated mentions in tags and text are deduplicated to a single presence."""
        posting = {
            "title": "Python Developer",
            "skills": ["python", "python3"],
            "description": "We need Python, Python, and more Python! Also python3.",
        }
        extracted = extract_skills_from_posting(posting, vocabulary)
        # Should be a set with exactly 1 element
        assert extracted == {"Python"}

    def test_rd_department_mention_does_not_extract_r(self, production_vocabulary):
        """
        Homework 5 regression test: An advertisement mentioning R&D (Research & Development)
        without referring to the R programming language must not extract 'R', while
        explicit mentions of Python as a programming language must be extracted.
        """
        posting = {
            "title": "R&D Software Engineer",
            "skills": [],  # Untagged to exercise description regex fallback
            "description": "Join our R&D department building machine learning pipelines in Python.",
        }
        extracted = extract_skills_from_posting(posting, production_vocabulary)
        assert "Python" in extracted
        assert "R" not in extracted


# ==============================================================================
# Area 2: Prevalence and Lift Calculation
# ==============================================================================

class TestPrevalenceAndLift:
    def test_readme_specification_prevalence_and_lift_extremes(self):
        """
        README requirement: Given a skill appearing in every Data Engineering posting
        but no Data Analytics posting, category comparison shows 100% prevalence for DE
        and 0% for DA, with lift > 1 for DE and lift = 0 for DA.
        """
        total_de = 100
        total_da = 100
        total_corpus = total_de + total_da

        count_de = 100
        count_da = 0
        count_corpus = count_de + count_da  # 100 out of 200

        prev_de = compute_prevalence(count_de, total_de)
        prev_da = compute_prevalence(count_da, total_da)
        prev_corpus = compute_prevalence(count_corpus, total_corpus)

        assert prev_de == 1.0
        assert prev_da == 0.0
        assert prev_corpus == 0.5

        lift_de = compute_lift(prev_de, prev_corpus)
        lift_da = compute_lift(prev_da, prev_corpus)

        assert lift_de == 2.0  # 1.0 / 0.5 = 2.0 > 1
        assert lift_de > 1.0
        assert lift_da == 0.0

    def test_typical_lift_calculation(self):
        """Calculates standard lift multipliers accurately."""
        # e.g., Python in Data Science: 78% prevalence vs 50% corpus baseline -> 1.56x
        lift = compute_lift(0.78, 0.50)
        assert pytest.approx(lift, 0.01) == 1.56

    def test_zero_division_guard(self):
        """Prevalence and lift handle empty categories or 0% corpus prevalence safely."""
        assert compute_prevalence(0, 0) == 0.0
        assert compute_prevalence(5, 0) == 0.0
        assert compute_lift(0.20, 0.0) == 0.0
        assert compute_lift(0.0, 0.50) == 0.0


# ==============================================================================
# Area 3: Distinctive-Skill Support and Noise Filtering
# ==============================================================================

class TestDistinctiveSkillFiltering:
    def test_low_count_noise_disqualification(self):
        """A skill with high lift but fewer than 20 mentions is filtered out."""
        skill_stats = [
            {
                "canonical": "NicheTool",
                "count": 5,  # < 20 mentions
                "prevalence": 0.02,
                "lift": 5.0,
            },
            {
                "canonical": "PyTorch",
                "count": 50,  # >= 20 mentions
                "prevalence": 0.25,  # >= 1.5%
                "lift": 3.2,
            },
        ]
        distinctive = filter_distinctive_skills(skill_stats, min_count=20, min_prevalence=0.015)
        canonical_names = [s["canonical"] for s in distinctive]
        assert "PyTorch" in canonical_names
        assert "NicheTool" not in canonical_names

    def test_low_prevalence_noise_disqualification(self):
        """A skill with high lift but prevalence < 1.5% is filtered out."""
        skill_stats = [
            {
                "canonical": "RareLibrary",
                "count": 22,  # >= 20 mentions
                "prevalence": 0.008,  # < 1.5%
                "lift": 2.5,
            },
            {
                "canonical": "Scikit-learn",
                "count": 60,
                "prevalence": 0.03,  # >= 1.5%
                "lift": 2.2,
            },
        ]
        distinctive = filter_distinctive_skills(skill_stats, min_count=20, min_prevalence=0.015)
        canonical_names = [s["canonical"] for s in distinctive]
        assert "Scikit-learn" in canonical_names
        assert "RareLibrary" not in canonical_names

    def test_lift_must_be_strictly_greater_than_one(self):
        """Eligible skills must have lift > 1.0 to qualify as distinctive."""
        skill_stats = [
            {
                "canonical": "Python",
                "count": 100,
                "prevalence": 0.50,
                "lift": 1.4,  # Distinctive
            },
            {
                "canonical": "SQL",
                "count": 120,
                "prevalence": 0.60,
                "lift": 0.9,  # Common baseline, but lift <= 1.0
            },
            {
                "canonical": "Git",
                "count": 80,
                "prevalence": 0.40,
                "lift": 1.0,  # Boundary case: lift == 1.0 not > 1.0
            },
        ]
        distinctive = filter_distinctive_skills(skill_stats, min_count=20, min_prevalence=0.015)
        canonical_names = [s["canonical"] for s in distinctive]
        assert canonical_names == ["Python"]

    def test_ranking_order_and_top_n_cap(self):
        """Skills are ranked descending by lift and capped at top_n."""
        skill_stats = [
            {"canonical": f"Skill_{i}", "count": 50, "prevalence": 0.05, "lift": 1.1 + (i * 0.1)}
            for i in range(15)
        ]
        distinctive = filter_distinctive_skills(skill_stats, min_count=20, min_prevalence=0.015, top_n=10)
        assert len(distinctive) == 10
        # Highest lift should be first
        assert distinctive[0]["canonical"] == "Skill_14"
        assert distinctive[0]["lift"] == pytest.approx(2.5, 0.01)


# ==============================================================================
# Area 4: Geographic N >= 300 Thresholding
# ==============================================================================

class TestGeographicThresholding:
    def test_readme_specification_under_300_excluded(self):
        """
        README requirement: Given a country with fewer than 300 observed postings,
        it appears on the map with its raw count but is excluded from the
        occupational-composition comparison.
        """
        country_counts = {
            "HU": 120,  # < 300
            "DE": 2307,  # >= 300
            "RO": 280,  # < 300
            "ES": 4849,  # >= 300
        }
        eligible, excluded = filter_eligible_countries(country_counts, threshold=300)
        assert "DE" in eligible
        assert "ES" in eligible
        assert "HU" in excluded
        assert "RO" in excluded
        assert eligible["DE"] == 2307
        assert excluded["HU"] == 120

    def test_exact_threshold_boundary(self):
        """A country with exactly 300 postings is eligible."""
        country_counts = {"BE": 300, "AT": 299}
        eligible, excluded = filter_eligible_countries(country_counts, threshold=300)
        assert "BE" in eligible
        assert "AT" in excluded


# ==============================================================================
# Area 5: Category Skill Statistics Aggregation
# ==============================================================================

class TestComputeCategorySkillStats:
    """Tests for compute_category_skill_stats shared helper."""

    def test_computes_correct_prevalence_and_lift(self, vocabulary):
        category_counts = {"data_science": 100, "data_engineering": 200}
        category_skill_counts = {
            "data_science": {"Python": 70, "SQL": 40},
            "data_engineering": {"Python": 120, "SQL": 160},
        }
        corpus_skill_counts = {"Python": 190, "SQL": 200}
        total_postings = 300

        stats = compute_category_skill_stats(
            vocabulary=vocabulary,
            category_counts=category_counts,
            category_skill_counts=category_skill_counts,
            corpus_skill_counts=corpus_skill_counts,
            total_postings=total_postings,
            categories=["data_science", "data_engineering"],
        )

        assert "data_science" in stats
        assert "data_engineering" in stats

        ds_skills = {s["canonical"]: s for s in stats["data_science"]}
        # Python in DS: count=70, prev=0.7, corpus_prev=190/300=0.6333, lift=0.7/0.6333=1.11
        assert ds_skills["Python"]["count"] == 70
        assert ds_skills["Python"]["prevalence"] == pytest.approx(0.7, 0.001)
        assert ds_skills["Python"]["prevalence_pct"] == 70.0
        assert ds_skills["Python"]["lift"] == pytest.approx(1.11, 0.01)

        # SQL in DS: count=40, prev=0.4, corpus_prev=200/300=0.6667, lift=0.4/0.6667=0.60
        assert ds_skills["SQL"]["count"] == 40
        assert ds_skills["SQL"]["prevalence"] == pytest.approx(0.4, 0.001)
        assert ds_skills["SQL"]["prevalence_pct"] == 40.0
        assert ds_skills["SQL"]["lift"] == pytest.approx(0.60, 0.01)

        # Unobserved skill in DS (e.g. R)
        assert ds_skills["R"]["count"] == 0
        assert ds_skills["R"]["prevalence"] == 0.0
        assert ds_skills["R"]["lift"] == 0.0

    def test_handles_zero_postings_safely(self, vocabulary):
        stats = compute_category_skill_stats(
            vocabulary=vocabulary,
            category_counts={"empty_category": 0},
            category_skill_counts={},
            corpus_skill_counts={},
            total_postings=0,
            categories=["empty_category"],
        )
        assert "empty_category" in stats
        for s in stats["empty_category"]:
            assert s["count"] == 0
            assert s["prevalence"] == 0.0
            assert s["lift"] == 0.0

    def test_includes_all_requested_categories(self, vocabulary):
        categories = ["cat_a", "cat_b", "cat_c"]
        stats = compute_category_skill_stats(
            vocabulary=vocabulary,
            category_counts={},
            category_skill_counts={},
            corpus_skill_counts={},
            total_postings=10,
            categories=categories,
        )
        assert list(stats.keys()) == categories
        for cat in categories:
            assert len(stats[cat]) == len(vocabulary.skills)


# ==============================================================================
# Area 6: Occupational Categories Canonical Mapping
# ==============================================================================

class TestOccupationalCategories:
    """Verifies that the canonical occupational categories and display labels are well-formed."""

    def test_canonical_categories_match_specification(self):
        expected = {
            "data_analytics": "Data Analytics",
            "data_engineering": "Data Engineering",
            "data_science": "Data Science",
            "ml_ai": "ML/AI",
            "ai_engineering": "AI Engineering",
        }
        assert OCCUPATIONAL_CATEGORIES == expected
        assert CATEGORY_NAMES == expected
        assert len(OCCUPATIONAL_CATEGORIES) == 5

    def test_canonical_keys_and_labels_are_valid(self):
        for cat_id, label in OCCUPATIONAL_CATEGORIES.items():
            assert isinstance(cat_id, str) and cat_id.islower()
            assert isinstance(label, str) and len(label.strip()) > 0
            assert "_" not in label


# ==============================================================================
# Area 7: EU-27 Geographic Mapping Canonical Definitions
# ==============================================================================

class TestEU27CountryMapping:
    """Verifies that the canonical EU-27 country mapping is complete, valid, and consistent."""

    def test_canonical_eu27_mapping_has_27_unique_iso2_codes(self):
        assert len(EU27_COUNTRIES) == 27
        assert len(set(EU27_COUNTRIES.keys())) == 27

    def test_iso2_codes_and_country_names_are_well_formed(self):
        for code, name in EU27_COUNTRIES.items():
            assert isinstance(code, str) and len(code) == 2 and code.isupper() and code.isalpha()
            assert isinstance(name, str) and len(name.strip()) > 0

    def test_czechia_is_canonical_short_name(self):
        assert EU27_COUNTRIES["CZ"] == "Czechia"

    def test_aliases_match_canonical_mapping(self):
        assert EU_COUNTRIES == EU27_COUNTRIES
        assert EU27_COUNTRY_NAMES == EU27_COUNTRIES
