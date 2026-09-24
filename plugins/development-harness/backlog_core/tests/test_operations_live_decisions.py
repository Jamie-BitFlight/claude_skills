"""Operation-level routing through command-scoped live work-item truth."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BackendUnavailableError,
    BacklogItem,
    DuplicateItemError,
    Entry,
    Output,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    Section,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _provider_item(item: BacklogItem) -> ProviderItem:
    return ProviderItem(
        provider_id=f"node-{item.issue}",
        reference=item.issue,
        title=item.title,
        body=render_issue_body(item),
        state="OPEN",
        labels=["status:groomed"],
        revision=f"revision-{item.issue}",
        milestone=item.metadata.milestone,
    )


class _LiveBackend(InMemoryBackend):
    """Observable GitHub-capable backend with disagreeing live/cache data."""

    supports_github_extras = True

    def __init__(
        self,
        live_items: list[BacklogItem],
        *,
        cached_items: list[BacklogItem] | None = None,
        pending_items: list[BacklogItem] | None = None,
    ) -> None:
        super().__init__()
        self.live_items = live_items
        self.cached_items = cached_items or []
        self.pending_items = pending_items or []
        self.snapshot_requests: list[ReconcileRequest] = []
        self.reconciliations: list[tuple[ReconcileRequest, ProviderSnapshot | None]] = []
        self.writes: list[BacklogItem] = []
        self.cached_list_calls = 0
        self.cached_get_calls = 0
        self.live_error: BackendUnavailableError | None = None

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        self.snapshot_requests.append(request)
        if self.live_error is not None:
            raise self.live_error
        by_reference = {item.issue: _provider_item(item) for item in self.live_items}
        if request.scope in {ReconcileScope.TARGETED, ReconcileScope.LINKED}:
            items = [
                by_reference.get(
                    reference,
                    ProviderItem(
                        provider_id="",
                        reference=reference,
                        title="",
                        body="",
                        state="",
                        labels=[],
                        revision="",
                        exists=False,
                    ),
                )
                for reference in request.references
            ]
        else:
            items = list(by_reference.values())
        return ProviderSnapshot(items=items, sync_started_at="2026-09-24T00:00:00+00:00")

    def pending_work_items(self) -> list[BacklogItem]:
        return [item.model_copy(deep=True) for item in self.pending_items]

    def list_work_items(self) -> list[BacklogItem]:
        self.cached_list_calls += 1
        return [item.model_copy(deep=True) for item in self.cached_items]

    def get_work_item(self, reference: str) -> BacklogItem:
        self.cached_get_calls += 1
        for item in self.cached_items:
            if reference in {item.reference, item.issue}:
                return item.model_copy(deep=True)
        raise KeyError(reference)

    def put_work_item(self, item: BacklogItem) -> None:
        self.writes.append(item.model_copy(deep=True))

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
        self.reconciliations.append((request, snapshot))
        return ReconcileResult(fetched_items=len(snapshot.items) if snapshot is not None else 0)


def _configure(mocker: MockerFixture, backend: _LiveBackend) -> None:
    mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))


@pytest.mark.parametrize(
    ("operation", "expected_title"),
    [(operations.list_items, "live title"), (lambda: operations.list_followups("P1/T1"), None)],
)
def test_read_operations_ignore_disagreeing_cached_provider_rows(
    mocker: MockerFixture, operation: Callable[[], object], expected_title: str | None
) -> None:
    live = BacklogItem(title="live title", issue="#7", priority="P1")
    cached = BacklogItem(title="stale title", issue="#7", priority="P1")
    cached.metadata.followup_to = "P1/T1"
    backend = _LiveBackend([live], cached_items=[cached])
    _configure(mocker, backend)

    result = operation()

    assert isinstance(result, dict)
    assert isinstance(result["items"], list)
    if expected_title is None:
        assert result["items"] == []
    else:
        assert result["items"][0]["title"] == expected_title
    assert backend.cached_list_calls == 0
    assert [request.scope for request in backend.snapshot_requests] == [ReconcileScope.INCREMENTAL]


@pytest.mark.parametrize("selector", ["#7", "live title"])
def test_close_selection_uses_live_exact_and_title_truth(mocker: MockerFixture, selector: str) -> None:
    live = BacklogItem(title="live title", issue="#7", priority="P1")
    cached = BacklogItem(title="stale title", issue="#7", priority="P1")
    backend = _LiveBackend([live], cached_items=[cached])
    _configure(mocker, backend)
    mocker.patch.object(operations, "update_item_metadata")
    mocker.patch.object(operations, "close_github_issue")

    result = operations.close_item(selector, "wontfix", force=True)

    assert result["title"] == "live title"
    assert backend.cached_list_calls == 0
    expected_scope = ReconcileScope.TARGETED if selector == "#7" else ReconcileScope.INCREMENTAL
    assert [request.scope for request in backend.snapshot_requests] == [expected_scope]


def test_pending_intent_blocks_duplicate_creation_and_reference_collision(mocker: MockerFixture) -> None:
    pending_duplicate = BacklogItem(
        title="queued duplicate", description="unique pending concept", issue="#8", reference="#8", priority="P1"
    )
    pending_reference = BacklogItem(title="same slug", reference="p1-new-item", priority="P1")
    backend = _LiveBackend([], pending_items=[pending_duplicate, pending_reference])
    _configure(mocker, backend)

    with pytest.raises(DuplicateItemError):
        operations.add_item("pending concept", "unique pending concept", "P1")

    created = operations.add_item("new item", "different content", "P1", force=True)

    assert created["reference"] == "p1-new-item-1"


def test_pending_mutation_supplies_strike_base_and_decision_snapshot_is_reused(mocker: MockerFixture) -> None:
    live = BacklogItem(
        title="live title",
        issue="#7",
        priority="P1",
        sections={"facts": Section(entries=[Entry(id="live", content="provider")])},
    )
    pending = BacklogItem(
        title="queued title",
        issue="#7",
        priority="P1",
        sections={"facts": Section(entries=[Entry(id="pending", content="queued")])},
    )
    backend = _LiveBackend([live], pending_items=[pending])
    _configure(mocker, backend)

    result = operations.strike_entry("#7", "pending", "obsolete")

    assert result["title"] == "queued title"
    written_section = backend.writes[0].sections["facts"]
    assert isinstance(written_section, Section)
    assert written_section.entries[0].struck is True
    assert len(backend.snapshot_requests) == 1
    assert backend.reconciliations[0][1] is not None


@pytest.mark.parametrize("allow_cached", [False, True])
def test_live_failure_reads_cache_only_for_explicit_warned_fallback(mocker: MockerFixture, allow_cached: bool) -> None:
    backend = _LiveBackend([], cached_items=[BacklogItem(title="cached title", issue="#7", priority="P1")])
    backend.live_error = BackendUnavailableError("offline")
    _configure(mocker, backend)
    output = Output()

    if not allow_cached:
        with pytest.raises(BackendUnavailableError, match="offline"):
            operations.list_items(output=output)
        assert backend.cached_list_calls == 0
        return

    result = operations.list_items(allow_cached=True, output=output)

    items = result["items"]
    assert isinstance(items, list)
    first = items[0]
    assert isinstance(first, dict)
    assert first["title"] == "cached title"
    assert backend.cached_list_calls == 1
    assert output.warnings == ["Live provider read failed; using cached work items: offline"]


@pytest.mark.parametrize("cached_title", [None, "stale title"])
@pytest.mark.parametrize("route", ["link", "close", "resolve", "title", "description", "plan", "mark-groomed"])
def test_metadata_mutations_persist_selected_live_base_without_cache_reload(
    mocker: MockerFixture, route: str, cached_title: str | None
) -> None:
    live = BacklogItem(title="live title", description="live description", issue="#7", priority="P1")
    cached = (
        BacklogItem(title=cached_title, description="stale description", issue="#7", priority="P1")
        if cached_title
        else None
    )
    backend = _LiveBackend([live], cached_items=[cached] if cached is not None else [])
    _configure(mocker, backend)
    mocker.patch.object(operations, "try_get_github", return_value=None)
    mocker.patch.object(operations, "close_github_issue")
    mocker.patch.object(operations, "resolve_github_issue")
    mocker.patch.object(operations, "apply_status_groomed")

    if route == "link":
        operations.link_followup("#7", "P1/T1")
    elif route == "close":
        operations.close_item("#7", "wontfix", force=True)
    elif route == "resolve":
        operations.resolve_item("#7", "completed", force=True)
    elif route == "title":
        operations.update_item("#7", title="new title")
    elif route == "description":
        operations.update_item("#7", description="new description")
    elif route == "plan":
        operations.update_item("#7", plan="P7")
    else:
        operations.groom_item("#7", mark_groomed=True)

    assert backend.cached_get_calls == 0
    assert backend.writes
    assert backend.writes[0].description != "stale description"


def test_command_snapshot_uses_supplied_repository(mocker: MockerFixture) -> None:
    backend = _LiveBackend([BacklogItem(title="live title", issue="#7", priority="P1")])
    _configure(mocker, backend)

    operations.view_item("#7", repo="supplied/repository")

    assert backend.snapshot_requests[0].repo == "supplied/repository"


def test_live_empty_list_has_no_cache_ambiguity_warning(mocker: MockerFixture) -> None:
    backend = _LiveBackend([])
    _configure(mocker, backend)

    result = operations.list_items()

    assert result["items"] == []
    assert result["from_cache"] is False
    assert result["warnings"] == []
