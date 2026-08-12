from __future__ import annotations

import ast
import inspect
import json
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from backlog_core.backend_types import ContentProvider
from backlog_core.backends.bd_runner import BdInvocationError, JsonValue
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import (
    ContentConflictError,
    ContentKind,
    ContentQuery,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)


class _BeadsKvRunner:
    def __init__(self, *, fail_sets: bool = False) -> None:
        self.values: dict[str, str] = {}
        self.calls: list[tuple[str, ...]] = []
        self.fail_sets = fail_sets

    def run_json(self, argv: Sequence[str]) -> JsonValue:
        self.calls.append(tuple(argv))
        match list(argv):
            case ["kv", "list"]:
                return {**self.values, "schema_version": 1}
            case ["kv", "get", key]:
                value = self.values.get(key)
                if value is None:
                    missing = {"found": False, "key": key, "schema_version": 1, "value": ""}
                    raise BdInvocationError(
                        "missing key",
                        argv=["bd", *argv, "--json"],
                        returncode=1,
                        stdout=json.dumps(missing, separators=(",", ":")),
                        stderr="",
                    )
                return {"found": True, "key": key, "schema_version": 1, "value": value}
            case unreachable:
                raise AssertionError(f"unexpected bd JSON command: {unreachable!r}")

    def run_text(self, argv: Sequence[str]) -> str:
        self.calls.append(tuple(argv))
        match list(argv):
            case ["kv", "set", key, value]:
                if self.fail_sets:
                    raise BdInvocationError(
                        "write failed", argv=["bd", *argv], returncode=2, stdout="", stderr="write failed"
                    )
                self.values[key] = value
                return ""
            case unreachable:
                raise AssertionError(f"unexpected bd text command: {unreachable!r}")

    def is_available(self) -> bool:
        return True


@pytest.fixture(params=("memory", "sqlite", "beads"))
def local_provider(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ContentProvider]:
    match request.param:
        case "memory":
            yield InMemoryBackend()
        case "sqlite":
            backend = SQLiteBackend(str(tmp_path / "content.sqlite3"))
            yield backend
            backend._conn.close()
        case "beads":
            yield BeadsBackend(_BeadsKvRunner())
        case unreachable:
            raise AssertionError(f"unexpected backend: {unreachable!r}")


@pytest.mark.unit
def test_native_content_contract_when_identity_owner_and_revision_change(local_provider: ContentProvider) -> None:
    # Given: opaque plan and artifact identifiers whose values must not be interpreted.
    assert isinstance(local_provider, ContentProvider)
    plan_ref = ContentRef(kind=ContentKind.PLAN, name="plan://opaque/%E2%98%83")
    owners = ("owner:alpha/7", "owner:beta/9")
    artifact_refs = (
        ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace=owners[0], name="manifest"),
        ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace=owners[1], name="manifest"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace=owners[0], artifact_type="design", name="same/id"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace=owners[1], artifact_type="design", name="same/id"),
        ContentRef(kind=ContentKind.ARTIFACT_CONTENT, namespace=owners[0], artifact_type="test", name="same/id"),
    )

    # When: the plan is created, reassigned, and unlinked while artifacts share apparent paths.
    created = local_provider.put_content(ContentWrite(reference=plan_ref, content="v1", owner_reference=owners[0]))
    preserved = local_provider.put_content(
        ContentWrite(reference=plan_ref, content="v1.1", expected_revision=created.revision)
    )
    reassigned = local_provider.put_content(
        ContentWrite(reference=plan_ref, content="v2", owner_reference=owners[1], expected_revision=preserved.revision)
    )
    unlinked = local_provider.put_content(
        ContentWrite(reference=plan_ref, content="v3", owner_reference="", expected_revision=reassigned.revision)
    )
    for index, reference in enumerate(artifact_refs):
        local_provider.put_content(ContentWrite(reference=reference, content=f"artifact-{index}"))

    # Then: the logical plan identity is unchanged and every artifact identity remains isolated.
    assert created.reference == preserved.reference == reassigned.reference == unlinked.reference == plan_ref
    assert preserved.owner_reference == owners[0]
    assert unlinked.owner_reference == ""
    assert local_provider.get_content(plan_ref).content == "v3"
    assert [local_provider.get_content(ref).content for ref in artifact_refs] == [
        "artifact-0",
        "artifact-1",
        "artifact-2",
        "artifact-3",
        "artifact-4",
    ]
    assert local_provider.list_content(ContentQuery(kind=ContentKind.PLAN, owner_reference="")) == [unlinked]
    assert local_provider.list_content(
        ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, owner_reference=owners[0], offset=1, limit=1)
    ) == [local_provider.get_content(artifact_refs[4])]

    with pytest.raises(ContentConflictError):
        local_provider.put_content(
            ContentWrite(reference=plan_ref, content="stale", expected_revision=created.revision)
        )
    with pytest.raises(ContentUnavailableError):
        local_provider.get_content(ContentRef(kind=ContentKind.PLAN, name="missing/opaque"))


@pytest.mark.unit
def test_beads_content_when_native_kv_write_fails() -> None:
    # Given: a Beads runner whose native KV write fails.
    runner = _BeadsKvRunner(fail_sets=True)
    backend = BeadsBackend(runner)
    reference = ContentRef(kind=ContentKind.PLAN, name="native-kv-only")

    # When: logical content is written through the backend.
    with pytest.raises(ContentUnavailableError):
        backend.put_content(ContentWrite(reference=reference, content="content"))

    # Then: the backend surfaces unavailability and invoked only native KV commands.
    assert runner.calls
    assert all(command[:2] in {("kv", "get"), ("kv", "set")} for command in runner.calls)


@pytest.mark.unit
def test_local_content_backends_have_no_yaml_or_file_cache_import_boundary() -> None:
    modules = [sys.modules[backend.__module__] for backend in (InMemoryBackend, SQLiteBackend, BeadsBackend)]
    trees = [ast.parse(inspect.getsource(module)) for module in modules]
    imports = {
        alias.name
        for tree in trees
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    } | {node.module for tree in trees for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}

    assert not {name for name in imports if "file_cache" in name.casefold() or "yaml_io" in name.casefold()}
