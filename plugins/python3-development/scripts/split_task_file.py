#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0", "ruamel.yaml>=0.18.0"]
# ///
"""Split multi-task markdown file into one-task-per-file directory structure.

This script converts a task file containing multiple tasks (either YAML frontmatter
format or legacy markdown format) into a directory of individual task files.

Usage:
    split_task_file.py <input-file> [output-directory]

Examples:
    # Split into tasks/ subdirectory
    split_task_file.py plugin-validator-tasks.md

    # Split into custom directory
    split_task_file.py tasks.md ./my-tasks/

File Naming Convention:
    Output files are named: {task-id}-{slug}.md
    Examples: T1-data-models.md, 1.1-prepare-host.md, T15-cli-tests.md

    Slug is derived from task title:
    - Lowercase
    - Spaces and special chars → hyphens
    - Multiple hyphens collapsed to single hyphen
    - Max 50 characters
"""

from __future__ import annotations

import re

# Import from implementation_manager in same repository
import sys
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import typer
from rich.console import Console

# sam_schema is the canonical task/plan schema package.
# Installed as a workspace dependency in the project venv.
# Fallback: add packages/ to sys.path for direct-script execution outside the venv.
_SPLIT_REPO_ROOT = Path(__file__).resolve().parents[3]
_SPLIT_SAM_PACKAGES_DIR = str(_SPLIT_REPO_ROOT / "packages")
if _SPLIT_SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _SPLIT_SAM_PACKAGES_DIR)

from sam_schema.core.query import load_plan as sam_load_plan
from sam_schema.task_format import has_yaml_frontmatter

if TYPE_CHECKING:
    from sam_schema.core.models import Task as SamTask

app = typer.Typer(
    name="split_task_file", help="Split multi-task file into one-task-per-file directory", no_args_is_help=True
)
console = Console()


# =============================================================================
# Task with body content
# =============================================================================

# Regex for legacy markdown task headers: ## Task X.Y: Title or ### Task X.Y: Title
_TASK_HEADER_PATTERN = re.compile(r"^#{2,3}\s+Task\s+([A-Za-z0-9.]+):\s*(.+)$")

# Patterns for legacy markdown metadata lines
_METADATA_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\*\*Status\*\*:\s*"),
    re.compile(r"^\*\*Agent\*\*:\s*"),
    re.compile(r"^\*\*Dependencies\*\*:\s*"),
    re.compile(r"^\*\*Priority\*\*:\s*"),
    re.compile(r"^\*\*Complexity\*\*:\s*"),
    re.compile(r"^\*\*Started\*\*:\s*"),
    re.compile(r"^\*\*Completed\*\*:\s*"),
]


@dataclass
class TaskWithBody:
    """A task with both parsed metadata and original body content.

    Args:
        task: Parsed Task object with metadata fields.
        body: Original body content from the monolithic file.
    """

    task: SamTask
    body: str = ""


def _is_metadata_line(line: str) -> bool:
    """Check if a line is a legacy markdown metadata field.

    Args:
        line: Line of text to check.

    Returns:
        True if line matches a known metadata pattern.
    """
    return any(pat.match(line) for pat in _METADATA_PATTERNS)


def _parse_legacy_bodies(content: str, tasks: list[SamTask]) -> list[TaskWithBody]:
    """Extract body content for each task from legacy markdown format.

    The body starts after all ``**Field**: value`` metadata lines and continues
    until the next task header or end of file.

    Args:
        content: Raw file content in legacy markdown format.
        tasks: Parsed Task objects (metadata only) from implementation_manager.

    Returns:
        List of TaskWithBody objects pairing each task with its body content.
    """
    lines = content.split("\n")

    # Find the line ranges for each task section
    task_ranges: list[tuple[int, int]] = []
    header_indices: list[int] = []

    for i, line in enumerate(lines):
        if _TASK_HEADER_PATTERN.match(line):
            header_indices.append(i)

    # Build (start_of_body, end_of_section) for each task
    for idx, header_line_idx in enumerate(header_indices):
        # Body starts after header and metadata lines
        body_start = header_line_idx + 1

        # Skip metadata lines
        while body_start < len(lines) and _is_metadata_line(lines[body_start]):
            body_start += 1

        # Section ends at next task header or end of file
        section_end = header_indices[idx + 1] if idx + 1 < len(header_indices) else len(lines)

        task_ranges.append((body_start, section_end))

    # Pair tasks with body content
    result: list[TaskWithBody] = []
    for i, task in enumerate(tasks):
        if i < len(task_ranges):
            start, end = task_ranges[i]
            body_lines = lines[start:end]
            body = "\n".join(body_lines).strip()
        else:
            body = ""
        result.append(TaskWithBody(task=task, body=body))

    return result


def _parse_yaml_multidoc_bodies(content: str, tasks: list[SamTask]) -> list[TaskWithBody]:
    """Extract body content for each task from YAML frontmatter format.

    Handles files with multiple YAML frontmatter documents concatenated together,
    where each document has ``---`` delimiters followed by markdown body content.

    Args:
        content: Raw file content with YAML frontmatter sections.
        tasks: Parsed Task objects (metadata only) from implementation_manager.

    Returns:
        List of TaskWithBody objects pairing each task with its body content.
    """
    # Split into individual YAML+body sections by finding --- delimiters
    # Each section starts with --- (YAML) --- (body until next --- or EOF)
    bodies: list[str] = []
    sections = re.split(r"(?:^|\n)---\n", content)

    # Filter out empty sections (the split creates empties before first ---)
    # Pattern: empty, yaml1, body1, yaml2, body2, ...
    # After splitting on "---\n", pairs are (yaml_content, body_content)
    for section in sections:
        # Skip empty leading section
        if not section.strip():
            continue

        # Try to detect if this is YAML metadata or body content
        # YAML sections contain "task:" field; body sections don't
        if "task:" in section.split("\n")[0] or _looks_like_yaml_frontmatter(section):
            # This is a YAML section, skip -- the body follows
            continue

        # This is a body section
        bodies.append(section.strip())

    # Pair tasks with body content
    result: list[TaskWithBody] = []
    for i, task in enumerate(tasks):
        body = bodies[i] if i < len(bodies) else ""
        result.append(TaskWithBody(task=task, body=body))

    return result


def _looks_like_yaml_frontmatter(section: str) -> bool:
    """Heuristic check if a section looks like YAML frontmatter content.

    Args:
        section: Text section to check.

    Returns:
        True if section appears to be YAML key-value pairs.
    """
    lines = section.strip().split("\n")
    if not lines:
        return False
    # Check if most lines look like YAML key: value
    yaml_line_count = sum(1 for line in lines[:5] if re.match(r"^[a-z_-]+\s*:", line))
    return yaml_line_count >= 2  # noqa: PLR2004


def parse_tasks_with_body(file_path: Path) -> list[TaskWithBody]:
    """Parse a monolithic task file and extract tasks with their body content.

    Handles both legacy markdown format and YAML frontmatter format.

    Args:
        file_path: Path to the monolithic task file.

    Returns:
        List of TaskWithBody objects.

    Raises:
        FileNotFoundError: If file_path does not exist.
    """
    content = file_path.read_text(encoding="utf-8")
    tasks = sam_load_plan(file_path).plan.tasks

    if not tasks:
        return []

    if has_yaml_frontmatter(content):
        return _parse_yaml_multidoc_bodies(content, tasks)
    return _parse_legacy_bodies(content, tasks)


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Input text to slugify
        max_length: Maximum slug length (default 50)

    Returns:
        Lowercase slug with hyphens, max_length characters
    """
    # Convert to lowercase
    slug = text.lower()

    # Replace spaces and special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


def generate_task_filename(task: SamTask) -> str:
    """Generate filename for task file.

    Args:
        task: SamTask object with id and name

    Returns:
        Filename in format: {task-id}-{slug}.md
        Example: T1-data-models.md
    """
    slug = slugify(task.title)
    return f"{task.id}-{slug}.md"


def _generate_skeleton_body(task: SamTask) -> str:
    """Generate placeholder body content for a task with no body.

    Args:
        task: SamTask object to generate skeleton for.

    Returns:
        Skeleton markdown body with placeholder sections.
    """
    return (
        "## Context\n\n"
        f"Task {task.id}: {task.title}\n\n"
        "## Objective\n\n"
        "[Task objective to be filled in]\n\n"
        "## Requirements\n\n"
        "1. [Requirement 1]\n"
        "2. [Requirement 2]\n\n"
        "## Expected Outputs\n\n"
        "- [Output 1]\n"
        "- [Output 2]\n"
    )


def write_task_file(task: SamTask, output_path: Path, body: str = "") -> None:
    """Write single task to file with YAML frontmatter and body content.

    Args:
        task: SamTask object to write.
        output_path: Path to output file.
        body: Original body content to preserve. Falls back to skeleton if empty.
    """
    # Build YAML frontmatter
    frontmatter_lines = ["---"]
    frontmatter_lines.extend((f'task: "{task.id}"', f'title: "{task.title}"'))

    # Status (convert enum value back to hyphenated format)
    status_value = task.status.value.lower().replace(" ", "-")
    frontmatter_lines.append(f"status: {status_value}")

    # Optional fields
    if task.agent:
        frontmatter_lines.append(f'agent: "{task.agent}"')

    if task.dependencies:
        deps_str = ", ".join(f'"{d}"' for d in task.dependencies)
        frontmatter_lines.append(f"dependencies: [{deps_str}]")

    frontmatter_lines.extend((f"priority: {task.priority.value}", f"complexity: {task.complexity.lower()}"))

    if task.started:
        frontmatter_lines.append(f'started: "{task.started}"')

    if task.completed:
        frontmatter_lines.append(f'completed: "{task.completed}"')

    frontmatter_lines.append("---")

    # Use preserved body content, or fall back to skeleton
    body_content = body if body.strip() else _generate_skeleton_body(task)

    # Write file
    content = "\n".join(frontmatter_lines) + "\n\n" + body_content + "\n"

    output_path.write_text(content, encoding="utf-8")


@app.command()
def main(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Path to multi-task markdown file", exists=True, file_okay=True, dir_okay=False, resolve_path=True
        ),
    ],
    output_dir: Annotated[
        Path | None, typer.Argument(help="Output directory for task files (default: {input-stem}/tasks/)")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing task files without prompting")
    ] = False,
) -> None:
    """Split multi-task file into one-task-per-file directory.

    Args:
        input_file: Path to input task file
        output_dir: Output directory (default: tasks/ in input file directory)
        force: Overwrite existing files without prompting
    """
    console.print(f"[blue]:file_folder: Reading {input_file}...[/blue]")

    # Parse tasks with body content from input file
    try:
        tasks_with_body = parse_tasks_with_body(input_file)
    except Exception as e:
        console.print(f"[red]:cross_mark: Failed to parse {input_file}: {e}[/red]")
        raise typer.Exit(1) from e

    if not tasks_with_body:
        console.print("[yellow]:warning: No tasks found in input file[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]:white_check_mark: Found {len(tasks_with_body)} tasks[/green]")

    # Determine output directory
    if output_dir is None:
        # Default: tasks/ subdirectory next to input file
        output_dir = input_file.parent / "tasks"

    # Create output directory
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[blue]:file_folder: Created directory: {output_dir}[/blue]")
    elif not force:
        # Check if directory is empty
        existing_files = list(output_dir.glob("*.md"))
        if existing_files:
            console.print(
                f"[yellow]:warning: Directory {output_dir} already contains {len(existing_files)} .md files[/yellow]"
            )
            overwrite = typer.confirm("Overwrite existing files?")
            if not overwrite:
                console.print("[red]:cross_mark: Aborted[/red]")
                raise typer.Exit(1)

    # Write each task to individual file
    console.print(f"[blue]:writing_hand: Writing {len(tasks_with_body)} task files...[/blue]")

    for twb in tasks_with_body:
        filename = generate_task_filename(twb.task)
        output_path = output_dir / filename

        write_task_file(twb.task, output_path, body=twb.body)
        console.print(f"  [green]:white_check_mark: {filename}[/green]")

    console.print(f"\n[green]:tada: Successfully split {len(tasks_with_body)} tasks into {output_dir}[/green]")
    console.print(
        f"\n[blue]Next steps:[/blue]\n"
        f"  1. Review generated files in {output_dir}\n"
        f"  2. Fill in Context, Objective, Requirements for each task\n"
        f"  3. Test with: implementation_manager.py status {output_dir.parent} tasks"
    )


if __name__ == "__main__":
    app()
