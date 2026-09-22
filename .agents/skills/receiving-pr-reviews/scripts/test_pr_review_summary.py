#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "pytest-mock",
#   "pytest-xdist",
#   "typer",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Tests for compact review summaries."""

from __future__ import annotations

import json
import string
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

import pr_review_threads
from pr_review_models import Author, CommentNode, UnresolvedThread
from pr_review_threads import app
from review_test_gh_fixtures import (
    _default_github_detection as _default_github_detection,
    _fetch_result,
    _review,
    _review_url,
    _thread_with_comment,
    runner,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# --- --summary -------------------------------------------------------------------------------


def test_fetch_summary_reduces_to_the_documented_fields(mocker: MockerFixture) -> None:
    """`fetch --summary` prints counts, blockers, and per-thread/per-review ids and content --
    not the full `FetchResult` JSON."""
    state = _fetch_result(
        unresolved=[_thread_with_comment(body="fix this")],
        unresponded_reviews=[_review("R1", body="ship it", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))],
        blockers=["draft: reviewers are not requested until the PR is marked ready for review"],
        codex_approved=True,
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["pr"] == 3208
    assert data["unresolved_count"] == 1
    assert data["unresponded_count"] == 1
    assert data["codex_approved"] is True
    assert data["blockers"] == ["draft: reviewers are not requested until the PR is marked ready for review"]
    assert data["unresolved"] == [
        {
            "thread_id": "T1",
            "comment_id": 42,
            "path": "x.py",
            "line": 10,
            "comment_count": 1,
            "comments_truncated": False,
            "author": "reviewer",
            "body": "fix this",
            "replies": [],
        }
    ]
    assert data["unresponded_reviews"] == [
        {"author": "codex", "state": "COMMENTED", "url": _review_url("R1"), "body": "ship it"}
    ]
    assert "reviews_with_body" not in data


def test_fetch_summary_thread_exposes_a_single_follow_up_comment(mocker: MockerFixture) -> None:
    """A thread with one follow-up carries `comment_count` and that reply in `replies` --
    reading only the opener risks acting on stale feedback a later reply already moved past."""
    thread = UnresolvedThread(
        id="T1",
        path="x.py",
        comments=[
            CommentNode(databaseId=42, body="fix this", line=10, originalLine=10, author=Author(login="reviewer")),
            CommentNode(
                databaseId=43, body="actually never mind", line=10, originalLine=10, author=Author(login="reviewer")
            ),
        ],
        comments_truncated=False,
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    entry = json.loads(result.output)["unresolved"][0]
    assert entry["comment_id"] == 42  # reply still targets the *opening* comment
    assert entry["comment_count"] == 2
    assert entry["body"] == "fix this"
    assert entry["replies"] == [{"author": "reviewer", "body": "actually never mind"}]


def test_fetch_summary_thread_preserves_a_middle_comment_not_just_the_last(mocker: MockerFixture) -> None:
    """A thread with three-plus comments preserves *every* follow-up, in order -- reporting only
    the newest one would hide a middle clarification behind an unrelated closing note."""
    thread = UnresolvedThread(
        id="T1",
        path="x.py",
        comments=[
            CommentNode(databaseId=1, body="opening finding", line=10, originalLine=10, author=Author(login="bot")),
            CommentNode(
                databaseId=2,
                body="clarification: actually X not Y",
                line=10,
                originalLine=10,
                author=Author(login="bot"),
            ),
            CommentNode(databaseId=3, body="thanks, got it", line=10, originalLine=10, author=Author(login="dev")),
        ],
        comments_truncated=False,
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    entry = json.loads(result.output)["unresolved"][0]
    assert entry["comment_count"] == 3
    assert entry["replies"] == [
        {"author": "bot", "body": "clarification: actually X not Y"},
        {"author": "dev", "body": "thanks, got it"},
    ]


def test_fetch_summary_thread_empty_replies_when_no_follow_ups(mocker: MockerFixture) -> None:
    """A single-comment thread carries `comment_count: 1` and an empty `replies` list -- nothing to
    report beyond what `body`/`author` already carry."""
    state = _fetch_result(unresolved=[_thread_with_comment()])
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    entry = json.loads(result.output)["unresolved"][0]
    assert entry["comment_count"] == 1
    assert entry["replies"] == []


def test_fetch_summary_thread_reports_replies_when_truncated_too(mocker: MockerFixture) -> None:
    """A truncated thread still reports whatever replies were actually fetched -- `comments_truncated`
    says more may exist beyond the fetched page, but it does not make the fetched replies untrue."""
    thread = UnresolvedThread(
        id="T1",
        path="x.py",
        comments=[
            CommentNode(databaseId=42, body="fix this", line=10, originalLine=10, author=Author(login="reviewer")),
            CommentNode(
                databaseId=43,
                body="reply within the fetched page",
                line=10,
                originalLine=10,
                author=Author(login="reviewer"),
            ),
        ],
        comments_truncated=True,
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    entry = json.loads(result.output)["unresolved"][0]
    assert entry["comment_count"] == 2
    assert entry["comments_truncated"] is True
    assert entry["replies"] == [{"author": "reviewer", "body": "reply within the fetched page"}]


def test_fetch_summary_thread_falls_back_to_original_line_when_line_is_null(mocker: MockerFixture) -> None:
    """An outdated diff comment has `line: null` but keeps `originalLine` -- the summary prefers
    it over a bare null whenever GitHub provides it."""
    thread = UnresolvedThread(
        id="T1",
        path="x.py",
        comments=[CommentNode(databaseId=42, body="fix this", line=None, originalLine=17, author=Author(login="r"))],
        comments_truncated=False,
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["unresolved"][0]["line"] == 17


def test_fetch_summary_fails_clean_on_a_thread_with_no_comments(mocker: MockerFixture) -> None:
    """An unresolved thread with an empty `comments` list -- an API shape this script has no
    source is possible, since a review thread is always created by a comment -- exits non-zero
    with a message naming the thread, rather than crashing with a bare `IndexError`."""
    thread = UnresolvedThread(id="T-empty", path="x.py", comments=[], comments_truncated=False)
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code != 0
    assert not isinstance(result.exception, IndexError)
    assert "T-empty" in result.output


def test_fetch_summary_prints_blockers_even_when_empty(mocker: MockerFixture) -> None:
    """`blockers` is always present in the summary, empty or not -- an empty `unresolved` with a
    non-empty `blockers` means something different from a clean PR."""
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result())

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["blockers"] == []


def test_fetch_summary_max_body_truncates_and_marks_it_visibly(mocker: MockerFixture) -> None:
    """`--max-body` cuts a printed body and leaves a visible marker rather than a silent cut."""
    state = _fetch_result(unresolved=[_thread_with_comment(body=string.digits)])
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary", "--max-body", "4"])

    assert result.exit_code == 0, result.output
    body = json.loads(result.output)["unresolved"][0]["body"]
    assert body == "0123...[truncated, showing 4/10 chars]"


def test_fetch_summary_max_body_leaves_short_bodies_untouched(mocker: MockerFixture) -> None:
    """A body at or under `--max-body` is printed unchanged, with no truncation marker."""
    state = _fetch_result(unresolved=[_thread_with_comment(body="short")])
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary", "--max-body", "100"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["unresolved"][0]["body"] == "short"


def test_fetch_without_summary_still_prints_the_full_result_by_default(mocker: MockerFixture) -> None:
    """A single `--pr` preserves every established `FetchResult` field in the full snapshot."""
    state = _fetch_result(unresolved=[_thread_with_comment()])
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    for field, value in json.loads(state.model_dump_json()).items():
        assert data[field] == value


def test_watch_summary_flattens_timed_out_instead_of_nesting_under_state(mocker: MockerFixture) -> None:
    """`watch --summary` normalizes `fetch`'s and `watch`'s summary shapes: `timed_out` sits
    alongside the summary fields, not nested under a separate `state` key."""
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result())

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0", "--summary"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    assert data["pr"] == 3208
    assert "state" not in data


def test_watch_summary_honors_max_body(mocker: MockerFixture) -> None:
    """`watch --summary --max-body` truncates the same way `fetch --summary` does."""
    state = _fetch_result(unresolved=[_thread_with_comment(body=string.digits)])
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0", "--summary", "--max-body", "4"])

    assert result.exit_code == 0, result.output
    body = json.loads(result.output)["unresolved"][0]["body"]
    assert body == "0123...[truncated, showing 4/10 chars]"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
