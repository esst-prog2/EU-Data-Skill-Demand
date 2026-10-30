"""
analysis/llm_regex_audit/alias_auditor.py

Audits candidate tag aliases against the actual FreeHire native dataset.
Calculates exact native tag frequencies, detects cross-skill overlaps,
and determines whether an alias adds genuine coverage beyond existing vocabulary.

Strict Conceptual Separation:
1. Alias registered in vocabulary (a dictionary definition, NOT evidence of occurrence).
2. Alias observed in native platform tags (empirical frequency > 0).
3. Alias not observed in native tags (empirical frequency == 0).
4. Alias adding new posting coverage (net new postings > 0).
5. Alias conflicting with another skill (cross-skill collision).
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set

from src.analytics import SkillVocabulary


def audit_tag_aliases(
    canonical_skill: str,
    proposed_aliases: Sequence[str],
    postings: Sequence[Dict[str, Any]],
    vocabulary: SkillVocabulary,
) -> Dict[str, Any]:
    """
    Audits a list of proposed tag aliases against the observed FreeHire corpus.

    Strictly separates:
    - registered_in_vocabulary
    - observed_in_native_tags (frequency > 0)
    - not_observed_in_native_tags (frequency == 0)
    - adds_new_coverage (net new postings > 0)
    - conflicts_with_other_skill
    """
    # 1. Build corpus native tag frequency index
    tag_counter: Counter[str] = Counter()
    posting_tags_map: Dict[str, Set[str]] = {}

    for p in postings:
        pid = str(p.get("id") or p.get("public_slug") or p.get("slug") or "")
        raw_tags = p.get("skills") or []
        cleaned_tags = set()
        for t in raw_tags:
            if isinstance(t, str) and t.strip():
                clean_t = t.strip().lower()
                cleaned_tags.add(clean_t)
                tag_counter[clean_t] += 1
        if pid:
            posting_tags_map[pid] = cleaned_tags

    # 2. Build cross-skill vocabulary lookup
    canonical_tags_map: Dict[str, str] = {}
    current_skill_aliases: Set[str] = set()

    for skill_entry in vocabulary.skills:
        c_name = skill_entry["canonical"]
        c_tags = {c_name.lower()}
        for a in skill_entry.get("aliases", []):
            c_tags.add(a.lower())

        if c_name == canonical_skill:
            current_skill_aliases = c_tags
        else:
            for tag_str in c_tags:
                canonical_tags_map[tag_str] = c_name

    # 3. Audit each proposed alias
    audited_aliases: List[Dict[str, Any]] = []

    for alias in proposed_aliases:
        alias_clean = alias.strip().lower()
        if not alias_clean:
            continue

        raw_freq = tag_counter.get(alias_clean, 0)
        is_registered = alias_clean in current_skill_aliases
        is_observed = raw_freq > 0
        not_observed = raw_freq == 0
        conflicting_skill = canonical_tags_map.get(alias_clean)

        # Net new postings (postings with this tag that don't already have an existing canonical tag)
        net_new_ids: Set[str] = set()
        if is_observed and not is_registered and not conflicting_skill:
            for pid, p_tags in posting_tags_map.items():
                if alias_clean in p_tags and not any(curr in p_tags for curr in current_skill_aliases):
                    net_new_ids.add(pid)

        adds_coverage = len(net_new_ids) > 0

        # Disambiguated recommendation determination
        if conflicting_skill:
            verdict = "CONFLICTING_OVERLAP"
            reason = f"Alias collides with another canonical skill ({conflicting_skill})."
        elif is_registered and not_observed:
            verdict = "ALREADY_REGISTERED_BUT_UNOBSERVED"
            reason = "Alias is already registered in skills_vocabulary.json, but has 0 observed native occurrences."
        elif is_registered and is_observed:
            verdict = "ALREADY_REGISTERED_AND_OBSERVED"
            reason = f"Alias is already registered in vocabulary and actively observed in {raw_freq} postings."
        elif not is_registered and not_observed:
            verdict = "UNSUPPORTED_ZERO_COUNT"
            reason = "Alias never appears in native FreeHire skill tags (0 observed occurrences)."
        elif not is_registered and is_observed and adds_coverage:
            verdict = "SUPPORTED_SAFE_ADDS_COVERAGE"
            reason = f"Appears in {raw_freq} postings; adds {len(net_new_ids)} net new native detections."
        elif not is_registered and is_observed and not adds_coverage:
            verdict = "OBSERVED_BUT_REDUNDANT"
            reason = f"Appears in {raw_freq} postings, but all matching postings already carry an existing tag."
        else:
            verdict = "UNKNOWN"
            reason = "Unclassified alias state."

        audited_aliases.append({
            "alias": alias_clean,
            "native_tag_frequency": raw_freq,
            "registered_in_vocabulary": is_registered,
            "observed_in_native_tags": is_observed,
            "not_observed_in_native_tags": not_observed,
            "adds_new_coverage": adds_coverage,
            "conflicts_with_other_skill": conflicting_skill,
            # Backwards compatibility keys
            "already_in_vocabulary": is_registered,
            "conflicting_skill": conflicting_skill,
            "net_new_postings_count": len(net_new_ids),
            "verdict": verdict,
            "reason": reason,
        })

    supported_count = sum(1 for a in audited_aliases if a["verdict"] == "SUPPORTED_SAFE_ADDS_COVERAGE")
    unsupported_count = sum(1 for a in audited_aliases if a["not_observed_in_native_tags"])
    conflicts_count = sum(1 for a in audited_aliases if a["conflicts_with_other_skill"] is not None)
    registered_count = sum(1 for a in audited_aliases if a["registered_in_vocabulary"])

    return {
        "canonical_skill": canonical_skill,
        "total_proposed_aliases": len(audited_aliases),
        "registered_in_vocabulary_count": registered_count,
        "supported_adds_coverage_count": supported_count,
        "unsupported_zero_count": unsupported_count,
        "conflicts_count": conflicts_count,
        "aliases": audited_aliases,
    }


def format_alias_audit_markdown(audit_result: Dict[str, Any]) -> str:
    """Formats the alias audit dictionary as a GitHub-flavored Markdown table."""
    skill = audit_result["canonical_skill"]
    lines = [
        f"### Native Tag Alias Audit: {skill}",
        f"**Evaluated Candidates:** {audit_result['total_proposed_aliases']} | "
        f"**Registered in Vocab:** {audit_result.get('registered_in_vocabulary_count', 0)} | "
        f"**Adds New Coverage:** {audit_result.get('supported_adds_coverage_count', 0)} | "
        f"**Unobserved (0 Count):** {audit_result['unsupported_zero_count']} | "
        f"**Conflicts:** {audit_result['conflicts_count']}",
        "",
        "> *Note: An alias being registered in the vocabulary is a dictionary definition and does not constitute evidence of data occurrence or coverage impact.*",
        "",
        "| Proposed Alias | In Vocab? | Native Count | Net New Hits | Conflict | Disambiguated Audit Verdict | Explanation |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for item in audit_result["aliases"]:
        conflict_str = f"`{item['conflicts_with_other_skill']}`" if item["conflicts_with_other_skill"] else "None"
        in_vocab_str = "YES" if item["registered_in_vocabulary"] else "NO"
        verdict_badge = {
            "SUPPORTED_SAFE_ADDS_COVERAGE": "✅ ADDS COVERAGE",
            "OBSERVED_BUT_REDUNDANT": "ℹ️ REDUNDANT HIT",
            "UNSUPPORTED_ZERO_COUNT": "❌ UNOBSERVED (0)",
            "CONFLICTING_OVERLAP": "⚠️ CONFLICT",
            "ALREADY_REGISTERED_BUT_UNOBSERVED": "ℹ️ IN VOCAB (0 in data)",
            "ALREADY_REGISTERED_AND_OBSERVED": "✅ IN VOCAB (Active)",
        }.get(item["verdict"], item["verdict"])

        lines.append(
            f"| `{item['alias']}` | `{in_vocab_str}` | `{item['native_tag_frequency']}` | "
            f"`{item['net_new_postings_count']}` | {conflict_str} | "
            f"**{verdict_badge}** | {item['reason']} |"
        )

    lines.append("")
    return "\n".join(lines)

    lines.append("")
    return "\n".join(lines)

