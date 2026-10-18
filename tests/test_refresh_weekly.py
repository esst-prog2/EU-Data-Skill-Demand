"""
tests/test_refresh_weekly.py

Unit tests for scripts/refresh_weekly.py local weekly refresh pipeline:
- Backup creation, restoration, and cleanup for managed datasets.
- Pre-existing .bak protection (never overwritten or deleted).
- Backup creation failure handling and cleanup of partial backups.
- Independent dataset restoration during rollback even if one fails.
- Retention of all recovery backups when any rollback operation fails.
- Safe handling of absent files and cleanup of newly created files on failure.
- Removal of only invocation-owned temporary backups on success.
- Accurate reporting and non-zero exit code on temporary backup cleanup failure.
- Accurate reporting of rollback errors and non-zero exit code.
- Pipeline interruption handling (KeyboardInterrupt / Exception).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import scripts.refresh_weekly as rw


class TestBackupAndRestore:
    """Verifies that backup_datasets, restore_backups, and remove_backups correctly manage dataset state."""

    def test_backup_and_restore_recovers_original_content(self, tmp_path: Path):
        file1 = tmp_path / "summary.json"
        file1.write_text("original summary", encoding="utf-8")
        file2 = tmp_path / "raw.json"  # Does not exist initially

        existing_backups, non_existent_before = rw.backup_datasets([file1, file2])

        assert file1 in existing_backups
        assert existing_backups[file1].exists()
        assert existing_backups[file1].read_text(encoding="utf-8") == "original summary"
        assert file2 in non_existent_before

        # Simulate pipeline modifying file1 and creating file2
        file1.write_text("corrupted summary", encoding="utf-8")
        file2.write_text("partial raw data", encoding="utf-8")

        # Rollback
        errors = rw.restore_backups(existing_backups, non_existent_before)
        assert errors == []

        assert file1.read_text(encoding="utf-8") == "original summary"
        assert not file2.exists()
        # Since all rollback operations succeeded, temporary backup was removed
        assert not existing_backups[file1].exists()

    def test_remove_backups_cleans_up_bak_files(self, tmp_path: Path):
        file1 = tmp_path / "summary.json"
        file1.write_text("original summary", encoding="utf-8")

        existing_backups, _ = rw.backup_datasets([file1])
        assert existing_backups[file1].exists()

        errors = rw.remove_backups(existing_backups)
        assert errors == []
        assert not existing_backups[file1].exists()
        assert file1.exists()

    def test_pre_existing_bak_file_is_not_overwritten_or_deleted(self, tmp_path: Path):
        file1 = tmp_path / "summary.json"
        file1.write_text("new content", encoding="utf-8")
        file1_bak = tmp_path / "summary.json.bak"
        file1_bak.write_text("pre-existing precious backup", encoding="utf-8")

        with pytest.raises(FileExistsError) as exc_info:
            rw.backup_datasets([file1])

        assert "Pre-existing backup found" in str(exc_info.value)
        # Pre-existing backup must not be overwritten or deleted
        assert file1_bak.exists()
        assert file1_bak.read_text(encoding="utf-8") == "pre-existing precious backup"
        assert file1.read_text(encoding="utf-8") == "new content"

    def test_backup_creation_failing_partway_cleans_up_only_new_backups(self, tmp_path: Path):
        file1 = tmp_path / "summary.json"
        file1.write_text("file1 original", encoding="utf-8")
        file2 = tmp_path / "metadata.json"
        file2.write_text("file2 original", encoding="utf-8")
        file2_bak = tmp_path / "metadata.json.bak"
        file2_bak.write_text("pre-existing bak for file2", encoding="utf-8")

        # file1 would be backed up first, then file2 encounters pre-existing bak
        with pytest.raises(FileExistsError):
            rw.backup_datasets([file1, file2])

        # file1.bak was created during this invocation, so it must be cleaned up
        assert not (tmp_path / "summary.json.bak").exists()
        # file2_bak existed before, so it must NOT be deleted or overwritten
        assert file2_bak.exists()
        assert file2_bak.read_text(encoding="utf-8") == "pre-existing bak for file2"
        # Original dataset files must be completely untouched
        assert file1.read_text(encoding="utf-8") == "file1 original"
        assert file2.read_text(encoding="utf-8") == "file2 original"

    def test_backup_creation_copy_failure_after_temp_file_created_cleans_up_and_leaves_no_bak(
        self, monkeypatch, tmp_path: Path
    ):
        file1 = tmp_path / "summary.json"
        file1.write_text("original valid summary", encoding="utf-8")

        # Simulate copy2 writing partial data to temporary destination and then failing
        def failing_copy2(src, dst, *args, **kwargs):
            Path(dst).write_text("corrupted partial copy", encoding="utf-8")
            raise OSError("Simulated disk error during copy2")

        monkeypatch.setattr(shutil, "copy2", failing_copy2)

        with pytest.raises(OSError) as exc_info:
            rw.backup_datasets([file1])

        assert "Simulated disk error during copy2" in str(exc_info.value)

        # No .bak file should exist (never created or treated as recovery backup)
        assert not (tmp_path / "summary.json.bak").exists()

        # No partial .tmp files should be left behind in directory
        temp_files = list(tmp_path.glob("*.tmp"))
        assert temp_files == []

        # Original file remains completely intact
        assert file1.read_text(encoding="utf-8") == "original valid summary"

    def test_failure_restoring_one_dataset_does_not_prevent_restoring_others(
        self, monkeypatch, tmp_path: Path
    ):
        file1 = tmp_path / "summary.json"
        file1.write_text("file1 original", encoding="utf-8")
        file2 = tmp_path / "metadata.json"
        file2.write_text("file2 original", encoding="utf-8")

        existing_backups, non_existent = rw.backup_datasets([file1, file2])

        # Modify both files during run
        file1.write_text("file1 corrupted", encoding="utf-8")
        file2.write_text("file2 corrupted", encoding="utf-8")

        # Simulate permission error when restoring file1
        original_copy2 = shutil.copy2

        def failing_copy2(src, dst, *args, **kwargs):
            if Path(dst) == file1:
                raise PermissionError("Access denied restoring file1")
            return original_copy2(src, dst, *args, **kwargs)

        monkeypatch.setattr(shutil, "copy2", failing_copy2)

        errors = rw.restore_backups(existing_backups, non_existent)

        # file1 restoration failed and was recorded
        assert len(errors) == 1
        assert "Access denied restoring file1" in errors[0]
        # file2 restoration succeeded despite file1 failure
        assert file2.read_text(encoding="utf-8") == "file2 original"
        # Backups are retained when rollback is incomplete (both file1 and file2 backups kept!)
        assert existing_backups[file1].exists()
        assert existing_backups[file2].exists()

    def test_rollback_preserves_all_backups_if_one_file_fails_after_another_succeeds(
        self, monkeypatch, tmp_path: Path
    ):
        file1 = tmp_path / "first.json"
        file1.write_text("first original", encoding="utf-8")
        file2 = tmp_path / "second.json"
        file2.write_text("second original", encoding="utf-8")

        existing_backups, non_existent = rw.backup_datasets([file1, file2])

        file1.write_text("first modified", encoding="utf-8")
        file2.write_text("second modified", encoding="utf-8")

        original_copy2 = shutil.copy2

        def fail_on_second(src, dst, *args, **kwargs):
            if Path(dst) == file2:
                raise PermissionError("Failed restoring second file")
            return original_copy2(src, dst, *args, **kwargs)

        monkeypatch.setattr(shutil, "copy2", fail_on_second)

        errors = rw.restore_backups(existing_backups, non_existent)
        assert len(errors) == 1
        assert "Failed restoring second file" in errors[0]

        # First file succeeded restoration
        assert file1.read_text(encoding="utf-8") == "first original"
        # Second file failed restoration
        assert file2.read_text(encoding="utf-8") == "second modified"

        # Crucial: BOTH backups must be retained on disk for manual recovery!
        assert existing_backups[file1].exists()
        assert existing_backups[file2].exists()

    def test_rollback_preserves_all_backups_if_new_file_cleanup_fails(
        self, monkeypatch, tmp_path: Path
    ):
        file1 = tmp_path / "existing.json"
        file1.write_text("existing original", encoding="utf-8")
        file2 = tmp_path / "new_created.json"

        existing_backups, non_existent = rw.backup_datasets([file1, file2])

        file1.write_text("existing corrupted", encoding="utf-8")
        file2.write_text("new content", encoding="utf-8")

        # Mock unlink of file2 to fail
        def failing_unlink(self_path, *args, **kwargs):
            if self_path == file2:
                raise PermissionError("Cannot delete new file")
            Path.unlink(self_path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", failing_unlink)

        errors = rw.restore_backups(existing_backups, non_existent)
        assert len(errors) == 1
        assert "Failed to remove newly created file" in errors[0]
        # file1 was restored
        assert file1.read_text(encoding="utf-8") == "existing original"
        # file1.bak must still be preserved because rollback was incomplete
        assert existing_backups[file1].exists()

    def test_dataset_absent_before_run_is_removed_if_created_during_failed_run(
        self, tmp_path: Path
    ):
        file1 = tmp_path / "summary.json"
        file1.write_text("file1 original", encoding="utf-8")
        file2 = tmp_path / "new_dataset.json"  # Did not exist before run

        existing_backups, non_existent = rw.backup_datasets([file1, file2])
        assert file2 in non_existent

        # Simulate failed run that creates file2 and corrupts file1
        file1.write_text("file1 corrupted", encoding="utf-8")
        file2.write_text("file2 newly created", encoding="utf-8")

        errors = rw.restore_backups(existing_backups, non_existent)
        assert errors == []
        assert file1.read_text(encoding="utf-8") == "file1 original"
        assert not file2.exists()


class TestRunPipeline:
    """Verifies sequential step execution, safety checks, abort on failure, and return codes."""

    def test_successful_pipeline_runs_all_steps_and_returns_zero(
        self, monkeypatch, tmp_path: Path
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("baseline", encoding="utf-8")

        executed_cmds = []

        def mock_subprocess_run(cmd, cwd=None):
            executed_cmds.append(cmd)
            res = MagicMock()
            res.returncode = 0
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 0
        assert len(executed_cmds) == 4
        assert not (tmp_path / "summary.json.bak").exists()
        assert mock_file.read_text(encoding="utf-8") == "baseline"

    def test_successful_run_removes_only_its_own_temporary_backups(
        self, monkeypatch, tmp_path: Path
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("baseline", encoding="utf-8")
        unrelated_bak = tmp_path / "other_project.bak"
        unrelated_bak.write_text("unrelated backup content", encoding="utf-8")

        def mock_subprocess_run(cmd, cwd=None):
            res = MagicMock()
            res.returncode = 0
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 0
        # Pipeline backup was removed
        assert not (tmp_path / "summary.json.bak").exists()
        # Unrelated backup remains intact
        assert unrelated_bak.exists()
        assert unrelated_bak.read_text(encoding="utf-8") == "unrelated backup content"

    def test_successful_pipeline_returns_nonzero_and_reports_cleanup_failure(
        self, monkeypatch, tmp_path: Path, capsys
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("baseline", encoding="utf-8")

        def mock_subprocess_run(cmd, cwd=None):
            res = MagicMock()
            res.returncode = 0
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        monkeypatch.setattr(
            rw, "remove_backups", lambda backups: ["Permission denied deleting summary.json.bak"]
        )

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 1

        captured = capsys.readouterr().out
        assert "Pipeline steps passed, but temporary backup cleanup was incomplete" in captured
        assert "Permission denied deleting summary.json.bak" in captured
        assert "Weekly refresh completed successfully!" not in captured

    def test_backup_creation_failure_does_not_start_pipeline(
        self, monkeypatch, tmp_path: Path
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("baseline", encoding="utf-8")
        pre_existing_bak = tmp_path / "summary.json.bak"
        pre_existing_bak.write_text("prior backup", encoding="utf-8")

        executed_cmds = []

        def mock_subprocess_run(cmd, cwd=None):
            executed_cmds.append(cmd)
            res = MagicMock()
            res.returncode = 0
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 1
        # Crucial: pipeline was NEVER started
        assert len(executed_cmds) == 0
        # Pre-existing backup was not touched
        assert pre_existing_bak.read_text(encoding="utf-8") == "prior backup"
        assert mock_file.read_text(encoding="utf-8") == "baseline"

    def test_pipeline_aborts_immediately_on_step1_failure_and_restores(
        self, monkeypatch, tmp_path: Path
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("original", encoding="utf-8")

        executed_cmds = []

        def mock_subprocess_run(cmd, cwd=None):
            executed_cmds.append(cmd)
            mock_file.write_text("corrupted", encoding="utf-8")
            res = MagicMock()
            res.returncode = 2
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 2
        assert len(executed_cmds) == 1
        assert mock_file.read_text(encoding="utf-8") == "original"
        assert not (tmp_path / "summary.json.bak").exists()

    def test_pipeline_aborts_on_pytest_failure_and_restores(
        self, monkeypatch, tmp_path: Path
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("original", encoding="utf-8")

        executed_cmds = []

        def mock_subprocess_run(cmd, cwd=None):
            executed_cmds.append(cmd)
            res = MagicMock()
            res.returncode = 0 if len(executed_cmds) < 4 else 1
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 1
        assert len(executed_cmds) == 4
        assert mock_file.read_text(encoding="utf-8") == "original"
        assert not (tmp_path / "summary.json.bak").exists()

    def test_failed_rollback_is_reported_accurately_and_produces_non_zero_exit_code(
        self, monkeypatch, tmp_path: Path, capsys
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("original", encoding="utf-8")

        def mock_subprocess_run(cmd, cwd=None):
            res = MagicMock()
            res.returncode = 3
            return res

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        # Mock restore_backups to simulate a failure
        monkeypatch.setattr(
            rw, "restore_backups", lambda backups, non_existent: ["Disk write failure on restore"]
        )

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 3

        captured = capsys.readouterr().out
        assert "Rollback incomplete" in captured
        assert "Disk write failure on restore" in captured
        assert "Rollback complete" not in captured
        assert "Recovery backups have been preserved" in captured

    def test_pipeline_catches_keyboard_interrupt_and_restores(
        self, monkeypatch, tmp_path: Path, capsys
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("original", encoding="utf-8")

        def mock_subprocess_run(cmd, cwd=None):
            mock_file.write_text("corrupted", encoding="utf-8")
            raise KeyboardInterrupt()

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 1
        assert mock_file.read_text(encoding="utf-8") == "original"
        assert not (tmp_path / "summary.json.bak").exists()

        captured = capsys.readouterr().out
        assert "Pipeline interrupted by user" in captured
        assert "Rollback complete" in captured

    def test_pipeline_catches_exception_and_restores(
        self, monkeypatch, tmp_path: Path, capsys
    ):
        mock_file = tmp_path / "summary.json"
        mock_file.write_text("original", encoding="utf-8")

        def mock_subprocess_run(cmd, cwd=None):
            mock_file.write_text("corrupted", encoding="utf-8")
            raise RuntimeError("Unexpected OS crash")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        exit_code = rw.run_pipeline(datasets=[mock_file])
        assert exit_code == 1
        assert mock_file.read_text(encoding="utf-8") == "original"
        assert not (tmp_path / "summary.json.bak").exists()

        captured = capsys.readouterr().out
        assert "Unexpected OS crash" in captured
        assert "Rollback complete" in captured
