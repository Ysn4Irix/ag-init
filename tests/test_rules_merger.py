"""Unit tests for RuleRegistry and rules_merger."""

from pathlib import Path
from ag_init.rules_merger import Rule, RuleRegistry, merge_rules_into_agents_md


def test_rule_registry_builtins():
    registry = RuleRegistry()
    rules = registry.list_rules()
    ids = {r.id for r in rules}
    assert "language" in ids
    assert "no-badges" in ids
    assert "github-cicd" in ids

    lang_rule = registry.get_rule("language")
    assert lang_rule is not None
    assert lang_rule.category == "general"
    assert "INPUT_LANGUAGE" in lang_rule.content


def test_custom_rule_loading(tmp_path: Path):
    custom_rule_file = tmp_path / "custom_rule.md"
    custom_rule_file.write_text(
        """---
id: custom-check
name: Custom Check
category: security
default: false
description: Custom verification rule
---
## Security Verification
Ensure all endpoints authenticate tokens.
""",
        encoding="utf-8",
    )

    registry = RuleRegistry(custom_rules_dir=tmp_path)
    rule = registry.get_rule("custom-check")
    assert rule is not None
    assert rule.name == "Custom Check"
    assert rule.category == "security"
    assert rule.default is False
    assert "Ensure all endpoints" in rule.content


def test_merge_rules_into_blank_file(tmp_path: Path):
    agents_md = tmp_path / "AGENTS.md"
    registry = RuleRegistry()
    rules = [
        registry.get_rule("language"),
        registry.get_rule("no-badges"),
    ]

    res = merge_rules_into_agents_md(
        agents_md,
        rules,
        context={"language_in": "french", "language_out": "french"},
    )

    assert len(res.rules_added) == 2
    content = agents_md.read_text(encoding="utf-8")
    assert "<!-- ag-init:rule:language:start -->" in content
    assert "INPUT_LANGUAGE is french" in content
    assert "<!-- ag-init:rule:no-badges:start -->" in content


def test_merge_rules_idempotent(tmp_path: Path):
    agents_md = tmp_path / "AGENTS.md"
    registry = RuleRegistry()
    rules = registry.list_rules()

    # First merge
    res1 = merge_rules_into_agents_md(agents_md, rules, context={"language_in": "english", "language_out": "english"})
    content1 = agents_md.read_text(encoding="utf-8")
    assert len(res1.rules_added) == len(rules)

    # Second merge
    res2 = merge_rules_into_agents_md(agents_md, rules, context={"language_in": "english", "language_out": "english"})
    content2 = agents_md.read_text(encoding="utf-8")
    assert len(res2.rules_updated) == len(rules)
    assert len(res2.rules_added) == 0
    assert content1 == content2


def test_legacy_untagged_migration(tmp_path: Path):
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        """<!-- antislop:start -->
## antislop
Antislop instructions here
<!-- antislop:end -->

INPUT_LANGUAGE is english
OUTPUT_LANGUAGE is english

## UI Rule: Prohibit Decorative Badges and Pills
Existing text here

## Custom Section
Never touch this custom developer section!
""",
        encoding="utf-8",
    )

    registry = RuleRegistry()
    rules = [registry.get_rule("language"), registry.get_rule("no-badges")]

    res = merge_rules_into_agents_md(agents_md, rules, context={"language_in": "english", "language_out": "english"})
    assert "language" in res.rules_updated
    assert "no-badges" in res.rules_updated

    content = agents_md.read_text(encoding="utf-8")
    # Verify antislop untouched
    assert "<!-- antislop:start -->" in content
    # Verify tags added
    assert "<!-- ag-init:rule:language:start -->" in content
    assert "<!-- ag-init:rule:no-badges:start -->" in content
    # Verify custom section preserved
    assert "## Custom Section" in content
    assert "Never touch this custom developer section!" in content
    # Verify backup was created
    assert res.backup_path is not None
    assert res.backup_path.exists()
