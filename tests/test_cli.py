"""Unit and integration tests for CLI."""

from pathlib import Path
from typer.testing import CliRunner
from ag_init.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ag-init version" in result.stdout


import re


def test_cli_help():
    result = runner.invoke(app, ["--help"], color=False)
    assert result.exit_code == 0
    clean_stdout = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result.stdout)
    assert "Automated workspace initializer" in clean_stdout
    assert "language-in" in clean_stdout
    assert "badges" in clean_stdout


def test_cli_rules_list():
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0
    assert "Available Workspace Rules" in result.stdout
    assert "engineering-standards" in result.stdout
    assert "language" in result.stdout
    assert "github-cicd" in result.stdout


def test_cli_dry_run(tmp_path: Path):
    target = tmp_path / "scratch_project"
    result = runner.invoke(app, ["--path", str(target), "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.stdout
    assert not target.exists()


def test_cli_init_full(tmp_path: Path, mocker):
    mocker.patch("ag_init.cli.run_antislop", return_value=(True, "OK"))
    mocker.patch("ag_init.cli.run_ag_kit", return_value=(True, "OK"))
    mocker.patch(
        "ag_init.cli.check_prerequisites",
        return_value=mocker.Mock(
            node_available=True,
            npx_available=True,
            git_available=True,
            ag_kit_global=True,
            warnings=[],
        ),
    )

    target = tmp_path / "full_project"
    result = runner.invoke(
        app,
        [
            "--path",
            str(target),
            "--language-in",
            "english",
            "--language-out",
            "english",
            "--git-init",
        ],
    )

    assert result.exit_code == 0
    assert "Project workspace initialization complete!" in result.stdout

    # Verify AGENTS.md was created
    agents_md = target / "AGENTS.md"
    assert agents_md.exists()
    content = agents_md.read_text(encoding="utf-8")
    assert "<!-- ag-init:rule:language:start -->" in content
    assert "<!-- ag-init:rule:engineering-standards:start -->" in content
    assert "<!-- ag-init:rule:github-cicd:start -->" in content

    # Verify .gitignore
    gitignore = target / ".gitignore"
    assert gitignore.exists()
    git_content = gitignore.read_text(encoding="utf-8")
    assert ".agents/" in git_content

    # Verify docs
    docs_dir = target / "docs"
    assert docs_dir.is_dir()


def test_cli_rules_add_and_sync(tmp_path: Path):
    target = tmp_path / "sync_project"
    target.mkdir()

    # Add single rule
    res_add = runner.invoke(app, ["rules", "add", "language", "--path", str(target)])
    assert res_add.exit_code == 0
    assert "Added rule 'language'" in res_add.stdout

    agents_md = target / "AGENTS.md"
    assert agents_md.exists()
    assert "<!-- ag-init:rule:language:start -->" in agents_md.read_text(encoding="utf-8")

    # Sync rules
    res_sync = runner.invoke(app, ["rules", "sync", "--path", str(target)])
    assert res_sync.exit_code == 0
    assert "Synced 1 rule(s)" in res_sync.stdout


def test_rich_unicode_compatibility():
    """Verify rich doesn't crash with ModuleNotFoundError for Unicode 17.0.0 on Python 3.14+."""
    import os
    import rich._unicode_data
    from rich.console import Console
    from ag_init._compat import patch_rich_unicode

    patch_rich_unicode()
    assert "UNICODE_VERSION" in os.environ

    # Directly test loading an unsupported Unicode version triggers safe fallback
    loaded = rich._unicode_data.load("17.0.0")
    assert loaded is not None

    # Verify Console printing with unicode and symbols works without exception
    c = Console()
    c.print("Unicode symbols: ✓ • — ╔═╗ 🚀 [bold green]OK[/bold green]")


def test_cli_uninstall_dry_run():
    result = runner.invoke(app, ["uninstall", "--dry-run"])
    assert result.exit_code == 0
    assert "Uninstalling ag-init..." in result.stdout
    assert "Command:" in result.stdout


def test_cli_uninstall_mocked(mocker):
    mocker.patch(
        "ag_init.cli.uninstall_ag_init",
        return_value=(True, "Uninstalled 1 package", ["uv", "tool", "uninstall", "ag-init"]),
    )
    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 0
    assert "ag-init uninstalled successfully." in result.stdout


def test_cli_uninstall_failure_mocked(mocker):
    mocker.patch(
        "ag_init.cli.uninstall_ag_init",
        return_value=(False, "Permission denied", ["uv", "tool", "uninstall", "ag-init"]),
    )
    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 1
    assert "Uninstallation failed: Permission denied" in result.output


def test_cli_update_workspace_dry_run(tmp_path: Path):
    result = runner.invoke(app, ["update", "-p", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    assert "Antigravity Workspace Updater" in result.stdout
    assert "DRY RUN" in result.stdout
    assert "Workspace Update Summary" in result.stdout


def test_cli_update_workspace_mocked(tmp_path: Path, mocker):
    mocker.patch("ag_init.cli.run_antislop", return_value=(True, "Updated 6 skills"))
    mocker.patch("ag_init.cli.run_ag_kit_update", return_value=(True, "Updated .agents tree"))

    # Create dummy existing AGENTS.md
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("<!-- ag-init:rule:language:start -->\nOLD\n<!-- ag-init:rule:language:end -->\n", encoding="utf-8")

    result = runner.invoke(app, ["update", "-p", str(tmp_path)])
    assert result.exit_code == 0
    assert "Workspace Update Summary" in result.stdout
    assert "Project workspace update complete!" in result.stdout

    # Verify AGENTS.md was synced and default rules were added
    content = agents_md.read_text(encoding="utf-8")
    assert "<!-- ag-init:rule:language:start -->" in content
    assert "<!-- ag-init:rule:engineering-standards:start -->" in content
    assert "<!-- ag-init:rule:github-cicd:start -->" in content


def test_cli_update_self_dry_run():
    result = runner.invoke(app, ["update", "--self", "--dry-run"])
    assert result.exit_code == 0
    assert "Updating ag-init globally..." in result.stdout
    assert "Command:" in result.stdout
    assert "ag-init updated successfully." in result.stdout


def test_cli_update_self_mocked(mocker):
    mocker.patch(
        "ag_init.cli.update_ag_init",
        return_value=(True, "Upgraded ag-init to 0.1.4", ["uv", "tool", "upgrade", "ag-init"]),
    )
    result = runner.invoke(app, ["update", "--self"])
    assert result.exit_code == 0
    assert "ag-init updated successfully." in result.stdout


