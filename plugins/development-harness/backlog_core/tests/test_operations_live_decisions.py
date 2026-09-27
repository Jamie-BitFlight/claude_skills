"""Operation-level routing through command-scoped live work-item truth."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from backlog_core import operations
from backlog_core.backend_types import BacklogConfig, ListPageResult
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.file_cache import FileCache
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
from backlog_core.reconciliation import provider_item_to_backlog_item

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from github.Repository import Repository
    from pytest_mock import MockerFixture

    from backlog_core.backend_types import ListPageRequest


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
        self.page_requests: list[object] = []
        self.reconciliations: list[tuple[ReconcileRequest, ProviderSnapshot | None]] = []
        self.writes: list[BacklogItem] = []
        self.write_repos: list[str] = []
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

    def pending_work_items(self, repo: str = "") -> list[BacklogItem]:
        del repo
        return [item.model_copy(deep=True) for item in self.pending_items]

    def list_work_items(self) -> list[BacklogItem]:
        self.cached_list_calls += 1
        return [item.model_copy(deep=True) for item in self.cached_items]

    def cached_work_items(self, repo: str = "") -> list[BacklogItem]:
        del repo
        return self.list_work_items()

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Return a structural repository stand-in carrying only ``full_name``."""
        del timeout
        return cast("Repository", SimpleNamespace(full_name=repo or "owner/repository"))

    def fetch_page(
        self, request: ListPageRequest, *, match: Callable[[BacklogItem, ProviderItem], bool], force_hydration: bool
    ) -> ListPageResult:
        """Apply *match* directly over ``live_items`` (see ``RequestShapedListing``)."""
        del force_hydration
        self.page_requests.append(request)
        if self.live_error is not None:
            raise self.live_error
        provider_items = [_provider_item(item) for item in self.live_items]
        matched = [pi for pi in provider_items if match(provider_item_to_backlog_item(pi), pi)]
        after_offset = matched[request.offset :]
        if request.limit > 0:
            has_more = len(after_offset) > request.limit
            page_items = after_offset[: request.limit]
        else:
            has_more = False
            page_items = after_offset
        return ListPageResult(
            items=page_items, has_more=has_more, total=len(matched), sync_started_at="2026-09-24T00:00:00+00:00"
        )

    def _fetch_issues_page_graphql(self, repo: object, owner: str, repo_name: str, **kwargs: object) -> object:
        """Unused by this double's own ``fetch_page`` -- present only to satisfy ``RequestShapedListing``."""
        raise NotImplementedError

    def search_issues_by_title(self, repo: str, selector: str) -> list[object]:
        """Return raw nodes for every live item whose title contains *selector*."""
        del repo
        return [
            {
                "id": f"node-{item.issue}",
                "number": int(item.issue.lstrip("#")),
                "title": item.title,
                "state": "OPEN",
                "body": render_issue_body(item),
                "createdAt": "2026-09-24T00:00:00Z",
                "updatedAt": "2026-09-24T00:00:00Z",
                "labels": [{"name": "status:groomed", "id": "status:groomed"}],
                "milestone": None,
                "assignees": [],
            }
            for item in self.live_items
            if selector.lower() in item.title.lower()
        ]

    def fetch_issue_titles(self, repo: str, *, include_closed: bool = False) -> list[tuple[int, str]]:
        """Return every live item's ``(number, title)``."""
        del repo, include_closed
        return [(int(item.issue.lstrip("#")), item.title) for item in self.live_items]

    def get_work_item(self, reference: str) -> BacklogItem:
        self.cached_get_calls += 1
        for item in self.cached_items:
            if reference in {item.reference, item.issue}:
                return item.model_copy(deep=True)
        raise KeyError(reference)

    def put_work_item(self, item: BacklogItem, repo: str = "") -> None:
        self.writes.append(item.model_copy(deep=True))
        self.write_repos.append(repo)

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
    # Both operations now read through the request-shaped page fetch, not a
    # bulk fetch_snapshot -- see WorkItemDecisionContext.page().
    assert backend.snapshot_requests == []
    assert len(backend.page_requests) == 1


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
    # An exact "#7" selector resolves through one TARGETED fetch_snapshot;
    # a title selector resolves through search then a TARGETED fetch_snapshot
    # of the one match -- either way, never a bulk/INCREMENTAL read.
    assert [request.scope for request in backend.snapshot_requests] == [ReconcileScope.TARGETED]


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


def test_command_reconciliation_uses_supplied_repository(mocker: MockerFixture) -> None:
    backend = _LiveBackend([BacklogItem(title="live title", issue="#7", priority="P1")])
    _configure(mocker, backend)

    operations.update_item("#7", description="updated", repo="supplied/repository")

    assert backend.snapshot_requests[0].repo == "supplied/repository"
    assert backend.write_repos == ["supplied/repository"]
    assert backend.reconciliations[0][0].repo == "supplied/repository"


def test_live_empty_list_has_no_cache_ambiguity_warning(mocker: MockerFixture) -> None:
    backend = _LiveBackend([])
    _configure(mocker, backend)

    result = operations.list_items()

    assert result["items"] == []
    assert result["from_cache"] is False
    assert result["warnings"] == []


_DIRECT_PROVIDER_ROUTES = ("add", "title", "plan", "status", "mark-groomed", "close", "resolve")


def _run_mutation_and_capture_direct_provider_call(
    mocker: MockerFixture, backend: _LiveBackend, route: str, *, allow_cached: bool
) -> MagicMock:
    """Run one route while replacing only its external provider side effect."""
    _configure(mocker, backend)
    repository = SimpleNamespace(full_name="owner/repository")
    mocker.patch.object(operations, "try_get_github", return_value=repository)
    mocker.patch.object(operations, "_fetch_issue_graphql", return_value={"id": "node-7"})
    provider_calls = {
        "add": mocker.patch.object(operations, "create_issue_for_item", return_value=99),
        "title": mocker.patch.object(operations, "_update_issue_graphql"),
        "plan": mocker.patch.object(operations, "_add_comment_graphql"),
        "status": mocker.patch.object(operations, "apply_status_in_progress"),
        "mark-groomed": mocker.patch.object(operations, "apply_status_groomed"),
        "close": mocker.patch.object(operations, "close_github_issue"),
        "resolve": mocker.patch.object(operations, "resolve_github_issue"),
    }

    if route == "add":
        operations.add_item("new item", "new description", "P1", force=True, allow_cached=allow_cached)
    elif route == "title":
        operations.update_item("#7", title="renamed", allow_cached=allow_cached)
    elif route == "plan":
        operations.update_item("#7", plan="P7", allow_cached=allow_cached)
    elif route == "status":
        operations.update_item("#7", status="in-progress", allow_cached=allow_cached)
    elif route == "mark-groomed":
        operations.groom_item("#7", mark_groomed=True, allow_cached=allow_cached)
    elif route == "close":
        operations.close_item("#7", "wontfix", force=True, allow_cached=allow_cached)
    else:
        operations.resolve_item("#7", "completed", force=True, allow_cached=allow_cached)
    return provider_calls[route]


@pytest.mark.parametrize("route", _DIRECT_PROVIDER_ROUTES)
def test_cached_fallback_queues_without_direct_provider_side_effect(mocker: MockerFixture, route: str) -> None:
    """Explicit fallback never mutates a provider selected from cached state."""
    cached = BacklogItem(title="cached title", issue="#7", priority="P1")
    backend = _LiveBackend([], cached_items=[cached])
    backend.live_error = BackendUnavailableError("offline")

    provider_call = _run_mutation_and_capture_direct_provider_call(mocker, backend, route, allow_cached=True)

    provider_call.assert_not_called()
    assert backend.writes


@pytest.mark.parametrize("route", _DIRECT_PROVIDER_ROUTES[1:])
def test_pending_only_tombstone_queues_without_direct_provider_side_effect(mocker: MockerFixture, route: str) -> None:
    """A live tombstone plus pending intent is not a live provider target."""
    pending = BacklogItem(title="pending title", issue="#7", priority="P1")
    backend = _LiveBackend([], pending_items=[pending])

    provider_call = _run_mutation_and_capture_direct_provider_call(mocker, backend, route, allow_cached=False)

    provider_call.assert_not_called()
    assert backend.writes


def test_exact_groom_and_mark_groomed_persist_content_and_status_together(mocker: MockerFixture) -> None:
    """The final queued item contains both mutations from one exact command."""
    live = BacklogItem(title="live title", issue="#7", priority="P1")
    backend = _LiveBackend([live])
    _configure(mocker, backend)
    mocker.patch.object(operations, "apply_status_groomed")

    operations.groom_item(
        "#7", section="Acceptance Criteria", content="- [ ] Retain the new criterion", mark_groomed=True
    )

    stored = backend.writes[-1]
    section = stored.sections["acceptance_criteria"]
    assert isinstance(section, Section)
    assert section.entries[-1].content == "- [ ] Retain the new criterion"
    assert stored.metadata.status == "groomed"


@pytest.mark.parametrize(("pending_only", "allow_cached"), [(False, True), (True, False)])
def test_verified_fallback_persists_queued_status_intent(
    tmp_path: Path, mocker: MockerFixture, pending_only: bool, allow_cached: bool
) -> None:
    """A queued verified report corresponds to a durable local status mutation."""
    repo = "owner/repository"
    item = BacklogItem(title="selected title", issue="#7", priority="P1")
    backend = GitHubBackend(repo=repo, cache=FileCache(tmp_path))
    if pending_only:
        backend.put_work_item(item, repo)
        snapshot = ProviderSnapshot(
            items=[
                ProviderItem(
                    provider_id="", reference="#7", title="", body="", state="", labels=[], revision="", exists=False
                )
            ],
            sync_started_at="2026-09-24T00:00:00+00:00",
        )
        mocker.patch.object(backend, "fetch_snapshot", return_value=snapshot)
    else:
        backend.reconcile(
            ReconcileRequest(scope=ReconcileScope.INITIAL, repo=repo, apply_local_patches=False),
            snapshot=ProviderSnapshot(items=[_provider_item(item)], sync_started_at="2026-09-24T00:00:00+00:00"),
        )
        mocker.patch.object(backend, "fetch_snapshot", side_effect=BackendUnavailableError("offline"))
    mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))
    apply_verified = mocker.patch.object(operations, "apply_status_verified")

    result = operations.update_item("#7", verified=True, repo=repo, allow_cached=allow_cached)

    apply_verified.assert_not_called()
    assert result["verified"] is True
    queued = backend.pending_work_items(repo)
    assert queued[-1].metadata.status == "verified"


def test_add_item_reports_refused_github_creation_and_keeps_the_item(tmp_path: Path, mocker: MockerFixture) -> None:
    """GitHub answering ``createIssue`` with a null issue is a reported creation failure, not a crash.

    GitHub returns ``{"createIssue": {"issue": null}}`` with no ``errors`` when it refuses content
    creation (observed 2026-09-27 while the account was under a secondary rate limit; REST returned
    403 for the same request). Only the GraphQL transport is faked; the backend, cache and
    ``gh_client`` creation path are real.
    """
    repo = "owner/repository"
    backend = GitHubBackend(repo=repo, cache=FileCache(tmp_path))
    mocker.patch.object(
        backend, "fetch_snapshot", return_value=ProviderSnapshot(items=[], sync_started_at="2026-09-27T00:00:00+00:00")
    )
    repository = mocker.Mock(full_name=repo, node_id="R_node")

    def graphql_query(query: str, _variables: dict[str, object]) -> tuple[dict[str, str], dict[str, object]]:
        if "createIssue" in query:
            return {}, {"data": {"createIssue": {"issue": None}}}
        return {}, {"data": {"repository": {}}}

    repository.requester.graphql_query.side_effect = graphql_query
    mocker.patch.object(backend, "try_get_github", return_value=repository)
    mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))

    result = operations.add_item("new item", "new description", "P1", type_="Bug", force=True)

    assert result["item_ref"] == ""
    errors = result["errors"]
    assert isinstance(errors, list)
    assert len(errors) == 1
    assert "createIssue" in errors[0]
    assert [item.title for item in backend.list_work_items()] == ["new item"]
