"""Unit tests for hygiene module."""

from pathlib import Path
from ag_init.hygiene import (
    cleanup_backup_directories,
    initialize_git_if_requested,
    setup_docs_directory,
    setup_gitignore,
)


def test_setup_gitignore_create(tmp_path: Path):
    modified, added = setup_gitignore(tmp_path)
    assert modified is True
    assert ".agents/" in added
    assert ".ag-init-backups/" in added

    gitignore = tmp_path / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert ".agents/" in content
    assert ".ag-init-backups/" in content


def test_setup_gitignore_already_present(tmp_path: Path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".agents/\n.ag-init-backups/\nnode_modules/\n", encoding="utf-8")

    modified, added = setup_gitignore(tmp_path)
    assert modified is False
    assert len(added) == 0


def test_setup_gitignore_partial(tmp_path: Path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".agents/\nnode_modules/\n", encoding="utf-8")

    modified, added = setup_gitignore(tmp_path)
    assert modified is True
    assert added == [".ag-init-backups/"]

    content = gitignore.read_text(encoding="utf-8")
    assert ".agents/" in content
    assert ".ag-init-backups/" in content
    assert "node_modules/" in content


def test_setup_docs_directory(tmp_path: Path):
    docs = tmp_path / "docs"
    assert not docs.exists()
    created = setup_docs_directory(tmp_path)
    assert created is True
    assert docs.is_dir()

    # Re-running shouldn't recreate
    created_again = setup_docs_directory(tmp_path)
    assert created_again is False


def test_initialize_git_if_requested(tmp_path: Path, mocker):
    mock_run = mocker.patch("ag_init.hygiene.run_command", return_value=(0, "Initialized", ""))
    initialized = initialize_git_if_requested(tmp_path, git_init=True)
    assert initialized is True
    assert mock_run.called

    # If not requested, should not run
    mock_run.reset_mock()
    assert initialize_git_if_requested(tmp_path, git_init=False) is False
    assert not mock_run.called


def test_cleanup_backup_directories(tmp_path: Path):
    init_backup = tmp_path / ".ag-init-backups"
    kit_backup = tmp_path / ".ag-kit-backups"
    init_backup.mkdir()
    kit_backup.mkdir()
    (init_backup / "dummy.txt").write_text("backup")
    (kit_backup / "dummy.txt").write_text("backup")

    # Dry run should not delete
    removed_dry = cleanup_backup_directories(tmp_path, dry_run=True)
    assert set(removed_dry) == {".ag-init-backups", ".ag-kit-backups"}
    assert init_backup.exists()
    assert kit_backup.exists()

    # Real run should delete
    removed_real = cleanup_backup_directories(tmp_path, dry_run=False)
    assert set(removed_real) == {".ag-init-backups", ".ag-kit-backups"}
    assert not init_backup.exists()
    assert not kit_backup.exists()

    # Re-running on empty should return empty list
    assert cleanup_backup_directories(tmp_path, dry_run=False) == []
