#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "gitpython>=3.1.45",
# ]
# ///
"""Install linting-root-cause-resolver agent to user or project scope.

This script copies the agent file from the skill bundle to the appropriate
.claude/agents/ directory, using content hash comparison to prevent accidental
overwrites of modified agent files.
"""

from __future__ import annotations

import hashlib
import sys
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

import git
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel

# Console setup
console = Console()
error_console = Console(stderr=True, style="bold red")


class InstallScope(StrEnum):
    """Agent installation scope."""

    USER = "user"
    PROJECT = "project"


def get_git_root() -> Path | None:
    """Find the git repository root directory.

    Returns:
        Path to git root directory, or None if not in a git repository
    """
    try:
        repo = git.Repo(search_parent_directories=True)
        git_root = repo.git.rev_parse("--show-toplevel")
        return Path(git_root)
    except git.InvalidGitRepositoryError:
        return None


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file contents.

    Args:
        file_path: Path to file to hash

    Returns:
        Hexadecimal SHA256 hash string

    Raises:
        OSError: If file cannot be read
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def show_diff(existing_file: Path, new_content: str) -> None:
    """Display git-style diff between existing file and new content.

    Args:
        existing_file: Path to existing file
        new_content: New content to compare against
    """
    existing_content = existing_file.read_text(encoding="utf-8")

    console.print("\n[yellow]Differences detected:[/yellow]")
    console.print(f"\n[dim]Existing file:[/dim] {existing_file}")
    console.print("[dim]New content from skill bundle[/dim]\n")

    # Show first 20 lines of each to give context
    existing_lines = existing_content.splitlines()[:20]
    new_lines = new_content.splitlines()[:20]

    console.print("[cyan]Existing (first 20 lines):[/cyan]")
    console.print(Panel("\n".join(existing_lines), border_style="cyan", box=box.ROUNDED))

    console.print("\n[green]New (first 20 lines):[/green]")
    console.print(Panel("\n".join(new_lines), border_style="green", box=box.ROUNDED))


def install_agent(source_file: Path, target_dir: Path, force: bool = False) -> bool:
    """Install agent file to target directory with hash-based change detection.

    Args:
        source_file: Source agent file to copy
        target_dir: Target directory for installation
        force: If True, overwrite existing file even if different

    Returns:
        True if installation succeeded, False if conflicts prevented installation

    Raises:
        OSError: If file operations fail
        ValueError: If source file doesn't exist
    """
    if not source_file.exists():
        msg = f"Source agent file not found: {source_file}"
        raise ValueError(msg)

    target_file = target_dir / source_file.name

    # Create target directory if needed
    target_dir.mkdir(parents=True, exist_ok=True)

    # Read source content
    source_content = source_file.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()

    # Check if target exists
    if target_file.exists():
        target_hash = compute_file_hash(target_file)

        if source_hash == target_hash:
            console.print(
                f":white_check_mark: [green]Agent already installed with identical content:[/green] {target_file}"
            )
            return True

        # Different content - check for force flag
        if not force:
            error_console.print(f":cross_mark: [red]Agent file exists with different content:[/red] {target_file}")
            show_diff(target_file, source_content)
            error_console.print("\n[yellow]To overwrite the existing file, use:[/yellow] --force")
            return False

        console.print(f":warning: [yellow]Overwriting existing agent file:[/yellow] {target_file}")

    # Install the file
    target_file.write_text(source_content, encoding="utf-8")
    console.print(f":white_check_mark: [green]Agent installed successfully:[/green] {target_file}")
    return True


app = typer.Typer(
    name="install_agents",
    help="Install linting-root-cause-resolver agent to user or project scope",
    rich_markup_mode="rich",
)


@app.command()
def main(
    scope: Annotated[
        InstallScope,
        typer.Option(
            help="Installation scope: user (~/.claude/agents/) or project (<git-root>/.claude/agents/)",
            case_sensitive=False,
        ),
    ],
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing agent file even if different")] = False,
) -> None:
    """Install linting-root-cause-resolver agent to specified scope.

    The agent file is copied from the skill bundle to the appropriate .claude/agents/
    directory. Content hash comparison prevents accidental overwrites of modified files.

    Args:
        scope: Installation scope (user or project)
        force: Overwrite existing file even if different

    Raises:
        typer.Exit: On installation failure or validation errors
    """
    # Locate source file relative to script location
    script_dir = Path(__file__).parent
    source_file = script_dir.parent / "agents" / "linting-root-cause-resolver.md"

    if not source_file.exists():
        error_console.print(f":cross_mark: [red]Agent source file not found:[/red] {source_file}")
        error_console.print(
            "\n[yellow]Expected location:[/yellow] holistic-linting/agents/linting-root-cause-resolver.md"
        )
        raise typer.Exit(code=1)

    # Determine target directory
    match scope:
        case InstallScope.USER:
            target_dir = Path.home() / ".claude" / "agents"
            console.print(f"[cyan]Installing to user scope:[/cyan] {target_dir}")

        case InstallScope.PROJECT:
            git_root = get_git_root()
            if git_root is None:
                error_console.print(":cross_mark: [red]Not in a git repository[/red]")
                error_console.print("\n[yellow]Project scope requires a git repository[/yellow]")
                raise typer.Exit(code=1)

            target_dir = git_root / ".claude" / "agents"
            console.print(f"[cyan]Installing to project scope:[/cyan] {target_dir}\n[dim]Git root:[/dim] {git_root}")

    # Install the agent
    try:
        success = install_agent(source_file, target_dir, force=force)
        if not success:
            raise typer.Exit(code=1)
    except (OSError, ValueError) as e:
        error_console.print(f":cross_mark: [red]Installation failed:[/red] {e}")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
