"""Unit tests for installer module and CLI commands."""

from pathlib import Path
from typer.testing import CliRunner
from ag_init.cli import app
from ag_init.installer import (
    build_install_command,
    build_uninstall_command,
    detect_available_backends,
    install_ag_init,
    resolve_install_source,
    uninstall_ag_init,
    verify_cli_path,
)

runner = CliRunner()


def test_detect_available_backends(monkeypatch):
    monkeypatch.setattr(
        "shutil.which",
        lambda cmd: "/bin/" + cmd if cmd in ("uv", "pip") else None,
    )
    backends = detect_available_backends()
    assert backends == ["uv", "pip"]


def test_resolve_install_source_local(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "ag-init"\nversion = "0.1.0"\n', encoding="utf-8")

    src, is_local = resolve_install_source(tmp_path)
    assert is_local is True
    assert src == str(tmp_path.resolve())


def test_resolve_install_source_remote(tmp_path: Path):
    src, is_local = resolve_install_source(tmp_path)
    assert is_local is False
    assert src == "ag-init"


def test_build_install_command_uv():
    cmd = build_install_command(backend="uv", source="ag-init", editable=False, upgrade=True)
    assert cmd == ["uv", "tool", "install", "--force", "ag-init"]

    cmd_edit = build_install_command(backend="uv", source="/path/to/src", editable=True, upgrade=True)
    assert cmd_edit == ["uv", "tool", "install", "--editable", "--force", "/path/to/src"]


def test_build_install_command_pipx():
    cmd = build_install_command(backend="pipx", source="ag-init", editable=False, upgrade=True)
    assert cmd == ["pipx", "install", "--force", "ag-init"]


def test_build_install_command_pip():
    cmd = build_install_command(backend="pip", source="ag-init", editable=False, upgrade=True)
    assert cmd == ["pip", "install", "--user", "--upgrade", "ag-init"]


def test_build_uninstall_command():
    assert build_uninstall_command("uv") == ["uv", "tool", "uninstall", "ag-init"]
    assert build_uninstall_command("pipx") == ["pipx", "uninstall", "ag-init"]
    assert build_uninstall_command("pip") == ["pip", "uninstall", "-y", "ag-init"]


def test_verify_cli_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/local/bin/ag-init" if cmd == "ag-init" else None)
    found, guidance = verify_cli_path()
    assert found is True
    assert guidance is None

    monkeypatch.setattr("shutil.which", lambda cmd: None)
    found, guidance = verify_cli_path()
    assert found is False
    assert guidance is not None
    assert "not on your PATH" in guidance


def test_install_ag_init_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/bin/" + cmd if cmd == "uv" else None)
    res = install_ag_init(source_path=tmp_path, dry_run=True)
    assert res.success is True
    assert res.backend_used == "uv"
    assert "uv tool install" in " ".join(res.command_executed)


def test_install_ag_init_execution_mocked(tmp_path: Path, mocker):
    mocker.patch("ag_init.installer.detect_available_backends", return_value=["uv"])
    mocker.patch("ag_init.installer.run_command", return_value=(0, "Installed ag-init v0.1.0", ""))
    mocker.patch("ag_init.installer.verify_cli_path", return_value=(True, None))

    res = install_ag_init(source_path=tmp_path)
    assert res.success is True
    assert res.is_on_path is True
    assert "Installed ag-init" in res.output


def test_cli_install_command_dry_run():
    result = runner.invoke(app, ["install", "--dry-run"])
    assert result.exit_code == 0
    assert "ag-init Package Installer" in result.stdout
    assert "DRY RUN" in result.stdout
    assert "Command:" in result.stdout


def test_resolve_install_source_git():
    src1, is_local1 = resolve_install_source(git_url="https://github.com/my-org/ag-init.git")
    assert is_local1 is False
    assert src1 == "git+https://github.com/my-org/ag-init.git"

    src2, is_local2 = resolve_install_source(target_path="git+ssh://git@github.com/my-org/ag-init.git")
    assert is_local2 is False
    assert src2 == "git+ssh://git@github.com/my-org/ag-init.git"


def test_cli_install_command_git_dry_run():
    result = runner.invoke(app, ["install", "--git", "https://github.com/org/repo.git", "--dry-run"])
    assert result.exit_code == 0
    assert "git+https://github.com/org/repo.git" in result.stdout


def test_cli_uninstall_command_dry_run():
    result = runner.invoke(app, ["uninstall", "--dry-run"])
    assert result.exit_code == 0
    assert "Uninstalling ag-init" in result.stdout
    assert "Command:" in result.stdout
