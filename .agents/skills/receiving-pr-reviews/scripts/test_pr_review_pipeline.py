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
"""End-to-end normalization tests for the GitHub review fetch pipeline."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import pr_review_gh
from pr_review_threads import app
from review_test_gh_fixtures import (
    _AGENT_LOGIN,
    _default_github_detection as _default_github_detection,
    _rest_pages,
    _review_url,
    _reviews_page,
    _thread_page,
    runner,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# --- fetch: full JSON-in/JSON-out pipeline -----------------------------------------------------


def test_fetch_flattens_pages_filters_resolved_and_derives_new_fields(mocker: MockerFixture) -> None:
    """`fetch` flattens multi-page thread results, dropping resolved threads and counting right,
    and derives `unresponded_reviews` and `codex_approved` from the issue-comments, reactions,
    authenticated-identity, and head-commit-date calls in the same pipeline.

    Two thread pages are fed to `run_gh` (page 1 has a resolved and an unresolved thread; page
    2's lone thread has `comments.pageInfo.hasNextPage: true`). One reviews page has a review with
    a null `author` (a deleted account) alongside an empty-body review — both must be parsed
    without error, and only the non-empty-body review must survive into `reviews_with_body`. One
    PR-level comment, authored by the same identity `gh` is authenticated as and quoting R1's own
    `url`, postdates the review, so it must NOT appear in `unresponded_reviews`. One reaction is
    Codex's "+1", and it postdates the PR's head commit, so `codex_approved` must be `True`.
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
    r1_url = _review_url("R1")
    reviews_pages = [
        _reviews_page(
            total_count=2,
            nodes=[
                {
                    "id": "R1",
                    "author": {"login": "codex"},
                    "state": "COMMENTED",
                    "body": "Some feedback",
                    "submittedAt": "2026-01-01T00:00:00Z",
                    "lastEditedAt": None,
                    "url": r1_url,
                },
                {
                    "id": "R2",
                    "author": None,
                    "state": "APPROVED",
                    "body": "",
                    "submittedAt": "2026-01-01T00:00:00Z",
                    "lastEditedAt": None,
                    "url": _review_url("R2"),
                },
            ],
        )
    ]
    issue_comments_raw = _rest_pages({
        "created_at": "2026-01-02T00:00:00Z",
        "user": {"login": _AGENT_LOGIN},
        "body": f"Addressed {r1_url}.",
    })
    reactions_raw = _rest_pages({
        "content": "+1",
        "user": {"login": "chatgpt-codex-connector[bot]"},
        "created_at": "2026-01-03T00:00:00Z",
    })
    head_state_raw = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "isDraft": False,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-01-01T12:00:00Z"}}]},
                }
            }
        }
    })
    # No `HeadRefForcePushedEvent` has ever landed on this PR — an empty `timelineItems.nodes`.
    force_push_raw = json.dumps({"data": {"repository": {"pullRequest": {"timelineItems": {"nodes": []}}}}})
    mocker.patch.object(
        pr_review_gh,
        "run_gh",
        side_effect=[
            json.dumps(thread_pages),
            json.dumps(reviews_pages),
            issue_comments_raw,
            reactions_raw,
            _AGENT_LOGIN,
            head_state_raw,
            force_push_raw,
        ],
    )

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
    # The agent's own PR-level comment (2026-01-02) postdates R1's review (2026-01-01) — followed up.
    assert data["unresponded_reviews"] == []
    # Codex's "+1" (2026-01-03) postdates the head commit (2026-01-01T12:00) — a live approval.
    assert data["codex_approved"] is True
    # A ready, conflict-free PR: reviews can happen, so nothing blocks them.
    assert data["reviewability"] == {
        "is_draft": False,
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "blockers": [],
    }
    assert data["snapshot_complete"] is False
    assert data["cycle_state"] == "SNAPSHOT_INCOMPLETE"
    assert data["completeness"]["truncated_input_ids"] == ["github:review-comment:3"]
    normalized = {item["input_id"]: item for item in data["review_inputs"]}
    assert set(normalized["github:review:R2"]["kinds"]) == {"approval"}
    assert normalized["github:review:R2"]["body"] == ""
    assert set(normalized["github:review:R1"]["kinds"]) == {"comment"}
    assert set(normalized["github:reaction:1767398400-0"]["kinds"]) == {"approval"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
