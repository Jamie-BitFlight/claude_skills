#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
#   "pytest",
#   "pytest-mock",
# ]
# [tool.ty.environment]
# # ty 0.0.75 treats any file carrying PEP 723 inline script metadata as an
# # isolated single-file script and ignores [tool.ty.environment].extra-paths
# # from pyproject.toml entirely, so this table (not the one in pyproject.toml)
# # is what ty actually reads for this file. Relative extra-paths declared here
# # resolve relative to this script's own directory, not the invocation cwd or
# # the project root -- "." is therefore this directory, which is where the
# # sibling pr_review_threads, pr_review_gh, and pr_review_models modules live.
# # `ty check` already passes without this table (pyproject.toml's own
# # extra-paths entry for this directory covers it in practice), but it is
# # added here for parity with skilllint's copy of this script and to remove
# # the dependency on pyproject.toml staying in sync with this file's location.
# extra-paths = ["."]
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
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

import pr_review_gh
import pr_review_models
import pr_review_threads
from pr_review_models import (
    Author,
    CommentNode,
    FetchResult,
    IssueComment,
    PullRequestHeadState,
    Reviewability,
    ReviewNode,
    UnresolvedThread,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()


@pytest.fixture(autouse=True)
def _default_github_detection(mocker: MockerFixture) -> None:
    """Stub `--github` autodetection for every test in this module by default.

    Every `fetch`/`watch`/`reply` invocation below that omits `--github` would otherwise shell out
    to the real `gh repo view` during the test run. The tests under "--github: autodetect vs
    explicit override" re-patch `detect_repo_identity` themselves to cover detection directly; this
    fixture only keeps every other test's `--github`-less invocation decoupled from it.
    """
    mocker.patch.object(pr_review_threads, "detect_repo_identity", return_value=("o", "r"))


_AGENT_LOGIN = "reviewing-agent"
_OLD_COMMIT_DATE = datetime(2025, 12, 1, tzinfo=UTC)


def _thread_page(*, has_next_page: bool, nodes: list[dict[str, object]], total_count: int) -> dict[str, object]:
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
    return json.dumps([list(items)])


def _review_url(review_id: str) -> str:
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
    body = f"Addressed {references.url}." if references is not None else "An unrelated administrative note."
    return IssueComment(created_at=created_at, user=Author(login=login), body=body)


def _head_state(
    commit_date: datetime = _OLD_COMMIT_DATE,
    *,
    is_draft: bool = False,
    mergeable: str = "MERGEABLE",
    merge_state_status: str = "CLEAN",
) -> PullRequestHeadState:
    return PullRequestHeadState.model_validate({
        "isDraft": is_draft,
        "mergeable": mergeable,
        "mergeStateStatus": merge_state_status,
        "commits": {"nodes": [{"commit": {"committedDate": commit_date}}]},
    })


def _state(
    *, unresolved_count: int = 0, unresponded_reviews: list[ReviewNode] | None = None, codex_approved: bool = False
) -> FetchResult:
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


def _thread_with_comment(
    thread_id: str = "T1",
    *,
    path: str = "x.py",
    body: str = "look at this",
    line: int | None = 10,
    login: str | None = "reviewer",
) -> UnresolvedThread:
    return UnresolvedThread(
        id=thread_id,
        path=path,
        comments=[
            CommentNode(
                databaseId=42,
                body=body,
                line=line,
                originalLine=line,
                author=Author(login=login) if login is not None else None,
            )
        ],
        comments_truncated=False,
    )


def _fetch_result(
    *,
    unresolved: list[UnresolvedThread] | None = None,
    unresponded_reviews: list[ReviewNode] | None = None,
    blockers: list[str] | None = None,
    codex_approved: bool = False,
    mergeable: str = "MERGEABLE",
    merge_state_status: str = "CLEAN",
) -> FetchResult:
    unresolved = unresolved or []
    unresponded_reviews = unresponded_reviews or []
    return FetchResult(
        reviews_count=len(unresponded_reviews),
        reviews_with_body=unresponded_reviews,
        unresponded_reviews=unresponded_reviews,
        threads_count=len(unresolved),
        unresolved=unresolved,
        unresolved_count=len(unresolved),
        codex_approved=codex_approved,
        reviewability=Reviewability(
            is_draft=False, mergeable=mergeable, merge_state_status=merge_state_status, blockers=blockers or []
        ),
    )


def _validation_error() -> ValidationError:
    try:
        pr_review_models.GitHubCommitDate.model_validate({"committedDate": "not-a-timestamp"})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected ValidationError")


def _reviews_conn(nodes: list[ReviewNode]) -> pr_review_gh.ReviewsConnection:
    return pr_review_gh.ReviewsConnection(totalCount=len(nodes), nodes=nodes)


def _empty_threads() -> list[pr_review_gh.ReviewThreadsConnection]:
    return [pr_review_gh.ReviewThreadsConnection(totalCount=0, nodes=[])]


def _patch_identity_and_commit_date(
    mocker: MockerFixture,
    *,
    login: str = _AGENT_LOGIN,
    commit_date: datetime = _OLD_COMMIT_DATE,
    force_push_at: datetime | None = None,
) -> None:
    """Stub unrelated calls required by focused fetch-result tests.

    The three `build_fetch_result` calls every matrix test below needs but does not itself
    exercise — the authenticated identity (for `unresponded_reviews`), the PR head state (its
    commit date, for `codex_approved`, plus the reviewability fields), and the latest force-push
    timestamp (also for `codex_approved`) — so each test's own `_fetch_*` mocks stay focused on
    what it covers. `force_push_at` defaults to `None` (this PR has never been force-pushed),
    matching most tests' scenarios, and the stubbed head state is a plain reviewable PR.
    """
    mocker.patch.object(pr_review_gh, "_fetch_authenticated_login", return_value=login)
    mocker.patch.object(pr_review_gh, "_fetch_head_state", return_value=_head_state(commit_date))
    mocker.patch.object(pr_review_gh, "_fetch_latest_force_push_at", return_value=force_push_at)
