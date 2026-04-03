#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml>=0.18.0",
#   "pydantic>=2.12.3",
#   "typer>=0.21.2",
#   "gitpython>=3.1.0",
#   "pygithub>=2.8.1",
#   "fastmcp>=3.0.2",
#   "tiktoken>=0.12.0",
#   "typing-extensions>=4.0.0",
#   "marko>=2.0.0",
# ]
# ///
"""migrate_backlog_to_yaml — bulk migration of .md backlog files to .yaml format.

Each file is loaded via load_item() (which handles .md parsing and section
extraction), verified for round-trip fidelity, then the .yaml is written and
the .md renamed to .md.bak.

Usage
-----
    # Always dry-run first to verify parsing
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --dry-run

    # Migrate after confirming dry-run is clean
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --confirm

    # Remove .md.bak files after verifying YAML is correct
    uv run plugins/development-harness/scripts/migrate_backlog_to_yaml.py --cleanup
"""

from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass, field
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Bootstrap: make the development-harness package importable within the PEP 723
# isolated environment.  The script lives at:
#   plugins/development-harness/scripts/migrate_backlog_to_yaml.py
# so parents[1] is plugins/development-harness/.
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

import typer
from backlog_core.yaml_io import load_item, load_item_text, save_item
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from ruamel.yaml import YAML, YAMLError

if TYPE_CHECKING:
    from backlog_core.models import BacklogItem

_DEFAULT_BACKLOG_DIR = Path.home() / ".dh/projects/-home-ubuntulinuxqa2-repos-claude_skills/backlog"

app = typer.Typer(
    name="migrate_backlog_to_yaml",
    help="Bulk migration of .md backlog files to pure YAML format.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------


@dataclass
class MigrationReport:
    """Aggregate results from a migration run."""

    total_found: int = 0
    """Total .md files discovered in the backlog directory."""

    migrated: int = 0
    """Files successfully migrated to .yaml."""

    skipped_no_frontmatter: int = 0
    """Files skipped because they lack YAML frontmatter (README, notes, etc.)."""

    skipped_already_converted: int = 0
    """Files skipped because a .yaml counterpart already exists."""

    skipped_bak_exists: int = 0
    """Files skipped because a .md.bak counterpart already exists (already migrated)."""

    errors: list[tuple[str, str]] = field(default_factory=list)
    """(file_path, error_message) pairs for every file that failed."""

    @property
    def error_count(self) -> int:
        """Number of migration failures."""
        return len(self.errors)

    @property
    def total_skipped(self) -> int:
        """Total files skipped for any reason."""
        return self.skipped_no_frontmatter + self.skipped_already_converted + self.skipped_bak_exists


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _has_frontmatter(text: str) -> bool:
    """Return True when text begins with a YAML frontmatter block (--- ... ---).

    Args:
        text: Raw file content.

    Returns:
        True if a frontmatter block is present.
    """
    if not text.startswith("---"):
        return False
    return "---" in text[3:]


def _item_to_yaml_str(item: BacklogItem) -> str:
    """Serialise a BacklogItem to a YAML string without touching the filesystem.

    Uses the same YAML settings as yaml_io.save_item for an accurate in-memory
    round-trip.

    Args:
        item: BacklogItem to serialise.

    Returns:
        YAML-formatted string.
    """
    data = item.model_dump(exclude={"file_path", "skip"})
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.width = 2147483647
    out = StringIO()
    yaml.dump(data, out)
    return out.getvalue()


def _dry_run_section_info(item: BacklogItem) -> tuple[int, list[str]]:
    """Return section count and section keys from a BacklogItem.

    Args:
        item: BacklogItem to inspect.

    Returns:
        Tuple of (section_count, sorted_key_list).
    """
    return len(item.sections), sorted(item.sections.keys())


# ---------------------------------------------------------------------------
# Core migration functions
# ---------------------------------------------------------------------------


def migrate_file_dry_run(md_path: Path) -> tuple[BacklogItem, bool, str]:
    """Parse and verify a single .md file without writing anything.

    Args:
        md_path: Path to the source .md file.

    Returns:
        Tuple of (item, round_trip_ok, detail_message).
        detail_message is empty on success, or describes the mismatch on failure.

    Raises:
        ValueError: When the file lacks frontmatter.
        OSError: When file I/O fails.
        ValidationError: When parsing produces an invalid model.
    """
    text = md_path.read_text(encoding="utf-8")

    if not _has_frontmatter(text):
        raise ValueError("No frontmatter — not a backlog item file")

    # Suppress DeprecationWarning — expected for .md files during migration
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        item = load_item(md_path)

    yaml_path = md_path.with_suffix(".yaml")
    yaml_str = _item_to_yaml_str(item)
    reloaded = load_item_text(yaml_str, yaml_path)

    pre_dump = item.model_dump(exclude={"file_path", "skip"})
    post_dump = reloaded.model_dump(exclude={"file_path", "skip"})

    if pre_dump == post_dump:
        return item, True, ""

    # Build a diff summary for the user
    diff_keys = [k for k in pre_dump if pre_dump.get(k) != post_dump.get(k)]
    detail = f"Mismatched fields: {diff_keys}"
    return item, False, detail


def migrate_file_live(md_path: Path) -> Path:
    """Migrate a single .md backlog file to .yaml format.

    Steps:
    1. Load the .md via load_item() — fully populated BacklogItem including sections.
    2. Write .yaml via save_item().
    3. Reload from disk via load_item() and compare model_dump().
    4. Rename .md to .md.bak on success, or remove corrupt .yaml and raise on failure.

    Args:
        md_path: Path to the source .md file.

    Returns:
        Path to the written .yaml file.

    Raises:
        ValueError: When round-trip verification detects data loss, or no frontmatter.
        OSError: When file I/O fails.
        ValidationError: When parsing or reloading produces an invalid model.
    """
    text = md_path.read_text(encoding="utf-8")
    if not _has_frontmatter(text):
        raise ValueError("No frontmatter — not a backlog item file")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        item = load_item(md_path)

    yaml_path = md_path.with_suffix(".yaml")
    save_item(item, yaml_path)

    reloaded = load_item(yaml_path)

    pre_dump = item.model_dump(exclude={"file_path", "skip"})
    post_dump = reloaded.model_dump(exclude={"file_path", "skip"})

    if pre_dump != post_dump:
        yaml_path.unlink(missing_ok=True)
        diff_keys = [k for k in pre_dump if pre_dump.get(k) != post_dump.get(k)]
        raise ValueError(
            f"Round-trip verification failed — .yaml removed, .md preserved.\n  Mismatched fields: {diff_keys}"
        )

    md_path.rename(md_path.with_suffix(".md.bak"))
    return yaml_path


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


def run_dry_run(backlog_dir: Path) -> MigrationReport:
    """Parse and verify all .md files without writing anything.

    Prints per-file section information and round-trip results.

    Args:
        backlog_dir: Directory containing .md backlog files.

    Returns:
        MigrationReport with outcomes.
    """
    report = MigrationReport()

    if not backlog_dir.exists():
        return report

    md_files = sorted(backlog_dir.glob("*.md"))
    report.total_found = len(md_files)

    for md_path in md_files:
        yaml_path = md_path.with_suffix(".yaml")
        bak_path = md_path.with_suffix(".md.bak")

        if yaml_path.exists():
            report.skipped_already_converted += 1
            continue

        if bak_path.exists():
            report.skipped_bak_exists += 1
            continue

        text = md_path.read_text(encoding="utf-8")
        if not _has_frontmatter(text):
            report.skipped_no_frontmatter += 1
            continue

        try:
            item, ok, detail = migrate_file_dry_run(md_path)
            section_count, section_keys = _dry_run_section_info(item)
            status = ":white_check_mark:" if ok else ":cross_mark:"
            rt_label = "pass" if ok else f"FAIL — {detail}"
            console.print(
                f"  {status} [cyan]{md_path.name}[/cyan] "
                f"sections={section_count} keys={section_keys} round-trip={rt_label}"
            )
            if ok:
                report.migrated += 1
            else:
                report.errors.append((str(md_path), detail))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, YAMLError, ValidationError) as exc:
            report.errors.append((str(md_path), str(exc)))
            err_console.print(f"  :cross_mark: [red]{md_path.name}[/red] — {exc}")

    return report


def run_migration(backlog_dir: Path) -> MigrationReport:
    """Migrate all .md files to .yaml in backlog_dir.

    Args:
        backlog_dir: Directory containing .md backlog files.

    Returns:
        MigrationReport with per-file outcomes.
    """
    report = MigrationReport()

    if not backlog_dir.exists():
        return report

    md_files = sorted(backlog_dir.glob("*.md"))
    report.total_found = len(md_files)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Migrating...", total=len(md_files))

        for md_path in md_files:
            progress.update(task, description=f"[cyan]{md_path.name}[/cyan]")

            yaml_path = md_path.with_suffix(".yaml")
            bak_path = md_path.with_suffix(".md.bak")

            if yaml_path.exists():
                report.skipped_already_converted += 1
                progress.advance(task)
                continue

            if bak_path.exists():
                report.skipped_bak_exists += 1
                progress.advance(task)
                continue

            text = md_path.read_text(encoding="utf-8")
            if not _has_frontmatter(text):
                report.skipped_no_frontmatter += 1
                progress.advance(task)
                continue

            try:
                migrate_file_live(md_path)
                report.migrated += 1
                console.print(f"  :white_check_mark: MIGRATED [cyan]{md_path.name}[/cyan]")
            except (OSError, ValueError, KeyError, TypeError, AttributeError, YAMLError, ValidationError) as exc:
                report.errors.append((str(md_path), str(exc)))
                console.print(f"  :cross_mark: ERROR [red]{md_path.name}[/red]")

            progress.advance(task)

    return report


def run_cleanup(backlog_dir: Path) -> int:
    """Remove all .md.bak files in backlog_dir.

    Args:
        backlog_dir: Directory to clean up.

    Returns:
        Number of .md.bak files removed.
    """
    removed = 0
    for bak_path in sorted(backlog_dir.glob("*.md.bak")):
        bak_path.unlink()
        console.print(f"  :wastebasket: Removed [dim]{bak_path.name}[/dim]")
        removed += 1
    return removed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


@app.command()
def main(
    backlog_dir: Annotated[
        Path,
        typer.Option("--backlog-dir", help="Directory containing .md backlog files to migrate.", show_default=True),
    ] = _DEFAULT_BACKLOG_DIR,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Parse and verify without writing .yaml or renaming .md files.", is_flag=True),
    ] = False,
    confirm: Annotated[
        bool, typer.Option("--confirm", help="Execute the migration (required for live runs).", is_flag=True)
    ] = False,
    cleanup: Annotated[
        bool, typer.Option("--cleanup", help="Remove .md.bak files after verifying YAML is correct.", is_flag=True)
    ] = False,
) -> None:
    """Migrate .md backlog files to pure YAML format.

    Run --dry-run first to verify parsing, then --confirm to migrate.
    Use --cleanup after verifying .yaml files are correct.
    """
    if not dry_run and not confirm and not cleanup:
        console.print(
            "\n[yellow]No action flag provided.[/yellow]\n\n"
            "  Use [bold]--dry-run[/bold] first to verify parsing and round-trip fidelity.\n"
            "  Then use [bold]--confirm[/bold] to execute the migration.\n"
            "  After verifying YAML output, use [bold]--cleanup[/bold] to remove .md.bak files.\n"
        )
        raise typer.Exit(code=0)

    if not backlog_dir.exists():
        err_console.print(f"[red]Error:[/red] Directory not found: {backlog_dir}")
        raise typer.Exit(code=1)

    if cleanup:
        console.print(f"\n:wastebasket: [bold]Cleanup:[/bold] removing .md.bak files in {backlog_dir}\n")
        removed = run_cleanup(backlog_dir)
        console.print(f"\n[green]:white_check_mark: Removed {removed} .md.bak file(s).[/green]")
        return

    if dry_run:
        console.print(
            f"\n:magnifying_glass_tilted_left: [bold]Dry run:[/bold] {backlog_dir}\n"
            "[yellow]No files will be written or renamed.[/yellow]\n"
        )
        report = run_dry_run(backlog_dir)
        _print_report(report, dry_run=True)
        if report.error_count:
            raise typer.Exit(code=1)
        return

    if confirm:
        console.print(
            f"\n:gear: [bold]Migration:[/bold] {backlog_dir}\n"
            "[green]LIVE — files will be written and originals renamed to .md.bak[/green]\n"
        )
        report = run_migration(backlog_dir)
        _print_report(report, dry_run=False)
        if report.error_count:
            raise typer.Exit(code=1)
        return


def _print_report(report: MigrationReport, *, dry_run: bool) -> None:
    """Print a Rich summary table for the migration report.

    Args:
        report: MigrationReport to display.
        dry_run: When True, labels the migrated count as verified-ok.
    """
    migrated_label = "Verified (round-trip ok)" if dry_run else "Successfully migrated"

    table = Table(title="Migration Report", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("Total .md files found", str(report.total_found))
    table.add_row(migrated_label, str(report.migrated), style="green" if report.migrated else "")
    table.add_row("Skipped (no frontmatter)", str(report.skipped_no_frontmatter))
    table.add_row("Skipped (.yaml already exists)", str(report.skipped_already_converted))
    table.add_row("Skipped (.md.bak already exists)", str(report.skipped_bak_exists))
    table.add_row("Errors", str(report.error_count), style="red" if report.error_count else "")

    console.print()
    console.print(table)

    if report.errors:
        console.print("\n[red bold]:cross_mark: Errors:[/red bold]")
        for file_path, msg in report.errors:
            console.print(f"  [red]:cross_mark:[/red] {file_path}")
            for line in msg.splitlines():
                console.print(f"     {line}")
            console.print()

    if dry_run and not report.error_count:
        console.print("\n[yellow]:warning:  Dry run complete — no files modified.[/yellow]")
        console.print("[dim]Run with --confirm to execute the migration.[/dim]")
    elif not dry_run and not report.error_count:
        console.print(f"\n[green]:white_check_mark: Done — {report.migrated} file(s) converted to YAML.[/green]")
        console.print("[dim]Run with --cleanup to remove .md.bak files after verifying YAML output.[/dim]")


if __name__ == "__main__":
    app()
