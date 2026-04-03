#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "daily-releases-lib",
#   "typer>=0.21.0",
#   "PyGithub>=2.1.1",
#   "python-dotenv>=1.0.0",
# ]
#
# [tool.uv.sources]
# daily-releases-lib = { path = "daily_releases_lib", editable = true }
# ///
"""Delete stale GitHub releases and tags left by prior daily-release script runs.

Removes two categories:
  1. daily-YYYY-MM-DD format releases+tags — old naming convention, superseded
     by v* canonical releases created by publish_daily_release.py.
  2. vYYYY.MM.DD-rN revision tags — orphaned tag refs left when
     publish_daily_release.py moved an existing tag to a revision suffix
     before creating the canonical tag at the correct commit.
     These tags have no GitHub release attached.

All operations use the GitHub REST API via PyGithub — no local git required.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from io import TextIOWrapper

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from typing import TYPE_CHECKING, Annotated

import typer
from daily_releases_lib.github_utils import make_github_client
from github import GithubException
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from github.Repository import Repository

app = typer.Typer(
    name="cleanup_stale_releases",
    help="Delete stale GitHub releases and tags from prior daily-release script runs",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

DEFAULT_REPO = "Jamie-BitFlight/claude_skills"
HTTP_NOT_FOUND = 404
TABLE_EXAMPLE_LIMIT = 3

# Patterns for stale artifacts
DAILY_TAG_RE = re.compile(r"^daily-\d{4}-\d{2}-\d{2}$")
REVISION_TAG_RE = re.compile(r"^v\d{4}\.\d{2}\.\d{2}-r\d+$")


@dataclass
class CleanupResult:
    """Accumulator for cleanup operation statistics.

    Attributes:
        deleted_releases: Number of releases successfully deleted.
        deleted_tags: Number of tags successfully deleted.
        errors: Number of operations that failed with an error.
    """

    deleted_releases: int = field(default=0)
    deleted_tags: int = field(default=0)
    errors: int = field(default=0)


def delete_release_for_tag(gh_repo: Repository, tag: str, *, dry_run: bool) -> bool:
    """Delete a GitHub release for the given tag.

    Args:
        gh_repo: PyGithub Repository object to operate on.
        tag: Tag name identifying the release to delete.
        dry_run: When True, print what would happen without making changes.

    Returns:
        True if the release was deleted (or would be in dry-run mode),
        False if no release exists for the tag.

    Raises:
        GithubException: If the API returns an error other than 404 Not Found.
    """
    try:
        release = gh_repo.get_release(tag)
    except GithubException as exc:
        if exc.status == HTTP_NOT_FOUND:
            return False
        raise
    else:
        if dry_run:
            console.print(f"  [dim]DRY RUN[/dim] would delete release: {tag}")
            return True
        release.delete_release()
        console.print(f"  [red]Deleted release[/red]: {tag}")
        return True


def delete_tag_ref(gh_repo: Repository, tag: str, *, dry_run: bool) -> bool:
    """Delete a git tag ref from the remote repository.

    Args:
        gh_repo: PyGithub Repository object to operate on.
        tag: Tag name to delete.
        dry_run: When True, print what would happen without making changes.

    Returns:
        True if the tag was deleted (or would be in dry-run mode),
        False if the tag ref does not exist.

    Raises:
        GithubException: If the API returns an error other than 404 Not Found.
    """
    try:
        ref = gh_repo.get_git_ref(f"tags/{tag}")
    except GithubException as exc:
        if exc.status == HTTP_NOT_FOUND:
            return False
        raise
    else:
        if dry_run:
            console.print(f"  [dim]DRY RUN[/dim] would delete tag:    {tag}")
            return True
        ref.delete()
        console.print(f"  [red]Deleted tag[/red]:    {tag}")
        return True


def _init_github_client(repo_slug: str) -> Repository:
    """Initialize and return a PyGithub Repository object.

    Reads GITHUB_TOKEN from the environment and validates access
    to the specified repository.

    Args:
        repo_slug: GitHub repository in OWNER/REPO format.

    Returns:
        Authenticated PyGithub Repository object.

    Raises:
        typer.Exit: If GITHUB_TOKEN is missing or the repo is inaccessible.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        err_console.print("[red]GITHUB_TOKEN environment variable not set[/red]")
        raise typer.Exit(code=1)

    gh = make_github_client(token)
    try:
        return gh.get_repo(repo_slug)
    except GithubException as exc:
        err_console.print(f"[red]Cannot access repo '{repo_slug}': {exc}[/red]")
        raise typer.Exit(code=1) from exc


def _collect_stale_tags(gh_repo: Repository) -> tuple[list[str], list[str]]:
    """Fetch all tags and classify them into daily and revision categories.

    Args:
        gh_repo: PyGithub Repository object to query.

    Returns:
        A tuple of (daily_tags, revision_tags), each a sorted list of
        tag names matching the respective stale pattern.
    """
    all_refs = list(gh_repo.get_git_refs())
    all_tags = [r.ref.removeprefix("refs/tags/") for r in all_refs if r.ref.startswith("refs/tags/")]

    daily_tags = sorted(t for t in all_tags if DAILY_TAG_RE.match(t))
    revision_tags = sorted(t for t in all_tags if REVISION_TAG_RE.match(t))
    return daily_tags, revision_tags


def _format_examples(tags: list[str]) -> str:
    """Format a truncated list of tag names for table display.

    Args:
        tags: Non-empty list of tag name strings.

    Returns:
        Comma-separated tag names, truncated with "..." when the list
        exceeds TABLE_EXAMPLE_LIMIT entries.
    """
    examples = ", ".join(tags[:TABLE_EXAMPLE_LIMIT])
    if len(tags) > TABLE_EXAMPLE_LIMIT:
        return examples + "..."
    return examples


def _display_summary_table(daily_tags: list[str], revision_tags: list[str]) -> bool:
    """Display a summary table of stale artifacts found.

    Args:
        daily_tags: List of daily-format tag names.
        revision_tags: List of revision-format tag names.

    Returns:
        True if artifacts were found and displayed, False if nothing
        to clean up.
    """
    if not daily_tags and not revision_tags:
        console.print("[green]Nothing to clean up.[/green]")
        return False

    table = Table(title="Stale artifacts to remove")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Examples")
    if daily_tags:
        table.add_row("daily-* releases+tags", str(len(daily_tags)), _format_examples(daily_tags))
    if revision_tags:
        table.add_row("v*-rN revision tags", str(len(revision_tags)), _format_examples(revision_tags))
    console.print(table)
    return True


def _cleanup_daily_tags(gh_repo: Repository, daily_tags: list[str], *, dry_run: bool, result: CleanupResult) -> None:
    """Delete releases and tags for all daily-format stale entries.

    Args:
        gh_repo: PyGithub Repository object to operate on.
        daily_tags: List of daily-format tag names to clean up.
        dry_run: When True, print what would happen without making changes.
        result: Accumulator for tracking deletion statistics.
    """
    console.print(f"\n[bold]Removing {len(daily_tags)} daily-* releases and tags[/bold]")
    for tag in daily_tags:
        try:
            had_release = delete_release_for_tag(gh_repo, tag, dry_run=dry_run)
            had_tag = delete_tag_ref(gh_repo, tag, dry_run=dry_run)
        except GithubException as exc:
            err_console.print(f"  [red]ERROR[/red] processing {tag}: {exc}")
            result.errors += 1
        else:
            if had_release:
                result.deleted_releases += 1
            if had_tag:
                result.deleted_tags += 1


def _cleanup_revision_tags(
    gh_repo: Repository, revision_tags: list[str], *, dry_run: bool, result: CleanupResult
) -> None:
    """Delete orphaned revision tag refs (no releases attached).

    Args:
        gh_repo: PyGithub Repository object to operate on.
        revision_tags: List of revision-format tag names to clean up.
        dry_run: When True, print what would happen without making changes.
        result: Accumulator for tracking deletion statistics.
    """
    console.print(f"\n[bold]Removing {len(revision_tags)} v*-rN revision tags[/bold]")
    for tag in revision_tags:
        try:
            had_tag = delete_tag_ref(gh_repo, tag, dry_run=dry_run)
        except GithubException as exc:
            err_console.print(f"  [red]ERROR[/red] deleting tag {tag}: {exc}")
            result.errors += 1
        else:
            if had_tag:
                result.deleted_tags += 1


def _print_report(result: CleanupResult) -> None:
    """Print the final cleanup summary.

    Args:
        result: Accumulated cleanup statistics to report.
    """
    console.print(
        f"\n[bold]Done.[/bold] Deleted {result.deleted_releases} releases, "
        f"{result.deleted_tags} tags. Errors: {result.errors}"
    )


@app.command()
def main(
    dry_run: Annotated[bool, typer.Option(help="Print what would happen without making changes")] = False,
    repo_slug: Annotated[str, typer.Option("--repo", "-R", help="GitHub repo OWNER/REPO")] = DEFAULT_REPO,
    skip_daily: Annotated[bool, typer.Option(help="Skip cleanup of daily-* releases")] = False,
    skip_revisions: Annotated[bool, typer.Option(help="Skip cleanup of v*-rN revision tags")] = False,
) -> None:
    """Delete stale GitHub releases and tags from prior daily-release script runs."""
    if dry_run:
        console.print("[yellow]DRY RUN mode — no changes will be made[/yellow]")

    gh_repo = _init_github_client(repo_slug)

    console.print(f"\nFetching all tags from [bold]{repo_slug}[/bold]...")
    daily_tags, revision_tags = _collect_stale_tags(gh_repo)

    has_work = _display_summary_table(daily_tags, revision_tags)
    if not has_work:
        return

    if not dry_run:
        confirm = typer.confirm("\nProceed with deletion?", default=False)
        if not confirm:
            console.print("Aborted.")
            raise typer.Exit(code=0)

    result = CleanupResult()

    if not skip_daily and daily_tags:
        _cleanup_daily_tags(gh_repo, daily_tags, dry_run=dry_run, result=result)

    if not skip_revisions and revision_tags:
        _cleanup_revision_tags(gh_repo, revision_tags, dry_run=dry_run, result=result)

    _print_report(result)


if __name__ == "__main__":
    app()
