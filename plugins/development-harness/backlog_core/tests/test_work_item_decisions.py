"""Command-scoped live work-item decision tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.file_cache import FileCache
from backlog_core.gh_client import _fetch_issues_graphql
from backlog_core.models import (
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    Output,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
)
from backlog_core.work_item_decisions import WorkItemDecisionContext

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def provider_item(reference: str, title: str, *, status: str = "status:groomed") -> ProviderItem:
    """Build one live provider item."""
    return ProviderItem(
        provider_id=f"node-{reference}",
        reference=reference,
        title=title,
        body="",
        state="OPEN",
        labels=[status],
        revision=f"revision-{reference}",
        milestone="M1",
    )


class DecisionBackend(InMemoryBackend):
    """In-memory backend with an observable GitHub live-read seam."""

    supports_github_extras = True

    def __init__(
        self,
        *,
        live_items: list[ProviderItem],
        cached_items: list[BacklogItem] | None = None,
        pending_items: list[BacklogItem] | None = None,
    ) -> None:
        super().__init__()
        self.live_items = live_items
        self.cached_items = cached_items or []
        self.pending_items = pending_items or []
        self.snapshot_requests: list[ReconcileRequest] = []
        self.cached_list_calls = 0
        self.live_error: Exception | None = None

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Return the requested live observation and record its scope."""
        self.snapshot_requests.append(request)
        if self.live_error is not None:
            raise self.live_error
        if request.scope in {ReconcileScope.TARGETED, ReconcileScope.LINKED}:
            by_reference = {item.reference: item for item in self.live_items}
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
            items = self.live_items
        return ProviderSnapshot(items=items, sync_started_at="2026-09-24T00:00:00+00:00")

    def pending_work_items(self, repo: str = "") -> list[BacklogItem]:
        """Return queued local intent independently from provider observations."""
        del repo
        return [item.model_copy(deep=True) for item in self.pending_items]

    def list_work_items(self) -> list[BacklogItem]:
        """Expose whether a live decision accidentally read the durable cache."""
        self.cached_list_calls += 1
        return [item.model_copy(deep=True) for item in self.cached_items]

    def cached_work_items(self, repo: str = "") -> list[BacklogItem]:
        """Expose repository-aware fallback through the provider-cache seam."""
        del repo
        return self.list_work_items()


def test_all_memoizes_one_bulk_snapshot_and_never_uses_cached_provider_rows() -> None:
    backend = DecisionBackend(
        live_items=[provider_item("#7", "live title")], cached_items=[BacklogItem(title="stale title", issue="#7")]
    )
    context = WorkItemDecisionContext(backend)

    first = context.all()
    second = context.all()

    assert [item.title for item in first.provider_items] == ["live title"]
    assert first.status_map[7].status == "status:groomed"
    assert first.status_map[7].milestone == "M1"
    assert second is first
    assert [request.scope for request in backend.snapshot_requests] == [ReconcileScope.INCREMENTAL]
    assert backend.cached_list_calls == 0


def test_explicit_cached_fallback_attempts_live_first_and_reads_cache_once() -> None:
    backend = DecisionBackend(live_items=[], cached_items=[BacklogItem(title="cached title", issue="#7")])
    backend.live_error = BackendUnavailableError("offline")
    output = Output()
    context = WorkItemDecisionContext(backend, allow_cached=True, output=output)

    first = context.all()
    second = context.all()
    target = context.select("#7", purpose="read")

    assert [item.title for item in first.provider_items] == ["cached title"]
    assert first.from_cache is True
    assert second is first
    assert len(backend.snapshot_requests) == 1
    assert backend.cached_list_calls == 1
    assert target.provider is not None
    assert target.provider.title == "cached title"
    assert target.provider_snapshot is None
    assert output.warnings == ["Live provider read failed; using cached work items: offline"]


def test_cached_fallback_withholds_rows_overlaid_by_the_pending_journal(tmp_path: Path, mocker: MockerFixture) -> None:
    backend = GitHubBackend(cache=FileCache(tmp_path))
    snapshot = ProviderSnapshot(
        items=[provider_item("#7", "provider title")], sync_started_at="2026-09-24T00:00:00+00:00"
    )
    backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL, apply_local_patches=False), snapshot=snapshot)
    backend.put_work_item(BacklogItem(title="queued title", description="queued edit", issue="#7"))
    assert [item.title for item in backend.list_work_items()] == ["queued title"]
    mocker.patch.object(backend, "fetch_snapshot", side_effect=BackendUnavailableError("offline"))
    context = WorkItemDecisionContext(backend, allow_cached=True)

    read = context.all()
    target = context.select("#7", purpose="mutation")

    assert read.provider_items == []
    assert target.provider is None
    assert target.pending is not None
    assert target.pending.title == "queued title"
    assert target.mutation_base == target.pending


def test_cached_fallback_selects_the_requested_repository_baseline(tmp_path: Path, mocker: MockerFixture) -> None:
    """Repository B fallback never selects repository A's equal issue number."""
    repo_a = "owner/repository-a"
    repo_b = "owner/repository-b"
    backend = GitHubBackend(repo=repo_a, cache=FileCache(tmp_path))
    backend.reconcile(
        ReconcileRequest(scope=ReconcileScope.INITIAL, repo=repo_a, apply_local_patches=False),
        snapshot=ProviderSnapshot(
            items=[provider_item("#7", "repository A item")], sync_started_at="2026-01-01T00:00:00+00:00"
        ),
    )
    backend.reconcile(
        ReconcileRequest(scope=ReconcileScope.INITIAL, repo=repo_b, apply_local_patches=False),
        snapshot=ProviderSnapshot(
            items=[provider_item("#7", "repository B item")], sync_started_at="2026-02-01T00:00:00+00:00"
        ),
    )
    backend.put_work_item(BacklogItem(title="repository A queued intent", issue="#7"), repo=repo_a)
    mocker.patch.object(backend, "fetch_snapshot", side_effect=BackendUnavailableError("offline"))

    target = WorkItemDecisionContext(backend, repo=repo_b, allow_cached=True).select("#7", purpose="mutation")

    assert target.provider is not None
    assert target.provider.title == "repository B item"
    assert target.provider_snapshot is None


def test_select_memoizes_one_targeted_snapshot_for_equivalent_exact_references() -> None:
    backend = DecisionBackend(live_items=[provider_item("#7", "live title")])
    context = WorkItemDecisionContext(backend)

    first = context.select("#7", purpose="read")
    second = context.select("7", purpose="read")

    assert first.provider is not None
    assert first.provider.title == "live title"
    assert second.provider == first.provider
    assert [(request.scope, request.references) for request in backend.snapshot_requests] == [
        (ReconcileScope.TARGETED, ["#7"])
    ]


def test_select_purpose_controls_pending_journal_access_and_mutation_base(mocker: MockerFixture) -> None:
    pending = BacklogItem(title="queued title", description="queued edit", issue="#7")
    backend = DecisionBackend(live_items=[provider_item("#7", "live title")], pending_items=[pending])
    pending_work_items = mocker.spy(backend, "pending_work_items")
    context = WorkItemDecisionContext(backend)

    read = context.select("#7", purpose="read")

    assert read.provider is not None
    assert read.provider.title == "live title"
    assert read.pending is None
    assert read.mutation_base is None
    pending_work_items.assert_not_called()

    mutation = context.select("#7", purpose="mutation")

    assert mutation.provider == read.provider
    assert mutation.pending == pending
    assert mutation.mutation_base == pending
    pending_work_items.assert_called_once_with()
    assert len(backend.snapshot_requests) == 1


def test_pending_is_repository_scoped_and_memoized(mocker: MockerFixture) -> None:
    pending = BacklogItem(title="queued title", issue="#7")
    backend = DecisionBackend(live_items=[], pending_items=[pending])
    pending_work_items = mocker.spy(backend, "pending_work_items")
    context = WorkItemDecisionContext(backend, repo="owner/repository")

    first = context.pending()
    second = context.pending()

    assert second is first
    assert first == [pending]
    pending_work_items.assert_called_once_with("owner/repository")


def test_targeted_then_global_reads_each_live_scope_once() -> None:
    backend = DecisionBackend(live_items=[provider_item("#7", "live title")])
    context = WorkItemDecisionContext(backend)

    context.select("#7", purpose="read")
    context.all()
    context.all()

    assert [request.scope for request in backend.snapshot_requests] == [
        ReconcileScope.TARGETED,
        ReconcileScope.INCREMENTAL,
    ]


def test_journal_entries_remain_separate_from_live_reads_and_supply_mutation_content() -> None:
    pending = BacklogItem(title="pending title", description="queued edit", issue="#7")
    pending_only = BacklogItem(title="pending only", issue="#8")
    backend = DecisionBackend(
        live_items=[provider_item("#7", "live title", status="status:blocked")], pending_items=[pending, pending_only]
    )
    context = WorkItemDecisionContext(backend)

    read = context.all()
    target = context.select("#7", purpose="mutation")

    assert [item.issue for item in read.provider_items] == ["#7"]
    assert target.provider is not None
    assert target.provider.title == "live title"
    assert target.provider.metadata.labels == ["status:blocked"]
    assert target.pending is not None
    assert target.pending.description == "queued edit"
    assert target.mutation_base == target.pending
    assert all(item.issue != "#8" for item in read.provider_items)


def test_supplied_repository_excludes_default_repository_pending_intent(tmp_path: Path, mocker: MockerFixture) -> None:
    backend = GitHubBackend(repo="default/repository", cache=FileCache(tmp_path))
    backend.put_work_item(BacklogItem(title="default pending", description="wrong repo", issue="#7"))
    mocker.patch.object(
        backend,
        "fetch_snapshot",
        return_value=ProviderSnapshot(
            items=[provider_item("#7", "supplied live")], sync_started_at="2026-09-24T00:00:00+00:00"
        ),
    )
    context = WorkItemDecisionContext(backend, repo="supplied/repository")

    target = context.select("#7", purpose="mutation")

    assert target.provider is not None
    assert target.provider.title == "supplied live"
    assert target.pending is None
    assert target.mutation_base == target.provider


def test_title_selection_joins_pending_intent_by_selected_provider_reference() -> None:
    selected_pending = BacklogItem(title="renamed queued title", description="selected edit", issue="#7")
    wrong_pending = BacklogItem(title="live title duplicate", description="wrong edit", issue="#8")
    backend = DecisionBackend(
        live_items=[provider_item("#7", "live title")], pending_items=[selected_pending, wrong_pending]
    )
    context = WorkItemDecisionContext(backend)

    target = context.select("live title", purpose="mutation")

    assert target.provider is not None
    assert target.provider.issue == "#7"
    assert target.pending is not None
    assert target.pending.issue == "#7"
    assert target.mutation_base == selected_pending


def test_live_read_failure_returns_no_partial_or_cached_result() -> None:
    backend = DecisionBackend(
        live_items=[provider_item("#7", "partial live row")], cached_items=[BacklogItem(title="cached row", issue="#9")]
    )
    backend.live_error = RuntimeError("second provider page failed")
    context = WorkItemDecisionContext(backend)

    with pytest.raises(RuntimeError, match="second provider page failed"):
        context.all()

    assert backend.cached_list_calls == 0


def test_snapshot_for_slices_memoized_bulk_snapshot_and_adds_absent_tombstones() -> None:
    backend = DecisionBackend(live_items=[provider_item("#7", "live title")])
    context = WorkItemDecisionContext(backend)
    context.all()

    snapshot = context.snapshot_for(ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#7", "#8"]))

    assert [(item.reference, item.exists) for item in snapshot.items] == [("#7", True), ("#8", False)]
    assert len(backend.snapshot_requests) == 1


def test_provider_pagination_failure_returns_no_partial_page(mocker: MockerFixture) -> None:
    page_one = {
        "repository": {
            "issues": {
                "nodes": [
                    {
                        "id": "node-7",
                        "number": 7,
                        "title": "first page",
                        "state": "OPEN",
                        "body": "",
                        "createdAt": "2026-09-24T00:00:00Z",
                        "updatedAt": "2026-09-24T00:00:00Z",
                        "labels": {"nodes": []},
                        "milestone": None,
                        "assignees": {"nodes": []},
                    }
                ],
                "pageInfo": {"hasNextPage": True, "endCursor": "page-2"},
            }
        }
    }
    graphql = mocker.patch(
        "backlog_core.gh_client._graphql_request", side_effect=[page_one, BacklogError("second provider page failed")]
    )

    with pytest.raises(BacklogError, match="second provider page failed"):
        _fetch_issues_graphql(mocker.Mock(), "owner", "repo")

    assert graphql.call_count == 2
