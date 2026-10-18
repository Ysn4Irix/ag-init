# ag-init

Automated workspace initializer for Google Antigravity and Gemini CLI agents.

## Overview

`ag-init` orchestrates the setup of modern Antigravity agent environments:
1. **Antislop Protection**: Installs and configures anti-slop rules via `npx antislop-ai`.
2. **AG Kit Core**: Merges and installs `.agents/` agents, skills, and memory systems via `ag-kit init`.
3. **Smart Rule Assembly**: Deterministically injects and updates opinionated team rules into `AGENTS.md` using scoped tags.
4. **Workspace Hygiene**: Configures `.gitignore` (ignoring `.agents/` and `.ag-kit-backups/`) and ensures `docs/` structure.

## Quick Start (Zero-Install)

Run instantly without installing via `uvx` or `pipx`:

```bash
uvx ag-init
```

Or run directly from a Git repository:

```bash
uvx --from git+https://github.com/Ysn4Irix/ag-init.git ag-init
```

Or target a specific directory:

```bash
uvx ag-init --path ./my-new-project
```

## Zero-Dependency One-Line Install (Fresh Machine)

If **Python, uv, and pipx are NOT installed** on the system, run this single command to bootstrap everything automatically (no admin/root privileges required):

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/Ysn4Irix/ag-init/main/install.ps1 | iex"
```

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ysn4Irix/ag-init/main/install.sh | sh
```

*(This automatically installs standalone `uv`, which pulls an isolated, sandboxed Python environment on demand without touching system packages).*

## Global Installation (When uv, pipx, or Python is Available)

Install `ag-init` permanently as a global CLI tool:

```bash
# 1. Directly from a Git repository:
uv tool install git+https://github.com/Ysn4Irix/ag-init.git
# or with pipx:
pipx install git+https://github.com/Ysn4Irix/ag-init.git

# 2. Or using the built-in installer:
ag-init install
ag-init install --git https://github.com/Ysn4Irix/ag-init.git

# Install in editable mode from local checkout
ag-init install --editable

# Uninstall
ag-init uninstall
```

## Options

```bash
uvx ag-init [PATH] [OPTIONS]

Options:
  -p, --path PATH               Target directory [default: .]
  --language-in TEXT            Input language directive [default: english]
  --language-out TEXT           Output language directive [default: english]
  --badges / --no-badges        Allow or prohibit decorative badges [default: no-badges]
  --rules-dir PATH              Custom rules directory to include
  --force / -f                  Non-interactive execution, skip prompts [default: false]
  --dry-run                     Preview operations without writing files [default: false]
```

## Managing Rules

```bash
# List available and active rules
uvx ag-init rules list

# Add a specific rule to existing project
uvx ag-init rules add <rule-id>

# Re-sync installed rules with latest templates
uvx ag-init rules sync
```

## CI/CD & Release Workflow

This project adheres to strict version control and automated release standards:

- **CI Matrix**: Automated testing on every PR and push across Python 3.10–3.14 on Linux and Windows via GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
- **Versioning**: Semantic Versioning (`MAJOR.MINOR.PATCH`) with [Conventional Commits](https://www.conventionalcommits.org/).
  - `feat:` bumps **MINOR**
  - `fix:`, `docs:`, `refactor:`, `test:` bump **PATCH**
  - `BREAKING CHANGE:` bumps **MAJOR**
- **Automated Releases**: Pushing a tag `v*.*.*` automatically triggers [`.github/workflows/release.yml`](.github/workflows/release.yml), building wheels/sdist and publishing a tagged GitHub Release with changelog and build artifacts.
- **Remote Policy**: Changes are committed locally. Pushes or publishing to remotes require explicit authorization.
