#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0", "rich>=14.0.0"]
# ///
"""MR description formatter - formats AI analysis into markdown description.

This script takes structured JSON analysis from AI and formats it into a
polished merge request description following the template standards.
"""

from __future__ import annotations

import json
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="format_mr_description", help="Format AI analysis into markdown MR description", add_completion=False
)

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# legacy_windows=False forces Rich to use ANSI escape sequences instead of the
# Windows Console API, avoiding charmap encoding failures on legacy consoles.
console = Console(legacy_windows=False)


class FormatError(Exception):
    """Custom exception for formatting errors."""


def load_analysis_file(analysis_file: Path) -> dict[str, Any]:
    """Load and validate analysis JSON file.

    Args:
        analysis_file: Path to analysis JSON file

    Returns:
        Parsed analysis data

    Raises:
        FormatError: If file cannot be loaded or parsed
    """
    if not analysis_file.exists():
        msg = f"Analysis file not found: {analysis_file}"
        raise FormatError(msg)

    try:
        content = analysis_file.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in analysis file: {e}"
        raise FormatError(msg) from e
    except OSError as e:
        msg = f"Could not read analysis file: {e}"
        raise FormatError(msg) from e

    return data


def format_file_list(files: list[str], max_files: int = 5) -> str:
    """Format file list with code ticks and truncation.

    Args:
        files: List of file paths
        max_files: Maximum files to show before truncating

    Returns:
        Formatted file list string
    """
    if not files:
        return ""

    formatted_files = [f"`{file}`" for file in files[:max_files]]

    if len(files) > max_files:
        remaining = len(files) - max_files
        formatted_files.append(f"*...and {remaining} more*")

    return ", ".join(formatted_files)


def format_bug_fixes(bug_fixes: list[dict[str, Any]]) -> str:
    """Format bug fixes section.

    Args:
        bug_fixes: List of bug fix dictionaries

    Returns:
        Formatted markdown string
    """
    if not bug_fixes:
        return ""

    lines = ["### 🐛 Bug Fixes\n"]

    for bug in bug_fixes:
        lines.append(f"- **{bug.get('title', 'Bug Fix')}**")

        if bug.get("description"):
            lines.append(f"  - **Description:** {bug['description']}")

        if bug.get("impact"):
            lines.append(f"  - **Impact:** {bug['impact']}")

        if bug.get("files_affected"):
            files_str = format_file_list(bug["files_affected"])
            if files_str:
                lines.append(f"  - **Files:** {files_str}")

        if bug.get("technical_details"):
            details = bug["technical_details"]
            if isinstance(details, list):
                details = "; ".join(details)
            lines.append(f"  - **Technical Notes:** {details}")

        lines.append("")  # Blank line between items

    return "\n".join(lines)


def format_enhancements(enhancements: list[dict[str, Any]]) -> str:
    """Format enhancements section.

    Args:
        enhancements: List of enhancement dictionaries

    Returns:
        Formatted markdown string
    """
    if not enhancements:
        return ""

    lines = ["### ✨ Enhancements\n"]

    for enhancement in enhancements:
        lines.append(f"- **{enhancement.get('title', 'Enhancement')}**")

        if enhancement.get("description"):
            lines.append(f"  - **Feature:** {enhancement['description']}")

        if enhancement.get("benefits"):
            lines.append(f"  - **Benefits:** {enhancement['benefits']}")

        if enhancement.get("usage"):
            lines.append(f"  - **Usage:** {enhancement['usage']}")

        if enhancement.get("files_affected"):
            files_str = format_file_list(enhancement["files_affected"])
            if files_str:
                lines.append(f"  - **Files:** {files_str}")

        if enhancement.get("technical_details"):
            details = enhancement["technical_details"]
            if isinstance(details, list):
                details = "; ".join(details)
            lines.append(f"  - **Technical Details:** {details}")

        lines.append("")

    return "\n".join(lines)


def format_tech_debt(tech_debt: list[dict[str, Any]]) -> str:
    """Format technical debt section.

    Args:
        tech_debt: List of technical debt dictionaries

    Returns:
        Formatted markdown string
    """
    if not tech_debt:
        return ""

    lines = ["### 🏗️ Technical Debt\n"]

    for item in tech_debt:
        lines.append(f"- **{item.get('title', 'Refactoring')}**")

        if item.get("purpose"):
            lines.append(f"  - **Purpose:** {item['purpose']}")

        if item.get("changes"):
            lines.append(f"  - **Changes:** {item['changes']}")

        if item.get("impact"):
            lines.append(f"  - **Impact:** {item['impact']}")

        if item.get("files_affected"):
            files_str = format_file_list(item["files_affected"])
            if files_str:
                lines.append(f"  - **Files:** {files_str}")

        lines.append("")

    return "\n".join(lines)


def format_documentation(documentation: list[dict[str, Any]]) -> str:
    """Format documentation section.

    Args:
        documentation: List of documentation update dictionaries

    Returns:
        Formatted markdown string
    """
    if not documentation:
        return ""

    lines = ["### 📚 Documentation\n"]

    for doc in documentation:
        title = doc.get("title", "Documentation Update")
        lines.append(f"- **{title}**")

        if doc.get("updates"):
            lines.append(f"  - **Updates:** {doc['updates']}")

        if doc.get("location"):
            location = doc["location"]
            if isinstance(location, list):
                location = ", ".join([f"`{loc}`" for loc in location])
            lines.append(f"  - **Location:** {location}")

        if doc.get("importance"):
            lines.append(f"  - **Importance:** {doc['importance']}")

        lines.append("")

    return "\n".join(lines)


def format_testing(testing: list[dict[str, Any]]) -> str:
    """Format testing section.

    Args:
        testing: List of testing dictionaries

    Returns:
        Formatted markdown string
    """
    if not testing:
        return ""

    lines = ["### 🧪 Testing\n"]

    for test in testing:
        title = test.get("title", "Tests Added")
        lines.append(f"- **{title}**")

        if test.get("coverage"):
            lines.append(f"  - **Coverage:** {test['coverage']}")

        if test.get("test_type"):
            lines.append(f"  - **Type:** {test['test_type']}")

        if test.get("files_affected"):
            files_str = format_file_list(test["files_affected"])
            if files_str:
                lines.append(f"  - **Files:** {files_str}")

        lines.append("")

    return "\n".join(lines)


def format_build_ci(build_ci: list[dict[str, Any]]) -> str:
    """Format build and CI section.

    Args:
        build_ci: List of build/CI dictionaries

    Returns:
        Formatted markdown string
    """
    if not build_ci:
        return ""

    lines = ["### 🔧 Build & CI\n"]

    for item in build_ci:
        lines.append(f"- **{item.get('title', 'Build/CI Change')}**")

        if item.get("changes"):
            lines.append(f"  - **Changes:** {item['changes']}")

        if item.get("impact"):
            lines.append(f"  - **Impact:** {item['impact']}")

        if item.get("files_affected"):
            files_str = format_file_list(item["files_affected"])
            if files_str:
                lines.append(f"  - **Files:** {files_str}")

        lines.append("")

    return "\n".join(lines)


def format_non_functional(non_functional: list[dict[str, Any]]) -> str:
    """Format non-functional changes section.

    Args:
        non_functional: List of non-functional change dictionaries

    Returns:
        Formatted markdown string
    """
    if not non_functional:
        return ""

    lines = ["### 🧹 Non-Functional Changes\n", "Minor repository improvements:\n"]

    for item in non_functional:
        item_type = item.get("type", "misc")
        description = item.get("description", "Minor changes")
        files = item.get("files_affected", [])

        files_str = format_file_list(files, max_files=3)
        if files_str:
            lines.append(f"- **{item_type}**: {description} ({files_str})")
        else:
            lines.append(f"- **{item_type}**: {description}")

    lines.append("")
    return "\n".join(lines)


def format_breaking_changes(breaking_changes: list[dict[str, Any]]) -> str:
    """Format breaking changes section.

    Args:
        breaking_changes: List of breaking change dictionaries

    Returns:
        Formatted markdown string
    """
    if not breaking_changes:
        return ""

    lines = ["### ⚠️ Breaking Changes\n"]

    for change in breaking_changes:
        lines.append(f"- **{change.get('change', 'Breaking Change')}**")

        if change.get("migration"):
            lines.append(f"  - **Migration:** {change['migration']}")

        if change.get("files_affected"):
            files_str = format_file_list(change["files_affected"])
            if files_str:
                lines.append(f"  - **Affected:** {files_str}")

        if change.get("commits"):
            commits = change["commits"]
            if isinstance(commits, list):
                commits = ", ".join([f"`{c[:7]}`" for c in commits])
            lines.append(f"  - **Commits:** {commits}")

        lines.append("")

    return "\n".join(lines)


def format_components(components: list[str]) -> str:
    """Format components affected section.

    Args:
        components: List of component names

    Returns:
        Formatted markdown string
    """
    if not components:
        return ""

    lines = ["### 📦 Components Affected\n"]

    lines.extend(f"- `{component}`" for component in components)

    lines.append("")
    return "\n".join(lines)


def format_statistics(stats: dict[str, Any]) -> str:
    """Format statistics section.

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted markdown string
    """
    lines = ["## Statistics\n"]

    lines.extend((
        f"- **Commits**: {stats.get('commits', 0)}",
        f"- **Files Changed**: {stats.get('files_changed', 0)}",
        f"- **Lines Added**: +{stats.get('lines_added', 0)}",
        f"- **Lines Deleted**: -{stats.get('lines_deleted', 0)}",
        "",
    ))
    return "\n".join(lines)


def generate_mr_description(analysis: dict[str, Any]) -> str:
    """Generate complete MR description from analysis.

    Args:
        analysis: Analysis data dictionary

    Returns:
        Formatted markdown description
    """
    lines = []

    # Title
    title = analysis.get("title", "Merge Request")
    lines.append(f"# {title}\n")

    # Summary
    if analysis.get("summary"):
        lines.extend(("## Summary\n", f"{analysis['summary']}\n"))

    # Statistics
    if analysis.get("statistics"):
        lines.append(format_statistics(analysis["statistics"]))

    # Changes by category
    categories = analysis.get("change_categories", {})

    lines.append("## Changes by Category\n")

    # Bug fixes
    if categories.get("bug_fixes"):
        lines.append(format_bug_fixes(categories["bug_fixes"]))

    # Enhancements
    if categories.get("enhancements"):
        lines.append(format_enhancements(categories["enhancements"]))

    # Technical debt
    if categories.get("tech_debt"):
        lines.append(format_tech_debt(categories["tech_debt"]))

    # Documentation
    if categories.get("documentation"):
        lines.append(format_documentation(categories["documentation"]))

    # Testing
    if categories.get("testing"):
        lines.append(format_testing(categories["testing"]))

    # Build & CI
    if categories.get("build_ci"):
        lines.append(format_build_ci(categories["build_ci"]))

    # Non-functional
    if categories.get("non_functional"):
        lines.append(format_non_functional(categories["non_functional"]))

    # Components affected
    if analysis.get("components_affected"):
        lines.append(format_components(analysis["components_affected"]))

    # Breaking changes
    if analysis.get("breaking_changes"):
        lines.append(format_breaking_changes(analysis["breaking_changes"]))

    # Footer
    lines.extend(("---\n", "*Generated by Claude Code `/create-merge-request-changelog` skill*\n"))

    return "\n".join(lines)


@app.command()
def format_description(
    analysis_file: Annotated[
        Path,
        typer.Argument(
            help="Path to analysis JSON file", exists=True, file_okay=True, dir_okay=False, resolve_path=True
        ),
    ],
    output_file: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file for markdown description", file_okay=True, dir_okay=False),
    ] = Path("mr_description.md"),
    preview: Annotated[
        bool, typer.Option("--preview/--no-preview", help="Display formatted description in terminal")
    ] = True,
) -> None:
    """Format AI analysis into markdown MR description.

    This command takes structured analysis JSON and formats it into a polished
    merge request description following the template standards.
    """
    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            # Load analysis file
            task = progress.add_task("Loading analysis file...", total=None)
            analysis = load_analysis_file(analysis_file)
            progress.update(task, description=":white_check_mark: Analysis loaded")

            # Generate description
            progress.update(task, description="Generating markdown description...")
            description = generate_mr_description(analysis)
            progress.update(task, description=":white_check_mark: Description generated")

            # Write output
            progress.update(task, description="Writing output file...")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(description, encoding="utf-8")
            progress.update(task, description=":white_check_mark: Output written")

            progress.remove_task(task)

        # Display success message
        console.print()
        console.print(
            Panel.fit(
                f"MR description written to [cyan]{output_file.absolute()}[/cyan]",
                title=":white_check_mark: Success",
                border_style="green",
            )
        )

        # Preview if requested
        if preview:
            console.print()
            console.print(
                Panel(
                    Markdown(description),
                    title=":page_facing_up: MR Description Preview",
                    border_style="blue",
                    expand=False,
                )
            )

    except FormatError as e:
        console.print(Panel.fit(f"[red]{e}[/red]", title=":cross_mark: Error", border_style="red"))
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(code=130) from None


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
