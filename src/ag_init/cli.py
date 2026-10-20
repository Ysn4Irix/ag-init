"""Typer CLI application for ag-init."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ag_init import __version__
from ag_init.hygiene import (
    cleanup_backup_directories,
    initialize_git_if_requested,
    setup_docs_directory,
    setup_gitignore,
)
from ag_init.rules_merger import (
    RuleRegistry,
    get_rule_delimiters,
    merge_rules_into_agents_md,
)
from ag_init.runner import (
    check_prerequisites,
    run_ag_kit,
    run_antislop,
)
from ag_init.installer import (
    install_ag_init,
    uninstall_ag_init,
)

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(
    name="ag-init",
    help="Automated workspace initializer for Google Antigravity and Gemini CLI agents.",
    no_args_is_help=False,
)
rules_app = typer.Typer(
    name="rules",
    help="Inspect, list, and manage rules for AGENTS.md.",
)
app.add_typer(rules_app, name="rules")

console = Console(legacy_windows=False)


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]ag-init[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Target project directory",
        file_okay=False,
        dir_okay=True,
    ),
    language_in: str = typer.Option(
        "english",
        "--language-in",
        help="Input natural language directive",
    ),
    language_out: str = typer.Option(
        "english",
        "--language-out",
        help="Output natural language directive",
    ),
    badges: bool = typer.Option(
        False,
        "--badges/--no-badges",
        help="Allow or prohibit decorative badges/pills in UI (default: prohibit)",
    ),
    rules_dir: Optional[Path] = typer.Option(
        None,
        "--rules-dir",
        help="Custom directory containing markdown rule snippets",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    include_rule: Optional[List[str]] = typer.Option(
        None,
        "--include-rule",
        help="Explicitly activate a rule ID (can be specified multiple times)",
    ),
    exclude_rule: Optional[List[str]] = typer.Option(
        None,
        "--exclude-rule",
        help="Explicitly deactivate a rule ID (can be specified multiple times)",
    ),
    skip_upstream: bool = typer.Option(
        False,
        "--skip-upstream",
        help="Skip running npx antislop-ai and ag-kit init",
    ),
    git_init: bool = typer.Option(
        False,
        "--git-init",
        help="Initialize git repository if missing",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Non-interactive execution, skip confirmations",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview actions without writing files or running mutations",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Initialize a project with antislop, ag-kit, and opinionated rules."""
    if ctx.invoked_subcommand is not None:
        return

    target_dir = path.resolve()
    console.print(
        Panel(
            f"[bold cyan]Antigravity Workspace Initializer[/bold cyan] [dim]v{__version__}[/dim]\n"
            f"[dim]Target:[/dim] [yellow]{target_dir}[/yellow]"
            + (" [bold red](DRY RUN)[/bold red]" if dry_run else ""),
            border_style="cyan",
        )
    )

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prerequisite verification
    prereqs = check_prerequisites()
    for warning in prereqs.warnings:
        console.print(f"[yellow]⚠️  {warning}[/yellow]")

    # 2. Run Upstream tools (antislop-ai & ag-kit)
    if not skip_upstream:
        # Step A: antislop-ai (installed non-interactively via npm unpack or bundled templates)
        if not dry_run:
            with console.status("[bold green]Installing antislop-ai skills...[/bold green]"):
                ok, msg = run_antislop(target_dir)
            if ok:
                console.print(f"  [green][+][/green] antislop-ai: {msg}")
            else:
                console.print(f"  [yellow][!] antislop-ai: {msg.strip()}[/yellow]")
        else:
            console.print("  [dim][dry-run][/dim] Would install: [cyan]antislop-ai skills into .agents/skills/[/cyan]")

        # Step B: ag-kit init
        if not dry_run:
            if prereqs.node_available and prereqs.npx_available:
                with console.status("[bold green]Executing ag-kit init...[/bold green]"):
                    ok, msg = run_ag_kit(target_dir, force=force)
                if ok:
                    console.print(f"  [green][+][/green] ag-kit: {msg}")
                else:
                    console.print(f"  [yellow][!] ag-kit non-zero exit: {msg.strip()}[/yellow]")
            else:
                from ag_init.runner import copy_bundled_agents
                copied = copy_bundled_agents(target_dir)
                if copied > 0:
                    console.print(f"  [green][+][/green] ag-kit: .agents initialized from offline template ({copied} files)")
                else:
                    console.print("  [yellow][>] Skipping ag-kit init due to missing Node/npx environment[/yellow]")
        else:
            console.print("  [dim][dry-run][/dim] Would execute: [cyan]ag-kit init -f -q --strategy merge[/cyan]")

    # 3. Discover and Filter Rules
    registry = RuleRegistry(custom_rules_dir=rules_dir)
    all_rules = registry.list_rules()

    includes = set(include_rule or [])
    excludes = set(exclude_rule or [])

    # By default, --no-badges includes the 'no-badges' rule; --badges excludes it
    if badges:
        excludes.add("no-badges")
    else:
        includes.add("no-badges")

    active_rules = []
    for r in all_rules:
        if r.id in excludes:
            continue
        if r.id in includes or r.default:
            active_rules.append(r)

    # 4. Merge rules into AGENTS.md
    agents_md = target_dir / "AGENTS.md"
    merge_context = {
        "language_in": language_in,
        "language_out": language_out,
    }

    merge_res = merge_rules_into_agents_md(
        agents_md,
        active_rules,
        context=merge_context,
        create_backup=True,
        dry_run=dry_run,
    )

    if merge_res.rules_added:
        console.print(f"  [green][+] Added rules to AGENTS.md:[/green] {', '.join(merge_res.rules_added)}")
    if merge_res.rules_updated:
        console.print(f"  [cyan][+] Updated rules in AGENTS.md:[/cyan] {', '.join(merge_res.rules_updated)}")

    # 5. Git and Workspace Hygiene
    git_modified, added_git_entries = setup_gitignore(target_dir, dry_run=dry_run)
    if git_modified:
        console.print(f"  [green][+] Updated .gitignore:[/green] {', '.join(added_git_entries)}")

    docs_created = setup_docs_directory(target_dir, dry_run=dry_run)
    if docs_created:
        console.print("  [green][+] Created docs/ directory[/green]")

    git_init_done = initialize_git_if_requested(target_dir, git_init=git_init, dry_run=dry_run)
    if git_init_done:
        console.print("  [green][+] Initialized git repository[/green]")

    # 6. Cleanup temporary backup directories (.ag-init-backups and .ag-kit-backups)
    removed_backups = cleanup_backup_directories(target_dir, dry_run=dry_run)
    if removed_backups:
        console.print(f"  [dim][+] Cleaned up backup folders: {', '.join(removed_backups)}[/dim]")

    # 7. Completion Summary Table
    table = Table(title="Workspace Configuration Summary", border_style="dim")
    table.add_column("Component", style="bold")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row(
        "AGENTS.md",
        "Configured",
        f"{len(active_rules)} active rules ({', '.join(r.id for r in active_rules)})",
    )
    table.add_row(
        ".gitignore",
        "Protected",
        "Ignoring .agents/ and .ag-kit-backups/",
    )
    table.add_row(
        "Docs Directory",
        "Ready",
        "docs/ directory available",
    )
    if not skip_upstream:
        table.add_row(
            "Agent Tree",
            "Installed",
            ".agents/ managed via ag-kit & antislop",
        )

    console.print()
    console.print(table)
    console.print("\n[bold green]Project workspace initialization complete![/bold green]\n")


@rules_app.command("list")
def list_rules(
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Target project directory to check active status against",
    ),
    rules_dir: Optional[Path] = typer.Option(
        None,
        "--rules-dir",
        help="Custom directory containing markdown rule snippets",
    ),
):
    """List all available rules and check if active in local AGENTS.md."""
    registry = RuleRegistry(custom_rules_dir=rules_dir)
    rules = registry.list_rules()

    agents_md = (path / "AGENTS.md").resolve()
    active_in_project = set()

    if agents_md.exists():
        text = agents_md.read_text(encoding="utf-8")
        for r in rules:
            start_tag, _ = get_rule_delimiters(r.id)
            if start_tag in text:
                active_in_project.add(r.id)

    table = Table(title="Available Workspace Rules", border_style="cyan")
    table.add_column("ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Category", style="yellow")
    table.add_column("Source", style="dim")
    table.add_column("Default", justify="center")
    table.add_column("Active in AGENTS.md", justify="center")

    for r in rules:
        is_active = "[green]YES[/green]" if r.id in active_in_project else "[dim]NO[/dim]"
        is_default = "[green]YES[/green]" if r.default else "[dim]-[/dim]"
        table.add_row(r.id, r.name, r.category, r.source, is_default, is_active)

    console.print(table)


@rules_app.command("add")
def add_rule(
    rule_id: str = typer.Argument(..., help="Rule ID to add to AGENTS.md"),
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Target project directory",
    ),
    rules_dir: Optional[Path] = typer.Option(
        None,
        "--rules-dir",
        help="Custom directory containing markdown rule snippets",
    ),
):
    """Add a specific rule to AGENTS.md without full initialization."""
    registry = RuleRegistry(custom_rules_dir=rules_dir)
    rule = registry.get_rule(rule_id)
    if not rule:
        console.print(f"[bold red]Error:[/bold red] Rule '[yellow]{rule_id}[/yellow]' not found.")
        console.print("Run [cyan]ag-init rules list[/cyan] to inspect available rules.")
        raise typer.Exit(code=1)

    agents_md = (path / "AGENTS.md").resolve()
    res = merge_rules_into_agents_md(agents_md, [rule], create_backup=True)

    if res.rules_added:
        console.print(f"[green][+] Added rule '{rule_id}' to {agents_md}[/green]")
    elif res.rules_updated:
        console.print(f"[cyan][+] Updated rule '{rule_id}' in {agents_md}[/cyan]")


@rules_app.command("sync")
def sync_rules(
    path: Path = typer.Option(
        Path("."),
        "--path",
        "-p",
        help="Target project directory",
    ),
    rules_dir: Optional[Path] = typer.Option(
        None,
        "--rules-dir",
        help="Custom directory containing markdown rule snippets",
    ),
):
    """Re-sync currently installed tagged rules in AGENTS.md with latest templates."""
    agents_md = (path / "AGENTS.md").resolve()
    if not agents_md.exists():
        console.print(f"[bold red]Error:[/bold red] {agents_md} does not exist.")
        raise typer.Exit(code=1)

    registry = RuleRegistry(custom_rules_dir=rules_dir)
    text = agents_md.read_text(encoding="utf-8")

    # Find all tagged rule IDs
    tag_pattern = re.compile(r"<!-- ag-init:rule:([a-zA-Z0-9_-]+):start -->")
    installed_ids = tag_pattern.findall(text)

    if not installed_ids:
        console.print("[yellow]No tagged ag-init rules found in AGENTS.md to sync.[/yellow]")
        return

    rules_to_sync = []
    missing_ids = []
    for rid in installed_ids:
        r = registry.get_rule(rid)
        if r:
            rules_to_sync.append(r)
        else:
            missing_ids.append(rid)

    res = merge_rules_into_agents_md(agents_md, rules_to_sync, create_backup=True)
    console.print(f"[green][+] Synced {len(res.rules_updated)} rule(s) in {agents_md}[/green]")
    if missing_ids:
        console.print(f"[yellow][!] Could not find template for installed rules: {', '.join(missing_ids)}[/yellow]")


@app.command("install")
def install_cmd(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Source checkout directory (auto-detects local ag-init source if omitted)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    git: Optional[str] = typer.Option(
        None,
        "--git",
        "-g",
        help="Git repository URL to install from (e.g. https://github.com/org/ag-init.git)",
    ),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help="Tool installer backend to use: 'uv', 'pipx', or 'pip' (auto-detects highest priority)",
    ),
    editable: bool = typer.Option(
        False,
        "--editable",
        "-e",
        help="Install in editable mode (only applies when installing from local source)",
    ),
    upgrade: bool = typer.Option(
        True,
        "--upgrade/--no-upgrade",
        "-U",
        help="Force overwrite or upgrade existing installation",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview command without executing",
    ),
):
    """Install ag-init globally on your system using uv tool, pipx, or pip."""
    console.print(
        Panel(
            f"[bold cyan]ag-init Package Installer[/bold cyan] [dim]v{__version__}[/dim]\n"
            + (" [bold red](DRY RUN)[/bold red]" if dry_run else ""),
            border_style="cyan",
        )
    )

    if not dry_run:
        with console.status("[bold green]Installing ag-init globally...[/bold green]"):
            result = install_ag_init(
                source_path=path,
                git_url=git,
                backend=backend,
                editable=editable,
                upgrade=upgrade,
                dry_run=dry_run,
            )
    else:
        result = install_ag_init(
            source_path=path,
            git_url=git,
            backend=backend,
            editable=editable,
            upgrade=upgrade,
            dry_run=dry_run,
        )

    if not result.success:
        console.print(f"[bold red]Installation failed:[/bold red] {result.output}")
        raise typer.Exit(code=1)

    console.print(f"  [green][+][/green] Backend: [bold cyan]{result.backend_used}[/bold cyan]")
    console.print(f"  [green][+][/green] Command: [dim]{' '.join(result.command_executed)}[/dim]")

    if result.output and not dry_run:
        console.print(Panel(result.output, title="Output", border_style="dim"))

    if result.is_on_path:
        console.print("\n[bold green][+] ag-init is installed and ready on your PATH![/bold green]")
        console.print("You can now run [cyan]ag-init[/cyan] anywhere in your terminal.\n")
    else:
        console.print("\n[bold yellow][!] PATH Notice:[/bold yellow]")
        if result.path_guidance:
            console.print(f"[yellow]{result.path_guidance}[/yellow]\n")


@app.command("uninstall")
def uninstall_cmd(
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help="Tool installer backend to uninstall from: 'uv', 'pipx', or 'pip'",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview command without executing",
    ),
):
    """Uninstall ag-init from your system."""
    console.print(f"[bold cyan]Uninstalling ag-init...[/bold cyan]")
    success, output, cmd = uninstall_ag_init(backend=backend, dry_run=dry_run)

    if not success:
        console.print(f"[bold red]Uninstallation failed:[/bold red] {output}")
        raise typer.Exit(code=1)

    console.print(f"  [green][+][/green] Command: [dim]{' '.join(cmd)}[/dim]")
    if output and not dry_run:
        console.print(output)
    console.print("[bold green][+] ag-init uninstalled successfully.[/bold green]")
