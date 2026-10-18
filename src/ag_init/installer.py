"""Package self-installer engine for ag-init using uv tool, pipx, or pip."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from ag_init.runner import run_command


@dataclass
class InstallResult:
    """Result of an installation attempt."""
    success: bool
    backend_used: str
    command_executed: List[str]
    output: str
    is_on_path: bool
    path_guidance: Optional[str] = None


def detect_available_backends() -> List[str]:
    """Return available tool installer backends in priority order."""
    backends = []
    if shutil.which("uv"):
        backends.append("uv")
    if shutil.which("pipx"):
        backends.append("pipx")
    if shutil.which("pip"):
        backends.append("pip")
    return backends


def resolve_install_source(
    target_path: Optional[Path | str] = None,
    git_url: Optional[str] = None,
) -> Tuple[str, bool]:
    """Determine whether to install from a local checkout, git repo, or remote package."""
    if git_url:
        normalized = git_url if git_url.startswith("git+") else f"git+{git_url}"
        return normalized, False

    if isinstance(target_path, str) and (
        target_path.startswith("http://")
        or target_path.startswith("https://")
        or target_path.startswith("git+")
        or target_path.startswith("git@")
    ):
        normalized = target_path if target_path.startswith("git+") else f"git+{target_path}"
        return normalized, False

    check_dir = (Path(target_path) if target_path else Path.cwd()).resolve()
    pyproject = check_dir / "pyproject.toml"

    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            if 'name = "ag-init"' in content:
                return str(check_dir), True
        except Exception:
            pass

    return "ag-init", False


def build_install_command(
    backend: str,
    source: str,
    editable: bool = False,
    upgrade: bool = True,
) -> List[str]:
    """Construct the command line for the selected installer backend."""
    cmd: List[str] = []

    if backend == "uv":
        cmd = ["uv", "tool", "install"]
        if editable:
            cmd.append("--editable")
        if upgrade:
            cmd.append("--force")
        cmd.append(source)

    elif backend == "pipx":
        cmd = ["pipx", "install"]
        if editable:
            cmd.append("--editable")
        if upgrade:
            cmd.append("--force")
        cmd.append(source)

    elif backend == "pip":
        cmd = ["pip", "install", "--user"]
        if editable:
            cmd.append("-e")
        if upgrade:
            cmd.append("--upgrade")
        cmd.append(source)

    else:
        raise ValueError(f"Unsupported backend: {backend}")

    return cmd


def build_uninstall_command(backend: str) -> List[str]:
    """Construct uninstall command line."""
    if backend == "uv":
        return ["uv", "tool", "uninstall", "ag-init"]
    elif backend == "pipx":
        return ["pipx", "uninstall", "ag-init"]
    elif backend == "pip":
        return ["pip", "uninstall", "-y", "ag-init"]
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def verify_cli_path() -> Tuple[bool, Optional[str]]:
    """Check if ag-init is accessible on system PATH, and return guidance if not."""
    found = shutil.which("ag-init") is not None
    if found:
        return True, None

    # Derive common tool binary directories
    is_windows = os.name == "nt"
    if is_windows:
        user_profile = os.environ.get("USERPROFILE", "")
        local_bin = Path(user_profile) / ".local" / "bin"
        guidance = (
            f"ag-init was installed, but '{local_bin}' is not on your PATH.\n"
            "To add it in PowerShell, run:\n"
            f'  $env:Path += ";{local_bin}"\n'
            'Or run: uv tool update-shell'
        )
    else:
        guidance = (
            "ag-init was installed, but '~/.local/bin' is not on your PATH.\n"
            "To add it to your shell, run:\n"
            '  export PATH="$HOME/.local/bin:$PATH"\n'
            'Or run: uv tool update-shell'
        )

    return False, guidance


def install_ag_init(
    source_path: Optional[Path | str] = None,
    git_url: Optional[str] = None,
    backend: Optional[str] = None,
    editable: bool = False,
    upgrade: bool = True,
    dry_run: bool = False,
) -> InstallResult:
    """Execute installation of ag-init."""
    available = detect_available_backends()
    if not available:
        return InstallResult(
            success=False,
            backend_used="none",
            command_executed=[],
            output="No compatible installer backend found (checked uv, pipx, pip).",
            is_on_path=False,
        )

    selected_backend = backend or available[0]
    if selected_backend not in available:
        return InstallResult(
            success=False,
            backend_used=selected_backend,
            command_executed=[],
            output=f"Selected backend '{selected_backend}' is not installed or available on PATH.",
            is_on_path=False,
        )

    source, is_local = resolve_install_source(source_path, git_url=git_url)
    # If installing a remote package or git repo, editable makes no sense
    use_editable = editable and is_local

    cmd = build_install_command(
        backend=selected_backend,
        source=source,
        editable=use_editable,
        upgrade=upgrade,
    )

    if dry_run:
        return InstallResult(
            success=True,
            backend_used=selected_backend,
            command_executed=cmd,
            output=f"[dry-run] Would execute: {' '.join(cmd)}",
            is_on_path=True,
        )

    ret_code, stdout, stderr = run_command(cmd, timeout=120)
    success = ret_code == 0
    output = stdout if success else (stderr or stdout)

    is_on_path, path_guidance = verify_cli_path()

    return InstallResult(
        success=success,
        backend_used=selected_backend,
        command_executed=cmd,
        output=output.strip(),
        is_on_path=is_on_path,
        path_guidance=path_guidance,
    )


def uninstall_ag_init(
    backend: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Execute uninstallation of ag-init."""
    available = detect_available_backends()
    if not available:
        return False, "No package manager backend found.", []

    selected_backend = backend or available[0]
    cmd = build_uninstall_command(selected_backend)

    if dry_run:
        return True, f"[dry-run] Would execute: {' '.join(cmd)}", cmd

    ret_code, stdout, stderr = run_command(cmd, timeout=60)
    success = ret_code == 0
    output = stdout if success else (stderr or stdout)
    return success, output.strip(), cmd
