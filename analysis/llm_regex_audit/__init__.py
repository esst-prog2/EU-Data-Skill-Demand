"""
analysis/llm_regex_audit

Offline infrastructure for LLM-assisted regex discovery, auditing, and validation.
Completely decoupled from production extraction and runtime dashboard execution.
Strictly separates discovery/prompt samples from blind evaluation benchmarks.
"""

from __future__ import annotations

from .alias_auditor import audit_tag_aliases, format_alias_audit_markdown
from .client import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_HOST,
    OllamaClientResult,
    get_local_models,
    get_model_details,
    is_ollama_running,
    request_candidate_proposals,
)
from .evaluator import evaluate_candidate_proposal
from .models import (
    BenchmarkSnippet,
    CandidateProposal,
    DiscoverySnippet,
    EvaluationResult,
    GroundTruthStatus,
    SampleSnippet,
    normalize_human_label,
)
from .pilot_runner import (
    load_benchmark_datasets,
    run_phase3_pilot,
    run_phase3_skill_pilot,
    run_skill_pilot,
    verify_discovery_sample,
)
from .prompt_builder import build_audit_prompt
from .reporter import generate_audit_markdown_report
from .sampler import (
    extract_bounded_snippet,
    load_benchmark_snippets,
    sample_discovery_snippets,
    sample_skill_postings,
)
from .schema import (
    CANDIDATE_OUTPUT_JSON_SCHEMA,
    validate_candidate_dict,
    validate_regex_safety,
)
from .synthetic_suites import SYNTHETIC_SUITES, evaluate_synthetic_suite

__all__ = [
    "GroundTruthStatus",
    "DiscoverySnippet",
    "BenchmarkSnippet",
    "SampleSnippet",
    "CandidateProposal",
    "EvaluationResult",
    "normalize_human_label",
    "CANDIDATE_OUTPUT_JSON_SCHEMA",
    "validate_candidate_dict",
    "validate_regex_safety",
    "extract_bounded_snippet",
    "sample_discovery_snippets",
    "load_benchmark_snippets",
    "sample_skill_postings",
    "build_audit_prompt",
    "evaluate_candidate_proposal",
    "generate_audit_markdown_report",
    "audit_tag_aliases",
    "format_alias_audit_markdown",
    "evaluate_synthetic_suite",
    "SYNTHETIC_SUITES",
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_HOST",
    "OllamaClientResult",
    "get_local_models",
    "get_model_details",
    "is_ollama_running",
    "request_candidate_proposals",
    "load_benchmark_datasets",
    "verify_discovery_sample",
    "run_skill_pilot",
    "run_phase3_skill_pilot",
    "run_phase3_pilot",
]
