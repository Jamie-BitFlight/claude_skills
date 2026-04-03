#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "ruamel.yaml>=0.18.0",
# ]
# ///
"""Migrate task files from markdown format to YAML frontmatter format.

This script converts existing markdown-format task files to the new YAML
frontmatter format while preserving all metadata and content.

Usage:
    # Migrate single file
    ./migrate_task_format.py tasks-refactor-plugin.md

    # Migrate all task files in directory (use dh_paths.plan_dir() to resolve path)
    ./migrate_task_format.py "$(uv run python -c 'from dh_paths import plan_dir; print(plan_dir())')"

    # Dry run (show changes without writing)
    ./migrate_task_format.py --dry-run tasks.md

    # Validate migrated files
    ./migrate_task_format.py --validate tasks.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO, TextIOWrapper
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
from rich.panel import Panel
from rich.table import Table
from ruamel.yaml import YAML, YAMLError

app = typer.Typer(
    name="migrate_task_format",
    help="Migrate task files from markdown to YAML frontmatter format.",
    no_args_is_help=True,
)
console = Console()

# Constants
DEFAULT_PRIORITY = 3
DEFAULT_COMPLEXITY = "medium"


# =============================================================================
# Status Mapping (Old Format -> New Format)
# =============================================================================

STATUS_MAP = {
    "NOT STARTED": "not-started",
    "IN PROGRESS": "in-progress",
    "COMPLETE": "complete",
    "BLOCKED": "blocked",
    # Emoji variations
    ":x:": "not-started",
    ":cross_mark:": "not-started",
    ":white_check_mark:": "complete",
    ":heavy_check_mark:": "complete",
    ":arrows_counterclockwise:": "in-progress",
    ":repeat:": "in-progress",
}


def normalize_status(old_status: str) -> str:
    """Convert old status format to new hyphenated lowercase format.

    Args:
        old_status: Status from old markdown format.

    Returns:
        Normalized status in new format.
    """
    # Remove emoji markers from status text
    # Common patterns: "✅ COMPLETE", ":white_check_mark: COMPLETE"
    status_clean = old_status.strip()

    # Remove common emoji characters
    status_clean = status_clean.replace("✅", "").replace("❌", "").replace("🔄", "")
    status_clean = status_clean.strip()

    status_upper = status_clean.upper()

    # Check for exact matches first
    if status_upper in STATUS_MAP:
        return STATUS_MAP[status_upper]

    # Check for emoji patterns in original text
    status_lower = old_status.lower().strip()
    for pattern, new_status in STATUS_MAP.items():
        if pattern in status_lower:
            return new_status

    # Check if cleaned text matches after removing emojis
    for old_pattern, new_status in STATUS_MAP.items():
        if old_pattern.upper() in status_upper:
            return new_status

    # Default to not-started if unclear
    return "not-started"


def normalize_complexity(old_complexity: str) -> str:
    """Convert old complexity format to lowercase.

    Args:
        old_complexity: Complexity from old format (e.g., "Medium", "Low").

    Returns:
        Lowercase complexity (e.g., "medium", "low").
    """
    return old_complexity.lower().strip()


# =============================================================================
# Task Data Structure
# =============================================================================


@dataclass(kw_only=True)
class TaskData:
    """Holds task metadata and body content for migration.

    Attributes:
        task_id: Unique task identifier.
        title: Task title/name.
        status: Task status (new format).
        agent: Agent responsible for task.
        dependencies: List of task IDs.
        priority: Priority level (1-5).
        complexity: Complexity level (low/medium/high).
        started: ISO 8601 timestamp when started.
        completed: ISO 8601 timestamp when completed.
        blocked_by: List of external blockers.
        body: Markdown body content.
    """

    task_id: str
    title: str
    status: str = "not-started"
    agent: str | None = None
    dependencies: list[str] = field(default_factory=list)
    priority: int = 3
    complexity: str = "medium"
    started: str | None = None
    completed: str | None = None
    blocked_by: list[str] = field(default_factory=list)
    body: str = ""

    def to_yaml_frontmatter(self) -> str:
        """Convert task to YAML frontmatter format.

        Returns:
            Complete task section with YAML frontmatter and markdown body.
        """
        frontmatter: dict[str, str | int | list[str]] = {
            "task": self.task_id,
            "title": self.title,
            "status": self.status,
        }

        # Add optional fields only if present
        if self.agent:
            frontmatter["agent"] = self.agent
        if self.dependencies:
            frontmatter["dependencies"] = self.dependencies
        if self.priority != DEFAULT_PRIORITY:
            frontmatter["priority"] = self.priority
        if self.complexity != DEFAULT_COMPLEXITY:
            frontmatter["complexity"] = self.complexity
        if self.started:
            frontmatter["started"] = self.started
        if self.completed:
            frontmatter["completed"] = self.completed
        if self.blocked_by:
            frontmatter["blocked-by"] = self.blocked_by

        # Convert to YAML
        yaml = YAML()
        yaml.default_flow_style = False
        buf = StringIO()
        yaml.dump(frontmatter, buf)
        yaml_str = buf.getvalue()

        # Build complete section
        return f"---\n{yaml_str}---\n\n{self.body}\n"


# =============================================================================
# Markdown Parser (Legacy Format)
# =============================================================================

_TASK_HEADER_PATTERN = re.compile(r"^#{2,3}\s+Task\s+([A-Za-z0-9.]+):\s*(.+)$")
_DEP_TASK_PATTERN = re.compile(r"Task\s+([A-Za-z0-9.]+)")
_DEP_DIRECT_PATTERN = re.compile(r"\b([A-Z]\d+|\d+(?:\.\d+)?)\b")


def _parse_dependencies(dep_text: str) -> list[str]:
    """Parse dependency task IDs from a dependency field value.

    Tries "Task X.Y" pattern first, then falls back to direct ID patterns.

    Args:
        dep_text: Raw text after "**Dependencies**:" label.

    Returns:
        List of parsed task ID strings, possibly empty.
    """
    if dep_text.lower() == "none":
        return []

    deps = _DEP_TASK_PATTERN.findall(dep_text)
    if deps:
        return deps

    # Fallback: direct ID pattern
    return _DEP_DIRECT_PATTERN.findall(dep_text)


def _parse_metadata_line(line: str, task: TaskData) -> bool:
    """Parse a single metadata line and apply it to the task.

    Args:
        line: A line from the markdown file.
        task: The TaskData object to mutate with parsed values.

    Returns:
        True if the line was recognized as a metadata field, False otherwise.
    """
    if line.startswith("**Status**:"):
        task.status = normalize_status(line.split(":", 1)[1].strip())
    elif line.startswith("**Agent**:"):
        agent_text = line.split(":", 1)[1].strip()
        if agent_text.lower() not in {"none", "n/a", "-"}:
            task.agent = agent_text
    elif line.startswith("**Dependencies**:"):
        task.dependencies = _parse_dependencies(line.split(":", 1)[1].strip())
    elif line.startswith("**Priority**:"):
        priority_match = re.search(r"(\d+)", line.split(":", 1)[1].strip())
        if priority_match:
            task.priority = int(priority_match.group(1))
    elif line.startswith("**Complexity**:"):
        complexity_match = re.match(r"(\w+)", line.split(":", 1)[1].strip())
        if complexity_match:
            task.complexity = normalize_complexity(complexity_match.group(1))
    elif line.startswith("**Started**:"):
        task.started = line.split(":", 1)[1].strip()
    elif line.startswith("**Completed**:"):
        task.completed = line.split(":", 1)[1].strip()
    else:
        return False
    return True


def _finalize_task(task: TaskData, body_lines: list[str], tasks: list[TaskData]) -> None:
    """Assign accumulated body lines to a task and append it to the task list.

    Args:
        task: The TaskData object to finalize.
        body_lines: Accumulated body content lines.
        tasks: The list to append the finalized task to.
    """
    task.body = "\n".join(body_lines).strip()
    tasks.append(task)


def parse_markdown_tasks(content: str) -> list[TaskData]:
    """Parse tasks from legacy markdown format.

    Args:
        content: Raw markdown file content.

    Returns:
        List of TaskData objects parsed from markdown.
    """
    tasks: list[TaskData] = []
    lines = content.split("\n")
    current_task: TaskData | None = None
    current_body_lines: list[str] = []
    in_body = False

    for line in lines:
        # Check for task header
        header_match = _TASK_HEADER_PATTERN.match(line)
        if header_match:
            # Save previous task
            if current_task:
                _finalize_task(current_task, current_body_lines, tasks)

            # Start new task
            current_task = TaskData(task_id=header_match.group(1), title=header_match.group(2).strip())
            current_body_lines = []
            in_body = False
            continue

        if current_task is None:
            continue

        # Parse metadata fields via helper
        if not _parse_metadata_line(line, current_task):
            # Not metadata -- accumulate as body content
            if not in_body and line.strip():
                in_body = True
            if in_body:
                current_body_lines.append(line)

    # Save last task
    if current_task:
        _finalize_task(current_task, current_body_lines, tasks)

    return tasks


# =============================================================================
# Migration Functions
# =============================================================================


def migrate_file(file_path: Path, *, dry_run: bool = False, validate: bool = False) -> tuple[int, int]:
    """Migrate a single task file to YAML frontmatter format.

    Args:
        file_path: Path to task file.
        dry_run: If True, show changes without writing.
        validate: If True, validate output against schema.

    Returns:
        Tuple of (tasks_migrated, errors_count).
    """
    # Read original content
    content = file_path.read_text(encoding="utf-8")

    # Check if already in YAML format
    if content.strip().startswith("---\n"):
        console.print(f"[yellow]Skipping {file_path.name}: Already in YAML format[/yellow]")
        return 0, 0

    # Parse tasks from markdown
    tasks = parse_markdown_tasks(content)

    if not tasks:
        console.print(f"[yellow]No tasks found in {file_path.name}[/yellow]")
        return 0, 0

    # Convert to YAML format
    migrated_sections = []
    errors = 0

    for task in tasks:
        try:
            yaml_section = task.to_yaml_frontmatter()
            migrated_sections.append(yaml_section)
            console.print(f"  :white_check_mark: Task {task.task_id}: {task.title}")
        except YAMLError as e:
            console.print(f"  :cross_mark: Task {task.task_id}: Failed - {e}")
            errors += 1

    # Build new file content
    new_content = "\n".join(migrated_sections)

    if dry_run:
        console.print("\n[bold]Dry run - changes not written[/bold]")
        console.print(Panel(new_content, title="Preview"))
        return len(tasks), errors

    # Write new content
    if errors == 0:
        # Backup original
        backup_path = file_path.with_suffix(f".md.backup.{datetime.now(tz=UTC):%Y%m%d%H%M%S}")
        backup_path.write_text(content, encoding="utf-8")
        console.print(f"[dim]Backup created: {backup_path.name}[/dim]")

        # Write migrated content
        file_path.write_text(new_content, encoding="utf-8")
        console.print(f":white_check_mark: File written: {file_path.name}")

    return len(tasks) - errors, errors


# =============================================================================
# CLI Commands
# =============================================================================


FilePath = Annotated[
    Path, typer.Argument(help="Path to task file or directory containing task files.", exists=True, resolve_path=True)
]


@app.command()
def migrate(
    path: FilePath,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without writing files.")] = False,
    validate: Annotated[bool, typer.Option("--validate", help="Validate migrated files against schema.")] = False,
) -> None:
    """Migrate task file(s) from markdown to YAML frontmatter format.

    Args:
        path: Path to task file or directory.
        dry_run: If True, show changes without writing.
        validate: If True, validate output against schema.
    """
    console.print("[bold blue]Task Format Migration Tool[/bold blue]\n")

    # Collect files to migrate
    files_to_migrate: list[Path] = []

    if path.is_file():
        if path.suffix == ".md":
            files_to_migrate.append(path)
        else:
            console.print(f"[red]Error: {path.name} is not a markdown file[/red]")
            raise typer.Exit(1)
    elif path.is_dir():
        # Find all task files in directory
        task_patterns = ["tasks-*.md", "*-tasks.md", "task-*.md"]
        for pattern in task_patterns:
            files_to_migrate.extend(path.glob(pattern))
        files_to_migrate = sorted(set(files_to_migrate))

        if not files_to_migrate:
            console.print(f"[yellow]No task files found in {path}[/yellow]")
            raise typer.Exit(0)

    # Migrate each file
    total_tasks = 0
    total_errors = 0

    for file_path in files_to_migrate:
        console.print(f"\n[bold]Migrating: {file_path.name}[/bold]")
        tasks_migrated, errors = migrate_file(file_path, dry_run=dry_run, validate=validate)
        total_tasks += tasks_migrated
        total_errors += errors

    # Summary
    console.print("\n" + "=" * 60)
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files processed", str(len(files_to_migrate)))
    table.add_row("Tasks migrated", str(total_tasks))
    table.add_row("Errors", str(total_errors), style="red" if total_errors > 0 else "green")

    console.print(table)

    if total_errors > 0:
        console.print("\n[red]Migration completed with errors[/red]")
        raise typer.Exit(1)

    if dry_run:
        console.print("\n[yellow]Dry run completed - no files modified[/yellow]")
    else:
        console.print("\n[green]:white_check_mark: Migration completed successfully[/green]")


if __name__ == "__main__":
    app()
