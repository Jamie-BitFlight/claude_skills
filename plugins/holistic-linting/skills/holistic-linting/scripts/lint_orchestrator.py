#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
# ]
# ///
"""Run project linters based on CLAUDE.md LINTERS configuration.

This script reads the LINTERS section from CLAUDE.md to determine which tools
to run, matches file patterns to tools, and executes formatters and linters in
the correct order with aggregated results.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
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
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")


class ExecutionMode(StrEnum):
    """Linting execution mode."""

    ALL = "all"
    FORMAT_ONLY = "format-only"
    LINT_ONLY = "lint-only"


@dataclass
class Tool:
    """Linting tool configuration."""

    name: str
    patterns: list[str]
    is_formatter: bool


@dataclass
class ToolResult:
    """Result of running a tool."""

    tool_name: str
    file_path: Path
    exit_code: int
    stdout: str
    stderr: str
    duration: float


@dataclass
class LintersConfig:
    """Parsed LINTERS configuration."""

    formatters: list[Tool]
    linters: list[Tool]


def parse_linters_section(claude_md: Path) -> LintersConfig:
    """Parse LINTERS section from CLAUDE.md.

    Args:
        claude_md: Path to CLAUDE.md file

    Returns:
        LintersConfig with formatters and linters

    Raises:
        ValueError: If LINTERS section not found or malformed
    """
    if not claude_md.exists():
        msg = f"CLAUDE.md not found: {claude_md}"
        raise ValueError(msg)

    content = claude_md.read_text(encoding="utf-8")

    # Find LINTERS section
    match = re.search(r"^## LINTERS\b.*?(?=^## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not match:
        msg = "LINTERS section not found in CLAUDE.md"
        raise ValueError(msg)

    linters_section = match.group(0)

    # Parse formatters
    formatters: list[Tool] = []
    formatter_match = re.search(r"### Formatters\s*\n(.*?)(?=###|\Z)", linters_section, re.DOTALL)
    if formatter_match:
        for line in formatter_match.group(1).splitlines():
            if tool_info := _parse_tool_line(line):
                name, patterns = tool_info
                formatters.append(Tool(name=name, patterns=patterns, is_formatter=True))

    # Parse linters
    linters: list[Tool] = []
    linter_match = re.search(r"### Static Checking and Linting\s*\n(.*?)(?=###|\Z)", linters_section, re.DOTALL)
    if linter_match:
        for line in linter_match.group(1).splitlines():
            if tool_info := _parse_tool_line(line):
                name, patterns = tool_info
                linters.append(Tool(name=name, patterns=patterns, is_formatter=False))

    return LintersConfig(formatters=formatters, linters=linters)


def _parse_tool_line(line: str) -> tuple[str, list[str]] | None:
    """Parse a tool line from LINTERS section.

    Args:
        line: Line to parse (e.g., "- ruff check [*.py]")

    Returns:
        Tuple of (tool_name, patterns) or None if line doesn't match
    """
    # Match pattern: - tool_name [pattern1, pattern2, ...]
    match = re.match(r"^\s*-\s+([^[]+)\s+\[([^\]]+)\]", line)
    if not match:
        return None

    tool_name = match.group(1).strip()
    patterns_str = match.group(2).strip()

    # Split patterns by comma and strip whitespace
    patterns = [p.strip() for p in patterns_str.split(",")]

    return (tool_name, patterns)


def matches_pattern(file_path: Path, patterns: list[str]) -> bool:
    """Check if file matches any of the glob patterns.

    Args:
        file_path: File to check
        patterns: List of glob patterns (e.g., ["*.py", "*.{ts,tsx}"])

    Returns:
        True if file matches any pattern
    """
    for pattern in patterns:
        # Handle brace expansion patterns like *.{ts,tsx}
        if "{" in pattern:
            # Extract extension group
            brace_match = re.search(r"\{([^}]+)\}", pattern)
            if brace_match:
                extensions = brace_match.group(1).split(",")
                prefix = pattern[: pattern.index("{")]
                for ext in extensions:
                    expanded = prefix + ext.strip()
                    if file_path.match(expanded):
                        return True
        elif file_path.match(pattern):
            return True

    return False


# Tool command mappings
TOOL_COMMANDS: dict[str, list[str]] = {
    "ruff format": ["uv", "run", "ruff", "format"],
    "ruff check": ["uv", "run", "ruff", "check"],
    "pyright": ["uv", "run", "pyright"],
    "bandit": ["uv", "run", "bandit"],
    "prettier": ["npx", "prettier", "--write"],
    "eslint": ["npx", "eslint"],
    "markdownlint": ["npx", "markdownlint-cli2", "--fix"],
    "shellcheck": ["shellcheck"],
    "shfmt": ["shfmt", "-w"],
}


def build_tool_command(tool_name: str, file_path: Path) -> list[str]:
    """Build command to execute a tool on a file.

    Args:
        tool_name: Name of tool to run
        file_path: File to check

    Returns:
        Command as list of strings

    Raises:
        ValueError: If tool is not recognized
    """
    if tool_name not in TOOL_COMMANDS:
        msg = f"Unknown tool: {tool_name}"
        raise ValueError(msg)

    return [*TOOL_COMMANDS[tool_name], str(file_path)]


def run_tool(tool: Tool, file_path: Path) -> ToolResult:
    """Run a tool on a file.

    Args:
        tool: Tool configuration
        file_path: File to check

    Returns:
        ToolResult with execution details

    Raises:
        ValueError: If tool command cannot be built
    """
    cmd = build_tool_command(tool.name, file_path)

    start_time = time.time()
    result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=60)
    duration = time.time() - start_time

    return ToolResult(
        tool_name=tool.name,
        file_path=file_path,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        duration=duration,
    )


def run_tools_on_files(tools: list[Tool], file_paths: list[Path], is_formatter: bool) -> list[ToolResult]:
    """Run tools on files, matching by pattern.

    Args:
        tools: List of tools to run
        file_paths: List of files to check
        is_formatter: True if these are formatters (affects output)

    Returns:
        List of tool results
    """
    results: list[ToolResult] = []

    for file_path in file_paths:
        # Find matching tools
        matching_tools = [t for t in tools if matches_pattern(file_path, t.patterns)]

        for tool in matching_tools:
            try:
                result = run_tool(tool, file_path)
                results.append(result)

                # Show progress
                status = ":white_check_mark:" if result.exit_code == 0 else ":cross_mark:"
                action = "Formatted" if is_formatter else "Checked"
                console.print(f"{status} {action} [cyan]{file_path}[/cyan] with [yellow]{tool.name}[/yellow]")

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
                error_console.print(f":cross_mark: Failed to run {tool.name} on {file_path}: {e}")

    return results


def show_results_summary(formatter_results: list[ToolResult], linter_results: list[ToolResult]) -> None:
    """Display summary of linting results.

    Args:
        formatter_results: Results from formatters
        linter_results: Results from linters
    """
    console.print("\n[bold cyan]Linting Summary[/bold cyan]")

    # Create summary table
    table = Table(box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Category", style="cyan")
    table.add_column("Files", justify="right", style="yellow")
    table.add_column("Tools", justify="right", style="magenta")
    table.add_column("Errors", justify="right", style="red")

    formatter_errors = sum(1 for r in formatter_results if r.exit_code != 0)
    linter_errors = sum(1 for r in linter_results if r.exit_code != 0)

    if formatter_results:
        unique_files = len({r.file_path for r in formatter_results})
        unique_tools = len({r.tool_name for r in formatter_results})
        table.add_row("Formatters", str(unique_files), str(unique_tools), str(formatter_errors))

    if linter_results:
        unique_files = len({r.file_path for r in linter_results})
        unique_tools = len({r.tool_name for r in linter_results})
        table.add_row("Linters", str(unique_files), str(unique_tools), str(linter_errors))

    console.print(table)

    # Show detailed errors
    error_results = [r for r in formatter_results + linter_results if r.exit_code != 0]
    if error_results:
        console.print("\n[bold red]Errors Found:[/bold red]")
        for result in error_results:
            console.print(f"\n[yellow]{result.tool_name}[/yellow] on [cyan]{result.file_path}[/cyan]:")
            if result.stdout:
                console.print(Panel(result.stdout, border_style="red"))
            if result.stderr:
                console.print(Panel(result.stderr, border_style="red"))


app = typer.Typer(
    name="lint_orchestrator", help="Run project linters based on CLAUDE.md configuration", rich_markup_mode="rich"
)


@app.command()
def main(
    paths: Annotated[list[Path], typer.Argument(help="File or directory paths to lint", exists=True)],
    config: Annotated[Path, typer.Option(help="Path to CLAUDE.md file (default: ./CLAUDE.md)")] = Path("CLAUDE.md"),
    format_only: Annotated[bool, typer.Option("--format-only", help="Run only formatters, skip linters")] = False,
    lint_only: Annotated[bool, typer.Option("--lint-only", help="Run only linters, skip formatters")] = False,
) -> None:
    """Run project linters based on CLAUDE.md LINTERS configuration.

    Reads the LINTERS section from CLAUDE.md, matches file patterns to tools,
    and executes formatters and linters in order.

    Args:
        paths: File or directory paths to lint
        config: Path to CLAUDE.md file
        format_only: Run only formatters
        lint_only: Run only linters

    Raises:
        typer.Exit: On configuration errors or linting failures
    """
    if format_only and lint_only:
        error_console.print(":cross_mark: [red]Cannot use both --format-only and --lint-only[/red]")
        raise typer.Exit(code=1)

    # Parse LINTERS configuration
    try:
        linters_config = parse_linters_section(config)
    except ValueError as e:
        error_console.print(f":cross_mark: [red]Configuration error:[/red] {e}")
        error_console.print("\n[yellow]Run:[/yellow] uv run python scripts/discover_linters.py")
        raise typer.Exit(code=1) from e

    # Collect all files to lint
    all_files: list[Path] = []
    for path in paths:
        if path.is_file():
            all_files.append(path)
        elif path.is_dir():
            # Recursively find all files
            all_files.extend(f for f in path.rglob("*") if f.is_file())

    if not all_files:
        error_console.print(":cross_mark: [red]No files found to lint[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Linting {len(all_files)} files with CLAUDE.md configuration[/cyan]\n")

    # Run formatters
    formatter_results: list[ToolResult] = []
    if not lint_only and linters_config.formatters:
        console.print("[bold cyan]Running formatters...[/bold cyan]")
        formatter_results = run_tools_on_files(linters_config.formatters, all_files, is_formatter=True)

    # Run linters
    linter_results: list[ToolResult] = []
    if not format_only and linters_config.linters:
        console.print("\n[bold cyan]Running linters...[/bold cyan]")
        linter_results = run_tools_on_files(linters_config.linters, all_files, is_formatter=False)

    # Show summary
    show_results_summary(formatter_results, linter_results)

    # Exit with appropriate code
    total_errors = sum(1 for r in formatter_results + linter_results if r.exit_code != 0)
    if total_errors > 0:
        error_console.print(f"\n:cross_mark: [red]Found {total_errors} errors[/red]")
        raise typer.Exit(code=1)

    console.print("\n:white_check_mark: [green]All checks passed[/green]")


if __name__ == "__main__":
    app()
