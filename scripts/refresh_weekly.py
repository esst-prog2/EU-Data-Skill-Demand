"""
scripts/refresh_weekly.py

Single-command local weekly data-refresh runner:
1. Backs up existing raw and processed dataset files before execution.
   - Copies to unique temporary files before atomically renaming to .bak.
   - Guards against overwriting or deleting pre-existing backup files.
   - Cleans up partial temporary files and aborts if backup creation fails partway through.
2. Executes the full pipeline sequentially:
   - eu27.py (collect fresh FreeHire EU-27 postings)
   - scripts/preprocess.py (extract skills and regenerate analytics summary)
   - scripts/check_refresh_diff.py --no-revert (inspect substantive diffs without reverting)
   - pytest (verify full test suite)
3. Stops immediately on any failure, attempts full rollback of all datasets,
   reports all errors, preserves all recovery backups if rollback is incomplete,
   and exits with a non-zero exit code.
4. On success, removes only its own temporary backups. If backup cleanup fails,
   reports cleanup failure and exits with a non-zero exit code.
   If all cleanup succeeds, reports review instructions and exits with 0.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

MANAGED_DATASETS: list[Path] = [
    ROOT_DIR / "data" / "raw" / "freehire_eu_raw.json",
    ROOT_DIR / "data" / "raw" / "collection_metadata_eu.json",
    ROOT_DIR / "data" / "processed" / "analytics_summary.json",
]


def backup_datasets(paths: list[Path]) -> tuple[dict[Path, Path], set[Path]]:
    """
    Creates temporary .bak copies of existing files and tracks missing files.

    Copies each file to a unique temporary file in the same directory first,
    then atomically renames it to the .bak destination upon completion.
    Fails clearly if a backup destination already exists or if copying fails.
    If backup creation fails partway through, cleans up only the temporary
    files and backups created during this invocation, leaving original datasets
    and pre-existing files intact.
    """
    created_backups: dict[Path, Path] = {}
    active_temp_paths: set[Path] = set()
    non_existent_before: set[Path] = set()

    try:
        for path in paths:
            if path.exists():
                backup_path = path.with_name(f"{path.name}.bak")
                if backup_path.exists():
                    raise FileExistsError(
                        f"Pre-existing backup found at {backup_path}. "
                        "Aborting to avoid overwriting or deleting an existing backup. "
                        "Please remove or rename it before running the refresh."
                    )
                temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
                active_temp_paths.add(temp_path)
                shutil.copy2(path, temp_path)
                if backup_path.exists():
                    raise FileExistsError(
                        f"Pre-existing backup found at {backup_path}. "
                        "Aborting to avoid overwriting or deleting an existing backup."
                    )
                temp_path.replace(backup_path)
                active_temp_paths.discard(temp_path)
                created_backups[path] = backup_path
            else:
                non_existent_before.add(path)
    except Exception:
        # Clean up any active temporary files created during this invocation
        for tp in active_temp_paths:
            try:
                if tp.exists():
                    tp.unlink()
            except OSError:
                pass
        # Clean up only completed backups created during this specific invocation
        for bp in created_backups.values():
            try:
                if bp.exists():
                    bp.unlink()
            except OSError:
                pass
        raise

    return created_backups, non_existent_before


def restore_backups(
    existing_backups: dict[Path, Path], non_existent_before: set[Path]
) -> list[str]:
    """
    Restores files from .bak backups and deletes newly created files on failure.

    Attempts every restore operation and reports all errors.
    Backups are retained until every dataset restoration and removal of newly
    created files succeeds. If any rollback operation fails, all available
    backups are preserved for manual recovery.
    """
    errors: list[str] = []

    # 1. Restore files that existed before the run (retain backups on disk)
    for original_path, backup_path in existing_backups.items():
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, original_path)
            else:
                errors.append(
                    f"Backup file missing for restore: {backup_path}"
                )
        except Exception as exc:
            errors.append(
                f"Failed to restore {original_path} from {backup_path}: {exc}"
            )

    # 2. Remove files that did not exist before the run
    for path in non_existent_before:
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:
            errors.append(
                f"Failed to remove newly created file {path}: {exc}"
            )

    # 3. Only delete temporary backups if every operation above succeeded
    if not errors:
        for backup_path in existing_backups.values():
            try:
                if backup_path.exists():
                    backup_path.unlink()
            except Exception as exc:
                errors.append(
                    f"Failed to remove temporary backup {backup_path}: {exc}"
                )

    return errors


def remove_backups(existing_backups: dict[Path, Path]) -> list[str]:
    """
    Removes only the .bak backup files created by this invocation upon success.

    Returns a list of error message strings if any backup deletion fails.
    """
    errors: list[str] = []
    for backup_path in existing_backups.values():
        try:
            if backup_path.exists():
                backup_path.unlink()
        except Exception as exc:
            errors.append(
                f"Failed to remove temporary backup {backup_path}: {exc}"
            )
    return errors


def run_pipeline(datasets: list[Path] | None = None) -> int:
    """Executes the local data-refresh pipeline with hardened rollback protection."""
    print("=" * 70)
    print("WEEKLY DATA REFRESH PIPELINE")
    print("=" * 70)

    if datasets is None:
        datasets = MANAGED_DATASETS

    print("[INFO] Creating backups of managed datasets before starting...")
    try:
        existing_backups, non_existent_before = backup_datasets(datasets)
    except Exception as exc:
        print(f"\n[ERROR] Backup creation failed: {exc}")
        print("[INFO] Pipeline not started. Original datasets remain untouched.")
        return 1

    steps: list[tuple[str, list[str]]] = [
        (
            "Step 1/4: Collecting fresh EU-27 job postings (eu27.py)",
            [sys.executable, str(ROOT_DIR / "eu27.py")],
        ),
        (
            "Step 2/4: Extracting skills & regenerating analytics summary (scripts/preprocess.py)",
            [sys.executable, str(ROOT_DIR / "scripts" / "preprocess.py")],
        ),
        (
            "Step 3/4: Checking substantive differences against Git HEAD (scripts/check_refresh_diff.py)",
            [
                sys.executable,
                str(ROOT_DIR / "scripts" / "check_refresh_diff.py"),
                "--no-revert",
            ],
        ),
        (
            "Step 4/4: Running full test suite (pytest)",
            [sys.executable, "-m", "pytest"],
        ),
    ]

    try:
        for step_num, (description, cmd) in enumerate(steps, 1):
            print()
            print("-" * 70)
            print(f"[{step_num}/4] {description}")
            print("-" * 70)
            result = subprocess.run(cmd, cwd=ROOT_DIR)
            if result.returncode != 0:
                print(
                    f"\n[ERROR] {description} failed with exit code {result.returncode}."
                )
                print(
                    "[INFO] Rolling back managed datasets to pre-refresh state..."
                )
                rollback_errors = restore_backups(
                    existing_backups, non_existent_before
                )
                if rollback_errors:
                    print(
                        "[ERROR] Rollback incomplete. The following errors occurred:"
                    )
                    for err in rollback_errors:
                        print(f"  - {err}")
                    print(
                        "[INFO] Recovery backups have been preserved for manual recovery."
                    )
                    return result.returncode if result.returncode != 0 else 1

                print("[INFO] Rollback complete. Original datasets preserved.")
                return result.returncode

        print()
        print("=" * 70)
        print("All pipeline steps passed. Removing temporary backup files...")
        cleanup_errors = remove_backups(existing_backups)
        if cleanup_errors:
            print(
                "[ERROR] Pipeline steps passed, but temporary backup cleanup was incomplete:"
            )
            for err in cleanup_errors:
                print(f"  - {err}")
            print(
                "[INFO] Please inspect and remove temporary backup files manually."
            )
            print("=" * 70)
            return 1

        print("Weekly refresh completed successfully!")
        print()
        print("Next steps:")
        print(
            "  1. Review changes: git status && git diff data/processed/analytics_summary.json"
        )
        print("  2. Test dashboard: uv run streamlit run app.py")
        print("  3. Commit and push manually when satisfied.")
        print("=" * 70)
        return 0

    except KeyboardInterrupt:
        print("\n[WARNING] Pipeline interrupted by user (SIGINT/KeyboardInterrupt).")
        print("[INFO] Rolling back managed datasets to pre-refresh state...")
        rollback_errors = restore_backups(existing_backups, non_existent_before)
        if rollback_errors:
            print(
                "[ERROR] Rollback incomplete. The following errors occurred:"
            )
            for err in rollback_errors:
                print(f"  - {err}")
            print(
                "[INFO] Recovery backups have been preserved for manual recovery."
            )
        else:
            print("[INFO] Rollback complete. Original datasets preserved.")
        return 1

    except Exception as exc:
        print(f"\n[ERROR] Pipeline aborted due to unexpected error: {exc}")
        print("[INFO] Rolling back managed datasets to pre-refresh state...")
        rollback_errors = restore_backups(existing_backups, non_existent_before)
        if rollback_errors:
            print(
                "[ERROR] Rollback incomplete. The following errors occurred:"
            )
            for err in rollback_errors:
                print(f"  - {err}")
            print(
                "[INFO] Recovery backups have been preserved for manual recovery."
            )
        else:
            print("[INFO] Rollback complete. Original datasets preserved.")
        return 1


def main() -> None:
    code = run_pipeline()
    sys.exit(code)


if __name__ == "__main__":
    main()
