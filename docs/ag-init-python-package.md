# Plan: Antigravity Workspace Initializer (`ag-init`) Python Package

> Task: Build a zero-install Python package/CLI (`ag-init`) to automate project initialization (`npx antislop-ai`, `ag-kit init`), rule injection, and workspace hygiene.

---

## Architecture Decisions Confirmed
- **Execution Model**: Python subprocess orchestrator executing `npx antislop-ai` and `ag-kit init -f`, with graceful degradation if Node/npx is missing.
- **Rule Strategy**: 3-tier modular rule discovery (`templates/rules/*.md`, `~/.config/ag-init/rules/*.md`, CLI flags) with idempotent `<!-- ag-init:rule:<id>:start -->` delimiters.
- **Conflict Handling**: Safe non-destructive merge with automatic `.ag-init-backup` backup creation.
- **CLI/Packaging**: Zero-install CLI runnable via `uvx ag-init` / `pipx run ag-init` built with `typer` and `rich`.

---

## Tasks

- [x] **Task 1: Package Scaffolding & Dependencies**
  - Create `pyproject.toml` using standard `hatchling` build backend.
  - Configure console script entrypoint: `ag-init = "ag_init.cli:app"`.
  - Dependencies: `typer>=0.12.0`, `rich>=13.0.0`, `pyyaml>=6.0.0`.
  - Verification: `uv pip install -e .` succeeds in a local venv.

- [x] **Task 2: Rule Templates & Discovery Engine (`templates/` + `rules_merger.py`)**
  - Create built-in rule snippets under `src/ag_init/templates/rules/`:
    - `language.md` (`INPUT_LANGUAGE is english`, `OUTPUT_LANGUAGE is english`).
    - `no_badges.md` (`## UI Rule: Prohibit Decorative Badges and Pills`).
    - `github_cicd.md` (`## GitHub CI/CD & Releases`).
  - Implement rule parsing with YAML frontmatter.
  - Implement 3-tier rule discovery (built-in, global user config, `--rules-dir`).
  - Implement safe, idempotent merge into `AGENTS.md` using `<!-- ag-init:rule:<id>:start -->` delimiters.
  - Verification: Unit test verifying that merging existing `AGENTS.md` updates tagged blocks, appends missing rules, creates `.ag-init-backup`, and preserves custom untagged text.

- [x] **Task 3: Subprocess Runner & Graceful Prerequisite Checker (`runner.py`)**
  - Implement `check_prerequisites()`: detect `node`, `npx`, `git`, and `ag-kit`.
  - Implement `run_antislop(target_dir)` with non-interactive flag/timeout.
  - Implement `run_ag_kit(target_dir, force=True, strategy="merge")` (falling back to `npx @vudovn/ag-kit` if global `ag-kit` is absent).
  - Graceful degradation: if Node/npx is missing, emit warning and proceed with rule and hygiene generation.
  - Verification: Mocked unit tests verifying execution, exit code handling, and fallback behavior.

- [x] **Task 4: Git & Directory Hygiene (`hygiene.py`)**
  - Implement `.gitignore` updater: ensure `.agents/` and `.ag-kit-backups/` are ignored.
  - Ensure `docs/` directory exists.
  - Verification: Unit tests verifying `.gitignore` appending without duplicates.

- [x] **Task 5: Typer CLI Application & User Interface (`cli.py`)**
  - Main command: `ag-init [PATH]` with options (`--no-badges`, `--language-in`, `--language-out`, `--rules-dir`, `--dry-run`, `--force`).
  - Subcommands:
    - `ag-init rules list`: List available rules and their status in current project.
    - `ag-init rules add <rule_id>`: Add a specific rule to existing `AGENTS.md`.
    - `ag-init rules sync`: Re-sync existing rule blocks to latest templates.
  - Rich spinners, status tables, and colored terminal feedback.
  - Verification: CLI help displays cleanly; commands execute in dry-run mode.

- [x] **Task 6: Verification & End-to-End Testing**
  - Run `pytest` on all unit and integration tests.
  - Test end-to-end execution on a temporary scratch directory.
  - Verify complete generated `AGENTS.md`, `.gitignore`, and `.agents/` setup.
