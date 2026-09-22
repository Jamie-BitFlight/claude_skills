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
"""Focused regressions for receiving-review correction cycles."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_contracts import ReviewActionResult
from pr_review_github_normalize import communicated_inputs
from pr_review_gitlab_normalize import normalize_state
from pr_review_output import action_view
from pr_review_threads import app
from review_test_fixtures import canonical_input, write_ready_files
from review_test_gitlab_fixtures import state as gitlab_state, target as gitlab_target

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


runner = CliRunner()


def gated_args(snapshot_file: Path, state_file: Path) -> list[str]:
    """Return the common authorized GitHub command arguments."""
    return [
        "--input-id",
        canonical_input().input_id,
        "--snapshot-file",
        str(snapshot_file),
        "--state-file",
        str(state_file),
        "--github",
        "acme/widgets",
    ]


def test_github_same_thread_follow_up_after_an_outbound_reply_remains_actionable() -> None:
    """Only inbound input that predates its same-thread answer is communicated."""
    opening = canonical_input().model_copy(
        update={"created_at": datetime(2026, 1, 1, tzinfo=UTC), "stable_reference": "opening-reference"}
    )
    response = opening.model_copy(
        update={
            "input_id": "github:review-comment:43",
            "direction": "outbound",
            "created_at": datetime(2026, 1, 2, tzinfo=UTC),
            "body": "Addressed the opening concern.",
        }
    )
    follow_up = opening.model_copy(
        update={
            "input_id": "github:review-comment:44",
            "created_at": datetime(2026, 1, 3, tzinfo=UTC),
            "stable_reference": "follow-up-reference",
            "body": "Please also address this later concern.",
        }
    )

    assert communicated_inputs([opening, response, follow_up]) == {opening.input_id}


def test_action_view_excludes_stale_gitlab_input_bodies() -> None:
    """GitLab stale inputs remain private reconciliation evidence, not live action output."""
    snapshot = normalize_state(gitlab_state(), gitlab_target())
    stale = snapshot.review_inputs[0].model_copy(update={"revision_relation": "stale", "body": "STALE-GITLAB"})

    rendered = action_view(snapshot.model_copy(update={"review_inputs": [stale]}), pr=3).model_dump_json()

    assert "STALE-GITLAB" not in rendered
    assert action_view(snapshot.model_copy(update={"review_inputs": [stale]}), pr=3).actionable_inputs == []


def test_reply_and_resolve_rejects_an_unconfirmed_resolution_without_persisting_it(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """A reply may persist before a failed resolve, but resolution itself remains open."""
    snapshot_file, state_file = write_ready_files(tmp_path)
    provider = mocker.Mock()
    provider.snapshot.return_value = pr_review_threads.load_snapshot(snapshot_file)
    provider.act.side_effect = [
        ReviewActionResult(provider="github", action_kind="reply", success=True, provider_object_id="99", raw={}),
        ReviewActionResult(provider="github", action_kind="resolve", success=False, provider_object_id=None, raw={}),
    ]
    mocker.patch.object(pr_review_threads, "review_provider", return_value=provider)

    result = runner.invoke(
        app, ["reply-and-resolve", "--pr", "17", "--body", "Addressed.", *gated_args(snapshot_file, state_file)]
    )

    assert result.exit_code != 0
    assert provider.act.call_count == 2
    persisted = pr_review_threads.load_cycle(state_file)
    assert persisted.communication_states[canonical_input().input_id] == "completed"
    assert persisted.resolution_states[canonical_input().input_id] == "open"


@pytest.mark.parametrize(
    ("argv", "target"),
    [
        (["fetch", "--pr", "17", "--github", "acme/widgets"], "github"),
        (
            ["fetch", "--pr", "17", "--provider", "gitlab", "--repo", "acme/widgets", "--host", "gitlab.example.test"],
            "gitlab",
        ),
    ],
)
def test_fetch_surfaces_complete_provider_stderr_after_target_resolution(
    argv: list[str], target: str, mocker: MockerFixture
) -> None:
    """Fetch preserves provider diagnostics for GitHub and GitLab snapshot failures."""
    diagnostic = f"PROVIDER-{target}: authentication required\\nPROVIDER-{target}: retry after reset"
    provider = mocker.Mock()
    provider.snapshot.side_effect = subprocess.CalledProcessError(7, [target], stderr=diagnostic)
    mocker.patch.object(pr_review_threads, "review_provider_for_target", return_value=provider)

    result = runner.invoke(app, argv)

    assert result.exit_code != 0
    assert diagnostic in result.output
