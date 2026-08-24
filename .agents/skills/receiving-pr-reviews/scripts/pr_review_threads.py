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
the GitHub API directly, relying on `gh`'s own authentication. A fourth
command, `watch`, blocks this process on an internal polling loop so a caller
never needs a separate resumption mechanism to re-check a PR later.

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

# A separate query+pagination from reviewThreads above: `gh api graphql --paginate` follows a
# single `$endCursor`/`pageInfo.endCursor` pair per invocation, so one query cannot paginate two
# independent connections (reviews and reviewThreads) at once — each needs its own `gh` call.
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
    totalCount: int
    nodes: list[_ReviewThreadNode]


class _Author(BaseModel):
    login: str


class ReviewNode(BaseModel):
    """A top-level review submission, in the shape GitHub's GraphQL API returns it.

    Distinct from a review *comment* (`CommentNode`): this is the review object itself —
    its `body` is the reviewer's summary text, separate from any inline comment threads
    it may or may not have attached.
    """

    author: _Author
    state: str
    body: str


class _ReviewsConnection(BaseModel):
    totalCount: int
    pageInfo: _PageInfo
    nodes: list[ReviewNode]


class _PullRequestThreadsData(BaseModel):
    reviewThreads: _ReviewThreadsConnection


class _RepositoryThreadsData(BaseModel):
    pullRequest: _PullRequestThreadsData


class _GraphQLThreadsPageData(BaseModel):
    repository: _RepositoryThreadsData


class _GraphQLThreadsPage(BaseModel):
    """One page of the reviewThreads `gh api graphql --paginate --slurp` output."""

    data: _GraphQLThreadsPageData


class _PullRequestReviewsData(BaseModel):
    reviews: _ReviewsConnection


class _RepositoryReviewsData(BaseModel):
    pullRequest: _PullRequestReviewsData


class _GraphQLReviewsPageData(BaseModel):
    repository: _RepositoryReviewsData


class _GraphQLReviewsPage(BaseModel):
    """One page of the reviews `gh api graphql --paginate --slurp` output.

    Fetched via a separate `gh` invocation from `_GraphQLThreadsPage`: `--paginate` follows one
    `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections with
    independent cursors — cannot be paginated together in a single query.
    """

    data: _GraphQLReviewsPageData


class UnresolvedThread(BaseModel):
    """One review thread and its full comment history, as emitted to the caller."""

    id: str
    path: str
    isResolved: bool
    comments: list[CommentNode]
    comments_truncated: bool


class FetchResult(BaseModel):
    """Result of `fetch`: totals plus every thread selected by `--include-resolved`."""

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
    polls: int
    elapsed_seconds: float
    new_thread_ids: list[str]
    new_reviews_with_body: list[ReviewNode]
    state: FetchResult


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


def _uv_executable() -> str:
    """Resolve the `uv` executable's absolute path.

    Returns:
        Absolute path to `uv`.

    Raises:
        RuntimeError: `uv` is not on PATH.
    """
    path = shutil.which("uv")
    if path is None:
        msg = "uv not found on PATH"
        raise RuntimeError(msg)
    return path


_GH_TIMEOUT_SECONDS = 30
_RUN_BOUNDED = "scripts/run_bounded.py"

# `watch`'s defaults keep each call short enough that the turn it returns into still lands
# within prompt-cache TTL even under a degraded (5-minute) cache window, not just under Claude
# Code's 600-second Bash tool-call cap — see the receiving-pr-reviews SKILL.md step 7 gotcha
# before raising `--timeout-seconds`; step 7 covers a longer watching window by looping short
# calls instead. A 90s interval over a 270s timeout polls 4 times per call (t=0/90/180/270).
_DEFAULT_WATCH_INTERVAL_SECONDS = 90
_DEFAULT_WATCH_TIMEOUT_SECONDS = 270


def _run_gh(args: list[str]) -> str:
    """Run a `gh` command through this repo's bounded runner and return its captured stdout.

    A stalled `gh` process (GitHub or the local proxy stops responding) would otherwise hang
    indefinitely with no timeout. `run_bounded.py` terminates the whole process group on expiry.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).

    Returns:
        The command's stdout, decoded as text.

    Raises:
        subprocess.CalledProcessError: `gh` exited non-zero, or the command exceeded
            `_GH_TIMEOUT_SECONDS` and was terminated. stderr is left connected to this
            process's own stderr (not captured) so the diagnostic reaches the caller directly
            instead of being buried in an exception attribute nobody prints.
    """
    result = subprocess.run(
        [
            _uv_executable(),
            "run",
            "--quiet",
            "--script",
            _RUN_BOUNDED,
            "--timeout-seconds",
            str(_GH_TIMEOUT_SECONDS),
            "--",
            _gh_executable(),
            *args,
        ],
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout


def _fetch_pages(owner: str, repo: str, pr: int) -> list[_GraphQLThreadsPage]:
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
    return [_GraphQLThreadsPage.model_validate(page) for page in json.loads(raw)]


def _fetch_review_pages(owner: str, repo: str, pr: int) -> list[_GraphQLReviewsPage]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.

    Returns:
        One validated page per page `gh api graphql --paginate` returned.
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
    return [_GraphQLReviewsPage.model_validate(page) for page in json.loads(raw)]


def _build_fetch_result(owner: str, repo: str, pr: int, *, include_resolved: bool) -> FetchResult:
    """Fetch and assemble one PR's review-thread and review state.

    Shared by `fetch` (prints the result once) and `watch` (calls this repeatedly on a polling
    interval) so both subcommands assemble a `FetchResult` identically.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        include_resolved: Include already-resolved threads in `unresolved` (auditing review
            history) instead of only currently-unresolved ones.

    Returns:
        Totals plus every thread selected by `include_resolved`.
    """
    pages = _fetch_pages(owner, repo, pr)
    review_pages = _fetch_review_pages(owner, repo, pr)
    threads = pages[0].data.repository.pullRequest.reviewThreads
    reviews = review_pages[0].data.repository.pullRequest.reviews
    all_nodes = [node for page in pages for node in page.data.repository.pullRequest.reviewThreads.nodes]
    all_reviews = [node for page in review_pages for node in page.data.repository.pullRequest.reviews.nodes]
    selected = all_nodes if include_resolved else [node for node in all_nodes if not node.isResolved]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            isResolved=node.isResolved,
            comments=node.comments.nodes,
            comments_truncated=node.comments.pageInfo.hasNextPage,
        )
        for node in selected
    ]
    return FetchResult(
        reviews_count=reviews.totalCount,
        reviews_with_body=[review for review in all_reviews if review.body.strip()],
        threads_count=threads.totalCount,
        unresolved=unresolved,
        unresolved_count=sum(1 for node in selected if not node.isResolved),
    )


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

    Also includes `reviews_with_body`: reviews whose top-level summary text is non-empty (an
    approval note, or feedback given in the review body rather than as an inline comment) —
    these have no thread at all and would otherwise be invisible even when `unresolved_count`
    is 0. Both `reviews` and `reviewThreads` are paginated independently and in full — neither
    is capped at one page of 100.
    """
    result = _build_fetch_result(owner, repo, pr, include_resolved=include_resolved)
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

    Blocks this process — one `uv run` invocation, one tool call — for up to `timeout_seconds`,
    re-fetching every `interval_seconds`. Returns the moment a thread id or `reviews_with_body`
    entry appears that the first fetch in this run did not have, or the final clean state once
    `timeout_seconds` elapses with no new activity. The polling loop lives entirely inside this
    one process, so no separate mechanism is needed to resume checking later — everything the
    check needs happens before this command returns.

    Each call covers only its own `timeout_seconds` window. To watch for longer than one call's
    default window, issue `watch` again immediately after a `timed_out: true` result — its own
    baseline fetch picks up exactly where the previous call's ended, so back-to-back calls never
    miss activity between them. The receiving-pr-reviews SKILL.md documents this loop pattern.

    Prints the same compact JSON `fetch` prints, nested under `state`, plus `timed_out`, `polls`,
    `elapsed_seconds`, `new_thread_ids`, and `new_reviews_with_body`.
    """
    start = time.monotonic()
    deadline = start + timeout_seconds
    baseline = _build_fetch_result(owner, repo, pr, include_resolved=False)
    baseline_thread_ids = {thread.id for thread in baseline.unresolved}
    current = baseline
    new_thread_ids: set[str] = set()
    new_reviews: list[ReviewNode] = []
    polls = 1
    while time.monotonic() < deadline:
        time.sleep(max(0.0, min(interval_seconds, deadline - time.monotonic())))
        polls += 1
        current = _build_fetch_result(owner, repo, pr, include_resolved=False)
        new_thread_ids = {thread.id for thread in current.unresolved} - baseline_thread_ids
        new_reviews = [review for review in current.reviews_with_body if review not in baseline.reviews_with_body]
        if new_thread_ids or new_reviews:
            break
    result = WatchResult(
        timed_out=not (new_thread_ids or new_reviews),
        polls=polls,
        elapsed_seconds=time.monotonic() - start,
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
    typer.echo(json.dumps(json.loads(raw), separators=(",", ":")))


@app.command()
def resolve(thread_id: Annotated[str, typer.Option(help="Review thread id, from `fetch`.")]) -> None:
    """Resolve a review thread. Prints gh's mutation response as compact JSON."""
    raw = _run_gh(["api", "graphql", "-f", f"query={_RESOLVE_THREAD_MUTATION}", "-f", f"threadId={thread_id}"])
    typer.echo(json.dumps(json.loads(raw), separators=(",", ":")))


if __name__ == "__main__":
    app()
