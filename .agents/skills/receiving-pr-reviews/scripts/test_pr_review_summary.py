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
"""Tests for bounded metadata-only review dashboards."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.core import TyperOption
from typer.main import get_group

import pr_review_threads
from pr_review_models import Author, CommentNode, ProviderApprovalState, ProviderSystemEvent, UnresolvedThread
from pr_review_output import action_view, summarize
from pr_review_state_models import calculate_snapshot_fingerprint
from pr_review_threads import app
from review_test_fixtures import canonical_input, canonical_snapshot
from review_test_gh_fixtures import (
    _default_github_detection as _default_github_detection,
    _fetch_result,
    _review,
    _thread_with_comment,
    runner,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def nested_keys(value: object) -> set[str]:
    """Return every mapping key in a serialized result."""
    if isinstance(value, dict):
        return set(value).union(*(nested_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(nested_keys(item) for item in value))
    return set()


def test_fetch_summary_is_metadata_only_and_body_length_independent(mocker: MockerFixture) -> None:
    def summary_for_bodies(opening_body: str, reply_body: str) -> tuple[str, dict[str, object]]:
        thread = UnresolvedThread(
            id="T1",
            path="x.py",
            comments=[
                CommentNode(
                    databaseId=42, body=opening_body, line=10, originalLine=10, author=Author(login="reviewer")
                ),
                CommentNode(databaseId=43, body=reply_body, line=10, originalLine=10, author=Author(login="reviewer")),
            ],
            comments_truncated=False,
        )
        mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result(unresolved=[thread]))
        result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])
        assert result.exit_code == 0, result.output
        return result.output, json.loads(result.output)

    short_output, short_summary = summary_for_bodies("BODY_A", "REPLY_A")
    long_output, long_summary = summary_for_bodies("\n".join(["BODY_A"] * 100), "\n".join(["REPLY_A"] * 100))

    assert short_summary == long_summary
    assert len(short_output) == len(long_output)
    assert nested_keys(short_summary).isdisjoint({
        "body",
        "replies",
        "patch",
        "review_inputs",
        "assessments",
        "clusters",
        "provider_metadata",
    })


def test_fetch_summary_contains_only_next_action_dashboard_fields(mocker: MockerFixture) -> None:
    state = _fetch_result(
        unresolved=[_thread_with_comment(body="fix this")],
        unresponded_reviews=[_review("R1", body="ship it", submitted_at=datetime(2026, 1, 1, tzinfo=UTC))],
        blockers=["draft: reviewers are not requested until the PR is marked ready for review"],
        codex_approved=True,
        mergeable="CONFLICTING",
        merge_state_status="DIRTY",
    )
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=state)

    result = runner.invoke(app, ["fetch", "--pr", "3208", "--summary"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert set(data) == {
        "pr",
        "provider",
        "snapshot_complete",
        "cycle_state",
        "unresolved_code_thread_count",
        "unanswered_input_count",
        "approval_count",
        "rejection_count",
        "codex_approved",
        "provider_approved",
        "approvals_required",
        "approvals_left",
        "assigned_reviewer_count",
        "requested_reviewer_count",
        "is_draft",
        "mergeable",
        "merge_state_status",
        "has_conflicts",
        "checks_state",
        "new_input",
    }
    assert data["pr"] == 3208
    assert data["unresolved_code_thread_count"] == 1
    assert data["unanswered_input_count"] == 1
    assert data["mergeable"] == "CONFLICTING"
    assert data["has_conflicts"] is True
    assert data["codex_approved"] is True
    assert data["new_input"] is True


def test_summary_aggregates_input_kinds_and_unanswered_locations() -> None:
    snapshot = canonical_snapshot()
    inline = canonical_input()
    top_level = inline.model_copy(
        update={
            "input_id": "github:issue-comment:43",
            "provider_ids": inline.provider_ids.model_copy(
                update={"object_id": "43", "reply_target_id": None, "resolution_target_id": None}
            ),
            "source_kind": "issue_comment",
            "location": "top_level",
            "kinds": {"comment", "question"},
            "stable_reference": "https://github.com/acme/widgets/pull/17#issuecomment-43",
            "path": None,
            "line": None,
            "capabilities": inline.capabilities.model_copy(update={"can_reply": False, "can_resolve": False}),
            "thread_id": None,
        }
    )
    rejection = top_level.model_copy(
        update={
            "input_id": "github:review:44",
            "provider_ids": top_level.provider_ids.model_copy(update={"object_id": "44"}),
            "source_kind": "review",
            "kinds": {"rejection"},
            "stable_reference": "https://github.com/acme/widgets/pull/17#pullrequestreview-44",
        }
    )
    inputs = [inline, top_level, rejection]
    fingerprint = calculate_snapshot_fingerprint(
        snapshot.target,
        snapshot.head_revision,
        inputs,
        snapshot.completeness,
        revision_at=snapshot.revision_at,
        reviewability=snapshot.reviewability,
    )
    snapshot = snapshot.model_copy(
        update={"review_inputs": inputs, "snapshot_fingerprint": fingerprint, "outstanding_input_count": len(inputs)}
    )

    dashboard = summarize(snapshot, pr=17)

    assert dashboard.unresolved_code_thread_count == 1
    assert dashboard.unanswered_input_count == 2
    assert dashboard.approval_count == 0
    assert dashboard.rejection_count == 1
    assert dashboard.new_input is True


def test_summary_projects_reviewer_approval_and_check_metadata() -> None:
    snapshot = canonical_snapshot()
    metadata = snapshot.provider_metadata.model_copy(
        update={
            "approval_state": ProviderApprovalState(
                approved=False, approvals_required=2, approvals_left=1, approval_rules_left=[]
            ),
            "assigned_reviewers": ["reviewer-one"],
            "requested_reviewers": ["reviewer-two"],
            "checks_state": "PENDING",
        }
    )

    dashboard = summarize(snapshot.model_copy(update={"provider_metadata": metadata}), pr=17)

    assert dashboard.provider_approved is False
    assert dashboard.approvals_required == 2
    assert dashboard.approvals_left == 1
    assert dashboard.assigned_reviewer_count == 1
    assert dashboard.requested_reviewer_count == 1
    assert dashboard.checks_state == "PENDING"


def test_fetch_without_summary_preserves_complete_action_evidence(mocker: MockerFixture) -> None:
    snapshot = canonical_snapshot()
    item = snapshot.review_inputs[0].model_copy(update={"body": "complete action evidence"})
    provider = mocker.Mock()
    provider.snapshot.return_value = snapshot.model_copy(update={"review_inputs": [item]})
    mocker.patch.object(pr_review_threads, "review_provider_for_target", return_value=provider)

    result = runner.invoke(app, ["fetch", "--pr", "3208"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert [item["body"] for item in data["actionable_inputs"]] == ["complete action evidence"]
    assert "review_inputs" not in data
    assert "unresolved" not in data


def test_fetch_persists_history_without_rendering_it(tmp_path: Path, mocker: MockerFixture) -> None:
    def snapshot_with_history(history_body: str):
        snapshot = canonical_snapshot()
        current = snapshot.review_inputs[0].model_copy(update={"body": "current action"})
        resolved = current.model_copy(
            update={
                "input_id": "github:review-comment:43",
                "provider_ids": current.provider_ids.model_copy(update={"object_id": "43"}),
                "body": history_body,
                "provider_state": "resolved",
            }
        )
        addressed = current.model_copy(
            update={
                "input_id": "github:review-comment:45",
                "provider_ids": current.provider_ids.model_copy(update={"object_id": "45"}),
                "body": history_body,
            }
        )
        metadata = snapshot.provider_metadata.model_copy(
            update={
                "system_notes": [ProviderSystemEvent(id="system-1", body=history_body, created_at=snapshot.revision_at)]
            }
        )
        return snapshot.model_copy(
            update={
                "review_inputs": [current, resolved, addressed],
                "provider_metadata": metadata,
                "communicated_input_ids": {addressed.input_id},
            }
        )

    provider = mocker.Mock()
    provider.snapshot.side_effect = [
        snapshot_with_history("HISTORICAL"),
        snapshot_with_history("\n".join(["HISTORICAL"] * 500)),
    ]
    mocker.patch.object(pr_review_threads, "review_provider_for_target", return_value=provider)
    first_snapshot = tmp_path / "first-snapshot.json"
    second_snapshot = tmp_path / "second-snapshot.json"

    first = runner.invoke(app, ["fetch", "--pr", "3208", "--snapshot-file", str(first_snapshot)])
    second = runner.invoke(app, ["fetch", "--pr", "3208", "--snapshot-file", str(second_snapshot)])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert first.output == second.output
    assert [item["body"] for item in json.loads(first.output)["actionable_inputs"]] == ["current action"]
    assert "HISTORICAL" not in first.output
    assert "HISTORICAL" in first_snapshot.read_text(encoding="utf-8")
    assert second_snapshot.stat().st_size > first_snapshot.stat().st_size


@pytest.mark.parametrize(
    ("update", "communicated"),
    [({"direction": "outbound"}, False), ({"provider_state": "resolved"}, False), ({}, True)],
    ids=["outbound", "resolved", "addressed"],
)
def test_action_view_excludes_non_immediate_inputs(update: dict[str, str], communicated: bool) -> None:
    snapshot = canonical_snapshot()
    item = snapshot.review_inputs[0].model_copy(update={**update, "body": "HISTORICAL"})
    snapshot = snapshot.model_copy(
        update={"review_inputs": [item], "communicated_input_ids": {item.input_id} if communicated else set()}
    )

    rendered = action_view(snapshot, pr=17).model_dump_json()

    assert json.loads(rendered)["actionable_inputs"] == []
    assert "HISTORICAL" not in rendered


def test_action_view_keeps_an_open_stale_input_for_assessment() -> None:
    """A stale location remains actionable until provider evidence closes or addresses it."""
    snapshot = canonical_snapshot()
    stale = snapshot.review_inputs[0].model_copy(update={"revision_relation": "stale", "body": "STALE-OPEN-ACTION"})

    rendered = action_view(snapshot.model_copy(update={"review_inputs": [stale]}), pr=17).model_dump_json()

    data = json.loads(rendered)
    assert data["dashboard"]["unresolved_code_thread_count"] == 1
    assert [item["body"] for item in data["actionable_inputs"]] == ["STALE-OPEN-ACTION"]
    assert data["actionable_inputs"][0]["revision_relation"] == "stale"


def test_legacy_python_projection_helpers_remain_available() -> None:
    """Projection changes retain the established helper surface for Python consumers."""
    from pr_review_models import BoardEntry, CommentSummary, ReviewSummary, ThreadSummary
    from pr_review_output import board_entry, summarize_review, summarize_thread, truncate_body

    assert BoardEntry is not None
    assert CommentSummary is not None
    assert ReviewSummary is not None
    assert ThreadSummary is not None
    assert callable(board_entry)
    assert callable(summarize_review)
    assert callable(summarize_thread)
    assert truncate_body("complete", None) == "complete"


def test_fetch_rejects_one_snapshot_file_for_multiple_targets(tmp_path: Path, mocker: MockerFixture) -> None:
    selected = mocker.patch.object(pr_review_threads, "review_provider_for_target")

    result = runner.invoke(app, ["fetch", "--pr", "41,42", "--snapshot-file", str(tmp_path / "snapshot.json")])

    assert result.exit_code != 0
    assert "snapshot-file requires exactly one PR or MR" in result.output
    selected.assert_not_called()


def test_watch_persists_complete_history_without_rendering_it(tmp_path: Path, mocker: MockerFixture) -> None:
    snapshot = canonical_snapshot()
    current = snapshot.review_inputs[0].model_copy(update={"body": "current action"})
    resolved = current.model_copy(
        update={
            "input_id": "github:review-comment:43",
            "provider_ids": current.provider_ids.model_copy(update={"object_id": "43"}),
            "body": "HISTORICAL",
            "provider_state": "resolved",
        }
    )
    provider = mocker.Mock()
    stale = current.model_copy(
        update={
            "input_id": "github:review-comment:44",
            "provider_ids": current.provider_ids.model_copy(update={"object_id": "44"}),
            "body": "STALE-OPEN-ACTION",
            "revision_relation": "stale",
        }
    )
    provider.snapshot.return_value = snapshot.model_copy(
        update={
            "target": snapshot.target.model_copy(update={"number": 3208}),
            "review_inputs": [current, resolved, stale],
        }
    )
    mocker.patch.object(pr_review_threads, "review_provider_for_target", return_value=provider)
    snapshot_file = tmp_path / "watched-snapshot.json"

    result = runner.invoke(
        app,
        [
            "watch",
            "--pr",
            "3208",
            "--github",
            "acme/widgets",
            "--timeout-seconds",
            "0",
            "--snapshot-file",
            str(snapshot_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert [item["body"] for item in json.loads(result.output)["actionable_inputs"]] == [
        "current action",
        "STALE-OPEN-ACTION",
    ]
    assert "HISTORICAL" not in result.output
    assert "STALE-OPEN-ACTION" in result.output
    assert "HISTORICAL" in snapshot_file.read_text(encoding="utf-8")


def test_summary_help_describes_metadata_boundary_without_body_limit() -> None:
    fetch_command = get_group(app).commands["fetch"]
    options = {
        option: parameter.help
        for parameter in fetch_command.params
        if isinstance(parameter, TyperOption)
        for option in parameter.opts
    }

    assert options["--summary"] == "Print aggregate status JSON; omit for live action content."
    assert "--max-body" not in options


def test_watch_summary_reports_new_input_signal_without_full_state(mocker: MockerFixture) -> None:
    mocker.patch.object(pr_review_threads, "build_fetch_result", return_value=_fetch_result())

    result = runner.invoke(app, ["watch", "--pr", "3208", "--timeout-seconds", "0", "--summary"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["timed_out"] is True
    assert data["new_input"] is False
    assert data["pr"] == 3208
    assert "state" not in data


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
