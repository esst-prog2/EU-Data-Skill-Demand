"""
analysis/llm_regex_audit/models.py

Domain models, enums, label normalization, and distinct prompt vs. holdout snippet types.
Strictly separates discovery/prompt data from blind evaluation benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class GroundTruthStatus(str, Enum):
    """
    Explicit status of a snippet's ground-truth label.
    Prevents unverified examples from being conflated with human-verified truth.
    """
    HUMAN_CONFIRMED_POSITIVE = "human_confirmed_positive"
    HUMAN_CONFIRMED_NEGATIVE = "human_confirmed_negative"
    HUMAN_UNEVALUABLE = "human_unevaluable"
    PRODUCTION_POSITIVE_UNVERIFIED = "production_positive_unverified"
    UNVERIFIED_NEAR_MISS = "unverified_near_miss"
    DIFFICULT_NEGATIVE_SYNTHETIC = "difficult_negative_synthetic"


def normalize_human_label(val: Any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Normalizes human validation labels with strict type safety:
    - Rejects boolean types explicitly (True/False are not valid annotation codes).
    - Accepts integer 1 or string "1" (with whitespace) -> (True, 1, "1")
    - Accepts integer 0 or string "0" (with whitespace) -> (True, 0, "0")
    - Accepts "u" / "U" (with whitespace) -> (True, None, "u")
    - Any other value -> (False, None, error_message)
    """
    # Reject booleans (in Python, isinstance(True, int) is True)
    if isinstance(val, bool) or val is None:
        return False, None, f"Unsupported label value: {val!r} (booleans and None are invalid)"

    if isinstance(val, int):
        if val == 1:
            return True, 1, "1"
        if val == 0:
            return True, 0, "0"
        return False, None, f"Invalid integer annotation value: {val} (expected 0 or 1)"

    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned == "1":
            return True, 1, "1"
        if cleaned == "0":
            return True, 0, "0"
        if cleaned == "u":
            return True, None, "u"
        return False, None, f"Invalid string annotation value: {val!r} (expected '1', '0', or 'u')"

    return False, None, f"Unsupported label type: {type(val).__name__}"


@dataclass(frozen=True)
class DiscoverySnippet:
    """
    A context snippet intended for LLM prompt context (discovery & rule improvement).
    Architectural invariant: MUST NOT carry human-confirmed benchmark ground truth.
    """
    sample_id: str
    posting_id: str
    canonical_skill: str
    stratum: str
    ground_truth_status: GroundTruthStatus
    snippet: str
    source_dataset: str
    category: Optional[str] = None
    country: Optional[str] = None
    match_span: Optional[Tuple[int, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.ground_truth_status in (
            GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            GroundTruthStatus.HUMAN_UNEVALUABLE,
        ):
            raise ValueError(
                f"Leakage Error: DiscoverySnippet (sample_id={self.sample_id!r}) cannot carry "
                f"human-confirmed benchmark status ({self.ground_truth_status.value}). "
                "Human benchmark holdouts must remain strictly blind."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "posting_id": self.posting_id,
            "canonical_skill": self.canonical_skill,
            "stratum": self.stratum,
            "ground_truth_status": self.ground_truth_status.value,
            "snippet": self.snippet,
            "source_dataset": self.source_dataset,
            "category": self.category,
            "country": self.country,
            "match_span": list(self.match_span) if self.match_span else None,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BenchmarkSnippet:
    """
    A human-annotated benchmark sample reserved for independent, blind candidate evaluation.
    Carries verified provenance and evidence notes. MUST NEVER enter LLM prompts.
    """
    sample_id: str
    posting_id: str
    canonical_skill: str
    ground_truth_status: GroundTruthStatus
    snippet: str
    source_dataset: str
    human_label: Optional[int] = None  # 1, 0, or None for 'u'
    evidence_notes: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    stratum: str = "human_annotated_benchmark"
    match_span: Optional[Tuple[int, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "posting_id": self.posting_id,
            "canonical_skill": self.canonical_skill,
            "stratum": self.stratum,
            "ground_truth_status": self.ground_truth_status.value,
            "snippet": self.snippet,
            "source_dataset": self.source_dataset,
            "human_label": self.human_label,
            "evidence_notes": self.evidence_notes,
            "category": self.category,
            "country": self.country,
            "match_span": list(self.match_span) if self.match_span else None,
            "metadata": self.metadata,
        }


# Backwards compatibility alias
SampleSnippet = DiscoverySnippet


@dataclass
class CandidateProposal:
    """
    Structured proposal generated by an LLM or expert rule engineer.
    Strictly separates regex rules, aliases, rationale, and validation cases.
    """
    canonical_skill: str
    proposed_regex: str
    proposed_aliases: List[str]
    explanation: str
    positive_test_cases: List[str]
    negative_test_cases: List[str]
    false_positive_risks: List[str]
    confidence_score: float
    human_review_required: List[str]
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_skill": self.canonical_skill,
            "proposed_regex": self.proposed_regex,
            "proposed_aliases": list(self.proposed_aliases),
            "explanation": self.explanation,
            "positive_test_cases": list(self.positive_test_cases),
            "negative_test_cases": list(self.negative_test_cases),
            "false_positive_risks": list(self.false_positive_risks),
            "confidence_score": float(self.confidence_score),
            "human_review_required": list(self.human_review_required),
        }


@dataclass
class EvaluationResult:
    """
    Results of deterministic Python-side evaluation of a candidate regex against
    test cases, human benchmarks, and the broader corpus.
    """
    canonical_skill: str
    candidate_regex: str
    current_regex: str
    is_valid_regex: bool
    safety_check_passed: bool
    safety_warnings: List[str]
    positive_test_results: Dict[str, bool]
    negative_test_results: Dict[str, bool]
    corpus_current_count: int
    corpus_candidate_count: int
    shared_ids_count: int
    current_only_ids: List[str]
    candidate_only_ids: List[str]
    execution_time_sec: float
    ground_truth_metrics: Optional[Dict[str, Optional[float]]] = None
    candidate_only_sample_snippets: List[Dict[str, Any]] = field(default_factory=list)
    worker_timeout_occurred: bool = False
    worker_error: Optional[str] = None
    decision_verdict: str = "PENDING"
    synthetic_suite_results: Optional[Dict[str, Any]] = None

    @property
    def net_count_difference(self) -> int:
        return self.corpus_candidate_count - self.corpus_current_count

    @property
    def synthetic_tests_passed(self) -> bool:
        pos_ok = all(self.positive_test_results.values()) if self.positive_test_results else True
        neg_ok = all(self.negative_test_results.values()) if self.negative_test_results else True
        suite_ok = (
            self.synthetic_suite_results.get("all_passed", True)
            if self.synthetic_suite_results
            else True
        )
        return pos_ok and neg_ok and suite_ok
