from __future__ import annotations

import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import (
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)
from pydantic import ValidationError

from sam_schema.core.action_models import CreatePlanConfig, UpdatePlanConfig
from sam_schema.core.backends.content import ContentTaskProvider


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


def test_content_task_provider_updates_fields_and_owner_in_one_write_and_hydrates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a persisted plan and observable provider writes.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    plan = provider.create_plan("atomic-update", "persist fields and owner", [], owner_reference="bd-old")
    writes: list[ContentWrite] = []
    original_put = content_provider.put_content

    def record_write(request: ContentWrite) -> ContentRecord:
        writes.append(request)
        return original_put(request)

    monkeypatch.setattr(content_provider, "put_content", record_write)

    # When: plan content and ownership change together.
    provider.update_plan_fields(plan["plan_id"], context="updated atomically", owner_reference="bd-new")

    # Then: one write persists both values and a fresh provider hydrates the content.
    assert [write.owner_reference for write in writes] == ["bd-new"]
    fresh_provider = ContentTaskProvider(content_provider)
    assert fresh_provider.read_plan(plan["plan_id"])["context"] == "updated atomically"
    assert (
        content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan["plan_id"])).owner_reference
        == "bd-new"
    )


def test_content_task_provider_updates_owner_only_in_one_write(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a persisted plan and observable provider writes.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    plan = provider.create_plan("owner-only", "persist ownership", [])
    writes: list[ContentWrite] = []
    original_put = content_provider.put_content

    def record_write(request: ContentWrite) -> ContentRecord:
        writes.append(request)
        return original_put(request)

    monkeypatch.setattr(content_provider, "put_content", record_write)

    # When: only the opaque owner reference changes.
    provider.update_plan_fields(plan["plan_id"], owner_reference="bd-a1b2")

    # Then: the owner is persisted through one write.
    assert [write.owner_reference for write in writes] == ["bd-a1b2"]
    assert (
        content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan["plan_id"])).owner_reference
        == "bd-a1b2"
    )


def test_content_task_provider_rejects_combined_update_without_changing_content_or_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an owned persisted plan and a write outage.
    content_provider = InMemoryBackend()
    provider = ContentTaskProvider(content_provider)
    plan = provider.create_plan(
        "rollback-owner", "retain prior values", [], context="original", owner_reference="bd-old"
    )
    snapshot = provider.read_plan(plan["plan_id"])

    def unavailable_write(_: ContentWrite) -> ContentRecord:
        raise ContentUnavailableError("write unavailable")

    monkeypatch.setattr(content_provider, "put_content", unavailable_write)

    # When: a combined content and owner update fails.
    with pytest.raises(ContentUnavailableError, match="write unavailable"):
        provider.update_plan_fields(plan["plan_id"], context="rejected", owner_reference="bd-new")

    # Then: both the local view and a fresh hydration retain prior state.
    assert provider.read_plan(plan["plan_id"]) == snapshot
    fresh_provider = ContentTaskProvider(content_provider)
    assert fresh_provider.read_plan(plan["plan_id"]) == snapshot
    assert (
        content_provider.get_content(ContentRef(kind=ContentKind.PLAN, name=plan["plan_id"])).owner_reference
        == "bd-old"
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
