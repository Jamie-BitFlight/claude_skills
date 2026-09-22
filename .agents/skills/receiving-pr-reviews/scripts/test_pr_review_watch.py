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
"""Tests for bounded review polling and provider failure handling."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import pr_review_gh
import pr_review_threads
from pr_review_models import FetchResult
from pr_review_state_models import calculate_snapshot_fingerprint
from pr_review_threads import app
from review_test_fixtures import canonical_input, canonical_snapshot
from review_test_gh_fixtures import (
    _default_github_detection as _default_github_detection,
    _review,
    _state,
    _validation_error,
    runner,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

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
    assert data["dashboard"]["unresolved_code_thread_count"] == 1


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
    assert data["dashboard"]["unresolved_code_thread_count"] == 1


def test_watch_survives_a_validation_error_mid_window(mocker: MockerFixture) -> None:
    """A malformed `gh` API response mid-window (`build_fetch_result`'s own `.model_validate()`
    rejecting it) does not crash `watch` — it counts as no fresh data for that one poll, the same
    as a `CalledProcessError`, and the loop continues toward `deadline` on its own schedule.
    """
    mocker.patch.object(
        pr_review_threads, "build_fetch_result", side_effect=[_state(), _validation_error(), _state(unresolved_count=1)]
    )
    mocker.patch.object(pr_review_threads.time, "sleep")

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "1", "--timeout-seconds", "40"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is False
    assert data["dashboard"]["unresolved_code_thread_count"] == 1


def test_watch_fails_loudly_on_a_validation_error_at_the_deadline(mocker: MockerFixture) -> None:
    """A `ValidationError` from the last poll of a window is a failed poll, the same as a
    non-zero `gh` exit — it is not explained or excused by the deadline, so reporting
    `timed_out: true` off stale state here would tell a caller the PR is clean when the last check
    actually raised.
    """
    mocker.patch.object(pr_review_threads, "build_fetch_result", side_effect=[_state(), _validation_error()])
    mocker.patch.object(pr_review_threads.time, "sleep")
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 100.0, 100.0])

    result = runner.invoke(app, ["watch", "--pr", "3208", "--interval-seconds", "10", "--timeout-seconds", "100"])

    assert result.exit_code != 0
    assert "the last of 1 poll(s) this window failed" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


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
    assert fetch_mock.call_args.kwargs["gh_timeout"] == pytest.approx(30)
    assert fetch_mock.call_args.kwargs["target"].number == 3208
    dashboard = json.loads(result.output)["dashboard"]
    assert dashboard["provider"] == "github"
    assert dashboard["pr"] == 3208
    assert dashboard["snapshot_complete"] is True


def test_watch_first_snapshot_uses_tighter_caller_command_timeout(mocker: MockerFixture) -> None:
    """The first snapshot honors a caller timeout smaller than the watch deadline."""
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state(unresolved_count=1))

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "270", "--gh-timeout-seconds", "5"])

    assert result.exit_code == 0, result.output
    assert fetch_mock.call_args.kwargs["gh_timeout"] == pytest.approx(5)


def test_watch_stops_when_first_snapshot_differs_from_saved_baseline(tmp_path: Path, mocker: MockerFixture) -> None:
    """A change before the first poll still returns to census when the caller supplies its baseline."""
    baseline = canonical_snapshot().model_copy(update={"unresolved_count": 0, "outstanding_input_count": 0})
    changed_input = canonical_input().model_copy(update={"provider_state": "resolved"})
    fingerprint = calculate_snapshot_fingerprint(
        baseline.target,
        baseline.head_revision,
        [changed_input],
        baseline.completeness,
        revision_at=baseline.revision_at,
        reviewability=baseline.reviewability,
        provider_metadata=baseline.provider_metadata,
        communicated_input_ids=baseline.communicated_input_ids,
    )
    changed = baseline.model_copy(update={"review_inputs": [changed_input], "snapshot_fingerprint": fingerprint})
    baseline_file = tmp_path / "watch-baseline.json"
    baseline_file.write_text(baseline.model_dump_json(), encoding="utf-8")
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=changed)

    result = runner.invoke(
        app,
        [
            "watch",
            "--pr",
            "17",
            "--github",
            "acme/widgets",
            "--timeout-seconds",
            "0",
            "--baseline-snapshot-file",
            str(baseline_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["timed_out"] is False


def test_gh_timeout_budget_without_a_deadline_uses_the_callers_bound() -> None:
    """No deadline uses the caller's timeout or the mandatory default when omitted."""
    assert pr_review_gh.gh_timeout_budget(None, None) == pytest.approx(30)
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
