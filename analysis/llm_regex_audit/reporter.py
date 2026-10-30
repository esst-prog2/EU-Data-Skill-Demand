"""
analysis/llm_regex_audit/reporter.py

Generates human-readable Markdown and structured audit reports from evaluation results.
Highlights decision verdicts, production regressions, worker timeouts, ReDoS safety warnings,
synthetic test suites, empirical tag alias audits, and holdout benchmark metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .alias_auditor import format_alias_audit_markdown
from .models import CandidateProposal, EvaluationResult, SampleSnippet


def generate_audit_markdown_report(
    result: EvaluationResult,
    proposal: CandidateProposal,
    sample_snippets: Optional[List[SampleSnippet]] = None,
    *,
    alias_audit: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Renders an auditable Markdown report evaluating a candidate regular expression proposal.
    Prominently flags decision verdict, regressions, worker timeouts, and gated validation status.
    """
    skill = result.canonical_skill
    lines: List[str] = []

    # Title & Header
    lines.append(f"# Regex Audit Report: {skill}")
    lines.append(f"**Evaluated on:** Snapshot Corpus ({result.corpus_current_count + len(result.candidate_only_ids)} evaluated postings)")
    lines.append(f"**Execution Time:** {result.execution_time_sec:.3f}s")
    lines.append("")

    # Decision Verdict Badge Banner
    verdict = result.decision_verdict
    badge_map = {
        "ELIGIBLE_FOR_HUMAN_REVIEW": "🟢 **ELIGIBLE FOR HUMAN REVIEW**",
        "REJECTED_TIMEOUT": "⛔ **REJECTED: WORKER TIMEOUT (ReDoS Risk)**",
        "REJECTED_FAILED_SYNTHETIC": "❌ **REJECTED: FAILED SYNTHETIC TEST SUITE**",
        "REJECTED_UNSAFE_REGEX": "⚠️ **REJECTED: UNSAFE REGEX / SYNTAX ERROR**",
        "REJECTED_WORKER_ERROR": "⚠️ **REJECTED: WORKER PROCESS ERROR**",
        "REJECTED_LOW_BENCHMARK_PRECISION": "❌ **REJECTED: LOW BENCHMARK PRECISION (<90%)**",
        "REJECTED_EXCESSIVE_REGRESSION": "⚠️ **REJECTED: EXCESSIVE REGRESSION (>50 drops)**",
        "PENDING": "ℹ️ **DECISION PENDING**",
    }
    badge_text = badge_map.get(verdict, f"ℹ️ **DECISION: {verdict}**")
    lines.append(f"> ### Validation Verdict: {badge_text}")
    lines.append("")

    # Timeout Banner
    if result.worker_timeout_occurred:
        lines.append("> ⛔ **SAFETY ABORT: WORKER TIMEOUT**")
        lines.append("> Candidate regular expression evaluation exceeded the safety timeout threshold on an isolated worker process. Execution was aborted to prevent catastrophic backtracking (ReDoS).")
        lines.append("")

    # Regression Warning Banner
    if result.current_only_ids:
        dropped_count = len(result.current_only_ids)
        lines.append(f"> ⚠️ **PRODUCTION REGRESSION WARNING:** The proposed regex drops `{dropped_count}` posting{'s' if dropped_count > 1 else ''} currently captured by production extraction!")
        preview_ids = ", ".join(f"`{pid}`" for pid in result.current_only_ids[:5])
        if dropped_count > 5:
            preview_ids += f", ... (+{dropped_count - 5} more)"
        lines.append(f"> **Dropped Posting IDs:** {preview_ids}")
        lines.append("> Expert manual review is required before considering adoption to ensure established coverage is not compromised.")
        lines.append("")

    # 1. Proposal Overview
    lines.append("## 1. Candidate Proposal Overview")
    lines.append(f"- **Canonical Skill:** `{skill}`")
    lines.append(f"- **Validation Verdict:** `{verdict}`")
    lines.append(f"- **Confidence Score:** `{proposal.confidence_score:.2f}`")
    lines.append(f"- **Synthetic Tests Passed:** `{'YES' if result.synthetic_tests_passed else 'NO'}`")
    lines.append(f"- **ReDoS Safety Check:** `{'PASSED' if result.safety_check_passed else 'WARNINGS FLAGGED'}`")
    lines.append("")
    lines.append("### Proposed Regular Expression")
    lines.append("```regex")
    lines.append(proposal.proposed_regex)
    lines.append("```")
    lines.append("")
    lines.append("### Current Production Regular Expression")
    lines.append("```regex")
    lines.append(result.current_regex or "[None / Native Tag Only]")
    lines.append("```")
    lines.append("")
    lines.append("### Technical Rationale")
    lines.append(f"> {proposal.explanation}")
    lines.append("")

    # 2. Tag Alias Audit (Separation of Concerns)
    if alias_audit:
        lines.append("## 2. Empirical Tag Alias Audit (FreeHire Native Platform Tags)")
        lines.append(format_alias_audit_markdown(alias_audit))
        lines.append("")
    elif proposal.proposed_aliases:
        lines.append("## 2. Proposed Tag Aliases")
        for alias in proposal.proposed_aliases:
            lines.append(f"- `{alias}`")
        lines.append("")

    # 3. Safety & Anti-Pattern Analysis
    lines.append("## 3. ReDoS & Syntactic Safety Analysis")
    if result.safety_warnings:
        for w in result.safety_warnings:
            lines.append(f"- ⚠️ **Safety Warning:** {w}")
    else:
        lines.append("- ✅ **Passed:** Static anti-pattern heuristic and adversarial repetition tests completed with no excessive backtracking.")
    lines.append("")

    # 4. Synthetic Test Suite Results
    lines.append("## 4. Synthetic Test Suite Results")
    if result.synthetic_suite_results and "detailed_cases" in result.synthetic_suite_results:
        details = result.synthetic_suite_results["detailed_cases"]
        lines.append("### Independent Domain Synthetic Suite (Positives & Confounders)")
        lines.append("| Test Phrase | Expected | Actual | Status | Type | Note |")
        lines.append("| :--- | :---: | :---: | :---: | :--- | :--- |")
        for text, d in details.items():
            st = "✅ PASS" if d["passed"] else "❌ FAIL"
            lines.append(f"| `{text}` | `{d['expected_match']}` | `{d['actual_match']}` | **{st}** | `{d['case_type']}` | {d['explanation']} |")
        lines.append("")

    lines.append("### Proposal-Declared Test Cases")
    lines.append("**Positive Cases (Must Match):**")
    for case, passed in result.positive_test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        lines.append(f"- `{status}`: {case!r}")
    lines.append("")
    lines.append("**Negative Cases (Must Reject):**")
    for case, passed in result.negative_test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        lines.append(f"- `{status}`: {case!r}")
    lines.append("")

    # 5. Corpus Differential Metrics
    lines.append("## 5. Corpus Posting-ID Differential Impact")
    if verdict in ("REJECTED_UNSAFE_REGEX", "REJECTED_FAILED_SYNTHETIC"):
        lines.append("> ℹ️ **GATING ACTIVE:** Corpus evaluation was skipped because this candidate was rejected during earlier validation stages.")
        lines.append("")
    else:
        lines.append("| Metric | Count | Description |")
        lines.append("| :--- | :---: | :--- |")
        lines.append(f"| **Current Hits** | `{result.corpus_current_count:,}` | Postings matched by production regex |")
        lines.append(f"| **Candidate Hits** | `{result.corpus_candidate_count:,}` | Postings matched by candidate regex |")
        lines.append(f"| **Shared Hits** | `{result.shared_ids_count:,}` | Postings agreed upon by both rules |")
        lines.append(f"| **Net Difference** | `{result.net_count_difference:+,}` | Net detection change |")
        lines.append(f"| **Current-Only (Lost)** | `{len(result.current_only_ids):,}` | Postings detected by current but dropped by candidate |")
        lines.append(f"| **Candidate-Only (New)** | `{len(result.candidate_only_ids):,}` | New postings captured exclusively by candidate |")
        lines.append("")

    # 6. Human-Annotated Benchmark Validation (if present)
    lines.append("## 6. Human-Confirmed Benchmark Validation")
    if verdict in ("REJECTED_UNSAFE_REGEX", "REJECTED_FAILED_SYNTHETIC", "REJECTED_TIMEOUT", "REJECTED_WORKER_ERROR"):
        lines.append(f"> ℹ️ **GATING ACTIVE:** Blind benchmark holdout evaluation was skipped because this candidate was rejected during earlier validation (Verdict: `{verdict}`). This preserves holdout integrity and avoids misleading performance metrics.")
        lines.append("")
    elif result.ground_truth_metrics:
        lines.append("*Evaluated strictly on human-verified ground-truth sample annotations.*")
        lines.append("")
        gt = result.ground_truth_metrics
        lines.append(f"- **Total Benchmark Postings:** `{int(gt.get('total_benchmark_samples', gt['evaluable_sample_size']))}`")
        lines.append(f"- **Evaluable Ground-Truth Postings:** `{int(gt['evaluable_sample_size'])}`")
        lines.append(f"- **Unevaluable Postings (Excluded):** `{int(gt.get('unevaluable_count', 0))}`")
        lines.append(f"- **True Positives (TP):** `{int(gt['true_positives'])}`")
        lines.append(f"- **False Positives (FP):** `{int(gt['false_positives'])}`")
        lines.append(f"- **False Negatives (FN):** `{int(gt['false_negatives'])}`")
        lines.append(f"- **True Negatives (TN):** `{int(gt['true_negatives'])}`")

        prec = gt.get("precision")
        if prec is not None:
            lines.append(f"- **Sample Precision:** `{prec * 100:.2f}%`")
        else:
            lines.append("- **Sample Precision:** `N/A (no predicted positive cases in benchmark)`")

        rec = gt.get("recall")
        if rec is not None:
            lines.append(f"- **Sample Recall:** `{rec * 100:.2f}%`")
        else:
            lines.append("- **Sample Recall:** `N/A (no actual positive cases in benchmark)`")

        f1 = gt.get("f1_score")
        if f1 is not None:
            lines.append(f"- **Sample F1 Score:** `{f1 * 100:.2f}%`")
        else:
            lines.append("- **Sample F1 Score:** `N/A`")
        lines.append("")
    else:
        lines.append("*No human-confirmed benchmark sample was attached for this run. Precision and recall are omitted to prevent misleading metrics.*")
        lines.append("")

    # 7. Candidate-Only Snippet Preview for Human Auditing
    if result.candidate_only_sample_snippets:
        lines.append("## 7. Sample Candidate-Only Excerpts (Inspection Required)")
        lines.append("The following excerpts represent new detections captured by the candidate pattern that the current production regex misses:")
        lines.append("")
        for idx, item in enumerate(result.candidate_only_sample_snippets, 1):
            lines.append(f"**{idx}. [{item.get('country') or 'EU'}] {item.get('title') or 'Job'} (ID: `{item.get('posting_id')}`)**")
            lines.append(f"- **Matched Text:** `{item.get('matched_text')}`")
            lines.append(f"- **Context:** `{item.get('snippet')}`")
            lines.append("")

    # 8. Identified Risks & Human Review Items
    lines.append("## 8. Identified Risks & Expert Review Decision")
    if proposal.false_positive_risks:
        lines.append("### Identified False Positive Risks")
        for risk in proposal.false_positive_risks:
            lines.append(f"- ⚠️ {risk}")
        lines.append("")

    if proposal.human_review_required:
        lines.append("### Cases Requiring Human Decision")
        for item in proposal.human_review_required:
            lines.append(f"- 🔍 {item}")
        lines.append("")

    lines.append("---")
    lines.append("*Audit generated by offline llm_regex_audit package. Production vocabulary is unchanged.*")

    return "\n".join(lines)

