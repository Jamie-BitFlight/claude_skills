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
"""Tests for multi-PR board output and polling attempt bounds."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import pr_review_threads
from pr_review_threads import app
from review_test_gh_fixtures import (
    _default_github_detection as _default_github_detection,
    _fetch_result,
    _state,
    _thread_with_comment,
    runner,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# --- multi-PR --pr ----------------------------------------------------------------------------


def test_fetch_multi_pr_prints_one_board_entry_per_pr_in_order(mocker: MockerFixture) -> None:
    """`--pr 41,42,44` without `--summary` prints one compact-JSON board entry per PR, in order,
    rather than the (potentially enormous) full JSON for each -- and rather than a hand-built
    text line, per this repository's own agent-only-output policy (AGENTS.md)."""
    states = {
        41: _fetch_result(unresolved=[_thread_with_comment()], mergeable="CONFLICTING", merge_state_status="DIRTY"),
        42: _fetch_result(),
        44: _fetch_result(codex_approved=True),
    }
    fetch_mock = mocker.patch.object(
        pr_review_threads, "build_fetch_result", side_effect=lambda _o, _r, pr, **_kw: states[pr]
    )

    result = runner.invoke(app, ["fetch", "--pr", "41,42,44"])

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in result.output.strip("\n").split("\n")]
    assert len(lines) == 3
    assert lines[0] == {
        "pr": 41,
        "unresolved": 1,
        "unresponded": 0,
        "codex_approved": False,
        "mergeable": "CONFLICTING",
        "merge_state_status": "DIRTY",
        "blockers": [],
    }
    assert lines[1] == {
        "pr": 42,
        "unresolved": 0,
        "unresponded": 0,
        "codex_approved": False,
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "blockers": [],
    }
    assert lines[2]["pr"] == 44
    assert lines[2]["codex_approved"] is True
    assert [call.args[2] for call in fetch_mock.call_args_list] == [41, 42, 44]


def test_fetch_multi_pr_with_summary_prints_one_json_line_per_pr(mocker: MockerFixture) -> None:
    """`--pr 41,42` with `--summary` prints one summary JSON block per PR, each self-describing
    via its own `pr` field, ordered as given."""
    states = {41: _fetch_result(unresolved=[_thread_with_comment()]), 42: _fetch_result()}
    mocker.patch.object(pr_review_threads, "build_fetch_result", side_effect=lambda _o, _r, pr, **_kw: states[pr])

    result = runner.invoke(app, ["fetch", "--pr", "41,42", "--summary"])

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in result.output.strip("\n").split("\n")]
    assert [line["pr"] for line in lines] == [41, 42]
    assert lines[0]["unresolved_count"] == 1
    assert lines[1]["unresolved_count"] == 0


def test_fetch_multi_pr_tolerates_whitespace_around_entries(mocker: MockerFixture) -> None:
    """`--pr "41, 42"` (with a space after the comma) parses the same as `--pr 41,42`."""
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result())

    result = runner.invoke(app, ["fetch", "--pr", "41, 42"])

    assert result.exit_code == 0, result.output
    assert [call.args[2] for call in fetch_mock.call_args_list] == [41, 42]


@pytest.mark.parametrize(
    "value",
    ["", "abc", "41,", "41,,42", "41, abc", "0", "-1", "41,0"],
    ids=["empty", "non-numeric", "trailing-comma", "empty-part", "mixed", "zero", "negative", "positive-then-zero"],
)
def test_fetch_rejects_a_malformed_pr_list(value: str, mocker: MockerFixture) -> None:
    """A malformed `--pr` value is rejected before any `gh` call is attempted -- including
    `--github` autodetection's own `gh repo view`, which would otherwise run first and could mask
    the actual `--pr` input error behind an unrelated detection failure."""
    detect_mock = mocker.patch.object(pr_review_threads, "detect_repo_identity")
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result")

    result = runner.invoke(app, ["fetch", "--pr", value])

    assert result.exit_code != 0
    fetch_mock.assert_not_called()
    detect_mock.assert_not_called()


def test_watch_attempt_budget_bounds_provider_snapshots(mocker: MockerFixture) -> None:
    fetch_mock = mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_state())
    mocker.patch.object(pr_review_threads.time, "sleep")
    mocker.patch.object(pr_review_threads.time, "monotonic", side_effect=[0.0, 0.0, 1.0])

    result = runner.invoke(
        app, ["watch", "--pr", "17", "--interval-seconds", "1", "--timeout-seconds", "100", "--max-attempts", "2"]
    )

    assert result.exit_code == 0, result.output
    assert fetch_mock.call_count == 2
    assert json.loads(result.output)["attempts"] == 2
    assert json.loads(result.output)["attempt_budget_exhausted"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
