#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "gitpython>=3.1.45",
# ]
# ///
"""Git change analysis script - extracts commits, diffs, and statistics.

This script analyzes git changes between two references and outputs detailed
information including commits, diffs, and statistics to a specified directory.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
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
from rich.console import Console, RenderableType
from rich.measure import Measurement
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Table

_MIN_NUMSTAT_FIELDS = 2  # Minimum fields in git diff --numstat output (added, deleted, filename)


def get_rendered_width(renderable: RenderableType) -> int:
    """Get actual rendered width of a Rich renderable.

    Handles color codes, Unicode, styling, padding, and borders.
    Works with Panel, Table, or any Rich container.

    Args:
        renderable: Any Rich renderable object

    Returns:
        Actual rendered width in characters
    """
    temp_console = Console(width=99999)
    measurement = Measurement.get(temp_console, temp_console.options, renderable)
    return int(measurement.maximum)


app = typer.Typer(
    name="analyze_git_changes", help="Extract commits, diffs, and statistics from git changes", add_completion=False
)
console = Console(highlight=False)


def open_repo() -> git.Repo:
    """Open the git repository for the current working directory.

    Returns:
        GitPython Repo object

    Raises:
        git.InvalidGitRepositoryError: If not inside a git repository
    """
    return git.Repo(Path.cwd(), search_parent_directories=True)


def find_merge_base(repo: git.Repo, base_ref: str, head_ref: str) -> str:
    """Find the merge base between two git references.

    Args:
        repo: GitPython Repo object
        base_ref: Base reference (e.g., 'main')
        head_ref: Head reference (e.g., 'HEAD')

    Returns:
        Merge base commit hash

    Raises:
        git.GitCommandError: If merge base cannot be found
        ValueError: If merge base result is empty
    """
    bases = repo.merge_base(base_ref, head_ref)
    if not bases:
        msg = f"Could not find merge base between {base_ref} and {head_ref}"
        raise ValueError(msg)
    return str(bases[0])


def get_current_branch(repo: git.Repo) -> str:
    """Get the name of the current git branch.

    Args:
        repo: GitPython Repo object

    Returns:
        Current branch name

    Raises:
        TypeError: If the repo is in detached HEAD state
    """
    return repo.active_branch.name


def extract_commits_oneline(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract one-line commit list.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.log("--oneline", "--no-merges", f"{merge_base}..{head_ref}")
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def extract_commits_detailed(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract detailed commit messages.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.log(
        "--format=%H%n%an%n%ae%n%at%n%s%n%b%n---COMMIT-SEPARATOR---", "--no-merges", f"{merge_base}..{head_ref}"
    )
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def count_commits(repo: git.Repo, merge_base: str, head_ref: str) -> int:
    """Count commits between merge base and head.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference

    Returns:
        Number of commits
    """
    output = repo.git.rev_list("--count", "--no-merges", f"{merge_base}..{head_ref}")
    return int(output.strip())


def extract_diff(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract unified diff of changes.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.diff(f"{merge_base}..{head_ref}")
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def extract_diff_stat(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract diff statistics.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.diff("--stat", f"{merge_base}..{head_ref}")
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def extract_changed_files(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract list of changed files with status.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.diff("--name-status", f"{merge_base}..{head_ref}")
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def extract_numstat(repo: git.Repo, merge_base: str, head_ref: str, output_file: Path) -> None:
    """Extract per-file line change statistics.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference
        output_file: Output file path
    """
    output = repo.git.diff("--numstat", f"{merge_base}..{head_ref}")
    output_file.write_text(output + "\n" if output else "", encoding="utf-8")


def calculate_statistics(repo: git.Repo, merge_base: str, head_ref: str) -> dict[str, int]:
    """Calculate total lines added, deleted, and files changed.

    Args:
        repo: GitPython Repo object
        merge_base: Merge base commit hash
        head_ref: Head reference

    Returns:
        Dictionary with lines_added, lines_deleted, files_changed
    """
    output = repo.git.diff("--numstat", f"{merge_base}..{head_ref}")

    lines_added = 0
    lines_deleted = 0
    files_changed = 0

    for line in output.strip().split("\n"):
        if not line:
            continue

        files_changed += 1
        parts = line.split("\t")
        if len(parts) >= _MIN_NUMSTAT_FIELDS:
            # Handle binary files (shown as '-')
            added = parts[0]
            deleted = parts[1]

            if added != "-":
                lines_added += int(added)
            if deleted != "-":
                lines_deleted += int(deleted)

    return {"lines_added": lines_added, "lines_deleted": lines_deleted, "files_changed": files_changed}


def create_summary_json(
    current_branch: str,
    base_ref: str,
    head_ref: str,
    merge_base: str,
    commit_count: int,
    *,
    stats: dict[str, int],
    output_file: Path,
) -> None:
    """Create machine-readable summary JSON.

    Args:
        current_branch: Current branch name
        base_ref: Base reference
        head_ref: Head reference
        merge_base: Merge base commit hash
        commit_count: Number of commits
        stats: Statistics dictionary
        output_file: Output file path
    """
    summary = {
        "current_branch": current_branch,
        "base_ref": base_ref,
        "head_ref": head_ref,
        "merge_base": merge_base,
        "commit_count": commit_count,
        "files_changed": stats["files_changed"],
        "lines_added": stats["lines_added"],
        "lines_deleted": stats["lines_deleted"],
        "analysis_timestamp": datetime.now(UTC).isoformat(),
    }

    output_file.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def create_summary_text(
    current_branch: str,
    base_ref: str,
    head_ref: str,
    merge_base: str,
    commit_count: int,
    *,
    stats: dict[str, int],
    output_file: Path,
) -> None:
    """Create human-readable summary text.

    Args:
        current_branch: Current branch name
        base_ref: Base reference
        head_ref: Head reference
        merge_base: Merge base commit hash
        commit_count: Number of commits
        stats: Statistics dictionary
        output_file: Output file path
    """
    summary = f"""Git Change Analysis Summary
============================

Branch: {current_branch}
Comparing: {base_ref}..{head_ref}
Merge Base: {merge_base}

Statistics:
- Commits: {commit_count}
- Files Changed: {stats["files_changed"]}
- Lines Added: {stats["lines_added"]}
- Lines Deleted: {stats["lines_deleted"]}

Output Files:
- commits_oneline.txt: One-line commit list
- commits_detailed.txt: Full commit messages
- changes.diff: Unified diff of all changes
- changes_stat.txt: Diffstat summary
- changed_files.txt: List of changed files with status
- changes_numstat.txt: Per-file line changes
- summary.json: Machine-readable summary
"""
    output_file.write_text(summary, encoding="utf-8")


def create_summary_table(
    current_branch: str, base_ref: str, head_ref: str, merge_base: str, commit_count: int, *, stats: dict[str, int]
) -> Table:
    """Create a Rich table for summary display.

    Args:
        current_branch: Current branch name
        base_ref: Base reference
        head_ref: Head reference
        merge_base: Merge base commit hash
        commit_count: Number of commits
        stats: Statistics dictionary

    Returns:
        Rich Table object
    """
    table = Table(title=":bar_chart: Git Change Analysis Summary", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold blue")

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Current Branch", current_branch)
    table.add_row("Comparing", f"{base_ref}..{head_ref}")
    table.add_row("Merge Base", merge_base[:12])
    table.add_row("Commits", str(commit_count))
    table.add_row("Files Changed", str(stats["files_changed"]))
    table.add_row("Lines Added", f"+{stats['lines_added']}")
    table.add_row("Lines Deleted", f"-{stats['lines_deleted']}")

    return table


def _run_analysis(
    repo: git.Repo, base_ref: str, head_ref: str, output_dir: Path, progress: Progress, task: TaskID
) -> tuple[str, str, int, dict[str, int]]:
    """Run all git analysis steps and return collected data.

    Args:
        repo: GitPython Repo object
        base_ref: Base reference
        head_ref: Head reference
        output_dir: Directory to write output files
        progress: Rich Progress instance
        task: Task ID for progress updates

    Returns:
        Tuple of (current_branch, merge_base, commit_count, stats)
    """
    progress.update(task, description="Finding merge base...")
    merge_base = find_merge_base(repo, base_ref, head_ref)
    progress.update(task, description=":white_check_mark: Merge base found")

    progress.update(task, description="Getting current branch...")
    current_branch = get_current_branch(repo)
    progress.update(task, description=":white_check_mark: Current branch identified")

    progress.update(task, description="Creating output directory...")
    output_dir.mkdir(parents=True, exist_ok=True)
    progress.update(task, description=":white_check_mark: Output directory ready")

    progress.update(task, description="Extracting commit history...")
    extract_commits_oneline(repo, merge_base, head_ref, output_dir / "commits_oneline.txt")
    extract_commits_detailed(repo, merge_base, head_ref, output_dir / "commits_detailed.txt")
    commit_count = count_commits(repo, merge_base, head_ref)
    progress.update(task, description=f":white_check_mark: Extracted {commit_count} commits")

    progress.update(task, description="Extracting diffs...")
    extract_diff(repo, merge_base, head_ref, output_dir / "changes.diff")
    extract_diff_stat(repo, merge_base, head_ref, output_dir / "changes_stat.txt")
    extract_changed_files(repo, merge_base, head_ref, output_dir / "changed_files.txt")
    extract_numstat(repo, merge_base, head_ref, output_dir / "changes_numstat.txt")
    progress.update(task, description=":white_check_mark: Diffs extracted")

    progress.update(task, description="Calculating statistics...")
    stats = calculate_statistics(repo, merge_base, head_ref)
    progress.update(task, description=":white_check_mark: Statistics calculated")

    progress.update(task, description="Creating summaries...")
    create_summary_json(
        current_branch,
        base_ref,
        head_ref,
        merge_base,
        commit_count,
        stats=stats,
        output_file=output_dir / "summary.json",
    )
    create_summary_text(
        current_branch,
        base_ref,
        head_ref,
        merge_base,
        commit_count,
        stats=stats,
        output_file=output_dir / "summary.txt",
    )
    progress.update(task, description=":white_check_mark: Summaries created")

    return current_branch, merge_base, commit_count, stats


def _display_results(
    console: Console,
    output_dir: Path,
    current_branch: str,
    base_ref: str,
    head_ref: str,
    merge_base: str,
    commit_count: int,
    stats: dict,
) -> None:
    """Print the success panel and summary table to the console."""
    console.print()
    success_panel = Panel.fit(
        f"Analysis complete. Results written to [cyan]{output_dir.absolute()}[/cyan]",
        title=":white_check_mark: Success",
        border_style="green",
    )
    console.width = get_rendered_width(success_panel)
    console.print(success_panel)
    console.print()

    summary_table = create_summary_table(current_branch, base_ref, head_ref, merge_base, commit_count, stats=stats)
    summary_table.width = get_rendered_width(summary_table)
    console.print(summary_table, crop=False, overflow="ignore")


@app.command()
def analyze(
    base_ref: Annotated[
        str, typer.Argument(help="Base git reference to compare from (e.g., 'main', 'develop')")
    ] = "main",
    head_ref: Annotated[
        str, typer.Argument(help="Head git reference to compare to (e.g., 'HEAD', 'feature-branch')")
    ] = "HEAD",
    output_dir: Annotated[
        Path, typer.Argument(help="Directory to write analysis output files", file_okay=False, dir_okay=True)
    ] = Path(),
) -> None:
    """Analyze git changes and extract commits, diffs, and statistics.

    This command analyzes changes between BASE_REF and HEAD_REF, generating
    detailed reports including commit history, diffs, and change statistics.

    All output files are written to OUTPUT_DIR.
    """
    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Verifying git repository...", total=None)
            repo = open_repo()
            progress.update(task, description=":white_check_mark: Git repository verified")
            current_branch, merge_base, commit_count, stats = _run_analysis(
                repo, base_ref, head_ref, output_dir, progress, task
            )
            progress.remove_task(task)

        _display_results(console, output_dir, current_branch, base_ref, head_ref, merge_base, commit_count, stats)

    except git.InvalidGitRepositoryError as e:
        err_panel = Panel.fit(f"[red]Not a git repository: {e}[/red]", title=":cross_mark: Error", border_style="red")
        console.width = get_rendered_width(err_panel)
        console.print(err_panel)
        raise typer.Exit(code=1) from e
    except git.GitCommandError as e:
        err_panel = Panel.fit(
            f"[red]{e.stderr.strip() if e.stderr else e}[/red]", title=":cross_mark: Error", border_style="red"
        )
        console.width = get_rendered_width(err_panel)
        console.print(err_panel)
        raise typer.Exit(code=1) from e
    except ValueError as e:
        err_panel = Panel.fit(f"[red]{e}[/red]", title=":cross_mark: Error", border_style="red")
        console.width = get_rendered_width(err_panel)
        console.print(err_panel)
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(code=130) from None


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
