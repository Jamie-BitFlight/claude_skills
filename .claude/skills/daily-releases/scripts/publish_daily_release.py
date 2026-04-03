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
"""Publish a daily GitHub release from a pre-rendered markdown file.

Handles git tag creation/movement and GitHub release creation or update.
Designed to be called after analyze_git_changes + AI analysis +
format_mr_description have produced the release notes markdown.

Uses PyGithub exclusively — no local git operations or subprocess calls.
Tag management is performed via the GitHub REST API, which works in proxy
environments where ``git push`` to origin returns HTTP 403.
"""

from __future__ import annotations

import os
import sys
from io import TextIOWrapper
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

import typer
from daily_releases_lib.github_utils import AppExit, get_github_repo, make_github_client
from github import GithubException
from rich.console import Console

if TYPE_CHECKING:
    from github.Repository import Repository

app = typer.Typer(
    name="publish_daily_release",
    help="Publish a daily GitHub release from a pre-rendered markdown file",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

DEFAULT_REPO = "Jamie-BitFlight/claude_skills"

# Bump this to force regeneration of all existing releases on next run.
GENERATOR_VERSION = "1.0"
GENERATOR_MARKER = f"<!-- created-by-release-generator: v{GENERATOR_VERSION} -->"

HTTP_NOT_FOUND = 404


def gh_get_tag_sha(gh_repo: Repository, tag: str) -> str | None:
    """Return the SHA the tag points to on GitHub, or None if the tag does not exist.

    For lightweight tags (the only type this script creates) the SHA is the
    commit SHA directly. Raises for errors other than 404.

    Returns:
        Commit SHA string, or None.
    """
    try:
        return gh_repo.get_git_ref(f"tags/{tag}").object.sha
    except GithubException as e:
        if e.status == HTTP_NOT_FOUND:
            return None
        raise


def gh_release_exists(gh_repo: Repository, tag: str) -> bool:
    """Check if a GitHub release exists for the given tag.

    Returns:
        True if release exists, False otherwise.
    """
    try:
        gh_repo.get_release(tag)
    except GithubException:
        return False
    else:
        return True


def gh_get_next_revision_tag(gh_repo: Repository, base_tag: str) -> str:
    """Get the next available revision tag on GitHub (e.g., v2026.02.21-r2).

    Returns:
        Next available revision tag string.
    """
    revision = 2
    while gh_get_tag_sha(gh_repo, f"{base_tag}-r{revision}") is not None:
        revision += 1
    return f"{base_tag}-r{revision}"


@app.command()
def main(
    release_date: Annotated[str, typer.Option("--date", help="Date in YYYY-MM-DD format")],
    tag: Annotated[str, typer.Option(help="Git tag name (e.g., v2026.02.21)")],
    head_ref: Annotated[str, typer.Option(help="Commit hash the tag should point to")],
    notes_file: Annotated[Path, typer.Option(help="Path to rendered markdown release notes")],
    dry_run: Annotated[bool, typer.Option(help="Print what would happen without making changes")] = False,
    keep_existing_tag: Annotated[
        bool, typer.Option(help="If tag exists, rename it to -r2 instead of moving it")
    ] = True,
    repo_slug: Annotated[str, typer.Option("--repo", "-R", help="GitHub repo OWNER/REPO")] = DEFAULT_REPO,
) -> None:
    """Publish a daily GitHub release.

    Creates or updates a GitHub tag and release for the given date.
    If the tag already exists at a different commit, the old tag is renamed
    to a revision suffix (vYYYY.MM.DD-r2) before the new tag is created.

    All tag operations are performed via the GitHub REST API — no local git
    push required.
    """
    if not notes_file.exists():
        raise AppExit(code=1, message=f"Notes file not found: {notes_file}")

    title = f"Daily Release - {release_date}"
    notes_content = notes_file.read_text(encoding="utf-8").rstrip() + f"\n\n{GENERATOR_MARKER}\n"

    if dry_run:
        console.print("[dim]DRY RUN - would publish:[/dim]")
        console.print(f"  Tag:   {tag} -> {head_ref[:12]}")
        console.print(f"  Title: {title}")
        console.print(f"  Notes: {len(notes_content)} chars from {notes_file}")
        return

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise AppExit(code=1, message="GITHUB_TOKEN environment variable not set")

    gh = make_github_client(token)
    gh_repo = get_github_repo(gh, repo_slug)

    existing_sha = gh_get_tag_sha(gh_repo, tag)
    if existing_sha is not None and keep_existing_tag and existing_sha != head_ref:
        # Delete release before deleting tag — otherwise the release becomes
        # orphaned (draft) and we'd create a duplicate when we recreate the tag.
        if gh_release_exists(gh_repo, tag):
            gh_repo.get_release(tag).delete_release()
            console.print(f"Deleted release for {tag} (will recreate after tag move)")

        # Rename existing tag to revision suffix, then delete the original.
        revision_tag = gh_get_next_revision_tag(gh_repo, tag)
        console.print(f"Moving existing tag {tag} -> {revision_tag}")
        gh_repo.create_git_ref(f"refs/tags/{revision_tag}", existing_sha)
        gh_repo.get_git_ref(f"tags/{tag}").delete()
        existing_sha = None  # tag deleted; will be recreated below

    # Create or update the tag via the GitHub API (no git push required).
    if existing_sha is None:
        gh_repo.create_git_ref(f"refs/tags/{tag}", head_ref)
    else:
        gh_repo.get_git_ref(f"tags/{tag}").edit(head_ref, force=True)
    console.print(f"[green]Tagged {head_ref[:12]} as {tag}[/green]")

    # Re-query live release state after all tag operations to avoid stale snapshot.
    # Handles concurrent runs and interrupted retries: update if release exists,
    # create if not — idempotent regardless of which path ran previously.
    try:
        live_release = gh_repo.get_release(tag)
        live_release.update_release(name=title, message=notes_content, draft=False)
        console.print(f"[green]Updated release {tag}[/green]")
    except GithubException as e:
        if e.status == HTTP_NOT_FOUND:
            gh_repo.create_git_release(tag=tag, name=title, message=notes_content, draft=False)
            console.print(f"[green]Created release {tag}[/green]")
        else:
            raise


if __name__ == "__main__":
    app()
