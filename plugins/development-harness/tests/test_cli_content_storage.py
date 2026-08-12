from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentKind, ContentQuery, ContentRef
from dh_core import operations
from sam_schema.core.backends.content import ContentTaskProvider


@pytest.fixture
def content_provider() -> InMemoryBackend:
    provider = InMemoryBackend()
    set_config(BacklogConfig(backend=provider))
    return provider


def _dispatch_plan(milestone: int = 10) -> dict[str, Any]:
    return {
        "milestone": {"number": milestone, "title": "Provider plan", "integration-branch": "main"},
        "waves": [{"wave": 1, "items": [{"title": "Issue", "issue": 101, "priority": "P1"}]}],
    }


def test_issue_less_plan_uses_configured_content_without_local_warning(content_provider: InMemoryBackend) -> None:
    result = operations.create_plan(
        ContentTaskProvider(content_provider),
        slug="provider-plan",
        goal="Persist through configured content",
        tasks=[{"id": "T1", "title": "Task", "status": "not-started"}],
    )

    assert result.warnings is None
    assert content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=result.plan_id)).content


def test_artifact_operations_use_configured_content_provider(content_provider: InMemoryBackend) -> None:
    registered = operations.artifact_register(42, "research", "report", content="# Report")
    listed = operations.artifact_list(42, "research")
    read = operations.artifact_read(42, "research", "report")

    assert registered["content_stored"] is True
    assert listed["count"] == 1
    assert read["content"] == "# Report"
    assert (
        content_provider.get_content(
            ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="42", artifact_type="research", name="report")
        ).content
        == "# Report"
    )


def test_dispatch_operations_use_dedicated_configured_content(content_provider: InMemoryBackend) -> None:
    created = operations.dispatch_create_plan(10, _dispatch_plan())
    read = operations.dispatch_read_plan(10)
    validated = operations.dispatch_validate_plan(10)

    assert created["wave_count"] == 1
    assert read["plan"]["milestone"]["number"] == 10
    assert validated["is_valid"] is True
    records = content_provider.list_content(ContentQuery(kind=ContentKind.DISPATCH_PLAN))
    assert len(records) == 1
    assert json.loads(records[0].content)["milestone"]["number"] == 10


def test_dh_core_has_no_legacy_content_storage_reachability() -> None:
    source = Path(operations.__file__).read_text(encoding="utf-8")
    imports = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imports & {
        "backlog_core.artifact_migration",
        "backlog_core.artifact_provider",
        "backlog_core.artifact_provider_local",
    }
    assert "artifact_migrate" not in operations.__all__
    assert "_ds.read_dispatch_plan" not in source
    assert "_ds.write_dispatch_plan" not in source
    assert "_ds.dispatch_plan_path" not in source
