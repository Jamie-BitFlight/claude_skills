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
"""Tests for review-response detection in GitHub fetch results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

import pr_review_gh
from pr_review_gh import build_fetch_result
from pr_review_models import Author, IssueComment
from review_test_gh_fixtures import (
    _AGENT_LOGIN,
    _default_github_detection as _default_github_detection,
    _empty_threads,
    _own_comment,
    _patch_identity_and_commit_date,
    _review,
    _reviews_conn,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
