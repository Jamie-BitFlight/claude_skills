#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
# ]
# ///
"""GitHub PR review-thread operations for the receiving-pr-reviews skill.

Wraps the three `gh` command pipelines the skill documents: fetching every unresolved review
thread (auto-paginated, filtered before it reaches an agent's context), replying to a review
comment, and resolving a review thread. Every operation shells out to `gh` (GitHub CLI) rather
than talking to the GitHub API directly, relying on `gh`'s own authentication. A fourth command,
`watch`, blocks this process on an internal polling loop so a caller never needs a separate
resumption mechanism to re-check a PR later.

Usage:
    uv run pr_review_threads.py fetch --pr 3208
    uv run pr_review_threads.py watch --pr 3208
    uv run pr_review_threads.py reply --pr 3208 --comment-id 123456 --body "Fixed in abc123."
    uv run pr_review_threads.py resolve --thread-id PRRT_kwDO...
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Annotated

import typer
from pydantic import BaseModel

# This checkout's own owner/repo — override with --owner/--repo to target any other repository;
# every `gh` call below takes them as explicit query variables, so nothing here is repo-specific.
DEFAULT_OWNER = "Jamie-BitFlight"
DEFAULT_REPO = "claude_skills"

app = typer.Typer(help="GitHub PR review-thread operations (fetch/watch/reply/resolve) via gh.")

_UNRESOLVED_THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved path
          comments(first: 100) { totalCount pageInfo { hasNextPage } nodes { databaseId body line originalLine } }
        }
      }
    }
  }
}
"""

_REVIEWS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviews(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes { author { login } state body }
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
    line: int | None
    originalLine: int | None


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
    """One page's `reviewThreads` connection, already unwrapped from `data.repository.pullRequest`.

    `_fetch_pages` pulls this dict straight out of each slurped page by subscripting the fixed
    `data.repository.pullRequest.reviewThreads` path — a mismatch there (GitHub renaming or
    removing a field) raises `KeyError` immediately at the point of access, which is an
    acceptable boundary failure for a query shape this script itself controls. Everything
    variable — the node fields — is validated here.
    """

    totalCount: int
    nodes: list[_ReviewThreadNode]


class _Author(BaseModel):
    login: str


class ReviewNode(BaseModel):
    """A top-level review submission, in the shape GitHub's GraphQL API returns it.

    Distinct from a review *comment* (`CommentNode`): this is the review object itself —
    its `body` is the reviewer's summary text, separate from any inline comment threads
    it may or may not have attached. `author` is `None` for a review left by an account
    that has since been deleted — GitHub's GraphQL schema allows a null `author` there.
    """

    author: _Author | None
    state: str
    body: str


class _ReviewsConnection(BaseModel):
    """One page's `reviews` connection, already unwrapped — see `_ReviewThreadsConnection`."""

    totalCount: int
    nodes: list[ReviewNode]


class UnresolvedThread(BaseModel):
    """One unresolved review thread and its full comment history, as emitted to the caller."""

    id: str
    path: str
    comments: list[CommentNode]
    comments_truncated: bool


class FetchResult(BaseModel):
    """Result of `fetch`: totals plus every currently-unresolved thread."""

    reviews_count: int
    reviews_with_body: list[ReviewNode]
    threads_count: int
    unresolved: list[UnresolvedThread]
    unresolved_count: int


class WatchResult(BaseModel):
    """Result of `watch`: the final fetch snapshot plus how the poll loop ended.

    `timed_out` is `False` exactly when `new_thread_ids` or `new_reviews_with_body` is non-empty —
    the loop breaks on the first poll that finds either, and returns `True` only once
    `timeout_seconds` elapses with neither ever appearing.
    """

    timed_out: bool
    new_thread_ids: list[str]
    new_reviews_with_body: list[ReviewNode]
    state: FetchResult


# Absolute `gh` path, resolved once at import time — ruff's start-process-with-partial-path (S607)
# requires a resolved path rather than a bare command name. Falls back to the literal "gh" when
# `shutil.which` can't find it, so a missing binary still surfaces as a normal FileNotFoundError
# from the exec call itself rather than a custom error path.
_GH = shutil.which("gh") or "gh"

_GH_TIMEOUT_SECONDS = 30

# Anthropic's raw prompt-cache API defaults to a 5-minute TTL in every billing mode; a 1-hour TTL
# is opt-in only (https://platform.claude.com/docs/en/build-with-claude/prompt-caching, accessed
# 2026-08-24). Claude Code additionally opts a Claude-subscription session into that 1-hour cache
# on its own, dropping back to 5 minutes only during usage overage — API-key/Bedrock/Vertex
# sessions stay on the 5-minute default throughout. Sizing `watch`'s defaults to the 5-minute
# floor keeps one call's turn cached under every billing mode. Cover a longer watching window by
# looping `watch` calls (receiving-pr-reviews SKILL.md step 7), not by raising `--timeout-seconds`.
_DEFAULT_WATCH_INTERVAL_SECONDS = 90
_DEFAULT_WATCH_TIMEOUT_SECONDS = 270


def _run_gh(args: list[str]) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).

    Returns:
        The command's stdout, decoded as text.

    Raises:
        FileNotFoundError: `gh` (GitHub CLI) is not on PATH.
        subprocess.CalledProcessError: `gh` exited non-zero. stderr is left connected to this
            process's own stderr (not captured) so the diagnostic reaches the caller directly.
        subprocess.TimeoutExpired: the command exceeded `_GH_TIMEOUT_SECONDS`.
    """
    result = subprocess.run([_GH, *args], stdout=subprocess.PIPE, text=True, timeout=_GH_TIMEOUT_SECONDS, check=True)
    return result.stdout


def _fetch_pages(owner: str, repo: str, pr: int) -> list[_ReviewThreadsConnection]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.

    Returns:
        One validated `reviewThreads` connection per page `gh api graphql --paginate` returned.
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
    return [
        _ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]


def _fetch_review_pages(owner: str, repo: str, pr: int) -> list[_ReviewsConnection]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.

    Returns:
        One validated `reviews` connection per page `gh api graphql --paginate` returned.
    """
    raw = _run_gh([
        "api",
        "graphql",
        "--paginate",
        "--slurp",
        "-f",
        f"query={_REVIEWS_QUERY}",
        "-f",
        f"o={owner}",
        "-f",
        f"r={repo}",
        "-F",
        f"pr={pr}",
    ])
    return [
        _ReviewsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviews"])
        for page in json.loads(raw)
    ]


def _build_fetch_result(owner: str, repo: str, pr: int) -> FetchResult:
    """Fetch and assemble one PR's unresolved review threads and top-level review state.

    Shared by `fetch` (prints the result once) and `watch` (calls this repeatedly on a polling
    interval) so both subcommands assemble a `FetchResult` identically.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.

    Returns:
        Totals plus every currently-unresolved thread.
    """
    thread_pages = _fetch_pages(owner, repo, pr)
    review_pages = _fetch_review_pages(owner, repo, pr)
    all_threads = [node for page in thread_pages for node in page.nodes]
    all_reviews = [node for page in review_pages for node in page.nodes]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            comments=node.comments.nodes,
            comments_truncated=node.comments.pageInfo.hasNextPage,
        )
        for node in all_threads
        if not node.isResolved
    ]
    return FetchResult(
        reviews_count=review_pages[0].totalCount,
        reviews_with_body=[review for review in all_reviews if review.body.strip()],
        threads_count=thread_pages[0].totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
    )


@app.command()
def fetch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
) -> None:
    """Fetch a PR's unresolved review threads, auto-paginated so none is silently truncated.

    Prints compact JSON with `reviews_count`, `threads_count`, `unresolved`, and
    `unresolved_count`. A `threads_count` of 0 means no reviews have landed yet — different from
    a nonzero `threads_count` with `unresolved_count: 0`, which means every thread found was
    already resolved. Never treat an empty `unresolved` array as "nothing to do" without checking
    these counts first. Each unresolved thread carries its own `id` (for resolving) and each
    comment's `databaseId` (for replying) — no separate lookup needed. A thread's
    `comments_truncated: true` means that single thread has passed 100 comments in its own
    back-and-forth (rare, but real content is missing) — page that thread's `comments` connection
    directly before concluding anything about it.

    Also includes `reviews_with_body`: reviews whose top-level summary text is non-empty (an
    approval note, or feedback given in the review body rather than as an inline comment) — these
    have no thread at all and would otherwise be invisible even when `unresolved_count` is 0;
    treat each as actionable input too.
    """
    result = _build_fetch_result(owner, repo, pr)
    typer.echo(result.model_dump_json())


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    interval_seconds: Annotated[
        int, typer.Option(help="Seconds to sleep between polls.")
    ] = _DEFAULT_WATCH_INTERVAL_SECONDS,
    timeout_seconds: Annotated[
        int, typer.Option(help="Stop polling and return the current state after this many seconds.")
    ] = _DEFAULT_WATCH_TIMEOUT_SECONDS,
) -> None:
    """Poll `fetch` until new PR review activity appears, or a timeout elapses.

    Blocks this process for up to `timeout_seconds`, re-fetching every `interval_seconds`.
    Returns the moment a thread id or `reviews_with_body` entry appears that the first fetch in
    this run did not have, or the final clean state once `timeout_seconds` elapses with no new
    activity.

    Each call covers only its own `timeout_seconds` window. To watch for longer than one call's
    default window, issue `watch` again immediately after a `timed_out: true` result — its own
    baseline fetch picks up exactly where the previous call's ended, so back-to-back calls never
    miss activity between them. The receiving-pr-reviews SKILL.md documents this loop pattern.

    Prints the same compact JSON `fetch` prints, nested under `state`, plus `timed_out`,
    `new_thread_ids`, and `new_reviews_with_body`.
    """
    deadline = time.monotonic() + timeout_seconds
    baseline = _build_fetch_result(owner, repo, pr)
    baseline_thread_ids = {thread.id for thread in baseline.unresolved}
    current = baseline
    new_thread_ids: set[str] = set()
    new_reviews: list[ReviewNode] = []
    while time.monotonic() < deadline:
        time.sleep(max(0.0, min(interval_seconds, deadline - time.monotonic())))
        current = _build_fetch_result(owner, repo, pr)
        new_thread_ids = {thread.id for thread in current.unresolved} - baseline_thread_ids
        new_reviews = [review for review in current.reviews_with_body if review not in baseline.reviews_with_body]
        if new_thread_ids or new_reviews:
            break
    result = WatchResult(
        timed_out=not (new_thread_ids or new_reviews),
        new_thread_ids=sorted(new_thread_ids),
        new_reviews_with_body=new_reviews,
        state=current,
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
    typer.echo(raw.strip())


@app.command()
def resolve(thread_id: Annotated[str, typer.Option(help="Review thread id, from `fetch`.")]) -> None:
    """Resolve a review thread. Prints gh's mutation response as compact JSON."""
    raw = _run_gh(["api", "graphql", "-f", f"query={_RESOLVE_THREAD_MUTATION}", "-f", f"threadId={thread_id}"])
    typer.echo(raw.strip())


if __name__ == "__main__":
    app()
