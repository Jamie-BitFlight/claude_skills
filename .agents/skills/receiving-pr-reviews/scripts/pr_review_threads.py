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
from pydantic import BaseModel, ConfigDict

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


class _GitHubResponseModel(BaseModel):
    """Base for every model that ingests a raw GitHub GraphQL response.

    `strict=True` so a producer-shape mismatch — GitHub or `gh` returning a string where the
    schema declares an integer or a boolean — is rejected at ingress instead of being coerced
    into apparently valid review state. Models this script builds itself from already-validated
    values (`UnresolvedThread`, `FetchResult`, `WatchResult`) are not ingress and do not inherit
    this: no untrusted input reaches them.
    """

    model_config = ConfigDict(strict=True)


class _Author(_GitHubResponseModel):
    login: str


class CommentNode(_GitHubResponseModel):
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


class _PageInfo(_GitHubResponseModel):
    hasNextPage: bool


class _CommentsConnection(_GitHubResponseModel):
    totalCount: int
    pageInfo: _PageInfo
    nodes: list[CommentNode]


class _ReviewThreadNode(_GitHubResponseModel):
    id: str
    isResolved: bool
    path: str
    comments: _CommentsConnection


class _ReviewThreadsConnection(_GitHubResponseModel):
    """One page's `reviewThreads` connection, already unwrapped from `data.repository.pullRequest`.

    `_fetch_pages` pulls this dict straight out of each slurped page by subscripting the fixed
    `data.repository.pullRequest.reviewThreads` path — a mismatch there (GitHub renaming or
    removing a field) raises `KeyError` immediately at the point of access, which is an
    acceptable boundary failure for a query shape this script itself controls. Everything
    variable — the node fields — is validated here.
    """

    totalCount: int
    nodes: list[_ReviewThreadNode]


class ReviewNode(_GitHubResponseModel):
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


class _ReviewsConnection(_GitHubResponseModel):
    """One page's `reviews` connection, already unwrapped — see `_ReviewThreadsConnection`."""

    totalCount: int
    nodes: list[ReviewNode]


class UnresolvedThread(BaseModel):
    """One unresolved review thread and its comment history, as emitted to the caller.

    `comments_total` is the thread's own `comments.totalCount`, which is *not* capped by the
    query's `comments(first: 100)` page size. `watch` diffs on it as well as on the comment ids,
    so a reply added to a thread that already had 100 comments — where the id list cannot
    change — is still detected as activity.
    """

    id: str
    path: str
    comments: list[CommentNode]
    comments_total: int
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

    `new_thread_ids` means "threads with activity this window", not "threads absent from the
    baseline": a reply added to a thread the baseline already listed keeps that thread's id, so
    an id-only diff would miss it.
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

# `gh` calls are bounded by the caller, not by a constant here. `gh api --paginate` requests
# every page sequentially inside one subprocess, so any fixed cap would have to cover a whole
# pagination run on an arbitrarily large PR over an arbitrarily slow link — a number this
# repository has no source for (CLAUDE.md, "No invented constraints"). `fetch` and `watch`
# therefore expose `--gh-timeout-seconds`, unbounded by default, and `watch` additionally
# bounds each *poll* by its own `--timeout-seconds` deadline, which the caller chose.

# Anthropic's raw prompt-cache API defaults to a 5-minute TTL in every billing mode; a 1-hour TTL
# is opt-in only (https://platform.claude.com/docs/en/build-with-claude/prompt-caching, accessed
# 2026-08-24). Claude Code additionally opts a Claude-subscription session into that 1-hour cache
# on its own, dropping back to 5 minutes only during usage overage — API-key/Bedrock/Vertex
# sessions stay on the 5-minute default throughout. Sizing `watch`'s defaults to the 5-minute
# floor keeps one call's turn cached under every billing mode. Cover a longer watching window by
# looping `watch` calls (receiving-pr-reviews SKILL.md step 7), not by raising `--timeout-seconds`.
_DEFAULT_WATCH_INTERVAL_SECONDS = 90
_DEFAULT_WATCH_TIMEOUT_SECONDS = 270


def _run_gh(args: list[str], *, timeout: float | None = None) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).
        timeout: Seconds to allow before killing the process, or `None` for no bound. `watch`
            passes the time left before its own deadline so one slow call near the end of a poll
            window can't push the whole command past `--timeout-seconds`.

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


def _fetch_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[_ReviewThreadsConnection]:
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


def _fetch_review_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[_ReviewsConnection]:
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


def _thread_activity_key(thread: UnresolvedThread) -> tuple[int, tuple[tuple[int, str], ...]]:
    """Return a value that changes whenever a thread's comments change.

    Three kinds of change have to register, and no single component catches all three:
    a reply adds an id; an *edit* to an existing comment changes neither its `databaseId`
    nor the count, so the body is needed; and a reply past the query's
    `comments(first: 100)` page cannot change the id/body tuple at all, so the untruncated
    `comments_total` is needed.

    Args:
        thread: An unresolved thread from a `fetch` snapshot.

    Returns:
        `(comments_total, ((databaseId, body), ...))`.
    """
    return thread.comments_total, tuple((comment.databaseId, comment.body) for comment in thread.comments)


def _gh_timeout_budget(deadline: float | None, gh_timeout: float | None) -> float | None:
    """Choose the timeout for one `gh` call.

    `deadline` is `None` for a plain `fetch` and for `watch`'s mandatory baseline: neither has a
    window to respect, so the caller's `--gh-timeout-seconds` applies unchanged (`None` = no
    bound). `watch` passes its own `deadline` for each *poll*, so both of
    `_build_fetch_result`'s `gh` calls are bounded by whatever is actually left rather than by a
    fixed reservation subtracted from every poll regardless of how fast GitHub responds.

    Args:
        deadline: A `time.monotonic()` timestamp to respect, or `None` for no deadline.
        gh_timeout: The caller's own per-call bound, used when there is no deadline.

    Returns:
        Seconds to pass as `_run_gh`'s `timeout`, or `None` for no bound.
    """
    if deadline is None:
        return gh_timeout
    return max(0.0, deadline - time.monotonic())


def _build_fetch_result(
    owner: str, repo: str, pr: int, *, deadline: float | None = None, gh_timeout: float | None = None
) -> FetchResult:
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
        gh_timeout: Per-call bound applied when `deadline` is `None`; `None` means no bound.

    Returns:
        Totals plus every currently-unresolved thread.
    """
    thread_pages = _fetch_pages(owner, repo, pr, gh_timeout=_gh_timeout_budget(deadline, gh_timeout))
    review_pages = _fetch_review_pages(owner, repo, pr, gh_timeout=_gh_timeout_budget(deadline, gh_timeout))
    all_threads = [node for page in thread_pages for node in page.nodes]
    all_reviews = [node for page in review_pages for node in page.nodes]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            comments=node.comments.nodes,
            comments_total=node.comments.totalCount,
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
    gh_timeout_seconds: Annotated[
        float | None, typer.Option(min=0, help="Seconds to bound each `gh` call to. Unbounded by default.")
    ] = None,
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
    result = _build_fetch_result(owner, repo, pr, gh_timeout=gh_timeout_seconds)
    typer.echo(result.model_dump_json())


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    interval_seconds: Annotated[
        int, typer.Option(min=1, help="Seconds to sleep between polls. Must be positive.")
    ] = _DEFAULT_WATCH_INTERVAL_SECONDS,
    timeout_seconds: Annotated[
        int,
        typer.Option(
            min=0,
            help="Stop polling and return the current state after this many seconds. 0 takes the baseline snapshot and returns.",
        ),
    ] = _DEFAULT_WATCH_TIMEOUT_SECONDS,
    gh_timeout_seconds: Annotated[
        float | None,
        typer.Option(
            min=0,
            help="Seconds to bound the baseline `gh` calls to. Unbounded by default; polls are bounded by --timeout-seconds.",
        ),
    ] = None,
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

    `deadline` is the only cutoff. The loop polls while a full `interval_seconds` still fits
    before it and stops once less than that remains — the point past which `_gh_timeout_budget`
    would starve the call to its 0.1s floor anyway. No fixed safety margin is reserved: this
    repository has no source for how long a `gh api graphql` round trip takes, and inventing one
    would be a guess (CLAUDE.md, "No invented constraints"). The final sub-interval stretch of a
    window is therefore left unpolled by design — the next `watch` call's baseline fetch covers
    it, which is exactly why the loop pattern above is documented as back-to-back calls.

    Exits non-zero, with nothing printed to stdout, if the *last* re-poll attempted this window
    failed (a transient `gh` failure — see the exception handling inside the loop). An earlier
    success in the same window does not offset a later failure: what matters is whether the final
    stretch before `deadline` was actually confirmed, not whether any check ever succeeded. A
    `timed_out: true` result on stdout is only ever printed when the most recent check — the
    baseline fetch, or the last re-poll if one was attempted — succeeded, including the case
    where no re-poll was attempted at all because the window ended too soon for one, which is an
    honest "nothing to report," not a failure.
    """
    deadline = time.monotonic() + timeout_seconds
    # The baseline is mandatory and is *not* deadline-bounded: with `--timeout-seconds 0` the
    # deadline is already spent, and starving this call would turn the documented immediate
    # snapshot into a `TimeoutExpired`. Only the polls below race the deadline.
    baseline = _build_fetch_result(owner, repo, pr, gh_timeout=gh_timeout_seconds)
    # Keyed by comment identity rather than a plain thread-id set: a reviewer replying to a
    # thread the baseline already listed leaves that thread's id unchanged, so an id-only diff
    # would report `timed_out: true` while unread review activity sits in `unresolved`.
    baseline_thread_activity = {thread.id: _thread_activity_key(thread) for thread in baseline.unresolved}
    # Keyed by review id rather than a plain id set, so a review whose body or state changes
    # after this baseline is taken — same id, different content — is still detected as activity
    # below, not just a review with an id the baseline never saw at all.
    baseline_review_states = {review.id: (review.state, review.body) for review in baseline.reviews_with_body}
    current = baseline
    new_thread_ids: set[str] = set()
    new_reviews: list[ReviewNode] = []
    poll_attempts = 0
    # Tracks the outcome of the most recent poll attempt, not a success count — a success
    # earlier in the window does not confirm the tail after a later failure. Starts True: the
    # baseline fetch above already succeeded (its own errors propagate uncaught, before the
    # loop), so "no poll attempted since" is itself a confirmed state, not an unknown one.
    last_poll_ok = True
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_seconds, remaining))
        if remaining <= interval_seconds:
            # That sleep consumed the rest of the window. `_gh_timeout_budget` would bound a poll
            # here to its 0.1s floor, too little for a `gh api graphql` round trip, so stop and
            # report the last successfully-fetched state rather than spawn a doomed call.
            break
        # Each of `_build_fetch_result`'s two `gh` calls is bounded to whatever's left before
        # `deadline` (see `_gh_timeout_budget`), re-measured between them rather than split from
        # a fixed reservation.
        poll_attempts += 1
        # `watch` is meant to run unattended, often backgrounded (see the receiving-pr-reviews
        # skill's own gotchas on polling a backgrounded call for its own result); crashing on a
        # single bad poll loses the whole call's result. Both handlers below record the outcome
        # and let the loop continue toward `deadline` on its own schedule.
        try:
            current = _build_fetch_result(owner, repo, pr, deadline=deadline)
            last_poll_ok = True
        except subprocess.TimeoutExpired:
            # A timeout is the one failure the clock can explain: `_gh_timeout_budget`
            # deliberately shrinks each call to the time left, so the last poll of a window is
            # *expected* to be cut short. At or past `deadline` that is the same honest "no time
            # left to check again" this command reports when it stops before polling at all.
            # With time still on the clock it is a real network stall and leaves the tail
            # unconfirmed.
            last_poll_ok = time.monotonic() >= deadline
            continue
        except subprocess.CalledProcessError:
            # A non-zero exit is an authentication, rate-limit, API or GraphQL error. The
            # deadline cannot cause it and cannot excuse it, so it is a failed poll whatever the
            # clock says — reporting `timed_out: true` off stale state here would tell a caller
            # the PR is clean when nothing was actually checked.
            last_poll_ok = False
            continue
        new_thread_ids = {
            thread.id
            for thread in current.unresolved
            if baseline_thread_activity.get(thread.id) != _thread_activity_key(thread)
        }
        new_reviews = [
            review
            for review in current.reviews_with_body
            if baseline_review_states.get(review.id) != (review.state, review.body)
        ]
        if new_thread_ids or new_reviews:
            break
    if poll_attempts and not last_poll_ok:
        # The most recent poll attempted this window raised — not just "every poll failed", but
        # specifically the *last* one, which is what actually matters: an earlier success in the
        # window does not confirm the tail after a later failure. Reporting `timed_out: true`
        # here would claim a confirmed check found nothing new for the whole window, when the
        # final stretch before `deadline` was never actually observed; a caller trusting that
        # signal would wrongly conclude the PR is clean instead of retrying or investigating why
        # the last `gh` call failed. A guard-triggered stop with zero poll attempts is not this
        # case — that one is an honest, intentional "no time left to check again," and a run that
        # ends on a *successful* poll (even after earlier failures) is confirmed as of that poll.
        typer.echo(
            f"watch: the last of {poll_attempts} poll(s) this window failed — final state before "
            "deadline was never confirmed",
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
