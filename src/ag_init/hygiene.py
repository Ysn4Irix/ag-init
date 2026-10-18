"""Workspace hygiene: .gitignore management, directory setup, and git sanity."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
from ag_init.runner import run_command


def setup_gitignore(target_dir: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
    """Ensure .agents/ and .ag-init-backups/ are ignored in .gitignore."""
    gitignore_path = target_dir / ".gitignore"
    required_entries = [".agents/", ".ag-init-backups/"]
    added_entries: List[str] = []

    existing_lines: List[str] = []
    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()

    # Normalize lines for comparison
    normalized_existing = {line.strip().rstrip("/") for line in existing_lines if line.strip() and not line.strip().startswith("#")}

    for entry in required_entries:
        key = entry.rstrip("/")
        if key not in normalized_existing:
            added_entries.append(entry)

    if added_entries and not dry_run:
        content_to_append = "\n# Antigravity Kit & Backups\n" + "\n".join(added_entries) + "\n"
        if existing_lines and existing_lines[-1].strip():
            content_to_append = "\n" + content_to_append

        with gitignore_path.open("a", encoding="utf-8") as f:
            f.write(content_to_append)

    return bool(added_entries), added_entries


def setup_docs_directory(target_dir: Path, dry_run: bool = False) -> bool:
    """Ensure the standard docs/ directory exists."""
    docs_dir = target_dir / "docs"
    if not docs_dir.exists():
        if not dry_run:
            docs_dir.mkdir(parents=True, exist_ok=True)
        return True
    return False


def initialize_git_if_requested(target_dir: Path, git_init: bool = False, dry_run: bool = False) -> bool:
    """Initialize a git repository if requested and not already present."""
    if not git_init:
        return False

    git_dir = target_dir / ".git"
    if not git_dir.exists():
        if not dry_run:
            run_command(["git", "init"], cwd=target_dir)
        return True
    return False
