#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
#   "pytest",
#   "pytest-mock",
# ]
# ///
"""Tests for pr_review_threads.py.

Covers the non-trivial logic identified in review: `_build_fetch_result`'s multi-page
flattening, resolved-thread filtering, `comments_truncated` derivation, and
`reviews_with_body` filtering (including a null `author`, which a deleted GitHub account
produces); and `watch`'s baseline-diff — both the "new activity found" and "timed out with
none" outcomes.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_threads import FetchResult, app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()


def _thread_page(*, has_next_page: bool, nodes: list[dict[str, object]], total_count: int) -> dict[str, object]:
    """Build one slurped `--paginate --slurp` page for the reviewThreads query."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "totalCount": total_count,
                        "pageInfo": {"hasNextPage": has_next_page, "endCursor": None},
                        "nodes": nodes,
                    }
                }
            }
        }
    }


def _reviews_page(*, nodes: list[dict[str, object]], total_count: int) -> dict[str, object]:
    """Build one slurped `--paginate --slurp` page for the reviews query."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviews": {
                        "totalCount": total_count,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": nodes,
                    }
                }
            }
        }
    }


def test_fetch_flattens_pages_filters_resolved_and_handles_null_author(mocker: MockerFixture) -> None:
    """`fetch` flattens multi-page thread results, dropping resolved threads and counting right.

    Two thread pages are fed to `_run_gh` (page 1 has a resolved and an unresolved thread; page
    2's lone thread has `comments.pageInfo.hasNextPage: true`). One reviews page has a review
    with a null `author` (a deleted account) alongside an empty-body review — both must be
    parsed without error, and only the non-empty-body review must survive into
    `reviews_with_body`.
    """
    thread_pages = [
        _thread_page(
            total_count=3,
            has_next_page=True,
            nodes=[
                {
                    "id": "T1",
                    "isResolved": False,
                    "path": "a.py",
                    "comments": {
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {"databaseId": 1, "body": "hi", "line": 5, "originalLine": 5, "author": {"login": "codex"}}
                        ],
                    },
                },
                {
                    "id": "T2",
                    "isResolved": True,
                    "path": "b.py",
                    "comments": {
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "databaseId": 2,
                                "body": "already resolved",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "codex"},
                            }
                        ],
                    },
                },
            ],
        ),
        _thread_page(
            total_count=3,
            has_next_page=False,
            nodes=[
                {
                    "id": "T3",
                    "isResolved": False,
                    "path": "c.py",
                    "comments": {
                        "totalCount": 101,
                        "pageInfo": {"hasNextPage": True},
                        # A comment left by a since-deleted account — `author` is null.
                        "nodes": [
                            {"databaseId": 3, "body": "flagged", "line": None, "originalLine": 10, "author": None}
                        ],
                    },
                }
            ],
        ),
    ]
    reviews_pages = [
        _reviews_page(
            total_count=2,
            nodes=[
                {"id": "R1", "author": {"login": "codex"}, "state": "COMMENTED", "body": "Some feedback"},
                {"id": "R2", "author": None, "state": "APPROVED", "body": ""},
            ],
        )
    ]
    mocker.patch.object(pr_review_threads, "_run_gh", side_effect=[json.dumps(thread_pages), json.dumps(reviews_pages)])

    result = runner.invoke(app, ["fetch", "--pr", "3208"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["threads_count"] == 3
    assert data["unresolved_count"] == 2
    unresolved_ids = {thread["id"] for thread in data["unresolved"]}
    assert unresolved_ids == {"T1", "T3"}
    truncated_by_id = {thread["id"]: thread["comments_truncated"] for thread in data["unresolved"]}
    assert truncated_by_id == {"T1": False, "T3": True}
    # `comments_total` comes from the thread's own totalCount, not the returned node count:
    # T3 reports 101 while only one comment fits the query's page.
    totals_by_id = {thread["id"]: thread["comments_total"] for thread in data["unresolved"]}
    assert totals_by_id == {"T1": 1, "T3": 101}
    assert data["reviews_count"] == 2
    assert len(data["reviews_with_body"]) == 1
    assert data["reviews_with_body"][0]["author"]["login"] == "codex"


def test_watch_reports_new_thread_when_activity_appears(mocker: MockerFixture) -> None:
    """`watch` returns `timed_out: False` and the new thread id as soon as a poll finds one."""
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    updated = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [{"id": "T9", "path": "d.py", "comments": [], "comments_total": 0, "comments_truncated": False}],
        "unresolved_count": 1,
    })
    mocker.patch.object(pr_review_threads, "_build_fetch_result", side_effect=[baseline, updated])
    mocker.patch.object(pr_review_threads.time, "sleep")

    # timeout-seconds must exceed interval-seconds: the loop stops once less than one interval
    # remains, and with time.sleep mocked to a no-op almost no wall-clock time elapses, so the
    # first iteration must find a full interval's headroom for this test's second poll to run.
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["new_thread_ids"] == ["T9"]
    assert data["new_reviews_with_body"] == []


def test_watch_reports_edited_review_with_unchanged_id(mocker: MockerFixture) -> None:
    """`watch` treats a baseline review whose body/state changed as new activity, same id or not.

    Regression coverage for comparing reviews by id alone: a reviewer editing an existing review
    (GitHub keeps its GraphQL id stable across edits) must still be detected — SKILL.md documents
    this as counting as new activity.
    """
    review_v1 = {"id": "R1", "author": {"login": "codex"}, "state": "COMMENTED", "body": "first pass"}
    review_v2 = {"id": "R1", "author": {"login": "codex"}, "state": "COMMENTED", "body": "edited after more thought"}
    baseline = FetchResult.model_validate({
        "reviews_count": 1,
        "reviews_with_body": [review_v1],
        "threads_count": 0,
        "unresolved": [],
        "unresolved_count": 0,
    })
    edited = FetchResult.model_validate({
        "reviews_count": 1,
        "reviews_with_body": [review_v2],
        "threads_count": 0,
        "unresolved": [],
        "unresolved_count": 0,
    })
    mocker.patch.object(pr_review_threads, "_build_fetch_result", side_effect=[baseline, edited])
    mocker.patch.object(pr_review_threads.time, "sleep")

    # timeout-seconds must exceed interval-seconds: the loop stops once less than one interval
    # remains, and with time.sleep mocked to a no-op almost no wall-clock time elapses, so the
    # first iteration must find a full interval's headroom for this test's second poll to run.
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert len(data["new_reviews_with_body"]) == 1
    assert data["new_reviews_with_body"][0]["body"] == "edited after more thought"


def test_watch_times_out_when_no_new_activity(mocker: MockerFixture) -> None:
    """`watch` returns `timed_out: True` when `timeout_seconds` elapses with nothing new."""
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    mocker.patch.object(pr_review_threads, "_build_fetch_result", return_value=baseline)

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    assert data["new_thread_ids"] == []
    assert data["new_reviews_with_body"] == []


def test_watch_stops_when_less_than_one_interval_remains(mocker: MockerFixture) -> None:
    """`watch` stops without attempting a doomed call once under one interval remains.

    `_gh_timeout_budget` floors an exhausted deadline to 0.1s — far too little for a real `gh`
    call — so when the sleep consumes the rest of the window there is nothing left to poll with.
    The cutoff is `deadline` itself rather than an invented safety margin: with
    `--timeout-seconds 50` and `--interval-seconds 90` the very first sleep covers the whole
    window, so no poll is attempted and the baseline is reported as an honest `timed_out: true`.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    fetch_mock = mocker.patch.object(pr_review_threads, "_build_fetch_result", return_value=baseline)
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline = 0.0 + 50), 0.0 (remaining = 50, which is <= the 90s interval → break).
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "90", "--timeout-seconds", "50"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    # Only the baseline fetch happened — no second, doomed poll attempt.
    assert fetch_mock.call_count == 1


def test_watch_survives_transient_gh_failure_mid_window(mocker: MockerFixture) -> None:
    """A transient `gh` failure during a poll (network hiccup, momentary GitHub error) does not
    crash `watch` — it counts as no fresh data for that one poll, and the loop continues toward
    `deadline` on its own schedule rather than propagating the exception.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    updated = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [{"id": "T9", "path": "d.py", "comments": [], "comments_total": 0, "comments_truncated": False}],
        "unresolved_count": 1,
    })
    mocker.patch.object(
        pr_review_threads,
        "_build_fetch_result",
        side_effect=[baseline, subprocess.TimeoutExpired(cmd=["gh"], timeout=30), updated],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["new_thread_ids"] == ["T9"]


def test_watch_fails_loudly_when_every_poll_fails(mocker: MockerFixture) -> None:
    """`watch` exits non-zero, printing nothing to stdout, when every re-poll attempted this
    window fails.

    Regression coverage for a Codex review on the fix that introduced the try/except around each
    poll: silently returning `timed_out: true` here would claim a confirmed check found nothing
    new, when no check after the baseline ever succeeded — a caller trusting that signal would
    wrongly conclude the PR is clean instead of retrying. Mocks `time.monotonic` to a fixed
    sequence for exactly two failed poll attempts (one clock read per iteration, plus one in the
    exception handler to tell a real failure from the window simply ending) followed by the
    window naturally expiring.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    mocker.patch.object(
        pr_review_threads,
        "_build_fetch_result",
        side_effect=[
            baseline,
            subprocess.TimeoutExpired(cmd=["gh"], timeout=30),
            subprocess.CalledProcessError(1, ["gh"]),
        ],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline = 0.0 + 100). Iter 1: 0.0 (remaining=100 > the 10s interval) → poll raises
    # TimeoutExpired, whose handler reads 10.0 (< deadline → a real failure). Iter 2: 20.0
    # (remaining=80) → poll raises CalledProcessError, whose handler reads no clock at all: a
    # non-zero exit is never excused by the deadline. Then 105.0 → remaining negative, loop ends.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 10.0, 20.0, 105.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 2 poll(s) this window failed" in result.output
    # No `timed_out`/`state` JSON was ever printed to stdout — only the failure message above.
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


def test_watch_treats_a_deadline_truncated_poll_as_an_honest_timeout(mocker: MockerFixture) -> None:
    """A poll that fails once `deadline` has passed is the window ending, not an unconfirmed tail.

    Regression coverage for the Codex finding that replaced an invented five-second reservation:
    `_gh_timeout_budget` deliberately shrinks each `gh` call to whatever time is left, so the last
    poll of a window is *expected* to be cut short. Classifying that as a failure would exit
    non-zero on ordinary runs; classifying a failure that lands with time still on the clock as
    success would hide a genuine transient error. Only the clock distinguishes them.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    fetch_mock = mocker.patch.object(
        pr_review_threads,
        "_build_fetch_result",
        side_effect=[baseline, subprocess.TimeoutExpired(cmd=["gh"], timeout=30)],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline=100). Iter 1: 0.0 (remaining=100 > the 10s interval) → poll raises; 100.0 in
    # the handler (>= deadline → the window ended, not a failure). Iter 2: 100.0 → remaining 0.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 100.0, 100.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["timed_out"] is True
    assert fetch_mock.call_count == 2


def test_watch_reports_a_reply_to_an_already_known_thread(mocker: MockerFixture) -> None:
    """A reply on a thread the baseline already listed counts as new activity.

    Regression coverage for the Codex finding that the baseline diff compared thread ids only: a
    reply leaves the thread's id unchanged, so the set difference stayed empty and `watch` reported
    `timed_out: true` while an unread comment sat in `unresolved`.
    """
    comment = {"databaseId": 11, "body": "first", "line": 1, "originalLine": 1, "author": {"login": "codex"}}
    reply_comment = {"databaseId": 12, "body": "and another thing", "line": 1, "originalLine": 1, "author": None}
    baseline = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [
            {"id": "T1", "path": "a.py", "comments": [comment], "comments_total": 1, "comments_truncated": False}
        ],
        "unresolved_count": 1,
    })
    replied = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [
            {
                "id": "T1",
                "path": "a.py",
                "comments": [comment, reply_comment],
                "comments_total": 2,
                "comments_truncated": False,
            }
        ],
        "unresolved_count": 1,
    })
    mocker.patch.object(pr_review_threads, "_build_fetch_result", side_effect=[baseline, replied])
    mocker.patch.object(pr_review_threads.time, "sleep")

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["new_thread_ids"] == ["T1"]


def test_watch_rejects_a_non_positive_interval() -> None:
    """`--interval-seconds 0` would busy-loop `gh` calls until the timeout; Typer must reject it."""
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "0"])

    assert result.exit_code != 0


def test_watch_reports_an_edit_to_an_existing_comment(mocker: MockerFixture) -> None:
    """Editing an unresolved comment counts as new activity.

    Regression coverage for the Codex finding that an edit changes neither the comment's
    `databaseId` nor the thread's `comments_total`, so an id-and-count key saw no change.
    """
    before = {"databaseId": 11, "body": "first pass", "line": 1, "originalLine": 1, "author": {"login": "codex"}}
    after = before | {"body": "edited after more thought"}
    thread = {"id": "T1", "path": "a.py", "comments_total": 1, "comments_truncated": False}
    baseline = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [thread | {"comments": [before]}],
        "unresolved_count": 1,
    })
    edited = FetchResult.model_validate({
        "reviews_count": 0,
        "reviews_with_body": [],
        "threads_count": 1,
        "unresolved": [thread | {"comments": [after]}],
        "unresolved_count": 1,
    })
    mocker.patch.object(pr_review_threads, "_build_fetch_result", side_effect=[baseline, edited])
    mocker.patch.object(pr_review_threads.time, "sleep")

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["new_thread_ids"] == ["T1"]


def test_watch_fails_loudly_on_a_nonzero_gh_exit_at_the_deadline(mocker: MockerFixture) -> None:
    """A non-zero `gh` exit is a failed poll whatever the clock says.

    Regression coverage for the Codex finding that the deadline-aware classification was applied to
    `CalledProcessError` as well as `TimeoutExpired`. Only a timeout can be explained by the
    shrinking budget; an authentication, rate-limit, API or GraphQL error cannot, so reporting
    `timed_out: true` from stale state would tell a caller the PR is clean when nothing was checked.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    mocker.patch.object(
        pr_review_threads, "_build_fetch_result", side_effect=[baseline, subprocess.CalledProcessError(1, ["gh"])]
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline=100). Iter 1: 0.0 (remaining=100 > the 10s interval) -> poll raises; the handler
    # reads 100.0, which would have excused a TimeoutExpired but must not excuse this.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 100.0, 100.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 1 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


def test_watch_rejects_a_negative_timeout() -> None:
    """`--timeout-seconds` is constrained to >= 0; 0 is the supported immediate-snapshot value."""
    assert runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "-1"]).exit_code != 0


def test_watch_baseline_is_not_deadline_bounded(mocker: MockerFixture) -> None:
    """`--timeout-seconds 0` returns an immediate snapshot rather than starving the baseline.

    Regression coverage for the Codex finding that an already-spent deadline was applied to the
    mandatory baseline fetch, flooring its `gh` timeout and raising `TimeoutExpired` instead of
    producing the documented snapshot. The baseline takes the caller's `--gh-timeout-seconds`
    instead; only the polls race `deadline`.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    fetch_mock = mocker.patch.object(pr_review_threads, "_build_fetch_result", return_value=baseline)

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["timed_out"] is True
    assert fetch_mock.call_args.kwargs == {"gh_timeout": None}


def test_gh_timeout_budget_without_a_deadline_uses_the_callers_bound() -> None:
    """No deadline means the caller's `--gh-timeout-seconds` applies unchanged, `None` included."""
    assert pr_review_threads._gh_timeout_budget(None, None) is None
    assert pr_review_threads._gh_timeout_budget(None, 12.5) == pytest.approx(12.5)


def test_gh_timeout_budget_with_a_deadline_uses_the_time_left() -> None:
    """A poll's bound is the time left before `deadline`, floored at zero once it has passed."""
    now = time.monotonic()

    assert pr_review_threads._gh_timeout_budget(now + 30, None) == pytest.approx(30, abs=1)
    assert pr_review_threads._gh_timeout_budget(now - 30, None) == pytest.approx(0.0)


def test_watch_fails_loudly_when_only_final_poll_fails(mocker: MockerFixture) -> None:
    """`watch` fails loudly when the *last* poll fails, even if an earlier poll in the same
    window succeeded.

    Regression coverage for a second Codex review, on the fix above: tracking whether *any* poll
    succeeded is not enough — an early success does not confirm the tail of the window after a
    later failure. If poll 1 succeeds (finding nothing new) and poll 2 then fails as the window
    ends, `current` is stale (still poll 1's data) and the final stretch before `deadline` was
    never actually observed; `watch` must still fail rather than report a `timed_out: true` built
    from that stale state.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    mocker.patch.object(
        pr_review_threads,
        "_build_fetch_result",
        side_effect=[baseline, baseline, subprocess.TimeoutExpired(cmd=["gh"], timeout=30)],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline=100). Iter 1: 0.0 (remaining=100) → poll succeeds, so the handler reads no
    # clock. Iter 2: 20.0 (remaining=80) → poll raises, handler reads 30.0 (< deadline → a real
    # failure, not the window ending). Then 105.0 → remaining negative, loop ends.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 20.0, 30.0, 105.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 2 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)
