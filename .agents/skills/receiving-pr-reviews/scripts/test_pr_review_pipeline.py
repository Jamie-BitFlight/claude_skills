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
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import pr_review_gh
from pr_review_github_transport import fetch_thread_pages
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


def test_fetch_flattens_pages_preserves_resolved_inputs_and_derives_new_fields(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """`fetch` keeps resolved history in the census while projecting only unresolved threads,
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
                        "totalCount": 2,
                        "pageInfo": {"hasNextPage": True},
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
                        "totalCount": 1,
                        "pageInfo": {"hasNextPage": False},
                        # A comment left by a since-deleted account — `author` is null.
                        "nodes": [
                            {"databaseId": 3, "body": "flagged", "line": None, "originalLine": 10, "author": None}
                        ],
                    },
                }
            ],
        ),
    ]
    nested_comment_pages = [
        {
            "data": {
                "node": {
                    "comments": {
                        "totalCount": 2,
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [
                            {
                                "databaseId": 2,
                                "body": "already resolved",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "codex"},
                            }
                        ],
                    }
                }
            }
        },
        {
            "data": {
                "node": {
                    "comments": {
                        "totalCount": 2,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "databaseId": 22,
                                "body": "resolved follow-up",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "reviewer"},
                            }
                        ],
                    }
                }
            }
        },
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
                    "commits": {
                        "nodes": [
                            {
                                "commit": {
                                    "committedDate": "2026-01-01T12:00:00Z",
                                    "statusCheckRollup": {"state": "SUCCESS"},
                                }
                            }
                        ]
                    },
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
            json.dumps(nested_comment_pages),
            json.dumps(reviews_pages),
            issue_comments_raw,
            reactions_raw,
            _AGENT_LOGIN,
            head_state_raw,
            force_push_raw,
        ],
    )

    snapshot_file = tmp_path / "snapshot.json"
    result = runner.invoke(app, ["fetch", "--pr", "3208", "--snapshot-file", str(snapshot_file)])

    assert result.exit_code == 0, result.output
    data = json.loads(snapshot_file.read_text(encoding="utf-8"))
    assert data["threads_count"] == 3
    assert data["unresolved_count"] == 2
    unresolved_ids = {thread["id"] for thread in data["unresolved"]}
    assert unresolved_ids == {"T1", "T3"}
    truncated_by_id = {thread["id"]: thread["comments_truncated"] for thread in data["unresolved"]}
    assert truncated_by_id == {"T1": False, "T3": False}
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
    assert data["provider_metadata"]["checks_state"] == "SUCCESS"
    assert data["provider_metadata"]["assigned_reviewers"] is None
    assert data["snapshot_complete"] is True
    assert data["cycle_state"] == "ASSESSMENT_REQUIRED"
    assert data["completeness"]["truncated_input_ids"] == []
    normalized = {item["input_id"]: item for item in data["review_inputs"]}
    assert normalized["github:review-comment:2"]["provider_state"] == "resolved"
    assert normalized["github:review-comment:2"]["capabilities"]["can_resolve"] is False
    assert normalized["github:review-comment:22"]["parent_id"] == "github:review-comment:2"
    assert set(normalized["github:review:R2"]["kinds"]) == {"approval"}
    assert normalized["github:review:R2"]["body"] == ""
    assert set(normalized["github:review:R1"]["kinds"]) == {"comment"}
    assert set(normalized["github:reaction:1767398400-0"]["kinds"]) == {"approval"}


@pytest.mark.parametrize(
    ("outer_total", "page_totals", "database_ids"), [(101, [2, 2], [2, 22]), (2, [2, 3], [2, 22]), (2, [2, 2], [2, 2])]
)
def test_nested_comment_census_rejects_conflicting_or_duplicate_evidence(
    outer_total: int, page_totals: list[int], database_ids: list[int]
) -> None:
    """A nested refetch cannot replace or overstate the outer authoritative census."""
    outer = [
        _thread_page(
            total_count=1,
            has_next_page=False,
            nodes=[
                {
                    "id": "T2",
                    "isResolved": True,
                    "path": "b.py",
                    "comments": {
                        "totalCount": outer_total,
                        "pageInfo": {"hasNextPage": True},
                        "nodes": [
                            {
                                "databaseId": database_ids[0],
                                "body": "first",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "codex"},
                            }
                        ],
                    },
                }
            ],
        )
    ]
    nested = [
        {
            "data": {
                "node": {
                    "comments": {
                        "totalCount": page_totals[0],
                        "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
                        "nodes": [
                            {
                                "databaseId": database_ids[0],
                                "body": "first",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "codex"},
                            }
                        ],
                    }
                }
            }
        },
        {
            "data": {
                "node": {
                    "comments": {
                        "totalCount": page_totals[1],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "databaseId": database_ids[1],
                                "body": "second",
                                "line": 1,
                                "originalLine": 1,
                                "author": {"login": "reviewer"},
                            }
                        ],
                    }
                }
            }
        },
    ]
    responses = iter([json.dumps(outer), json.dumps(nested)])

    with pytest.raises(ValueError, match=r"nested comment pagination.*incomplete"):
        fetch_thread_pages(lambda _args, timeout=None: next(responses), "acme", "widgets", 17, timeout=30)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
