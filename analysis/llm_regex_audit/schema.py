"""
analysis/llm_regex_audit/schema.py

JSON Schema definitions, candidate structure validation, and static regex safety verification.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Tuple

from .models import CandidateProposal

CANDIDATE_OUTPUT_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CandidateSkillRuleProposal",
    "description": "Structured LLM proposal for skill regular expression refinement and alias discovery.",
    "type": "object",
    "required": [
        "canonical_skill",
        "proposed_regex",
        "proposed_aliases",
        "explanation",
        "positive_test_cases",
        "negative_test_cases",
        "false_positive_risks",
        "confidence_score",
        "human_review_required",
    ],
    "properties": {
        "canonical_skill": {
            "type": "string",
            "description": "The exact canonical skill name in the vocabulary.",
        },
        "proposed_regex": {
            "type": "string",
            "description": "Python re-compatible regular expression pattern for description matching.",
        },
        "proposed_aliases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Normalized lowercase alias strings for native tag matching (evaluated separately).",
        },
        "explanation": {
            "type": "string",
            "description": "Technical justification of each boundary, lookahead, and guard.",
        },
        "positive_test_cases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific phrases or sentences this regex MUST match.",
        },
        "negative_test_cases": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific phrases or confounding sentences this regex MUST reject.",
        },
        "false_positive_risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Identified failure modes, ambiguous contexts, or risky syntactic environments.",
        },
        "confidence_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Subjective model confidence between 0.0 and 1.0.",
        },
        "human_review_required": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific linguistic ambiguities or business edge cases needing human expert verification.",
        },
    },
    "additionalProperties": False,
}


def validate_candidate_dict(data: Any) -> Tuple[bool, List[str], CandidateProposal | None]:
    """
    Validates a raw dictionary against the candidate rule schema.
    Returns (is_valid, error_messages, parsed_proposal_or_none).
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        return False, ["Payload must be a JSON object / dictionary."], None

    required_fields = [
        "canonical_skill",
        "proposed_regex",
        "proposed_aliases",
        "explanation",
        "positive_test_cases",
        "negative_test_cases",
        "false_positive_risks",
        "confidence_score",
        "human_review_required",
    ]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return False, errors, None

    # Type & boundary checks
    if not isinstance(data["canonical_skill"], str) or not data["canonical_skill"].strip():
        errors.append("'canonical_skill' must be a non-empty string.")

    if not isinstance(data["proposed_regex"], str) or not data["proposed_regex"].strip():
        errors.append("'proposed_regex' must be a non-empty string.")

    for list_field in ["proposed_aliases", "positive_test_cases", "negative_test_cases", "false_positive_risks", "human_review_required"]:
        if not isinstance(data[list_field], list):
            errors.append(f"'{list_field}' must be a list of strings.")
        elif any(not isinstance(item, str) for item in data[list_field]):
            errors.append(f"All elements in '{list_field}' must be strings.")

    if not isinstance(data["explanation"], str):
        errors.append("'explanation' must be a string.")

    score = data["confidence_score"]
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not (0.0 <= score <= 1.0):
        errors.append(f"'confidence_score' must be a numeric float between 0.0 and 1.0 (got {score!r}).")

    if errors:
        return False, errors, None

    raw_regex = data["proposed_regex"].strip()
    # Strip python raw string prefixes r'...' or r"..." or quotes
    if (raw_regex.startswith("r'") and raw_regex.endswith("'")) or (raw_regex.startswith('r"') and raw_regex.endswith('"')):
        raw_regex = raw_regex[2:-1].strip()
    elif (raw_regex.startswith("'") and raw_regex.endswith("'")) or (raw_regex.startswith('"') and raw_regex.endswith('"')):
        raw_regex = raw_regex[1:-1].strip()
    elif raw_regex.startswith("r'") or raw_regex.startswith('r"'):
        raw_regex = raw_regex[2:].strip()

    perl_match = re.match(r"^/(.*)/([a-zA-Z]*)$", raw_regex)
    clean_regex = perl_match.group(1).strip() if perl_match else raw_regex

    proposal = CandidateProposal(
        canonical_skill=data["canonical_skill"].strip(),
        proposed_regex=clean_regex,
        proposed_aliases=[a.strip().lower() for a in data["proposed_aliases"] if a.strip()],
        explanation=data["explanation"].strip(),
        positive_test_cases=[c for c in data["positive_test_cases"] if c.strip()],
        negative_test_cases=[c for c in data["negative_test_cases"] if c.strip()],
        false_positive_risks=[r for r in data["false_positive_risks"] if r.strip()],
        confidence_score=float(score),
        human_review_required=[h for h in data["human_review_required"] if h.strip()],
        raw_response=data,
    )
    return True, [], proposal


# Static ReDoS anti-pattern heuristics: nested repetitions and repeated alternations
NESTED_REPETITION_PATTERNS = [
    re.compile(r"\([^)]*[\*\+][^)]*\)[\*\+]"),            # e.g. (a+)+, (.*)*, (x*)+
    re.compile(r"\(\?:[^)]*[\*\+][^)]*\)[\*\+]"),         # e.g. (?:a+)+, (?:.*)+
    re.compile(r"\b\.\*[\*\+]"),                          # e.g. .*+
    re.compile(r"\([^)]*\|[^)]*\)[\*\+]"),                # e.g. (a|a)+, ([a-z]|[a-z0-9])+
]


def validate_regex_safety(
    pattern: str,
    adversarial_timeout_sec: float = 0.5,
) -> Tuple[bool, List[str]]:
    """
    Evaluates pattern compilation, rejects empty patterns, and applies conservative ReDoS safety checks.

    Limitations:
    Python's standard 're' module has no built-in per-match timeout mechanism.
    These checks detect common catastrophic backtracking anti-patterns and test
    against synthetic adversarial strings, but cannot guarantee linear-time safety
    without a non-backtracking engine (such as Google RE2).
    """
    warnings: List[str] = []

    # 1. Non-empty check
    if not pattern or not pattern.strip():
        return False, ["Regex pattern cannot be empty or whitespace only."]

    # 2. Compilation check
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return False, [f"Invalid Python regex syntax: {e}"]

    # 3. Static ReDoS anti-pattern inspection
    for anti_pat in NESTED_REPETITION_PATTERNS:
        if anti_pat.search(pattern):
            return False, [f"Potentially catastrophic ReDoS pattern detected: nested repetition or repeated alternation in {pattern!r}."]

    # 4. Adversarial execution tests with synthetic repetitive input
    test_adversarial_strings = [
        "a" * 2000 + "!" + "b" * 2000,
        "R" * 1500 + " " + "r" * 1500,
        "excel " * 500 + "in a professional environment",
        " " * 4000,
    ]

    for adv in test_adversarial_strings:
        start_t = time.perf_counter()
        try:
            compiled.search(adv)
        except Exception as e:
            return False, [f"Error during adversarial string evaluation: {e}"]
        elapsed = time.perf_counter() - start_t
        if elapsed > adversarial_timeout_sec:
            return False, [
                f"Adversarial execution exceeded safety threshold ({elapsed:.3f}s > {adversarial_timeout_sec}s). "
                f"Pattern shows high risk of catastrophic backtracking."
            ]

    return True, warnings
