from __future__ import annotations

import ast
import json
from collections.abc import Generator
from pathlib import Path

import pytest
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from typer.testing import CliRunner

import sam_schema.cli_active_task as cli_active_task
import sam_schema.sam_plan as sam_plan
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

    _invoke("active-task", "set", "--address", f"{plan_id}/T1", "--plan-dir", str(ignored_directory))
    assert (
        _invoke("active-task", "update", "--set-fields-json", '{"title":"Updated through active task"}')["updated"]
        is True
    )

    task = _invoke("plan", "read", "--address", f"{plan_id}/T1")["task"]
    assert task["title"] == "Updated through active task"
    assert not list(ignored_directory.iterdir())


def test_cli_modules_do_not_import_legacy_task_storage() -> None:
    for module in (sam_plan, cli_active_task):
        source_path = module.__file__
        assert source_path is not None
        imports = {
            node.module
            for node in ast.walk(ast.parse(Path(source_path).read_text(encoding="utf-8")))
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "sam_schema.core.task_config" not in imports
