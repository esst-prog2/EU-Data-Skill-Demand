"""
analysis/llm_regex_audit/prompt_builder.py

Structured prompt construction for offline LLM regular expression auditing.
Provider-independent, schema-enforced, and snippet-bounded.
Architecturally prevents benchmark leakage by strictly accepting discovery samples only.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from src.analytics import SkillVocabulary
from .models import BenchmarkSnippet, DiscoverySnippet, GroundTruthStatus
from .schema import CANDIDATE_OUTPUT_JSON_SCHEMA


SYSTEM_AUDITOR_INSTRUCTION = """You are an expert Regular Expression Engineer specializing in tech skill extraction from European job postings.
Your role is to audit and propose refined regular expressions and tag aliases for technical skills.
Return ONLY valid JSON adhering strictly to the candidate schema."""


def build_audit_prompt(
    canonical_skill: str,
    vocabulary: SkillVocabulary,
    samples: Sequence[DiscoverySnippet],
    *,
    skill_specific_guidance: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Constructs a structured, provider-independent prompt payload containing
    canonical skill metadata, bounded context snippets, and schema instructions.

    Architectural Invariant:
    Strictly accepts DiscoverySnippet objects. If any BenchmarkSnippet or human ground-truth
    status is detected, a ValueError is raised immediately to prevent benchmark leakage.
    """
    skill_entry = next((s for s in vocabulary.skills if s["canonical"] == canonical_skill), None)
    current_regex = skill_entry.get("regex", "") if skill_entry else ""
    current_aliases = skill_entry.get("aliases", []) if skill_entry else []
    category = skill_entry.get("category", "") if skill_entry else ""

    sample_items = []
    for s in samples:
        # Strict benchmark leakage validation
        if isinstance(s, BenchmarkSnippet):
            raise ValueError(
                f"Benchmark leakage violation: BenchmarkSnippet (sample_id={s.sample_id!r}) "
                "cannot be passed to prompt builder. Benchmark holdouts must remain strictly blind."
            )

        gt_status = getattr(s, "ground_truth_status", None)
        if gt_status in (
            GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE,
            GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE,
            GroundTruthStatus.HUMAN_UNEVALUABLE,
        ):
            raise ValueError(
                f"Benchmark leakage violation: Sample {s.sample_id!r} has human ground truth status "
                f"({gt_status}). Benchmark annotations must never enter the LLM prompt."
            )

        stratum = getattr(s, "stratum", "")
        if stratum in ("human_annotated_benchmark", "human_annotated"):
            raise ValueError(
                f"Benchmark leakage violation: Sample {s.sample_id!r} originates from benchmark stratum {stratum!r}."
            )

        sample_items.append({
            "sample_id": s.sample_id,
            "stratum": s.stratum,
            "category": s.category,
            "country": s.country,
            "snippet": s.snippet,
        })

    instructions = [
        f'The "canonical_skill" field in your JSON output MUST be set strictly to the exact string "{canonical_skill}". Do not modify or replace the canonical skill name.',
        "Review the current regular expression against the provided context snippets.",
        "Identify blind spots, false negatives, or boundary vulnerabilities in the current pattern.",
        "Identify confounding false-positive triggers (e.g. departments, currencies, hardware models, or ordinary verbs).",
        "Propose a refined, boundary-safe Python regular expression without leading/trailing slashes (re.IGNORECASE is applied automatically).",
        "CRITICAL REGEX CONSTRAINTS: DO NOT use `^` (start-of-string) or `$` (end-of-string) anchors, as the pattern searches within full job descriptions. DO NOT use nested word boundaries or redundant alternations such as `\\b(?:\\b|\\s|\\.)?\\b` which trigger catastrophic backtracking (ReDoS) and cause hard timeouts.",
        "Keep the pattern concise, explainable, and simple (under 120 characters, max 3-5 alternations). Do not generate exhaustive lists of 20+ arbitrary libraries or tools.",
        "Propose any new standardized lowercase tag aliases if relevant (separate from regex). Note that tag aliases are audited separately against native platform tags.",
        "Provide explicit positive test cases (phrases it MUST match) and negative test cases (phrases it MUST reject).",
        "Explain the technical rationale for each lookahead/lookbehind guard used in your proposed regex.",
        "Highlight potential false-positive risks and any ambiguous cases that require human expert review.",
    ]
    if skill_specific_guidance:
        instructions.extend(skill_specific_guidance)

    snippets_text = "\n".join(
        f"[{idx + 1}] (Stratum: {s.stratum}) {s.snippet}"
        for idx, s in enumerate(samples)
    )

    instructions_text = "\n".join(f"{i + 1}. {inst}" for i, inst in enumerate(instructions))

    user_prompt = (
        f"# AUDIT TASK: Regex Refinement for Technical Skill '{canonical_skill}'\n\n"
        f"**TARGET SKILL:** {canonical_skill} (Domain: {category or 'Technical skill'})\n"
        f"**CURRENT PRODUCTION REGEX:** `{current_regex or '[None]'}`\n"
        f"**CURRENT PRODUCTION ALIASES:** `{current_aliases}`\n\n"
        f"## CONTEXT SNIPPETS FROM REAL JOB POSTINGS ({len(samples)} examples):\n"
        f"{snippets_text}\n\n"
        f"## TASK INSTRUCTIONS:\n"
        f"{instructions_text}\n\n"
        f"## CRITICAL OUTPUT INSTRUCTION:\n"
        f"Return ONLY a valid JSON object matching the candidate schema where 'canonical_skill' is strictly '{canonical_skill}'."
    )

    return {
        "system_instruction": SYSTEM_AUDITOR_INSTRUCTION,
        "user_prompt": user_prompt,
        "target_skill": canonical_skill,
        "sample_count": len(samples),
        "context_samples": sample_items,
    }
