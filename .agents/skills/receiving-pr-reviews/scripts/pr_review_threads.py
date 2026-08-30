#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
# ]
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
_DEFAULT_WATCH_TIMEOUT_SECONDS = 270

# `gh_timeout_budget` floors a near-zero remainder to 0.1s — enough to keep the return type
# positive, not enough for a real `gh api graphql` round trip. `_DEFAULT_WATCH_TIMEOUT_SECONDS`
# being an exact multiple of `_DEFAULT_WATCH_INTERVAL_SECONDS` (270 / 90 = 3) means the loop's
# final sleep lands within a fraction of a second of `deadline` on essentially every run, so an
# unguarded poll there is starved to that floor and reliably raises `TimeoutExpired` — not a
# flaky network failure. `watch`'s loop skips a poll once the remaining budget drops below this,
# rather than attempting one that is near-certain to fail.
# ponytail: 5.0 is an unmeasured heuristic, not a proven-sufficient margin for seven sequential `gh
# api` round trips — `build_fetch_result` makes seven such calls, and if the earlier ones eat most
# of this budget the last can still be starved. The exception handler around the poll in `watch`
# is the real backstop for that case, not this guard alone; raise this value if starvation is
# observed in practice with the guard already in place.
_MIN_POLL_BUDGET_SECONDS = 5.0


@app.command()
def fetch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    owner: Annotated[str, typer.Option(help="Repository owner.")] = DEFAULT_OWNER,
    repo: Annotated[str, typer.Option(help="Repository name.")] = DEFAULT_REPO,
) -> None:
    """Fetch a PR's outstanding review activity, auto-paginated so none is silently truncated.

    Prints compact JSON with `reviews_count`, `threads_count`, `unresolved`, `unresolved_count`,
    `reviews_with_body`, `unresponded_reviews`, and `codex_approved`. A `threads_count` of 0 means
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
    """
    result = build_fetch_result(owner, repo, pr)
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

    Prints the same compact JSON `fetch` prints, nested under `state`, plus `timed_out`.

    Reserves `_MIN_POLL_BUDGET_SECONDS` before `deadline` (shortening the final sleep rather than
    sleeping all the way to `deadline`), so a normal-length last leg still gets a real final poll
    instead of being silently skipped — under the default interval/timeout, the whole window
    through shortly before `deadline` gets checked, not just up through the second-to-last
    interval. Only a pathologically short `--timeout-seconds`, or a poll that overruns its own
    interval, leaves no room for that final attempt.

    Exits non-zero, with nothing printed to stdout, if the *last* re-poll attempted this window
    failed (a transient `gh` failure — see the exception handling inside the loop). An earlier
    success in the same window does not offset a later failure: what matters is whether the final
    stretch before `deadline` was actually confirmed, not whether any check ever succeeded. A
    `timed_out: true` result on stdout is only ever printed when the most recent check — the first
    fetch, or the last re-poll if one was attempted — succeeded, including the case where no
    re-poll was attempted at all because the window ended too soon for one, which is an honest
    "nothing to report," not a failure.
    """
    deadline = time.monotonic() + timeout_seconds
    current = build_fetch_result(owner, repo, pr, deadline=deadline)
    poll_attempts = 0
    # Tracks the outcome of the most recent poll attempt, not a success count — a success earlier
    # in the window does not confirm the tail after a later failure. Starts True: the first fetch
    # above already succeeded (its own errors propagate uncaught, before the loop), so "no poll
    # attempted since" is itself a confirmed state, not an unknown one.
    last_poll_ok = True
    while not current.has_outstanding_work() and time.monotonic() < deadline:
        # Sleep only up to `deadline - _MIN_POLL_BUDGET_SECONDS`, not all the way to `deadline`
        # itself — reserving that much time means the final poll below is attempted with a real
        # chance to complete, rather than skipped.
        time.sleep(max(0.0, min(interval_seconds, deadline - _MIN_POLL_BUDGET_SECONDS - time.monotonic())))
        if deadline - time.monotonic() < _MIN_POLL_BUDGET_SECONDS:
            # Only reached when there wasn't even `_MIN_POLL_BUDGET_SECONDS` left at the start of
            # this iteration (a pathologically short `--timeout-seconds`, or a previous poll that
            # ran long) — the sleep above already couldn't reserve it. `gh_timeout_budget` would
            # otherwise starve a call here to a floor too small to succeed; stop polling and
            # report the last successfully-fetched state instead of attempting a call that cannot
            # complete.
            break
        poll_attempts += 1
        try:
            current = build_fetch_result(owner, repo, pr, deadline=deadline)
            last_poll_ok = True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            last_poll_ok = False
            # A genuine transient `gh` failure mid-window (network hiccup, momentary GitHub
            # error). `watch` is meant to run unattended, often backgrounded; crashing here loses
            # the whole call's result instead of just this one poll. Treat it as no fresh data
            # this poll and let the loop continue toward `deadline` on its own schedule.
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
) -> None:
    """Reply to a review comment. Prints gh's created-comment response as compact JSON."""
    raw = run_gh([
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
    raw = run_gh(["api", "graphql", "-f", f"query={RESOLVE_THREAD_MUTATION}", "-f", f"threadId={thread_id}"])
    typer.echo(raw.strip())


if __name__ == "__main__":
    app()
