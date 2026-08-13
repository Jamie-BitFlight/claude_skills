from __future__ import annotations

import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentKind, ContentQuery, ContentRef, ContentWrite
from pydantic import ValidationError

from sam_schema.core.action_models import CreatePlanConfig, UpdatePlanConfig
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.models import Task, TaskStatus


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
