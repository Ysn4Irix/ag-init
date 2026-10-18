"""Rule parsing, discovery, and idempotent merging into AGENTS.md."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class Rule:
    """Represents a workspace rule template."""
    id: str
    name: str
    category: str = "general"
    default: bool = True
    description: str = ""
    content: str = ""
    source: str = "builtin"


@dataclass
class MergeResult:
    """Summary of operations performed on AGENTS.md."""
    rules_added: List[str] = field(default_factory=list)
    rules_updated: List[str] = field(default_factory=list)
    backup_path: Optional[Path] = None
    target_path: Optional[Path] = None


class RuleRegistry:
    """Discovers rules across built-in, global user config, and custom paths."""

    def __init__(self, custom_rules_dir: Optional[Path] = None):
        self.custom_rules_dir = custom_rules_dir
        self.rules: Dict[str, Rule] = {}
        self.reload()

    def reload(self) -> None:
        """Scan all tiers and reload the registry."""
        self.rules.clear()
        # 1. Built-in package rules
        builtin_dir = Path(__file__).parent / "templates" / "rules"
        if builtin_dir.is_dir():
            self._scan_directory(builtin_dir, source="builtin")

        # 2. Global user rules (~/.config/ag-init/rules or %APPDATA%/ag-init/rules)
        global_dir = self.get_global_config_dir() / "rules"
        if global_dir.is_dir():
            self._scan_directory(global_dir, source="global")

        # 3. Custom rules dir from CLI
        if self.custom_rules_dir and self.custom_rules_dir.is_dir():
            self._scan_directory(self.custom_rules_dir, source="custom")

    @staticmethod
    def get_global_config_dir() -> Path:
        """Return cross-platform configuration directory."""
        if os.name == "nt":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "ag-init"
        return Path.home() / ".config" / "ag-init"

    def _scan_directory(self, directory: Path, source: str) -> None:
        for file in sorted(directory.glob("*.md")):
            try:
                rule = self.load_rule_from_file(file, default_source=source)
                self.rules[rule.id] = rule
            except Exception:
                # Skip unparseable files without crashing
                continue

    @staticmethod
    def load_rule_from_file(file_path: Path, default_source: str = "custom") -> Rule:
        """Parse a markdown file with optional YAML frontmatter into a Rule."""
        text = file_path.read_text(encoding="utf-8")
        stem_id = file_path.stem.replace("_", "-")

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                raw_meta = parts[1].strip()
                content = parts[2].strip()
                meta = yaml.safe_load(raw_meta) or {}
                return Rule(
                    id=str(meta.get("id", stem_id)),
                    name=str(meta.get("name", stem_id.title())),
                    category=str(meta.get("category", "general")),
                    default=bool(meta.get("default", True)),
                    description=str(meta.get("description", "")),
                    content=content,
                    source=default_source,
                )

        # Fallback if no frontmatter
        return Rule(
            id=stem_id,
            name=stem_id.title(),
            category="custom",
            default=True,
            description="",
            content=text.strip(),
            source=default_source,
        )

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        return self.rules.get(rule_id)

    def list_rules(self) -> List[Rule]:
        return sorted(self.rules.values(), key=lambda r: (r.category, r.id))


def get_rule_delimiters(rule_id: str) -> tuple[str, str]:
    """Return start and end delimiter tags for a given rule ID."""
    return f"<!-- ag-init:rule:{rule_id}:start -->", f"<!-- ag-init:rule:{rule_id}:end -->"


def merge_rules_into_agents_md(
    agents_md_path: Path,
    rules: List[Rule],
    context: Optional[Dict[str, Any]] = None,
    create_backup: bool = True,
    dry_run: bool = False,
) -> MergeResult:
    """Merge rules into AGENTS.md idempotently using scoped delimiters."""
    context = context or {}
    result = MergeResult(target_path=agents_md_path)

    existing_content = ""
    if agents_md_path.exists():
        existing_content = agents_md_path.read_text(encoding="utf-8")
        if create_backup and not dry_run and existing_content.strip():
            backup_dir = agents_md_path.parent / ".ag-init-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"AGENTS_{timestamp}.md.bak"
            shutil.copy2(agents_md_path, backup_file)
            result.backup_path = backup_file

    working_content = existing_content

    # Legacy migration patterns for untagged standard rules
    legacy_replacements = [
        (
            "language",
            re.compile(r"(?:\r?\n)?INPUT_LANGUAGE is [^\r\n]+\r?\nOUTPUT_LANGUAGE is [^\r\n]+", re.MULTILINE),
        ),
        (
            "no-badges",
            re.compile(r"(?:\r?\n)?## UI Rule: Prohibit Decorative Badges and Pills.*?(?=\r?\n## |\Z)", re.DOTALL),
        ),
        (
            "github-cicd",
            re.compile(r"(?:\r?\n)?## GitHub CI/CD & Releases.*?(?=\r?\n## |\Z)", re.DOTALL),
        ),
    ]

    for rule in rules:
        start_tag, end_tag = get_rule_delimiters(rule.id)
        # Render placeholders like {language_in}, {language_out}
        try:
            rendered_body = rule.content.format(**context).strip()
        except KeyError:
            rendered_body = rule.content.strip()

        tagged_block = f"{start_tag}\n{rendered_body}\n{end_tag}"

        tagged_regex = re.compile(
            rf"{re.escape(start_tag)}.*?{re.escape(end_tag)}",
            re.DOTALL,
        )

        if tagged_regex.search(working_content):
            # Already tagged: replace in place
            working_content = tagged_regex.sub(tagged_block, working_content)
            result.rules_updated.append(rule.id)
        else:
            # Check for legacy un-tagged block to replace smoothly
            replaced_legacy = False
            for legacy_id, legacy_rx in legacy_replacements:
                if legacy_id == rule.id and legacy_rx.search(working_content):
                    working_content = legacy_rx.sub(f"\n\n{tagged_block}", working_content, count=1)
                    result.rules_updated.append(rule.id)
                    replaced_legacy = True
                    break

            if not replaced_legacy:
                # Append cleanly to the end
                if working_content.strip():
                    working_content = working_content.rstrip() + f"\n\n{tagged_block}\n"
                else:
                    working_content = f"{tagged_block}\n"
                result.rules_added.append(rule.id)

    if not dry_run:
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
        agents_md_path.write_text(working_content.strip() + "\n", encoding="utf-8")

    return result
