#!/usr/bin/env -S uv run --quiet --script
"""Fix invalid tool format patterns in Claude Code frontmatter.

Recursively scans:
- ~/.claude/agents/*.md
- ~/.claude/commands/*.md
- ~/.claude/skills/*/SKILL.md
- ~/repos/**/agents/*.md
- ~/repos/**/commands/*.md
- ~/repos/**/skills/*/SKILL.md

Converts:
1. YAML list format to comma-separated string
2. JSON array format to comma-separated string
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
# ]
# ///

from __future__ import annotations

import re
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

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()
app = typer.Typer(help="Fix invalid tool format patterns in Claude Code frontmatter", no_args_is_help=False)


class FrontmatterProcessor:
    """Process YAML frontmatter in markdown files."""

    YAML_LIST_PATTERN = re.compile(r"^((?:tools|allowed-tools|disallowedTools):)\s*\n((?:  - .+\n)+)", re.MULTILINE)
    JSON_ARRAY_PATTERN = re.compile(r"^((?:tools|allowed-tools|disallowedTools):)\s*\[([^\]]+)\]", re.MULTILINE)

    def __init__(self) -> None:
        """Initialize the FrontmatterProcessor."""
        self.changed = False

    def fix_yaml_list_format(self, content: str) -> str:
        """Convert YAML list format to comma-separated string.

        Args:
            content: Markdown file content with YAML frontmatter

        Returns:
            Modified content with list format converted to string format

        Example:
            Before:
                allowed-tools:
                  - Read
                  - Glob

            After:
                allowed-tools: Read, Glob
        """

        def replace_list(match: re.Match[str]) -> str:
            self.changed = True
            field = match.group(1)
            items = match.group(2)
            tools = [line.strip()[2:].strip() for line in items.strip().split("\n")]
            return f"{field} {', '.join(tools)}\n"

        return self.YAML_LIST_PATTERN.sub(replace_list, content)

    def fix_json_array_format(self, content: str) -> str:
        """Convert JSON array format to comma-separated string.

        Args:
            content: Markdown file content with YAML frontmatter

        Returns:
            Modified content with JSON array format converted to string format

        Example:
            Before:
                tools: ["Read", "Grep"]

            After:
                tools: Read, Grep
        """

        def replace_array(match: re.Match[str]) -> str:
            self.changed = True
            field = match.group(1)
            items = match.group(2)
            tools = [item.strip().strip('"').strip("'") for item in items.split(",")]
            return f"{field} {', '.join(tools)}"

        return self.JSON_ARRAY_PATTERN.sub(replace_array, content)

    def process_content(self, content: str) -> tuple[str, bool]:
        """Process content and apply all transformations.

        Args:
            content: Markdown file content

        Returns:
            Tuple of (modified_content, changed_flag)
        """
        self.changed = False
        content = self.fix_yaml_list_format(content)
        content = self.fix_json_array_format(content)
        return content, self.changed


class FileScanner:
    """Scan filesystem for Claude Code frontmatter files."""

    def __init__(self, skip_venv: bool = True, skip_node_modules: bool = True) -> None:
        """Initialize file scanner.

        Args:
            skip_venv: Skip .venv directories
            skip_node_modules: Skip node_modules directories
        """
        self.skip_venv = skip_venv
        self.skip_node_modules = skip_node_modules

    def find_files(self, scan_home: bool = False) -> list[Path]:
        """Find all relevant markdown files.

        Args:
            scan_home: Include ~/repos/** paths in scan

        Returns:
            Sorted list of unique file paths
        """
        home = Path.home()

        patterns: list[Path] = [
            home / ".claude/agents/**/*.md",
            home / ".claude/commands/**/*.md",
            home / ".claude/skills/**/SKILL.md",
        ]

        if scan_home:
            patterns.extend([home / "**/agents/*.md", home / "**/commands/*.md", home / "**/skills/*/SKILL.md"])

        files: set[Path] = set()
        for pattern in patterns:
            for filepath in home.glob(str(pattern.relative_to(home))):
                if self._should_skip(filepath):
                    continue
                # Only include files in .claude directories or repos if scanning repos
                if ".claude" in filepath.parts or (scan_home and "repos" in filepath.parts):
                    files.add(filepath)

        return sorted(files)

    def _should_skip(self, filepath: Path) -> bool:
        """Determine if file should be skipped.

        Args:
            filepath: Path to check

        Returns:
            True if file should be skipped
        """
        if self.skip_venv and ".venv" in filepath.parts:
            return True
        return bool(self.skip_node_modules and "node_modules" in filepath.parts)


def process_file(filepath: Path, processor: FrontmatterProcessor) -> bool:
    """Process a single file and return True if changes were made.

    Args:
        filepath: Path to markdown file
        processor: FrontmatterProcessor instance

    Returns:
        True if file was modified

    Raises:
        OSError: If file cannot be read or written
    """
    content = filepath.read_text(encoding="utf-8")
    modified_content, changed = processor.process_content(content)

    if changed:
        filepath.write_text(modified_content, encoding="utf-8")
        return True
    return False


def process_files_batch(
    files: list[Path], processor: FrontmatterProcessor, dry_run: bool
) -> tuple[list[Path], list[Path], list[tuple[Path, str]]]:
    """Process a batch of files and collect results.

    Args:
        files: List of file paths to process
        processor: FrontmatterProcessor instance
        dry_run: If True, only check for changes without modifying files

    Returns:
        Tuple of (fixed_files, skipped_files, error_files)
    """
    fixed_files: list[Path] = []
    skipped_files: list[Path] = []
    error_files: list[tuple[Path, str]] = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        process_task = progress.add_task("Processing files...", total=len(files))

        for filepath in files:
            try:
                if dry_run:
                    content = filepath.read_text(encoding="utf-8")
                    _, changed = processor.process_content(content)
                    if changed:
                        fixed_files.append(filepath)
                    else:
                        skipped_files.append(filepath)
                elif process_file(filepath, processor):
                    fixed_files.append(filepath)
                    console.print(f":white_check_mark: Fixed: {filepath}")
                else:
                    skipped_files.append(filepath)
            except OSError as e:
                error_files.append((filepath, str(e)))
                console.print(f":cross_mark: Error: {filepath}: {e}")

            progress.advance(process_task)

    return fixed_files, skipped_files, error_files


def display_summary(
    fixed_files: list[Path],
    skipped_files: list[Path],
    error_files: list[tuple[Path, str]],
    total_files: int,
    dry_run: bool,
) -> None:
    """Display summary table and error details.

    Args:
        fixed_files: List of files that were fixed
        skipped_files: List of files that were skipped
        error_files: List of files with errors
        total_files: Total number of files processed
        dry_run: Whether this was a dry run
    """
    table = Table(title=":clipboard: Summary")
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")

    if dry_run:
        table.add_row("Would fix", str(len(fixed_files)))
    else:
        table.add_row("Fixed", str(len(fixed_files)))
    table.add_row("Skipped (no changes needed)", str(len(skipped_files)))
    table.add_row("Errors", str(len(error_files)))
    table.add_row("Total", str(total_files))

    console.print()
    console.print(table)

    if error_files:
        console.print("\n:warning: Files with errors:")
        for filepath, error in error_files:
            console.print(f"  {filepath}: {error}")

    if dry_run and fixed_files:
        console.print("\n:information: This was a dry run. Rerun without --dry-run to apply changes.")


@app.command()
def main(
    scan_home: Annotated[
        bool, typer.Option("--scan-repos/--no-scan-repos", help="Include ~/repos/** paths in scan")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be changed without modifying files")
    ] = False,
) -> None:
    """Scan and fix invalid tool format patterns in Claude Code frontmatter.

    Args:
        scan_home: Include ~/repos/** paths in scan
        dry_run: Show changes without modifying files
    """
    console.print(":magnifying_glass_tilted_right: Scanning for markdown files with invalid tool formats...\n")

    scanner = FileScanner()
    processor = FrontmatterProcessor()

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        scan_task = progress.add_task("Finding files...", total=None)
        files = scanner.find_files(scan_home=scan_home)
        progress.update(scan_task, completed=True)

    console.print(f"Found {len(files)} files to check\n")

    if not files:
        console.print(":warning: No files found to process")
        return

    fixed_files, skipped_files, error_files = process_files_batch(files, processor, dry_run)
    display_summary(fixed_files, skipped_files, error_files, len(files), dry_run)


if __name__ == "__main__":
    app()
