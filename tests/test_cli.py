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
    assert "no-badges" in result.stdout
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
    assert "<!-- ag-init:rule:no-badges:start -->" in content
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
