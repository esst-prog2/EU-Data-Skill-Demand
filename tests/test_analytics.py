"""
tests/test_analytics.py

Unit tests for analytical core logic across four designated pytest areas:
1. Hybrid skill extraction
2. Prevalence and lift calculation
3. Distinctive-skill support and noise filtering
4. Geographic N >= 300 thresholding
"""

import pytest
from src.analytics import (
    SkillVocabulary,
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

