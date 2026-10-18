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

Or target a specific directory:

```bash
uvx ag-init --path ./my-new-project
```

## Global Installation

Install `ag-init` permanently as a global CLI tool:

```bash
# Automatically installs via uv tool (or pipx/pip)
ag-init install

# Install in editable mode from local checkout
ag-init install --editable

# Specify a preferred backend
ag-init install --backend pipx

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
