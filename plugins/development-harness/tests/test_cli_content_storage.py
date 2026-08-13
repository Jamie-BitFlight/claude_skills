from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from backlog_core.artifact_registry import ArtifactRegistry
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig, ContentProvider
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import (
    ArtifactEntry,
    ArtifactManifest,
    ArtifactType,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)
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


class _ConcurrentManifestWriter(InMemoryBackend):
    def __init__(self) -> None:
        super().__init__()
        self.inject_conflict = False
        self.concurrent_write: ContentRecord | None = None

    def put_content(self, request: ContentWrite) -> ContentRecord:
        if self.inject_conflict and request.reference.kind == ContentKind.ARTIFACT_MANIFEST:
            self.inject_conflict = False
            record = self.get_content(request.reference)
            manifest = ArtifactManifest.model_validate_json(record.content)
            competing_manifest = ArtifactRegistry().register(
                manifest, ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="concurrent.md")
            )
            self.concurrent_write = super().put_content(
                ContentWrite(
                    reference=request.reference,
                    content=competing_manifest.model_dump_json(),
                    expected_revision=record.revision,
                )
            )
        return super().put_content(request)


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


def test_artifact_register_does_not_replace_unavailable_manifest() -> None:
    provider = MagicMock(spec=ContentProvider)
    provider.get_content.side_effect = ContentUnavailableError("offline cache miss")
    set_config(BacklogConfig(backend=provider))

    with pytest.raises(ContentUnavailableError, match="offline cache miss"):
        operations.artifact_register(42, "research", "report")

    provider.put_content.assert_not_called()


def test_artifact_register_retries_conflicting_manifest_write() -> None:
    provider = _ConcurrentManifestWriter()
    set_config(BacklogConfig(backend=provider))
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="42", name="manifest")
    provider.put_content(ContentWrite(reference=reference, content=ArtifactManifest(issue_number=42).model_dump_json()))
    provider.inject_conflict = True

    result = operations.artifact_register(42, "architect", "primary.md")

    manifest = ArtifactManifest.model_validate_json(provider.get_content(reference).content)
    assert result["registered"] is True
    assert provider.concurrent_write is not None
    assert {(entry.artifact_type, entry.artifact_id) for entry in manifest.artifacts} == {
        (ArtifactType.ARCHITECT, "primary.md"),
        (ArtifactType.RESEARCH, "concurrent.md"),
    }


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


def test_dispatch_create_does_not_overwrite_when_existing_plan_is_unavailable() -> None:
    provider = MagicMock(spec=ContentProvider)
    provider.get_content.side_effect = ContentUnavailableError("offline cache miss")
    set_config(BacklogConfig(backend=provider))

    with pytest.raises(ContentUnavailableError, match="offline cache miss"):
        operations.dispatch_create_plan(10, _dispatch_plan())

    provider.put_content.assert_not_called()


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
