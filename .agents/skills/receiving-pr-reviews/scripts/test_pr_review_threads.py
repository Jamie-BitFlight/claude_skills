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
authenticated `gh` identity's own PR-level comments (and its exclusion of comments from any other
account, including Codex or another bystander), and `codex_approved` reaction detection scoped to
reactions that postdate the PR's current head commit — all as one JSON-in/JSON-out pipeline test
plus a matrix of focused unit tests against `build_fetch_result` directly. Also covers
`FetchResult.has_outstanding_work` (the single trigger rule `watch` polls for) and `watch`'s own
loop: returning immediately when the first fetch is already actionable, polling until it becomes
actionable, timing out when it never does, and the deadline-budget/transient-failure mechanics
carried over from the pre-existing polling loop.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_gh
import pr_review_threads
from pr_review_gh import _is_codex_thumbs_up, build_fetch_result
from pr_review_models import Author, FetchResult, IssueComment, Reaction, ReviewNode, UnresolvedThread
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


def _review(review_id: str, *, body: str, submitted_at: datetime | None, login: str = "codex") -> ReviewNode:
    return ReviewNode(id=review_id, author=Author(login=login), state="COMMENTED", body=body, submittedAt=submitted_at)


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
    )


def _reviews_conn(nodes: list[ReviewNode]) -> pr_review_gh.ReviewsConnection:
    return pr_review_gh.ReviewsConnection(totalCount=len(nodes), nodes=nodes)


def _empty_threads() -> list[pr_review_gh.ReviewThreadsConnection]:
    """A single empty `reviewThreads` page — `build_fetch_result` always indexes page zero."""
    return [pr_review_gh.ReviewThreadsConnection(totalCount=0, nodes=[])]


def _patch_identity_and_commit_date(
    mocker: MockerFixture, *, login: str = _AGENT_LOGIN, commit_date: datetime = _OLD_COMMIT_DATE
) -> None:
    """Stub the two `build_fetch_result` calls every matrix test below needs but does not itself
    exercise — the authenticated identity (for `unresponded_reviews`) and the head commit date
    (for `codex_approved`) — so each test's own `_fetch_*` mocks stay focused on what it covers.
    """
    mocker.patch.object(pr_review_gh, "_fetch_authenticated_login", return_value=login)
    mocker.patch.object(pr_review_gh, "_fetch_latest_commit_date", return_value=commit_date)


# --- fetch: full JSON-in/JSON-out pipeline -----------------------------------------------------


def test_fetch_flattens_pages_filters_resolved_and_derives_new_fields(mocker: MockerFixture) -> None:
    """`fetch` flattens multi-page thread results, dropping resolved threads and counting right,
    and derives `unresponded_reviews` and `codex_approved` from the issue-comments, reactions,
    authenticated-identity, and head-commit-date calls in the same pipeline.

    Two thread pages are fed to `run_gh` (page 1 has a resolved and an unresolved thread; page
    2's lone thread has `comments.pageInfo.hasNextPage: true`). One reviews page has a review with
    a null `author` (a deleted account) alongside an empty-body review — both must be parsed
    without error, and only the non-empty-body review must survive into `reviews_with_body`. One
    PR-level comment, authored by the same identity `gh` is authenticated as, postdates the
    review, so it must NOT appear in `unresponded_reviews`. One reaction is Codex's "+1", and it
    postdates the PR's head commit, so `codex_approved` must be `True`.
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
                {
                    "id": "R1",
                    "author": {"login": "codex"},
                    "state": "COMMENTED",
                    "body": "Some feedback",
                    "submittedAt": "2026-01-01T00:00:00Z",
                },
                {"id": "R2", "author": None, "state": "APPROVED", "body": "", "submittedAt": "2026-01-01T00:00:00Z"},
            ],
        )
    ]
    issue_comments_raw = _rest_pages({"created_at": "2026-01-02T00:00:00Z", "user": {"login": _AGENT_LOGIN}})
    reactions_raw = _rest_pages({
        "content": "+1",
        "user": {"login": "chatgpt-codex-connector[bot]"},
        "created_at": "2026-01-03T00:00:00Z",
    })
    commits_raw = _rest_pages({"commit": {"committer": {"date": "2026-01-01T12:00:00Z"}}})
    mocker.patch.object(
        pr_review_gh,
        "run_gh",
        side_effect=[
            json.dumps(thread_pages),
            json.dumps(reviews_pages),
            issue_comments_raw,
            reactions_raw,
            _AGENT_LOGIN,
            commits_raw,
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


def test_build_fetch_result_responded_when_own_pr_comment_postdates_review(mocker: MockerFixture) -> None:
    """A review is excluded from `unresponded_reviews` once the authenticated identity's own
    PR-level comment postdates it.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    comment = IssueComment(created_at=datetime(2026, 1, 2, tzinfo=UTC), user=Author(login=_AGENT_LOGIN))
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == []


def test_build_fetch_result_unresponded_when_own_pr_comment_predates_review(mocker: MockerFixture) -> None:
    """A review submitted after the newest of the authenticated identity's own PR-level comments
    is still unresponded.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 2, tzinfo=UTC))
    comment = IssueComment(created_at=datetime(2026, 1, 1, tzinfo=UTC), user=Author(login=_AGENT_LOGIN))
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(pr_review_gh, "_fetch_issue_comments", return_value=[comment])
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


def test_build_fetch_result_unresponded_when_only_other_accounts_commented(mocker: MockerFixture) -> None:
    """A review stays unresponded when a PR-level comment postdates it but was authored by an
    account other than the currently-authenticated `gh` identity.

    Regression coverage for a Codex review on the previous design: any PR-level comment at all —
    an unrelated bystander, a bot, a CI notification — used to silence the review even though
    nothing evidenced that comment actually addressed the review's feedback.
    """
    review = _review("R1", body="feedback", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))
    unrelated_comment = IssueComment(created_at=datetime(2026, 1, 2, tzinfo=UTC), user=Author(login="a-bystander"))
    deleted_account_comment = IssueComment(created_at=datetime(2026, 1, 3, tzinfo=UTC), user=None)
    mocker.patch.object(pr_review_gh, "_fetch_pages", return_value=_empty_threads())
    mocker.patch.object(pr_review_gh, "_fetch_review_pages", return_value=[_reviews_conn([review])])
    mocker.patch.object(
        pr_review_gh, "_fetch_issue_comments", return_value=[unrelated_comment, deleted_account_comment]
    )
    mocker.patch.object(pr_review_gh, "_fetch_pr_reactions", return_value=[])
    _patch_identity_and_commit_date(mocker)

    result = build_fetch_result("o", "r", 1)

    assert result.unresponded_reviews == [review]


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


@pytest.mark.parametrize(
    "reaction",
    [
        Reaction(content="heart", user=Author(login="chatgpt-codex-connector[bot]"), created_at=_OLD_COMMIT_DATE),
        Reaction(content="+1", user=Author(login="some-human"), created_at=_OLD_COMMIT_DATE),
        Reaction(content="+1", user=None, created_at=_OLD_COMMIT_DATE),
    ],
    ids=["wrong-content", "wrong-user", "null-user"],
)
def test_is_codex_thumbs_up_false_for_non_matching_reactions(reaction: Reaction) -> None:
    """Only a "+1" from a `chatgpt-codex-connector`-prefixed login counts as Codex's approval."""
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

    # timeout-seconds must clear _MIN_POLL_BUDGET_SECONDS with real headroom: with time.sleep
    # mocked to a no-op, almost no wall-clock time elapses between polls, so a timeout right at
    # (or below) the guard threshold spuriously trips it before this test's second poll runs.
    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

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


def test_watch_skips_final_poll_when_budget_too_low(mocker: MockerFixture) -> None:
    """`watch` stops polling, without attempting a doomed call, once the budget remaining before
    `deadline` drops below `_MIN_POLL_BUDGET_SECONDS`.

    Regression coverage: `gh_timeout_budget` floors an exhausted deadline to 0.1s — far too little
    for a real `gh` call. Because `_DEFAULT_WATCH_TIMEOUT_SECONDS` is an exact multiple of
    `_DEFAULT_WATCH_INTERVAL_SECONDS` (270 / 90 = 3), the loop's final sleep lands within a
    fraction of a second of `deadline` on essentially every real run, so an unguarded poll there
    reliably raised `TimeoutExpired` instead of returning a clean `timed_out` result. Mocks
    `time.monotonic` to a fixed sequence matching the loop's real call order (deadline
    computation, the loop condition, the sleep-duration calculation, the budget check) so the
    near-deadline condition is reproduced without a real wait.
    """
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline = 0.0 + 100), 0.0 (loop condition), 0.0 (sleep-duration calc), 96.0 (budget
    # check: 100.0 - 96.0 = 4.0 < _MIN_POLL_BUDGET_SECONDS's 5.0 — guard fires, loop breaks).
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 96.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "90", "--timeout-seconds", "100"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    # Only the first fetch happened — the guard prevented a second, doomed poll attempt.
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

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "20"])

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
    fixed sequence for exactly two failed poll attempts (each iteration: loop condition,
    sleep-duration calc, guard check) followed by the window naturally expiring, matching the real
    function's call order the same way `test_watch_skips_final_poll_when_budget_too_low` does.
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


def test_watch_polls_final_leg_instead_of_skipping_it(mocker: MockerFixture) -> None:
    """`watch` attempts a final poll on a normal-length last leg instead of sleeping straight to
    `deadline` and skipping it.

    Regression coverage for a Codex review on the earlier fix: with `--timeout-seconds 100` and
    `--interval-seconds 90`, after the first poll at t=90 only 10s remain — under the pre-fix
    sleep formula (`min(interval_seconds, deadline - now)`), the second poll would sleep the full
    10s straight to `deadline` (t=100), where the guard's `deadline - now < _MIN_POLL_BUDGET_SECONDS`
    (100-100=0 < 5) fires and skips it entirely, leaving that whole final stretch unconfirmed even
    on total success. The fixed formula reserves `_MIN_POLL_BUDGET_SECONDS`, sleeping only to
    t=95 (`min(90, 100-5-90)=5`), where `100-95=5` does *not* trip the guard, so the second poll
    is attempted and finds the new activity it otherwise would have missed for this call entirely.
    """
    fetch_mock = mocker.patch.object(
        pr_review_threads, "build_fetch_result", side_effect=[_state(), _state(), _state(unresolved_count=1)]
    )
    mocker.patch.object(pr_review_threads.time, "sleep")
    # 0.0 (deadline=100). Iter 1: 0.0 (loop cond), 0.0 (sleep calc: min(90,95)=90), 90.0 (guard:
    # 100-90=10 ≥ 5) → poll succeeds, nothing outstanding. Iter 2: 90.0 (loop cond), 90.0 (sleep
    # calc: min(90, 100-5-90=5)=5 — the fixed reservation, not the interval), 95.0 (guard:
    # 100-95=5, not < 5) → poll attempted (would have been skipped under the pre-fix formula) and
    # finds the unresolved thread.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 90.0, 90.0, 90.0, 95.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "90", "--timeout-seconds", "100"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["state"]["unresolved_count"] == 1
    assert fetch_mock.call_count == 3


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
    # Same 8-call shape as the all-fail test above, but iter 1's poll succeeds this time (finding
    # nothing outstanding, so the loop does not break) before iter 2's poll fails as the window ends.
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 10.0, 20.0, 20.0, 30.0, 105.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 2 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)
