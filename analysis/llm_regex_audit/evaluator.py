"""
analysis/llm_regex_audit/evaluator.py

Deterministic Python-side evaluation of candidate regular expressions.
Computes posting-ID-level differentials, synthetic test suite execution,
and holdout benchmark metrics.
Enforces strict validation gating: early rejection on syntax errors, synthetic test failures,
or worker timeouts skips downstream corpus and benchmark evaluation to prevent misleading metrics.
"""

from __future__ import annotations

import multiprocessing
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from src.analytics import SkillVocabulary
from .models import (
    BenchmarkSnippet,
    CandidateProposal,
    EvaluationResult,
    GroundTruthStatus,
    SampleSnippet,
)
from .sampler import extract_bounded_snippet
from .schema import validate_regex_safety
from .synthetic_suites import evaluate_synthetic_suite


def _corpus_eval_worker(
    candidate_regex_str: str,
    current_regex_str: str,
    minimal_postings: List[Tuple[str, str]],
    max_candidate_snippets: int,
    conn: Any,
    precomputed_current_ids: Optional[Set[str]] = None,
) -> None:
    """
    Top-level picklable worker function for multiprocessing evaluation.
    Evaluates candidate regex patterns across minimal posting tuples:
    (ident, desc).
    If precomputed_current_ids is provided, avoids redundant baseline execution.
    Sends ('ok', (current_hit_ids, candidate_hit_ids, candidate_only_matches))
    or ('error', error_str) across pipe connection.
    """
    try:
        cand_compiled = re.compile(candidate_regex_str, re.IGNORECASE)
        curr_compiled = (
            re.compile(current_regex_str, re.IGNORECASE)
            if (current_regex_str and precomputed_current_ids is None)
            else None
        )

        current_hit_ids: Set[str] = set(precomputed_current_ids) if precomputed_current_ids is not None else set()
        candidate_hit_ids: Set[str] = set()
        candidate_only_matches: List[Tuple[str, int, int]] = []

        for ident, desc in minimal_postings:
            if precomputed_current_ids is not None:
                is_current = ident in current_hit_ids
            else:
                is_current = bool(curr_compiled.search(desc)) if curr_compiled else False
                if is_current:
                    current_hit_ids.add(ident)

            cand_match = cand_compiled.search(desc)
            is_cand = bool(cand_match)

            if is_cand:
                candidate_hit_ids.add(ident)

            if is_cand and not is_current and len(candidate_only_matches) < max_candidate_snippets:
                candidate_only_matches.append((ident, cand_match.start(), cand_match.end()))

        conn.send(("ok", (current_hit_ids, candidate_hit_ids, candidate_only_matches)))
    except Exception as exc:
        conn.send(("error", f"Worker evaluation error: {exc}"))
    finally:
        conn.close()


def evaluate_candidate_proposal(
    proposal: CandidateProposal,
    current_vocab: SkillVocabulary,
    postings: Sequence[Dict[str, Any]],
    *,
    human_validated_samples: Optional[Sequence[BenchmarkSnippet | SampleSnippet]] = None,
    max_candidate_snippets_preview: int = 15,
    worker_timeout_sec: float = 25.0,
    run_domain_synthetic: bool = False,
    precomputed_current_hit_ids: Optional[Set[str]] = None,
) -> EvaluationResult:
    """
    Executes an independent deterministic evaluation of a candidate regex with strict gating:
    1. Static & adversarial ReDoS safety validation.
       -> If failed, mark REJECTED_UNSAFE_REGEX and skip synthetic, corpus, and benchmark.
    2. Synthetic test suite execution (proposal's test cases, and domain synthetic suite if run_domain_synthetic=True).
       -> If failed, mark REJECTED_FAILED_SYNTHETIC; corpus evaluation runs to record differential impact,
          but blind benchmark evaluation is strictly SKIPPED.
    3. Posting-ID differential comparison across the provided postings corpus in an isolated
       worker process with hard timeout.
       -> If timed out, mark REJECTED_TIMEOUT and skip benchmark.
       -> If worker error, mark REJECTED_WORKER_ERROR and skip benchmark.
    4. Empirical precision/recall/F1 on human-annotated benchmark holdout samples.
       -> Evaluated ONLY if stages 1, 2, and 3 passed!
       -> If metrics meet quality threshold, mark ELIGIBLE_FOR_HUMAN_REVIEW; else REJECTED_POOR_BENCHMARK_METRICS.
    """
    start_time = time.perf_counter()

    # Retrieve current production regex
    current_regex_str = (
        next(
            (s.get("regex", "") for s in current_vocab.skills if s["canonical"] == proposal.canonical_skill),
            "",
        )
    )

    # ---------------------------------------------------------
    # STAGE 1: Syntax & Static ReDoS Safety Check
    # ---------------------------------------------------------
    safety_passed, safety_warnings = validate_regex_safety(proposal.proposed_regex)
    is_valid = safety_passed or not any("syntax" in w.lower() for w in safety_warnings)

    if not is_valid or not safety_passed:
        return EvaluationResult(
            canonical_skill=proposal.canonical_skill,
            candidate_regex=proposal.proposed_regex,
            current_regex=current_regex_str,
            is_valid_regex=is_valid,
            safety_check_passed=False,
            safety_warnings=safety_warnings,
            positive_test_results={},
            negative_test_results={},
            corpus_current_count=0,
            corpus_candidate_count=0,
            shared_ids_count=0,
            current_only_ids=[],
            candidate_only_ids=[],
            execution_time_sec=round(time.perf_counter() - start_time, 3),
            decision_verdict="REJECTED_UNSAFE_REGEX",
            synthetic_suite_results=None,
        )

    cand_compiled = re.compile(proposal.proposed_regex, re.IGNORECASE)

    # ---------------------------------------------------------
    # STAGE 2: Synthetic Test Suites
    # ---------------------------------------------------------
    # 2a. Proposal's own declared test cases
    pos_results: Dict[str, bool] = {}
    for case in proposal.positive_test_cases:
        pos_results[case] = bool(cand_compiled.search(case))

    neg_results: Dict[str, bool] = {}
    for case in proposal.negative_test_cases:
        neg_results[case] = not bool(cand_compiled.search(case))

    proposal_synthetic_passed = (
        all(pos_results.values()) if pos_results else True
    ) and (
        all(neg_results.values()) if neg_results else True
    )

    # 2b. Domain synthetic test suite (if enabled)
    synthetic_suite_data: Optional[Dict[str, Any]] = None
    domain_suite_passed = True
    if run_domain_synthetic:
        domain_suite_passed, domain_suite_details = evaluate_synthetic_suite(
            cand_compiled, proposal.canonical_skill
        )
        synthetic_suite_data = {
            "all_passed": domain_suite_passed and proposal_synthetic_passed,
            "domain_suite_passed": domain_suite_passed,
            "proposal_tests_passed": proposal_synthetic_passed,
            "detailed_cases": domain_suite_details,
        }
    else:
        synthetic_suite_data = {
            "all_passed": proposal_synthetic_passed,
            "domain_suite_passed": True,
            "proposal_tests_passed": proposal_synthetic_passed,
            "detailed_cases": {},
        }

    all_synthetic_passed = proposal_synthetic_passed and domain_suite_passed

    if not all_synthetic_passed:
        decision_verdict = "REJECTED_FAILED_SYNTHETIC"
    else:
        decision_verdict = "PENDING"

    # ---------------------------------------------------------
    # STAGE 3: Corpus Posting-ID Differential Evaluation
    # ---------------------------------------------------------
    minimal_postings: List[Tuple[str, str]] = []
    posting_meta_map: Dict[str, Dict[str, Any]] = {}

    for p in postings:
        desc = p.get("description") or ""
        if isinstance(desc, str) and desc.strip():
            ident = str(p.get("id") or p.get("public_slug") or p.get("slug") or "")
            minimal_postings.append((ident, desc))
            posting_meta_map[ident] = {
                "title": str(p.get("title") or ""),
                "category": str(p.get("_collection_category") or ""),
                "country": str(p.get("_collection_country") or ""),
                "description": desc,
            }

    current_hit_ids: Set[str] = set()
    candidate_hit_ids: Set[str] = set()
    candidate_only_snippets: List[Dict[str, Any]] = []
    worker_timeout_occurred = False
    worker_error: Optional[str] = None

    if minimal_postings:
        # Precompute baseline production hits once in the parent process if not provided,
        # preventing the worker process from wasting its ReDoS timeout budget re-evaluating baseline rules.
        if precomputed_current_hit_ids is None and current_regex_str:
            curr_compiled = re.compile(current_regex_str, re.IGNORECASE)
            precomputed_current_hit_ids = {
                ident for ident, desc in minimal_postings if curr_compiled.search(desc)
            }
        elif precomputed_current_hit_ids is None:
            precomputed_current_hit_ids = set()

        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
        proc = multiprocessing.Process(
            target=_corpus_eval_worker,
            args=(
                proposal.proposed_regex,
                current_regex_str,
                minimal_postings,
                max_candidate_snippets_preview,
                child_conn,
                precomputed_current_hit_ids,
            ),
        )
        try:
            proc.start()
            child_conn.close()  # Close child end in parent for clean EOF semantics

            # Use non-blocking poll with timeout to prevent OS pipe buffer deadlock
            if parent_conn.poll(timeout=worker_timeout_sec):
                status, payload = parent_conn.recv()
                proc.join()
                if status == "ok":
                    current_hit_ids, candidate_hit_ids, candidate_only_matches = payload
                    for s_id, start_idx, end_idx in candidate_only_matches:
                        meta = posting_meta_map.get(s_id, {})
                        s_desc = meta.get("description", "")
                        snip, _ = extract_bounded_snippet(s_desc, start_idx, end_idx, window=120)
                        candidate_only_snippets.append({
                            "posting_id": s_id,
                            "title": meta.get("title", ""),
                            "category": meta.get("category", ""),
                            "country": meta.get("country", ""),
                            "snippet": snip,
                            "matched_text": s_desc[start_idx:end_idx],
                        })
                else:
                    worker_error = str(payload)
                    safety_warnings.append(worker_error)
            else:
                # Hard timeout triggered
                proc.terminate()
                proc.join()
                worker_timeout_occurred = True
                safety_warnings.append(
                    f"Corpus evaluation timed out after {worker_timeout_sec}s. "
                    "Process terminated to prevent catastrophic backtracking."
                )
        finally:
            if proc.is_alive():
                proc.terminate()
                proc.join()
            parent_conn.close()

    current_only = sorted(list(current_hit_ids - candidate_hit_ids))
    candidate_only = sorted(list(candidate_hit_ids - current_hit_ids))
    shared_ids = current_hit_ids & candidate_hit_ids

    # Update verdict if worker timed out or errored
    if worker_timeout_occurred:
        decision_verdict = "REJECTED_TIMEOUT"
    elif worker_error:
        decision_verdict = "REJECTED_WORKER_ERROR"

    # ---------------------------------------------------------
    # STAGE 4: Blind Holdout Benchmark Evaluation (Strictly Gated)
    # ---------------------------------------------------------
    ground_truth_metrics: Optional[Dict[str, Optional[float]]] = None

    # Strict Gating: only run benchmark evaluation if candidate passed synthetic tests and corpus completed without error/timeout
    benchmark_eligible = (
        all_synthetic_passed
        and not worker_timeout_occurred
        and not worker_error
    )

    if benchmark_eligible and human_validated_samples:
        tp = 0
        fp = 0
        fn = 0
        tn = 0
        evaluable_count = 0
        unevaluable_count = 0

        for s in human_validated_samples:
            if s.ground_truth_status not in (
                GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
                GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            ):
                unevaluable_count += 1
                continue

            evaluable_count += 1
            human_pos = (s.ground_truth_status == GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE)
            eval_text = s.metadata.get("full_description") or s.snippet
            cand_pos = bool(cand_compiled.search(eval_text))

            if human_pos and cand_pos:
                tp += 1
            elif not human_pos and cand_pos:
                fp += 1
            elif human_pos and not cand_pos:
                fn += 1
            else:
                tn += 1

        if evaluable_count > 0:
            precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
            recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
            f1 = (
                (2 * precision * recall / (precision + recall))
                if (precision is not None and recall is not None and (precision + recall) > 0)
                else None
            )

            ground_truth_metrics = {
                "total_benchmark_samples": float(len(human_validated_samples)),
                "evaluable_sample_size": float(evaluable_count),
                "unevaluable_count": float(unevaluable_count),
                "true_positives": float(tp),
                "false_positives": float(fp),
                "false_negatives": float(fn),
                "true_negatives": float(tn),
                "precision": round(precision, 4) if precision is not None else None,
                "recall": round(recall, 4) if recall is not None else None,
                "f1_score": round(f1, 4) if f1 is not None else None,
            }

            # Quality verdict gating based on benchmark performance
            if precision is not None and precision < 0.90:
                decision_verdict = "REJECTED_LOW_BENCHMARK_PRECISION"
            elif len(current_only) > 50:
                decision_verdict = "REJECTED_EXCESSIVE_REGRESSION"
            else:
                decision_verdict = "ELIGIBLE_FOR_HUMAN_REVIEW"
        else:
            decision_verdict = "ELIGIBLE_FOR_HUMAN_REVIEW"

    execution_time = time.perf_counter() - start_time

    return EvaluationResult(
        canonical_skill=proposal.canonical_skill,
        candidate_regex=proposal.proposed_regex,
        current_regex=current_regex_str,
        is_valid_regex=is_valid,
        safety_check_passed=safety_passed and not worker_timeout_occurred,
        safety_warnings=safety_warnings,
        positive_test_results=pos_results,
        negative_test_results=neg_results,
        corpus_current_count=len(current_hit_ids),
        corpus_candidate_count=len(candidate_hit_ids),
        shared_ids_count=len(shared_ids),
        current_only_ids=current_only,
        candidate_only_ids=candidate_only,
        execution_time_sec=round(execution_time, 3),
        ground_truth_metrics=ground_truth_metrics,
        candidate_only_sample_snippets=candidate_only_snippets,
        worker_timeout_occurred=worker_timeout_occurred,
        worker_error=worker_error,
        decision_verdict=decision_verdict,
        synthetic_suite_results=synthetic_suite_data,
    )

