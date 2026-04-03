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
"""List daily commit ranges for the daily releases pipeline.

Outputs a JSON array of days with base_ref/head_ref pairs, suitable for
driving analyze_git_changes.py and publish_daily_release.py.

Uses PyGithub for release/tag operations and the GitHub GraphQL API for
commit history — no local git repository required.
"""

from __future__ import annotations

import json
import sys
from io import TextIOWrapper

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Annotated

import typer
from daily_releases_lib.github_utils import AppExit, get_github_repo, get_ssl_verify, graphql, make_github_client
from github import GithubException
from rich.console import Console

if TYPE_CHECKING:
    from github.Repository import Repository

EMPTY_TREE_SHA: str = os.environ.get("EMPTY_TREE_SHA") or "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
DEFAULT_REPO: str = os.environ.get("DEFAULT_REPO") or "Jamie-BitFlight/claude_skills"
_MIN_PARENT_PARTS = 2

# Must match GENERATOR_VERSION in publish_daily_release.py.
# Bump both to force regeneration of all existing releases on next run.
GENERATOR_VERSION: str = os.environ.get("GENERATOR_VERSION") or "1.0"
# GitHub's API returns the Markdown-escaped form "<\!--" instead of "<!--" for HTML
# comments in release bodies.  Match both to avoid false-positive needs_update.
_MARKER_RE = re.compile(r"<\\?!-- created-by-release-generator: v([\d.]+) -->")

app = typer.Typer(
    name="list_daily_ranges", help="List daily commit ranges for release pipeline processing", add_completion=False
)
console = Console()
err_console = Console(stderr=True)


def get_release_generator_version(gh_repo: Repository, tag: str) -> str | None:
    """Return the generator version embedded in an existing release body, or None.

    Returns None if the release does not exist, the body is missing, or the
    marker comment is not present.
    """
    try:
        release = gh_repo.get_release(tag)
    except GithubException:
        return None
    body = release.body or ""
    match = _MARKER_RE.search(body)
    return match.group(1) if match else None


def tag_exists(gh_repo: Repository, tag: str) -> bool:
    """Check if a git tag exists on GitHub.

    Returns:
        True if tag exists, False otherwise.
    """
    try:
        gh_repo.get_git_ref(f"tags/{tag}")
    except GithubException:
        return False
    else:
        return True


def get_tag_commit(gh_repo: Repository, tag: str) -> str | None:
    """Get the commit SHA a tag points to on GitHub (dereferenced to commit).

    Handles both lightweight tags (pointing directly to a commit) and annotated
    tags (pointing to a tag object which in turn points to a commit).

    Returns:
        Commit hexsha, or None if tag does not exist.
    """
    try:
        ref = gh_repo.get_git_ref(f"tags/{tag}")
        obj = ref.object
        # Annotated tags have type "tag" and must be dereferenced to a commit.
        if obj.type == "tag":
            tag_obj = gh_repo.get_git_tag(obj.sha)
            return tag_obj.object.sha
    except GithubException:
        return None
    else:
        return obj.sha  # lightweight tag points directly to a commit


# ---------------------------------------------------------------------------
# GitHub GraphQL helpers
# ---------------------------------------------------------------------------

_BRANCH_HISTORY_QUERY = """
query BranchHistory($owner: String!, $repo: String!, $qualifiedName: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    ref(qualifiedName: $qualifiedName) {
      target {
        ... on Commit {
          history(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              oid
              committedDate
              parents { totalCount }
            }
          }
        }
      }
    }
  }
}
"""


def _branch_to_qualified_ref(branch: str) -> str:
    """Convert a local-style branch name to a GitHub qualified ref name.

    Examples:
        ``origin/main`` → ``refs/heads/main``
        ``main`` → ``refs/heads/main``
        ``refs/heads/main`` → ``refs/heads/main``

    Args:
        branch: Branch name, possibly with a remote prefix (e.g., ``origin/``).

    Returns:
        GitHub qualified ref string suitable for the GraphQL ``ref(qualifiedName:)`` field.
    """
    if branch.startswith("refs/"):
        return branch
    # Strip remote prefix (e.g., "origin/main" → "main")
    if "/" in branch:
        _, branch = branch.split("/", 1)
    return f"refs/heads/{branch}"


def _fetch_all_commits_graphql(
    token: str, owner: str, repo_name: str, qualified_ref: str, *, verify: bool | str, base_url: str
) -> list[dict]:
    """Fetch the full commit history of a branch via GitHub GraphQL.

    Paginates through all pages using cursor-based pagination, returning
    commits in newest-first order (same order as the GitHub API returns them).

    Args:
        token: GitHub token.
        owner: Repository owner login.
        repo_name: Repository name (without owner prefix).
        qualified_ref: Fully qualified ref name (e.g. ``refs/heads/main``).
        verify: SSL verification setting — False, True, or CA bundle path.
        base_url: GitHub API base URL.

    Returns:
        List of commit node dicts with ``oid``, ``committedDate``, and
        ``parents.totalCount`` fields, newest-first.

    Raises:
        AppExit: If the ref is not found or GraphQL returns an error.
    """
    commits: list[dict] = []
    after: str | None = None
    while True:
        data = graphql(
            token,
            _BRANCH_HISTORY_QUERY,
            {"owner": owner, "repo": repo_name, "qualifiedName": qualified_ref, "after": after},
            verify=verify,
            base_url=base_url,
        )
        ref_node = data.get("repository", {}).get("ref")
        if ref_node is None:
            raise AppExit(code=1, message=f"Branch ref '{qualified_ref}' not found in repository")
        history = ref_node["target"]["history"]
        commits.extend(history["nodes"])
        page_info = history["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]
    return commits  # newest-first


def get_commits_by_day(
    token: str, repo_slug: str, branch: str, *, verify: bool | str, base_url: str
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Fetch branch commits via GraphQL and group them by UTC date.

    Args:
        token: GitHub personal access token.
        repo_slug: Repository in ``OWNER/REPO`` format.
        branch: Branch name (local format, e.g. ``origin/main`` or ``main``).
        verify: SSL verification setting — False, True, or CA bundle path.
        base_url: GitHub API base URL.

    Returns:
        A tuple ``(all_by_day, non_merge_by_day)`` where each value is a dict
        mapping ``YYYY-MM-DD`` to a list of commit SHAs in oldest-first order.
        ``non_merge_by_day`` excludes merge commits (commits with >1 parent).
    """
    owner, repo_name = repo_slug.split("/", 1)
    qualified_ref = _branch_to_qualified_ref(branch)
    err_console.print(f"[dim]Fetching commit history for {qualified_ref} via GraphQL...[/dim]")

    raw_commits = _fetch_all_commits_graphql(token, owner, repo_name, qualified_ref, verify=verify, base_url=base_url)
    err_console.print(f"[dim]  {len(raw_commits)} commits fetched[/dim]")

    all_by_day: dict[str, list[str]] = {}
    non_merge_by_day: dict[str, list[str]] = {}

    for node in raw_commits:  # newest-first from GraphQL
        oid: str = node["oid"]
        # committedDate from GraphQL is ISO 8601 with timezone offset or trailing "Z"
        committed_dt = datetime.fromisoformat(node["committedDate"])
        day = committed_dt.astimezone(UTC).strftime("%Y-%m-%d")

        all_by_day.setdefault(day, []).append(oid)

        parent_count: int = node["parents"]["totalCount"]
        if parent_count <= 1:  # 0 = root commit, 1 = regular commit; >1 = merge commit
            non_merge_by_day.setdefault(day, []).append(oid)

    # GraphQL returns newest-first; reverse each day's list to oldest-first
    all_by_day = {d: list(reversed(shas)) for d, shas in all_by_day.items()}
    non_merge_by_day = {d: list(reversed(shas)) for d, shas in non_merge_by_day.items()}

    return all_by_day, non_merge_by_day


def get_day_base_ref(all_commits_by_day: dict[str, list[str]], day_str: str) -> str:
    """Return the last commit on main strictly before ``day_str``.

    Iterates sorted day keys and returns the last commit SHA of the most
    recent day that precedes ``day_str``.

    Returns:
        Commit SHA, or EMPTY_TREE_SHA if no commits precede ``day_str``.
    """
    base_ref = EMPTY_TREE_SHA
    for day in sorted(all_commits_by_day):
        if day >= day_str:
            break
        base_ref = all_commits_by_day[day][-1]  # last commit of that day
    return base_ref


@dataclass
class DayRange:
    """Commit range data for a single calendar day."""

    date: str
    tag: str
    base_ref: str
    head_ref: str
    commit_count: int
    release_exists: bool
    needs_update: bool


def _check_day_release_status(gh_repo: Repository, tag: str, newest_commit: str) -> tuple[bool, bool]:
    """Return ``(release_exists, needs_update)`` for the given tag and commit.

    Checks whether the tag exists, whether its commit has changed, and whether
    the release was generated by an older version of the generator.
    """
    exists = tag_exists(gh_repo, tag)
    if not exists:
        return False, False
    current_tag_commit = get_tag_commit(gh_repo, tag)
    commit_changed = current_tag_commit != newest_commit
    if commit_changed:
        return True, True
    version_outdated = get_release_generator_version(gh_repo, tag) != GENERATOR_VERSION
    return True, version_outdated


def _build_day_range(
    day_str: str, all_by_day: dict[str, list[str]], non_merge_by_day: dict[str, list[str]], gh_repo: Repository
) -> DayRange:
    """Build a DayRange entry for a single calendar day.

    Extracted to keep ``main()`` under the local-variable limit (PLR0914).

    Returns:
        Populated DayRange dataclass for ``day_str``.
    """
    non_merge_commits = non_merge_by_day[day_str]
    head_ref = all_by_day.get(day_str, non_merge_commits)[-1]
    tag = f"v{day_str.replace('-', '.')}"
    exists, needs_update = _check_day_release_status(gh_repo, tag, head_ref)
    return DayRange(
        date=day_str,
        tag=tag,
        base_ref=get_day_base_ref(all_by_day, day_str),
        head_ref=head_ref,
        commit_count=len(non_merge_commits),
        release_exists=exists,
        needs_update=needs_update,
    )


@app.command()
def main(
    branch: Annotated[str, typer.Option(help="Git branch to read commits from")] = "origin/main",
    start_date: Annotated[str | None, typer.Option(help="Only process days on or after YYYY-MM-DD")] = None,
    end_date: Annotated[str | None, typer.Option(help="Only process days on or before YYYY-MM-DD")] = None,
    include_existing: Annotated[bool, typer.Option(help="Include days that already have up-to-date releases")] = False,
    repo_slug: Annotated[str, typer.Option("--repo", "-R", help="GitHub repo OWNER/REPO")] = DEFAULT_REPO,
) -> None:
    """List daily commit ranges for release processing.

    Outputs JSON array to stdout. Each entry includes base_ref and head_ref
    for use with analyze_git_changes.py, plus release status flags.

    Commit history is fetched from the GitHub GraphQL API — no local git
    repository is required.
    """
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else datetime.now(tz=UTC).date()
    except ValueError as e:
        raise AppExit(code=1, message=f"Invalid date: {e}") from e

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise AppExit(code=1, message="GITHUB_TOKEN environment variable not set")

    ssl_verify = get_ssl_verify()
    base_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")

    gh = make_github_client(token)
    gh_repo = get_github_repo(gh, repo_slug)

    all_by_day, non_merge_by_day = get_commits_by_day(token, repo_slug, branch, verify=ssl_verify, base_url=base_url)

    results: list[dict] = []

    for day_str in sorted(non_merge_by_day):
        try:
            day = date.fromisoformat(day_str)
        except ValueError:
            continue

        if start and day < start:
            continue
        if day > end:
            continue

        entry = _build_day_range(day_str, all_by_day, non_merge_by_day, gh_repo)

        if include_existing or not entry.release_exists or entry.needs_update:
            results.append(asdict(entry))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    app()
