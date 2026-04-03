#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ruamel.yaml>=0.18.0",
#     "typer>=0.21.0",
#     "rich>=13.0",
# ]
# ///
"""Rename legacy plan files from tasks-{N}-{slug} to P{NNN}-{slug}.yaml.

Migration steps per file:
1. Resolve slug from legacy filename.
2. Determine P{NNN} from linked GitHub issue number (via backlog items) or
   assign sequential from a counter starting above the highest seen issue.
3. Convert legacy markdown / YAML-frontmatter format to pure YAML via ``sam migrate``.
4. Rename the output file to ``P{NNN}-{slug}.yaml``.
5. Update the backlog item's ``plan`` field to the new path (``--update-backlog``).

Idempotent: files already named ``P{NNN}-*`` are skipped.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.table import Table
from ruamel.yaml import YAML

app = typer.Typer(help="Rename plan files from tasks-{N}-{slug} to P{NNN}-{slug}.yaml")
console = Console()
err_console = Console(stderr=True)

# Regex patterns
_TASKS_RE = re.compile(r"^tasks-\d+-(.+)$")
_P_NUMERIC_RE = re.compile(r"^P(\d+)-")
_ISSUE_RE = re.compile(r"issue:\s*['\"]?#?(\d+)['\"]?")
_PLAN_RE = re.compile(r"^  plan:\s+(.+)$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


@dataclass
class RenameEntry:
    """One planned file rename operation."""

    old_path: Path
    slug: str
    p_num: int
    new_path: Path
    has_backlog: bool


def _extract_slug(name: str) -> str | None:
    """Extract slug from legacy ``tasks-{N}-{slug}`` name.

    Args:
        name: Filename or directory name without extension.

    Returns:
        The slug portion, or None if the name does not match the legacy pattern.
    """
    m = _TASKS_RE.match(name)
    return m.group(1) if m else None


def _build_plan_to_issue_map(backlog_dir: Path) -> dict[str, int]:
    """Build mapping from plan path to GitHub issue number.

    Scans all backlog item files for YAML frontmatter containing both
    ``issue`` and ``plan`` fields.

    Args:
        backlog_dir: Directory containing ``.md`` backlog item files.

    Returns:
        Dictionary mapping plan file paths to integer issue numbers.
    """
    plan_to_issue: dict[str, int] = {}
    if not backlog_dir.is_dir():
        return plan_to_issue

    yaml = YAML()
    yaml.preserve_quotes = True

    for f in backlog_dir.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        if not content.startswith("---"):
            continue

        fm_match = _FRONTMATTER_RE.match(content)
        if not fm_match:
            continue

        try:
            data = yaml.load(fm_match.group(1))
        except Exception:  # noqa: BLE001, S112
            continue

        if not isinstance(data, dict):
            continue

        _extract_plan_issue(data, content, plan_to_issue)

    return plan_to_issue


def _extract_plan_issue(data: dict, content: str, plan_to_issue: dict[str, int]) -> None:
    """Extract plan->issue mapping from a parsed backlog item.

    Mutates ``plan_to_issue`` in place.

    Args:
        data: Parsed YAML frontmatter dict.
        content: Raw file content (for regex fallback).
        plan_to_issue: Mapping to update.
    """
    metadata = data.get("metadata", {}) or {}
    issue_raw = metadata.get("issue") or data.get("issue")
    plan_raw = metadata.get("plan") or data.get("plan")

    if not issue_raw or not plan_raw:
        issue_m = _ISSUE_RE.search(content)
        plan_m = _PLAN_RE.search(content)
        if issue_m and plan_m:
            plan_raw = plan_m.group(1).strip()
            issue_raw = issue_m.group(1)

    if not issue_raw or not plan_raw:
        return

    issue_str = str(issue_raw).lstrip("#").strip()
    if not issue_str.isdigit():
        return

    plan_path = str(plan_raw).strip()
    if plan_path and plan_path not in {"", "N/A"}:
        plan_to_issue[plan_path] = int(issue_str)


def _find_legacy_entries(plan_dir: Path) -> list[Path]:
    """Find all legacy ``tasks-*`` files and directories.

    Args:
        plan_dir: Directory to search.

    Returns:
        Sorted list of Path objects matching the legacy naming pattern.
    """
    entries: list[Path] = [entry for entry in plan_dir.iterdir() if _TASKS_RE.match(entry.name)]
    entries.sort(key=lambda p: p.name)
    return entries


def _next_sequential(seen_numbers: set[int], start: int = 1) -> int:
    """Return the next unused positive integer not in ``seen_numbers``.

    Args:
        seen_numbers: Set of integers already allocated.
        start: Minimum value to consider.

    Returns:
        Smallest integer >= start that is not in seen_numbers.
    """
    n = start
    while n in seen_numbers:
        n += 1
    return n


def _run_sam_migrate(slug: str, plan_dir: Path) -> Path | None:
    """Run ``sam migrate`` to convert a legacy plan to pure YAML.

    Args:
        slug: Plan slug (used as the address for ``sam migrate``).
        plan_dir: Plan directory (passed as ``--plan-dir``).

    Returns:
        Path to the migrated YAML file on success, or None on failure.
    """
    cmd = ["uv", "run", "sam", "migrate", slug, "--plan-dir", str(plan_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        err_console.print(
            f":cross_mark: [red]sam migrate failed for slug [bold]{slug}[/bold]:[/red]\n{result.stderr.strip()}"
        )
        return None

    candidates = list(plan_dir.glob(f"tasks-*-{slug}.yaml"))
    if len(candidates) == 1:
        return candidates[0]

    candidates = [p for p in plan_dir.glob("*.yaml") if slug in p.name]
    if len(candidates) == 1:
        return candidates[0]

    err_console.print(f":warning: [yellow]Cannot find migrated YAML for slug [bold]{slug}[/bold][/yellow]")
    return None


def _update_backlog_plan(plan_path_old: str, plan_path_new: str, backlog_dir: Path, *, verbose: bool = False) -> bool:
    """Update backlog item plan field to new path using the backlog CLI.

    Args:
        plan_path_old: Current plan path value in backlog item.
        plan_path_new: New plan path to write.
        backlog_dir: Directory containing backlog item files.
        verbose: Print additional debug output.

    Returns:
        True if an update was performed, False if no matching backlog item found
        or the CLI call failed.
    """
    matching_file: Path | None = None
    for f in backlog_dir.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        if f"plan: {plan_path_old}" in content or f"plan: plan/{plan_path_old}" in content:
            matching_file = f
            break

    if not matching_file:
        if verbose:
            err_console.print(f"  [dim]No backlog item found for plan [bold]{plan_path_old}[/bold][/dim]")
        return False

    content = matching_file.read_text(encoding="utf-8")
    issue_m = _ISSUE_RE.search(content)
    if issue_m:
        selector = f"#{issue_m.group(1)}"
    else:
        name_parts = matching_file.stem.split("-", 1)
        selector = name_parts[1].replace("-", " ") if len(name_parts) > 1 else matching_file.stem

    backlog_script = backlog_dir.parent / "skills" / "backlog" / "scripts" / "backlog.py"
    cmd = ["uv", "run", str(backlog_script), "update", selector, "--plan", plan_path_new]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        err_console.print(
            f":warning: [yellow]Backlog update failed for [bold]{selector}[/bold]:[/yellow]\n{result.stderr.strip()}"
        )
        return False

    return True


def _build_rename_map(
    legacy_entries: list[Path], plan_dir: Path, plan_to_issue: dict[str, int], allocated_numbers: set[int]
) -> tuple[list[RenameEntry], int]:
    """Map legacy plan entries to their target P{NNN}-{slug}.yaml names.

    Args:
        legacy_entries: List of legacy path entries to process.
        plan_dir: Resolved plan directory.
        plan_to_issue: Mapping of plan path -> issue number from backlog.
        allocated_numbers: Set of already-allocated P numbers (mutated in place).

    Returns:
        Tuple of (rename_entries, skipped_count).
    """
    rename_map: list[RenameEntry] = []
    skipped = 0
    sequential_start = max(allocated_numbers, default=0) + 1

    for entry in legacy_entries:
        stem = entry.stem if entry.is_file() else entry.name
        slug = _extract_slug(stem)
        if not slug:
            skipped += 1
            continue

        p_num = _resolve_p_num(entry, plan_dir, plan_to_issue, allocated_numbers, sequential_start)
        if p_num > sequential_start:
            sequential_start = p_num + 1

        allocated_numbers.add(p_num)

        new_name = f"P{p_num:03d}-{slug}.yaml"
        new_path = plan_dir / new_name

        if new_path.exists():
            skipped += 1
            continue

        has_backlog = f"plan/{entry.name}" in plan_to_issue or entry.name in plan_to_issue
        rename_map.append(RenameEntry(entry, slug, p_num, new_path, has_backlog))

    return rename_map, skipped


def _resolve_p_num(
    entry: Path, plan_dir: Path, plan_to_issue: dict[str, int], allocated_numbers: set[int], sequential_start: int
) -> int:
    """Determine P number for a legacy entry from backlog or sequential counter.

    Args:
        entry: Legacy plan path entry.
        plan_dir: Resolved plan directory.
        plan_to_issue: Mapping of plan path -> issue number.
        allocated_numbers: Already-allocated numbers (checked but not mutated).
        sequential_start: Fallback counter start value.

    Returns:
        Integer P number to assign.
    """
    candidates = [f"plan/{entry.name}", str(plan_dir / entry.name), entry.name]
    for key in candidates:
        if key in plan_to_issue:
            return plan_to_issue[key]
    return _next_sequential(allocated_numbers, sequential_start)


def _migrate_to_yaml(old_path: Path, slug: str, plan_dir: Path) -> Path | None:
    """Convert a legacy .md or directory plan to pure YAML via sam migrate.

    Removes the original file or directory on success.

    Args:
        old_path: Legacy plan path to migrate.
        slug: Plan slug (passed to sam migrate).
        plan_dir: Plan directory.

    Returns:
        Path to the intermediate .yaml file, or None on failure.
    """
    yaml_path = _run_sam_migrate(slug, plan_dir)
    if yaml_path is None:
        return None

    if old_path.is_dir():
        import shutil  # noqa: PLC0415 — imported here to avoid top-level cost when unused

        shutil.rmtree(old_path)
    else:
        old_path.unlink()

    return yaml_path


def _execute_rename(entry: RenameEntry, plan_dir: Path) -> Path | None:
    """Perform format conversion and file rename for one entry.

    Args:
        entry: Rename operation to execute.
        plan_dir: Resolved plan directory.

    Returns:
        The new path on success, or None on failure.
    """
    if entry.old_path.suffix == ".md" or entry.old_path.is_dir():
        yaml_intermediate = _migrate_to_yaml(entry.old_path, entry.slug, plan_dir)
        if yaml_intermediate is None:
            return None
    else:
        yaml_intermediate = entry.old_path

    try:
        yaml_intermediate.rename(entry.new_path)
    except OSError as exc:
        err_console.print(f":cross_mark: [red]Rename failed for [bold]{yaml_intermediate.name}[/bold]: {exc}[/red]")
        return None

    return entry.new_path


def _print_rename_table(rename_map: list[RenameEntry], *, dry_run: bool) -> None:
    """Print a Rich table showing planned or executed renames.

    Args:
        rename_map: List of rename entries.
        dry_run: True if this is a preview table.
    """
    table = Table("Old Name", "P#", "New Name", "Backlog?", title="Rename Plan" if dry_run else "Renames")
    for entry in rename_map:
        has_backlog_str = ":white_check_mark:" if entry.has_backlog else ":cross_mark:"
        table.add_row(entry.old_path.name, str(entry.p_num), entry.new_path.name, has_backlog_str)
    console.print(table)


@app.command()
def rename(
    plan_dir: Annotated[Path, typer.Argument(help="Directory containing plan files (default: plan)")] = Path("plan"),
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Report changes without executing")] = False,
    update_backlog: Annotated[
        bool, typer.Option("--update-backlog/--no-update-backlog", help="Update backlog plan references to new paths")
    ] = True,
    backlog_dir: Annotated[Path, typer.Option("--backlog-dir", help="Directory containing backlog item files")] = Path(
        ".claude/backlog"
    ),
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Print additional detail")] = False,
) -> None:
    """Rename tasks-{N}-{slug} plan files to P{NNN}-{slug}.yaml.

    For each legacy plan file:

    1. Determines P{NNN} from linked GitHub issue (via backlog item) or assigns
       a sequential number above the highest seen issue number.
    2. Converts to pure YAML via ``sam migrate`` if not already YAML.
    3. Renames to ``P{NNN}-{slug}.yaml``.
    4. Updates backlog ``plan`` reference if ``--update-backlog`` is set.

    Idempotent: already-renamed P{NNN}-* files are skipped.

    Args:
        plan_dir: Directory containing plan files.
        dry_run: Preview changes without writing.
        update_backlog: Update backlog plan field references.
        backlog_dir: Backlog items directory.
        verbose: Extra output.
    """
    plan_dir = plan_dir.resolve()
    backlog_dir = backlog_dir.resolve()

    if not plan_dir.is_dir():
        err_console.print(f":cross_mark: [red]Plan directory not found: {plan_dir}[/red]")
        raise typer.Exit(1)

    plan_to_issue = _build_plan_to_issue_map(backlog_dir)
    if verbose:
        console.print(f"[dim]Found {len(plan_to_issue)} backlog items with plan references[/dim]")

    allocated_numbers: set[int] = set(plan_to_issue.values())
    for entry in plan_dir.iterdir():
        m = _P_NUMERIC_RE.match(entry.name)
        if m:
            allocated_numbers.add(int(m.group(1)))

    legacy_entries = _find_legacy_entries(plan_dir)
    if not legacy_entries:
        console.print(":white_check_mark: [green]No legacy tasks-* files found. Nothing to rename.[/green]")
        return

    console.print(f"Found [bold]{len(legacy_entries)}[/bold] legacy plan entries in [bold]{plan_dir}[/bold].")
    if dry_run:
        console.print("[yellow]Dry run mode — no files will be modified.[/yellow]")

    rename_map, skipped = _build_rename_map(legacy_entries, plan_dir, plan_to_issue, allocated_numbers)

    if skipped:
        console.print(f"[dim]Skipped {skipped} entries (already renamed or no slug).[/dim]")

    if not rename_map:
        console.print(":white_check_mark: [green]All plan files already renamed. No changes needed.[/green]")
        return

    _print_rename_table(rename_map, dry_run=dry_run)

    if dry_run:
        console.print(f"\n[yellow]Dry run complete:[/yellow] {len(rename_map)} renames would be performed.")
        return

    succeeded, failed, backlog_updated = _run_renames(
        rename_map, plan_dir, backlog_dir, update_backlog=update_backlog, verbose=verbose
    )

    console.print(
        f"\n[bold green]Done:[/bold green] {succeeded} renamed, "
        f"{failed} failed, "
        f"{backlog_updated} backlog references updated."
    )

    if failed:
        raise typer.Exit(1)


def _run_renames(
    rename_map: list[RenameEntry], plan_dir: Path, backlog_dir: Path, *, update_backlog: bool, verbose: bool
) -> tuple[int, int, int]:
    """Execute all rename operations and return counts.

    Args:
        rename_map: Entries to rename.
        plan_dir: Resolved plan directory.
        backlog_dir: Backlog items directory.
        update_backlog: Whether to update backlog plan references.
        verbose: Verbose output flag.

    Returns:
        Tuple of (succeeded, failed, backlog_updated).
    """
    succeeded = 0
    failed = 0
    backlog_updated = 0

    for entry in rename_map:
        console.print(f"[dim]Processing [bold]{entry.old_path.name}[/bold] -> {entry.new_path.name}...[/dim]")
        result_path = _execute_rename(entry, plan_dir)
        if result_path is None:
            failed += 1
            continue

        succeeded += 1
        console.print(f"  :white_check_mark: {entry.old_path.name} -> {entry.new_path.name}")

        if update_backlog:
            old_ref = f"plan/{entry.old_path.name}"
            new_ref = f"plan/{entry.new_path.name}"
            if _update_backlog_plan(old_ref, new_ref, backlog_dir, verbose=verbose):
                backlog_updated += 1
                if verbose:
                    console.print(f"  :white_check_mark: Backlog updated: plan -> {new_ref}")

    return succeeded, failed, backlog_updated


if __name__ == "__main__":
    app()
