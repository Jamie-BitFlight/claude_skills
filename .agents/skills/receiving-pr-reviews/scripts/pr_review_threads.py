#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
# ]
# ///
"""GitHub PR review-thread operations for the receiving-pr-reviews skill.

Wraps the three `gh` command pipelines the skill documents: fetching every
unresolved review thread (auto-paginated, filtered before it reaches an
agent's context), replying to a review comment, and resolving a review
thread. Every operation shells out to `gh` (GitHub CLI) rather than talking to
the GitHub API directly, relying on `gh`'s own authentication.

Usage:
    uv run pr_review_threads.py fetch --pr 3208
    uv run pr_review_threads.py reply --pr 3208 --comment-id 123456 --body "Fixed in abc123."
    uv run pr_review_threads.py resolve --thread-id PRRT_kwDO...
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Annotated

import typer
from pydantic import BaseModel

DEFAULT_OWNER = "Jamie-BitFlight"
DEFAULT_REPO = "claude_skills"

app = typer.Typer(help="GitHub PR review-thread operations (fetch/reply/resolve) via gh.")

_UNRESOLVED_THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviews(first: 0) { totalCount }
      reviewThreads(first: 100, after: $endCursor) {
        totalCount
        nodes {
          id isResolved path
          comments(first: 100) { totalCount pageInfo { hasNextPage } nodes { databaseId body } }
        }
      }
    }
  }
}
"""

_RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread { isResolved }
  }
}
"""


class CommentNode(BaseModel):
    """A single review comment, in the shape GitHub's GraphQL API returns it.

    Field names mirror the GraphQL schema exactly (`databaseId`, not
    `database_id`) rather than being converted to snake_case, so the JSON
    this script emits matches the shape the receiving-pr-reviews skill
    already documents and its downstream reader already parses.
    """

    databaseId: int
    body: str


class _PageInfo(BaseModel):
    hasNextPage: bool


class _CommentsConnection(BaseModel):
    totalCount: int
    pageInfo: _PageInfo
    nodes: list[CommentNode]


class _ReviewThreadNode(BaseModel):
    id: str
    isResolved: bool
    path: str
    comments: _CommentsConnection


class _ReviewThreadsConnection(BaseModel):
    totalCount: int
    nodes: list[_ReviewThreadNode]


class _Reviews(BaseModel):
    totalCount: int


class _PullRequestData(BaseModel):
    reviews: _Reviews
    reviewThreads: _ReviewThreadsConnection


class _RepositoryData(BaseModel):
    pullRequest: _PullRequestData


class _GraphQLPageData(BaseModel):
    repository: _RepositoryData


class _GraphQLPage(BaseModel):
    """One page of `gh api graphql --paginate --slurp` output."""

    data: _GraphQLPageData


class UnresolvedThread(BaseModel):
    """One review thread and its full comment history, as emitted to the caller."""

    id: str
    path: str
    comments: list[CommentNode]
    comments_truncated: bool


class FetchResult(BaseModel):
    """Result of `fetch`: totals plus every thread selected by `--include-resolved`."""

    reviews_count: int
    threads_count: int
    unresolved: list[UnresolvedThread]
    unresolved_count: int


def _gh_executable() -> str:
    """Resolve the `gh` executable's absolute path.

    Returns:
        Absolute path to `gh`.

    Raises:
        RuntimeError: `gh` is not on PATH.
    """
    path = shutil.which("gh")
    if path is None:
        msg = "gh (GitHub CLI) not found on PATH"
        raise RuntimeError(msg)
    return path


def _run_gh(args: list[str]) -> str:
    """Run a `gh` command and return its captured stdout.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).

    Returns:
        The command's stdout, decoded as text.

    Raises:
        subprocess.CalledProcessError: `gh` exited non-zero. stderr is left connected to this
            process's own stderr (not captured) so `gh`'s diagnostic reaches the caller directly
            instead of being buried in an exception attribute nobody prints.
    """
    result = subprocess.run([_gh_executable(), *args], stdout=subprocess.PIPE, text=True, check=True)
    return result.stdout


def _fetch_pages(owner: str, repo: str, pr: int) -> list[_GraphQLPage]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.

    Returns:
        One validated page per page `gh api graphql --paginate` returned. A schema mismatch
        (a field GitHub renamed or removed) raises `pydantic.ValidationError` immediately here
        rather than surfacing later as a confusing `KeyError` deep in the caller.
    """
    raw = _run_gh([
        "api",
        "graphql",
        "--paginate",
        "--slurp",
        "-f",
        f"query={_UNRESOLVED_THREADS_QUERY}",
        "-f",
        f"o={owner}",
        "-f",
        f"r={repo}",
        "-F",
        f"pr={pr}",
    ])
    return [_GraphQLPage.model_validate(page) for page in json.loads(raw)]


@app.command()
def fetch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    include_resolved: Annotated[
        bool, typer.Option("--include-resolved", help="Include already-resolved threads (auditing review history).")
    ] = False,
) -> None:
    """Fetch a PR's review threads, auto-paginated so none is silently truncated.

    Prints compact JSON with `reviews_count`, `threads_count`, `unresolved` (every thread when
    `--include-resolved` is set, otherwise only unresolved ones), and `unresolved_count`. A
    `threads_count` of 0 means no reviews have landed yet — different from a nonzero
    `threads_count` with `unresolved_count: 0`, which means everything found was already
    resolved. Each thread's `comments_truncated: true` means that thread alone has passed 100
    comments in its own back-and-forth and needs its `comments` connection paged directly.
    """
    pages = _fetch_pages(owner, repo, pr)
    pull_request = pages[0].data.repository.pullRequest
    all_nodes = [node for page in pages for node in page.data.repository.pullRequest.reviewThreads.nodes]
    selected = all_nodes if include_resolved else [node for node in all_nodes if not node.isResolved]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            comments=node.comments.nodes,
            comments_truncated=node.comments.pageInfo.hasNextPage,
        )
        for node in selected
    ]
    result = FetchResult(
        reviews_count=pull_request.reviews.totalCount,
        threads_count=pull_request.reviewThreads.totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
    )
    typer.echo(result.model_dump_json())


@app.command()
def reply(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    comment_id: Annotated[int, typer.Option(help="Review comment databaseId, from `fetch`.")],
    body: Annotated[str, typer.Option(help="Reply text.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
) -> None:
    """Reply to a review comment. Prints gh's created-comment response as compact JSON."""
    raw = _run_gh([
        "api",
        "-X",
        "POST",
        f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies",
        "-f",
        f"body={body}",
    ])
    typer.echo(json.dumps(json.loads(raw), separators=(",", ":")))


@app.command()
def resolve(thread_id: Annotated[str, typer.Option(help="Review thread id, from `fetch`.")]) -> None:
    """Resolve a review thread. Prints gh's mutation response as compact JSON."""
    raw = _run_gh(["api", "graphql", "-f", f"query={_RESOLVE_THREAD_MUTATION}", "-f", f"threadId={thread_id}"])
    typer.echo(json.dumps(json.loads(raw), separators=(",", ":")))


if __name__ == "__main__":
    app()
