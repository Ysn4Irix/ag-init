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
AG_KIT_CODEX_START = "<!-- ag-kit:codex:start -->"
AG_KIT_CODEX_END = "<!-- ag-kit:codex:end -->"

_CODEX_SKIP_FILES = {
    "antigravity.json",
    "hooks.json",
    "mcp_config.json",
    "manifest.json",
    "manifest.lock.json",
}
_CODEX_SKIP_DIRS = {".ag-kit"}
_CODEX_TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml"}

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


def _upsert_marked_block(
    file_path: Path,
    start_marker: str,
    end_marker: str,
    block: str,
    append: bool = False,
) -> None:
    """Safely insert or replace a delimited block inside a Markdown file."""
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(block + "\n", encoding="utf-8")
        return

    content = file_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
    if pattern.search(content):
        new_content = pattern.sub(block, content)
    elif append:
        base = content.rstrip()
        new_content = f"{base}\n\n{block}\n" if base else f"{block}\n"
    else:
        new_content = block + "\n\n" + content.lstrip()

    file_path.write_text(new_content, encoding="utf-8")


def update_antislop_pointer(agents_md_path: Path, skills_dir: Path) -> None:
    """Safely update or inject antislop pointer block into AGENTS.md."""
    base_dir = agents_md_path.parent
    block = generate_antislop_pointer(skills_dir, base_dir)
    _upsert_marked_block(agents_md_path, ANTISLOP_POINTER_START, ANTISLOP_POINTER_END, block, append=False)


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
    skills_dir: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Install antislop skills non-interactively into skills_dir (default .agents/skills/) and configure AGENTS.md."""
    target_skills_dir = skills_dir or (target_dir / ".agents" / "skills")
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


def rewrite_codex_references(text: str) -> str:
    """Rewrite .agents/* path references to .codex/* for Codex CLI compatibility."""
    replacements = (
        (".agents/agent/", ".codex/agents/"),
        (".agents/agent", ".codex/agents"),
        (".agents/skills/", ".codex/skills/"),
        (".agents/rules/", ".codex/rules/"),
        (".agents/workflows/", ".codex/workflows/"),
        (".agents/memory/", ".codex/memory/"),
        (".agents/scripts/", ".codex/scripts/"),
        (".agents/schemas/", ".codex/schemas/"),
        (".agents/hooks/", ".codex/hooks/"),
        (".agents/", ".codex/"),
    )
    updated = text
    for old, new in replacements:
        updated = updated.replace(old, new)
    return updated


def _map_codex_relative_path(rel_path: Path) -> Optional[Path]:
    """Map a relative path inside staged .agents/ to its .codex/ destination path."""
    parts = list(rel_path.parts)
    if not parts:
        return rel_path
    if parts[0] in _CODEX_SKIP_DIRS:
        return None
    if len(parts) == 1 and parts[0] in _CODEX_SKIP_FILES:
        return None
    if parts[0] == "agent":
        parts[0] = "agents"
    return Path(*parts)


def project_agents_to_codex(
    staged_agents_dir: Path,
    target_dir: Path,
    strategy: str = "merge",
) -> int:
    """Project an ag-kit .agents/ tree into target_dir/.codex/ for Codex CLI."""
    if not staged_agents_dir.is_dir():
        return 0

    dest_codex_dir = target_dir / ".codex"
    dest_codex_dir.mkdir(parents=True, exist_ok=True)
    copied = 0

    for root, dirs, files in os.walk(staged_agents_dir):
        dirs[:] = [d for d in dirs if d not in _CODEX_SKIP_DIRS]
        rel_dir = Path(root).relative_to(staged_agents_dir)
        mapped_dir = _map_codex_relative_path(rel_dir) if rel_dir != Path(".") else Path(".")
        if mapped_dir is None:
            continue

        target_sub_dir = dest_codex_dir / mapped_dir
        target_sub_dir.mkdir(parents=True, exist_ok=True)

        for filename in files:
            src_file = Path(root) / filename
            mapped_file = _map_codex_relative_path(rel_dir / filename)
            if mapped_file is None:
                continue

            dest_file = dest_codex_dir / mapped_file
            if dest_file.exists() and strategy != "replace":
                continue

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            if src_file.suffix.lower() in _CODEX_TEXT_SUFFIXES:
                try:
                    raw_text = src_file.read_text(encoding="utf-8")
                    dest_file.write_text(rewrite_codex_references(raw_text), encoding="utf-8")
                    copied += 1
                    continue
                except UnicodeDecodeError:
                    pass

            shutil.copy2(src_file, dest_file)
            copied += 1

    return copied


def generate_codex_ag_kit_block(codex_dir: Path, base_dir: Path) -> str:
    """Generate Codex CLI guidance block pointing to .codex/ resources."""
    rel_codex = codex_dir.relative_to(base_dir).as_posix()
    lines = [
        AG_KIT_CODEX_START,
        "## ag-kit (Codex Runtime)",
        f"This workspace uses AG Kit resources projected under `{rel_codex}/` for Codex CLI:",
        f"- **Core Rules**: `{rel_codex}/rules/core-protocol.md` and `{rel_codex}/rules/universal-rules.md`",
        f"- **Specialist Agents**: `{rel_codex}/agents/`",
        f"- **Workflows**: `{rel_codex}/workflows/`",
        f"- **Skills**: `{rel_codex}/skills/` (auto-discovered by Codex CLI)",
        f"- **Project Memory**: Read `{rel_codex}/memory/MEMORY.md` at session start when present",
        AG_KIT_CODEX_END,
    ]
    return "\n".join(lines)


def update_codex_agents_md(agents_md_path: Path, codex_dir: Path) -> None:
    """Safely inject or update the ag-kit Codex guidance block in AGENTS.md."""
    block = generate_codex_ag_kit_block(codex_dir, agents_md_path.parent)
    _upsert_marked_block(agents_md_path, AG_KIT_CODEX_START, AG_KIT_CODEX_END, block, append=True)


def copy_bundled_codex(target_dir: Path, strategy: str = "merge") -> int:
    """Project bundled agents_template into target_dir/.codex/ and configure AGENTS.md."""
    bundled_dir = get_bundled_agents_dir()
    if not bundled_dir.is_dir():
        return 0
    copied = project_agents_to_codex(bundled_dir, target_dir, strategy=strategy)
    if (target_dir / ".codex").is_dir():
        update_codex_agents_md(target_dir / "AGENTS.md", target_dir / ".codex")
    return copied


def _build_ag_kit_command(action: str, project_dir: Path, strategy: str) -> List[str]:
    """Build ag-kit CLI command preferring global binary and falling back to npx."""
    args = [action, "--force", "--quiet", "--no-backup", "-p", str(project_dir.resolve()), "--strategy", strategy]
    if shutil.which("ag-kit") is not None:
        return ["ag-kit"] + args
    return ["npx", "--yes", "@vudovn/ag-kit"] + args


def _run_ag_kit_codex(
    action: str,
    target_dir: Path,
    strategy: str = "merge",
    timeout: int = 35,
) -> Tuple[bool, str]:
    """Stage upstream ag-kit in a temporary dir and project into target_dir/.codex/ + AGENTS.md."""
    verb = "initialized" if action == "init" else "updated"
    with tempfile.TemporaryDirectory() as tmp_dir:
        staging_dir = Path(tmp_dir)
        # Always stage with `init` because staging_dir has no prior .agents/ tree
        cmd = _build_ag_kit_command("init", staging_dir, strategy="replace")
        ret_code, stdout, stderr = run_command(cmd, cwd=staging_dir, timeout=timeout)

        staged_agents = staging_dir / ".agents"
        if ret_code == 0 and staged_agents.is_dir():
            copied = project_agents_to_codex(staged_agents, target_dir, strategy=strategy)
            update_codex_agents_md(target_dir / "AGENTS.md", target_dir / ".codex")
            return True, f"ag-kit .codex {verb} successfully ({copied} files)"

        copied = copy_bundled_codex(target_dir, strategy=strategy)
        if copied > 0:
            reason = (stderr or stdout or "network timeout").strip()[:80]
            return True, f"ag-kit .codex {verb} from offline template ({copied} files, upstream fallback: {reason})"

        if action == "update" and (target_dir / ".codex").is_dir():
            update_codex_agents_md(target_dir / "AGENTS.md", target_dir / ".codex")
            return True, "ag-kit .codex preserved locally"

        return False, stderr or stdout or f"ag-kit {action} failed for codex projection"


def run_ag_kit(
    target_dir: Path,
    force: bool = True,
    strategy: str = "merge",
    timeout: int = 35,
    codex: bool = False,
) -> Tuple[bool, str]:
    """Execute `ag-kit init` with quiet flags, falling back gracefully to bundled template if offline/stuck."""
    if codex:
        return _run_ag_kit_codex("init", target_dir, strategy=strategy, timeout=timeout)

    cmd = _build_ag_kit_command("init", target_dir, strategy=strategy)
    ret_code, stdout, stderr = run_command(cmd, cwd=target_dir, timeout=timeout)
    if ret_code == 0:
        return True, stdout.strip() or "ag-kit .agents initialized successfully"

    # Upstream failed or timed out; fall back to pre-bundled .agents template
    copied = copy_bundled_agents(target_dir)
    if copied > 0:
        reason = (stderr or stdout or "network timeout").strip()[:80]
        return True, f"ag-kit .agents initialized from offline template ({copied} files, upstream fallback: {reason})"

    return False, stderr or stdout or "ag-kit init failed with non-zero exit code"


def run_ag_kit_update(
    target_dir: Path,
    force: bool = True,
    strategy: str = "merge",
    timeout: int = 35,
    codex: bool = False,
) -> Tuple[bool, str]:
    """Execute `ag-kit update` with quiet flags, preserving local changes and falling back if offline."""
    if codex:
        return _run_ag_kit_codex("update", target_dir, strategy=strategy, timeout=timeout)

    cmd = _build_ag_kit_command("update", target_dir, strategy=strategy)
    ret_code, stdout, stderr = run_command(cmd, cwd=target_dir, timeout=timeout)
    if ret_code == 0:
        return True, stdout.strip() or "ag-kit .agents updated successfully"

    # Fallback to copy any missing bundled agents if upstream failed or offline
    copied = copy_bundled_agents(target_dir)
    if copied > 0:
        reason = (stderr or stdout or "network timeout").strip()[:80]
        return True, f"ag-kit .agents updated from bundled template ({copied} files, upstream fallback: {reason})"

    if (target_dir / ".agents").is_dir():
        return True, "ag-kit .agents preserved locally"

    return False, stderr or stdout or "ag-kit update failed with non-zero exit code"

