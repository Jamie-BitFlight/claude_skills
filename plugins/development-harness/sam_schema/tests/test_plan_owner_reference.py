from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from backlog_core.backends.bd_runner import BdInvocationError
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import (
    ContentConflictError,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    UnsupportedCapabilityError,
)
from pydantic import ValidationError

from sam_schema.core.action_models import CreatePlanConfig, UpdatePlanConfig
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.exceptions import PlanNotFoundError
from sam_schema.core.models import Task, TaskStatus

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_create_accepts_opaque_owner_reference() -> None:
    config = CreatePlanConfig(slug="opaque", goal="route natively", owner_reference="bd-a1b2")

    assert config.owner_reference == "bd-a1b2"


def test_create_rejects_numeric_and_opaque_owners() -> None:
    with pytest.raises(ValidationError):
        CreatePlanConfig(slug="invalid", goal="reject ambiguity", issue=7, owner_reference="bd-a1b2")


def test_update_rejects_numeric_and_opaque_owners() -> None:
    with pytest.raises(ValidationError):
        UpdatePlanConfig(set_fields_json={"issue": 7}, owner_reference="bd-a1b2")


def test_dispatch_content_reference_rejects_sam_owner_namespace() -> None:
    # Given: dispatch content is project-level and has no owner namespace.
    # When: a caller attempts to associate it with a SAM plan owner.
    # Then: boundary validation rejects the mixed logical identity.
    with pytest.raises(ValidationError, match="plan namespace"):
        ContentRef(kind=ContentKind.DISPATCH_PLAN, namespace="#7", name="dispatch-milestone-7")


def test_content_task_provider_hydrates_owned_plan_after_fresh_provider() -> None:
    # Given: more than one bounded page of plans, including one opaque owner.
    content_provider = InMemoryBackend()
    first_provider = ContentTaskProvider(content_provider)
    plans = [first_provider.create_plan(f"persisted-{index}", "survives a fresh request", []) for index in range(101)]
    plan_id = plans[-1]["plan_id"]
    first_provider.set_owner(plan_id, "bd-a1b2")

    # When: a fresh task provider hydrates and updates the persisted plan.
    fresh_provider = ContentTaskProvider(content_provider)
    fresh_provider.update_plan_fields(plan_id, context="updated after hydration")

    # Then: the owned plan is discoverable and its update persists through the content provider.
    assert len(fresh_provider.list_plans()) == len(plans)
    assert fresh_provider.read_plan(plan_id)["context"] == "updated after hydration"
    persisted = content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan_id))
    assert persisted.owner_reference == "bd-a1b2"


def test_content_task_provider_persists_create_owner_in_one_write_and_hydrates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: an empty content provider whose writes are observable.
    content_provider = InMemoryBackend()
    writes: list[ContentWrite] = []
    original_put = content_provider.put_content

    def record_write(request: ContentWrite) -> ContentRecord:
        writes.append(request)
        return original_put(request)

    monkeypatch.setattr(content_provider, "put_content", record_write)
    first_provider = ContentTaskProvider(content_provider)

    # When: a plan is created with an opaque owner reference.
    plan = first_provider.create_plan("atomic-owner", "persist the owner", [], owner_reference="bd-a1b2")

    # Then: the sole write includes the owner and a fresh provider hydrates it.
    assert [write.owner_reference for write in writes] == ["bd-a1b2"]
    assert ContentTaskProvider(content_provider).read_plan(plan["plan_id"])["feature"] == "atomic-owner"
    assert (
        content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan["plan_id"])).owner_reference
        == "bd-a1b2"
    )


def test_content_task_provider_keeps_legacy_issue_owner_alias() -> None:
    # Given: a provider-backed plan created with the legacy numeric issue alias.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)

    # When: the plan is persisted.
    plan = provider.create_plan("legacy-owner", "preserve the numeric alias", [], issue=7)

    # Then: plan metadata and content ownership both retain the legacy representation.
    assert plan["issue"] == "7"
    assert content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan["plan_id"])).owner_reference == "#7"


def test_content_task_provider_ignores_dispatch_plan_when_hydrating_sam_plans() -> None:
    # Given: a provider that contains both a SAM plan and a dispatch plan.
    content_provider = InMemoryBackend()
    sam_provider = ContentTaskProvider(content_provider)
    sam_plan = sam_provider.create_plan("sam", "remain isolated", [])
    content_provider.put_content(
        ContentWrite(
            reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name="dispatch-milestone-10"),
            content='{"milestone":{"number":10}}',
        )
    )

    # When: a fresh SAM provider hydrates from the shared content provider.
    fresh_provider = ContentTaskProvider(content_provider)

    # Then: only SAM plans are decoded and dispatch content remains separately discoverable.
    assert [plan["plan_id"] for plan in fresh_provider.list_plans()] == [sam_plan["plan_id"]]
    assert [
        record.reference.name for record in content_provider.list_content(ContentQuery(kind=ContentKind.DISPATCH_PLAN))
    ] == ["dispatch-milestone-10"]


def test_content_task_provider_claim_uses_loaded_revision() -> None:
    # Given: two providers hydrated from the same persisted not-started task.
    content_provider = InMemoryBackend()
    creator = ContentTaskProvider(content_provider)
    plan = creator.create_plan(
        "atomic-claim", "claim once", [Task(id="T01", title="Claim once", status=TaskStatus.NOT_STARTED)]
    )
    plan_id = plan["plan_id"]
    creator.set_owner(plan_id, "bd-a1b2")
    first_provider = ContentTaskProvider(content_provider)
    second_provider = ContentTaskProvider(content_provider)

    # When: both stale snapshots attempt the same claim.
    assert first_provider.claim_task(plan_id, "T01") is True
    assert second_provider.claim_task(plan_id, "T01") is False

    # Then: the losing snapshot refreshes and the persisted plan has one claim.
    fresh_provider = ContentTaskProvider(content_provider)
    fresh_task = fresh_provider.read_task(plan_id, "T01")
    assert second_provider.read_task(plan_id, "T01") == fresh_task
    assert [task["status"] for task in fresh_provider.read_plan(plan_id)["tasks"]] == ["in-progress"]
    assert fresh_task["status"] == "in-progress"
    assert fresh_task["started"] is not None
    assert content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan_id)).owner_reference == "bd-a1b2"


def test_content_task_provider_removes_failed_create_from_local_state(mocker: MockerFixture) -> None:
    # Given: a content provider which rejects an otherwise valid create.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    writes: list[ContentWrite] = []

    def reject_create(request: ContentWrite) -> ContentRecord:
        writes.append(request)
        raise UnsupportedCapabilityError("create rejected")

    mocker.patch.object(content_provider, "put_content", side_effect=reject_create)

    # When: persistence fails after the in-memory plan has been created.
    with pytest.raises(UnsupportedCapabilityError, match="create rejected"):
        provider.create_plan("no-ghost", "must not remain locally", [], owner_reference="bd-a1b2")

    # Then: same-process reads cannot observe a plan the provider never accepted.
    assert [write.owner_reference for write in writes] == ["bd-a1b2"]
    assert content_provider.list_content(ContentQuery(kind=ContentKind.PLAN)) == []
    assert provider.list_plans() == []
    with pytest.raises(PlanNotFoundError):
        provider.read_plan(writes[0].reference.name)


def test_content_task_provider_restores_plan_when_write_and_refresh_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a persisted plan and an outage that rejects both its write and refresh.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    plan = provider.create_plan("restore-plan", "keep local state coherent", [])
    plan_id = plan["plan_id"]
    snapshot = provider.read_plan(plan_id)
    revision = provider._revisions[plan_id]

    def unavailable_write(_: ContentWrite) -> ContentRecord:
        raise ContentUnavailableError("write unavailable")

    def unavailable_refresh(_: ContentRef) -> ContentRecord:
        raise ContentUnavailableError("refresh unavailable")

    # When: a plan mutation cannot be persisted or authoritatively refreshed.
    with monkeypatch.context() as outage:
        outage.setattr(content_provider, "put_content", unavailable_write)
        outage.setattr(content_provider, "get_content", unavailable_refresh)
        with pytest.raises(ContentUnavailableError):
            provider.update_plan_fields(plan_id, context="rejected context")

    # Then: the rejected field and revision cannot leak into a later successful write.
    assert provider.read_plan(plan_id) == snapshot
    assert provider._revisions[plan_id] == revision
    provider.update_plan_fields(plan_id, set_fields={"description": "accepted description"})
    persisted = content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan_id))
    assert ContentTaskProvider(content_provider).read_plan(plan_id) == {
        **snapshot,
        "description": "accepted description",
    }
    assert persisted.revision != revision


def test_content_task_provider_restores_task_when_write_and_refresh_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a persisted task and an outage that rejects both its write and refresh.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    plan = provider.create_plan(
        "restore-task", "keep local task coherent", [Task(id="T01", title="Original", status=TaskStatus.NOT_STARTED)]
    )
    plan_id = plan["plan_id"]
    snapshot = provider.read_plan(plan_id)
    revision = provider._revisions[plan_id]

    def unavailable_write(_: ContentWrite) -> ContentRecord:
        raise ContentUnavailableError("write unavailable")

    def unavailable_refresh(_: ContentRef) -> ContentRecord:
        raise ContentUnavailableError("refresh unavailable")

    # When: a task mutation cannot be persisted or authoritatively refreshed.
    with monkeypatch.context() as outage:
        outage.setattr(content_provider, "put_content", unavailable_write)
        outage.setattr(content_provider, "get_content", unavailable_refresh)
        with pytest.raises(ContentUnavailableError):
            provider.update_task_fields(plan_id, "T01", {"title": "Rejected"})

    # Then: the rejected task field and revision cannot leak into a later successful write.
    assert provider.read_plan(plan_id) == snapshot
    assert provider._revisions[plan_id] == revision
    provider.update_task_status(plan_id, "T01", "in-progress")
    persisted = ContentTaskProvider(content_provider).read_plan(plan_id)
    assert persisted["tasks"][0]["title"] == "Original"
    assert persisted["tasks"][0]["status"] == "in-progress"


def test_content_task_provider_restores_plan_when_beads_workspace_is_unavailable(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    values: dict[str, str] = {}
    workspace_available = True
    runner = mocker.MagicMock()
    tmp_path.joinpath(".beads").mkdir()

    def run_json(argv: list[str]) -> object:
        if argv == ["where"]:
            if not workspace_available:
                raise BdInvocationError("where failed", argv=["bd", "where"], returncode=1, stdout="", stderr="")
            return {"path": str(tmp_path / ".beads")}
        if argv == ["kv", "list"]:
            return values
        if argv[:2] == ["kv", "get"]:
            if (value := values.get(argv[2])) is not None:
                return {"found": True, "value": value}
            raise BdInvocationError(
                "missing", argv=["bd", *argv], returncode=1, stdout='{"found":false,"value":""}', stderr=""
            )
        raise AssertionError(argv)

    def run_text(argv: list[str]) -> str:
        values[argv[2]] = argv[3]
        return ""

    runner.run_json.side_effect = run_json
    runner.run_text.side_effect = run_text
    provider = ContentTaskProvider(BeadsBackend(runner))
    plan = provider.create_plan("beads-outage", "rollback rejected state", [])
    snapshot = provider.read_plan(plan["plan_id"])
    workspace_available = False

    with pytest.raises(ContentUnavailableError):
        provider.update_plan_fields(plan["plan_id"], context="rejected context")

    assert provider.read_plan(plan["plan_id"]) == snapshot


def test_content_task_provider_refreshes_plan_after_stale_write_and_recovers() -> None:
    # Given: a stale provider and an authoritative provider over the same plan.
    content_provider = InMemoryBackend()
    creator = ContentTaskProvider(content_provider)
    plan = creator.create_plan("refresh-plan", "restore authoritative plan", [])
    plan_id = plan["plan_id"]
    stale_provider = ContentTaskProvider(content_provider)
    authoritative_provider = ContentTaskProvider(content_provider)
    authoritative_provider.update_plan_fields(plan_id, context="authoritative context")

    # When: the stale provider's plan mutation conflicts.
    with pytest.raises(ContentConflictError, match="revision"):
        stale_provider.update_plan_fields(plan_id, context="stale context")

    # Then: it exposes the authoritative value and can write again with the refreshed revision.
    assert stale_provider.read_plan(plan_id)["context"] == "authoritative context"
    stale_provider.update_plan_fields(plan_id, context="recovered context")
    assert ContentTaskProvider(content_provider).read_plan(plan_id)["context"] == "recovered context"


def test_content_task_provider_refreshes_task_after_stale_write_and_recovers() -> None:
    # Given: a stale provider and an authoritative provider over the same task.
    content_provider = InMemoryBackend()
    creator = ContentTaskProvider(content_provider)
    plan = creator.create_plan(
        "refresh-task", "restore authoritative task", [Task(id="T01", title="Refresh", status=TaskStatus.NOT_STARTED)]
    )
    plan_id = plan["plan_id"]
    stale_provider = ContentTaskProvider(content_provider)
    authoritative_provider = ContentTaskProvider(content_provider)
    authoritative_provider.update_task_status(plan_id, "T01", "in-progress")

    # When: the stale provider's task mutation conflicts.
    with pytest.raises(ContentConflictError, match="revision"):
        stale_provider.update_task_status(plan_id, "T01", "complete")

    # Then: it exposes the authoritative task state and can write again with the refreshed revision.
    assert stale_provider.read_task(plan_id, "T01")["status"] == "in-progress"
    stale_provider.update_task_status(plan_id, "T01", "complete")
    assert ContentTaskProvider(content_provider).read_task(plan_id, "T01")["status"] == "complete"


def test_sqlite_content_write_allows_only_one_concurrent_stale_revision(tmp_path: Path) -> None:
    # Given: separate SQLite connections holding the same revision.
    database = str(tmp_path / "content.sqlite3")
    first_backend = SQLiteBackend(database)
    second_backend = SQLiteBackend(database)
    reference = ContentRef(kind=ContentKind.PLAN, name="atomic-content")
    initial = first_backend.put_content(ContentWrite(reference=reference, content="initial"))
    ready = threading.Barrier(3)
    release = threading.Event()
    results: list[ContentRecord | ContentConflictError] = []

    def write(backend: SQLiteBackend, content: str) -> None:
        ready.wait()
        release.wait()
        try:
            results.append(
                backend.put_content(
                    ContentWrite(reference=reference, content=content, expected_revision=initial.revision)
                )
            )
        except ContentConflictError as error:
            results.append(error)

    try:
        # When: both writers are released against the same expected revision.
        first_thread = threading.Thread(target=write, args=(first_backend, "first"))
        second_thread = threading.Thread(target=write, args=(second_backend, "second"))
        first_thread.start()
        second_thread.start()
        ready.wait()
        release.set()
        first_thread.join()
        second_thread.join()

        # Then: exactly one write persists and the other reports the content conflict contract.
        successes = [result for result in results if isinstance(result, ContentRecord)]
        conflicts = [result for result in results if isinstance(result, ContentConflictError)]
        assert len(successes) == len(conflicts) == 1
        assert first_backend.get_content(reference) == successes[0]
        assert successes[0].revision == str(int(initial.revision) + 1)
    finally:
        first_backend._conn.close()
        second_backend._conn.close()


def test_sqlite_content_task_providers_claim_once_from_concurrent_snapshots(tmp_path: Path) -> None:
    # Given: two providers over separate SQLite connections hydrated from one not-started task.
    database = str(tmp_path / "claims.sqlite3")
    first_content = SQLiteBackend(database)
    second_content = SQLiteBackend(database)
    creator = ContentTaskProvider(first_content)
    plan = creator.create_plan(
        "atomic-claim", "claim once", [Task(id="T01", title="Claim once", status=TaskStatus.NOT_STARTED)]
    )
    plan_id = plan["plan_id"]
    first_provider = ContentTaskProvider(first_content)
    second_provider = ContentTaskProvider(second_content)
    ready = threading.Barrier(3)
    release = threading.Event()
    results: list[bool] = []

    def claim(provider: ContentTaskProvider) -> None:
        ready.wait()
        release.wait()
        results.append(provider.claim_task(plan_id, "T01"))

    try:
        # When: both providers claim their loaded not-started snapshot together.
        first_thread = threading.Thread(target=claim, args=(first_provider,))
        second_thread = threading.Thread(target=claim, args=(second_provider,))
        first_thread.start()
        second_thread.start()
        ready.wait()
        release.set()
        first_thread.join()
        second_thread.join()

        # Then: one caller claims the task, while the loser refreshes the persisted winner.
        assert sorted(results) == [False, True]
        persisted = ContentTaskProvider(first_content).read_task(plan_id, "T01")
        assert persisted["status"] == "in-progress"
    finally:
        first_content._conn.close()
        second_content._conn.close()
