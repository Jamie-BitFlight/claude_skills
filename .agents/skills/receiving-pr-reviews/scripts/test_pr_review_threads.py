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
from typing import TYPE_CHECKING

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

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "5"])

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

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "5"])

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
