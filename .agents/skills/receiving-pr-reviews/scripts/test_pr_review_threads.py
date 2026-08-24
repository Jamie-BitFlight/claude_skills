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
        "unresolved": [{"id": "T9", "path": "d.py", "comments": [], "comments_truncated": False}],
        "unresolved_count": 1,
    })
    mocker.patch.object(pr_review_threads, "_build_fetch_result", side_effect=[baseline, updated])
    mocker.patch.object(pr_review_threads.time, "sleep")

    # timeout-seconds must clear _MIN_POLL_BUDGET_SECONDS with real headroom: with time.sleep
    # mocked to a no-op, almost no wall-clock time elapses between polls, so a timeout right at
    # (or below) the guard threshold spuriously trips it before this test's second poll runs.
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

    # timeout-seconds must clear _MIN_POLL_BUDGET_SECONDS with real headroom: with time.sleep
    # mocked to a no-op, almost no wall-clock time elapses between polls, so a timeout right at
    # (or below) the guard threshold spuriously trips it before this test's second poll runs.
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


def test_watch_skips_final_poll_when_budget_too_low(mocker: MockerFixture) -> None:
    """`watch` stops polling, without attempting a doomed call, once the budget remaining before
    `deadline` drops below `_MIN_POLL_BUDGET_SECONDS`.

    Regression coverage: `_gh_timeout_budget` floors an exhausted deadline to 0.1s — far too
    little for a real `gh` call. Because `_DEFAULT_WATCH_TIMEOUT_SECONDS` is an exact multiple of
    `_DEFAULT_WATCH_INTERVAL_SECONDS` (270 / 90 = 3), the loop's final sleep lands within a
    fraction of a second of `deadline` on essentially every real run, so an unguarded poll there
    reliably raised `TimeoutExpired` instead of returning a clean `timed_out` result. Mocks
    `time.monotonic` to a fixed sequence matching the loop's real call order (deadline
    computation, the loop condition, the sleep-duration calculation, the budget check) so the
    near-deadline condition is reproduced without a real wait.
    """
    baseline = FetchResult(reviews_count=0, reviews_with_body=[], threads_count=0, unresolved=[], unresolved_count=0)
    fetch_mock = mocker.patch.object(pr_review_threads, "_build_fetch_result", return_value=baseline)
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline = 0.0 + 100), 0.0 (loop condition), 0.0 (sleep-duration calc), 96.0 (budget
    # check: 100.0 - 96.0 = 4.0 < _MIN_POLL_BUDGET_SECONDS's 5.0 — guard fires, loop breaks).
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 96.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "90", "--timeout-seconds", "100"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    # Only the baseline fetch happened — the guard prevented a second, doomed poll attempt.
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
        "unresolved": [{"id": "T9", "path": "d.py", "comments": [], "comments_truncated": False}],
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
    sequence for exactly two failed poll attempts (each iteration: loop condition, sleep-duration
    calc, guard check) followed by the window naturally expiring, matching the real function's
    call order the same way `test_watch_skips_final_poll_when_budget_too_low` does.
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
    # 0.0 (deadline = 0.0 + 100). Iter 1: 0.0 (loop cond), 0.0 (sleep calc), 10.0 (guard: 100-10=90
    # ≥ 5.0, doesn't fire) → poll raises TimeoutExpired. Iter 2: 20.0, 20.0, 30.0 (guard: 70 ≥ 5.0)
    # → poll raises CalledProcessError. Then 105.0 (loop cond: 105 ≥ 100 → loop ends naturally).
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 10.0, 20.0, 20.0, 30.0, 105.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 2 poll(s) this window failed" in result.output
    # No `timed_out`/`state` JSON was ever printed to stdout — only the failure message above.
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


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
    # Same 8-call shape as the all-fail test above, but iter 1's poll succeeds this time (finding
    # nothing new, so the loop does not break) before iter 2's poll fails as the window ends.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 10.0, 20.0, 20.0, 30.0, 105.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 2 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)
