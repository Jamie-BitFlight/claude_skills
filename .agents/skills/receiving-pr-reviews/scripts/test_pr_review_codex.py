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
"""Tests for Codex-specific GitHub review signals."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

import pr_review_gh
from pr_review_gh import _is_codex_thumbs_up, build_fetch_result
from pr_review_models import Author, Reaction
from review_test_gh_fixtures import (
    _OLD_COMMIT_DATE,
    _default_github_detection as _default_github_detection,
    _empty_threads,
    _patch_identity_and_commit_date,
    _review,
    _reviews_conn,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_CODEX_EMPTY_REVIEW_BODY = (
    "\n### 💡 Codex Review\n\n"
    "Here are some automated review suggestions for this pull request.\n\n"
    "**Reviewed commit:** `a4929550cb`\n    \n\n"
    "<details> <summary>\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} About Codex in GitHub</summary>\n<br/>\n\n"
    "[Your team has set up Codex to review pull requests in this repo]"
    "(https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you\n"
    "- Open a pull request for review\n"
    "- Mark a draft as ready\n"
    '- Comment "@codex review".\n\n'
    "If Codex has suggestions, it will comment; otherwise it will react with 👍.\n\n\n\n\n"
    'Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".\n            \n'
    "</details>"
)


def test_build_fetch_result_codex_empty_review_is_not_unresponded(mocker: MockerFixture) -> None:
    """A Codex review whose entire body is its own fixed no-findings boilerplate is excluded from
    `unresponded_reviews` without needing a reply — every push posts one regardless of findings.

    Body captured verbatim from this repo's own PR history (#3318, #3306).
    """
    review = _review(
        "R1",
        body=_CODEX_EMPTY_REVIEW_BODY,
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        login="chatgpt-codex-connector[bot]",
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []
    assert result.reviews_with_body == [review]


def test_build_fetch_result_codex_review_with_real_findings_still_unresponded(mocker: MockerFixture) -> None:
    """A Codex review carrying the same wrapper plus an actual finding still requires a response —
    only the all-boilerplate body is excluded, not every review from Codex.
    """
    body_with_finding = _CODEX_EMPTY_REVIEW_BODY.replace(
        "Here are some automated review suggestions for this pull request.\n\n"
        "**Reviewed commit:** `a4929550cb`\n    \n\n",
        "**P1** Share the outer timeout across both CLI calls.\n    \n\n",
    )
    review = _review(
        "R1",
        body=body_with_finding,
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        login="chatgpt-codex-connector[bot]",
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_codex_review_with_finding_after_footer_still_unresponded(mocker: MockerFixture) -> None:
    """A Codex review that appends a real finding after the fixed footer's closing `</details>`
    tag still requires a response.

    Regression coverage: `_is_codex_empty_review` must reject the whole body via `fullmatch`, not
    merely find the fixed template pieces present via `.search()` — a search would still match the
    fixed prefix and footer and silently miss a finding tacked on after them.
    """
    body_with_trailing_finding = _CODEX_EMPTY_REVIEW_BODY + "\n\nP.S. Also consider extracting this into a helper."
    review = _review(
        "R1",
        body=body_with_trailing_finding,
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        login="chatgpt-codex-connector[bot]",
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_non_codex_boilerplate_lookalike_still_unresponded(mocker: MockerFixture) -> None:
    """A review from a different author whose body happens to match Codex's boilerplate text is
    not exempted — only the Codex bot's own login is excluded.
    """
    review = _review(
        "R1", body=_CODEX_EMPTY_REVIEW_BODY, submitted_at=datetime(2026, 1, 1, tzinfo=UTC), login="a-human-reviewer"
    )
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
    assert (
        _is_codex_thumbs_up(
            Reaction(content="+1", user=Author(login="chatgpt-codex-connector[bot]"), created_at=_OLD_COMMIT_DATE)
        )
        is True
    )
