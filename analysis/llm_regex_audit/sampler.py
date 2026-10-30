"""
analysis/llm_regex_audit/sampler.py

Deterministic sample extraction, bounded snippet generation, and stratum classification.
Strictly separates discovery snippets (for prompt construction) from benchmark snippets
(for independent, blind candidate evaluation).
"""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from src.analytics import SkillVocabulary, extract_skills_from_posting
from .models import (
    BenchmarkSnippet,
    DiscoverySnippet,
    GroundTruthStatus,
    normalize_human_label,
)


def extract_bounded_snippet(
    text: str,
    match_start: int,
    match_end: int,
    window: int = 120,
) -> Tuple[str, Tuple[int, int]]:
    """
    Extracts a bounded context window around a match span (±window chars).
    Expands outward to nearest whitespace or punctuation to avoid amputating words.
    Normalizes internal whitespace and attaches ellipsis indicators if truncated.
    Returns (cleaned_snippet, (new_match_start, new_match_end)).
    """
    if not text:
        return "", (0, 0)

    raw_len = len(text)
    start = max(0, match_start - window)
    end = min(raw_len, match_end + window)

    # Word-boundary expansion outward
    while start > 0 and not text[start - 1].isspace() and text[start - 1] not in ",.;:()[]{}":
        start -= 1
        if match_start - start > window + 40:
            break

    while end < raw_len and not text[end].isspace() and text[end] not in ",.;:()[]{}":
        end += 1
        if end - match_end > window + 40:
            break

    prefix = "... " if start > 0 else ""
    suffix = " ..." if end < raw_len else ""

    raw_slice = text[start:end]

    # Normalize newlines and excess whitespace while tracking approximate span
    normalized_slice = " ".join(raw_slice.split())
    cleaned_snippet = f"{prefix}{normalized_slice}{suffix}"

    return cleaned_snippet, (start, end)


# Domain-specific heuristic candidate patterns for discovery
BROAD_DISCOVERY_PATTERNS: Dict[str, re.Pattern] = {
    "R": re.compile(
        r"(?<![A-Za-z0-9_])R(?![A-Za-z0-9_])|\b[Rr]\s*(?:lang|language|programming|scripting|studio|shiny|markdown)\b|\b(?:software|package)\s+R\b",
        re.IGNORECASE,
    ),
    "Excel": re.compile(
        r"\bexcel\b|\b(?:ms|microsoft)\s*excel\b|\bexcel\s+vba\b|\bexcel\s+reporting\b|\badvanced\s+excel\b|\bspreadsheets?\b",
        re.IGNORECASE,
    ),
}

# Synthetic difficult negative confounding controls for regression validation
SYNTHETIC_DIFFICULT_NEGATIVES: Dict[str, List[str]] = {
    "R": [
        "Leading our European R&D initiatives across product lines.",
        "Responsible for processing invoices in our A/R department.",
        "Diagnostics for hardware revision Model R-200.",
        "Tracking serial batch R/1204 in logistics.",
        "System build R.10 release notes.",
        "Compensation: R$ 8,000 per month gross.",
        "The applicant must have an R.N. nursing license.",
        "Contact Dr. R. Watson in the administrative office.",
    ],
    "Excel": [
        "Candidates should excel in communication and leadership skills.",
        "We are looking for individuals who excel at analytical problem solving.",
        "Applicants who excel within cross-functional engineering teams.",
        "Demonstrated ability to excel as a team lead under pressure.",
        "Engineers who excel with complex distributed architectures.",
    ],
}


def sample_discovery_snippets(
    postings: Sequence[Dict[str, Any]],
    canonical_skill: str,
    vocabulary: SkillVocabulary,
    *,
    seed: int = 20261030,
    current_hits_n: int = 20,
    near_miss_n: int = 20,
    negative_controls_n: int = 10,
    include_synthetic_difficult_negatives: bool = True,
    excluded_posting_ids: Optional[Set[str] | Sequence[str]] = None,
    window: int = 120,
) -> List[DiscoverySnippet]:
    """
    Deterministically samples context snippets across discovery strata:
    1. Synthetic difficult negative controls (known confounding distractors).
    2. Production-positive examples (current production extractor hits).
    3. Unverified near-misses (broad heuristic match, but production regex misses).
    4. Unrelated negative controls (postings with zero candidate mentions).

    Crucially, any IDs in excluded_posting_ids (e.g. human benchmark datasets)
    are strictly excluded to guarantee prompt-evaluation separation and zero leakage.
    """
    rng = random.Random(seed)
    sampled_snippets: List[DiscoverySnippet] = []
    seen_posting_ids: Set[str] = set()

    if excluded_posting_ids:
        seen_posting_ids.update(str(pid) for pid in excluded_posting_ids)

    # 1. Add synthetic difficult negative controls
    if include_synthetic_difficult_negatives:
        difficult_cases = SYNTHETIC_DIFFICULT_NEGATIVES.get(canonical_skill, [])
        for idx, test_str in enumerate(difficult_cases):
            sampled_snippets.append(
                DiscoverySnippet(
                    sample_id=f"synth_diff_neg_{idx:02d}",
                    posting_id=f"synthetic_neg_{idx:02d}",
                    canonical_skill=canonical_skill,
                    stratum="difficult_negative_synthetic",
                    ground_truth_status=GroundTruthStatus.DIFFICULT_NEGATIVE_SYNTHETIC,
                    snippet=test_str,
                    source_dataset="synthetic_regression_corpus",
                    match_span=(0, len(test_str)),
                )
            )

    # 2. Categorize raw corpus postings into strata
    prod_hits: List[Tuple[Dict[str, Any], int, int]] = []
    near_misses: List[Tuple[Dict[str, Any], int, int]] = []
    unrelated_controls: List[Dict[str, Any]] = []

    broad_pat = BROAD_DISCOVERY_PATTERNS.get(
        canonical_skill,
        re.compile(rf"\b{re.escape(canonical_skill)}\b", re.IGNORECASE),
    )

    for p in postings:
        pid = str(p.get("id") or p.get("public_slug") or p.get("slug") or "")
        if not pid or pid in seen_posting_ids:
            continue

        desc = p.get("description") or ""
        if not desc or not isinstance(desc, str):
            continue

        prod_skills = extract_skills_from_posting(p, vocabulary)
        is_prod_hit = canonical_skill in prod_skills

        broad_match = broad_pat.search(desc)

        if is_prod_hit:
            m_start = broad_match.start() if broad_match else 0
            m_end = broad_match.end() if broad_match else min(len(desc), 20)
            prod_hits.append((p, m_start, m_end))
        elif broad_match:
            # Broad keyword matches, but production regex did not extract it
            near_misses.append((p, broad_match.start(), broad_match.end()))
        else:
            unrelated_controls.append(p)

    # Deterministic sampling from each stratum
    sample_prod = rng.sample(prod_hits, min(current_hits_n, len(prod_hits)))
    sample_near = rng.sample(near_misses, min(near_miss_n, len(near_misses)))
    sample_ctrl = rng.sample(unrelated_controls, min(negative_controls_n, len(unrelated_controls)))

    for idx, (p, m_start, m_end) in enumerate(sample_prod):
        pid = str(p.get("id") or p.get("public_slug") or f"prod_{idx}")
        desc = p.get("description") or ""
        snip, span = extract_bounded_snippet(desc, m_start, m_end, window=window)
        sampled_snippets.append(
            DiscoverySnippet(
                sample_id=f"prod_hit_{idx:03d}",
                posting_id=pid,
                canonical_skill=canonical_skill,
                stratum="production_positive",
                ground_truth_status=GroundTruthStatus.PRODUCTION_POSITIVE_UNVERIFIED,
                snippet=snip,
                source_dataset="freehire_eu_raw.json",
                category=p.get("_collection_category"),
                country=p.get("_collection_country"),
                match_span=span,
            )
        )

    for idx, (p, m_start, m_end) in enumerate(sample_near):
        pid = str(p.get("id") or p.get("public_slug") or f"near_{idx}")
        desc = p.get("description") or ""
        snip, span = extract_bounded_snippet(desc, m_start, m_end, window=window)
        sampled_snippets.append(
            DiscoverySnippet(
                sample_id=f"near_miss_{idx:03d}",
                posting_id=pid,
                canonical_skill=canonical_skill,
                stratum="unverified_near_miss",
                ground_truth_status=GroundTruthStatus.UNVERIFIED_NEAR_MISS,
                snippet=snip,
                source_dataset="freehire_eu_raw.json",
                category=p.get("_collection_category"),
                country=p.get("_collection_country"),
                match_span=span,
            )
        )

    for idx, p in enumerate(sample_ctrl):
        pid = str(p.get("id") or p.get("public_slug") or f"ctrl_{idx}")
        desc = p.get("description") or ""
        snip = ("... " + desc[: window * 2] + " ...") if len(desc) > window * 2 else desc
        sampled_snippets.append(
            DiscoverySnippet(
                sample_id=f"ctrl_neg_{idx:03d}",
                posting_id=pid,
                canonical_skill=canonical_skill,
                stratum="unrelated_negative_control",
                ground_truth_status=GroundTruthStatus.PRODUCTION_POSITIVE_UNVERIFIED,
                snippet=" ".join(snip.split()),
                source_dataset="freehire_eu_raw.json",
                category=p.get("_collection_category"),
                country=p.get("_collection_country"),
                match_span=(0, min(len(desc), window * 2)),
            )
        )

    return sampled_snippets


def load_benchmark_snippets(
    records: Sequence[Dict[str, Any]],
    canonical_skill: str,
    *,
    source_dataset: str = "human_validation",
    window: int = 120,
) -> List[BenchmarkSnippet]:
    """
    Parses and constructs verified BenchmarkSnippet instances from human-annotated records.
    Strictly normalizes human labels via normalize_human_label() and captures provenance notes.
    These snippets are exclusively reserved for candidate evaluation and MUST NEVER enter LLM prompts.
    """
    benchmarks: List[BenchmarkSnippet] = []

    for idx, rec in enumerate(records):
        pid = str(rec.get("id") or rec.get("public_slug") or f"bench_{idx:03d}")
        desc = rec.get("description") or ""
        raw_label = rec.get("human_label")

        is_valid, int_code, raw_str = normalize_human_label(raw_label)
        if not is_valid:
            raise ValueError(f"Invalid human label {raw_label!r} for posting ID {pid}: {raw_str}")

        if int_code == 1:
            status = GroundTruthStatus.HUMAN_CONFIRMED_POSITIVE
        elif int_code == 0:
            status = GroundTruthStatus.HUMAN_CONFIRMED_NEGATIVE
        else:
            status = GroundTruthStatus.HUMAN_UNEVALUABLE

        snippet_text = desc[: window * 2] if desc else "[Empty description]"
        span = (0, len(snippet_text))
        if desc:
            find_pat = rf"\b{re.escape(canonical_skill)}\b" if len(canonical_skill) <= 2 else re.escape(canonical_skill)
            m = re.search(find_pat, desc, re.IGNORECASE)
            if m:
                snippet_text, span = extract_bounded_snippet(desc, m.start(), m.end(), window=window)

        benchmarks.append(
            BenchmarkSnippet(
                sample_id=f"human_bench_{idx:03d}",
                posting_id=pid,
                canonical_skill=canonical_skill,
                ground_truth_status=status,
                snippet=snippet_text,
                source_dataset=rec.get("source_dataset", source_dataset),
                human_label=int_code,
                evidence_notes=rec.get("evidence_notes"),
                category=rec.get("category") or rec.get("_collection_category"),
                country=rec.get("country") or rec.get("_collection_country"),
                match_span=span,
                metadata={"raw_label_str": raw_str, "full_description": desc},
            )
        )

    return benchmarks


def sample_skill_postings(
    postings: Sequence[Dict[str, Any]],
    canonical_skill: str,
    vocabulary: SkillVocabulary,
    *,
    seed: int = 20261030,
    current_hits_n: int = 20,
    near_miss_n: int = 20,
    negative_controls_n: int = 10,
    human_annotated_records: Optional[Sequence[Dict[str, Any]]] = None,
    window: int = 120,
) -> List[Any]:
    """
    Backwards-compatible sampling function.
    Note: For benchmark evaluation separation, prefer sample_discovery_snippets()
    and load_benchmark_snippets() separately.
    """
    if human_annotated_records:
        benchmarks = load_benchmark_snippets(human_annotated_records, canonical_skill, window=window)
        excluded = {b.posting_id for b in benchmarks}
        discovery = sample_discovery_snippets(
            postings,
            canonical_skill,
            vocabulary,
            seed=seed,
            current_hits_n=current_hits_n,
            near_miss_n=near_miss_n,
            negative_controls_n=negative_controls_n,
            excluded_posting_ids=excluded,
            window=window,
        )
        return list(benchmarks) + list(discovery)

    return sample_discovery_snippets(
        postings,
        canonical_skill,
        vocabulary,
        seed=seed,
        current_hits_n=current_hits_n,
        near_miss_n=near_miss_n,
        negative_controls_n=negative_controls_n,
        window=window,
    )
