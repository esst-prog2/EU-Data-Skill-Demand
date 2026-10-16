"""
scripts/check_refresh_diff.py

Idempotency and noise-prevention utility for automated data-refresh workflows:
1. Compares newly generated data/processed/analytics_summary.json against HEAD,
   ignoring volatile generation timestamps ("generated_at").
2. Compares newly generated data/raw/collection_metadata_eu.json against HEAD,
   ignoring collection run timestamps ("collection_timestamp_utc").
3. If both files contain no substantive differences beyond timestamps, reverts
   them back to HEAD to prevent opening empty/noisy pull requests.
4. If substantive differences exist, leaves the updated files on disk and prints
   a diagnostic summary of the detected changes.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent

SUMMARY_PATH = ROOT_DIR / "data" / "processed" / "analytics_summary.json"
METADATA_PATH = ROOT_DIR / "data" / "raw" / "collection_metadata_eu.json"


def has_substantive_summary_diff(
    current: Dict[str, Any], baseline: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Compares current analytics summary with baseline, ignoring volatile timestamps.
    Returns (has_diff, reason).
    """
    for section in ("kpis", "market_overview", "category_profiles", "geographic"):
        cur_sec = current.get(section)
        base_sec = baseline.get(section)
        if cur_sec != base_sec:
            return True, f"Section '{section}' differs from baseline."
    return False, "No substantive differences in analytics summary."


def has_substantive_metadata_diff(
    current: Dict[str, Any], baseline: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Compares current collection metadata with baseline, ignoring volatile timestamps.
    Returns (has_diff, reason).
    """
    fields_to_check = (
        "source",
        "api_endpoint",
        "geographic_scope",
        "countries",
        "categories",
        "country_count",
        "category_count",
        "unique_jobs",
        "category_distribution",
        "country_distribution",
        "query_summary",
    )
    for field in fields_to_check:
        cur_val = current.get(field)
        base_val = baseline.get(field)
        if cur_val != base_val:
            return True, f"Metadata field '{field}' differs from baseline."
    return False, "No substantive differences in collection metadata."


def get_git_head_content(rel_path: str) -> str | None:
    """Retrieves file content from git HEAD."""
    try:
        res = subprocess.run(
            ["git", "show", f"HEAD:{rel_path}"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def revert_files_to_head(*rel_paths: str) -> None:
    """Reverts specified files back to git HEAD."""
    subprocess.run(
        ["git", "checkout", "HEAD", "--", *rel_paths],
        cwd=ROOT_DIR,
        check=True,
    )


def check_and_revert_if_no_diff(
    summary_path: Path = SUMMARY_PATH,
    metadata_path: Path = METADATA_PATH,
) -> bool:
    """
    Checks for substantive differences in summary and metadata files against HEAD.
    If no substantive diff exists, reverts both files to HEAD and returns False.
    If substantive diff exists, keeps files and returns True.
    """
    rel_summary = str(summary_path.relative_to(ROOT_DIR)).replace("\\", "/")
    rel_metadata = str(metadata_path.relative_to(ROOT_DIR)).replace("\\", "/")

    head_summary_str = get_git_head_content(rel_summary)
    head_metadata_str = get_git_head_content(rel_metadata)

    if head_summary_str is None or head_metadata_str is None:
        print("[INFO] Could not read baseline from HEAD; keeping updated files.")
        return True

    try:
        cur_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        base_summary = json.loads(head_summary_str)
        cur_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        base_metadata = json.loads(head_metadata_str)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Error reading files for comparison: {exc}. Keeping updated files.")
        return True

    summary_diff, summary_reason = has_substantive_summary_diff(cur_summary, base_summary)
    metadata_diff, metadata_reason = has_substantive_metadata_diff(cur_metadata, base_metadata)

    if summary_diff or metadata_diff:
        reasons = []
        if summary_diff:
            reasons.append(f"Summary: {summary_reason}")
        if metadata_diff:
            reasons.append(f"Metadata: {metadata_reason}")
        print(f"[INFO] Substantive data change detected: {'; '.join(reasons)}")
        return True

    print("[INFO] No substantive changes detected (only timestamps changed). Reverting files to avoid noisy PR.")
    revert_files_to_head(rel_summary, rel_metadata)
    return False


def main() -> None:
    has_diff = check_and_revert_if_no_diff()
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"has_diff={'true' if has_diff else 'false'}\n")


if __name__ == "__main__":
    main()
