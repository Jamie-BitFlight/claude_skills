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

import json
import subprocess
import time
from typing import Annotated

import typer
from pydantic import ValidationError

from pr_review_gh import RESOLVE_THREAD_MUTATION, build_fetch_result, detect_repo_identity, run_gh
from pr_review_models import FetchResult, ReviewNode, UnresolvedThread, WatchResult

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


def _validate_github_option(value: str | None) -> str | None:
    """Typer callback: reject a malformed `--github` value before any command body runs.

    Args:
        value: The raw `--github` argument, or `None` when the flag was not passed.

    Returns:
        `value` unchanged, once confirmed to be `None` or `"owner/repo"` with both halves
        non-empty.

    Raises:
        typer.BadParameter: `value` is not exactly one `/` with both halves non-empty.
    """
    if value is None:
        return None
    owner, separator, repo = value.partition("/")
    if not separator or not owner or not repo or "/" in repo:
        message = "must be 'owner/repo' -- exactly one '/', with both halves non-empty"
        raise typer.BadParameter(message)
    return value


# Shared by every command that targets a specific repository (`fetch`, `watch`, `reply`) so the
# flag, its help text, and its format validation stay identical across all three rather than
# duplicated per command.
GithubOption = Annotated[
    str | None,
    typer.Option(
        "--github",
        help="Target repository as 'owner/repo'. Detected via `gh repo view` when omitted.",
        callback=_validate_github_option,
    ),
]


def _owner_repo(github: str | None, *, gh_timeout: float | None) -> tuple[str, str]:
    """Resolve the `(owner, repo)` to operate on: an explicit `--github` override, or autodetected.

    Detection relies entirely on `gh repo view`'s own remote resolution for this checkout -- see
    `pr_review_gh.detect_repo_identity`. A wrong owner/repo would send a reply to the wrong
    repository, so a failed detection stops the command rather than falling back to a guess
    (CLAUDE.md, "No invented constraints").

    Args:
        github: The `--github` value, already format-validated by `_validate_github_option`, or
            `None` to autodetect.
        gh_timeout: Seconds to bound the detection `gh` call to, or `None` for no bound.

    Returns:
        The `(owner, repo)` pair to query.

    Raises:
        typer.Exit: Autodetection was attempted (no `--github` given) and failed -- `gh` is
            missing, unauthenticated, or this checkout has no GitHub remote `gh` recognizes.
            Exits with code 1; nothing else is printed to stdout.
    """
    if github is not None:
        owner, repo = github.split("/", 1)
        return owner, repo
    try:
        return detect_repo_identity(gh_timeout=gh_timeout)
    except (FileNotFoundError, subprocess.CalledProcessError, ValidationError) as exc:
        typer.echo(
            f"Could not detect this checkout's GitHub repository via `gh repo view` ({exc}). "
            "Pass --github owner/repo to specify it explicitly.",
            err=True,
        )
        raise typer.Exit(code=1) from exc


def _parse_pr_list(value: str) -> list[int]:
    """Parse a `--pr` value into pull request numbers, in the order given.

    Args:
        value: Raw `--pr` argument, e.g. `"3208"` or `"41,42,44"`. Whitespace around each
            comma-separated part is stripped, so `"41, 42"` works too.

    Returns:
        Every PR number, in the order given. Duplicates are kept as-is -- a caller who typed one
        twice presumably wants it reported twice, and deduping would be an unrequested guess about
        intent.

    Raises:
        typer.BadParameter: `value` is empty, or any comma-separated part is not a plain integer.
    """
    parts = [part.strip() for part in value.split(",")]
    if not all(parts):
        message = "must be one or more PR numbers, comma-separated (e.g. '41,42,44')"
        raise typer.BadParameter(message)
    try:
        return [int(part) for part in parts]
    except ValueError as exc:
        raise typer.BadParameter(f"not a valid PR number: {exc}") from exc


def _truncate_body(body: str, max_body: int | None) -> str:
    """Cut `body` to `max_body` characters, marking the cut visibly rather than silently.

    `max_body=None` (the default) returns `body` unchanged. Unlimited-by-default matters here: a
    silently truncated body forces re-verifying separately that nothing load-bearing (e.g. Codex's
    own trailing footer) fell past the cut before trusting the summary at all.

    Args:
        body: The raw comment/review body text.
        max_body: The character limit, or `None` for no limit.

    Returns:
        `body` unchanged, or its first `max_body` characters followed by a visible
        `"...[truncated, showing N/M chars]"` marker.
    """
    if max_body is None or len(body) <= max_body:
        return body
    return f"{body[:max_body]}...[truncated, showing {max_body}/{len(body)} chars]"


def _summarize_thread(thread: UnresolvedThread, *, max_body: int | None) -> dict[str, object]:
    """Reduce one unresolved thread to the fields `--summary` needs.

    Ids, its opening comment, and -- when the thread has follow-ups -- its latest comment too.
    `comment_id`/`author`/`body` always come from the thread's *first* comment -- the one that
    opened it, and the one `reply`'s `--comment-id` must target regardless of how the discussion
    continued (GitHub rejects a reply targeted at another reply). But the opening comment alone can
    be stale: a reviewer's later reply in the same thread can clarify or renew an objection the
    opening comment never carried, and reading only the opener risks answering and resolving a
    thread against feedback that has since moved on. `comment_count` names how many comments the
    thread actually has; `latest_author`/`latest_body` are added only when it is more than one, so
    a single-comment thread (the common case) costs nothing extra. The full comment history stays
    available via a plain (non-`--summary`) `fetch`.

    Args:
        thread: One entry from `FetchResult.unresolved`.
        max_body: Forwarded to `_truncate_body`.

    Returns:
        A dict with `thread_id`, `comment_id`, `path`, `line`, `comment_count`, `author`, `body`,
        plus `latest_author`/`latest_body` when `comment_count > 1`.
    """
    first = thread.comments[0]
    summary: dict[str, object] = {
        "thread_id": thread.id,
        "comment_id": first.databaseId,
        "path": thread.path,
        "line": first.line,
        "comment_count": len(thread.comments),
        "author": first.author.login if first.author is not None else None,
        "body": _truncate_body(first.body, max_body),
    }
    if len(thread.comments) > 1:
        latest = thread.comments[-1]
        summary["latest_author"] = latest.author.login if latest.author is not None else None
        summary["latest_body"] = _truncate_body(latest.body, max_body)
    return summary


def _summarize_review(review: ReviewNode, *, max_body: int | None) -> dict[str, object]:
    """Reduce one unresponded review to the fields `--summary` needs.

    Args:
        review: One entry from `FetchResult.unresponded_reviews`.
        max_body: Forwarded to `_truncate_body`.

    Returns:
        A dict with `author`, `state`, `url`, `body`.
    """
    return {
        "author": review.author.login if review.author is not None else None,
        "state": review.state,
        "url": review.url,
        "body": _truncate_body(review.body, max_body),
    }


def _summarize(result: FetchResult, *, pr: int, max_body: int | None) -> dict[str, object]:
    """Build the reduced-field dict `--summary` prints for one `FetchResult` snapshot.

    Carries exactly what the receiving-pr-reviews workflow reads on every call instead of the full
    JSON `fetch` prints by default: the outcome counts, `reviewability.blockers` (always present,
    even empty -- an empty `unresolved` with a non-empty `blockers` means something different from
    a clean PR, see `fetch`'s own docstring), every unresolved thread's id/first-comment
    id/path/line/author/body, and every unresponded review's author/state/url/body. Thread and
    comment ids are kept rather than replaced by a human-readable digest -- `reply` and `resolve`
    need them, and omitting them would force a second full `fetch` to recover them.

    Args:
        result: A fresh `FetchResult` (or `WatchResult.state`) to reduce.
        pr: The PR number this snapshot is for, stamped onto the summary so multi-`--pr` output is
            self-describing per block.
        max_body: Forwarded to `_truncate_body`.

    Returns:
        A JSON-serializable dict with the reduced fields.
    """
    return {
        "pr": pr,
        "reviews_count": result.reviews_count,
        "threads_count": result.threads_count,
        "unresolved_count": result.unresolved_count,
        "unresponded_count": len(result.unresponded_reviews),
        "codex_approved": result.codex_approved,
        "blockers": result.reviewability.blockers,
        "unresolved": [_summarize_thread(thread, max_body=max_body) for thread in result.unresolved],
        "unresponded_reviews": [_summarize_review(review, max_body=max_body) for review in result.unresponded_reviews],
    }


def _board_entry(pr: int, result: FetchResult) -> dict[str, object]:
    """One PR's status entry for the multi-`--pr` `fetch` board.

    The default output when several PRs are checked without `--summary`. A dict, not a formatted
    string: this repository's own CLI-output policy (AGENTS.md, "CLI and
    script output — agent-only, never human-facing") requires structured output to be JSON with an
    explicit repeated key per value, not a text table or a hand-built `key=value` line, since only
    an agent ever reads this. `mergeable`/`merge_state_status` are included alongside `blockers`
    because `blockers` alone doesn't say whether a PR is landable -- it can be empty (reviews
    aren't blocked) while the PR is still unresolved or otherwise unmergeable, which is the
    difference between "quiet" and "ready".

    Args:
        pr: The PR number this entry is for.
        result: Its fresh `FetchResult` snapshot.

    Returns:
        A dict with `pr`, `unresolved`, `unresponded`, `codex_approved`, `mergeable`,
        `merge_state_status`, `blockers`.
    """
    return {
        "pr": pr,
        "unresolved": result.unresolved_count,
        "unresponded": len(result.unresponded_reviews),
        "codex_approved": result.codex_approved,
        "mergeable": result.reviewability.mergeable,
        "merge_state_status": result.reviewability.merge_state_status,
        "blockers": result.reviewability.blockers,
    }


SummaryOption = Annotated[
    bool,
    typer.Option(
        "--summary",
        help=(
            "Print only the counts, blockers, and per-thread/per-review fields an agent actually "
            "acts on, instead of the full JSON."
        ),
    ),
]
MaxBodyOption = Annotated[
    int | None,
    typer.Option(
        "--max-body",
        min=1,
        help="With --summary, cut each printed body to this many characters (visibly marked). Unlimited by default.",
    ),
]


@app.command()
def fetch(
    pr: Annotated[str, typer.Option(help="Pull request number(s). Comma-separated for multiple, e.g. 41,42,44.")],
    github: GithubOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
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

    `--pr` takes a single number or a comma-separated list (`--pr 41,42,44`) to check several PRs
    in one call, in the order given. With one `--pr` number, `--summary` prints the reduced-field
    JSON described on `_summarize` instead of the full result above; without it, one compact-JSON
    board entry per PR (see `_board_entry`) — `--summary` with several PRs still gets the full
    per-PR summary JSON, one compact-JSON line per PR.
    """
    # Parsed before `_owner_repo` resolves the repository: a malformed `--pr` must be rejected
    # before any `gh` call is attempted (including autodetection's `gh repo view`), the same
    # reject-before-any-`gh`-call rule `_validate_github_option`'s callback already follows.
    pr_numbers = _parse_pr_list(pr)
    owner, repo = _owner_repo(github, gh_timeout=gh_timeout_seconds)
    if len(pr_numbers) == 1 and not summary:
        result = build_fetch_result(owner, repo, pr_numbers[0], gh_timeout=gh_timeout_seconds)
        typer.echo(result.model_dump_json())
        return
    for number in pr_numbers:
        result = build_fetch_result(owner, repo, number, gh_timeout=gh_timeout_seconds)
        if summary:
            typer.echo(json.dumps(_summarize(result, pr=number, max_body=max_body)))
        else:
            typer.echo(json.dumps(_board_entry(number, result)))


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number. Single PR only -- watch polls one target.")],
    *,
    github: GithubOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
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

    `--summary` prints the same reduced fields `fetch --summary` does (see `_summarize`), with
    `timed_out` and every summary field flattened at the top level rather than nested under `state`
    — `fetch`'s and `watch`'s summaries are the same shape, so one parser handles either.

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
    owner, repo = _owner_repo(github, gh_timeout=gh_timeout_seconds)
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
    timed_out = not current.has_outstanding_work()
    if summary:
        payload = _summarize(current, pr=pr, max_body=max_body)
        payload["timed_out"] = timed_out
        typer.echo(json.dumps(payload))
        return
    result = WatchResult(timed_out=timed_out, state=current)
    typer.echo(result.model_dump_json())


@app.command()
def reply(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    comment_id: Annotated[int, typer.Option(help="Review comment databaseId, from `fetch`.")],
    body: Annotated[str, typer.Option(help="Reply text.")],
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[
        float | None, typer.Option(min=0, help="Seconds to bound the `gh` call to. Unbounded by default.")
    ] = None,
) -> None:
    """Reply to a review comment. Prints gh's created-comment response as compact JSON."""
    owner, repo = _owner_repo(github, gh_timeout=gh_timeout_seconds)
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
