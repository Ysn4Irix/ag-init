"""Unit tests for runner module."""

import io
import subprocess
import tarfile
from pathlib import Path
from ag_init.runner import (
    ANTISLOP_POINTER_END,
    ANTISLOP_POINTER_START,
    check_prerequisites,
    copy_bundled_skills,
    run_ag_kit,
    run_antislop,
    run_command,
    update_antislop_pointer,
)


def test_check_prerequisites_all_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")
    prereqs = check_prerequisites()
    assert prereqs.node_available is True
    assert prereqs.npx_available is True
    assert prereqs.npm_available is True
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


def test_copy_bundled_skills(tmp_path: Path):
    dest = tmp_path / "skills"
    count = copy_bundled_skills(dest)
    assert count == 6
    assert (dest / "antislop" / "SKILL.md").exists()
    assert (dest / "antislop" / "VERSION").exists()
    assert (dest / "antislop-ui" / "SKILL.md").exists()
    assert (dest / "antislop-copywriting" / "SKILL.md").exists()
    assert (dest / "antislop-human" / "SKILL.md").exists()
    assert (dest / "antislop-human" / "contrast-check.py").exists()
    assert (dest / "antislop-layoutmobile" / "SKILL.md").exists()
    assert (dest / "antislop-code" / "SKILL.md").exists()


def test_update_antislop_pointer_new_file(tmp_path: Path):
    skills_dir = tmp_path / ".agents" / "skills"
    copy_bundled_skills(skills_dir)

    agents_md = tmp_path / "AGENTS.md"
    update_antislop_pointer(agents_md, skills_dir)

    assert agents_md.exists()
    content = agents_md.read_text(encoding="utf-8")
    assert ANTISLOP_POINTER_START in content
    assert ANTISLOP_POINTER_END in content
    assert ".agents/skills/antislop/SKILL.md" in content
    assert ".agents/skills/antislop-ui/SKILL.md" in content


def test_update_antislop_pointer_existing_file(tmp_path: Path):
    skills_dir = tmp_path / ".agents" / "skills"
    copy_bundled_skills(skills_dir)

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "# Existing Project Rules\n\nSome custom notes here.\n",
        encoding="utf-8",
    )

    update_antislop_pointer(agents_md, skills_dir)
    content = agents_md.read_text(encoding="utf-8")
    assert ANTISLOP_POINTER_START in content
    assert "Some custom notes here." in content

    # Call it again to verify idempotency
    update_antislop_pointer(agents_md, skills_dir)
    content2 = agents_md.read_text(encoding="utf-8")
    assert content2.count(ANTISLOP_POINTER_START) == 1
    assert content2.count(ANTISLOP_POINTER_END) == 1


def test_run_antislop_bundled(tmp_path: Path):
    success, msg = run_antislop(tmp_path, prefer_bundled=True)
    assert success is True
    assert "bundled templates" in msg
    assert (tmp_path / ".agents" / "skills" / "antislop" / "SKILL.md").exists()
    assert (tmp_path / "AGENTS.md").exists()


def test_run_antislop_fallback_on_npm_error(tmp_path: Path, mocker):
    # Simulate npm failing
    mocker.patch("ag_init.runner.download_and_extract_npm_skills", return_value=0)

    success, msg = run_antislop(tmp_path, prefer_bundled=False)
    assert success is True
    assert "bundled templates" in msg
    assert (tmp_path / ".agents" / "skills" / "antislop" / "SKILL.md").exists()


def test_run_antislop_npm_success(tmp_path: Path, mocker):
    mocker.patch("ag_init.runner.download_and_extract_npm_skills", return_value=6)

    success, msg = run_antislop(tmp_path, prefer_bundled=False)
    assert success is True
    assert "npm (6 skills)" in msg


def test_run_antislop_total_failure(tmp_path: Path, mocker):
    mocker.patch("ag_init.runner.download_and_extract_npm_skills", return_value=0)
    mocker.patch("ag_init.runner.copy_bundled_skills", return_value=0)

    success, msg = run_antislop(tmp_path, prefer_bundled=False)
    assert success is False
    assert "Failed to install antislop skills" in msg


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


def test_copy_bundled_agents(tmp_path: Path):
    from ag_init.runner import copy_bundled_agents
    count = copy_bundled_agents(tmp_path)
    assert count > 0
    assert (tmp_path / ".agents" / "antigravity.json").exists()
    assert (tmp_path / ".agents" / "agent").is_dir()
    assert (tmp_path / ".agents" / "workflows").is_dir()


def test_run_ag_kit_fallback_to_bundled_on_error(tmp_path: Path, mocker):
    mocker.patch("shutil.which", return_value=None)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="Failed to download template github:vudovn/ag-kit",
    )

    success, msg = run_ag_kit(tmp_path, force=True)
    assert success is True
    assert "offline template" in msg
    assert (tmp_path / ".agents" / "antigravity.json").exists()


def test_run_command_timeout(tmp_path: Path, mocker):
    def timeout_func(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["sleep"], timeout=1)

    mocker.patch("subprocess.run", side_effect=timeout_func)
    ret, stdout, stderr = run_command(["sleep"], cwd=tmp_path, timeout=1)
    assert ret == -1
    assert "timed out after 1 seconds" in stderr
