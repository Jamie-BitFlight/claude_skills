#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0", "python-gitlab>=4.0.0", "gitpython>=3.1.0"]
# ///
"""GitLab merge request fetcher - extracts MR metadata and changes via python-gitlab.

This script fetches merge request details from GitLab including metadata,
commits, and diffs, outputting structured JSON for further processing.
"""

from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, cast

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import git
import gitlab
import gitlab.exceptions
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if TYPE_CHECKING:
    from gitlab.v4.objects import ProjectMergeRequest


app = typer.Typer(name="fetch_gitlab_mr", help="Fetch GitLab merge request metadata and changes", add_completion=False)
console = Console()


class GitLabFetchError(Exception):
    """Custom exception for GitLab fetch errors."""


@lru_cache(maxsize=1)
def _get_repo() -> git.Repo:
    """Get the git repository for the current directory.

    Returns:
        GitPython Repo object for the current repository.
    """
    return git.Repo(Path.cwd(), search_parent_directories=True)


@lru_cache(maxsize=1)
def _parse_git_origin() -> tuple[str, str]:
    """Parse hostname and project path from git origin URL.

    Returns:
        Tuple of (hostname, project_path).

    Raises:
        GitLabFetchError: If the origin URL cannot be parsed.
    """
    repo = _get_repo()
    url: str = repo.remotes.origin.url
    if match := re.search(r"(?:@|://(?:[^@]+@)?)([^:/]+)[:/](.+?)(?:\.git)?$", url):
        return match.group(1), match.group(2)
    msg = f"Could not parse git origin URL: {url}"
    raise GitLabFetchError(msg)


def _get_gitlab_host() -> str:
    """Get GitLab hostname from git remote origin.

    Returns:
        GitLab hostname (e.g. "gitlab.com").
    """
    return _parse_git_origin()[0]


def _get_project_path() -> str:
    """Get project path from git remote origin.

    Returns:
        Project path (e.g. "mygroup/myproject").
    """
    return _parse_git_origin()[1]


def _resolve_token() -> str | None:
    """Resolve GitLab API token from environment variables.

    Checks in order:
    1. GITLAB_TOKEN environment variable
    2. GITLAB_PRIVATE_TOKEN environment variable

    Returns:
        Token string, or None if no token found.
    """
    return os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_PRIVATE_TOKEN") or None


def get_gitlab_client() -> gitlab.Gitlab:
    """Get authenticated GitLab client.

    Returns:
        Authenticated GitLab client instance.

    Raises:
        GitLabFetchError: If no authentication token is available.
    """
    token = _resolve_token()
    if not token:
        msg = "No GitLab token found. Set GITLAB_TOKEN or GITLAB_PRIVATE_TOKEN env var."
        raise GitLabFetchError(msg)

    return gitlab.Gitlab(f"https://{_get_gitlab_host()}", private_token=token)


def extract_mr_id(mr_identifier: str) -> int:
    """Extract MR IID from URL or direct ID.

    Args:
        mr_identifier: MR URL or ID (e.g., "123", "!123", "https://gitlab.com/org/project/-/merge_requests/123")

    Returns:
        MR IID as integer

    Raises:
        GitLabFetchError: If MR ID cannot be extracted
    """
    # Try URL pattern first
    url_pattern = r"merge_requests/(\d+)"
    url_match = re.search(url_pattern, mr_identifier)
    if url_match:
        return int(url_match.group(1))

    # Try direct ID pattern (with or without !)
    id_pattern = r"!?(\d+)"
    id_match = re.fullmatch(id_pattern, mr_identifier)
    if id_match:
        return int(id_match.group(1))

    msg = f"Could not extract MR ID from '{mr_identifier}'. Provide ID as number (123), !123, or full URL."
    raise GitLabFetchError(msg)


def fetch_mr_metadata(mr_iid: int) -> ProjectMergeRequest:
    """Fetch merge request object using python-gitlab.

    Args:
        mr_iid: MR internal ID (project-scoped)

    Returns:
        GitLab MR object

    Raises:
        GitLabFetchError: If fetch fails
    """
    try:
        gl = get_gitlab_client()
        project = gl.projects.get(_get_project_path())
        return project.mergerequests.get(mr_iid)
    except gitlab.exceptions.GitlabGetError as e:
        msg = f"MR !{mr_iid} not found: {e}"
        raise GitLabFetchError(msg) from e
    except gitlab.exceptions.GitlabAuthenticationError as e:
        msg = f"Authentication failed: {e}"
        raise GitLabFetchError(msg) from e
    except gitlab.exceptions.GitlabError as e:
        msg = f"GitLab API error fetching MR !{mr_iid}: {e}"
        raise GitLabFetchError(msg) from e


def fetch_mr_commits(mr: ProjectMergeRequest) -> list[dict[str, str]]:
    """Fetch commit list for merge request.

    Args:
        mr: GitLab MR object

    Returns:
        List of commit dictionaries with sha, title, and author

    Raises:
        GitLabFetchError: If fetch fails
    """
    try:
        commits = list(mr.commits())
    except gitlab.exceptions.GitlabError as e:
        msg = f"GitLab API error fetching commits for MR !{mr.iid}: {e}"
        raise GitLabFetchError(msg) from e

    return [{"sha": commit.id, "title": commit.title, "author": commit.author_name} for commit in commits]


def fetch_mr_changes(mr: ProjectMergeRequest) -> str:
    """Fetch unified diff for merge request.

    Reconstructs a unified diff string from the MR changes endpoint.

    Args:
        mr: GitLab MR object

    Returns:
        Unified diff as string

    Raises:
        GitLabFetchError: If fetch fails
    """
    try:
        changes_data = mr.changes()
    except gitlab.exceptions.GitlabError as e:
        msg = f"GitLab API error fetching diff for MR !{mr.iid}: {e}"
        raise GitLabFetchError(msg) from e

    if not isinstance(changes_data, dict):
        return ""

    changes: list[dict[str, Any]] = cast("dict[str, Any]", changes_data).get("changes", [])
    if not changes:
        return ""

    diff_parts: list[str] = []
    for change in changes:
        old_path = change.get("old_path", "")
        new_path = change.get("new_path", "")
        diff_text = change.get("diff", "")

        if change.get("new_file"):
            header = f"diff --git a/{old_path} b/{new_path}\nnew file mode {change.get('b_mode', '100644')}\n--- /dev/null\n+++ b/{new_path}\n"
        elif change.get("deleted_file"):
            header = f"diff --git a/{old_path} b/{new_path}\ndeleted file mode {change.get('a_mode', '100644')}\n--- a/{old_path}\n+++ /dev/null\n"
        elif change.get("renamed_file"):
            header = f"diff --git a/{old_path} b/{new_path}\nrename from {old_path}\nrename to {new_path}\n--- a/{old_path}\n+++ b/{new_path}\n"
        else:
            header = f"diff --git a/{old_path} b/{new_path}\n--- a/{old_path}\n+++ b/{new_path}\n"

        diff_parts.append(header + diff_text)

    return "\n".join(diff_parts)


def parse_labels(labels_list: list[str] | None) -> list[str]:
    """Parse and clean labels list.

    Args:
        labels_list: Raw labels list from API

    Returns:
        Cleaned labels list
    """
    if not labels_list:
        return []

    # Filter out empty strings and strip whitespace
    return [label.strip() for label in labels_list if label and label.strip()]


def create_mr_summary(mr: ProjectMergeRequest, commits: list[dict[str, str]]) -> dict[str, Any]:
    """Create structured MR summary from python-gitlab MR object.

    Args:
        mr: GitLab MR object from python-gitlab
        commits: List of commits

    Returns:
        Structured MR summary dictionary
    """
    author = mr.author if isinstance(mr.author, dict) else {}
    return {
        "id": mr.iid,
        "iid": mr.iid,
        "title": mr.title,
        "description": mr.description or "",
        "state": mr.state,
        "source_branch": mr.source_branch,
        "target_branch": mr.target_branch,
        "author": {"username": author.get("username", ""), "name": author.get("name", "")},
        "web_url": mr.web_url,
        "labels": parse_labels(mr.labels),
        "created_at": mr.created_at,
        "updated_at": mr.updated_at,
        "merged_at": getattr(mr, "merged_at", None),
        "commits": commits,
        "commit_count": len(commits),
        "has_conflicts": getattr(mr, "has_conflicts", False),
        "work_in_progress": getattr(mr, "work_in_progress", False),
    }


def create_summary_table(mr_summary: dict[str, Any]) -> Table:
    """Create a Rich table for MR summary display.

    Args:
        mr_summary: MR summary dictionary

    Returns:
        Rich Table object
    """
    table = Table(
        title=f":merge: Merge Request !{mr_summary['iid']}", box=box.MINIMAL_DOUBLE_HEAD, title_style="bold blue"
    )

    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Title", mr_summary["title"])
    table.add_row("State", mr_summary["state"])
    table.add_row("Author", mr_summary["author"]["name"])
    table.add_row("Source Branch", mr_summary["source_branch"])
    table.add_row("Target Branch", mr_summary["target_branch"])
    table.add_row("Commits", str(mr_summary["commit_count"]))

    if mr_summary["labels"]:
        table.add_row("Labels", ", ".join(mr_summary["labels"]))

    if mr_summary["has_conflicts"]:
        table.add_row("Conflicts", ":cross_mark: Has conflicts")

    if mr_summary["work_in_progress"]:
        table.add_row("Status", ":construction: Work in Progress")

    return table


@app.command()
def fetch(
    mr_identifier: Annotated[str, typer.Argument(help="MR ID, URL, or !ID (e.g., '123', '!123', or full GitLab URL)")],
    output_file: Annotated[
        Path, typer.Option("--output", "-o", help="Output file for JSON data", file_okay=True, dir_okay=False)
    ] = Path("mr_data.json"),
    include_diff: Annotated[
        bool, typer.Option("--include-diff/--no-diff", help="Include unified diff in output")
    ] = True,
) -> None:
    """Fetch GitLab merge request metadata and changes.

    This command fetches comprehensive MR data including metadata, commits,
    and optionally the full diff, outputting structured JSON for analysis.
    """
    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            # Extract MR ID
            task = progress.add_task("Parsing MR identifier...", total=None)
            mr_iid = extract_mr_id(mr_identifier)
            progress.update(task, description=f":white_check_mark: MR IID: {mr_iid}")

            # Fetch MR object
            progress.update(task, description="Fetching MR metadata...")
            mr = fetch_mr_metadata(mr_iid)
            progress.update(task, description=":white_check_mark: Metadata fetched")

            # Fetch commits
            progress.update(task, description="Fetching commit list...")
            commits = fetch_mr_commits(mr)
            progress.update(task, description=f":white_check_mark: Fetched {len(commits)} commits")

            # Create summary
            progress.update(task, description="Creating summary...")
            mr_summary = create_mr_summary(mr, commits)
            progress.update(task, description=":white_check_mark: Summary created")

            # Fetch diff if requested
            if include_diff:
                progress.update(task, description="Fetching unified diff...")
                diff = fetch_mr_changes(mr)
                mr_summary["diff"] = diff
                progress.update(task, description=":white_check_mark: Diff fetched")

            # Write output
            progress.update(task, description="Writing output file...")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(mr_summary, indent=2, ensure_ascii=False) + "\n")
            progress.update(task, description=":white_check_mark: Output written")

            progress.remove_task(task)

        # Display summary
        console.print()
        console.print(
            Panel.fit(
                f"MR data written to [cyan]{output_file.absolute()}[/cyan]",
                title=":white_check_mark: Success",
                border_style="green",
            )
        )
        console.print()

        summary_table = create_summary_table(mr_summary)
        console.print(summary_table)

        # Show description if present
        if mr_summary["description"]:
            console.print()
            console.print(Panel(mr_summary["description"], title=":page_facing_up: Description", border_style="blue"))

    except GitLabFetchError as e:
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
