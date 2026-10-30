"""
tests/test_analytics.py

Unit tests for analytical core logic across four designated pytest areas:
1. Hybrid skill extraction
2. Prevalence and lift calculation
3. Distinctive-skill support and noise filtering
4. Geographic N >= 300 thresholding
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from src.analytics import (
    CATEGORY_NAMES,
    EU_COUNTRIES,
    EU27_COUNTRIES,
    EU27_COUNTRY_NAMES,
    OCCUPATIONAL_CATEGORIES,
    SkillVocabulary,
    atomic_dump_json,
    compute_category_skill_stats,
    compute_lift,
    compute_prevalence,
    extract_skills_from_posting,
    filter_distinctive_skills,
    filter_eligible_countries,
    filter_skills_by_family,
    prepare_scatter_data,
    rank_distinctive_skills,
    rank_in_demand_skills,
    SKILL_FAMILIES,
    SENIORITY_LEVELS,
    SENIORITY_DISPLAY_NAMES,
    extract_posting_record,
    filter_postings_population,
    compute_population_kpis,
    compute_population_skill_stats,
    get_skills_for_family,
    filter_postings_by_skill_family,
    compute_file_sha256,
    compute_extraction_fingerprint,
    validate_postings_cache,
    save_postings_cache,
    load_or_create_postings_cache,
    extract_posting_records_batch,
    EXTRACTION_PIPELINE_VERSION,
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

    def test_r_genuine_description_mentions_and_variations(self, production_vocabulary):
        """Genuine mentions of R in descriptions (R, R programming, R language, R/Python, RStudio) are extracted."""
        cases = [
            ("Candidates must know SQL, Python, and R.", {"SQL", "Python", "R"}),
            ("Strong experience with R programming and statistical inference.", {"R"}),
            ("Proficiency in the R language is required.", {"R"}),
            ("Tools: Python/R, Docker, and Git.", {"Python", "R", "Docker", "Git"}),
            ("Experience with RStudio and R shiny applications.", {"R"}),
        ]
        for desc, expected in cases:
            posting = {"title": "Analyst", "skills": [], "description": desc}
            extracted = extract_skills_from_posting(posting, production_vocabulary)
            for skill in expected:
                assert skill in extracted, f"Expected {skill} in {extracted} for {desc!r}"

    def test_r_aliases_normalize_to_canonical(self, production_vocabulary):
        """Native tag aliases for R (r-project, r-lang, r-language, r-programming) normalize to canonical 'R'."""
        aliases = ["r-project", "r-lang", "r-language", "r-programming"]
        for alias in aliases:
            posting = {"title": "Analyst", "skills": [alias], "description": ""}
            extracted = extract_skills_from_posting(posting, production_vocabulary)
            assert extracted == {"R"}, f"Alias {alias} did not normalize to 'R'"

    def test_r_false_positives_prevented(self, production_vocabulary):
        """Contexts where R does not mean the programming language are excluded."""
        non_r_descriptions = [
            "Leading our European R&D initiatives across product lines.",
            "Responsible for processing invoices in our A/R department.",
            "Diagnostics for hardware revision Model R-200.",
            "Tracking serial batch R/1204 in logistics.",
            "System build R.10 release notes.",
            "Compensation: R$ 8,000 per month gross.",
        ]
        for desc in non_r_descriptions:
            posting = {"title": "Engineer", "skills": [], "description": desc}
            extracted = extract_skills_from_posting(posting, production_vocabulary)
            assert "R" not in extracted, f"False positive 'R' extracted from: {desc!r}"

    def test_extract_posting_record_includes_description_fallback_for_r_and_excel(self, production_vocabulary):
        """extract_posting_record utilizes hybrid extraction so R and Excel in descriptions are detected."""
        raw_p = {
            "_collection_country": "DE",
            "_collection_category": "data_science",
            "enrichment": {"seniority": "senior"},
            "skills": ["python"],
            "description": "Must have expertise in advanced Excel modeling and R programming.",
        }
        rec = extract_posting_record(raw_p, production_vocabulary)
        assert rec["country"] == "DE"
        assert rec["category"] == "data_science"
        assert rec["seniority"] == "senior"
        assert rec["skills"] == {"Python", "R", "Excel"}

    def test_cpp_regex_positive_cases(self, production_vocabulary):
        """
        C++ regex boundary fix: C++ mentions in descriptions are reliably extracted
        across various common syntactic contexts (spaces, punctuation, versions, slashes).
        """
        positive_cases = [
            ("Must have strong skills in C++.", "C++"),
            ("We are looking for a C++ programming expert.", "C++"),
            ("Senior C++ developer wanted for low-latency engine.", "C++"),
            ("Experience with C++ and Python is required.", "C++"),
            ("Stack includes C++/Java backend services.", "C++"),
            ("Proficiency in cpp for algorithms.", "C++"),
            ("Core competencies: C++, Python, SQL.", "C++"),
            ("Hands-on development in (C++) environments.", "C++"),
            ("Expert in modern C++17 or newer standards.", "C++"),
        ]
        for desc, expected_skill in positive_cases:
            posting = {"title": "Software Engineer", "skills": [], "description": desc}
            extracted = extract_skills_from_posting(posting, production_vocabulary)
            assert expected_skill in extracted, f"Failed to extract {expected_skill} from {desc!r}"

    def test_cpp_regex_negative_cases(self, production_vocabulary):
        """
        C++ regex boundary fix: Unrelated patterns must NOT trigger false positive C++ extraction.
        """
        negative_cases = [
            "We listen to music++ at the office.",
            "Evaluating C+++ candidate architectures.",
            "Using libcpp standard library internals.",
            "Static analysis with cppcheck utility.",
            "Solving A+B algorithmic challenges.",
            "Experience with C# and .NET framework.",
        ]
        for desc in negative_cases:
            posting = {"title": "Developer", "skills": [], "description": desc}
            extracted = extract_skills_from_posting(posting, production_vocabulary)
            assert "C++" not in extracted, f"False positive 'C++' extracted from {desc!r}"


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


# ==============================================================================
# Area 8: Atomic JSON Output Serialization
# ==============================================================================

class TestAtomicDumpJson:
    """Verifies atomic write-and-replace behavior and failure preservation for JSON outputs."""

    def test_successful_json_output_and_formatting(self, tmp_path: Path):
        dest = tmp_path / "output.json"
        data = {
            "title": "Data Scientist",
            "count": 42,
            "skills": ["Python", "SQL"],
            "country": "Czechia",
            "unicode_text": "Příliš žluťoučký kůň",
        }
        atomic_dump_json(data, dest, indent=2, ensure_ascii=False)

        assert dest.exists()
        raw_text = dest.read_text(encoding="utf-8")
        assert "Příliš žluťoučký kůň" in raw_text
        assert '  "title": "Data Scientist"' in raw_text
        loaded = json.loads(raw_text)
        assert loaded == data

        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_creation_of_destination_that_does_not_already_exist(self, tmp_path: Path):
        dest = tmp_path / "nested" / "sub_dir" / "created.json"
        assert not dest.exists()
        assert not dest.parent.exists()

        atomic_dump_json({"status": "created"}, dest)
        assert dest.exists()
        assert json.loads(dest.read_text(encoding="utf-8")) == {"status": "created"}

    def test_serialization_failure_preserves_existing_destination(self, tmp_path: Path):
        dest = tmp_path / "preexisting_serial_fail.json"
        original_content = '{\n  "version": 1,\n  "status": "valid"\n}'
        dest.write_text(original_content, encoding="utf-8")

        unserializable_payload = {"invalid_set": {"item1", "item2"}}

        with pytest.raises(TypeError):
            atomic_dump_json(unserializable_payload, dest)

        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == original_content

        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_temporary_file_write_failure_preserves_existing_destination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        dest = tmp_path / "preexisting_write_fail.json"
        original_content = '{\n  "original": "intact"\n}'
        dest.write_text(original_content, encoding="utf-8")

        def mock_dump_fail(*args, **kwargs):
            raise OSError("Simulated disk full during json.dump")

        monkeypatch.setattr(json, "dump", mock_dump_fail)

        with pytest.raises(OSError, match="Simulated disk full"):
            atomic_dump_json({"new": "data"}, dest)

        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == original_content

        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_cleanup_of_temporary_files_after_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        dest = tmp_path / "cleanup_target.json"

        def mock_dump_fail(*args, **kwargs):
            raise RuntimeError("Unexpected failure during serialization stream")

        monkeypatch.setattr(json, "dump", mock_dump_fail)

        with pytest.raises(RuntimeError, match="Unexpected failure during serialization stream"):
            atomic_dump_json({"key": "value"}, dest)

        assert not dest.exists()
        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_replacement_failure_preserves_existing_destination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        dest = tmp_path / "preexisting_replace_fail.json"
        original_content = '{\n  "pre_existing": true\n}'
        dest.write_text(original_content, encoding="utf-8")

        def mock_replace_fail(self, target):
            raise PermissionError("Simulated replacement failure")

        monkeypatch.setattr(Path, "replace", mock_replace_fail)

        with pytest.raises(PermissionError, match="Simulated replacement failure"):
            atomic_dump_json({"new": "replacement"}, dest)

        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == original_content
        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_fsync_failure_aborts_replacement_and_preserves_destination(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        dest = tmp_path / "preexisting_fsync_fail.json"
        original_content = '{\n  "status": "intact"\n}'
        dest.write_text(original_content, encoding="utf-8")

        def mock_fsync_fail(fd):
            raise OSError("Simulated fsync I/O failure")

        monkeypatch.setattr(os, "fsync", mock_fsync_fail)

        with pytest.raises(OSError, match="Simulated fsync I/O failure"):
            atomic_dump_json({"new": "data"}, dest)

        # Existing destination must remain untouched
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == original_content

        # Temporary file must be unlinked/cleaned up
        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_close_failure_during_exception_cleanup_preserves_original_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        dest = tmp_path / "preexisting_close_fail.json"
        original_content = '{\n  "status": "unaltered"\n}'
        dest.write_text(original_content, encoding="utf-8")

        unlink_attempted = False
        original_named_temp_file = tempfile.NamedTemporaryFile

        def mock_named_temp_file(*args, **kwargs):
            tf = original_named_temp_file(*args, **kwargs)
            orig_close = tf.close

            def faulty_close():
                orig_close()  # Close underlying handle so unlink is permitted on Windows
                raise OSError("Simulated close error during exception cleanup")

            tf.close = faulty_close
            return tf

        monkeypatch.setattr(tempfile, "NamedTemporaryFile", mock_named_temp_file)

        orig_unlink = Path.unlink

        def spy_unlink(path_self, *args, **kwargs):
            nonlocal unlink_attempted
            unlink_attempted = True
            return orig_unlink(path_self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", spy_unlink)

        with pytest.raises(TypeError, match="not JSON serializable"):
            atomic_dump_json({"unserializable_set": {1, 2, 3}}, dest)

        # Cleanup must have been attempted despite close failure
        assert unlink_attempted is True

        # Existing destination must remain untouched
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == original_content

        # Temporary file must be unlinked
        temp_files = list(tmp_path.glob(".*.tmp")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0


# ==============================================================================
# Area 9: Skill Family Filtering & Bivariate Scatter Plot Helpers
# ==============================================================================

class TestSkillFamilyFiltering:
    """Tests for filter_skills_by_family helper and SKILL_FAMILIES constant."""

    def test_skill_families_constant_matches_5_canonical_domains(self):
        expected = (
            "Programming languages",
            "Databases & data warehouses",
            "BI & visualization",
            "Cloud & infrastructure",
            "ML/AI frameworks & tools",
        )
        assert SKILL_FAMILIES == expected

    def test_filter_skills_by_family_all_families_or_none_returns_all(self):
        skills = [
            {"canonical": "Python", "skill_group": "Programming languages"},
            {"canonical": "SQL", "skill_group": "Databases & data warehouses"},
            {"canonical": "Power BI", "skill_group": "BI & visualization"},
        ]
        assert filter_skills_by_family(skills, None) == skills
        assert filter_skills_by_family(skills, "All Families") == skills
        assert filter_skills_by_family(skills, "all") == skills
        assert filter_skills_by_family(skills, "ALL FAMILIES") == skills

    def test_filter_skills_by_family_specific_family_filters_accurately(self):
        skills = [
            {"canonical": "Python", "skill_group": "Programming languages"},
            {"canonical": "R", "skill_group": "Programming languages"},
            {"canonical": "SQL", "skill_group": "Databases & data warehouses"},
            {"canonical": "AWS", "skill_group": "Cloud & infrastructure"},
        ]
        prog_skills = filter_skills_by_family(skills, "Programming languages")
        assert len(prog_skills) == 2
        assert {s["canonical"] for s in prog_skills} == {"Python", "R"}

        cloud_skills = filter_skills_by_family(skills, "Cloud & infrastructure")
        assert len(cloud_skills) == 1
        assert cloud_skills[0]["canonical"] == "AWS"

        bi_skills = filter_skills_by_family(skills, "BI & visualization")
        assert len(bi_skills) == 0

    def test_filter_skills_by_family_unrecognized_family_raises_value_error(self):
        skills = [{"canonical": "Python", "skill_group": "Programming languages"}]
        with pytest.raises(ValueError, match="Unrecognized skill family"):
            filter_skills_by_family(skills, "Invalid Family Name")

        with pytest.raises(ValueError, match="Unrecognized skill family"):
            filter_skills_by_family(skills, "")

    def test_filter_skills_by_family_handles_empty_or_none_skills(self):
        assert filter_skills_by_family([], "Programming languages") == []
        assert filter_skills_by_family(None, "Programming languages") == []
        assert filter_skills_by_family(None, None) == []


class TestFamilySkillReRanking:
    """Tests for within-family re-ranking helpers rank_in_demand_skills and rank_distinctive_skills."""

    def test_rank_in_demand_skills_sorts_by_prevalence_then_count(self):
        skills = [
            {"canonical": "SQL", "prevalence": 0.40, "count": 40},
            {"canonical": "Python", "prevalence": 0.70, "count": 70},
            {"canonical": "R", "prevalence": 0.40, "count": 45},
            {"canonical": "Bash", "prevalence": 0.10, "count": 10},
        ]
        ranked = rank_in_demand_skills(skills, top_n=3)
        assert len(ranked) == 3
        assert ranked[0]["canonical"] == "Python"
        assert ranked[1]["canonical"] == "R"
        assert ranked[2]["canonical"] == "SQL"

    def test_rank_in_demand_skills_handles_empty_and_non_finite_prevalence(self):
        assert rank_in_demand_skills([]) == []
        assert rank_in_demand_skills(None) == []

        skills_with_invalid = [
            {"canonical": "Valid", "prevalence": 0.5, "count": 50},
            {"canonical": "NaNPrev", "prevalence": float("nan"), "count": 10},
            {"canonical": "PosInfPrev", "prevalence": float("inf"), "count": 10},
            {"canonical": "NegInfPrev", "prevalence": float("-inf"), "count": 10},
            {"canonical": "BoolPrev", "prevalence": True, "count": 10},
            {"canonical": "StrPrev", "prevalence": "0.5", "count": 10},
        ]
        ranked = rank_in_demand_skills(skills_with_invalid)
        assert len(ranked) == 1
        assert ranked[0]["canonical"] == "Valid"

    def test_rank_in_demand_skills_handles_none_count_without_type_error(self):
        skills = [
            {"canonical": "SkillNone", "prevalence": 0.40, "count": None},
            {"canonical": "SkillZero", "prevalence": 0.40, "count": 0},
            {"canonical": "SkillHigh", "prevalence": 0.40, "count": 20},
            {"canonical": "SkillTop", "prevalence": 0.50, "count": None},
        ]
        ranked = rank_in_demand_skills(skills, top_n=4)
        assert len(ranked) == 4
        assert ranked[0]["canonical"] == "SkillTop"
        assert ranked[1]["canonical"] == "SkillHigh"
        assert ranked[2]["canonical"] == "SkillNone"
        assert ranked[3]["canonical"] == "SkillZero"

    def test_rank_distinctive_skills_applies_support_and_lift_criteria(self):
        skills = [
            {"canonical": "XGBoost", "count": 30, "prevalence": 0.03, "lift": 3.5},
            {"canonical": "PyTorch", "count": 50, "prevalence": 0.05, "lift": 2.1},
            {"canonical": "LowCount", "count": 15, "prevalence": 0.02, "lift": 5.0},
            {"canonical": "LowPrev", "count": 25, "prevalence": 0.010, "lift": 2.5},
            {"canonical": "LowLift", "count": 100, "prevalence": 0.50, "lift": 0.9},
        ]
        distinctive = rank_distinctive_skills(skills, top_n=10)
        assert len(distinctive) == 2
        assert distinctive[0]["canonical"] == "XGBoost"
        assert distinctive[1]["canonical"] == "PyTorch"

    def test_rank_distinctive_skills_returns_empty_when_none_qualify(self):
        skills = [
            {"canonical": "Rare", "count": 5, "prevalence": 0.005, "lift": 4.0},
            {"canonical": "Common", "count": 100, "prevalence": 0.50, "lift": 0.8},
        ]
        assert rank_distinctive_skills(skills) == []
        assert rank_distinctive_skills([]) == []
        assert rank_distinctive_skills(None) == []


class TestPrepareScatterData:
    """Tests for prepare_scatter_data helper."""

    def test_excludes_unobserved_zero_count_skills(self):
        skills = [
            {"canonical": "ActiveSkill", "count": 5, "prevalence": 0.05, "lift": 1.2, "skill_group": "Languages"},
            {"canonical": "ZeroSkill", "count": 0, "prevalence": 0.0, "lift": 0.0, "skill_group": "Languages"},
        ]
        data = prepare_scatter_data(skills, min_count=1)
        assert len(data) == 1
        assert data[0]["canonical"] == "ActiveSkill"

    def test_excludes_non_finite_missing_or_negative_lift(self):
        skills = [
            {"canonical": "Valid", "count": 10, "prevalence": 0.10, "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "MissingLift", "count": 10, "prevalence": 0.10, "lift": None, "skill_group": "Cloud"},
            {"canonical": "NaNLift", "count": 10, "prevalence": 0.10, "lift": float("nan"), "skill_group": "Cloud"},
            {"canonical": "InfLift", "count": 10, "prevalence": 0.10, "lift": float("inf"), "skill_group": "Cloud"},
            {"canonical": "NegLift", "count": 10, "prevalence": 0.10, "lift": -0.5, "skill_group": "Cloud"},
        ]
        data = prepare_scatter_data(skills)
        assert len(data) == 1
        assert data[0]["canonical"] == "Valid"

    def test_calculates_prevalence_pct_if_missing(self):
        skills = [
            {"canonical": "Python", "count": 25, "prevalence": 0.254, "lift": 1.3, "skill_group": "Languages"}
        ]
        data = prepare_scatter_data(skills)
        assert len(data) == 1
        assert data[0]["prevalence_pct"] == 25.4

    def test_validates_supplied_prevalence_pct_numeric_finite_non_negative(self):
        skills = [
            {"canonical": "ValidPct", "count": 10, "prevalence": 0.10, "prevalence_pct": 10.0, "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "MissingPct", "count": 10, "prevalence": 0.10, "prevalence_pct": None, "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "NaNPct", "count": 10, "prevalence": 0.10, "prevalence_pct": float("nan"), "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "PosInfPct", "count": 10, "prevalence": 0.10, "prevalence_pct": float("inf"), "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "NegInfPct", "count": 10, "prevalence": 0.10, "prevalence_pct": float("-inf"), "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "NegPct", "count": 10, "prevalence": 0.10, "prevalence_pct": -5.0, "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "BoolPct", "count": 10, "prevalence": 0.10, "prevalence_pct": True, "lift": 1.5, "skill_group": "Cloud"},
            {"canonical": "StrPct", "count": 10, "prevalence": 0.10, "prevalence_pct": "10.0", "lift": 1.5, "skill_group": "Cloud"},
        ]
        data = prepare_scatter_data(skills)
        canonicals = [d["canonical"] for d in data]
        assert set(canonicals) == {"ValidPct", "MissingPct"}
        by_name = {d["canonical"]: d for d in data}
        assert by_name["ValidPct"]["prevalence_pct"] == 10.0
        assert by_name["MissingPct"]["prevalence_pct"] == 10.0

    def test_flags_eligible_distinctive_correctly(self):
        skills = [
            # Qualified: N >= 20, Prev >= 1.5%, Lift > 1.0
            {"canonical": "Qualified", "count": 25, "prevalence": 0.02, "lift": 1.8, "skill_group": "Languages"},
            # Low count: N < 20
            {"canonical": "LowCount", "count": 10, "prevalence": 0.03, "lift": 2.5, "skill_group": "Languages"},
            # Low prev: Prev < 1.5%
            {"canonical": "LowPrev", "count": 22, "prevalence": 0.010, "lift": 1.5, "skill_group": "Languages"},
            # Below parity: Lift <= 1.0
            {"canonical": "BelowParity", "count": 100, "prevalence": 0.50, "lift": 0.95, "skill_group": "Languages"},
        ]
        data = prepare_scatter_data(skills)
        by_name = {d["canonical"]: d for d in data}

        assert by_name["Qualified"]["is_eligible_distinctive"] is True
        assert "Qualified Distinctive" in by_name["Qualified"]["support_status"]
        assert by_name["Qualified"]["marker_opacity"] == 1.0

        assert by_name["LowCount"]["is_eligible_distinctive"] is False
        assert "Low support" in by_name["LowCount"]["support_status"]
        assert by_name["LowCount"]["marker_opacity"] == 0.45

        assert by_name["LowPrev"]["is_eligible_distinctive"] is False
        assert "Sub-threshold prevalence" in by_name["LowPrev"]["support_status"]
        assert by_name["LowPrev"]["marker_opacity"] == 0.45

        assert by_name["BelowParity"]["is_eligible_distinctive"] is False
        assert "Below baseline parity" in by_name["BelowParity"]["support_status"]
        assert by_name["BelowParity"]["marker_opacity"] == 0.45

    def test_marker_size_scaled_between_8_and_22(self):
        skills = [
            {"canonical": "MaxSkill", "count": 100, "prevalence": 0.5, "lift": 1.0, "skill_group": "Languages"},
            {"canonical": "MinSkill", "count": 10, "prevalence": 0.05, "lift": 1.0, "skill_group": "Languages"},
        ]
        data = prepare_scatter_data(skills)
        by_name = {d["canonical"]: d for d in data}
        assert by_name["MaxSkill"]["marker_size"] == 22.0
        assert 8.0 <= by_name["MinSkill"]["marker_size"] < 22.0

    def test_prepare_scatter_data_empty_or_zero_division_guard(self):
        assert prepare_scatter_data([]) == []
        assert prepare_scatter_data(None) == []


class TestPostingPopulationFiltering:
    """Unit tests for filter_postings_population and extract_posting_record."""

    @pytest.fixture
    def sample_postings(self):
        return [
            {"country": "DE", "category": "data_science", "seniority": "senior", "skills": {"Python", "SQL"}},
            {"country": "DE", "category": "data_science", "seniority": None, "skills": {"Python"}},
            {"country": "DE", "category": "data_engineering", "seniority": "senior", "skills": {"Spark", "SQL"}},
            {"country": "FR", "category": "data_science", "seniority": "junior", "skills": {"Python", "R"}},
            {"country": "HU", "category": "data_analytics", "seniority": None, "skills": {"SQL", "Excel"}},
        ]

    def test_default_all_filters_returns_complete_population(self, sample_postings):
        res = filter_postings_population(sample_postings, country="All Countries", category="All Categories", seniority="All Seniorities")
        assert res["baseline_count"] == 5
        assert res["active_count"] == 5
        assert res["known_seniority_count"] == 3
        assert res["seniority_coverage_pct"] == 60.0

    def test_filter_by_country_isolates_country(self, sample_postings):
        res = filter_postings_population(sample_postings, country="DE")
        assert res["baseline_count"] == 3
        assert res["active_count"] == 3
        assert all(p["country"] == "DE" for p in res["active_postings"])
        assert res["known_seniority_count"] == 2
        assert res["seniority_coverage_pct"] == round(2 / 3 * 100, 1)

    def test_filter_by_multi_country(self, sample_postings):
        # Multiple countries selection
        res = filter_postings_population(sample_postings, country=["DE", "FR"])
        assert res["baseline_count"] == 4
        assert res["active_count"] == 4
        assert all(p["country"] in ("DE", "FR") for p in res["active_postings"])

        # Empty list defaults to all countries
        res_all = filter_postings_population(sample_postings, country=[])
        assert res_all["baseline_count"] == len(sample_postings)
        assert res_all["active_count"] == len(sample_postings)

    def test_filter_by_category_isolates_category(self, sample_postings):
        res = filter_postings_population(sample_postings, category="data_science")
        assert res["baseline_count"] == 3
        assert res["active_count"] == 3
        assert all(p["category"] == "data_science" for p in res["active_postings"])

    def test_combined_country_and_category_filter(self, sample_postings):
        res = filter_postings_population(sample_postings, country="DE", category="data_science")
        assert res["baseline_count"] == 2
        assert res["active_count"] == 2
        assert res["known_seniority_count"] == 1
        assert res["seniority_coverage_pct"] == 50.0

    def test_seniority_filtering_and_explicit_denominator(self, sample_postings):
        res = filter_postings_population(sample_postings, country="DE", category="data_science", seniority="senior")
        assert res["baseline_count"] == 2
        assert res["known_seniority_count"] == 1
        assert res["seniority_coverage_pct"] == 50.0
        assert res["active_count"] == 1
        assert res["active_postings"][0]["seniority"] == "senior"

    def test_empty_filter_match_returns_zero_counts_without_error(self, sample_postings):
        res = filter_postings_population(sample_postings, country="NONEXISTENT")
        assert res["baseline_count"] == 0
        assert res["active_count"] == 0
        assert res["known_seniority_count"] == 0
        assert res["seniority_coverage_pct"] == 0.0

    def test_extract_posting_record_handles_enrichment_and_raw(self):
        raw_p = {
            "_collection_country": "DE",
            "_collection_category": "data_science",
            "enrichment": {"seniority": "senior"},
            "skills": ["python", "sql", "unknown_tag"],
        }
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages", "aliases": ["python"]},
            {"canonical": "SQL", "category": "Databases & data warehouses", "aliases": ["sql"]},
        ]})
        rec = extract_posting_record(raw_p, vocab)
        assert rec["country"] == "DE"
        assert rec["category"] == "data_science"
        assert rec["seniority"] == "senior"
        assert rec["skills"] == {"Python", "SQL"}


class TestPopulationKPIsAndSkillStats:
    """Unit tests for compute_population_kpis and compute_population_skill_stats."""

    def test_compute_population_kpis(self):
        active = [
            {"country": "DE", "category": "data_science", "skills": {"Python", "SQL"}},
            {"country": "FR", "category": "data_science", "skills": {"Python"}},
        ]
        skills_stats = [
            {"canonical": "Python", "is_eligible_distinctive": True},
            {"canonical": "SQL", "is_eligible_distinctive": False},
        ]
        kpis = compute_population_kpis(active, corpus_total=10, active_skills_stats=skills_stats)
        assert kpis["active_postings_count"] == 2
        assert kpis["corpus_share_pct"] == 20.0
        assert kpis["represented_countries_count"] == 2
        assert kpis["detected_skills_count"] == 2
        assert kpis["qualified_distinctive_count"] == 1

    def test_compute_population_skill_stats(self):
        active = [
            {"country": "DE", "skills": {"Python", "SQL"}},
            {"country": "FR", "skills": {"Python"}},
        ]
        corpus_counts = {"Python": 5, "SQL": 2}
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages"},
            {"canonical": "SQL", "category": "Databases & data warehouses"},
        ]})
        stats = compute_population_skill_stats(active, corpus_counts, corpus_total=10, vocabulary=vocab)
        assert len(stats) == 2
        by_name = {s["canonical"]: s for s in stats}
        assert by_name["Python"]["count"] == 2
        assert by_name["Python"]["prevalence"] == 1.0
        assert by_name["Python"]["lift"] == 2.0
class TestSkillFamilyPostingFiltering:
    """Unit tests for get_skills_for_family and filter_postings_by_skill_family."""

    def test_get_skills_for_family(self):
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages"},
            {"canonical": "SQL", "category": "Databases & data warehouses"},
            {"canonical": "Power BI", "category": "BI & visualization"},
        ]})
        bi_skills = get_skills_for_family(vocab, "BI & visualization")
        assert bi_skills == {"Power BI"}

        empty_skills = get_skills_for_family(vocab, "All Families")
        assert empty_skills == set()

    def test_filter_postings_by_skill_family(self):
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages"},
            {"canonical": "SQL", "category": "Databases & data warehouses"},
            {"canonical": "Power BI", "category": "BI & visualization"},
        ]})
        postings = [
            {"id": 1, "category": "data_analytics", "skills": {"Power BI", "SQL"}},
            {"id": 2, "category": "data_engineering", "skills": {"Python", "SQL"}},
            {"id": 3, "category": "data_science", "skills": {"Python"}},
        ]

        # Filter by BI & visualization
        bi_filtered = filter_postings_by_skill_family(postings, "BI & visualization", vocab)
        assert len(bi_filtered) == 1
        assert bi_filtered[0]["id"] == 1

        # Filter by All Families returns all
        all_filtered = filter_postings_by_skill_family(postings, "All Families", vocab)
        assert len(all_filtered) == 3

class TestExtractionParityAndCacheIntegrity:
    """Unit and regression tests for extraction parity, fingerprinting, and cache invalidation."""

    def test_compute_file_sha256_known_content(self, tmp_path):
        test_file = tmp_path / "sample.txt"
        test_file.write_bytes(b"Hello world\n")
        digest = compute_file_sha256(test_file)
        import hashlib
        expected = hashlib.sha256(b"Hello world\n").hexdigest()
        assert digest == expected

    def test_compute_file_sha256_missing_file_returns_empty(self, tmp_path):
        missing = tmp_path / "nonexistent.txt"
        assert compute_file_sha256(missing) == ""

    def test_compute_extraction_fingerprint(self, tmp_path):
        raw = tmp_path / "raw.json"
        raw.write_text("{}", encoding="utf-8")
        vocab = tmp_path / "vocab.json"
        vocab.write_text("{}", encoding="utf-8")

        fp = compute_extraction_fingerprint(raw, vocab)
        assert "raw_sha256" in fp
        assert "vocab_sha256" in fp
        assert fp["pipeline_version"] == EXTRACTION_PIPELINE_VERSION
        assert len(fp["raw_sha256"]) == 64
        assert len(fp["vocab_sha256"]) == 64

    def test_validate_postings_cache_valid(self, tmp_path):
        cache_file = tmp_path / "cache.json"
        fp = {"raw_sha256": "abc", "vocab_sha256": "def", "pipeline_version": "v1"}
        records = [
            {"country": "DE", "category": "data_science", "seniority": "senior", "skills": {"Python", "SQL"}},
            {"country": "FR", "category": "data_analytics", "seniority": "junior", "skills": {"Excel"}},
        ]
        save_postings_cache(cache_file, records, fp)

        validated = validate_postings_cache(cache_file, fp)
        assert validated is not None
        assert len(validated) == 2
        assert validated[0]["country"] == "DE"
        assert validated[0]["skills"] == {"Python", "SQL"}
        assert isinstance(validated[0]["skills"], set)
        assert validated[1]["skills"] == {"Excel"}

    def test_validate_postings_cache_invalidates_on_raw_hash_mismatch(self, tmp_path):
        cache_file = tmp_path / "cache.json"
        fp_saved = {"raw_sha256": "original_hash", "vocab_sha256": "def", "pipeline_version": "v1"}
        records = [{"country": "DE", "category": "data_science", "seniority": None, "skills": {"Python"}}]
        save_postings_cache(cache_file, records, fp_saved)

        fp_expected = {"raw_sha256": "modified_hash", "vocab_sha256": "def", "pipeline_version": "v1"}
        assert validate_postings_cache(cache_file, fp_expected) is None

    def test_validate_postings_cache_invalidates_on_vocab_hash_mismatch(self, tmp_path):
        cache_file = tmp_path / "cache.json"
        fp_saved = {"raw_sha256": "raw_hash", "vocab_sha256": "old_vocab", "pipeline_version": "v1"}
        records = [{"country": "DE", "category": "data_science", "seniority": None, "skills": {"Python"}}]
        save_postings_cache(cache_file, records, fp_saved)

        fp_expected = {"raw_sha256": "raw_hash", "vocab_sha256": "new_vocab", "pipeline_version": "v1"}
        assert validate_postings_cache(cache_file, fp_expected) is None

    def test_validate_postings_cache_invalidates_on_pipeline_version_mismatch(self, tmp_path):
        cache_file = tmp_path / "cache.json"
        fp_saved = {"raw_sha256": "raw_hash", "vocab_sha256": "vocab_hash", "pipeline_version": "v1"}
        records = [{"country": "DE", "category": "data_science", "seniority": None, "skills": {"Python"}}]
        save_postings_cache(cache_file, records, fp_saved)

        fp_expected = {"raw_sha256": "raw_hash", "vocab_sha256": "vocab_hash", "pipeline_version": "v2"}
        assert validate_postings_cache(cache_file, fp_expected) is None

    def test_validate_postings_cache_handles_corrupted_json(self, tmp_path):
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{invalid_json: 123", encoding="utf-8")
        assert validate_postings_cache(corrupt_file, {}) is None

        non_dict_file = tmp_path / "list.json"
        non_dict_file.write_text("[]", encoding="utf-8")
        assert validate_postings_cache(non_dict_file, {}) is None

    def test_load_or_create_postings_cache_regenerates_when_invalid(self, tmp_path):
        raw_file = tmp_path / "raw.json"
        raw_file.write_text(json.dumps([
            {"id": "1", "_collection_country": "DE", "_collection_category": "data_science", "skills": ["python", "sql"]},
            {"id": "2", "_collection_country": "FR", "_collection_category": "data_analytics", "skills": [], "description": "Needs R programming and Excel."},
        ]), encoding="utf-8")

        vocab_file = tmp_path / "vocab.json"
        vocab_file.write_text(json.dumps({"skills": [
            {"canonical": "Python", "category": "Programming languages", "aliases": ["python"], "regex": r"\bpython\b"},
            {"canonical": "SQL", "category": "Databases & data warehouses", "aliases": ["sql"], "regex": r"\bsql\b"},
            {"canonical": "R", "category": "Programming languages", "aliases": ["r-lang"], "regex": r"\bR\b"},
            {"canonical": "Excel", "category": "BI & visualization", "aliases": ["excel"], "regex": r"\bexcel\b"},
        ]}), encoding="utf-8")

        cache_file = tmp_path / "cache.json"
        cache_file.write_text("CORRUPTED STALE CACHE", encoding="utf-8")

        # Calling load_or_create should detect corruption and regenerate fresh records
        records = load_or_create_postings_cache(cache_file, raw_file, vocab_file, max_workers=1)
        assert len(records) == 2
        assert records[0]["skills"] == {"Python", "SQL"}
        assert records[1]["skills"] == {"R", "Excel"}

        # And cache file should now be a valid JSON cache
        fp = compute_extraction_fingerprint(raw_file, vocab_file)
        cached_again = validate_postings_cache(cache_file, fp)
        assert cached_again is not None
        assert len(cached_again) == 2

    def test_extract_posting_records_batch_parity(self):
        postings = [
            {"_collection_country": "DE", "_collection_category": "data_science", "skills": ["python"], "description": "Also uses R."},
            {"_collection_country": "FR", "_collection_category": "data_analytics", "skills": ["sql"], "description": "Advanced Excel required."},
        ]
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages", "aliases": ["python"], "regex": r"\bpython\b"},
            {"canonical": "SQL", "category": "Databases & data warehouses", "aliases": ["sql"], "regex": r"\bsql\b"},
            {"canonical": "R", "category": "Programming languages", "aliases": ["r-lang"], "regex": r"\bR\b"},
            {"canonical": "Excel", "category": "BI & visualization", "aliases": ["excel"], "regex": r"\bexcel\b"},
        ]})

        seq = [extract_posting_record(p, vocab) for p in postings]
        batch = extract_posting_records_batch(postings, vocab, max_workers=1)
        assert seq == batch

    def test_filter_intersections_and_unique_posting_counts(self):
        postings = [
            {"id": "p1", "country": "DE", "category": "data_science", "seniority": "senior", "skills": {"Python", "R"}},
            {"id": "p2", "country": "DE", "category": "data_science", "seniority": "junior", "skills": {"Python"}},
            {"id": "p3", "country": "FR", "category": "data_science", "seniority": "senior", "skills": {"Python", "SQL"}},
            {"id": "p4", "country": "DE", "category": "data_analytics", "seniority": "senior", "skills": {"Excel", "SQL"}},
            {"id": "p5", "country": "ES", "category": "data_engineering", "seniority": None, "skills": {"Python", "SQL"}},
        ]
        vocab = SkillVocabulary({"skills": [
            {"canonical": "Python", "category": "Programming languages"},
            {"canonical": "R", "category": "Programming languages"},
            {"canonical": "SQL", "category": "Databases & data warehouses"},
            {"canonical": "Excel", "category": "BI & visualization"},
        ]})

        # Filter by Country DE + Category data_science + Seniority senior
        res = filter_postings_population(postings, country=["DE"], category="data_science", seniority="senior")
        assert res["baseline_count"] == 2  # p1, p2
        assert res["known_seniority_count"] == 2
        assert res["active_count"] == 1  # only p1
        assert res["active_postings"][0]["id"] == "p1"

        # Apply technical skill family filter
        prog_filtered = filter_postings_by_skill_family(res["active_postings"], "Programming languages", vocab)
        assert len(prog_filtered) == 1

        bi_filtered = filter_postings_by_skill_family(res["active_postings"], "BI & visualization", vocab)
        assert len(bi_filtered) == 0


class TestDashboardFilteringRegression:
    """Comprehensive regression tests for dashboard filtering dimensions and intentional exceptions."""

    @pytest.fixture
    def complex_corpus(self):
        return [
            {"id": "p1", "country": "DE", "category": "data_science", "seniority": "senior", "skills": {"Python", "PyTorch"}},
            {"id": "p2", "country": "DE", "category": "data_science", "seniority": "junior", "skills": {"Python", "R"}},
            {"id": "p3", "country": "DE", "category": "data_engineering", "seniority": "senior", "skills": {"Python", "Apache Spark", "SQL"}},
            {"id": "p4", "country": "FR", "category": "data_science", "seniority": "senior", "skills": {"Python", "SQL"}},
            {"id": "p5", "country": "FR", "category": "data_analytics", "seniority": None, "skills": {"Power BI", "Excel"}},
            {"id": "p6", "country": "ES", "category": "ml_ai", "seniority": "lead", "skills": {"Python", "PyTorch", "C++"}},
            {"id": "p7", "country": "IT", "category": "ai_engineering", "seniority": None, "skills": {"Python", "C++", "Docker"}},
            {"id": "p8", "country": "DE", "category": "data_analytics", "seniority": "middle", "skills": {"Tableau", "Looker"}},
        ]

    def test_country_filtering_single_multi_all_and_unrepresented(self, complex_corpus):
        # Single country
        de_res = filter_postings_population(complex_corpus, country=["DE"])
        assert de_res["active_count"] == 4
        assert all(p["country"] == "DE" for p in de_res["active_postings"])

        # Multiple countries
        multi_res = filter_postings_population(complex_corpus, country=["DE", "FR"])
        assert multi_res["active_count"] == 6
        assert all(p["country"] in ("DE", "FR") for p in multi_res["active_postings"])

        # All countries
        all_res = filter_postings_population(complex_corpus, country="All Countries")
        assert all_res["active_count"] == 8

        # Unrepresented country
        unrep_res = filter_postings_population(complex_corpus, country=["MT"])
        assert unrep_res["active_count"] == 0
        assert unrep_res["baseline_count"] == 0

    def test_category_filtering_single_and_all(self, complex_corpus):
        ds_res = filter_postings_population(complex_corpus, category="data_science")
        assert ds_res["active_count"] == 3
        assert all(p["category"] == "data_science" for p in ds_res["active_postings"])

        all_cat_res = filter_postings_population(complex_corpus, category="All Categories")
        assert all_cat_res["active_count"] == 8

    def test_seniority_filtering_and_missing_seniority_handling(self, complex_corpus):
        # Specific seniority
        senior_res = filter_postings_population(complex_corpus, seniority="senior")
        assert senior_res["active_count"] == 3
        assert all(p["seniority"] == "senior" for p in senior_res["active_postings"])
        # Baseline includes all postings regardless of seniority
        assert senior_res["baseline_count"] == 8
        assert senior_res["known_seniority_count"] == 6  # p5 and p7 have None

        # All seniorities retains postings with None seniority
        all_sen_res = filter_postings_population(complex_corpus, seniority="All Seniorities")
        assert all_sen_res["active_count"] == 8
        none_sen_in_active = [p for p in all_sen_res["active_postings"] if p["seniority"] is None]
        assert len(none_sen_in_active) == 2

    def test_skill_family_filtering_and_cross_family_postings(self, complex_corpus, production_vocabulary):
        # Postings with skills in 'Programming languages'
        prog_postings = filter_postings_by_skill_family(complex_corpus, "Programming languages", production_vocabulary)
        assert len(prog_postings) == 6

        # Postings with skills in 'BI & visualization'
        bi_postings = filter_postings_by_skill_family(complex_corpus, "BI & visualization", production_vocabulary)
        assert len(bi_postings) == 2
        assert {p["id"] for p in bi_postings} == {"p5", "p8"}

        # All Families returns everything unchanged
        all_family = filter_postings_by_skill_family(complex_corpus, "All Families", production_vocabulary)
        assert len(all_family) == 8

    def test_multi_filter_intersection(self, complex_corpus, production_vocabulary):
        # Country DE + Category data_science + Seniority senior
        res = filter_postings_population(
            complex_corpus,
            country=["DE"],
            category="data_science",
            seniority="senior",
        )
        assert res["baseline_count"] == 2  # DE data_science: p1 (senior), p2 (junior)
        assert res["known_seniority_count"] == 2
        assert res["active_count"] == 1  # p1
        assert res["active_postings"][0]["id"] == "p1"

        family_filtered = filter_postings_by_skill_family(
            res["active_postings"],
            "Programming languages",
            production_vocabulary,
        )
        assert len(family_filtered) == 1
        assert family_filtered[0]["id"] == "p1"

        # Filter by BI & visualization yields 0 cleanly
        bi_filtered = filter_postings_by_skill_family(
            res["active_postings"],
            "BI & visualization",
            production_vocabulary,
        )
        assert len(bi_filtered) == 0

    def test_intentional_exceptions_preserved(self, complex_corpus, production_vocabulary):
        # 1. Corpus baseline benchmark uses full corpus denominator
        corpus_total = len(complex_corpus)
        assert corpus_total == 8

        # 2. Distinctiveness Lift uses category prevalence / corpus prevalence
        p_ds = 3 / 3
        p_corpus = 6 / 8
        lift = compute_lift(p_ds, p_corpus)
        assert round(lift, 2) == 1.33

        # 3. Cross-country composition denominator is total country postings across all 5 categories
        de_postings = [p for p in complex_corpus if p["country"] == "DE"]
        assert len(de_postings) == 4
        ds_share = 2 / 4
        de_share = 1 / 4
        da_share = 1 / 4
        assert (ds_share + de_share + da_share) == 1.0
