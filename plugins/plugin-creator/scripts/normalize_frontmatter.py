#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ruamel.yaml>=0.18.0",
#     "python-frontmatter>=1.1.0",
#     "typer>=0.21.0",
# ]
# ///
"""Normalize YAML frontmatter quoting across all component files.

Round-trips every markdown file that contains YAML frontmatter through
ruamel.yaml to remove unnecessary quotes.  Only the frontmatter block is
affected; the body of each file is preserved verbatim.

Files discovered:
- plugins/**/*.md
- .claude/**/*.md

Exclusions: node_modules/, .venv/, *.lock

Usage::

    # Preview changes without writing
    ./normalize_frontmatter.py --dry-run

    # Apply changes
    ./normalize_frontmatter.py
"""

from __future__ import annotations

import difflib
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import ruamel.yaml
import typer
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Bootstrap: frontmatter_utils lives next to this script
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from frontmatter_utils import dump_frontmatter, load_frontmatter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FRONTMATTER_DELIMITER = "---"
EXCLUDED_DIRS: frozenset[str] = frozenset({"node_modules", ".venv", "__pycache__"})

console = Console()
app = typer.Typer(
    name="normalize-frontmatter",
    help="Normalize YAML frontmatter quoting in all plugin and .claude markdown files.",
    no_args_is_help=False,
)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _has_frontmatter(path: Path) -> bool:
    """Return True if *path* starts with a YAML frontmatter delimiter.

    Args:
        path: Markdown file to inspect.

    Returns:
        True when the first non-empty line is ``---``.
    """
    try:
        first_line = path.read_text(encoding="utf-8").lstrip().split("\n", 1)[0].strip()
    except (OSError, UnicodeDecodeError):
        return False
    return first_line == FRONTMATTER_DELIMITER


def _is_excluded(path: Path) -> bool:
    """Return True when any path component matches an excluded directory name.

    Args:
        path: File path to check.

    Returns:
        True if the path passes through an excluded directory.
    """
    return any(part in EXCLUDED_DIRS for part in path.parts)


def discover_files(root: Path) -> list[Path]:
    """Discover markdown files with frontmatter in *plugins/* and *.claude/*.

    Args:
        root: Repository root to search from.

    Returns:
        Sorted list of markdown file paths that contain YAML frontmatter.
    """
    candidates: list[Path] = []
    for pattern in ("plugins/**/*.md", ".claude/**/*.md"):
        for md_file in root.glob(pattern):
            if not md_file.is_file():
                continue
            if _is_excluded(md_file):
                continue
            if _has_frontmatter(md_file):
                candidates.append(md_file)
    return sorted(candidates)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def normalize_file(path: Path) -> str | None:
    """Round-trip frontmatter through ruamel.yaml and return the new content.

    Returns the normalized file content when different from the original, or
    ``None`` when the file is unchanged or cannot be parsed.

    Args:
        path: Markdown file to normalize.

    Returns:
        Normalized file content string if changes were made, else ``None``.
    """
    original = path.read_text(encoding="utf-8")
    try:
        post = load_frontmatter(path)
        normalized = dump_frontmatter(post)
    except (ruamel.yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
        console.print(f"  :warning:  [yellow]Skipping[/yellow] {path}: {exc}")
        return None

    # python-frontmatter's dumps() strips the trailing newline; restore it so
    # the "fix end of files" pre-commit hook does not flag every written file.
    if original.endswith("\n") and not normalized.endswith("\n"):
        normalized += "\n"

    if normalized == original:
        return None
    return normalized


# ---------------------------------------------------------------------------
# Diff rendering
# ---------------------------------------------------------------------------


def _unified_diff(original: str, normalized: str, label: str) -> str:
    """Produce a unified diff between two strings.

    Args:
        original: Original file content.
        normalized: Normalized file content.
        label: Human-readable label for the diff header.

    Returns:
        Unified diff as a string (empty if no differences).
    """
    orig_lines = original.splitlines(keepends=True)
    new_lines = normalized.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, new_lines, fromfile=f"a/{label}", tofile=f"b/{label}", n=3)
    return "".join(diff)


def _get_table_width(table: Table) -> int:
    """Measure the natural rendered width of a Rich table.

    Args:
        table: The Rich table to measure.

    Returns:
        Minimum character width needed to display the table without wrapping.
    """
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@app.command()
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Report changes without writing files.")] = False,
    root: Annotated[
        Path,
        typer.Option(
            "--root",
            help="Repository root to search from.",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path(),
) -> None:
    """Normalize YAML frontmatter quoting across all plugin and .claude markdown files.

    Discovers all ``.md`` files in ``plugins/`` and ``.claude/`` that contain
    YAML frontmatter, round-trips each through ruamel.yaml to strip unnecessary
    quotes, and writes the result back to disk (unless ``--dry-run`` is set).

    Args:
        dry_run: When True, report diffs without writing.
        root: Repository root directory.
    """
    mode_label = "[yellow]DRY RUN[/yellow]" if dry_run else "[green]LIVE[/green]"
    console.print(f"\n:magnifying_glass: Normalizing frontmatter quoting ({mode_label})\n")

    files = discover_files(root)
    if not files:
        console.print("[yellow]No markdown files with frontmatter found.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [bold]{len(files)}[/bold] files to inspect.\n")

    modified: list[Path] = []
    skipped: list[Path] = []
    unchanged: list[Path] = []

    for path in files:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        original = path.read_text(encoding="utf-8")
        normalized = normalize_file(path)

        if normalized is None:
            # Either parse error (warning already printed) or no change
            if path not in skipped:
                unchanged.append(path)
            continue

        diff_text = _unified_diff(original, normalized, str(rel))
        console.print(f":white_check_mark: [bold]{rel}[/bold]")
        if diff_text:
            panel = Panel(diff_text, title=f"diff {rel}", border_style="blue", expand=False)
            console.print(panel)

        if not dry_run:
            path.write_text(normalized, encoding="utf-8")

        modified.append(path)

    # ---------- Summary table ----------
    console.print()
    table = Table(title=":bar_chart: Normalization Summary", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold cyan")
    table.add_column("Category", style="bold", no_wrap=True)
    table.add_column("Count", justify="right", no_wrap=True)
    table.add_row("Files inspected", str(len(files)))
    table.add_row("[green]Modified[/green]" if not dry_run else "[yellow]Would modify[/yellow]", str(len(modified)))
    table.add_row("Unchanged", str(len(unchanged)))
    table.add_row("Skipped (parse errors)", str(len(skipped)))

    table.width = _get_table_width(table)
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)

    if dry_run and modified:
        console.print(f"\n[yellow]Dry-run complete — {len(modified)} file(s) would be modified.[/yellow]")
    elif modified:
        console.print(f"\n[green]:white_check_mark: Done — {len(modified)} file(s) normalized.[/green]")
    else:
        console.print("\n[green]:white_check_mark: All files already normalized.[/green]")


if __name__ == "__main__":
    app()
