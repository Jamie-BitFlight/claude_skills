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
"""Tests for pr_review_threads.py, pr_review_gh.py, and pr_review_models.py.

Covers: `pr_review_gh.build_fetch_result`'s multi-page flattening, resolved-thread filtering,
`comments_truncated` derivation, `reviews_with_body` filtering (including a null `author`, which a
deleted GitHub account produces), `unresponded_reviews` derivation against the currently-
authenticated `gh` identity's own PR-level comments — requiring each comment to explicitly quote a
review's own `url` and postdate its effective timestamp (the later of `submittedAt`/`lastEditedAt`)
before it counts as a response to that specific review, not merely inferred from chronological
order or excluded only by author — and `codex_approved` reaction detection scoped to reactions that
postdate the PR's current head commit — all as one JSON-in/JSON-out pipeline test plus a matrix of
focused unit tests against `build_fetch_result` directly. Also covers `FetchResult.has_outstanding_work`
(the single trigger rule `watch` polls for) and `watch`'s own loop: returning immediately when the
first fetch is already actionable, polling until it becomes actionable, timing out when it never
does, and the deadline-budget/transient-failure mechanics carried over from the pre-existing polling
loop.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from pydantic import BaseModel, ValidationError
from typer.testing import CliRunner

import pr_review_gh
import pr_review_models
import pr_review_threads
from pr_review_gh import _is_codex_thumbs_up, build_fetch_result
from pr_review_models import (
    Author,
    FetchResult,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    Reviewability,
    ReviewNode,
    UnresolvedThread,
)
from pr_review_threads import app

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()

_AGENT_LOGIN = "reviewing-agent"
_OLD_COMMIT_DATE = datetime(2025, 12, 1, tzinfo=UTC)


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


def _rest_pages(*items: dict[str, object]) -> str:
    """Build the `--paginate --slurp` output for a plain REST array endpoint: one page of items."""
    return json.dumps([list(items)])


def _review_url(review_id: str) -> str:
    """A review's canonical GitHub permalink, derived from its id for test fixtures only."""
    return f"https://github.com/o/r/pull/1#pullrequestreview-{review_id}"


def _review(
    review_id: str,
    *,
    body: str,
    submitted_at: datetime | None,
    login: str = "codex",
    last_edited_at: datetime | None = None,
) -> ReviewNode:
    return ReviewNode(
        id=review_id,
        author=Author(login=login),
        state="COMMENTED",
        body=body,
        submittedAt=submitted_at,
        lastEditedAt=last_edited_at,
        url=_review_url(review_id),
    )


def _own_comment(
    created_at: datetime, *, references: ReviewNode | None = None, login: str = _AGENT_LOGIN
) -> IssueComment:
    """Build an own PR-level comment, optionally quoting a specific review's `url`."""
    body = f"Addressed {references.url}." if references is not None else "An unrelated administrative note."
    return IssueComment(created_at=created_at, user=Author(login=login), body=body)


def _head_state(
    commit_date: datetime = _OLD_COMMIT_DATE,
    *,
    is_draft: bool = False,
    mergeable: str = "MERGEABLE",
    merge_state_status: str = "CLEAN",
) -> PullRequestHeadState:
    """Build a `PullRequestHeadState`, defaulting to a reviewable (non-draft, conflict-free) PR."""
    return PullRequestHeadState.model_validate({
        "isDraft": is_draft,
        "mergeable": mergeable,
        "mergeStateStatus": merge_state_status,
        "commits": {"nodes": [{"commit": {"committedDate": commit_date}}]},
    })


def _state(
    *, unresolved_count: int = 0, unresponded_reviews: list[ReviewNode] | None = None, codex_approved: bool = False
) -> FetchResult:
    """Build a minimal `FetchResult` for `watch`-loop tests, with `has_outstanding_work` control."""
    return FetchResult(
        reviews_count=0,
        reviews_with_body=[],
        unresponded_reviews=unresponded_reviews or [],
        threads_count=unresolved_count,
        unresolved=[
            UnresolvedThread(id=f"T{i}", path="x.py", comments=[], comments_truncated=False)
            for i in range(unresolved_count)
        ],
        unresolved_count=unresolved_count,
        codex_approved=codex_approved,
        reviewability=Reviewability(is_draft=False, mergeable="MERGEABLE", merge_state_status="CLEAN", blockers=[]),
    )


def _reviews_conn(nodes: list[ReviewNode]) -> pr_review_gh.ReviewsConnection:
    return pr_review_gh.ReviewsConnection(totalCount=len(nodes), nodes=nodes)


def _empty_threads() -> list[pr_review_gh.ReviewThreadsConnection]:
    """A single empty `reviewThreads` page — `build_fetch_result` always indexes page zero."""
    return [pr_review_gh.ReviewThreadsConnection(totalCount=0, nodes=[])]


def _patch_identity_and_commit_date(
    mocker: MockerFixture,
    *,
    login: str = _AGENT_LOGIN,
    commit_date: datetime = _OLD_COMMIT_DATE,
    force_push_at: datetime | None = None,
) -> None:
    """Stub the three `build_fetch_result` calls every matrix test below needs but does not itself
    exercise — the authenticated identity (for `unresponded_reviews`), the PR head state (its
    commit date, for `codex_approved`, plus the reviewability fields), and the latest force-push
    timestamp (also for `codex_approved`) — so each test's own `_fetch_*` mocks stay focused on
    what it covers. `force_push_at` defaults to `None` (this PR has never been force-pushed),
    matching most tests' scenarios, and the stubbed head state is a plain reviewable PR.
    """
    mocker.patch.object(pr_review_gh, "_fetch_authenticated_login", return_value=login)
    mocker.patch.object(pr_review_gh, "_fetch_head_state", return_value=_head_state(commit_date))
    mocker.patch.object(pr_review_gh, "_fetch_latest_force_push_at", return_value=force_push_at)


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


# --- build_fetch_result: unresponded_reviews / codex_approved unit matrix ----------------------


def test_build_fetch_result_unresponded_when_no_pr_comments_exist(mocker: MockerFixture) -> None:
    """A bodied, submitted review is unresponded when the PR has no PR-level comments at all."""
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_unresponded_when_own_comment_does_not_reference_it(mocker: MockerFixture) -> None:
    """A review stays unresponded when the authenticated identity's own comment postdates it but
    never actually references it.

    Regression coverage for a Codex review with fresh evidence from this very PR: an unrelated
    administrative comment this workflow posts — e.g. the cross-thread sequencing/summary comment
    its own SKILL.md step 6 sanctions — happens to postdate a review, but chronological order alone
    cannot distinguish that from a comment that actually engaged with the review's feedback.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    unrelated_own_comment = _own_comment(datetime(2026, 1, 2, tzinfo=UTC))
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[unrelated_own_comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_responded_when_own_pr_comment_postdates_review(mocker: MockerFixture) -> None:
    """A review is excluded from `unresponded_reviews` once the authenticated identity's own
    PR-level comment postdates it and explicitly quotes its `url`.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    comment = _own_comment(datetime(2026, 1, 2, tzinfo=UTC), references=review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []


def test_build_fetch_result_unresponded_when_own_pr_comment_predates_review(mocker: MockerFixture) -> None:
    """A review submitted after the newest of the authenticated identity's own referencing
    PR-level comments is still unresponded.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 2, tzinfo=UTC))
    comment = _own_comment(datetime(2026, 1, 1, tzinfo=UTC), references=review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_unresponded_when_review_edited_after_own_response(mocker: MockerFixture) -> None:
    """A review edited after this workflow already responded is unresponded again — its edit
    postdates the referencing response even though its original `submittedAt` predates it.

    Regression coverage for a Codex review: comparing only `submittedAt` let an editor add new
    feedback to an already-submitted review after the workflow had already replied, and that new
    feedback would then be skipped indefinitely, because the review's unchanged `submittedAt`
    still predated the earlier response.
    """
    review = _review(
        "R1",
        body="updated feedback",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_edited_at=datetime(2026, 1, 3, tzinfo=UTC),
    )
    comment = _own_comment(datetime(2026, 1, 2, tzinfo=UTC), references=review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_responded_when_own_comment_postdates_review_edit(mocker: MockerFixture) -> None:
    """A review is still responded-to when the workflow's own referencing comment postdates its
    latest edit, not just its original submission.
    """
    review = _review(
        "R1",
        body="updated feedback",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_edited_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    comment = _own_comment(datetime(2026, 1, 3, tzinfo=UTC), references=review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []


def test_build_fetch_result_unresponded_when_only_other_accounts_commented(mocker: MockerFixture) -> None:
    """A review stays unresponded when a PR-level comment postdates it and references its `url`
    but was authored by an account other than the currently-authenticated `gh` identity.

    Regression coverage for a Codex review on the previous design: any PR-level comment at all —
    an unrelated bystander, a bot, a CI notification — used to silence the review even though
    nothing evidenced that comment actually addressed the review's feedback.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    unrelated_comment = IssueComment(
        created_at=datetime(2026, 1, 2, tzinfo=UTC), user=Author(login="a-bystander"), body=f"Addressed {review.url}."
    )
    deleted_account_comment = IssueComment(
        created_at=datetime(2026, 1, 3, tzinfo=UTC), user=None, body=f"Addressed {review.url}."
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(
        pr_review_gh, "_fetch_issue_comments", return_value=[unrelated_comment, deleted_account_comment]
    )
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_older_review_stays_unresponded_when_only_newer_one_referenced(
    mocker: MockerFixture,
) -> None:
    """A comment that quotes only the newer of two concurrently-outstanding reviews' URLs does not
    also clear the older one, even though it postdates both.

    Regression coverage for a Codex review: a count-only "one comment per review" pairing based on
    chronological order alone could still misattribute a comment to the wrong review; requiring an
    explicit `url` reference ties a comment to the specific review it names instead.
    """
    older_review = _review("R1", body="first round of feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    newer_review = _review("R2", body="second round of feedback", submitted_at=datetime(2026, 1, 2, tzinfo=UTC))
    comment = _own_comment(datetime(2026, 1, 3, tzinfo=UTC), references=newer_review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([older_review, newer_review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [older_review]


def test_build_fetch_result_both_reviews_responded_when_one_comment_references_both(mocker: MockerFixture) -> None:
    """One comment that quotes both reviews' URLs clears both — a review is not limited to being
    addressed by only one comment.
    """
    older_review = _review("R1", body="first round of feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    newer_review = _review("R2", body="second round of feedback", submitted_at=datetime(2026, 1, 2, tzinfo=UTC))
    comment = IssueComment(
        created_at=datetime(2026, 1, 3, tzinfo=UTC),
        user=Author(login=_AGENT_LOGIN),
        body=f"Addressed both {older_review.url} and {newer_review.url}.",
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([older_review, newer_review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []


def test_build_fetch_result_shorter_review_stays_unresponded_when_only_longer_id_referenced(
    mocker: MockerFixture,
) -> None:
    """A comment quoting only a review whose id is a numeric superset of another review's id (e.g.
    `pullrequestreview-1234` vs `pullrequestreview-123`) does not also clear the shorter one.

    Regression coverage for a Codex review: plain substring containment does not enforce a
    boundary at the end of the id, so `"...pullrequestreview-123" in "...pullrequestreview-1234..."`
    is `True` even though the two are different reviews — `_references_review` must reject that.
    """
    shorter_review = _review("123", body="first round of feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    longer_review = _review("1234", body="second round of feedback", submitted_at=datetime(2026, 1, 2, tzinfo=UTC))
    comment = _own_comment(datetime(2026, 1, 3, tzinfo=UTC), references=longer_review)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(
        pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([shorter_review, longer_review])]
    )
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [shorter_review]


@pytest.mark.parametrize(
    ("comment_body", "expected"),
    [
        ("Addressed https://github.com/o/r/pull/1#pullrequestreview-123.", True),
        ("Addressed https://github.com/o/r/pull/1#pullrequestreview-123", True),
        ("Addressed https://github.com/o/r/pull/1#pullrequestreview-1234.", False),
        ("No reference here.", False),
    ],
    ids=["trailing-punctuation", "end-of-string", "longer-id-does-not-match-shorter", "no-match"],
)
def test_references_review_enforces_id_boundary(comment_body: str, expected: bool) -> None:
    assert (
        pr_review_gh._references_review(comment_body, "https://github.com/o/r/pull/1#pullrequestreview-123") is expected
    )


def test_build_fetch_result_excludes_review_with_no_submitted_at(mocker: MockerFixture) -> None:
    """A review that has not actually been submitted yet is never unresponded."""
    review = _review("R1", body="feedback", submitted_at=None)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []


def test_build_fetch_result_codex_approved_true_when_reaction_postdates_head_commit(mocker: MockerFixture) -> None:
    """`codex_approved` is `True` when the bot's "+1" reaction postdates the PR's head commit."""
    reaction = Reaction(
        content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=datetime(2026, 1, 2, tzinfo=UTC)
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[reaction])
    _patch_identity_and_commit_date(mocker, commit_date=datetime(2026, 1, 1, tzinfo=UTC))

    result = build_fetch_result("o", "r", 1)

    assert result.codex_approved is True


def test_build_fetch_result_codex_approved_false_when_reaction_predates_head_commit(mocker: MockerFixture) -> None:
    """`codex_approved` is `False` when Codex's "+1" reaction predates the PR's current head
    commit — a stale approval left on an earlier revision must not be reported as current.

    Regression coverage for a Codex review flagging that the pre-fix design never compared a
    reaction's timestamp against anything: once Codex approved once, the reaction persisted and
    every later revision — including ones Codex never actually looked at — kept reporting as
    approved.
    """
    reaction = Reaction(
        content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[reaction])
    _patch_identity_and_commit_date(mocker, commit_date=datetime(2026, 1, 2, tzinfo=UTC))

    result = build_fetch_result("o", "r", 1)

    assert result.codex_approved is False


def test_build_fetch_result_codex_approved_false_when_reaction_predates_reused_commit_force_push(
    mocker: MockerFixture,
) -> None:
    """`codex_approved` is `False` when a later force-push reset the branch onto a pre-existing
    commit object whose own committer date is *older* than the reaction — the force-push's own
    server-recorded timestamp, not the reused commit's stale metadata, must govern.

    Regression coverage for a Codex review: comparing only the head commit's embedded committer
    date is not sufficient, because a force-push that resets a branch back onto a commit object
    that already existed (rather than creating a fresh commit) does not update that commit's own
    dates — a `HeadRefForcePushedEvent` timeline entry is the reliable, server-recorded signal for
    when the head actually changed instead.
    """
    reaction = Reaction(
        content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=datetime(2026, 1, 2, tzinfo=UTC)
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[reaction])
    # The reused commit's own committer date (2026-01-01) predates the reaction, but the
    # force-push that made it head happened later (2026-01-03) — after the reaction.
    _patch_identity_and_commit_date(
        mocker, commit_date=datetime(2026, 1, 1, tzinfo=UTC), force_push_at=datetime(2026, 1, 3, tzinfo=UTC)
    )

    result = build_fetch_result("o", "r", 1)

    assert result.codex_approved is False


def test_build_fetch_result_codex_approved_true_when_reaction_postdates_force_push(mocker: MockerFixture) -> None:
    """`codex_approved` is `True` when the reaction postdates a force-push that reused an older
    commit object, even though that commit's own committer date alone would say otherwise.
    """
    reaction = Reaction(
        content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=datetime(2026, 1, 4, tzinfo=UTC)
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[reaction])
    _patch_identity_and_commit_date(
        mocker, commit_date=datetime(2026, 1, 1, tzinfo=UTC), force_push_at=datetime(2026, 1, 3, tzinfo=UTC)
    )

    result = build_fetch_result("o", "r", 1)

    assert result.codex_approved is True


def test_fetch_head_state_reads_commit_date_via_graphql_last_one(mocker: MockerFixture) -> None:
    """`_fetch_head_state` reads the head commit's date from GraphQL's `commits(last: 1)`.

    Regression coverage for a Codex review: the REST `/pulls/{pr}/commits` endpoint this used to
    call is documented as listing a maximum of 250 commits total regardless of pagination, so on a
    PR with more commits than that, its last element would not reliably be the actual head. GraphQL
    connection pagination has no equivalent flat cap.
    """
    raw = json.dumps({
        "data": {
            "repository": {
                "pullRequest": {
                    "isDraft": False,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-01-06T00:00:00Z"}}]},
                }
            }
        }
    })
    mocker.patch.object(pr_review_gh, "run_gh", return_value=raw)

    result = pr_review_gh._fetch_head_state("o", "r", 1, gh_timeout=None)

    assert result.commits.nodes[-1].commit.committedDate == datetime(2026, 1, 6, tzinfo=UTC)


def test_fetch_latest_force_push_at_returns_none_when_never_force_pushed(mocker: MockerFixture) -> None:
    """`_fetch_latest_force_push_at` returns `None` for a PR with no `HeadRefForcePushedEvent`."""
    raw = json.dumps({"data": {"repository": {"pullRequest": {"timelineItems": {"nodes": []}}}}})
    mocker.patch.object(pr_review_gh, "run_gh", return_value=raw)

    result = pr_review_gh._fetch_latest_force_push_at("o", "r", 1, gh_timeout=None)

    assert result is None


def test_fetch_latest_force_push_at_returns_event_timestamp(mocker: MockerFixture) -> None:
    """`_fetch_latest_force_push_at` returns the timeline event's `createdAt` when one exists."""
    raw = json.dumps({
        "data": {"repository": {"pullRequest": {"timelineItems": {"nodes": [{"createdAt": "2026-01-05T00:00:00Z"}]}}}}
    })
    mocker.patch.object(pr_review_gh, "run_gh", return_value=raw)

    result = pr_review_gh._fetch_latest_force_push_at("o", "r", 1, gh_timeout=None)

    assert result == datetime(2026, 1, 5, tzinfo=UTC)


@pytest.mark.parametrize(
    "reaction",
    [
        Reaction(content="heart", user=Author(login="chatgpt-codex-connector[bot]"), created_at=_OLD_COMMIT_DATE),
        Reaction(content="+1", user=Author(login="some-human"), created_at=_OLD_COMMIT_DATE),
        Reaction(content="+1", user=None, created_at=_OLD_COMMIT_DATE),
        Reaction(content="+1", user=Author(login="chatgpt-codex-connector-imposter"), created_at=_OLD_COMMIT_DATE),
    ],
    ids=["wrong-content", "wrong-user", "null-user", "prefix-only-impersonator"],
)
def test_is_codex_thumbs_up_false_for_non_matching_reactions(reaction: Reaction) -> None:
    """Only a "+1" from exactly the Codex bot's known login counts as Codex's approval.

    The `prefix-only-impersonator` case is regression coverage for a Codex review: matching by
    `.startswith()` on a public PR would also accept a "+1" from any account whose login merely
    starts with the same text, letting an unrelated account spoof `codex_approved`.
    """
    assert _is_codex_thumbs_up(reaction) is False


def test_is_codex_thumbs_up_true_regardless_of_bot_suffix() -> None:
    """Matches both the GraphQL-style login (no `[bot]`) and REST-style login (`[bot]` suffix)."""
    assert (
        _is_codex_thumbs_up(
            Reaction(content="+1", user=Author(login="chatgpt-codex-connector"), created_at=_OLD_COMMIT_DATE)
        )
        is True
    )
    assert (
        _is_codex_thumbs_up(
            Reaction(content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=_OLD_COMMIT_DATE)
        )
        is True
    )


# --- strict ingress ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (pr_review_models.CommentNode, {"databaseId": "12", "body": "b", "line": 1, "originalLine": 1, "author": None}),
        (pr_review_models.PageInfo, {"hasNextPage": "false"}),
        (pr_review_models.ReviewThreadsConnection, {"totalCount": "3", "nodes": []}),
        (
            pr_review_models.PullRequestHeadState,
            {"isDraft": "false", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN", "commits": {"nodes": []}},
        ),
        (
            pr_review_models.PullRequestHeadState,
            {"isDraft": False, "mergeable": 1, "mergeStateStatus": "CLEAN", "commits": {"nodes": []}},
        ),
    ],
    ids=["int-as-string", "bool-as-string", "count-as-string", "is-draft-as-string", "mergeable-as-number"],
)
def test_ingress_models_reject_a_coerced_producer_shape(model: type[BaseModel], payload: dict[str, object]) -> None:
    """A `gh` response whose scalar types do not match the schema fails at the boundary.

    In lax mode `"3"` silently becomes `3` and `"false"` becomes `True` — a producer-shape change
    would then reach review state looking valid. `_GitHubResponseModel` sets `strict=True` so it
    raises here instead.
    """
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_ingress_models_still_parse_github_iso_timestamps() -> None:
    """Strict mode does not break timestamps: GitHub sends ISO-8601 strings and that is correct.

    These models are validated from `json.loads` output (Pydantic's Python mode), where a strict
    `datetime` field would reject the string GitHub actually sends. `GitHubTimestamp` relaxes
    strictness on exactly those fields and nothing else — so an unparseable value is still
    rejected, while the other forms a lax `datetime` accepts (a Unix epoch number) remain accepted.
    """
    assert pr_review_models.GitHubCommitDate.model_validate({"committedDate": "2026-01-06T00:00:00Z"}) == (
        pr_review_models.GitHubCommitDate(committedDate=datetime(2026, 1, 6, tzinfo=UTC))
    )
    with pytest.raises(ValidationError):
        pr_review_models.GitHubCommitDate.model_validate({"committedDate": "not-a-timestamp"})


def test_internal_result_models_are_not_strict() -> None:
    """`FetchResult`/`WatchResult`/`UnresolvedThread` are output shapes, not ingress.

    They are assembled from already-validated values, so they deliberately do not inherit
    `_GitHubResponseModel` — see its docstring.
    """
    for model in (pr_review_models.FetchResult, pr_review_models.WatchResult, pr_review_models.UnresolvedThread):
        assert model.model_config.get("strict") is not True


# --- every command can bound its own gh calls -----------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["fetch", "--pr", "3208", "--gh-timeout-seconds", "7"],
        ["reply", "--pr", "3208", "--comment-id", "1", "--body", "x", "--gh-timeout-seconds", "7"],
        ["resolve", "--thread-id", "T1", "--gh-timeout-seconds", "7"],
    ],
    ids=["fetch", "reply", "resolve"],
)
def test_every_gh_backed_command_accepts_a_timeout_bound(argv: list[str], mocker: MockerFixture) -> None:
    """`--gh-timeout-seconds` reaches `run_gh` from every command that shells out.

    Regression coverage for a Codex review of the change that removed the hardcoded
    `_GH_TIMEOUT_SECONDS`: `reply` and `resolve` were left with no way to bound their `gh` call at
    all, so an unattended workflow could hang on them indefinitely with no option to prevent it.
    """
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())
    run_gh_mock = mocker.patch.object(pr_review_threads, "run_gh", return_value="{}")

    result = runner.invoke(app, argv)

    assert result.exit_code == 0, result.output
    if argv[0] != "fetch":
        assert run_gh_mock.call_args.kwargs["timeout"] == pytest.approx(7)


# --- reviewability -------------------------------------------------------------------------------


def test_reviewability_reports_no_blockers_for_a_ready_conflict_free_pr() -> None:
    """A non-draft, mergeable PR can be reviewed, so `blockers` is empty."""
    result = pr_review_gh._reviewability(_head_state())

    assert result.blockers == []
    assert result.is_draft is False
    assert result.mergeable == "MERGEABLE"
    assert result.merge_state_status == "CLEAN"


def test_reviewability_reports_a_draft_pr() -> None:
    """A draft PR gets no reviewers requested, so an empty review queue is expected, not clean."""
    result = pr_review_gh._reviewability(_head_state(is_draft=True, merge_state_status="DRAFT"))

    assert result.is_draft is True
    assert result.blockers == ["draft: reviewers are not requested until the PR is marked ready for review"]


def test_reviewability_reports_a_conflicting_pr() -> None:
    """A conflicting PR gets no review runs, so an empty review queue is expected, not clean."""
    result = pr_review_gh._reviewability(_head_state(mergeable="CONFLICTING", merge_state_status="DIRTY"))

    assert result.mergeable == "CONFLICTING"
    assert result.merge_state_status == "DIRTY"
    assert result.blockers == ["conflicting: reviews will not run until the merge conflicts are resolved"]


def test_reviewability_reports_both_blockers_when_both_apply() -> None:
    """A draft PR that also conflicts names both consequences, not just the first one found."""
    result = pr_review_gh._reviewability(
        _head_state(is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY")
    )

    assert len(result.blockers) == 2


def test_reviewability_does_not_treat_unknown_mergeable_as_a_conflict() -> None:
    """`UNKNOWN` is GitHub still computing mergeability, not a conflict — reporting one is a lie.

    GitHub computes mergeability in a background job and returns `UNKNOWN` while it runs, which is
    exactly the moment just after a push — precisely when this script is most likely to be called.
    The value is surfaced as data and left for the next check to resolve; `watch` re-reads it every
    poll.
    """
    result = pr_review_gh._reviewability(_head_state(mergeable="UNKNOWN", merge_state_status="UNKNOWN"))

    assert result.mergeable == "UNKNOWN"
    assert result.blockers == []


def test_reviewability_survives_a_merge_state_status_this_script_has_never_seen() -> None:
    """An unrecognized GitHub state reaches the caller as data instead of failing validation."""
    result = pr_review_gh._reviewability(_head_state(merge_state_status="SOME_FUTURE_STATE"))

    assert result.merge_state_status == "SOME_FUTURE_STATE"
    assert result.blockers == []


def test_watch_reports_reviewability_on_a_timed_out_result(mocker: MockerFixture) -> None:
    """`watch` carries the blockers too: blocking 270s for reviews on a draft PR is pure waste."""
    blocked = _state()
    blocked.reviewability = Reviewability(
        is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY", blockers=["draft: x", "conflicting: y"]
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=blocked)

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    assert data["state"]["reviewability"]["blockers"] == ["draft: x", "conflicting: y"]


def test_blockers_do_not_change_has_outstanding_work() -> None:
    """Reviewability explains an empty result set; it never creates or suppresses work."""
    blocked = _state()
    blocked.reviewability = Reviewability(
        is_draft=True, mergeable="CONFLICTING", merge_state_status="DIRTY", blockers=["draft: x"]
    )
    assert blocked.has_outstanding_work() is False

    blocked_with_work = _state(unresolved_count=1)
    blocked_with_work.reviewability = blocked.reviewability
    assert blocked_with_work.has_outstanding_work() is True


# --- FetchResult.has_outstanding_work -----------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        _state(unresolved_count=1),
        _state(unresponded_reviews=[_review("R1", body="x", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))]),
        _state(codex_approved=True),
    ],
    ids=["unresolved-thread", "unresponded-review", "codex-approved"],
)
def test_has_outstanding_work_true_when_any_signal_present(state: FetchResult) -> None:
    assert state.has_outstanding_work() is True


def test_has_outstanding_work_false_when_all_clear() -> None:
    assert _state().has_outstanding_work() is False


# --- watch: immediate return when already actionable ---------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        _state(unresolved_count=1),
        _state(unresponded_reviews=[_review("R1", body="x", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))]),
        _state(codex_approved=True),
    ],
    ids=["unresolved-thread", "unresponded-review", "codex-approved"],
)
def test_watch_returns_immediately_when_first_fetch_already_actionable(
    state: FetchResult, mocker: MockerFixture
) -> None:
    """`watch` returns on its first fetch, without sleeping, when that fetch is already actionable."""
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)
    sleep_mock = mocker.patch.object(pr_review_threads.time, "sleep")

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    fetch_mock.assert_called_once()
    sleep_mock.assert_not_called()


def test_watch_polls_until_thread_becomes_unresolved(mocker: MockerFixture) -> None:
    """`watch` keeps polling while nothing is outstanding, and returns once a thread appears."""
    mocker.patch.object(pr_review_threads, "build_fetch_result", side_effect=[_state(), _state(unresolved_count=1)])
    mocker.patch.object(pr_review_threads.time, "sleep")

    # timeout-seconds must exceed interval-seconds: the loop stops once less than one interval
    # remains, and with time.sleep mocked to a no-op almost no wall-clock time elapses, so the
    # first iteration must find a full interval's headroom for this test's second poll to run.
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "40"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["state"]["unresolved_count"] == 1


def test_watch_times_out_when_nothing_outstanding(mocker: MockerFixture) -> None:
    """`watch` returns `timed_out: True` when `timeout_seconds` elapses with nothing outstanding."""
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True


def test_watch_stops_when_less_than_one_interval_remains(mocker: MockerFixture) -> None:
    """`watch` stops without attempting a doomed call once under one interval remains.

    `gh_timeout_budget` bounds a poll to the time left before `deadline`, so once a sleep has
    consumed the window there is nothing left to poll with. The cutoff is `deadline` itself rather
    than an invented safety margin: with `--timeout-seconds 50` and `--interval-seconds 90` the
    very first sleep covers the whole window, so no poll is attempted and the first fetch is
    reported as an honest `timed_out: true`.
    """
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline = 0.0 + 50), 0.0 (remaining = 50, which is <= the 90s interval -> break).
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "90", "--timeout-seconds", "50"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    # Only the first fetch happened — no second, doomed poll attempt.
    assert fetch_mock.call_count == 1


def test_watch_survives_transient_gh_failure_mid_window(mocker: MockerFixture) -> None:
    """A transient `gh` failure during a poll (network hiccup, momentary GitHub error) does not
    crash `watch` — it counts as no fresh data for that one poll, and the loop continues toward
    `deadline` on its own schedule rather than propagating the exception.
    """
    mocker.patch.object(
        pr_review_threads,
        "build_fetch_result",
        side_effect=[_state(), subprocess.TimeoutExpired(cmd=["gh"], timeout=30), _state(unresolved_count=1)],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")

    # 40s leaves a full interval's headroom on the first iteration (see the comment on
    # `test_watch_polls_until_thread_becomes_unresolved` above).
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "40"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["state"]["unresolved_count"] == 1


def test_watch_fails_loudly_when_every_poll_fails(mocker: MockerFixture) -> None:
    """`watch` exits non-zero, printing nothing to stdout, when every re-poll attempted this
    window fails.

    Regression coverage for a Codex review on the fix that introduced the try/except around each
    poll: silently returning `timed_out: true` here would claim a confirmed check found nothing
    outstanding, when no check after the first fetch ever succeeded — a caller trusting that
    signal would wrongly conclude the PR is clean instead of retrying. Mocks `time.monotonic` to a
    fixed sequence for exactly two failed poll attempts (one clock read per iteration, plus one in
    the `TimeoutExpired` handler to tell a real failure from the window simply ending) followed by
    the window naturally expiring.
    """
    mocker.patch.object(
        pr_review_threads,
        "build_fetch_result",
        side_effect=[
            _state(),
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
    """A poll that times out once `deadline` has passed is the window ending, not an unconfirmed tail.

    Regression coverage for the Codex finding that replaced an invented safety reservation:
    `gh_timeout_budget` deliberately shrinks each `gh` call to whatever time is left, so the last
    poll of a window is *expected* to be cut short. Classifying that as a failure would exit
    non-zero on ordinary runs; classifying a failure that lands with time still on the clock as
    success would hide a genuine transient error. Only the clock distinguishes them.
    """
    fetch_mock = mocker.patch.object(
        pr_review_threads,
        "build_fetch_result",
        side_effect=[_state(), subprocess.TimeoutExpired(cmd=["gh"], timeout=30)],
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline=100). Iter 1: 0.0 (remaining=100 > the 10s interval) → poll raises; 100.0 in
    # the handler (>= deadline → the window ended, not a failure). Iter 2: 100.0 → remaining 0.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 100.0, 100.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["timed_out"] is True
    assert fetch_mock.call_count == 2


def test_watch_fails_loudly_on_a_nonzero_gh_exit_at_the_deadline(mocker: MockerFixture) -> None:
    """A non-zero `gh` exit is a failed poll whatever the clock says.

    The deadline-aware classification above applies to `TimeoutExpired` only. An authentication,
    rate-limit, API or GraphQL error is not explained by the shrinking budget, so reporting
    `timed_out: true` from stale state would tell a caller the PR is clean when nothing was checked.
    """
    mocker.patch.object(
        pr_review_threads, "build_fetch_result", side_effect=[_state(), subprocess.CalledProcessError(1, ["gh"])]
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # Same clock as the test above — 100.0 would have excused a TimeoutExpired but must not excuse
    # this. The handler reads no clock at all, so only four values are consumed.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 100.0, 100.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 1 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


def test_watch_rejects_a_non_positive_interval() -> None:
    """`--interval-seconds 0` would busy-loop `gh` calls until the timeout; Typer must reject it."""
    assert runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "0"]).exit_code != 0


def test_watch_rejects_a_negative_timeout() -> None:
    """`--timeout-seconds` is constrained to >= 0; 0 is the supported immediate-snapshot value."""
    assert runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "-1"]).exit_code != 0


def test_watch_first_fetch_is_not_deadline_bounded(mocker: MockerFixture) -> None:
    """`--timeout-seconds 0` returns an immediate snapshot rather than starving the first fetch.

    Regression coverage for the Codex finding that an already-spent deadline was applied to the
    mandatory first fetch, flooring its `gh` timeout and raising `TimeoutExpired` instead of
    producing the documented snapshot. That fetch takes the caller's `--gh-timeout-seconds`
    instead; only the polls race `deadline`.
    """
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["timed_out"] is True
    assert fetch_mock.call_args.kwargs == {"gh_timeout": None}


def test_gh_timeout_budget_without_a_deadline_uses_the_callers_bound() -> None:
    """No deadline means the caller's `--gh-timeout-seconds` applies unchanged, `None` included."""
    assert pr_review_gh.gh_timeout_budget(None, None) is None
    assert pr_review_gh.gh_timeout_budget(None, 12.5) == pytest.approx(12.5)


def test_gh_timeout_budget_with_a_deadline_uses_the_time_left() -> None:
    """A poll's bound is the time left before `deadline`, floored at zero once it has passed."""
    now = time.monotonic()

    assert pr_review_gh.gh_timeout_budget(now + 30, None) == pytest.approx(30, abs=1)
    assert pr_review_gh.gh_timeout_budget(now - 30, None) == pytest.approx(0.0)


def test_watch_fails_loudly_when_only_final_poll_fails(mocker: MockerFixture) -> None:
    """`watch` fails loudly when the *last* poll fails, even if an earlier poll in the same
    window succeeded.

    Regression coverage for a second Codex review, on the fix above: tracking whether *any* poll
    succeeded is not enough — an early success does not confirm the tail of the window after a
    later failure. If poll 1 succeeds (finding nothing outstanding) and poll 2 then fails as the
    window ends, `current` is stale (still poll 1's data) and the final stretch before `deadline`
    was never actually observed; `watch` must still fail rather than report a `timed_out: true`
    built from that stale state.
    """
    mocker.patch.object(
        pr_review_threads,
        "build_fetch_result",
        side_effect=[_state(), _state(), subprocess.TimeoutExpired(cmd=["gh"], timeout=30)],
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
