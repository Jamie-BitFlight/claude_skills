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
          comments(first: 100) {
            totalCount
            pageInfo { hasNextPage }
            nodes { databaseId body line originalLine author { login } }
          }
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
        nodes { id author { login } state body }
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


class _Author(BaseModel):
    login: str


class CommentNode(BaseModel):
    """A single review comment, in the shape GitHub's GraphQL API returns it.

    Field names mirror the GraphQL schema exactly (`databaseId`, not
    `database_id`) rather than being converted to snake_case, so the JSON
    this script emits matches the shape the receiving-pr-reviews skill
    already documents and its downstream reader already parses. `author` is
    `None` for a comment left by an account that has since been deleted —
    GitHub's GraphQL schema allows a null `author` there, same as `ReviewNode`.
    """

    databaseId: int
    body: str
    line: int | None
    originalLine: int | None
    author: _Author | None


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


class ReviewNode(BaseModel):
    """A top-level review submission, in the shape GitHub's GraphQL API returns it.

    Distinct from a review *comment* (`CommentNode`): this is the review object itself —
    its `body` is the reviewer's summary text, separate from any inline comment threads
    it may or may not have attached. `author` is `None` for a review left by an account
    that has since been deleted — GitHub's GraphQL schema allows a null `author` there.
    `id` is GitHub's own GraphQL node id for this review submission: `watch` diffs reviews by
    this id (falling back to no field would compare full content, which two distinct reviews
    with identical author/state/body — e.g. the same bot re-posting the same message — could
    satisfy without being the same submission).
    """

    id: str
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

# `_gh_timeout_budget` floors a near-zero remainder to 0.1s — enough to keep the return type
# positive, not enough for a real `gh api graphql` round trip. `_DEFAULT_WATCH_TIMEOUT_SECONDS`
# being an exact multiple of `_DEFAULT_WATCH_INTERVAL_SECONDS` (270 / 90 = 3) means the loop's
# final sleep lands within a fraction of a second of `deadline` on essentially every run, so an
# unguarded poll there is starved to that floor and reliably raises `TimeoutExpired` — not a
# flaky network failure. `watch`'s loop skips a poll once the remaining budget drops below this,
# rather than attempting one that is near-certain to fail.
# ponytail: 5.0 is an unmeasured heuristic, not a proven-sufficient margin for two sequential `gh
# api graphql` round trips — `_build_fetch_result` makes two such calls, and if the first eats
# most of this budget the second can still be starved. The exception handler around the poll in
# `watch` is the real backstop for that case, not this guard alone; raise this value if starvation
# is observed in practice with the guard already in place.
_MIN_POLL_BUDGET_SECONDS = 5.0


def _run_gh(args: list[str], *, timeout: float = _GH_TIMEOUT_SECONDS) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).
        timeout: Seconds to allow before killing the process. Defaults to `_GH_TIMEOUT_SECONDS`;
            `watch` passes a smaller value as its own deadline approaches so one slow call near
            the end of a poll window can't push the whole command past `--timeout-seconds`.

    Returns:
        The command's stdout, decoded as text.

    Raises:
        FileNotFoundError: `gh` (GitHub CLI) is not on PATH.
        subprocess.CalledProcessError: `gh` exited non-zero. stderr is left connected to this
            process's own stderr (not captured) so the diagnostic reaches the caller directly.
        subprocess.TimeoutExpired: the command exceeded `timeout`.
    """
    result = subprocess.run([_GH, *args], stdout=subprocess.PIPE, text=True, timeout=timeout, check=True)
    return result.stdout


def _fetch_pages(
    owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS
) -> list[_ReviewThreadsConnection]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `_run_gh`.

    Returns:
        One validated `reviewThreads` connection per page `gh api graphql --paginate` returned.
    """
    raw = _run_gh(
        [
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
        ],
        timeout=gh_timeout,
    )
    return [
        _ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]


def _fetch_review_pages(
    owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS
) -> list[_ReviewsConnection]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `_run_gh`.

    Returns:
        One validated `reviews` connection per page `gh api graphql --paginate` returned.
    """
    raw = _run_gh(
        [
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
        ],
        timeout=gh_timeout,
    )
    return [
        _ReviewsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviews"])
        for page in json.loads(raw)
    ]


def _gh_timeout_budget(deadline: float | None) -> float:
    """Bound a `gh` call to whatever time remains before `deadline`, capped at `_GH_TIMEOUT_SECONDS`.

    `deadline` is `None` for a plain `fetch` (no overall time budget to respect — use the full
    default). For `watch`, passing its own `deadline` here means each of `_build_fetch_result`'s
    two `gh` calls is bounded by whatever is actually left, not by a fixed worst-case reservation
    subtracted from every poll regardless of how fast GitHub responds — a call made with plenty of
    time left still gets the full `_GH_TIMEOUT_SECONDS`, and only a call made close to `deadline`
    is tightened.

    Args:
        deadline: A `time.monotonic()` timestamp to respect, or `None` for no deadline.

    Returns:
        Seconds to pass as `_run_gh`'s `timeout`, always positive.
    """
    if deadline is None:
        return _GH_TIMEOUT_SECONDS
    return max(0.1, min(_GH_TIMEOUT_SECONDS, deadline - time.monotonic()))


def _build_fetch_result(owner: str, repo: str, pr: int, *, deadline: float | None = None) -> FetchResult:
    """Fetch and assemble one PR's unresolved review threads and top-level review state.

    Shared by `fetch` (prints the result once, `deadline=None`) and `watch` (calls this
    repeatedly on a polling interval, passing its own deadline) so both subcommands assemble a
    `FetchResult` identically.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp the caller wants this call's two `gh`
            invocations to respect — see `_gh_timeout_budget`. `None` means no deadline.

    Returns:
        Totals plus every currently-unresolved thread.
    """
    thread_pages = _fetch_pages(owner, repo, pr, gh_timeout=_gh_timeout_budget(deadline))
    review_pages = _fetch_review_pages(owner, repo, pr, gh_timeout=_gh_timeout_budget(deadline))
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

    Exits non-zero, with nothing printed to stdout, if every re-poll attempted this window
    failed (a transient `gh` failure on each one — see the exception handling inside the loop).
    A `timed_out: true` result on stdout is only ever printed when at least one check since the
    baseline fetch actually succeeded — including the case where no re-poll was attempted at all
    because the window ended too soon for one, which is an honest "nothing to report," not a
    failure.
    """
    deadline = time.monotonic() + timeout_seconds
    baseline = _build_fetch_result(owner, repo, pr, deadline=deadline)
    baseline_thread_ids = {thread.id for thread in baseline.unresolved}
    # Keyed by review id rather than a plain id set, so a review whose body or state changes
    # after this baseline is taken — same id, different content — is still detected as activity
    # below, not just a review with an id the baseline never saw at all.
    baseline_review_states = {review.id: (review.state, review.body) for review in baseline.reviews_with_body}
    current = baseline
    new_thread_ids: set[str] = set()
    new_reviews: list[ReviewNode] = []
    poll_attempts = 0
    poll_successes = 0
    while time.monotonic() < deadline:
        time.sleep(max(0.0, min(interval_seconds, deadline - time.monotonic())))
        if deadline - time.monotonic() < _MIN_POLL_BUDGET_SECONDS:
            # Not enough time left before `deadline` for a real `gh` call to plausibly finish —
            # `_gh_timeout_budget` would otherwise starve it to a floor too small to succeed.
            # Stop polling and report the last successfully-fetched state instead of attempting
            # a call that cannot complete.
            break
        # `_build_fetch_result`'s two `gh` calls are each bounded to whatever's left before
        # `deadline` (see `_gh_timeout_budget`) rather than a static reservation subtracted from
        # every poll — a call made with time to spare still gets the full `_GH_TIMEOUT_SECONDS`.
        poll_attempts += 1
        try:
            current = _build_fetch_result(owner, repo, pr, deadline=deadline)
            poll_successes += 1
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # Two distinct causes land here, not one: a genuine transient `gh` failure mid-window
            # (network hiccup, momentary GitHub error), and the guard above not being a complete
            # fix on its own — `_build_fetch_result` makes two sequential `gh` calls, each
            # re-budgeted from whatever's left, so a slow first call can still starve the second
            # even though the guard passed. This handler is that starved-second-call case's real
            # backstop, not a belt-and-suspenders duplicate of the guard.
            # `watch` is meant to run unattended, often backgrounded (see the receiving-pr-reviews
            # skill's own gotchas on polling a backgrounded call for its own result); crashing
            # here loses the whole call's result instead of just this one poll. Treat it as no
            # fresh data this poll and let the loop continue toward `deadline` on its own schedule.
            continue
        new_thread_ids = {thread.id for thread in current.unresolved} - baseline_thread_ids
        new_reviews = [
            review
            for review in current.reviews_with_body
            if baseline_review_states.get(review.id) != (review.state, review.body)
        ]
        if new_thread_ids or new_reviews:
            break
    if poll_attempts and not poll_successes:
        # Every re-poll this window attempted raised — `current` never advanced past the
        # baseline fetch. Reporting `timed_out: true` here would claim a confirmed check found
        # nothing new, when no check after the baseline actually succeeded; a caller trusting
        # that signal would wrongly conclude the PR is clean instead of retrying or investigating
        # why every `gh` call failed. A guard-triggered stop with zero poll attempts is not this
        # case — that one is an honest, intentional "no time left to check again."
        typer.echo(
            f"watch: all {poll_attempts} poll(s) this window failed — no confirmed state beyond the baseline fetch",
            err=True,
        )
        raise typer.Exit(code=1)
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
