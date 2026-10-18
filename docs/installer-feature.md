# Plan: Package Installer Feature (`ag-init install`)

> Task: Implement a global self-installer feature (`ag-init install`) supporting `uv tool`, `pipx`, and `pip`, with smart source detection and PATH verification.

---

## Architecture Decisions Confirmed
- **Target**: Global CLI self-installer enabling developers to install `ag-init` permanently on their system.
- **Backend Priority**: `uv tool` (fast, modern) -> `pipx` -> `pip` (fallback), with optional `--backend` override.
- **Source Resolution**: Smart detection — installs from current local repo if inside an `ag-init` source checkout, otherwise remote package.
- **Environment & PATH**: Reinstalls/upgrades cleanly (`--force`/`--upgrade`), checks if `ag-init` is on shell `PATH`, and provides exact shell configuration instructions if missing.

---

## Tasks

- [x] **Task 1: Installer Engine (`src/ag_init/installer.py`)**
  - Implement tool backend discovery: detect `uv`, `pipx`, and `pip`.
  - Implement source resolver: check current directory or custom path for `pyproject.toml` with `name = "ag-init"`.
  - Implement `install_ag_init(source, backend, editable, upgrade, dry_run)`: executes the chosen tool installer.
  - Implement `uninstall_ag_init(backend, dry_run)`.
  - Implement `verify_cli_path()`: verifies whether `ag-init` is accessible in `PATH`, identifies missing bin paths, and returns setup advice.
  - Verification: Unit tests verifying backend selection, command generation, and PATH validation.

- [x] **Task 2: CLI Integration in `src/ag_init/cli.py`**
  - Add `ag-init install` command with options (`--editable`, `--upgrade`, `--backend`, `--path`, `--dry-run`).
  - Add `ag-init uninstall` command.
  - Rich progress spinners, summary panels, and PATH instruction formatting.
  - Verification: `ag-init install --help` and CLI test runner assertions.

- [x] **Task 3: Automated Tests (`tests/test_installer.py`)**
  - Test backend discovery priority (`uv` over `pipx` over `pip`).
  - Test source resolution for local vs remote.
  - Test command construction for all backends.
  - Test PATH verification logic on Windows and Unix.
  - Test CLI subcommands via `CliRunner`.
  - Verification: All tests pass with 100% success.

- [x] **Task 4: Documentation & Final Verification**
  - Update `README.md` and `docs/architecture-and-usage.md` with installation commands.
  - Run full test suite across the entire project.
