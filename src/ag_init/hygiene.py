"""Workspace hygiene: .gitignore management, directory setup, and git sanity."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Tuple
from ag_init.runner import run_command


def cleanup_backup_directories(target_dir: Path, dry_run: bool = False) -> List[str]:
    """Remove .ag-init-backups and .ag-kit-backups folders after installation."""
    backup_dirs = [".ag-init-backups", ".ag-kit-backups"]
    removed: List[str] = []
    for b_name in backup_dirs:
        b_path = target_dir / b_name
        if b_path.exists() and b_path.is_dir():
            if not dry_run:
                shutil.rmtree(b_path, ignore_errors=True)
            removed.append(b_name)
    return removed


def setup_gitignore(target_dir: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
    """Ensure backup directories are ignored and .agents/ is NOT ignored in .gitignore."""
    gitignore_path = target_dir / ".gitignore"
    required_entries = [".ag-init-backups/", ".ag-kit-backups/"]
    added_entries: List[str] = []

    existing_lines: List[str] = []
    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()

    # Filter out .agents/ or .agents if present
    cleaned_lines: List[str] = []
    removed_any = False
    for line in existing_lines:
        if line.strip() in (".agents", ".agents/"):
            removed_any = True
            continue
        cleaned_lines.append(line)

    # Normalize lines for comparison
    normalized_existing = {
        line.strip().rstrip("/")
        for line in cleaned_lines
        if line.strip() and not line.strip().startswith("#")
    }

    for entry in required_entries:
        key = entry.rstrip("/")
        if key not in normalized_existing:
            added_entries.append(entry)

    modified = removed_any or bool(added_entries)

    if modified and not dry_run:
        final_lines = list(cleaned_lines)
        if added_entries:
            if final_lines and final_lines[-1].strip():
                final_lines.append("")
            final_lines.append("# Antigravity Backups")
            final_lines.extend(added_entries)

        content = "\n".join(final_lines).rstrip() + "\n"
        gitignore_path.write_text(content, encoding="utf-8")

    return modified, added_entries


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
