#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
# ]
#
# [tool.ty.environment]
# extra-paths = ["."]
# ///
"""GitHub PR review-thread operations for the receiving-pr-reviews skill.

Wraps the `gh` command pipelines the skill documents: fetching every unresolved review thread and
unresponded review (auto-paginated, filtered before it reaches an agent's context), replying to a
review comment, and resolving a review thread. Every operation shells out to `gh` (GitHub CLI)
rather than talking to the GitHub API directly, relying on `gh`'s own authentication. A fourth
command, `watch`, blocks this process on an internal polling loop so a caller never needs a
separate resumption mechanism to re-check a PR later.

`fetch`'s I/O and `FetchResult`/`WatchResult` assembly live in `pr_review_gh.py`; the data
contracts live in `pr_review_models.py`. This module is the CLI presentation layer: it parses
arguments, drives `watch`'s polling loop, and prints results.

Usage:
    uv run pr_review_threads.py fetch --pr 3208
    uv run pr_review_threads.py watch --pr 3208
    uv run pr_review_threads.py reply --pr 3208 --comment-id 123456 --body "Fixed in abc123."
    uv run pr_review_threads.py resolve --thread-id PRRT_kwDO...
"""

from __future__ import annotations

import subprocess
import time
from typing import Annotated

import typer

from pr_review_gh import RESOLVE_THREAD_MUTATION, build_fetch_result, run_gh
from pr_review_models import WatchResult

# This checkout's own owner/repo — override with --owner/--repo to target any other repository;
# every `gh` call below takes them as explicit query variables, so nothing here is repo-specific.
DEFAULT_OWNER = "Jamie-BitFlight"
DEFAULT_REPO = "claude_skills"

app = typer.Typer(help="GitHub PR review-thread operations (fetch/watch/reply/resolve) via gh.")

# Anthropic's raw prompt-cache API defaults to a 5-minute TTL in every billing mode; a 1-hour TTL
# is opt-in only (https://platform.claude.com/docs/en/build-with-claude/prompt-caching, accessed
# 2026-08-24). Claude Code additionally opts a Claude-subscription session into that 1-hour cache
# on its own, dropping back to 5 minutes only during usage overage — API-key/Bedrock/Vertex
# sessions stay on the 5-minute default throughout. Sizing `watch`'s defaults to the 5-minute
# floor keeps one call's turn cached under every billing mode. Cover a longer watching window by
# looping `watch` calls (receiving-pr-reviews SKILL.md step 7), not by raising `--timeout-seconds`.
_DEFAULT_WATCH_INTERVAL_SECONDS = 90
# 270 is deliberately under the 5-minute prompt-cache TTL (every Claude billing mode) — a
# watch call blocking this long still returns before the caller's context falls out of cache.
_DEFAULT_WATCH_TIMEOUT_SECONDS = 270


@app.command()
def fetch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    gh_timeout_seconds: Annotated[
        float | None, typer.Option(min=0, help="Seconds to bound each `gh` call to. Unbounded by default.")
    ] = None,
) -> None:
    """Fetch a PR's outstanding review activity, auto-paginated so none is silently truncated.

    Prints compact JSON with `reviews_count`, `threads_count`, `unresolved`, `unresolved_count`,
    `reviews_with_body`, `unresponded_reviews`, `codex_approved`, and `reviewability`. A `threads_count` of 0 means
    no reviews have landed yet — different from a nonzero `threads_count` with `unresolved_count:
    0`, which means every thread found was already resolved. Never treat an empty `unresolved`
    array as "nothing to do" without checking these counts first. Each unresolved thread carries
    its own `id` (for resolving) and each comment's `databaseId` (for replying) — no separate
    lookup needed. A thread's `comments_truncated: true` means that single thread has passed 100
    comments in its own back-and-forth (rare, but real content is missing) — page that thread's
    `comments` connection directly before concluding anything about it.

    `reviews_with_body` is every review whose top-level summary text is non-empty (an approval
    note, or feedback given in the review body rather than as an inline comment) — these have no
    thread at all and would otherwise be invisible even when `unresolved_count` is 0.
    `unresponded_reviews` narrows that to the ones nothing has been posted on the PR about since —
    see `pr_review_gh.build_fetch_result` for exactly how that is derived; treat each as
    actionable input. `codex_approved` is `True` when Codex's thumbs-up reaction is currently
    present on the PR.

    `reviewability.blockers` is non-empty when the PR itself is why nothing is outstanding: a draft
    gets no reviewers requested and a conflicting branch gets no review runs, so an empty
    `unresolved` array there means "nothing can happen yet", not "nothing to do". Read it before
    concluding a PR is clean. An empty `blockers` means reviews can proceed.
    """
    result = build_fetch_result(owner, repo, pr, gh_timeout=gh_timeout_seconds)
    typer.echo(result.model_dump_json())


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    *,
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    interval_seconds: Annotated[
        int, typer.Option(min=1, help="Seconds to sleep between polls. Must be positive.")
    ] = _DEFAULT_WATCH_INTERVAL_SECONDS,
    timeout_seconds: Annotated[
        int,
        typer.Option(
            min=0,
            help=(
                "Stop polling and return the current state after this many seconds. 0 takes one snapshot and returns."
            ),
        ),
    ] = _DEFAULT_WATCH_TIMEOUT_SECONDS,
    gh_timeout_seconds: Annotated[
        float | None,
        typer.Option(
            min=0,
            help="Seconds to bound the first `gh` calls to. Unbounded by default; polls are bounded by --timeout-seconds.",
        ),
    ] = None,
) -> None:
    """Poll `fetch` until outstanding review activity exists, or a timeout elapses.

    Blocks this process for up to `timeout_seconds`, re-fetching every `interval_seconds`. Returns
    the moment a poll's result satisfies `state.has_outstanding_work()` — at least one unresolved
    thread, at least one unresponded review, or Codex's approval reaction — or the final state once
    `timeout_seconds` elapses with none of those ever true. If the very first fetch already has
    outstanding work, `watch` returns immediately without sleeping at all: every check here is a
    fresh `gh` snapshot, not a diff against an earlier call, so there is nothing to wait for that
    the first fetch would have missed.

    Each call covers only its own `timeout_seconds` window. To watch for longer than one call's
    default window, issue `watch` again immediately after a `timed_out: true` result — its own
    first fetch picks up exactly where the previous call's last poll left off, so consecutive calls
    never miss activity in between (nothing here depends on what an earlier call saw). The
    receiving-pr-reviews SKILL.md documents this loop pattern.

    Prints the same compact JSON `fetch` prints, nested under `state`, plus `timed_out`. Check
    `state.reviewability.blockers` on a `timed_out: true` result before issuing another call:
    waiting out another window for reviews that cannot arrive — the PR is a draft, or conflicting —
    is pure waste, and the fix is on the PR rather than in the review queue.

    `deadline` is the only cutoff. The loop polls while a full `interval_seconds` still fits before
    it and stops once less than that remains — the point past which `gh_timeout_budget` would
    starve the call to nothing anyway. No fixed safety margin is reserved: this repository has no
    source for how long seven sequential `gh api` round trips take, and inventing one would be a
    guess (CLAUDE.md, "No invented constraints"). The final sub-interval stretch of a window is
    therefore left unpolled by design — the next `watch` call's own first fetch covers it, which is
    exactly why the loop pattern above is documented as back-to-back calls.

    Exits non-zero, with nothing printed to stdout, if the *last* re-poll attempted this window
    failed (a transient `gh` failure — see the exception handling inside the loop). An earlier
    success in the same window does not offset a later failure: what matters is whether the final
    stretch before `deadline` was actually confirmed, not whether any check ever succeeded. A
    `timed_out: true` result on stdout is only ever printed when the most recent check — the first
    fetch, or the last re-poll if one was attempted — succeeded, including the case where no
    re-poll was attempted at all because the window ended too soon for one, which is an honest
    "nothing to report," not a failure. A poll cut short by `deadline` itself is that same honest
    ending rather than a failure; a non-zero `gh` exit never is — see the two handlers below.
    """
    deadline = time.monotonic() + timeout_seconds
    # The first fetch is mandatory and is *not* deadline-bounded: with `--timeout-seconds 0` the
    # deadline is already spent, and starving this call would turn the documented immediate
    # snapshot into a `TimeoutExpired`. Only the polls below race the deadline.
    current = build_fetch_result(owner, repo, pr, gh_timeout=gh_timeout_seconds)
    poll_attempts = 0
    # Tracks the outcome of the most recent poll attempt, not a success count — a success earlier
    # in the window does not confirm the tail after a later failure. Starts True: the first fetch
    # above already succeeded (its own errors propagate uncaught, before the loop), so "no poll
    # attempted since" is itself a confirmed state, not an unknown one.
    last_poll_ok = True
    while not current.has_outstanding_work():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_seconds, remaining))
        if remaining <= interval_seconds:
            # That sleep consumed the rest of the window. `gh_timeout_budget` would bound a poll
            # here to nothing, so stop and report the last successfully-fetched state rather than
            # spawn a doomed call.
            break
        # Each of `build_fetch_result`'s seven `gh` calls is bounded to whatever's left before
        # `deadline` (see `gh_timeout_budget`), re-measured between them rather than split from a
        # fixed reservation.
        poll_attempts += 1
        # `watch` is meant to run unattended, often backgrounded (see the receiving-pr-reviews
        # skill's own gotchas on polling a backgrounded call for its own result); crashing on a
        # single bad poll loses the whole call's result. Both handlers below record the outcome and
        # let the loop continue toward `deadline` on its own schedule.
        try:
            current = build_fetch_result(owner, repo, pr, deadline=deadline, gh_timeout=gh_timeout_seconds)
            last_poll_ok = True
        except subprocess.TimeoutExpired:
            # A timeout is the one failure the clock can explain: `gh_timeout_budget` deliberately
            # shrinks each call to the time left, so the last poll of a window is *expected* to be
            # cut short. At or past `deadline` that is the same honest "no time left to check
            # again" this command reports when it stops before polling at all. With time still on
            # the clock it is a real network stall and leaves the tail unconfirmed.
            last_poll_ok = time.monotonic() >= deadline
            continue
        except subprocess.CalledProcessError:
            # A non-zero exit is an authentication, rate-limit, API or GraphQL error. The deadline
            # cannot cause it and cannot excuse it, so it is a failed poll whatever the clock says
            # — reporting `timed_out: true` off stale state here would tell a caller the PR is
            # clean when nothing was actually checked.
            last_poll_ok = False
            continue
    if poll_attempts and not last_poll_ok:
        # The most recent poll attempted this window raised — not just "every poll failed", but
        # specifically the *last* one, which is what actually matters: an earlier success in the
        # window does not confirm the tail after a later failure. Reporting `timed_out: true`
        # here would claim a confirmed check found nothing outstanding for the whole window, when
        # the final stretch before `deadline` was never actually observed.
        typer.echo(
            f"watch: the last of {poll_attempts} poll(s) this window failed — final state before "
            "deadline was never confirmed",
            err=True,
        )
        raise typer.Exit(code=1)
    result = WatchResult(timed_out=not current.has_outstanding_work(), state=current)
    typer.echo(result.model_dump_json())


@app.command()
def reply(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    comment_id: Annotated[int, typer.Option(help="Review comment databaseId, from `fetch`.")],
    body: Annotated[str, typer.Option(help="Reply text.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
    gh_timeout_seconds: Annotated[
        float | None, typer.Option(min=0, help="Seconds to bound the `gh` call to. Unbounded by default.")
    ] = None,
) -> None:
    """Reply to a review comment. Prints gh's created-comment response as compact JSON."""
    raw = run_gh(
        ["api", "-X", "POST", f"repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies", "-f", f"body={body}"],
        timeout=gh_timeout_seconds,
    )
    typer.echo(raw.strip())


@app.command()
def resolve(
    thread_id: Annotated[str, typer.Option(help="Review thread id, from `fetch`.")],
    gh_timeout_seconds: Annotated[
        float | None, typer.Option(min=0, help="Seconds to bound the `gh` call to. Unbounded by default.")
    ] = None,
) -> None:
    """Resolve a review thread. Prints gh's mutation response as compact JSON."""
    raw = run_gh(
        ["api", "graphql", "-f", f"query={RESOLVE_THREAD_MUTATION}", "-f", f"threadId={thread_id}"],
        timeout=gh_timeout_seconds,
    )
    typer.echo(raw.strip())


if __name__ == "__main__":
    app()
