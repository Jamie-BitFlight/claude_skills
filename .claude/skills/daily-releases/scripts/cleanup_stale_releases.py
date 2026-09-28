#!/usr/bin/env -S uv run --quiet --script
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
#
# [tool.ty.environment]
# extra-paths = ["./daily_releases_lib"]
# ///
"""Preview or delete stale GitHub releases and tags from prior daily releases.

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

import json
import os
import re
from typing import TYPE_CHECKING, Annotated, TypedDict

from dotenv import load_dotenv

load_dotenv()

import typer
from daily_releases_lib.github_utils import make_github_client
from github import GithubException

if TYPE_CHECKING:
    from github.Repository import Repository

app = typer.Typer(
    name="cleanup_stale_releases",
    help="Preview or delete stale GitHub releases and tags from prior daily-release script runs",
    add_completion=False,
    context_settings={"terminal_width": 800},
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)

DEFAULT_REPO = "Jamie-BitFlight/claude_skills"
HTTP_NOT_FOUND = 404

# Patterns for stale artifacts
DAILY_TAG_RE = re.compile(r"^daily-\d{4}-\d{2}-\d{2}$")
REVISION_TAG_RE = re.compile(r"^v\d{4}\.\d{2}\.\d{2}-r\d+$")


class CleanupAction(TypedDict):
    """One independently observed release or tag operation."""

    category: str
    resource: str
    name: str
    operation: str
    status: str
    error: str | None


class CleanupPayload(TypedDict):
    """Complete machine-readable cleanup result."""

    mode: str
    repository: str
    selected_categories: dict[str, bool]
    actions: list[CleanupAction]
    summaries: dict[str, object]
    fatal_error: str | None


def _action(category: str, resource: str, name: str, status: str, error: str | None = None) -> CleanupAction:
    """Build one complete action record.

    Returns:
        The action record.
    """
    return {
        "category": category,
        "resource": resource,
        "name": name,
        "operation": "delete",
        "status": status,
        "error": error,
    }


def _operate_release(gh_repo: Repository, tag: str, *, apply: bool) -> CleanupAction:
    """Observe or delete one release without affecting its tag operation.

    Returns:
        The independently observed release action.
    """
    try:
        release = gh_repo.get_release(tag)
        if apply:
            release.delete_release()
    except GithubException as exc:
        status = "not_found" if exc.status == HTTP_NOT_FOUND else "error"
        return _action("daily", "release", tag, status, None if status == "not_found" else str(exc))
    return _action("daily", "release", tag, "deleted" if apply else "would_delete")


def _operate_tag(gh_repo: Repository, tag: str, category: str, *, apply: bool) -> CleanupAction:
    """Observe or delete one tag independently.

    Returns:
        The independently observed tag action.
    """
    try:
        ref = gh_repo.get_git_ref(f"tags/{tag}")
        if apply:
            ref.delete()
    except GithubException as exc:
        status = "not_found" if exc.status == HTTP_NOT_FOUND else "error"
        return _action(category, "tag", tag, status, None if status == "not_found" else str(exc))
    return _action(category, "tag", tag, "deleted" if apply else "would_delete")


def _init_github_client(repo_slug: str) -> Repository:
    """Initialize and return a PyGithub Repository object.

    Reads GITHUB_TOKEN from the environment and validates access
    to the specified repository.

    Args:
        repo_slug: GitHub repository in OWNER/REPO format.

    Returns:
        Authenticated PyGithub Repository object.

    Raises:
        RuntimeError: If GITHUB_TOKEN is missing.
        GithubException: If the repository is inaccessible.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable not set")

    gh = make_github_client(token)
    return gh.get_repo(repo_slug)


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


def _summaries(actions: list[CleanupAction]) -> dict[str, object]:
    """Count every status overall and per resource.

    Returns:
        Complete counters for all action statuses.
    """
    statuses = ("would_delete", "deleted", "not_found", "error", "not_attempted")
    return {
        "total": len(actions),
        "by_status": {status: sum(action["status"] == status for action in actions) for status in statuses},
        "by_resource": {
            resource: {
                status: sum(action["resource"] == resource and action["status"] == status for action in actions)
                for status in statuses
            }
            for resource in ("release", "tag")
        },
    }


def _emit(payload: CleanupPayload) -> None:
    """Emit the single compact machine-readable result."""
    payload["summaries"] = _summaries(payload["actions"])
    typer.echo(json.dumps(payload, separators=(",", ":")))


@app.command()
def main(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without making changes")] = False,
    apply: Annotated[bool, typer.Option("--apply", help="Delete the selected stale resources")] = False,
    repo_slug: Annotated[str, typer.Option("--repo", "-R", help="GitHub repo OWNER/REPO")] = DEFAULT_REPO,
    skip_daily: Annotated[bool, typer.Option(help="Skip cleanup of daily-* releases")] = False,
    skip_revisions: Annotated[bool, typer.Option(help="Skip cleanup of v*-rN revision tags")] = False,
) -> None:
    """Preview by default; delete only when ``--apply`` is explicit."""
    payload: CleanupPayload = {
        "mode": "apply" if apply else "preview",
        "repository": repo_slug,
        "selected_categories": {"daily": not skip_daily, "revisions": not skip_revisions},
        "actions": [],
        "summaries": {},
        "fatal_error": None,
    }
    if apply and dry_run:
        payload["mode"] = "invalid"
        payload["fatal_error"] = "--apply and --dry-run are mutually exclusive"
        _emit(payload)
        raise typer.Exit(code=2)

    try:
        gh_repo = _init_github_client(repo_slug)
        daily_tags, revision_tags = _collect_stale_tags(gh_repo)
    except Exception as exc:
        payload["fatal_error"] = str(exc)
        _emit(payload)
        raise typer.Exit(code=1) from exc

    if not skip_daily:
        for tag in daily_tags:
            payload["actions"].append(_operate_release(gh_repo, tag, apply=apply))
            payload["actions"].append(_operate_tag(gh_repo, tag, "daily", apply=apply))
    if not skip_revisions:
        for tag in revision_tags:
            payload["actions"].append(_operate_tag(gh_repo, tag, "revision", apply=apply))

    _emit(payload)
    if any(action["status"] in {"error", "not_attempted"} for action in payload["actions"]):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
