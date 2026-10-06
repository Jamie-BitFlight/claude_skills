from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from typer.testing import CliRunner

from sam_schema.cli import app
from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend
from sam_schema.core.context_config import ContextConfig, reset_context_config, set_context_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def _configured_content_backend() -> Generator[InMemoryBackend, None, None]:
    backend = InMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    set_context_config(ContextConfig(backend=InMemoryContextBackend()))
    yield backend
    reset_config()
    reset_context_config()


def _invoke(*args: str):
    result = runner.invoke(app, list(args), env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""
    assert ": " not in result.stdout
    assert ", " not in result.stdout
    return json.loads(result.stdout)


def test_plan_and_active_task_update_use_configured_content(tmp_path: Path) -> None:
    ignored_directory = tmp_path / "ignored"
    ignored_directory.mkdir()

    created = _invoke(
        "plan",
        "create",
        "--slug",
        "content-route",
        "--goal",
        "Persist through configured content",
        "--task-id",
        "T1",
        "--task-title",
        "Initial title",
        "--plan-dir",
        str(ignored_directory),
    )
    plan_id = str(created["plan_id"])

    assert _invoke("plan", "list", "--plan-dir", str(ignored_directory))["count"] == 1
    assert _invoke("plan", "read", "--address", plan_id)["plan"]["goal"] == "Persist through configured content"
    assert _invoke("plan", "update", "--plan-address", plan_id, "--goal", "Updated goal")["updated"] is True

    _invoke(
        "active-task",
        "set",
        "--address",
        f"{plan_id}/T1",
        "--plan-dir",
        str(ignored_directory),
        "--session-id",
        "test-session-content-route",
    )
    assert (
        _invoke(
            "active-task",
            "update",
            "--set-fields-json",
            '{"title":"Updated through active task"}',
            "--session-id",
            "test-session-content-route",
        )["updated"]
        is True
    )

    task = _invoke("plan", "read", "--address", f"{plan_id}/T1")["task"]
    assert task["title"] == "Updated through active task"
    assert not list(ignored_directory.iterdir())
