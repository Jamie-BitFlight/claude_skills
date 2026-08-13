from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

import pytest
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BacklogItem,
    BacklogItemMetadata,
    Entry,
    PatchResult,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
    Section,
)
from backlog_core.reconciliation import (
    ActionResult,
    LogicalCacheRecord,
    ReconcileExecution,
    finalize_reconciliation,
    reconcile_backlog,
    synchronized_fingerprint,
)


def _item(description: str, *, reference: str = "#1", fingerprint: str = "", title: str = "Example") -> BacklogItem:
    return BacklogItem(
        title=title,
        description=description,
        metadata=BacklogItemMetadata(
            source="test",
            added="2026-08-12",
            priority="P1",
            item_type="Feature",
            status="open",
            issue=reference,
            sync_fingerprint=fingerprint,
            plan="local-plan.md",
            topic="local-topic",
        ),
    )


def _provider(
    body: str, *, state: str = "OPEN", exists: bool = True, reference: str = "#1", title: str = "Example"
) -> ProviderItem:
    return ProviderItem(
        provider_id=f"node-{reference}",
        reference=reference,
        title=title,
        body=body,
        state=state,
        labels=["feature"],
        revision="rev-1",
        exists=exists,
    )


def _plan(local: BacklogItem | None, provider: ProviderItem, **request_updates):
    records = [] if local is None else [LogicalCacheRecord(key="cache-1", item=local)]
    request = ReconcileRequest(scope=ReconcileScope.LINKED, references=[provider.reference], **request_updates)
    snapshot = ProviderSnapshot(items=[provider], sync_started_at="watermark", pages_fetched=1)
    return reconcile_backlog(records, snapshot, request)


def _applied(plan, *, cache_error_phase: str = ""):
    cache_results = [
        ActionResult(
            key=action.key, phase=action.phase, status="error" if action.phase == cache_error_phase else "applied"
        )
        for action in plan.cache_actions
    ]
    patch_results = [
        PatchResult(provider_id=patch.provider_id, reference=patch.reference, status="applied", revision="rev-2")
        for patch in plan.provider_patches
    ]
    return finalize_reconciliation(plan, ReconcileExecution(cache_results=cache_results, patch_results=patch_results))


def test_engine_has_no_filesystem_or_yaml_imports() -> None:
    source = Path(__file__).parents[1] / "backlog_core" / "reconciliation.py"

    tree = ast.parse(source.read_text())
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}

    assert not any("yaml_io" in name or "file_cache" in name or "pathlib" in name for name in imports)
    assert calls.isdisjoint({"parse_backlog", "get_backlog_dir", "open"})


def test_unchanged_body_is_a_no_op() -> None:
    baseline = _item("same")
    local = baseline.model_copy(deep=True)
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local.metadata.labels = ["feature"]
    local.metadata.updated_at = "rev-1"

    plan = _plan(local, _provider(render_issue_body(baseline)))

    assert plan.provider_patches == []
    assert plan.cache_actions == []
    assert plan.result.no_ops == 1


def test_unchanged_title_is_a_no_op() -> None:
    baseline = _item("same")
    local = baseline.model_copy(deep=True)
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
    local.metadata.labels = ["feature"]
    local.metadata.updated_at = "rev-1"

    plan = _plan(local, _provider(render_issue_body(baseline)))

    assert plan.provider_patches == []
    assert plan.cache_actions == []
    assert plan.result.no_ops == 1


def test_local_title_change_stays_pending_without_checkpoint() -> None:
    baseline = _item("same")
    local = _item("same", fingerprint=synchronized_fingerprint(baseline), title="Local rename")

    plan = _plan(local, _provider(render_issue_body(baseline)))

    assert plan.cache_actions[0].record.item.title == "Local rename"
    assert not any(action.phase == "checkpoint" for action in plan.cache_actions)
    assert plan.provider_patches == []
    assert plan.result.conflicts == 1


def test_remote_title_change_updates_local_state() -> None:
    baseline = _item("same")
    local = _item("same", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(baseline), title="Provider rename"))

    updated = plan.cache_actions[0].record.item
    assert updated.title == "Provider rename"
    assert updated.metadata.sync_fingerprint == synchronized_fingerprint(updated)
    assert plan.provider_patches == []


def test_equal_body_updates_provider_fields_without_patch() -> None:
    baseline = _item("same")
    local = baseline.model_copy(deep=True)
    local.reference = "opaque-cache-key"
    local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)

    plan = _plan(local, _provider(render_issue_body(baseline)))

    assert plan.provider_patches == []
    observed = plan.cache_actions[0].record.item
    assert observed.reference == "opaque-cache-key"
    assert (observed.metadata.status, observed.metadata.labels, observed.metadata.updated_at) == (
        "open",
        ["feature"],
        "rev-1",
    )


def test_local_only_change_requests_patch_and_checkpoint() -> None:
    baseline = _item("before")
    local = _item("after", fingerprint=synchronized_fingerprint(baseline))
    local.reference = "opaque-cache-key"

    plan = _plan(local, _provider(render_issue_body(baseline)))
    outcome = _applied(plan)

    assert len(plan.provider_patches) == 1
    assert any(action.phase == "checkpoint" for action in plan.cache_actions)
    assert all(action.record.item.reference == "opaque-cache-key" for action in plan.cache_actions)
    assert outcome.result.provider_patches == 1
    assert outcome.advance_snapshot_checkpoint is True


def test_remote_only_change_requests_local_update() -> None:
    baseline = _item("before")
    local = _item("before", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(_item("after"))))

    assert plan.provider_patches == []
    assert plan.cache_actions[-1].record.item.description == "after"


def test_concurrent_change_reuses_entry_aware_merge() -> None:
    baseline = _item("same")
    local = _item("same", fingerprint=synchronized_fingerprint(baseline))
    local.sections["fact_check"] = Section(entries=[Entry(id="2026-08-12T00:00:00Z", content="local")])
    remote = _item("same")
    remote.sections["fact_check"] = Section(entries=[Entry(id="2026-08-12T00:00:01Z", content="remote")])

    plan = _plan(local, _provider(render_issue_body(remote)))

    merged = plan.cache_actions[0].record.item.sections["fact_check"]
    assert isinstance(merged, Section)
    assert [entry.content for entry in merged.entries] == ["local", "remote"]
    assert len(plan.provider_patches) == 1


def test_bootstrap_equal_body_establishes_checkpoint_without_patch() -> None:
    local = _item("same")

    plan = _plan(local, _provider(render_issue_body(local)))

    assert plan.provider_patches == []
    assert plan.cache_actions[-1].record.item.metadata.sync_fingerprint


def test_force_replaces_synchronized_content() -> None:
    baseline = _item("before")
    local = _item("local", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(_item("remote"))), force=True)

    assert plan.provider_patches == []
    assert plan.cache_actions[-1].record.item.description == "remote"


def test_remote_only_item_requests_logical_cache_creation() -> None:
    remote = _provider(render_issue_body(_item("remote", reference="#2")), reference="#2")

    plan = _plan(None, remote)

    assert plan.cache_actions[0].key == "#2"
    assert plan.cache_actions[0].record.item.reference == "#2"
    assert plan.cache_actions[0].record.item.description == "remote"


def test_tombstone_unlinks_without_discarding_local_content() -> None:
    local = _item("keep me", fingerprint="checkpoint")
    local.reference = "opaque-cache-key"

    plan = _plan(local, _provider("", exists=False))

    action = plan.cache_actions[0]
    outcome = _applied(plan)

    assert action.kind == "unlink"
    assert action.record.item.reference == "opaque-cache-key"
    assert action.record.item.description == "keep me"
    assert action.record.item.metadata.issue == ""
    assert outcome.result.deleted_provider_items == 1


def test_remote_closed_local_change_stays_closed_and_only_patches_body() -> None:
    baseline = _item("before")
    local = _item("after", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(baseline), state="CLOSED"))

    assert plan.cache_actions[0].record.item.metadata.status == "closed"
    assert plan.provider_patches[0].body.endswith("after\n")


def test_equal_rendered_body_suppresses_provider_patch() -> None:
    local = _item("same")

    plan = _plan(local, _provider(render_issue_body(local).replace("\n", "\r\n")))

    assert plan.provider_patches == []


def test_remote_merge_preserves_local_only_metadata() -> None:
    baseline = _item("before")
    local = _item("before", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(_item("after"))))

    updated = plan.cache_actions[-1].record.item
    assert (updated.metadata.plan, updated.metadata.topic) == ("local-plan.md", "local-topic")


@pytest.mark.parametrize(("patch_status", "conflicts", "failures"), [("conflict", 1, 0), ("error", 0, 1)])
def test_patch_failures_leave_checkpoint_unapplied(
    patch_status: Literal["conflict", "error"], conflicts: int, failures: int
) -> None:
    baseline = _item("before")
    plan = _plan(_item("after", fingerprint=synchronized_fingerprint(baseline)), _provider(render_issue_body(baseline)))
    patch = plan.provider_patches[0]
    checkpoint = next(action for action in plan.cache_actions if action.phase == "checkpoint")
    before_provider = [
        ActionResult(key=action.key, phase=action.phase, status="applied")
        for action in plan.cache_actions
        if action.phase == "before_provider"
    ]
    execution = ReconcileExecution(
        cache_results=[*before_provider, ActionResult(key=checkpoint.key, phase="checkpoint", status="applied")],
        patch_results=[
            PatchResult(provider_id=patch.provider_id, reference=patch.reference, status=patch_status, message="failed")
        ],
    )

    outcome = finalize_reconciliation(plan, execution)

    assert (outcome.result.conflicts, outcome.result.failures) == (conflicts, failures)
    assert outcome.result.local_updates == len({result.key for result in before_provider})
    assert checkpoint.requires_patch == patch.reference
    assert outcome.advance_snapshot_checkpoint is (patch_status == "conflict")


def test_checkpoint_failure_blocks_global_checkpoint() -> None:
    baseline = _item("before")
    plan = _plan(_item("after", fingerprint=synchronized_fingerprint(baseline)), _provider(render_issue_body(baseline)))

    outcome = _applied(plan, cache_error_phase="checkpoint")

    assert outcome.result.failures == 1
    assert outcome.advance_snapshot_checkpoint is False


def test_dry_run_returns_no_executable_actions() -> None:
    baseline = _item("before")
    local = _item("after", fingerprint=synchronized_fingerprint(baseline))

    plan = _plan(local, _provider(render_issue_body(baseline)), dry_run=True)
    outcome = finalize_reconciliation(plan, ReconcileExecution())

    assert plan.cache_actions == []
    assert plan.provider_patches == []
    assert plan.result.changed_references == ["#1"]
    assert outcome.advance_snapshot_checkpoint is False
