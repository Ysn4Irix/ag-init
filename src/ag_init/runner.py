"""Subprocess runner and prerequisite checker for Node/npx/ag-kit."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Prerequisites:
    """System prerequisites status."""
    node_available: bool = False
    npx_available: bool = False
    git_available: bool = False
    ag_kit_global: bool = False
    warnings: List[str] = field(default_factory=list)


def check_prerequisites() -> Prerequisites:
    """Check availability of system tools."""
    prereqs = Prerequisites()

    prereqs.node_available = shutil.which("node") is not None
    prereqs.npx_available = shutil.which("npx") is not None
    prereqs.git_available = shutil.which("git") is not None
    prereqs.ag_kit_global = shutil.which("ag-kit") is not None

    if not prereqs.node_available or not prereqs.npx_available:
        prereqs.warnings.append(
            "Node.js and/or npx not found on system PATH. "
            "Antislop-ai and ag-kit upstream initialization will be skipped (graceful degradation)."
        )

    return prereqs


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 120,
) -> Tuple[int, str, str]:
    """Execute a system command safely with output capture."""
    exec_cwd = str(cwd) if cwd else None
    is_windows = os.name == "nt"

    # Use shell=True on Windows to correctly resolve .cmd and .ps1 script wrappers
    try:
        process = subprocess.run(
            cmd,
            cwd=exec_cwd,
            capture_output=True,
            text=True,
            shell=is_windows,
            timeout=timeout,
            env=dict(os.environ, CI="true"),
        )
        return process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
    except Exception as exc:
        return -1, "", f"Failed to execute command: {exc}"


def run_antislop(target_dir: Path, timeout: int = 90) -> Tuple[bool, str]:
    """Execute `npx --yes antislop-ai` inside target directory."""
    cmd = ["npx", "--yes", "antislop-ai"]
    ret_code, stdout, stderr = run_command(cmd, cwd=target_dir, timeout=timeout)
    if ret_code == 0:
        return True, stdout
    return False, stderr or stdout or "antislop-ai failed with non-zero exit code"


def run_ag_kit(
    target_dir: Path,
    force: bool = True,
    strategy: str = "merge",
    timeout: int = 120,
) -> Tuple[bool, str]:
    """Execute `ag-kit init` or fallback to `npx @vudovn/ag-kit init`."""
    has_global = shutil.which("ag-kit") is not None

    args = ["init"]
    if force:
        args.append("-f")
    args.extend(["-p", str(target_dir.resolve()), "--strategy", strategy])

    if has_global:
        cmd = ["ag-kit"] + args
    else:
        cmd = ["npx", "--yes", "@vudovn/ag-kit"] + args

    ret_code, stdout, stderr = run_command(cmd, cwd=target_dir, timeout=timeout)
    if ret_code == 0:
        return True, stdout
    return False, stderr or stdout or "ag-kit init failed with non-zero exit code"
