"""Tests that a refused query never reports itself as a missing or empty backlog.

Two reads told the same lie in a sandbox that serves REST but rejects GraphQL.
``backlog view --selector "#519"`` raised ``ItemNotFoundError`` for an issue that
exists, because ``view_enrich_from_github`` returned ``False`` for the refusal and
``view_item`` reads ``False`` as "no such item". ``backlog list`` reported
``count: 0`` against a real backlog, because a cache that had never synced is
shaped exactly like an empty one.

Neither read is made fatal here. A cached record still answers a view, and a list
still renders. What changes is that the answer names its own limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from github import GithubException

from backlog_core import gh_client, operations
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    GraphQLUnavailableError,
    ItemNotFoundError,
    Output,
    ReconcileResult,
    ViewItemResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pytest_mock import MockerFixture

    from backlog_core.models import ReconcileRequest

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``try_get_github`` returns."""

    full_name = "owner/repo"


def _item(issue: str, title: str = "An item") -> BacklogItem:
    """Build a minimal open backlog item carrying the given issue reference."""
    return BacklogItem(title=title, issue=issue, section="P1", status="status:in-progress")


class TestViewEnrichSurfacesTheRefusal:
    """``False`` from this function means "no such issue", so a refusal must not return it."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")

    def test_a_generic_backlog_error_still_returns_false(self, mocker: MockerFixture) -> None:
        """An ordinary failure keeps the existing local-only fallback."""
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=BacklogError("query rejected"))

        assert gh_client.view_enrich_from_github(ViewItemResult(), "519") is False

    def test_a_github_exception_still_returns_false(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=GithubException(status=404, data={"message": "Not Found"}, headers={}),
        )

        assert gh_client.view_enrich_from_github(ViewItemResult(), "519") is False

    def test_an_unreachable_backend_still_returns_false(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        assert gh_client.view_enrich_from_github(ViewItemResult(), "519") is False


class _ViewBackend:
    """Backend stub exposing only what ``view_item`` reads."""

    issue_id_type = "int"
    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items


def _patch_view_backend(mocker: MockerFixture, items: list[BacklogItem]) -> None:
    """Point ``operations.get_config()`` at a backend serving *items*."""
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_ViewBackend(items)))


class TestViewItemDoesNotCallARefusalAMissingItem:
    """ "The backend refused the query" and "the item does not exist" are different answers."""

    def test_an_uncached_item_reports_the_refusal(self, mocker: MockerFixture) -> None:
        """This is the reported defect: #519 exists, and the view claimed it did not."""
        _patch_view_backend(mocker, [])
        mocker.patch.object(
            operations, "view_enrich_from_github", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE)
        )

        with pytest.raises(GraphQLUnavailableError):
            operations.view_item("#519", output=Output())

    def test_a_genuinely_absent_item_still_reports_not_found(self, mocker: MockerFixture) -> None:
        """The refusal path must not blur the real missing-item answer."""
        _patch_view_backend(mocker, [])
        mocker.patch.object(operations, "view_enrich_from_github", return_value=False)

        with pytest.raises(ItemNotFoundError):
            operations.view_item("#519", output=Output())

    def test_a_cached_item_still_renders(self, mocker: MockerFixture) -> None:
        """The cached record answers the view, so a refusal does not fail the read."""
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(
            operations, "view_enrich_from_github", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE)
        )

        assert operations.view_item("#519", output=Output()).title == "Cached title"

    def test_a_cached_item_warns_and_names_the_cause(self, mocker: MockerFixture) -> None:
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(
            operations, "view_enrich_from_github", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE)
        )
        out = Output()

        operations.view_item("#519", output=out)

        assert any(_REFUSAL_MESSAGE in w for w in out.warnings)

    def test_a_plain_unreachable_backend_keeps_its_existing_wording(self, mocker: MockerFixture) -> None:
        """Callers match on this string, so the non-refusal path must not change."""
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(operations, "view_enrich_from_github", return_value=False)
        out = Output()

        operations.view_item("#519", output=out)

        assert any(w.startswith("backend unreachable — ") for w in out.warnings)


class _CacheBackend:
    """Backend stub whose cache is fed by an external provider."""

    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Satisfy the ``SyncProvider`` protocol; never called by ``list_items``."""
        raise NotImplementedError


class _NativeBackend:
    """Backend stub that owns its own storage, with no provider to lag behind."""

    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items


def _warnings(result: Mapping[str, object]) -> list[str]:
    """Narrow the heterogeneous ``list_items`` result to its warning strings."""
    raw = result.get("warnings", [])
    return [str(entry) for entry in raw] if isinstance(raw, list) else []


_EMPTY_CACHE_MARKER = "The local cache holds no items"


class TestEmptyCacheIsDistinguishableFromAnEmptyBacklog:
    """``count: 0`` from a cache that never synced is not the same answer as an empty backlog."""

    def test_an_empty_provider_backed_cache_warns(self, mocker: MockerFixture) -> None:
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_CacheBackend([])))

        warnings = _warnings(operations.list_items(output=Output()))

        assert any(_EMPTY_CACHE_MARKER in w for w in warnings)

    def test_a_populated_cache_does_not_warn(self, mocker: MockerFixture) -> None:
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_CacheBackend([_item("#1")])))

        warnings = _warnings(operations.list_items(output=Output()))

        assert not any(_EMPTY_CACHE_MARKER in w for w in warnings)

    def test_a_filter_matching_nothing_does_not_warn(self, mocker: MockerFixture) -> None:
        """A genuine zero against a populated cache is an answer, not an ambiguity."""
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_CacheBackend([_item("#1")])))

        result = operations.list_items(title="no-such-title-xyz", output=Output())

        assert result["count"] == 0
        assert not any(_EMPTY_CACHE_MARKER in w for w in _warnings(result))

    def test_a_native_backend_with_no_items_does_not_warn(self, mocker: MockerFixture) -> None:
        """SQLite, memory and beads own their storage — an empty read is authoritative."""
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_NativeBackend([])))

        warnings = _warnings(operations.list_items(output=Output()))

        assert not any(_EMPTY_CACHE_MARKER in w for w in warnings)


class _CheckpointedBackend:
    """Backend stub that also implements ``SnapshotCheckpointProvider``.

    Unlike ``_CacheBackend`` above (whose ``reconcile`` is documented "never
    called by ``list_items``"), this stub reports its checkpoint state via
    ``has_synced_snapshot`` so ``list_items``'s one-shot cold-cache
    read-through (A-critique.md Sec 5, ALT-5) is reachable in a test.
    """

    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem], *, synced: bool) -> None:
        self._items = items
        self._synced = synced

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def has_synced_snapshot(self) -> bool:
        return self._synced

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Satisfy the ``SyncProvider`` protocol; tests patch the wrapper instead."""
        raise NotImplementedError


class TestColdCacheReadsThroughOnce:
    """A never-synced cache triggers one automatic refresh instead of only naming
    the ambiguity (A-critique.md Sec 5, ALT-5)."""

    def test_a_cold_cache_triggers_exactly_one_refresh_attempt(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github")

        operations.list_items(output=Output())

        refresh_mock.assert_called_once()

    def test_a_warm_cache_does_not_trigger_a_spurious_refresh(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([_item("#1")], synced=True)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github")

        operations.list_items(output=Output())

        refresh_mock.assert_not_called()

    def test_an_explicit_refresh_request_does_not_also_trigger_the_automatic_path(self, mocker: MockerFixture) -> None:
        """``refresh=True`` must not cause two refresh attempts in one call."""
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github")

        operations.list_items(refresh=True, output=Output())

        refresh_mock.assert_called_once()

    def test_a_failed_refresh_does_not_loop_and_the_existing_warning_still_fires(self, mocker: MockerFixture) -> None:
        """A refusal/offline failure (no token, still refused) is swallowed: it must
        not raise for a caller who never asked for a refresh, and the existing
        never-synced-cache warning must still fire, unchanged, because the
        checkpoint honestly stays ``None``."""
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(
            operations,
            "refresh_local_cache_from_github",
            side_effect=GithubException(status=401, data={"message": "Bad credentials"}, headers={}),
        )
        out = Output()

        result = operations.list_items(output=out)

        refresh_mock.assert_called_once()
        assert any(_EMPTY_CACHE_MARKER in w for w in _warnings(result))

    def test_a_second_cold_but_explained_call_attempts_again_without_looping(self, mocker: MockerFixture) -> None:
        """Each call against a cache that never manages to sync tries exactly once
        per call -- never a retry loop within a single call -- and a later call is
        not suppressed just because an earlier one already failed: the checkpoint
        is still honestly ``None``, so "we tried and could not" is what every
        subsequent listing should keep attempting to upgrade to real data, not a
        cost paid once and then silently given up on."""
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(
            operations, "refresh_local_cache_from_github", side_effect=BacklogError("no token configured")
        )

        operations.list_items(output=Output())
        operations.list_items(output=Output())

        assert refresh_mock.call_count == 2

    def test_a_successful_refresh_returns_real_data_not_just_a_provenance_note(self, mocker: MockerFixture) -> None:
        """The caller of a cold-cache listing that resolves gets real items back --
        A1's honest checkpoint plus this read-through, not merely an annotation
        that the emptiness was explained."""
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))

        def _do_refresh(*_args: object, **_kwargs: object) -> dict[str, int]:
            backend._synced = True
            backend._items = [_item("#1", title="Freshly synced")]
            return {"refreshed": 1, "reconciled": 0, "pending_mutations": 0, "rejected_mutations": 0}

        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github", side_effect=_do_refresh)
        out = Output()

        result = operations.list_items(output=out)

        refresh_mock.assert_called_once()
        assert result["count"] == 1
        items = result["items"]
        assert isinstance(items, list)
        first_item = items[0]
        assert isinstance(first_item, dict)
        assert first_item["title"] == "Freshly synced"
        assert not any(_EMPTY_CACHE_MARKER in w for w in _warnings(result))
