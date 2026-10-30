"""
tests/test_llm_regex_audit.py

Unit tests for offline LLM regular expression audit infrastructure:
- Deterministic sampling and reproducibility
- Benchmark leakage prevention and stratum separation
- Strict human label normalization (including boolean rejection)
- Empty/whitespace regex rejection and ReDoS safety heuristics
- Multiprocessing worker timeout protection against hangs
- Undefined precision/recall handling on zero denominators
- Regression warnings in human-readable Markdown reports
"""

from __future__ import annotations

import json
import time
from pathlib import Path
import pytest

from analysis.llm_regex_audit import (
    CANDIDATE_OUTPUT_JSON_SCHEMA,
    BenchmarkSnippet,
    CandidateProposal,
    DiscoverySnippet,
    EvaluationResult,
    GroundTruthStatus,
    SampleSnippet,
    build_audit_prompt,
    evaluate_candidate_proposal,
    extract_bounded_snippet,
    generate_audit_markdown_report,
    load_benchmark_snippets,
    normalize_human_label,
    sample_discovery_snippets,
    sample_skill_postings,
    validate_candidate_dict,
    validate_regex_safety,
)
from src.analytics import SkillVocabulary


@pytest.fixture
def mock_vocab():
    """Provides a small vocabulary with current R and Excel rules."""
    return SkillVocabulary({
        "skills": [
            {
                "canonical": "R",
                "category": "Programming languages",
                "aliases": ["r-project", "r-lang"],
                "regex": r"\b[Rr]\s*programming\b|(?<!\w)R(?!\w)",
            },
            {
                "canonical": "Excel",
                "category": "BI & visualization",
                "aliases": ["excel", "ms-excel"],
                "regex": r"\bexcel\b(?!\s+in\b)",
            },
        ]
    })


@pytest.fixture
def mock_postings():
    """Mock corpus of postings with varied description contexts."""
    return [
        {
            "id": "post_1",
            "_collection_category": "data_science",
            "_collection_country": "DE",
            "skills": ["python"],
            "description": "Senior position requiring Python and R programming for Bayesian analysis.",
        },
        {
            "id": "post_2",
            "_collection_category": "data_analytics",
            "_collection_country": "FR",
            "skills": [],
            "description": "Expert in Excel modeling and dashboards. Must not excel in procrastination.",
        },
        {
            "id": "post_3",
            "_collection_category": "ml_ai",
            "_collection_country": "ES",
            "skills": [],
            "description": "Join our R&D unit developing computer vision and modern C++ models.",
        },
        {
            "id": "post_4",
            "_collection_category": "data_engineering",
            "_collection_country": "IT",
            "skills": ["sql"],
            "description": "Candidates must excel in communication and data pipeline orchestration.",
        },
        {
            "id": "post_5",
            "_collection_category": "data_science",
            "_collection_country": "NL",
            "skills": [],
            "description": "Experience building R/Shiny microservices and statistical reporting in Excel VBA.",
        },
    ]


# ==============================================================================
# 1. Bounded Context Snippet Generation
# ==============================================================================

def test_extract_bounded_snippet_word_boundaries():
    text = "The candidate must have strong experience in Python and advanced Excel modeling."
    start = text.find("Excel")
    end = start + len("Excel")

    snip, span = extract_bounded_snippet(text, start, end, window=15)
    assert "Excel" in snip
    assert "modeling" in snip
    assert "advanced" in snip
    assert isinstance(snip, str)
    assert span[0] <= start
    assert span[1] >= end


def test_extract_bounded_snippet_empty_and_boundaries():
    assert extract_bounded_snippet("", 0, 0) == ("", (0, 0))

    short_text = "R programming"
    snip, span = extract_bounded_snippet(short_text, 0, 1, window=50)
    assert snip == "R programming"
    assert span == (0, 13)


def test_extract_bounded_snippet_normalizes_whitespace():
    multiline_text = "Skills required:\n\n* Python\n* R programming\n* SQL"
    pos = multiline_text.find("R")
    snip, _ = extract_bounded_snippet(multiline_text, pos, pos + 13, window=20)
    assert "\n" not in snip
    assert "R programming" in snip


# ==============================================================================
# 2. Strict Human Label Normalization
# ==============================================================================

def test_normalize_human_label_valid_codes():
    # Integer 1 and 0
    ok, code, raw = normalize_human_label(1)
    assert ok is True and code == 1 and raw == "1"

    ok, code, raw = normalize_human_label(0)
    assert ok is True and code == 0 and raw == "0"

    # String "1" and "0" with whitespace
    ok, code, raw = normalize_human_label("  1  ")
    assert ok is True and code == 1 and raw == "1"

    ok, code, raw = normalize_human_label("0")
    assert ok is True and code == 0 and raw == "0"

    # Unevaluable "u" and "U"
    ok, code, raw = normalize_human_label("u")
    assert ok is True and code is None and raw == "u"

    ok, code, raw = normalize_human_label("  U  ")
    assert ok is True and code is None and raw == "u"


def test_normalize_human_label_rejects_booleans_and_invalids():
    # Strict boolean rejection (Python bool is subclass of int!)
    ok, _, err = normalize_human_label(True)
    assert ok is False
    assert "boolean" in err.lower()

    ok, _, err = normalize_human_label(False)
    assert ok is False
    assert "boolean" in err.lower()

    # None, arbitrary strings, out-of-range ints
    ok, _, err = normalize_human_label(None)
    assert ok is False

    ok, _, err = normalize_human_label("positive")
    assert ok is False

    ok, _, err = normalize_human_label(2)
    assert ok is False


# ==============================================================================
# 3. Deterministic Sampling & Benchmark Leakage Prevention
# ==============================================================================

def test_deterministic_discovery_sampling_reproducibility(mock_postings, mock_vocab):
    samples_run1 = sample_discovery_snippets(
        mock_postings,
        "R",
        mock_vocab,
        seed=42,
        current_hits_n=2,
        near_miss_n=2,
        negative_controls_n=1,
    )
    samples_run2 = sample_discovery_snippets(
        mock_postings,
        "R",
        mock_vocab,
        seed=42,
        current_hits_n=2,
        near_miss_n=2,
        negative_controls_n=1,
    )

    assert len(samples_run1) == len(samples_run2)
    for s1, s2 in zip(samples_run1, samples_run2):
        assert isinstance(s1, DiscoverySnippet)
        assert s1.sample_id == s2.sample_id
        assert s1.posting_id == s2.posting_id
        assert s1.stratum == s2.stratum
        assert s1.snippet == s2.snippet


def test_excluded_posting_ids_prevent_leakage(mock_postings, mock_vocab):
    # If post_1 is in benchmark, it must NOT appear in discovery snippets
    discovery = sample_discovery_snippets(
        mock_postings,
        "R",
        mock_vocab,
        excluded_posting_ids={"post_1"},
        current_hits_n=5,
    )
    sampled_ids = {s.posting_id for s in discovery}
    assert "post_1" not in sampled_ids


def test_prompt_builder_rejects_benchmark_snippets(mock_vocab):
    # Benchmark snippet must cause prompt builder to raise ValueError immediately
    bench = BenchmarkSnippet(
        sample_id="bench_01",
        posting_id="p100",
        canonical_skill="R",
        ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
        snippet="Expert in R language.",
        source_dataset="r_validation.xlsx",
        human_label=1,
    )

    with pytest.raises(ValueError, match="leakage violation"):
        build_audit_prompt("R", mock_vocab, [bench])  # type: ignore


def test_discovery_snippet_forbids_human_ground_truth_status():
    # DiscoverySnippet dataclass itself rejects human benchmark statuses
    with pytest.raises(ValueError, match="Leakage Error"):
        DiscoverySnippet(
            sample_id="disc_01",
            posting_id="p101",
            canonical_skill="R",
            stratum="production_positive",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="R code",
            source_dataset="test",
        )


def test_load_benchmark_snippets_provenance():
    records = [
        {"id": "h_1", "description": "Expert in R statistical software.", "human_label": 1, "evidence_notes": "Valid mention"},
        {"id": "h_2", "description": "Director of R&D facilities.", "human_label": "0", "evidence_notes": "R&D noise"},
        {"id": "h_3", "description": "Short bio...", "human_label": "u", "evidence_notes": "Ambiguous"},
    ]

    benchmarks = load_benchmark_snippets(records, "R")
    assert len(benchmarks) == 3

    assert benchmarks[0].ground_truth_status == GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE
    assert benchmarks[0].human_label == 1
    assert benchmarks[0].evidence_notes == "Valid mention"

    assert benchmarks[1].ground_truth_status == GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE
    assert benchmarks[1].human_label == 0

    assert benchmarks[2].ground_truth_status == GroundTruthStatus.HUMAN_UNEVALUABLE
    assert benchmarks[2].human_label is None


def test_load_benchmark_snippets_invalid_label_raises():
    bad_records = [{"id": "h_bad", "description": "Some text", "human_label": True}]
    with pytest.raises(ValueError, match="Invalid human label"):
        load_benchmark_snippets(bad_records, "R")


# ==============================================================================
# 4. Candidate JSON Validation & Empty Regex Rejection
# ==============================================================================

def test_validate_candidate_dict_valid():
    valid_payload = {
        "canonical_skill": "Excel",
        "proposed_regex": r"\b(?:ms\s*|microsoft\s*)?excel\b(?!(\s+(?:in|at|within)\b))",
        "proposed_aliases": ["excel", "ms-excel", "excel-vba"],
        "explanation": "Guards against verbal usage while capturing Microsoft Excel mentions.",
        "positive_test_cases": ["Proficient in Microsoft Excel.", "Excel spreadsheets"],
        "negative_test_cases": ["He will excel in everything.", "Candidates excel at tests."],
        "false_positive_risks": ["Rare adjectives or idioms."],
        "confidence_score": 0.95,
        "human_review_required": ["Check if Excel VBA is tagged separately."],
    }
    is_valid, errors, proposal = validate_candidate_dict(valid_payload)
    assert is_valid is True
    assert errors == []
    assert proposal is not None
    assert proposal.canonical_skill == "Excel"
    assert proposal.proposed_aliases == ["excel", "ms-excel", "excel-vba"]
    assert proposal.confidence_score == 0.95


def test_validate_candidate_dict_missing_fields_and_invalid_types():
    bad_payload = {"proposed_regex": r"\br\b"}
    is_valid, errors, proposal = validate_candidate_dict(bad_payload)
    assert is_valid is False
    assert proposal is None
    assert any("canonical_skill" in e for e in errors)


def test_validate_regex_safety_empty_and_whitespace():
    is_safe, warnings = validate_regex_safety("")
    assert is_safe is False
    assert any("empty" in w.lower() for w in warnings)

    is_safe, warnings = validate_regex_safety("   \t\n  ")
    assert is_safe is False
    assert any("empty" in w.lower() for w in warnings)


def test_validate_regex_safety_catastrophic_nested_repetition():
    catastrophic_pat = r"(?:a+)+$"
    is_safe, warnings = validate_regex_safety(catastrophic_pat)
    assert is_safe is False
    assert any("redos" in w.lower() for w in warnings)


# ==============================================================================
# 5. Multiprocessing Worker Timeout Protection
# ==============================================================================

def test_evaluator_worker_timeout_protection(mock_vocab):
    # Simulates a scenario where worker evaluation exceeds hard timeout threshold
    # We pass a 0.0001s timeout to guarantee timeout trigger on Windows multiprocessing spawn
    postings = [
        {"id": f"p_{i}", "description": f"Some job posting text mention {i} with R programming."}
        for i in range(50)
    ]

    proposal = CandidateProposal(
        canonical_skill="R",
        proposed_regex=r"\bR\b",
        proposed_aliases=[],
        explanation="Test timeout",
        positive_test_cases=["R"],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.9,
        human_review_required=[],
    )

    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        postings,
        worker_timeout_sec=0.0001,  # Sub-millisecond hard timeout triggers timeout handling
    )

    assert result.worker_timeout_occurred is True
    assert result.safety_check_passed is False
    assert any("timed out" in w.lower() for w in result.safety_warnings)


def test_evaluator_worker_normal_completion(mock_vocab, mock_postings):
    proposal = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\bexcel\b(?!\s+in\b)",
        proposed_aliases=["excel"],
        explanation="Valid Excel pattern",
        positive_test_cases=["Expert in Excel."],
        negative_test_cases=["Candidates excel in multitasking."],
        false_positive_risks=[],
        confidence_score=1.0,
        human_review_required=[],
    )

    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        mock_postings,
        worker_timeout_sec=5.0,
    )

    assert result.worker_timeout_occurred is False
    assert result.is_valid_regex is True
    assert result.synthetic_tests_passed is True
    assert result.corpus_candidate_count > 0


# ==============================================================================
# 6. Undefined Benchmark Metrics Handling
# ==============================================================================

def test_evaluator_undefined_benchmark_metrics():
    vocab = SkillVocabulary({"skills": [{"canonical": "Excel", "regex": r"\bexcel\b"}]})

    # Case A: Predicted Positives == 0 (Precision denominator is zero -> None)
    proposal_matches_nothing = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\bnonexistent_keyword_xyz\b",
        proposed_aliases=[],
        explanation="Matches nothing",
        positive_test_cases=[],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.5,
        human_review_required=[],
    )

    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="p1",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Excel modeling",
            source_dataset="test",
            human_label=1,
        ),
        BenchmarkSnippet(
            sample_id="b2",
            posting_id="p2",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            snippet="excel in communication",
            source_dataset="test",
            human_label=0,
        ),
    ]

    res_no_pred = evaluate_candidate_proposal(
        proposal_matches_nothing,
        vocab,
        [],
        human_validated_samples=human_samples,
    )

    assert res_no_pred.ground_truth_metrics is not None
    # tp = 0, fp = 0 => precision should be None
    assert res_no_pred.ground_truth_metrics["precision"] is None
    # tp = 0, fn = 1 => recall should be 0.0
    assert res_no_pred.ground_truth_metrics["recall"] == 0.0

    # Case B: Actual Positives == 0 (Recall denominator is zero -> None)
    negative_only_samples = [
        BenchmarkSnippet(
            sample_id="b3",
            posting_id="p3",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            snippet="excel in leadership",
            source_dataset="test",
            human_label=0,
        )
    ]

    proposal_matches_something = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\bexcel\b",
        proposed_aliases=[],
        explanation="Matches",
        positive_test_cases=[],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.5,
        human_review_required=[],
    )

    res_no_actual = evaluate_candidate_proposal(
        proposal_matches_something,
        vocab,
        [],
        human_validated_samples=negative_only_samples,
    )

    assert res_no_actual.ground_truth_metrics is not None
    # tp = 0, fp = 1 => precision is 0.0
    assert res_no_actual.ground_truth_metrics["precision"] == 0.0
    # tp = 0, fn = 0 => recall should be None
    assert res_no_actual.ground_truth_metrics["recall"] is None


# ==============================================================================
# 7. Production Regression Warnings in Markdown Reports
# ==============================================================================

def test_reporter_flags_production_regression_and_na_metrics(mock_vocab):
    proposal = CandidateProposal(
        canonical_skill="R",
        proposed_regex=r"\b[Rr]\s*programming\b",
        proposed_aliases=[],
        explanation="Drops bare R mentions",
        positive_test_cases=["R programming"],
        negative_test_cases=["R&D"],
        false_positive_risks=[],
        confidence_score=0.85,
        human_review_required=[],
    )

    # Postings where current regex matches both, but candidate only matches post_1
    postings = [
        {"id": "post_keep", "description": "Requires R programming skills."},
        {"id": "post_dropped_1", "description": "Statistical modeling with R and Python."},
        {"id": "post_dropped_2", "description": "Advanced R for biostatistics."},
    ]

    # Benchmark with 0 predicted positives so precision is None
    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="h1",
            canonical_skill="R",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Requires bare R language knowledge",
            source_dataset="test",
            human_label=1,
        )
    ]

    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        postings,
        human_validated_samples=human_samples,
    )

    assert len(result.current_only_ids) == 2
    assert "post_dropped_1" in result.current_only_ids
    assert "post_dropped_2" in result.current_only_ids

    report_md = generate_audit_markdown_report(result, proposal)

    # Check regression warning banner
    assert "PRODUCTION REGRESSION WARNING" in report_md
    assert "drops `2` postings currently captured by production extraction" in report_md
    assert "`post_dropped_1`" in report_md
    assert "`post_dropped_2`" in report_md

    # Check N/A metric formatting
    assert "N/A (no predicted positive cases in benchmark)" in report_md


def test_reporter_flags_worker_timeout_banner():
    proposal = CandidateProposal(
        canonical_skill="R",
        proposed_regex=r"\bR\b",
        proposed_aliases=[],
        explanation="Test",
        positive_test_cases=[],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.5,
        human_review_required=[],
    )

    result = EvaluationResult(
        canonical_skill="R",
        candidate_regex=r"\bR\b",
        current_regex="",
        is_valid_regex=True,
        safety_check_passed=False,
        safety_warnings=["Timed out after 5.0s"],
        positive_test_results={},
        negative_test_results={},
        corpus_current_count=0,
        corpus_candidate_count=0,
        shared_ids_count=0,
        current_only_ids=[],
        candidate_only_ids=[],
        execution_time_sec=5.001,
        worker_timeout_occurred=True,
    )

    report = generate_audit_markdown_report(result, proposal)
    assert "SAFETY ABORT: WORKER TIMEOUT" in report
    assert "exceeded the safety timeout threshold" in report


# =============================================================================
# Phase 3 Tests: Alias Auditor, Synthetic Suites, and Strict Validation Gating
# =============================================================================

def test_audit_tag_aliases_verdicts(mock_vocab):
    from analysis.llm_regex_audit import audit_tag_aliases, format_alias_audit_markdown

    postings = [
        {"id": "p1", "skills": ["r-project", "custom-tag-1"]},
        {"id": "p2", "skills": ["custom-tag-1", "excel"]},
        {"id": "p3", "skills": ["python"]},
    ]

    # mock_vocab has:
    # R: aliases = ["r-project", "r-lang"]
    # Excel: aliases = ["excel", "ms-excel"]

    proposed_aliases = [
        "r-project",       # Already in vocabulary for R (observed in p1)
        "r-lang",          # Already in vocabulary for R (unobserved in postings)
        "excel",           # Conflicting overlap with Excel
        "custom-tag-1",    # Supported safe (appears in p1, p2; adds coverage)
        "never-seen-tag",  # Unsupported zero count
    ]

    audit = audit_tag_aliases("R", proposed_aliases, postings, mock_vocab)

    assert audit["canonical_skill"] == "R"
    assert audit["total_proposed_aliases"] == 5
    assert audit["registered_in_vocabulary_count"] == 2
    assert audit["supported_adds_coverage_count"] == 1
    assert audit["unsupported_zero_count"] == 2  # r-lang (0 count) and never-seen-tag (0 count)
    assert audit["conflicts_count"] == 1

    alias_map = {item["alias"]: item for item in audit["aliases"]}

    # 1. Registered and observed
    assert alias_map["r-project"]["registered_in_vocabulary"] is True
    assert alias_map["r-project"]["observed_in_native_tags"] is True
    assert alias_map["r-project"]["verdict"] == "ALREADY_REGISTERED_AND_OBSERVED"

    # 2. Registered but NOT observed (presence in vocab does NOT imply data presence)
    assert alias_map["r-lang"]["registered_in_vocabulary"] is True
    assert alias_map["r-lang"]["observed_in_native_tags"] is False
    assert alias_map["r-lang"]["not_observed_in_native_tags"] is True
    assert alias_map["r-lang"]["adds_new_coverage"] is False
    assert alias_map["r-lang"]["verdict"] == "ALREADY_REGISTERED_BUT_UNOBSERVED"

    # 3. Conflicting overlap
    assert alias_map["excel"]["conflicts_with_other_skill"] == "Excel"
    assert alias_map["excel"]["verdict"] == "CONFLICTING_OVERLAP"

    # 4. Safe and adds net new coverage
    assert alias_map["custom-tag-1"]["registered_in_vocabulary"] is False
    assert alias_map["custom-tag-1"]["observed_in_native_tags"] is True
    assert alias_map["custom-tag-1"]["adds_new_coverage"] is True
    assert alias_map["custom-tag-1"]["net_new_postings_count"] == 1  # p2 is net new (p1 already has r-project)
    assert alias_map["custom-tag-1"]["verdict"] == "SUPPORTED_SAFE_ADDS_COVERAGE"

    # 5. Unsupported zero count
    assert alias_map["never-seen-tag"]["registered_in_vocabulary"] is False
    assert alias_map["never-seen-tag"]["observed_in_native_tags"] is False
    assert alias_map["never-seen-tag"]["not_observed_in_native_tags"] is True
    assert alias_map["never-seen-tag"]["adds_new_coverage"] is False
    assert alias_map["never-seen-tag"]["verdict"] == "UNSUPPORTED_ZERO_COUNT"

    md_table = format_alias_audit_markdown(audit)
    assert "Native Tag Alias Audit: R" in md_table
    assert "ADDS COVERAGE" in md_table
    assert "UNOBSERVED (0)" in md_table
    assert "CONFLICT" in md_table
    assert "IN VOCAB (Active)" in md_table
    assert "IN VOCAB (0 in data)" in md_table


def test_alias_audit_conceptual_separation(mock_vocab):
    """
    Explicitly asserts the 5-way separation of alias concepts required by Phase 4:
    1. Registered in vocabulary
    2. Observed in native tags (count > 0)
    3. Not observed in native tags (count == 0)
    4. Adds new coverage (net new postings > 0)
    5. Conflicts with another skill
    """
    from analysis.llm_regex_audit import audit_tag_aliases

    postings = [
        {"id": "p1", "skills": ["r-project"]},
        {"id": "p2", "skills": ["new-r-tool"]},
        {"id": "p3", "skills": ["python"]},
    ]

    # Testing an alias that is registered in vocab but NEVER appears in data
    audit = audit_tag_aliases("R", ["r-lang", "new-r-tool", "python"], postings, mock_vocab)
    alias_dict = {a["alias"]: a for a in audit["aliases"]}

    # Rule: In vocabulary != Observed in data
    assert alias_dict["r-lang"]["registered_in_vocabulary"] is True
    assert alias_dict["r-lang"]["observed_in_native_tags"] is False
    assert alias_dict["r-lang"]["adds_new_coverage"] is False

    # Rule: Unregistered but observed and adds coverage
    assert alias_dict["new-r-tool"]["registered_in_vocabulary"] is False
    assert alias_dict["new-r-tool"]["observed_in_native_tags"] is True
    assert alias_dict["new-r-tool"]["adds_new_coverage"] is True

    # Rule: Cross-skill conflict takes precedence
    assert alias_dict["python"]["conflicts_with_other_skill"] is None  # python not in mock_vocab



def test_evaluate_synthetic_suites():
    import re
    from analysis.llm_regex_audit import evaluate_synthetic_suite

    # Naive \bR\b fails negative distractors like R&D, Model R-200
    r_naive = re.compile(r"\bR\b", re.IGNORECASE)
    all_passed, details = evaluate_synthetic_suite(r_naive, "R")
    assert all_passed is False
    assert any("R&D" in k for k, d in details.items() if not d["passed"])

    # Naive \bexcel\b fails verbal 'excel in' / 'excel at'
    excel_naive = re.compile(r"\bexcel\b", re.IGNORECASE)
    all_passed_ex, details_ex = evaluate_synthetic_suite(excel_naive, "Excel")
    assert all_passed_ex is False
    assert any("excel in" in k for k, d in details_ex.items() if not d["passed"])

    # Guarded Excel regex passes the full synthetic suite
    excel_guarded = re.compile(
        r"\b(?:ms[- ]?)?excel\b(?!\s+(?:in|at|within|as|with)\b)",
        re.IGNORECASE,
    )
    all_passed_guarded, details_guarded = evaluate_synthetic_suite(excel_guarded, "Excel")
    assert all_passed_guarded is True
    assert all(d["passed"] for d in details_guarded.values())


def test_strict_gating_skips_benchmark_on_synthetic_failure(mock_vocab):
    # Candidate that will fail synthetic test suite
    proposal = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\bexcel\b",  # Naive pattern without negative lookaheads fails 'excel in'
        proposed_aliases=[],
        explanation="Naive Excel pattern",
        positive_test_cases=["Excel"],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.7,
        human_review_required=[],
    )

    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="p1",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Excel analytics",
            source_dataset="test",
            human_label=1,
        )
    ]

    postings = [{"id": "p1", "description": "Expert in Excel analytics."}]

    # When run_domain_synthetic=True, synthetic suite failure triggers gating
    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        postings,
        human_validated_samples=human_samples,
        run_domain_synthetic=True,
    )

    assert result.decision_verdict == "REJECTED_FAILED_SYNTHETIC"
    assert result.synthetic_tests_passed is False
    # Gating assertion: benchmark evaluation was skipped
    assert result.ground_truth_metrics is None

    report = generate_audit_markdown_report(result, proposal)
    assert "REJECTED: FAILED SYNTHETIC TEST SUITE" in report
    assert "Blind benchmark holdout evaluation was skipped" in report


def test_strict_gating_skips_benchmark_on_worker_timeout(mock_vocab):
    proposal = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\bexcel\b(?!\s+in\b)",
        proposed_aliases=[],
        explanation="Guarded against in",
        positive_test_cases=["Excel"],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.9,
        human_review_required=[],
    )

    postings = [{"id": f"p_{i}", "description": "Excel modeling"} for i in range(50)]
    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="p1",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Excel modeling",
            source_dataset="test",
            human_label=1,
        )
    ]

    # Worker timeout triggered by sub-millisecond timeout
    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        postings,
        human_validated_samples=human_samples,
        worker_timeout_sec=0.0001,
        run_domain_synthetic=False,
    )

    assert result.worker_timeout_occurred is True
    assert result.decision_verdict == "REJECTED_TIMEOUT"
    assert result.ground_truth_metrics is None

    report = generate_audit_markdown_report(result, proposal)
    assert "REJECTED: WORKER TIMEOUT" in report
    assert "Blind benchmark holdout evaluation was skipped" in report


def test_strict_gating_skips_benchmark_on_unsafe_regex(mock_vocab):
    proposal = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"(?P<unclosed_parenthesis",  # Invalid regex syntax
        proposed_aliases=[],
        explanation="Invalid syntax",
        positive_test_cases=[],
        negative_test_cases=[],
        false_positive_risks=[],
        confidence_score=0.1,
        human_review_required=[],
    )

    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="p1",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Excel modeling",
            source_dataset="test",
            human_label=1,
        )
    ]

    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        [],
        human_validated_samples=human_samples,
    )

    assert result.is_valid_regex is False
    assert result.decision_verdict == "REJECTED_UNSAFE_REGEX"
    assert result.ground_truth_metrics is None

    report = generate_audit_markdown_report(result, proposal)
    assert "REJECTED: UNSAFE REGEX" in report


def test_strict_gating_eligible_verdict_with_f1_score(mock_vocab):
    proposal = CandidateProposal(
        canonical_skill="Excel",
        proposed_regex=r"\b(?:ms[- ]?)?excel\b(?!\s+(?:in|at|within|as|with)\b)",
        proposed_aliases=["excel"],
        explanation="Guarded Excel pattern",
        positive_test_cases=["Advanced Microsoft Excel."],
        negative_test_cases=["Candidates excel at problem solving."],
        false_positive_risks=[],
        confidence_score=0.95,
        human_review_required=[],
    )

    postings = [
        {"id": "p1", "description": "Strong Microsoft Excel skills required."},
        {"id": "p2", "description": "Must excel in team environments."},
    ]

    human_samples = [
        BenchmarkSnippet(
            sample_id="b1",
            posting_id="p1",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            snippet="Advanced Microsoft Excel financial modeling.",
            source_dataset="test",
            human_label=1,
        ),
        BenchmarkSnippet(
            sample_id="b2",
            posting_id="p2",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            snippet="We need individuals who excel at software architecture.",
            source_dataset="test",
            human_label=0,
        ),
        BenchmarkSnippet(
            sample_id="b3",
            posting_id="p3",
            canonical_skill="Excel",
            ground_truth_status=GroundTruthStatus.HUMAN_UNEVALUABLE,
            snippet="Ambiguous text mention.",
            source_dataset="test",
            human_label=None,
        ),
    ]

    result = evaluate_candidate_proposal(
        proposal,
        mock_vocab,
        postings,
        human_validated_samples=human_samples,
        run_domain_synthetic=True,
    )

    assert result.decision_verdict == "ELIGIBLE_FOR_HUMAN_REVIEW"
    assert result.ground_truth_metrics is not None
    gt = result.ground_truth_metrics
    assert gt["true_positives"] == 1.0
    assert gt["false_positives"] == 0.0
    assert gt["precision"] == 1.0
    assert gt["recall"] == 1.0
    assert gt["f1_score"] == 1.0
    assert gt["unevaluable_count"] == 1.0

    report = generate_audit_markdown_report(result, proposal)
    assert "ELIGIBLE FOR HUMAN REVIEW" in report
    assert "Sample F1 Score:** `100.00%`" in report
    assert "Unevaluable Postings (Excluded):** `1`" in report

