"""Unit tests for runner module."""

import subprocess
from pathlib import Path
from ag_init.runner import (
    check_prerequisites,
    run_ag_kit,
    run_antislop,
    run_command,
)


def test_check_prerequisites_all_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    prereqs = check_prerequisites()
    assert prereqs.node_available is True
    assert prereqs.npx_available is True
    assert prereqs.git_available is True
    assert prereqs.ag_kit_global is True
    assert len(prereqs.warnings) == 0


def test_check_prerequisites_missing_node(monkeypatch):
    def fake_which(cmd):
        if cmd in ("node", "npx"):
            return None
        return f"/usr/bin/{cmd}"

    monkeypatch.setattr("shutil.which", fake_which)
    prereqs = check_prerequisites()
    assert prereqs.node_available is False
    assert prereqs.npx_available is False
    assert len(prereqs.warnings) == 1
    assert "Node.js and/or npx not found" in prereqs.warnings[0]


def test_run_antislop_success(tmp_path: Path, mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=["npx", "--yes", "antislop-ai"],
        returncode=0,
        stdout="Initialized antislop",
        stderr="",
    )

    success, msg = run_antislop(tmp_path)
    assert success is True
    assert "Initialized antislop" in msg


def test_run_antislop_failure(tmp_path: Path, mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=["npx", "--yes", "antislop-ai"],
        returncode=1,
        stdout="",
        stderr="NPM Registry Error",
    )

    success, msg = run_antislop(tmp_path)
    assert success is False
    assert "NPM Registry Error" in msg


def test_run_ag_kit_global(tmp_path: Path, mocker):
    mocker.patch("shutil.which", return_value="/usr/local/bin/ag-kit")
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="ag-kit installed",
        stderr="",
    )

    success, msg = run_ag_kit(tmp_path, force=True)
    assert success is True
    assert mock_run.call_args[0][0][0] == "ag-kit"


def test_run_ag_kit_fallback_npx(tmp_path: Path, mocker):
    mocker.patch("shutil.which", return_value=None)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="npx ag-kit installed",
        stderr="",
    )

    success, msg = run_ag_kit(tmp_path, force=True)
    assert success is True
    assert mock_run.call_args[0][0][0] == "npx"
    assert mock_run.call_args[0][0][2] == "@vudovn/ag-kit"


def test_run_command_timeout(tmp_path: Path, mocker):
    def timeout_func(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["sleep"], timeout=1)

    mocker.patch("subprocess.run", side_effect=timeout_func)
    ret, stdout, stderr = run_command(["sleep"], cwd=tmp_path, timeout=1)
    assert ret == -1
    assert "timed out after 1 seconds" in stderr
