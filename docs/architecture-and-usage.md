# `ag-init` Architecture & Usage Guide

## Introduction

`ag-init` is an automated workspace orchestrator built in Python for developers configuring Google Antigravity and Gemini CLI environments.

It consolidates what was previously a multi-step manual process into a single command:
1. Running `npx antislop-ai` (anti-slop filters for AI agents)
2. Running `ag-kit init` (Antigravity agents, skills, and memory system)
3. Appending and managing opinionated team rules in `AGENTS.md` (Language directives, Badge prohibition, GitHub CI/CD policies)
4. Enforcing workspace hygiene (`.gitignore` protection and `docs/` conventions)

---

## Command Reference

### Initialization

```bash
# In current working directory
uvx ag-init

# Target a specific directory
uvx ag-init --path ./my-project

# Customize language directives
uvx ag-init --language-in spanish --language-out spanish

# Allow decorative badges (default is --no-badges)
uvx ag-init --badges

# Supply custom team rule snippets
uvx ag-init --rules-dir /path/to/custom/rules

# Dry run preview
uvx ag-init --dry-run
```

---

## Global Package Installation

`ag-init` can install itself permanently as a global CLI tool across your system:

```bash
# Auto-detects uv tool (or pipx/pip) and installs globally
ag-init install

# Install local development checkout in editable mode
ag-init install --editable

# Force a specific installer backend
ag-init install --backend pipx

# Dry run preview of installation commands
ag-init install --dry-run

# Uninstall
ag-init uninstall
```

### PATH Verification & Shell Guidance
When running `ag-init install`, the engine automatically verifies whether the binary directory is present on your active `PATH`. If missing, it provides clear setup instructions (e.g. `uv tool update-shell` or adding the user local bin directory to environment variables).

---

## Managing Future & Custom Rules

`ag-init` includes a sub-command group `rules`:

```bash
# List all discovered rules (built-in, global, custom) and check active status
uvx ag-init rules list

# Add a single rule without running full init
uvx ag-init rules add <rule-id>

# Re-sync existing rules in AGENTS.md with latest template versions
uvx ag-init rules sync
```

### Adding New Rules (Zero Code Changes)
To introduce a new rule for your machine or team, place a `.md` file in `%APPDATA%\ag-init\rules\` (Windows) or `~/.config/ag-init/rules/` (Unix):

```markdown
---
id: database-migrations
name: Database Migrations Rule
category: backend
default: true
description: Enforces explicit migration checks before touching models
---
## Database Migration Standards
Always create timestamped migrations when altering database schemas...
```

The CLI will automatically discover this rule on your next run.
