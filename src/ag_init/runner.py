"""Subprocess runner and prerequisite checker for Node/npx/ag-kit and antislop."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ANTISLOP_POINTER_START = "<!-- antislop:start -->"
ANTISLOP_POINTER_END = "<!-- antislop:end -->"

SKILL_LINES: Dict[str, str] = {
    "antislop": "Core filter, always on: `antislop`",
    "antislop-ui": "UI / visual: `antislop-ui`",
    "antislop-copywriting": "Copy & text: `antislop-copywriting`",
    "antislop-human": "People: `antislop-human`",
    "antislop-layoutmobile": "Mobile / responsive: `antislop-layoutmobile`",
    "antislop-code": "Code comments: `antislop-code`",
}


@dataclass
class Prerequisites:
    """System prerequisites status."""
    node_available: bool = False
    npx_available: bool = False
    npm_available: bool = False
    git_available: bool = False
    ag_kit_global: bool = False
    warnings: List[str] = field(default_factory=list)


def check_prerequisites() -> Prerequisites:
    """Check availability of system tools."""
    prereqs = Prerequisites()

    prereqs.node_available = shutil.which("node") is not None
    prereqs.npx_available = shutil.which("npx") is not None
    prereqs.npm_available = shutil.which("npm") is not None
    prereqs.git_available = shutil.which("git") is not None
    prereqs.ag_kit_global = shutil.which("ag-kit") is not None

    if not prereqs.node_available or not prereqs.npx_available:
        prereqs.warnings.append(
            "Node.js and/or npx not found on system PATH. "
            "ag-kit initialization will be skipped (graceful degradation)."
        )

    return prereqs


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 120,
) -> Tuple[int, str, str]:
    """Execute a system command safely with output capture, UTF-8 decoding, and closed stdin."""
    exec_cwd = str(cwd) if cwd else None
    is_windows = os.name == "nt"

    # Always use UTF-8 with replace error handler and closed stdin to prevent
    # character decode crashes on Windows and prompt hangs on redirected pipes.
    try:
        process = subprocess.run(
            cmd,
            cwd=exec_cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            shell=is_windows,
            timeout=timeout,
            env=dict(os.environ, CI="true", FORCE_COLOR="0", PYTHONIOENCODING="utf-8"),
        )
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
    except Exception as exc:
        return -1, "", f"Failed to execute command: {exc}"


def get_bundled_skills_dir() -> Path:
    """Return path to bundled antislop skills directory."""
    return Path(__file__).resolve().parent / "templates" / "antislop_skills"


def generate_antislop_pointer(skills_dir: Path, base_dir: Path) -> str:
    """Generate antislop pointer block referencing skills installed in skills_dir."""
    lines = [
        ANTISLOP_POINTER_START,
        "## antislop",
        "For UI, copy, people, mobile layout, or code comments work, read these installed skill files directly (use these paths even if a same-named global skill exists):",
    ]
    for skill_name, label in SKILL_LINES.items():
        skill_file = skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            rel_path = skill_file.relative_to(base_dir).as_posix()
            lines.append(f"- {label}: `{rel_path}`")
    lines.extend([
        'Before starting, follow the core\'s "Two Usage Modes" section in strict order: explicit session instruction first, then global preference, then ask. A session instruction always wins. For a resolved mode, say `antislop active: <mode> (session override).` or `antislop active: <mode> (global preference).` once before presenting findings or making edits, using the actual mode and source. Acknowledging the user\'s request without naming the source does not replace this notice.',
        "Only an explicit choice of antislop during or after selects a session mode. A request to review, audit, or avoid file edits does not select a mode; read the global preference in that case. Another skill's mode does not select antislop's mode.",
        "If the mode is unresolved, ask during/after and end the response; wait for the answer before any UI review, planning, or concept. For read-only tasks, put the active-mode notice only at the start of the final answer, never in progress messages. For editing tasks, announce before the first edit and omit it from the final answer.",
        "To update antislop later: `npx antislop-ai --update`, or run `npx antislop-ai` and pick Overwrite them.",
        ANTISLOP_POINTER_END,
    ])
    return "\n".join(lines)


def update_antislop_pointer(agents_md_path: Path, skills_dir: Path) -> None:
    """Safely update or inject antislop pointer block into AGENTS.md."""
    base_dir = agents_md_path.parent
    block = generate_antislop_pointer(skills_dir, base_dir)

    if not agents_md_path.exists():
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
        agents_md_path.write_text(block + "\n", encoding="utf-8")
        return

    content = agents_md_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"{re.escape(ANTISLOP_POINTER_START)}.*?{re.escape(ANTISLOP_POINTER_END)}", re.DOTALL)
    if pattern.search(content):
        new_content = pattern.sub(block, content)
    else:
        new_content = block + "\n\n" + content.lstrip()

    agents_md_path.write_text(new_content, encoding="utf-8")


def extract_skills_from_tarball(tgz_path: Path, dest_skills_dir: Path) -> int:
    """Extract package/skills/* from npm tarball into dest_skills_dir."""
    installed_skills = set()
    dest_skills_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("package/skills/"):
                rel_path = member.name[len("package/skills/"):]
                if not rel_path or ".." in rel_path or rel_path.startswith("/"):
                    continue
                dest_path = dest_skills_dir / rel_path
                if member.isdir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    f = tar.extractfile(member)
                    if f:
                        with open(dest_path, "wb") as out:
                            out.write(f.read())
                        parts = rel_path.split("/")
                        if parts:
                            installed_skills.add(parts[0])
    return len(installed_skills)


def copy_bundled_skills(dest_skills_dir: Path) -> int:
    """Copy pre-packaged antislop skills from templates directory."""
    bundled_dir = get_bundled_skills_dir()
    if not bundled_dir.is_dir():
        return 0

    count = 0
    dest_skills_dir.mkdir(parents=True, exist_ok=True)
    for item in bundled_dir.iterdir():
        if item.is_dir():
            dest = dest_skills_dir / item.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
            count += 1
    return count


def download_and_extract_npm_skills(dest_skills_dir: Path, timeout: int = 15) -> int:
    """Pack antislop-ai via npm and extract skills non-interactively."""
    if shutil.which("npm") is None:
        return 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ret, stdout, stderr = run_command(
            ["npm", "pack", "antislop-ai", "--pack-destination", str(tmp_path)],
            timeout=timeout,
        )
        if ret != 0:
            return 0

        tgz_files = list(tmp_path.glob("antislop-ai-*.tgz"))
        if not tgz_files:
            return 0

        return extract_skills_from_tarball(tgz_files[0], dest_skills_dir)


def run_antislop(
    target_dir: Path,
    timeout: int = 30,
    prefer_bundled: bool = False,
) -> Tuple[bool, str]:
    """Install antislop skills non-interactively into target_dir/.agents/skills/ and configure AGENTS.md."""
    target_skills_dir = target_dir / ".agents" / "skills"
    agents_md = target_dir / "AGENTS.md"
    count = 0
    source = ""

    if not prefer_bundled:
        try:
            count = download_and_extract_npm_skills(target_skills_dir, timeout=timeout)
            if count > 0:
                source = f"npm ({count} skills)"
        except Exception:
            count = 0

    if count == 0:
        count = copy_bundled_skills(target_skills_dir)
        if count > 0:
            source = f"bundled templates ({count} skills)"

    if count == 0:
        return False, "Failed to install antislop skills: could not unpack from npm and bundled templates missing"

    update_antislop_pointer(agents_md, target_skills_dir)
    return True, f"Installed antislop skills from {source}"


def get_bundled_agents_dir() -> Path:
    """Return path to bundled .agents template directory."""
    return Path(__file__).resolve().parent / "templates" / "agents_template"


def copy_bundled_agents(target_dir: Path) -> int:
    """Copy bundled .agents template tree into target_dir/.agents, merging files safely."""
    bundled_dir = get_bundled_agents_dir()
    if not bundled_dir.is_dir():
        return 0

    dest_agent_dir = target_dir / ".agents"
    dest_agent_dir.mkdir(parents=True, exist_ok=True)
    copied = 0

    for root, _dirs, files in os.walk(bundled_dir):
        rel_path = Path(root).relative_to(bundled_dir)
        sub_dir = dest_agent_dir / rel_path
        sub_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            dest_file = sub_dir / f
            if not dest_file.exists():
                shutil.copy2(Path(root) / f, dest_file)
                copied += 1

    return copied


def run_ag_kit(
    target_dir: Path,
    force: bool = True,
    strategy: str = "merge",
    timeout: int = 35,
) -> Tuple[bool, str]:
    """Execute `ag-kit init` with quiet flags, falling back gracefully to bundled template if offline/stuck."""
    has_global = shutil.which("ag-kit") is not None

    # Always pass --force and --quiet to prevent interactive readline prompts and ora spinners
    args = ["init", "--force", "--quiet", "-p", str(target_dir.resolve()), "--strategy", strategy]

    if has_global:
        cmd = ["ag-kit"] + args
    else:
        cmd = ["npx", "--yes", "@vudovn/ag-kit"] + args

    ret_code, stdout, stderr = run_command(cmd, cwd=target_dir, timeout=timeout)
    if ret_code == 0:
        return True, stdout.strip() or "ag-kit .agents initialized successfully"

    # Upstream failed or timed out; fall back to pre-bundled .agents template
    copied = copy_bundled_agents(target_dir)
    if copied > 0:
        reason = (stderr or stdout or "network timeout").strip()[:80]
        return True, f"ag-kit .agents initialized from offline template ({copied} files, upstream fallback: {reason})"

    return False, stderr or stdout or "ag-kit init failed with non-zero exit code"
