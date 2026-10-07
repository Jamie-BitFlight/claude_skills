"""Contract tests for GitHubTaskProvider plan-status aggregation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sam_schema.core.backends.github_task import GitHubTaskProvider


def _task_node(task_id: str, status: str) -> dict[str, object]:
    return {
        "number": int(task_id.removeprefix("T")),
        "title": f"[{task_id}] Task {task_id}",
        "body": "",
        "labels": [{"name": "sam:task"}, {"name": f"sam:{status}"}],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


@pytest.mark.parametrize(
    ("statuses", "expected_completion_pct"),
    [(["complete", "deferred", "skipped"], 100.0), (["complete", "deferred", "skipped", "failed"], 75.0)],
)
def test_get_plan_status_successful_terminal_completion(
    monkeypatch: pytest.MonkeyPatch, statuses: list[str], expected_completion_pct: float
) -> None:
    """GitHub status summaries include successful terminal statuses only."""
    provider = GitHubTaskProvider(MagicMock(), MagicMock())
    plan_node = {
        "title": "SAM Plan: plan",
        "body": "## Goal\n\nGoal\n\n<!-- sam-plan-slug: plan -->",
        "labels": [{"name": "sam:plan"}],
    }
    task_nodes = [_task_node(f"T{index:02d}", status) for index, status in enumerate(statuses, start=1)]
    monkeypatch.setattr(provider, "_fetch_plan_node", lambda plan_id: plan_node)
    monkeypatch.setattr(provider, "_fetch_task_nodes", lambda plan_id: task_nodes)

    status = provider.get_plan_status("1")

    assert status["completion_pct"] == expected_completion_pct
