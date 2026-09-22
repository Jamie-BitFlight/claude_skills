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
"""Tests for exhaustive read-only review-cycle projections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import pr_review_threads
from pr_review_contracts import ReplyAction
from pr_review_state import ReviewAuthorizationError, authorize_action, validate_cycle_projection
from pr_review_state_models import ReviewCycleState
from review_test_fixtures import canonical_input, canonical_snapshot, ready_cycle
from review_test_gh_fixtures import runner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def dry_run_cycle() -> ReviewCycleState:
    """Return exhaustive projected state with every unperformed phase explicit."""
    item = canonical_input()
    return ready_cycle().model_copy(
        update={
            "implementation_evidence": ["pending: source action was not performed in this dry-run"],
            "verification_evidence": ["pending: verification was not performed in this dry-run"],
            "recheck_snapshot_fingerprint": "pending: no provider recheck was performed",
            "communication_states": {item.input_id: "pending"},
            "resolution_states": {item.input_id: "open"},
            "implementation_states": {item.input_id: "pending"},
            "terminal_annotations": {},
            "cycle_terminal": "action_pending",
            "cycle_state": "IMPLEMENTATION_REQUIRED",
        }
    )


def test_dry_run_projection_validates_exact_typed_cover_without_action_readiness() -> None:
    snapshot = canonical_snapshot()
    cycle = dry_run_cycle()

    inputs, assessments, clusters = validate_cycle_projection(snapshot, cycle)

    assert set(inputs) == {canonical_input().input_id}
    assert set(assessments) == set(inputs)
    assert set(clusters) == {"cluster-1"}
    with pytest.raises(ReviewAuthorizationError, match="READY_FOR_ACTION"):
        authorize_action(snapshot, cycle, canonical_input().input_id, ReplyAction(body="Not authorized."))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("input_census", [], "input census"),
        ("assessments", [], "assessment census"),
        ("clusters", [], "cluster membership"),
        ("communication_states", {}, "communication states"),
        ("resolution_states", {}, "resolution states"),
        ("implementation_states", {}, "implementation states"),
    ],
)
def test_dry_run_projection_rejects_omitted_typed_state(field: str, value: object, message: str) -> None:
    cycle = dry_run_cycle().model_copy(update={field: value})

    with pytest.raises(ReviewAuthorizationError, match=message):
        validate_cycle_projection(canonical_snapshot(), cycle)


def test_validate_projection_cli_reports_no_mutation_authority(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    state_path = tmp_path / "state.json"
    snapshot_path.write_text(canonical_snapshot().model_dump_json(), encoding="utf-8")
    state_path.write_text(dry_run_cycle().model_dump_json(), encoding="utf-8")
    provider = mocker.patch.object(pr_review_threads, "review_provider_for_target")

    result = runner.invoke(
        pr_review_threads.app,
        ["validate-projection", "--snapshot-file", str(snapshot_path), "--state-file", str(state_path)],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "snapshot_fingerprint": canonical_snapshot().snapshot_fingerprint,
        "inputs": 1,
        "assessments": 1,
        "clusters": 1,
        "cycle_state": "IMPLEMENTATION_REQUIRED",
        "cycle_terminal": "action_pending",
        "mutation_authorized": False,
    }
    provider.assert_not_called()


def test_validate_projection_rejects_completion_claim() -> None:
    cycle = dry_run_cycle().model_copy(update={"cycle_terminal": "review_complete", "cycle_state": "REVIEW_COMPLETE"})

    with pytest.raises(ReviewAuthorizationError, match="cannot assert REVIEW_COMPLETE"):
        validate_cycle_projection(canonical_snapshot(), cycle)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
