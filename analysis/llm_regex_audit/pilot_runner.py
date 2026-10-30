"""
analysis/llm_regex_audit/pilot_runner.py

End-to-end orchestration for the local LLM regular expression discovery pilot.
Strictly local inference via Ollama (zero network cost, zero external API transmission).
Enforces complete separation between discovery samples and blind benchmark holdouts.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics import SkillVocabulary
from .alias_auditor import audit_tag_aliases
from .client import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_HOST,
    OllamaClientResult,
    get_model_details,
    is_ollama_running,
    request_candidate_proposals,
)
from .evaluator import evaluate_candidate_proposal
from .models import BenchmarkSnippet, CandidateProposal, DiscoverySnippet, EvaluationResult
from .prompt_builder import build_audit_prompt
from .reporter import generate_audit_markdown_report
from .sampler import load_benchmark_snippets, sample_discovery_snippets


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CORPUS_PATH = PROJECT_ROOT / "data" / "raw" / "freehire_eu_raw.json"
SKILLS_VOCAB_PATH = PROJECT_ROOT / "data" / "fixtures" / "skills_vocabulary.json"
R_VALIDATION_PATH = PROJECT_ROOT / "analysis" / "r_validation.xlsx"
SPIKE_VALIDATION_PATH = PROJECT_ROOT / "analysis" / "spike_validation.xlsx"
ARTIFACTS_DIR = PROJECT_ROOT / "analysis" / "llm_regex_audit" / "artifacts"


def load_benchmark_datasets() -> Tuple[Set[str], List[BenchmarkSnippet], List[BenchmarkSnippet]]:
    """
    Loads human-annotated benchmark records from r_validation.xlsx and spike_validation.xlsx.
    Returns:
    (all_benchmark_posting_ids, r_benchmark_snippets, excel_benchmark_snippets)
    """
    benchmark_ids: Set[str] = set()
    r_records: List[Dict[str, Any]] = []
    excel_records: List[Dict[str, Any]] = []

    # 1. Load r_validation.xlsx
    if R_VALIDATION_PATH.exists():
        wb_r = openpyxl.load_workbook(str(R_VALIDATION_PATH), read_only=True)
        ws_r = wb_r["Annotation"]
        rows_r = list(ws_r.iter_rows(values_only=True))
        if rows_r:
            headers = [str(h) for h in rows_r[0]]
            for r in rows_r[1:]:
                if not any(r):
                    continue
                row_dict = dict(zip(headers, r))
                slug = str(row_dict.get("public_slug") or row_dict.get("sample_id") or "")
                if slug:
                    benchmark_ids.add(slug)
                r_records.append({
                    "id": slug,
                    "description": row_dict.get("description") or "",
                    "human_label": row_dict.get("human_r_label"),
                    "evidence_notes": row_dict.get("evidence_notes"),
                    "category": row_dict.get("category"),
                    "country": row_dict.get("country"),
                    "source_dataset": "r_validation.xlsx",
                })

    # 2. Load spike_validation.xlsx
    if SPIKE_VALIDATION_PATH.exists():
        wb_s = openpyxl.load_workbook(str(SPIKE_VALIDATION_PATH), read_only=True)
        ws_s = wb_s["Annotation"]
        rows_s = list(ws_s.iter_rows(values_only=True))
        if rows_s:
            headers = [str(h) for h in rows_s[0]]
            for r in rows_s[1:]:
                if not any(r):
                    continue
                row_dict = dict(zip(headers, r))
                slug = str(row_dict.get("public_slug") or row_dict.get("sample_id") or "")
                if slug:
                    benchmark_ids.add(slug)

                # R label in spike workbook
                if "R" in row_dict and row_dict["R"] is not None:
                    r_records.append({
                        "id": slug,
                        "description": row_dict.get("description") or "",
                        "human_label": row_dict.get("R"),
                        "evidence_notes": f"Spike workbook ground truth for R (sample {row_dict.get('sample_id')})",
                        "category": row_dict.get("category"),
                        "country": row_dict.get("country"),
                        "source_dataset": "spike_validation.xlsx",
                    })

                # Excel label in spike workbook
                if "Excel" in row_dict and row_dict["Excel"] is not None:
                    excel_records.append({
                        "id": slug,
                        "description": row_dict.get("description") or "",
                        "human_label": row_dict.get("Excel"),
                        "evidence_notes": f"Spike workbook ground truth for Excel (sample {row_dict.get('sample_id')})",
                        "category": row_dict.get("category"),
                        "country": row_dict.get("country"),
                        "source_dataset": "spike_validation.xlsx",
                    })

    r_benchmarks = load_benchmark_snippets(r_records, "R")
    excel_benchmarks = load_benchmark_snippets(excel_records, "Excel")

    return benchmark_ids, r_benchmarks, excel_benchmarks


def verify_discovery_sample(
    snippets: List[DiscoverySnippet],
    benchmark_ids: Set[str],
) -> Dict[str, Any]:
    """
    Computes and verifies strict diagnostic metrics for discovery samples:
    - Discovery sample count
    - Unique posting ID count
    - Excluded benchmark ID count
    - Duplicate ID count
    - Snippet length distribution (min, mean, max)
    - Stratum distribution
    - Confirms zero benchmark ID leakage
    """
    total_count = len(snippets)
    unique_ids = set(s.posting_id for s in snippets)
    duplicate_count = total_count - len(unique_ids)

    lengths = [len(s.snippet) for s in snippets]
    min_len = min(lengths) if lengths else 0
    max_len = max(lengths) if lengths else 0
    mean_len = (sum(lengths) / len(lengths)) if lengths else 0.0

    strata_counts: Dict[str, int] = {}
    for s in snippets:
        strata_counts[s.stratum] = strata_counts.get(s.stratum, 0) + 1

    leakage_ids = unique_ids.intersection(benchmark_ids)
    if leakage_ids:
        raise ValueError(
            f"CRITICAL BENCHMARK LEAKAGE DETECTED! {len(leakage_ids)} benchmark posting IDs "
            f"were found in discovery snippets: {list(leakage_ids)[:5]}"
        )

    return {
        "total_sample_count": total_count,
        "unique_posting_id_count": len(unique_ids),
        "duplicate_id_count": duplicate_count,
        "excluded_benchmark_ids_count": len(benchmark_ids),
        "snippet_length_min": min_len,
        "snippet_length_max": max_len,
        "snippet_length_mean": round(mean_len, 1),
        "stratum_distribution": strata_counts,
        "benchmark_leakage_verified_zero": True,
    }


SKILL_DOMAIN_GUIDANCE: Dict[str, List[str]] = {
    "R": [
        "Focus on R-specific language variants (e.g. R programming, R script, RStudio, R/Shiny, tidyverse).",
        "Confounding distractors: guard against R&D, A/R, Model R, R as an initial, R currency (R$), and medical licenses (R.N.).",
    ],
    "Excel": [
        "Focus on explicit software mentions (e.g. Microsoft Excel, MS Excel, Excel VBA, advanced Excel modeling).",
        "Confounding distractors: strictly guard against ordinary English verbs such as 'excel in', 'excel at', 'excel within'.",
    ],
}

PHASE3_SKILL_GUIDANCE: Dict[str, List[str]] = {
    "R": [
        "Focus on isolating the standalone programming language 'R' in technical skill lists (e.g. 'Python, R, SQL'), 'R programming', 'RStudio', 'R/Shiny', 'tidyverse'.",
        "Confounding distractors: strictly reject Research & Development (R&D, R & D), Accounts Receivable (A/R), hardware models (Model R-200), batch codes (R/1204), software builds (R.10), currency symbols (R$ 8,000), professional licenses (R.N.), person initials (Dr. R. Watson), and words containing 'r'.",
        "Boundary & ReDoS Safety: DO NOT use nested word boundaries or redundant alternations such as `\\b(?:\\b|\\s|\\.)?\\b` (causes worker timeout). DO NOT use start/end anchors (^, $). Keep the pattern concise and under 120 characters.",
    ],
    "Excel": [
        "Focus on explicit spreadsheet software mentions: Microsoft Excel, MS Excel, Excel VBA, advanced Excel modeling, and standalone Excel in analytical tool lists.",
        "Confounding distractors: strictly reject ordinary English verbs like 'excel in', 'excel at', 'excel within', 'excel as', 'excel with' using a negative lookahead, e.g. `(?!\\s+(?:in|at|within|as|with)\\b)`.",
        "Boundary & ReDoS Safety: DO NOT use start/end anchors (^, $) because the regex searches within large job descriptions. DO NOT use nested boundaries. Keep the pattern concise and under 120 characters.",
    ],
}


def run_phase3_skill_pilot(
    canonical_skill: str,
    vocab: SkillVocabulary,
    postings: List[Dict[str, Any]],
    discovery_snippets: List[DiscoverySnippet],
    benchmark_snippets: List[BenchmarkSnippet],
    *,
    model_name: str = DEFAULT_MODEL,
    host: str = DEFAULT_OLLAMA_HOST,
    seed: int = 20261030,
) -> Dict[str, Any]:
    """
    Executes a Phase 3 candidate discovery, alias audit, and gated validation run for a single skill.
    Preserves all Phase 2 artifacts by writing distinct Phase 3 artifacts.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    sanitized_model = model_name.replace(":", "_").replace("/", "_")

    # 1. Build prompt package with Phase 3 guidance & anti-pattern constraints
    guidance = PHASE3_SKILL_GUIDANCE.get(canonical_skill)
    prompt_pkg = build_audit_prompt(
        canonical_skill, vocab, discovery_snippets, skill_specific_guidance=guidance
    )

    # 2. Call local Ollama model
    print(f"[Phase 3: {canonical_skill}] Calling local Ollama ({model_name}) with {len(discovery_snippets)} discovery snippets...")
    client_result: OllamaClientResult = request_candidate_proposals(
        prompt_pkg,
        model_name=model_name,
        host=host,
        seed=seed,
    )

    details = get_model_details(model_name, host=host)
    quantization = details.get("details", {}).get("quantization_level", "Q4_K_M")

    result_data: Dict[str, Any] = {
        "canonical_skill": canonical_skill,
        "phase": 3,
        "model_name": model_name,
        "quantization": quantization,
        "sampling_seed": seed,
        "prompt_version": "v3.0-constrained-gated",
        "inference_duration_sec": client_result.inference_duration_sec,
        "prompt_tokens": client_result.prompt_tokens,
        "response_tokens": client_result.response_tokens,
        "client_success": client_result.success,
        "client_error": client_result.error,
        "raw_model_response": client_result.raw_response,
        "parsed_json": client_result.parsed_json,
        "proposals_count": len(client_result.proposals),
        "validation_errors": client_result.validation_errors,
        "evaluated_candidates": [],
    }

    if not client_result.success or not client_result.proposals:
        print(f"[Phase 3: {canonical_skill}] Inference or proposal validation failed: {client_result.error}")
        out_json_path = ARTIFACTS_DIR / f"{canonical_skill.lower()}_phase3_result_{sanitized_model}.json"
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        return result_data

    # 3. Evaluate each candidate proposal with alias audit and strict gating
    for idx, proposal in enumerate(client_result.proposals, 1):
        print(f"[Phase 3: {canonical_skill}] Auditing candidate #{idx}: regex {proposal.proposed_regex!r} | aliases {proposal.proposed_aliases}...")

        # 3a. Empirical Tag Alias Audit against native platform tags
        alias_audit = audit_tag_aliases(
            canonical_skill,
            proposal.proposed_aliases,
            postings,
            vocab,
        )

        # 3b. Gated Evaluation (syntax -> synthetic -> corpus with 10s timeout -> benchmark holdouts)
        eval_result: EvaluationResult = evaluate_candidate_proposal(
            proposal,
            vocab,
            postings,
            human_validated_samples=benchmark_snippets,
            worker_timeout_sec=10.0,
            run_domain_synthetic=True,
        )

        # 3c. Generate Phase 3 Markdown Report
        md_report = generate_audit_markdown_report(eval_result, proposal, alias_audit=alias_audit)

        # Save Phase 3 Markdown report (distinct filename, preserving Phase 2 files)
        md_filename = f"{canonical_skill.lower()}_phase3_report_{sanitized_model}_cand{idx}.md"
        md_path = ARTIFACTS_DIR / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        print(f"  -> Verdict: {eval_result.decision_verdict} | Execution: {eval_result.execution_time_sec:.2f}s | Report: {md_filename}")

        cand_data = {
            "candidate_index": idx,
            "decision_verdict": eval_result.decision_verdict,
            "proposal": proposal.to_dict(),
            "alias_audit": alias_audit,
            "evaluation": {
                "decision_verdict": eval_result.decision_verdict,
                "is_valid_regex": eval_result.is_valid_regex,
                "safety_check_passed": eval_result.safety_check_passed,
                "safety_warnings": eval_result.safety_warnings,
                "worker_timeout_occurred": eval_result.worker_timeout_occurred,
                "synthetic_tests_passed": eval_result.synthetic_tests_passed,
                "synthetic_suite_results": eval_result.synthetic_suite_results,
                "corpus_current_count": eval_result.corpus_current_count,
                "corpus_candidate_count": eval_result.corpus_candidate_count,
                "net_count_difference": eval_result.net_count_difference,
                "shared_ids_count": eval_result.shared_ids_count,
                "current_only_count": len(eval_result.current_only_ids),
                "candidate_only_count": len(eval_result.candidate_only_ids),
                "current_only_preview": eval_result.current_only_ids[:10],
                "candidate_only_preview": eval_result.candidate_only_ids[:10],
                "ground_truth_metrics": eval_result.ground_truth_metrics,
                "execution_time_sec": eval_result.execution_time_sec,
            },
            "markdown_report_path": str(md_path.relative_to(PROJECT_ROOT)),
        }
        result_data["evaluated_candidates"].append(cand_data)

    # Save Phase 3 JSON summary (distinct filename, preserving Phase 2 files)
    out_json_path = ARTIFACTS_DIR / f"{canonical_skill.lower()}_phase3_result_{sanitized_model}.json"
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    return result_data


def run_phase3_pilot(
    model_name: str = DEFAULT_MODEL,
    host: str = DEFAULT_OLLAMA_HOST,
    seed: int = 20261030,
) -> Dict[str, Any]:
    """
    Executes the Phase 3 candidate discovery, alias audit, and gated validation workflow for R and Excel.
    """
    print(f"=== Starting Phase 3 Controlled Validation Pilot (Model: {model_name}) ===")

    # 1. Load vocabulary and raw corpus
    print("Loading skills vocabulary and corpus...")
    vocab = SkillVocabulary.load_from_file(SKILLS_VOCAB_PATH)
    with open(RAW_CORPUS_PATH, "r", encoding="utf-8") as f:
        postings = json.load(f)
    print(f"Loaded {len(postings)} corpus postings and {len(vocab.skills)} canonical skills.")

    # 2. Load benchmark datasets (strict holdout)
    print("Loading human benchmark workbooks...")
    bench_ids, r_bench, excel_bench = load_benchmark_datasets()
    print(f"Loaded {len(bench_ids)} unique benchmark posting IDs (Holdout size: R={len(r_bench)}, Excel={len(excel_bench)}).")

    # 3. Sample discovery snippets (excluding benchmark IDs)
    print("Sampling discovery context snippets...")
    r_discovery = sample_discovery_snippets(
        postings, "R", vocab,
        seed=seed, current_hits_n=20, near_miss_n=20, negative_controls_n=10,
        excluded_posting_ids=bench_ids,
    )
    r_diag = verify_discovery_sample(r_discovery, bench_ids)

    excel_discovery = sample_discovery_snippets(
        postings, "Excel", vocab,
        seed=seed, current_hits_n=20, near_miss_n=20, negative_controls_n=10,
        excluded_posting_ids=bench_ids,
    )
    excel_diag = verify_discovery_sample(excel_discovery, bench_ids)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / "phase3_discovery_samples_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"R": r_diag, "Excel": excel_diag}, f, indent=2)
    print(f"Phase 3 discovery samples verified and diagnostics saved to {summary_path.name}.")

    # 4. Run R experiment
    print("\n--- Running Phase 3 Experiment 1: R ---")
    r_result = run_phase3_skill_pilot(
        "R", vocab, postings, r_discovery, r_bench,
        model_name=model_name, host=host, seed=seed,
    )

    # 5. Run Excel experiment
    print("\n--- Running Phase 3 Experiment 2: Microsoft Excel ---")
    excel_result = run_phase3_skill_pilot(
        "Excel", vocab, postings, excel_discovery, excel_bench,
        model_name=model_name, host=host, seed=seed,
    )

    return {
        "phase": 3,
        "model_name": model_name,
        "seed": seed,
        "discovery_diagnostics": {"R": r_diag, "Excel": excel_diag},
        "r_result": r_result,
        "excel_result": excel_result,
    }


def run_skill_pilot(
    canonical_skill: str,
    vocab: SkillVocabulary,
    postings: List[Dict[str, Any]],
    discovery_snippets: List[DiscoverySnippet],
    benchmark_snippets: List[BenchmarkSnippet],
    *,
    model_name: str = DEFAULT_MODEL,
    host: str = DEFAULT_OLLAMA_HOST,
    seed: int = 20261030,
) -> Dict[str, Any]:
    """
    Executes an end-to-end discovery and evaluation run for a single skill.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    sanitized_model = model_name.replace(":", "_").replace("/", "_")

    # 1. Build prompt package
    guidance = SKILL_DOMAIN_GUIDANCE.get(canonical_skill)
    prompt_pkg = build_audit_prompt(canonical_skill, vocab, discovery_snippets, skill_specific_guidance=guidance)

    # 2. Call local Ollama model
    print(f"[{canonical_skill}] Calling local Ollama ({model_name}) with {len(discovery_snippets)} discovery snippets...")
    client_result: OllamaClientResult = request_candidate_proposals(
        prompt_pkg,
        model_name=model_name,
        host=host,
        seed=seed,
    )

    # Fetch model details
    details = get_model_details(model_name, host=host)
    quantization = details.get("details", {}).get("quantization_level", "Q4_K_M")

    result_data: Dict[str, Any] = {
        "canonical_skill": canonical_skill,
        "model_name": model_name,
        "quantization": quantization,
        "sampling_seed": seed,
        "prompt_version": "v1.0-structured-schema",
        "inference_duration_sec": client_result.inference_duration_sec,
        "prompt_tokens": client_result.prompt_tokens,
        "response_tokens": client_result.response_tokens,
        "client_success": client_result.success,
        "client_error": client_result.error,
        "raw_model_response": client_result.raw_response,
        "parsed_json": client_result.parsed_json,
        "proposals_count": len(client_result.proposals),
        "validation_errors": client_result.validation_errors,
        "evaluated_candidates": [],
    }

    if not client_result.success or not client_result.proposals:
        print(f"[{canonical_skill}] Model inference or proposal validation failed: {client_result.error}")
        out_json_path = ARTIFACTS_DIR / f"{canonical_skill.lower()}_pilot_result_{sanitized_model}.json"
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        return result_data

    # 3. Evaluate each valid candidate
    for idx, proposal in enumerate(client_result.proposals, 1):
        print(f"[{canonical_skill}] Evaluating candidate #{idx}: proposed regex {proposal.proposed_regex!r}...")
        eval_result: EvaluationResult = evaluate_candidate_proposal(
            proposal,
            vocab,
            postings,
            human_validated_samples=benchmark_snippets,
            worker_timeout_sec=15.0,
        )

        md_report = generate_audit_markdown_report(eval_result, proposal)

        # Save Markdown report
        md_filename = f"{canonical_skill.lower()}_pilot_report_{sanitized_model}_cand{idx}.md"
        md_path = ARTIFACTS_DIR / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        cand_data = {
            "candidate_index": idx,
            "proposal": proposal.to_dict(),
            "evaluation": {
                "is_valid_regex": eval_result.is_valid_regex,
                "safety_check_passed": eval_result.safety_check_passed,
                "safety_warnings": eval_result.safety_warnings,
                "worker_timeout_occurred": eval_result.worker_timeout_occurred,
                "synthetic_tests_passed": eval_result.synthetic_tests_passed,
                "corpus_current_count": eval_result.corpus_current_count,
                "corpus_candidate_count": eval_result.corpus_candidate_count,
                "net_count_difference": eval_result.net_count_difference,
                "shared_ids_count": eval_result.shared_ids_count,
                "current_only_count": len(eval_result.current_only_ids),
                "candidate_only_count": len(eval_result.candidate_only_ids),
                "current_only_preview": eval_result.current_only_ids[:10],
                "candidate_only_preview": eval_result.candidate_only_ids[:10],
                "ground_truth_metrics": eval_result.ground_truth_metrics,
                "execution_time_sec": eval_result.execution_time_sec,
            },
            "markdown_report_path": str(md_path.relative_to(PROJECT_ROOT)),
        }
        result_data["evaluated_candidates"].append(cand_data)

    # Save overall JSON artifact
    out_json_path = ARTIFACTS_DIR / f"{canonical_skill.lower()}_pilot_result_{sanitized_model}.json"
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    return result_data


def run_full_pilot(
    model_name: str = DEFAULT_MODEL,
    host: str = DEFAULT_OLLAMA_HOST,
    seed: int = 20261030,
) -> Dict[str, Any]:
    """
    Executes the full discovery and evaluation pilot for R and Excel (Phase 2 legacy).
    """
    print(f"=== Starting Local LLM Regex Pilot (Model: {model_name}) ===")

    # 1. Load vocabulary and raw corpus
    print("Loading skills vocabulary and corpus...")
    vocab = SkillVocabulary.load_from_file(SKILLS_VOCAB_PATH)
    with open(RAW_CORPUS_PATH, "r", encoding="utf-8") as f:
        postings = json.load(f)
    print(f"Loaded {len(postings)} corpus postings and {len(vocab.skills)} canonical skills.")

    # 2. Load benchmark datasets (strict holdout)
    print("Loading human benchmark workbooks...")
    bench_ids, r_bench, excel_bench = load_benchmark_datasets()
    print(f"Loaded {len(bench_ids)} unique benchmark posting IDs (Holdout size: R={len(r_bench)}, Excel={len(excel_bench)}).")

    # 3. Sample discovery snippets (excluding benchmark IDs)
    print("Sampling discovery context snippets...")
    r_discovery = sample_discovery_snippets(
        postings, "R", vocab,
        seed=seed, current_hits_n=20, near_miss_n=20, negative_controls_n=10,
        excluded_posting_ids=bench_ids,
    )
    r_diag = verify_discovery_sample(r_discovery, bench_ids)

    excel_discovery = sample_discovery_snippets(
        postings, "Excel", vocab,
        seed=seed, current_hits_n=20, near_miss_n=20, negative_controls_n=10,
        excluded_posting_ids=bench_ids,
    )
    excel_diag = verify_discovery_sample(excel_discovery, bench_ids)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = ARTIFACTS_DIR / "discovery_samples_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"R": r_diag, "Excel": excel_diag}, f, indent=2)
    print(f"Discovery samples verified and diagnostics saved to {summary_path.name}.")

    # 4. Run R experiment
    print("\n--- Running Experiment 1: R ---")
    r_result = run_skill_pilot(
        "R", vocab, postings, r_discovery, r_bench,
        model_name=model_name, host=host, seed=seed,
    )

    # 5. Run Excel experiment
    print("\n--- Running Experiment 2: Microsoft Excel ---")
    excel_result = run_skill_pilot(
        "Excel", vocab, postings, excel_discovery, excel_bench,
        model_name=model_name, host=host, seed=seed,
    )

    return {
        "model_name": model_name,
        "seed": seed,
        "discovery_diagnostics": {"R": r_diag, "Excel": excel_diag},
        "r_result": r_result,
        "excel_result": excel_result,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM Regex Audit Pilot Runner")
    parser.add_argument("--phase", type=int, default=3, choices=[2, 3], help="Experiment Phase (2 or 3)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--seed", type=int, default=20261030, help="Random sampling seed")
    args = parser.parse_args()

    if args.phase == 3:
        run_phase3_pilot(model_name=args.model, seed=args.seed)
    else:
        run_full_pilot(model_name=args.model, seed=args.seed)


