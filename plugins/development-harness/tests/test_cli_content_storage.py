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
from pydantic import ValidationError
from ruamel.yaml import YAMLError
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.models import Task, TaskStatus


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


class _FailingArtifactContentWriter(InMemoryBackend):
    def put_content(self, request: ContentWrite) -> ContentRecord:
        if request.reference.kind == ContentKind.ARTIFACT_CONTENT:
            raise ContentUnavailableError("artifact content storage unavailable")
        return super().put_content(request)


class _DispatchRaceBackend(InMemoryBackend):
    def __init__(self) -> None:
        super().__init__()
        self.writes: list[ContentWrite] = []
        self.race: str | None = None

    def put_content(self, request: ContentWrite) -> ContentRecord:
        self.writes.append(request)
        if self.race == "create" and request.create_only:
            self.race = None
            super().put_content(ContentWrite(reference=request.reference, content="concurrent", create_only=True))
        elif self.race == "overwrite" and request.expected_revision:
            self.race = None
            super().put_content(
                ContentWrite(
                    reference=request.reference, content="concurrent", expected_revision=request.expected_revision
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


def test_content_task_provider_hydrates_legacy_yaml_and_rewrites_mutation_as_compact_json() -> None:
    provider = InMemoryBackend()
    reference = ContentRef(kind=ContentKind.PLAN, name="Plegacy123")
    provider.put_content(
        ContentWrite(
            reference=reference,
            content=(
                "plan-id: Plegacy123\n"
                "feature: legacy-provider-plan\n"
                'version: "1.0"\n'
                "description: Plan created by the prior Gist task layer\n"
                "goal: Preserve provider-backed plans across upgrades\n"
                'issue: "2882"\n'
                "tasks:\n"
                "  - id: T1\n"
                "    title: Preserve legacy content\n"
                "    status: NOT STARTED\n"
            ),
        )
    )

    task_provider = ContentTaskProvider(provider)

    assert [plan["plan_id"] for plan in task_provider.list_plans()] == ["Plegacy123"]
    assert task_provider.read_plan("Plegacy123")["tasks"][0]["status"] == TaskStatus.NOT_STARTED

    task_provider.update_task_status("Plegacy123", "T1", TaskStatus.IN_PROGRESS)

    persisted = provider.get_content(reference).content
    assert json.loads(persisted)["tasks"][0]["status"] == TaskStatus.IN_PROGRESS
    assert "\n" not in persisted


def test_content_task_provider_hydrates_existing_json() -> None:
    provider = InMemoryBackend()
    created = ContentTaskProvider(provider).create_plan(
        "json-provider-plan", "Retain JSON hydration", [Task(id="T1", title="Keep JSON", status=TaskStatus.NOT_STARTED)]
    )

    hydrated = ContentTaskProvider(provider)

    assert hydrated.read_plan(created["plan_id"])["goal"] == "Retain JSON hydration"


def test_content_task_provider_rejects_malformed_json_without_yaml_fallback() -> None:
    provider = InMemoryBackend()
    provider.put_content(
        ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="Pmalformed"), content='{"plan_id":"Pmalformed"}')
    )

    with pytest.raises(ValidationError):
        ContentTaskProvider(provider)


def test_content_task_provider_rejects_malformed_legacy_yaml() -> None:
    provider = InMemoryBackend()
    provider.put_content(
        ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="Pmalformed"), content="plan-id: [")
    )

    with pytest.raises(YAMLError):
        ContentTaskProvider(provider)


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
        operations.artifact_register(42, "research", "report", content="# Report")

    assert provider.put_content.call_args.args[0].reference == ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace="42", artifact_type="research", name="report"
    )


def test_artifact_register_rejects_empty_content_before_provider_mutation() -> None:
    provider = MagicMock(spec=ContentProvider)
    set_config(BacklogConfig(backend=provider))

    result = operations.artifact_register(42, "research", "report", content="")

    assert result["error"] == "Artifact content must not be empty."
    provider.get_content.assert_not_called()
    provider.put_content.assert_not_called()


def test_artifact_register_retries_conflicting_manifest_write() -> None:
    provider = _ConcurrentManifestWriter()
    set_config(BacklogConfig(backend=provider))
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="42", name="manifest")
    provider.put_content(ContentWrite(reference=reference, content=ArtifactManifest(issue_number=42).model_dump_json()))
    provider.inject_conflict = True

    result = operations.artifact_register(42, "architect", "primary.md", content="# Primary")

    manifest = ArtifactManifest.model_validate_json(provider.get_content(reference).content)
    assert result["registered"] is True
    assert provider.concurrent_write is not None
    assert {(entry.artifact_type, entry.artifact_id) for entry in manifest.artifacts} == {
        (ArtifactType.ARCHITECT, "primary.md"),
        (ArtifactType.RESEARCH, "concurrent.md"),
    }


def test_artifact_register_content_failure_preserves_prior_readable_artifact() -> None:
    provider = _FailingArtifactContentWriter()
    set_config(BacklogConfig(backend=provider))
    manifest_ref = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="42", name="manifest")
    provider.put_content(
        ContentWrite(
            reference=manifest_ref,
            content=ArtifactManifest(
                issue_number=42, artifacts=[ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="prior.md")]
            ).model_dump_json(),
        )
    )
    prior_ref = ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace="42", artifact_type="research", name="prior.md")
    InMemoryBackend.put_content(provider, ContentWrite(reference=prior_ref, content="# Prior"))

    with pytest.raises(ContentUnavailableError, match="artifact content storage unavailable"):
        operations.artifact_register(42, "research", "next.md", content="# Next")

    manifest = ArtifactManifest.model_validate_json(provider.get_content(manifest_ref).content)
    assert [entry.artifact_id for entry in manifest.artifacts] == ["prior.md"]
    assert operations.artifact_read(42, "research")["content"] == "# Prior"


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


def test_dispatch_create_uses_observed_write_conditions_and_rejects_races() -> None:
    provider = _DispatchRaceBackend()
    set_config(BacklogConfig(backend=provider))

    provider.race = "create"
    created = operations.dispatch_create_plan(10, _dispatch_plan())

    assert created["error"] == "Content already exists"
    assert provider.get_content(operations._dispatch_reference(10)).content == "concurrent"
    assert provider.writes[0].create_only is True

    provider.writes.clear()
    current = provider.get_content(operations._dispatch_reference(10))
    provider.race = "overwrite"
    replaced = operations.dispatch_create_plan(10, _dispatch_plan(), overwrite=True)

    assert replaced["error"] == "Content revision no longer matches"
    assert provider.get_content(operations._dispatch_reference(10)).content == "concurrent"
    assert provider.writes[0].expected_revision == current.revision
    assert provider.writes[0].create_only is False


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
