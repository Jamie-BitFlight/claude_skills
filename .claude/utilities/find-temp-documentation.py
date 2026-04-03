#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-frontmatter>=1.0.0",
#     "typer>=0.12.0",
# ]
# ///
"""Find and manage temporary documentation files.

This tool identifies, validates, and reports on temporary documentation
files created during development tasks. Prevents git pollution from
AI-generated scaffolding documents.

Usage:
    find-temp-documentation.py find [PATH]
    find-temp-documentation.py list [PATH] [--status STATUS]
    find-temp-documentation.py audit [PATH]
    find-temp-documentation.py show FILE
    find-temp-documentation.py cleanup [PATH] [--dry-run]

Examples:
    # Find all temp docs in current directory
    ./find-temp-documentation.py find

    # List only active temp docs
    ./find-temp-documentation.py list --status active

    # Audit for violations
    ./find-temp-documentation.py audit

    # Show details of specific file
    ./find-temp-documentation.py show scripts/pypis_delivery_service/tests/IMPLEMENTATION_BUGS.md

Documentation:
    Based on official documentation:
    - python-frontmatter: https://python-frontmatter.readthedocs.io/
    - typer: https://github.com/fastapi/typer (Annotated syntax for CLI params)
    - rich: https://github.com/textualize/rich (Tables with box.MINIMAL_DOUBLE_HEAD)
"""

from __future__ import annotations

import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Literal, cast

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import frontmatter
import typer
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table

# Type alias for list type annotations (builtin list)
ListType = list

# Module constants
TEMP_DOC_PATTERNS = [
    "*BUGS*.md",
    "*BUG*.md",
    "*INVESTIGATION*.md",
    "*NOTES*.md",
    "*CHECKLIST*.md",
    "*TODO*.md",
    "*FINDINGS*.md",
    "*SUMMARY*.md",
    "*REPORT*.md",
]

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", "docs"}

# Display limits for output formatting
MAX_TASKS_TO_DISPLAY = 10  # Maximum number of tasks to show in summary
CONTENT_PREVIEW_LINES = 5  # Number of content lines to show in preview

# Type aliases for YAML frontmatter values
# Based on .claude/commands/templates/temporary-doc-template.md
DocType = Literal["bugs", "investigation", "checklist", "findings", "summary", "report"]
StatusType = Literal["active", "for-review", "completed", "archived"]
CleanupAction = Literal["delete", "archive", "extract"]

# Initialize Typer app and Rich console
app = typer.Typer(
    name="find-temp-documentation", help="Find and manage temporary documentation files", add_completion=False
)
console = Console()


@dataclass
class TempDoc:
    """Represents a temporary documentation file with validated frontmatter.

    This dataclass holds all required fields from the temporary documentation
    template defined in .claude/commands/templates/temporary-doc-template.md.

    Attributes:
        path: Absolute path to the markdown file
        temporary: Must be True for temporary docs
        type: Document type (bugs, investigation, etc.)
        task: Brief task description or task file path
        agent: Agent name or "orchestrator"
        created: Creation date
        cleanup_trigger: Description of when to delete/archive
        cleanup_action: What to do when cleanup_trigger is met
        status: Current status (active, completed, archived)
        content: Markdown content after frontmatter
    """

    path: Path
    temporary: bool
    type: DocType
    task: str
    agent: str
    created: date
    cleanup_trigger: str
    cleanup_action: CleanupAction
    status: StatusType
    content: str

    @classmethod
    def from_file(cls, path: Path) -> TempDoc | None:
        """Parse markdown file with YAML frontmatter.

        Uses python-frontmatter library to extract and validate YAML metadata
        from markdown files per https://python-frontmatter.readthedocs.io/

        Args:
            path: Path to markdown file to parse

        Returns:
            TempDoc instance if valid temporary doc, None otherwise

        Raises:
            No exceptions raised - returns None for any parsing errors
        """
        try:
            # Load file using frontmatter.load()
            # Reference: https://python-frontmatter.readthedocs.io/
            post = frontmatter.load(str(path))

            # Check if it's a temporary doc
            if not post.get("temporary", False):
                return None

            # Parse created date - handle both string and date objects
            created_value = post.get("created")
            if isinstance(created_value, date):
                created_date = created_value
            elif isinstance(created_value, str):
                created_date = datetime.strptime(created_value, "%Y-%m-%d").replace(tzinfo=UTC).date()
            else:
                return None

            # Validate all required fields exist
            required_fields = [
                "temporary",
                "type",
                "task",
                "agent",
                "created",
                "cleanup_trigger",
                "cleanup_action",
                "status",
            ]

            for field in required_fields:
                if field not in post:
                    return None

            return cls(
                path=path.absolute(),
                temporary=bool(post["temporary"]),
                type=cast("DocType", post["type"]),
                task=str(post["task"]),
                agent=str(post["agent"]),
                created=created_date,
                cleanup_trigger=str(post["cleanup_trigger"]),
                cleanup_action=cast("CleanupAction", post["cleanup_action"]),
                status=cast("StatusType", post["status"]),
                content=str(post.content),
            )
        except (OSError, KeyError, TypeError, ValueError):
            # Return None for file errors, missing keys, type mismatches, or date parsing errors
            return None

    def is_valid(self) -> tuple[bool, list[str]]:
        """Validate all required fields are present and correct type.

        Checks that all 8 required fields from the template are present
        and have valid values according to the Literal types defined.

        Returns:
            Tuple of (is_valid: bool, errors: list[str])
        """
        errors = []

        # Check temporary flag
        if not isinstance(self.temporary, bool) or not self.temporary:
            errors.append("Field 'temporary' must be True")

        # Check type is valid
        valid_types: list[DocType] = ["bugs", "investigation", "checklist", "findings", "summary", "report"]
        if self.type not in valid_types:
            errors.append(f"Field 'type' must be one of: {', '.join(valid_types)}")

        # Check task is non-empty string
        if not self.task or not isinstance(self.task, str):
            errors.append("Field 'task' must be a non-empty string")

        # Check agent is non-empty string
        if not self.agent or not isinstance(self.agent, str):
            errors.append("Field 'agent' must be a non-empty string")

        # Check created is a date
        if not isinstance(self.created, date):
            errors.append("Field 'created' must be a valid date (YYYY-MM-DD)")

        # Check cleanup_trigger is non-empty string
        if not self.cleanup_trigger or not isinstance(self.cleanup_trigger, str):
            errors.append("Field 'cleanup_trigger' must be a non-empty string")

        # Check cleanup_action is valid
        valid_actions: list[CleanupAction] = ["delete", "archive", "extract"]
        if self.cleanup_action not in valid_actions:
            errors.append(f"Field 'cleanup_action' must be one of: {', '.join(valid_actions)}")

        # Check status is valid
        valid_statuses: list[StatusType] = ["active", "for-review", "completed", "archived"]
        if self.status not in valid_statuses:
            errors.append(f"Field 'status' must be one of: {', '.join(valid_statuses)}")

        return (len(errors) == 0, errors)


def _get_table_width(table: Table) -> int:
    """Get the natural width of a table using a temporary wide console.

    This prevents Rich from wrapping table content to fit terminal width.
    Based on Rich table best practices for preventing unwanted wrapping.

    Args:
        table: The Rich table to measure

    Returns:
        The width in characters needed to display the table
    """
    # Create a temporary console with very wide width
    temp_console = Console(width=9999)
    # Measure the table
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


def _find_temp_doc_files(root: Path, recursive: bool = True) -> list[Path]:
    """Find all files matching temporary documentation patterns.

    Searches for markdown files matching the patterns defined in
    .claude/commands/temp-doc, excluding specified directories.

    Args:
        root: Root directory to search
        recursive: Whether to search subdirectories

    Returns:
        List of Path objects for matching files
    """
    matches: list[Path] = []

    if recursive:
        # Use rglob for recursive search
        for pattern in TEMP_DOC_PATTERNS:
            for file_path in root.rglob(pattern):
                # Skip excluded directories
                if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                    continue
                if file_path.is_file():
                    matches.append(file_path)
    else:
        # Use glob for non-recursive search
        for pattern in TEMP_DOC_PATTERNS:
            matches.extend(file_path for file_path in root.glob(pattern) if file_path.is_file())

    return sorted(set(matches))


def _load_temp_docs(files: list[Path]) -> tuple[list[TempDoc], list[Path]]:
    """Load and parse temporary documentation files.

    Args:
        files: List of file paths to parse

    Returns:
        Tuple of (valid_temp_docs, invalid_files)
    """
    valid_docs: list[TempDoc] = []
    invalid_files: list[Path] = []

    for file_path in files:
        doc = TempDoc.from_file(file_path)
        if doc is not None:
            valid_docs.append(doc)
        else:
            invalid_files.append(file_path)

    return valid_docs, invalid_files


def _find_all_temp_docs(path: Path) -> list[TempDoc]:
    """Find and parse all temporary documentation files.

    Args:
        path: Root directory to search

    Returns:
        List of valid TempDoc objects
    """
    files = _find_temp_doc_files(path, recursive=True)
    temp_docs, _ = _load_temp_docs(files)
    return temp_docs


def _print_summary_yaml(docs: list[TempDoc], path: Path) -> None:
    """Print minimal YAML summary statistics.

    Args:
        docs: List of TempDoc objects
        path: Root path for computing relative paths
    """
    # Count by type, status, and task
    type_counts = Counter(doc.type for doc in docs)
    status_counts = Counter(doc.status for doc in docs)
    task_counts = Counter(doc.task for doc in docs)

    console.print("summary:")
    console.print(f"  total: {len(docs)}")

    if type_counts:
        console.print("  by_type:")
        for doc_type, count in sorted(type_counts.items()):
            console.print(f"    {doc_type}: {count}")

    if status_counts:
        console.print("  by_status:")
        for status, count in sorted(status_counts.items()):
            console.print(f"    {status}: {count}")

    if task_counts and len(task_counts) <= MAX_TASKS_TO_DISPLAY:
        console.print("  by_task:")
        for task, count in sorted(task_counts.items()):
            console.print(f"    {task}: {count}")


def _print_full_list_yaml(
    docs: list[TempDoc], path: Path, group_by: Literal["type", "status", "task", "agent"] | None = None
) -> None:
    """Print full YAML list with index numbers.

    Args:
        docs: List of TempDoc objects
        path: Root path for computing relative paths
        group_by: Optional field to group documents by
    """
    # Print summary first
    _print_summary_yaml(docs, path)
    console.print()

    # Group documents if requested
    if group_by:
        groups: dict[str, ListType[tuple[int, TempDoc]]] = {}

        for idx, doc in enumerate(docs):
            key = str(getattr(doc, group_by))
            if key not in groups:
                groups[key] = []
            groups[key].append((idx, doc))

        console.print("documents:")
        for group_key in sorted(groups.keys()):
            console.print(f"  # {group_by}: {group_key}")
            for idx, doc in groups[group_key]:
                _print_doc_yaml(doc, idx, path, indent=2)
    else:
        console.print("documents:")
        for idx, doc in enumerate(docs):
            _print_doc_yaml(doc, idx, path, indent=2)


def _print_doc_yaml(doc: TempDoc, index: int, path: Path, indent: int = 2) -> None:
    """Print a single document as YAML.

    Args:
        doc: TempDoc object to print
        index: Document index number
        path: Root path for computing relative paths
        indent: Number of spaces to indent
    """
    prefix = " " * indent
    relative_path = doc.path.relative_to(path) if doc.path.is_relative_to(path) else doc.path

    # Extract first line of content as description
    content_lines = doc.content.strip().split("\n")
    first_line = content_lines[0] if content_lines else ""
    description = first_line

    console.print(f"{prefix}- index: {index}")
    console.print(f"{prefix}  name: {doc.path.stem}")
    console.print(f"{prefix}  path: {relative_path}")
    console.print(f"{prefix}  type: {doc.type}")
    console.print(f"{prefix}  status: {doc.status}")
    console.print(f"{prefix}  task: {doc.task}")
    console.print(f"{prefix}  agent: {doc.agent}")
    console.print(f"{prefix}  created: {doc.created}")
    if description:
        console.print(f"{prefix}  description: {description}")
    console.print()


def _find_doc_by_identifier(
    docs: list[TempDoc], identifier: str | None = None, index: int | None = None
) -> TempDoc | None:
    """Find a document by name, path, or index.

    Args:
        docs: List of TempDoc objects to search
        identifier: Document name (stem) or path
        index: Document index (0-based)

    Returns:
        TempDoc if found, None otherwise
    """
    # Handle index-based lookup
    if index is not None:
        return docs[index] if 0 <= index < len(docs) else None

    if identifier is None:
        return None

    # Search strategies in priority order: exact path, stem name, partial path
    def matches_path(doc: TempDoc) -> bool:
        return str(doc.path) == identifier or str(doc.path.absolute()) == identifier

    def matches_stem(doc: TempDoc) -> bool:
        return doc.path.stem == identifier

    def matches_partial(doc: TempDoc) -> bool:
        return identifier in str(doc.path)

    for match_fn in (matches_path, matches_stem, matches_partial):
        for doc in docs:
            if match_fn(doc):
                return doc

    return None


def _ensure_wastepaper_gitignored(repo_root: Path) -> None:
    """Ensure .wastepaper/ is in .gitignore.

    Args:
        repo_root: Root directory of the repository
    """
    gitignore = repo_root / ".gitignore"

    if gitignore.exists():
        content = gitignore.read_text()
        if ".wastepaper/" not in content:
            with Path(gitignore).open("a", encoding="utf-8") as f:
                f.write("\n# Temporary documentation cleanup folder\n.wastepaper/\n")
            console.print("[dim]Added .wastepaper/ to .gitignore[/]")
    else:
        # Create .gitignore with .wastepaper/ entry
        gitignore.write_text("# Temporary documentation cleanup folder\n.wastepaper/\n")
        console.print("[dim]Created .gitignore with .wastepaper/ entry[/]")


@app.command()
def scan(
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Root directory to search for temporary documentation files",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    summary: Annotated[bool, typer.Option("--summary", help="Show summary only (minimal tokens)")] = False,
    group_by: Annotated[
        Literal["type", "status", "task", "agent"] | None, typer.Option("--group-by", help="Group documents by field")
    ] = None,
) -> None:
    """Scan temporary documentation with progressive disclosure.

    Examples:
        # Minimal context (50-100 tokens)
        scan --summary

        # Full list with index numbers
        scan

        # Grouped view
        scan --group-by type
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    docs = _find_all_temp_docs(path)

    if not docs:
        console.print("[yellow]No temporary documentation files found.[/]")
        return

    if summary:
        # Output only summary stats
        _print_summary_yaml(docs, path)
    else:
        # Output full list with index numbers
        _print_full_list_yaml(docs, path, group_by)


@app.command()
def find(
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Root directory to search for temporary documentation files",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    recursive: Annotated[
        bool, typer.Option("--recursive/--no-recursive", "-r/-R", help="Search subdirectories recursively")
    ] = True,
) -> None:
    """Find all temporary documentation files (legacy command).

    DEPRECATED: Use 'scan' command instead for better output.

    Searches for markdown files matching temporary documentation patterns
    and identifies which have valid `temporary: true` frontmatter.
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    console.print("[yellow]Note: 'find' command is deprecated. Use 'scan' for YAML output.[/]\n")
    console.print(f"[cyan]Searching for temporary documentation in:[/] {path}\n")

    # Find candidate files
    files = _find_temp_doc_files(path, recursive)

    if not files:
        console.print("[yellow]No files matching temporary documentation patterns found.[/]")
        return

    # Parse files
    temp_docs, invalid_files = _load_temp_docs(files)

    # Display results
    console.print(f"[green]Found {len(files)} candidate files:[/]")
    console.print(f"  [cyan]✓[/] {len(temp_docs)} valid temporary docs")
    console.print(f"  [yellow]✗[/] {len(invalid_files)} files without valid frontmatter\n")

    if temp_docs:
        console.print("[bold]Valid Temporary Documentation:[/]")
        for doc in temp_docs:
            relative_path = doc.path.relative_to(path) if doc.path.is_relative_to(path) else doc.path
            status_color = {"active": "yellow", "for-review": "cyan", "completed": "green", "archived": "blue"}.get(
                doc.status, "white"
            )
            console.print(f"  [{status_color}]{doc.status:10s}[/] {relative_path} ({doc.type})")

    if invalid_files:
        console.print("\n[bold]Files Without Valid Frontmatter:[/]")
        for file_path in invalid_files:
            relative_path = file_path.relative_to(path) if file_path.is_relative_to(path) else file_path
            console.print(f"  [dim]{relative_path}[/]")


@app.command()
def list_docs(
    path: Annotated[
        Path | None,
        typer.Argument(help="Root directory to search", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    ] = None,
    status: Annotated[StatusType | None, typer.Option("--status", "-s", help="Filter by status")] = None,
    doc_type: Annotated[DocType | None, typer.Option("--type", "-t", help="Filter by document type")] = None,
) -> None:
    """List temporary docs with details in a table format.

    Displays temporary documentation in a Rich table with filtering options.
    Uses box.MINIMAL_DOUBLE_HEAD style per Rich best practices.
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    # Find and parse files
    files = _find_temp_doc_files(path, recursive=True)
    temp_docs, _ = _load_temp_docs(files)

    # Apply filters
    if status:
        temp_docs = [doc for doc in temp_docs if doc.status == status]
    if doc_type:
        temp_docs = [doc for doc in temp_docs if doc.type == doc_type]

    if not temp_docs:
        console.print("[yellow]No temporary documentation files found.[/]")
        return

    # Create table using Rich best practices
    # Reference: https://github.com/textualize/rich
    table = Table(
        title=f"Temporary Documentation ({len(temp_docs)} files)", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold blue"
    )

    # Add columns with styling
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    table.add_column("File", style="blue")
    table.add_column("Created", style="green", no_wrap=True)
    table.add_column("Agent", style="yellow", no_wrap=True)
    table.add_column("Cleanup", style="red", no_wrap=True)

    # Add rows
    for doc in temp_docs:
        relative_path = str(doc.path.relative_to(path)) if doc.path.is_relative_to(path) else str(doc.path)
        table.add_row(doc.status, doc.type, relative_path, str(doc.created), doc.agent, doc.cleanup_action)

    # Set table width to natural size to prevent wrapping
    table_width = _get_table_width(table)
    table.width = table_width

    # Print with parameters to prevent wrapping
    console.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


def _check_invalid_frontmatter(invalid_files: list[Path], path: Path, violations: list[str]) -> None:
    """Check for files without valid frontmatter and add to violations."""
    if invalid_files:
        violations.append(f"[red]✗[/] {len(invalid_files)} files missing valid frontmatter")
        for file_path in invalid_files:
            relative_path = file_path.relative_to(path) if file_path.is_relative_to(path) else file_path
            violations.append(f"    {relative_path}")


def _check_completed_docs(temp_docs: list[TempDoc], path: Path, warnings: list[str]) -> None:
    """Check for completed docs that need cleanup and add to warnings."""
    completed_docs = [doc for doc in temp_docs if doc.status == "completed"]
    if completed_docs:
        warnings.append(f"[yellow]![/] {len(completed_docs)} completed docs need cleanup")
        for doc in completed_docs:
            relative_path = doc.path.relative_to(path) if doc.path.is_relative_to(path) else doc.path
            warnings.append(f"    {relative_path} (action: {doc.cleanup_action})")


def _check_invalid_fields(temp_docs: list[TempDoc], path: Path, violations: list[str]) -> None:
    """Check for invalid field values and add to violations."""
    for doc in temp_docs:
        is_valid, errors = doc.is_valid()
        if not is_valid:
            relative_path = doc.path.relative_to(path) if doc.path.is_relative_to(path) else doc.path
            violations.append(f"[red]✗[/] Invalid fields in {relative_path}")
            violations.extend(f"    {error}" for error in errors)


def _print_frontmatter_only(doc: TempDoc) -> None:
    """Print only the frontmatter fields in YAML format."""
    console.print("---")
    console.print(f"temporary: {doc.temporary}")
    console.print(f"type: {doc.type}")
    console.print(f"task: {doc.task}")
    console.print(f"agent: {doc.agent}")
    console.print(f"created: {doc.created}")
    console.print(f"cleanup_trigger: {doc.cleanup_trigger}")
    console.print(f"cleanup_action: {doc.cleanup_action}")
    console.print(f"status: {doc.status}")
    console.print("---")


def _print_full_doc_details(doc: TempDoc, is_valid: bool, errors: list[str]) -> None:
    """Print full document details including frontmatter, validation, and content summary."""
    # Display frontmatter details
    console.print(Panel(f"[bold]{doc.path.name}[/]", subtitle=f"Type: {doc.type}", border_style="cyan"))
    console.print()

    # Create details table
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Path", str(doc.path))
    table.add_row("Temporary", str(doc.temporary))
    table.add_row("Type", doc.type)
    table.add_row("Task", doc.task)
    table.add_row("Agent", doc.agent)
    table.add_row("Created", str(doc.created))
    table.add_row("Cleanup Trigger", doc.cleanup_trigger)
    table.add_row("Cleanup Action", doc.cleanup_action)
    table.add_row("Status", doc.status)

    console.print(table)
    console.print()

    # Show validation status
    if is_valid:
        console.print("[green]✓ Valid frontmatter[/]")
    else:
        console.print("[red]✗ Invalid frontmatter:[/]")
        for error in errors:
            console.print(f"  [red]•[/] {error}")

    # Show content summary
    content_lines = doc.content.strip().split("\n")
    console.print("\n[bold]Content Summary:[/]")
    console.print(f"  Lines: {len(content_lines)}")
    console.print(f"  Characters: {len(doc.content)}")

    # Show first few lines
    if content_lines:
        console.print("\n[bold]First Few Lines:[/]")
        for line in content_lines[:CONTENT_PREVIEW_LINES]:
            console.print(f"  [dim]{line}[/]")
        if len(content_lines) > CONTENT_PREVIEW_LINES:
            remaining = len(content_lines) - CONTENT_PREVIEW_LINES
            console.print(f"  [dim]... and {remaining} more lines[/]")


@app.command()
def audit(
    path: Annotated[
        Path | None,
        typer.Argument(help="Root directory to audit", exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    ] = None,
) -> None:
    """Audit temporary docs for violations.

    Checks for:
    - Files matching patterns but missing frontmatter
    - Files with invalid frontmatter fields
    - Completed docs that should be cleaned up
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    console.print(Panel("[bold cyan]Auditing Temporary Documentation[/]", border_style="cyan"))
    console.print()

    # Find and parse files
    files = _find_temp_doc_files(path, recursive=True)
    temp_docs, invalid_files = _load_temp_docs(files)

    # Track violations
    violations: list[str] = []
    warnings: list[str] = []

    # Run checks
    _check_invalid_frontmatter(invalid_files, path, violations)
    _check_completed_docs(temp_docs, path, warnings)
    _check_invalid_fields(temp_docs, path, violations)

    # Display results
    if not violations and not warnings:
        console.print("[green]✓ No violations found! All temporary docs are valid.[/]")
        console.print(f"\n[dim]Found {len(temp_docs)} active temporary documentation files.[/]")
    else:
        if violations:
            console.print("[bold red]Violations:[/]\n")
            for violation in violations:
                console.print(violation)
            console.print()

        if warnings:
            console.print("[bold yellow]Warnings:[/]\n")
            for warning in warnings:
                console.print(warning)
            console.print()

        # Exit with error code if violations found
        if violations:
            sys.exit(1)


@app.command()
def show(
    identifier: Annotated[str | None, typer.Argument(help="Document name or path")] = None,
    index: Annotated[int | None, typer.Option("--index", help="Document index (0-based)")] = None,
    frontmatter: Annotated[bool, typer.Option("--frontmatter", help="Show frontmatter only")] = False,
    path: Annotated[
        Path | None,
        typer.Option(
            "--path", help="Root directory to search", exists=True, file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = None,
) -> None:
    """Show specific document by name, path, or index.

    Examples:
        # Peek at frontmatter (100-150 tokens)
        show --index 0 --frontmatter
        show implementation-bugs-pypis-config --frontmatter

        # Full content with frontmatter
        show --index 0
        show scripts/pypis_delivery_service/tests/IMPLEMENTATION_BUGS.md
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    # Find all docs to enable index lookup
    docs = _find_all_temp_docs(path)

    if not docs:
        console.print("[yellow]No temporary documentation files found.[/]")
        sys.exit(1)

    # Find the document
    doc = _find_doc_by_identifier(docs, identifier, index)

    if doc is None:
        if index is not None:
            console.print(f"[red]Error:[/] No document at index {index}")
            console.print(f"[dim]Valid range: 0-{len(docs) - 1}[/]")
        else:
            console.print(f"[red]Error:[/] Document not found: {identifier}")
        sys.exit(1)

    # Validate fields
    is_valid, errors = doc.is_valid()

    # Display based on mode
    if frontmatter:
        _print_frontmatter_only(doc)
    else:
        _print_full_doc_details(doc, is_valid, errors)


@app.command()
def cleanup(
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Root directory to search for completed temp docs",
            exists=True,
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = None,
    task_file: Annotated[str | None, typer.Option("--task-file", help="Clean only this task's docs")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run/--no-dry-run", help="Show what would be moved without moving")
    ] = True,
) -> None:
    """Move non-active temporary docs to .wastepaper/ folder.

    Safety: Files are MOVED to .wastepaper/, not deleted.

    Cleanup criteria:
        - status: completed or for-review
        - status: archived

    Active docs (status: active) are NEVER moved.
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    # Find and parse files
    files = _find_temp_doc_files(path, recursive=True)
    temp_docs, _ = _load_temp_docs(files)

    # Filter for cleanup candidates: completed, for-review, or archived
    cleanup_docs = [doc for doc in temp_docs if doc.status in {"completed", "for-review", "archived"}]

    # Filter by task if specified
    if task_file:
        cleanup_docs = [doc for doc in cleanup_docs if task_file in doc.task]

    if not cleanup_docs:
        console.print("[green]✓ No temporary docs to clean up.[/]")
        return

    # Ensure .wastepaper/ is gitignored
    _ensure_wastepaper_gitignored(path)

    # Create .wastepaper/ directory
    wastepaper_dir = path / ".wastepaper"

    console.print(Panel(f"[bold]Found {len(cleanup_docs)} temporary documents to move[/]", border_style="yellow"))
    console.print()

    mode = "[yellow]DRY RUN[/]" if dry_run else "[red]EXECUTING[/]"
    console.print(f"Mode: {mode}\n")

    moved_count = 0

    for doc in cleanup_docs:
        relative_path = doc.path.relative_to(path) if doc.path.is_relative_to(path) else doc.path

        console.print(f"[bold cyan]File:[/] {relative_path}")
        console.print(f"[dim]Status:[/] {doc.status}")
        console.print(f"[dim]Type:[/] {doc.type}")
        console.print(f"[dim]Task:[/] {doc.task}")

        if not dry_run:
            # Create wastepaper directory if it doesn't exist
            wastepaper_dir.mkdir(exist_ok=True)

            # Compute destination path preserving structure
            dest_path = wastepaper_dir / relative_path

            # Create parent directories in wastepaper
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Move the file
            shutil.move(str(doc.path), str(dest_path))

            console.print(f"[green]→ Moved to:[/] .wastepaper/{relative_path}")
            moved_count += 1
        else:
            console.print(f"[dim]→ Would move to:[/] .wastepaper/{relative_path}")

        console.print()

    if dry_run:
        console.print("[yellow]This was a dry run. Use --no-dry-run to move files.[/]")
    else:
        console.print(f"[green]✓ Moved {moved_count} files to .wastepaper/[/]")
        console.print("[dim]Files can be recovered from .wastepaper/ if needed.[/]")


@app.command()
def state(
    identifier: Annotated[str, typer.Argument(help="Document name or path")],
    new_status: Annotated[StatusType | None, typer.Argument(help="New status value")] = None,
    index: Annotated[int | None, typer.Option("--index", help="Use index instead of name/path")] = None,
    path: Annotated[
        Path | None,
        typer.Option(
            "--path", help="Root directory to search", exists=True, file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = None,
) -> None:
    """Get or set document status efficiently.

    Examples:
        # Get current status
        state implementation-bugs-pypis-config

        # Set status
        state implementation-bugs-pypis-config completed
        state --index 0 for-review
    """
    # Handle default path
    if path is None:
        path = Path.cwd()

    # Find all docs to enable index lookup
    docs = _find_all_temp_docs(path)

    if not docs:
        console.print("[yellow]No temporary documentation files found.[/]")
        sys.exit(1)

    # Find the document
    doc = _find_doc_by_identifier(docs, identifier if index is None else None, index)

    if doc is None:
        if index is not None:
            console.print(f"[red]Error:[/] No document at index {index}")
            console.print(f"[dim]Valid range: 0-{len(docs) - 1}[/]")
        else:
            console.print(f"[red]Error:[/] Document not found: {identifier}")
        sys.exit(1)

    if new_status is None:
        # Get current status
        console.print(f"[bold]Document:[/] {doc.path.name}")
        console.print(f"[bold]Status:[/] {doc.status}")
        return

    # Set new status
    console.print(f"[bold]Document:[/] {doc.path.name}")
    console.print(f"[dim]Current status:[/] {doc.status}")
    console.print(f"[dim]New status:[/] {new_status}")

    # Load frontmatter and update status field
    post = frontmatter.load(str(doc.path))
    post["status"] = new_status

    # Write back to file
    Path(doc.path).write_text(frontmatter.dumps(post), encoding="utf-8")

    console.print(f"[green]✓ Status updated to:[/] {new_status}")


if __name__ == "__main__":
    app()
