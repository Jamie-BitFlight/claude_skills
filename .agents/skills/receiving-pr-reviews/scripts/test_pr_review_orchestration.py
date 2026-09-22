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
"""Mutation authorization, ordering, validation, and timeout tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import pr_review_threads
from pr_review_cli_actions import authorized_action
from pr_review_contracts import ReplyAction, ReviewActionResult
from pr_review_models import ReviewSnapshot
from pr_review_provider import ProviderResponseError
from pr_review_state_models import (
    ProviderInputIdentity,
    ReviewAssessment,
    ReviewCluster,
    ReviewInput,
    calculate_snapshot_fingerprint,
)
from pr_review_threads import app
from review_test_fixtures import canonical_input, canonical_snapshot, ready_cycle, write_ready_files

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

runner = CliRunner()


def fingerprint_for(snapshot: ReviewSnapshot, inputs: list[ReviewInput]) -> str:
    """Recalculate a customized snapshot with every authorization field."""
    return calculate_snapshot_fingerprint(
        snapshot.target,
        snapshot.head_revision,
        inputs,
        snapshot.completeness,
        revision_at=snapshot.revision_at,
        reviewability=snapshot.reviewability,
        provider_metadata=snapshot.provider_metadata,
        communicated_input_ids=snapshot.communicated_input_ids,
    )


def resolved_response() -> str:
    """Return one confirmed resolve mutation payload."""
    return json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}})


def gated_args(snapshot_file: Path, state_file: Path) -> list[str]:
    """Return shared current-cycle CLI arguments."""
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


def mock_live_snapshot(snapshot_file: Path, mocker: MockerFixture) -> None:
    """Make the mandatory provider refresh return the saved current snapshot."""
    mocker.patch.object(
        pr_review_threads, "build_fetch_result", return_value=pr_review_threads.load_snapshot(snapshot_file)
    )


def test_raw_reply_without_cycle_evidence_is_rejected_before_provider_call(mocker: MockerFixture) -> None:
    run_mock = mocker.patch.object(pr_review_threads, "run_gh")

    result = runner.invoke(app, ["reply", "--pr", "17", "--input-id", canonical_input().input_id, "--body", "x"])

    assert result.exit_code != 0
    run_mock.assert_not_called()


def test_authorized_action_rejects_saved_snapshot_when_live_state_changed(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    live = canonical_snapshot().model_copy(update={"head_revision": "new-head"})
    provider = mocker.Mock()
    provider.snapshot.return_value = live

    with pytest.raises(ProviderResponseError, match="no longer current"):
        authorized_action(
            canonical_snapshot().target,
            snapshot_file,
            state_file,
            canonical_input().input_id,
            ReplyAction(body="Addressed."),
            provider=provider,
            command_timeout=7.0,
        )

    provider.snapshot.assert_called_once_with(canonical_snapshot().target, deadline=None, command_timeout=7.0)


def test_validate_cycle_checks_complete_evidence_without_provider_mutation(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    run_mock = mocker.patch.object(pr_review_threads, "run_gh")

    result = runner.invoke(
        app, ["validate-cycle", "--snapshot-file", str(snapshot_file), "--state-file", str(state_file)]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "validation": "action_ready",
        "cycle_state": "READY_FOR_ACTION",
        "cycle_terminal": "action_pending",
    }
    run_mock.assert_not_called()


def test_complete_cycle_refreshes_provider_evidence_and_persists_only_success_terminal(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    snapshot = pr_review_threads.load_snapshot(snapshot_file)
    communicated = {canonical_input().input_id}
    fingerprint = calculate_snapshot_fingerprint(
        snapshot.target,
        snapshot.head_revision,
        snapshot.review_inputs,
        snapshot.completeness,
        revision_at=snapshot.revision_at,
        reviewability=snapshot.reviewability,
        provider_metadata=snapshot.provider_metadata,
        communicated_input_ids=communicated,
    )
    snapshot = snapshot.model_copy(
        update={
            "communicated_input_ids": communicated,
            "snapshot_fingerprint": fingerprint,
            "unresolved_count": 0,
            "outstanding_input_count": 0,
        }
    )
    snapshot_file.write_text(snapshot.model_dump_json())
    cycle = pr_review_threads.load_cycle(state_file).model_copy(
        update={
            "snapshot_fingerprint": fingerprint,
            "recheck_snapshot_fingerprint": fingerprint,
            "communication_states": {canonical_input().input_id: "completed"},
            "resolution_states": {canonical_input().input_id: "resolved"},
            "implementation_states": {canonical_input().input_id: "completed"},
            "terminal_annotations": {canonical_input().input_id: "Verified provider-backed completion."},
        }
    )
    state_file.write_text(cycle.model_dump_json())
    mock_live_snapshot(snapshot_file, mocker)

    result = runner.invoke(
        app,
        [
            "complete-cycle",
            "--pr",
            "17",
            "--snapshot-file",
            str(snapshot_file),
            "--state-file",
            str(state_file),
            "--github",
            "acme/widgets",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"cycle_state": "REVIEW_COMPLETE", "cycle_terminal": "review_complete"}
    persisted = pr_review_threads.load_cycle(state_file)
    assert persisted.cycle_state == "REVIEW_COMPLETE"
    assert persisted.cycle_terminal == "review_complete"


@pytest.mark.parametrize("command", ["reply", "resolve"], ids=["reply", "resolve"])
def test_mutation_commands_forward_timeout_bound(command: str, tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    mock_live_snapshot(snapshot_file, mocker)
    if command == "resolve":
        completed_cycle = ready_cycle().model_copy(
            update={"communication_states": {canonical_input().input_id: "completed"}}
        )
        state_file.write_text(completed_cycle.model_dump_json())
    response = json.dumps({"id": 1}) if command == "reply" else resolved_response()
    run_mock = mocker.patch.object(pr_review_threads, "run_gh", return_value=response)
    argv = [command, "--pr", "17", *gated_args(snapshot_file, state_file), "--gh-timeout-seconds", "7"]
    if command == "reply":
        argv.extend(["--body", "Addressed."])

    result = runner.invoke(app, argv)

    assert result.exit_code == 0, result.output
    expected = (
        {"input_id": canonical_input().input_id, "replied": True}
        if command == "reply"
        else {"input_id": canonical_input().input_id, "resolved": True}
    )
    assert json.loads(result.output) == expected
    assert run_mock.call_args.kwargs["timeout"] == pytest.approx(7)
    persisted = pr_review_threads.load_cycle(state_file)
    if command == "reply":
        assert persisted.communication_states[canonical_input().input_id] == "completed"
    else:
        assert persisted.resolution_states[canonical_input().input_id] == "resolved"


def test_reply_and_resolve_does_not_resolve_after_invalid_reply(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    mock_live_snapshot(snapshot_file, mocker)
    run_mock = mocker.patch.object(pr_review_threads, "run_gh", return_value="{}")

    result = runner.invoke(
        app, ["reply-and-resolve", "--pr", "17", "--body", "Addressed.", *gated_args(snapshot_file, state_file)]
    )

    assert result.exit_code != 0
    assert run_mock.call_count == 1
    assert pr_review_threads.load_cycle(state_file).communication_states[canonical_input().input_id] == "pending"


def test_reply_and_resolve_does_not_record_or_resolve_after_unsuccessful_provider_result(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """An unconfirmed reply leaves the cycle pending and prevents resolution."""
    snapshot_file, state_file = write_ready_files(tmp_path)
    provider = mocker.Mock()
    provider.snapshot.return_value = pr_review_threads.load_snapshot(snapshot_file)
    provider.act.return_value = ReviewActionResult(
        provider="github", action_kind="reply", success=False, provider_object_id=None, raw={}
    )
    mocker.patch.object(pr_review_threads, "review_provider", return_value=provider)

    result = runner.invoke(
        app, ["reply-and-resolve", "--pr", "17", "--body", "Addressed.", *gated_args(snapshot_file, state_file)]
    )

    assert result.exit_code != 0
    assert provider.act.call_count == 1, result.output
    assert pr_review_threads.load_cycle(state_file).communication_states[canonical_input().input_id] == "pending"


def test_reply_and_resolve_rejects_graphql_errors(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    mock_live_snapshot(snapshot_file, mocker)
    run_mock = mocker.patch.object(
        pr_review_threads,
        "run_gh",
        side_effect=[json.dumps({"id": 99}), json.dumps({"errors": [{"message": "denied"}]})],
    )

    result = runner.invoke(
        app, ["reply-and-resolve", "--pr", "17", "--body", "Addressed.", *gated_args(snapshot_file, state_file)]
    )

    assert result.exit_code != 0
    assert run_mock.call_count == 2
    persisted = pr_review_threads.load_cycle(state_file)
    assert persisted.communication_states[canonical_input().input_id] == "completed"
    assert persisted.resolution_states[canonical_input().input_id] == "open"


def test_reply_and_resolve_preflights_resolution_before_reply(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    snapshot = pr_review_threads.load_snapshot(snapshot_file)
    item = snapshot.review_inputs[0].model_copy(
        update={"capabilities": snapshot.review_inputs[0].capabilities.model_copy(update={"can_resolve": False})}
    )
    fingerprint = fingerprint_for(snapshot, [item])
    snapshot_file.write_text(
        snapshot.model_copy(update={"review_inputs": [item], "snapshot_fingerprint": fingerprint}).model_dump_json()
    )
    cycle = pr_review_threads.load_cycle(state_file).model_copy(
        update={"snapshot_fingerprint": fingerprint, "recheck_snapshot_fingerprint": fingerprint}
    )
    state_file.write_text(cycle.model_dump_json())
    mock_live_snapshot(snapshot_file, mocker)
    run_mock = mocker.patch.object(pr_review_threads, "run_gh")

    result = runner.invoke(
        app, ["reply-and-resolve", "--pr", "17", "--body", "Addressed.", *gated_args(snapshot_file, state_file)]
    )

    assert result.exit_code != 0
    run_mock.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [{"input_id": canonical_input().input_id, "body": ""}],
        [{"input_id": canonical_input().input_id, "body": "   "}],
        [{"input_id": canonical_input().input_id, "body": "x"}, {"input_id": canonical_input().input_id, "body": "y"}],
    ],
    ids=["not-list", "empty-body", "blank-body", "duplicate-input"],
)
def test_batch_validates_all_entries_before_first_provider_call(
    payload: object, tmp_path: Path, mocker: MockerFixture
) -> None:
    snapshot_file, state_file = write_ready_files(tmp_path)
    input_file = tmp_path / "batch.json"
    input_file.write_text(json.dumps(payload))
    run_mock = mocker.patch.object(pr_review_threads, "run_gh")

    result = runner.invoke(
        app,
        [
            "reply-and-resolve-batch",
            "--pr",
            "17",
            "--input-file",
            str(input_file),
            "--snapshot-file",
            str(snapshot_file),
            "--state-file",
            str(state_file),
            "--github",
            "acme/widgets",
        ],
    )

    assert result.exit_code != 0
    run_mock.assert_not_called()


def write_two_input_cycle(directory: Path) -> tuple[Path, Path]:
    """Write a complete two-input snapshot and cycle for batch ordering tests."""
    first = canonical_input()
    second = first.model_copy(
        update={
            "input_id": "github:review-comment:43",
            "provider_ids": ProviderInputIdentity(object_id="43", reply_target_id="43", resolution_target_id="T2"),
            "stable_reference": "https://github.com/acme/widgets/pull/17#discussion_r43",
            "thread_id": "T2",
        }
    )
    original_snapshot = canonical_snapshot()
    fingerprint = fingerprint_for(original_snapshot, [first, second])
    snapshot = original_snapshot.model_copy(
        update={"review_inputs": [first, second], "snapshot_fingerprint": fingerprint}
    )
    cycle = ready_cycle()
    first_assessment = cycle.assessments[0]
    second_assessment = ReviewAssessment.model_validate({
        **first_assessment.model_dump(),
        "input_id": second.input_id,
        "cluster_id": "cluster-2",
    })
    first_cluster = cycle.clusters[0]
    second_cluster = ReviewCluster.model_validate({
        **first_cluster.model_dump(),
        "cluster_id": "cluster-2",
        "input_ids": [second.input_id],
    })
    cycle = cycle.model_copy(
        update={
            "snapshot_fingerprint": fingerprint,
            "assessed_inputs": {first.input_id: first, second.input_id: second},
            "input_census": [first.input_id, second.input_id],
            "assessments": [first_assessment, second_assessment],
            "clusters": [first_cluster, second_cluster],
            "recheck_snapshot_fingerprint": fingerprint,
            "communication_states": {first.input_id: "pending", second.input_id: "pending"},
            "resolution_states": {first.input_id: "open", second.input_id: "open"},
            "implementation_states": {first.input_id: "completed", second.input_id: "completed"},
        }
    )
    snapshot_path = directory / "snapshot-two.json"
    state_path = directory / "state-two.json"
    snapshot_path.write_text(snapshot.model_dump_json())
    state_path.write_text(cycle.model_dump_json())
    return snapshot_path, state_path


def test_batch_stops_after_first_failed_action(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_two_input_cycle(tmp_path)
    mock_live_snapshot(snapshot_file, mocker)
    input_file = tmp_path / "batch.json"
    input_file.write_text(
        json.dumps([
            {"input_id": canonical_input().input_id, "body": "first"},
            {"input_id": "github:review-comment:43", "body": "second"},
        ])
    )
    run_mock = mocker.patch.object(
        pr_review_threads,
        "run_gh",
        side_effect=[json.dumps({"id": 11}), json.dumps({"errors": [{"message": "denied"}]})],
    )

    result = runner.invoke(
        app,
        [
            "reply-and-resolve-batch",
            "--pr",
            "17",
            "--input-file",
            str(input_file),
            "--snapshot-file",
            str(snapshot_file),
            "--state-file",
            str(state_file),
            "--github",
            "acme/widgets",
        ],
    )

    assert result.exit_code != 0
    assert run_mock.call_count == 2


def test_batch_preflights_every_resolution_before_first_reply(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot_file, state_file = write_two_input_cycle(tmp_path)
    snapshot = pr_review_threads.load_snapshot(snapshot_file)
    second = snapshot.review_inputs[1].model_copy(
        update={"capabilities": snapshot.review_inputs[1].capabilities.model_copy(update={"can_resolve": False})}
    )
    inputs = [snapshot.review_inputs[0], second]
    fingerprint = fingerprint_for(snapshot, inputs)
    snapshot_file.write_text(
        snapshot.model_copy(update={"review_inputs": inputs, "snapshot_fingerprint": fingerprint}).model_dump_json()
    )
    cycle = pr_review_threads.load_cycle(state_file).model_copy(
        update={
            "snapshot_fingerprint": fingerprint,
            "recheck_snapshot_fingerprint": fingerprint,
            "assessed_inputs": {item.input_id: item for item in inputs},
        }
    )
    state_file.write_text(cycle.model_dump_json())
    mock_live_snapshot(snapshot_file, mocker)
    input_file = tmp_path / "batch-preflight.json"
    input_file.write_text(
        json.dumps([
            {"input_id": canonical_input().input_id, "body": "first"},
            {"input_id": second.input_id, "body": "second"},
        ])
    )
    run_mock = mocker.patch.object(pr_review_threads, "run_gh")

    result = runner.invoke(
        app,
        [
            "reply-and-resolve-batch",
            "--pr",
            "17",
            "--input-file",
            str(input_file),
            "--snapshot-file",
            str(snapshot_file),
            "--state-file",
            str(state_file),
            "--github",
            "acme/widgets",
        ],
    )

    assert result.exit_code != 0
    run_mock.assert_not_called()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
