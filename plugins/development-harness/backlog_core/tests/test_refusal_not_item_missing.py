"""Tests that a refused query never reports itself as a missing or empty backlog.

Two reads told the same lie in a sandbox that serves REST but rejects GraphQL.
``backlog view --selector "#519"`` raised ``ItemNotFoundError`` for an issue that
exists, because ``view_enrich_from_github`` returned ``False`` for the refusal and
``view_item`` reads ``False`` as "no such item". ``backlog list`` reported
``count: 0`` against a real backlog, because a cache that had never synced is
shaped exactly like an empty one.

Neither read is made fatal here. A cached record still answers a view, and a list
still renders. What changes is that the answer names its own limits.

A third read told a quieter version of the same lie: ``view_enrich_from_github``
folded a genuine failure (network error, 500, rate limit) into the identical
``False`` a missing token produces (#3546), so a real outage rendered exactly like
"GitHub is not configured here". Only the actually-benign case — no
``GITHUB_TOKEN`` configured at all — keeps that ``False``/local-fallback behaviour
now; a genuine failure propagates as ``GitHubUnavailableError`` instead, which
``view_item``'s existing ``except BackendUnavailableError`` clause already catches.

A fourth read told a narrower version of the same lie: the #3546 fix's own
``_is_not_found_error`` helper matched any 'could not resolve'/'not found'
text, so GitHub's GraphQL error for an inaccessible or incorrect repository
('Could not resolve to a Repository with the name ...') was misclassified as
the requested issue being not found (#3570 Finding). ``_is_not_found_error``
now only matches an error that specifically names the issue as unresolvable.

A fifth read told the same lie once more, this time triggered by naming: the
prior fix's 'issue' + not-found substring check still matched a
repository-not-found error whenever the repository or owner name itself
contained the literal substring "issue" (e.g. 'owner/issue-tracker'), because
it scanned the whole message rather than anchoring on the exact
issue-not-found form (#3570 Finding B). ``_is_not_found_error`` now matches
only the exact prefix ``_fetch_issue_graphql`` synthesizes, so no repository
or owner name can influence the result.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from github import GithubException

from backlog_core import gh_client, operations
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    CacheStateCorruptError,
    GitHubUnavailableError,
    GraphQLUnavailableError,
    ItemNotFoundError,
    Output,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    ViewItemResult,
)
from backlog_core.sync_state import SyncState, SyncStatus

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from pytest_mock import MockerFixture


_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``try_get_github`` returns."""

    full_name = "owner/repo"


def _item(issue: str, title: str = "An item") -> BacklogItem:
    """Build a minimal open backlog item carrying the given issue reference."""
    return BacklogItem(title=title, issue=issue, section="P1", status="status:in-progress")


class TestViewEnrichSurfacesTheRefusal:
    """``False`` from this function means "no such issue", so neither a refusal nor a
    genuine failure may return it."""

    def test_a_refusal_propagates(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        with pytest.raises(GraphQLUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")

    def test_a_generic_backlog_error_now_propagates_instead_of_hiding_as_false(self, mocker: MockerFixture) -> None:
        """A non-refusal failure must not read as "issue #519 does not exist"."""
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(gh_client, "_fetch_issue_graphql", side_effect=BacklogError("query rejected"))

        with pytest.raises(GitHubUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")

    def test_a_github_exception_now_propagates_instead_of_hiding_as_false(self, mocker: MockerFixture) -> None:
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=GithubException(status=404, data={"message": "Not Found"}, headers={}),
        )

        with pytest.raises(GitHubUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")

    def test_a_try_get_github_failure_propagates_as_github_unavailable(self, mocker: MockerFixture) -> None:
        """A network error/500/rate limit resolving the repo itself is not a refusal either.

        This is the earlier of the two swallow points #3546 fixed: ``try_get_github``
        itself used to fold *any* ``GithubException`` from ``get_repo`` — not just a
        missing token — into the same ``None`` a missing token produces.
        """
        mocker.patch.object(
            gh_client, "try_get_github", side_effect=GitHubUnavailableError("GitHub repository unavailable")
        )

        with pytest.raises(GitHubUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")

    def test_an_unreachable_backend_still_returns_false(self, mocker: MockerFixture) -> None:
        """``try_get_github`` returning None is the no-token config state, not a failure."""
        mocker.patch.object(gh_client, "try_get_github", return_value=None)

        assert gh_client.view_enrich_from_github(ViewItemResult(), "519") is False

    def test_a_genuine_issue_not_found_still_returns_false(self, mocker: MockerFixture) -> None:
        """A reachable repository confirming the issue does not exist must not
        become GitHubUnavailableError — that reads as an outage, not an absence.

        Regression for #3570 Finding 1: the blanket ``except (BacklogError,
        GithubException)`` this file's own #3546 fix introduced converted
        ``_fetch_issue_graphql``'s genuine "Could not resolve to issue" 404
        equivalent into GitHubUnavailableError alongside every other failure,
        which made ``view_item("#999")`` report "GitHub is unavailable" for an
        issue that simply does not exist instead of raising ItemNotFoundError.
        """
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=BacklogError("GraphQL error: Could not resolve to issue #519"),
        )

        assert gh_client.view_enrich_from_github(ViewItemResult(), "519") is False

    def test_a_repository_not_found_error_now_propagates_instead_of_becoming_item_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """An inaccessible/nonexistent repository is not a missing-issue answer.

        Regression for #3570 Finding: ``_is_not_found_error`` matched any
        'could not resolve'/'not found' text, so GitHub's actual GraphQL error
        for an inaccessible or incorrect repository — 'Could not resolve to a
        Repository with the name ...' (verified against
        https://github.com/cli/cli/issues/3591) — was misclassified as the
        issue itself being not found. That made ``view_item("#N")`` raise
        ItemNotFoundError for the issue instead of preserving the
        repository/access failure as GitHubUnavailableError.
        """
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=BacklogError("GraphQL error: Could not resolve to a Repository with the name 'owner/repo'."),
        )

        with pytest.raises(GitHubUnavailableError):
            gh_client.view_enrich_from_github(ViewItemResult(), "519")


class _LiveGitHubBackend:
    """Backend stand-in whose ``view_enrich_from_github`` delegates to the real
    ``gh_client.view_enrich_from_github`` (unlike ``_ViewBackend`` below, which
    is patched directly at the ``operations`` boundary) — used to prove the
    not-found detection propagates correctly end-to-end through ``view_item``.
    """

    issue_id_type = "int"
    supports_batch_status_fetch = False

    def list_work_items(self) -> list[BacklogItem]:
        return []

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        return gh_client.view_enrich_from_github(result, issue_num, repo)


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

    def test_a_plain_lookup_failure_names_unreachable_backend_and_possible_causes(self, mocker: MockerFixture) -> None:
        _patch_view_backend(mocker, [_item("#519", title="Cached title")])
        mocker.patch.object(operations, "view_enrich_from_github", return_value=False)
        out = Output()

        operations.view_item("#519", output=out)

        assert any(
            w.startswith("backend unreachable — GitHub lookup failed (")
            and "authentication failure" in w
            and "issue not found" in w
            for w in out.warnings
        )

    def test_a_genuinely_nonexistent_issue_on_a_reachable_repo_raises_not_found(self, mocker: MockerFixture) -> None:
        """End-to-end regression for #3570 Finding 1.

        Unlike ``test_a_genuinely_absent_item_still_reports_not_found`` above
        (which patches ``operations.view_enrich_from_github`` directly and so
        never exercises the not-found detection itself), this test runs the
        real ``gh_client.view_enrich_from_github`` chain — a reachable
        repository whose GraphQL issue lookup genuinely fails to resolve —
        through ``view_item`` and asserts the result is ``ItemNotFoundError``,
        not ``GitHubUnavailableError``.
        """
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_LiveGitHubBackend()))
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=BacklogError("GraphQL error: Could not resolve to issue #999"),
        )

        with pytest.raises(ItemNotFoundError):
            operations.view_item("#999", output=Output())

    def test_a_repository_not_found_error_raises_github_unavailable_not_item_not_found(
        self, mocker: MockerFixture
    ) -> None:
        """End-to-end regression for #3570 Finding.

        Mirrors ``test_a_genuinely_nonexistent_issue_on_a_reachable_repo_raises_not_found``
        above, but with GitHub's actual GraphQL error text for an inaccessible
        or incorrect repository — 'Could not resolve to a Repository with the
        name ...' (verified against https://github.com/cli/cli/issues/3591) —
        instead of the issue-specific not-found message. Asserts the result is
        ``GitHubUnavailableError``, not ``ItemNotFoundError``: the repository
        being unresolvable is not the same failure as the issue being absent,
        and must not report the issue as missing.
        """
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_LiveGitHubBackend()))
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=BacklogError("GraphQL error: Could not resolve to a Repository with the name 'owner/repo'."),
        )

        with pytest.raises(GitHubUnavailableError):
            operations.view_item("#999", output=Output())

    def test_a_repository_named_with_issue_substring_raises_github_unavailable(self, mocker: MockerFixture) -> None:
        """End-to-end regression for #3570 Finding B.

        Mirrors ``test_a_repository_not_found_error_raises_github_unavailable_not_item_not_found``
        above, but the unresolvable repository's name itself contains the
        literal substring "issue" (``owner/issue-tracker``). A predicate that
        scans the whole error message for 'issue' alongside a not-found
        phrase would misclassify this as the requested issue being absent;
        the exact-prefix match must not be swayed by the repository's name.
        Asserts the result is ``GitHubUnavailableError``, not
        ``ItemNotFoundError``.
        """
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_LiveGitHubBackend()))
        mocker.patch.object(gh_client, "try_get_github", return_value=_Repo())
        mocker.patch.object(
            gh_client,
            "_fetch_issue_graphql",
            side_effect=BacklogError(
                "GraphQL error: Could not resolve to a Repository with the name 'owner/issue-tracker'."
            ),
        )

        with pytest.raises(GitHubUnavailableError):
            operations.view_item("#999", output=Output())


class _CacheBackend:
    """Backend stub whose cache is fed by an external provider.

    Deliberately does not implement ``SnapshotCheckpointProvider`` or
    ``SnapshotCompletenessProvider`` -- it satisfies only ``SyncProvider``,
    exactly as before A4. ``supports_cached_listing = True`` now flows
    through to the ``from_cache`` response bit, but A4's fail-safe gate
    never activates for this stub because it can't report checkpoint/skip
    state, matching the real backend's own docstring rationale for keeping
    those two protocols separate from ``SyncProvider``.
    """

    supports_batch_status_fetch = False
    supports_cached_listing = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def has_pending_writes(self) -> bool:
        return False

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Satisfy the ``SyncProvider`` protocol; never called by ``list_items``."""
        raise NotImplementedError


class _NativeBackend:
    """Backend stub that owns its own storage, with no provider to lag behind."""

    supports_batch_status_fetch = False
    supports_cached_listing = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def has_pending_writes(self) -> bool:
        return False


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
    supports_cached_listing = True

    def __init__(self, items: list[BacklogItem], *, synced: bool) -> None:
        self._items = items
        self._synced = synced
        self.reconcile_requests: list[ReconcileRequest] = []

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def has_synced_snapshot(self) -> bool:
        return self._synced

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Record a successful reconciliation and establish the checkpoint."""
        self.reconcile_requests.append(request)
        self._synced = True
        return ReconcileResult()


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
            operations, "refresh_local_cache_from_github", side_effect=BackendUnavailableError("no token configured")
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

    def test_labelled_cold_cache_establishes_one_global_checkpoint(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))

        operations.list_items(label="status:in-progress", output=Output())
        operations.list_items(label="status:in-progress", output=Output())

        assert len(backend.reconcile_requests) == 1
        assert backend.reconcile_requests[0].label == ""
        assert backend.reconcile_requests[0].apply_local_patches is False

    @pytest.mark.parametrize("failure", [OSError("cache is read-only"), CacheStateCorruptError("invalid cache state")])
    def test_cache_io_failure_withholds_unconfirmed_listing_by_default(
        self, mocker: MockerFixture, failure: OSError | CacheStateCorruptError
    ) -> None:
        backend = _CheckpointedBackend([_item("#1")], synced=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "refresh_local_cache_from_github", side_effect=failure)
        out = Output()

        result = operations.list_items(output=out)

        assert result["items"] is None
        assert result["count"] is None
        assert any(str(failure) in warning for warning in out.warnings)

    def test_undocumented_value_error_propagates_and_releases_claim(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([_item("#1")], synced=False)
        state = SyncState()
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "get_sync_state", return_value=state)
        mocker.patch.object(operations, "refresh_local_cache_from_github", side_effect=ValueError("programming error"))

        with pytest.raises(ValueError, match="programming error"):
            operations.list_items(output=Output())

        assert state.status == SyncStatus.IDLE

    def test_successful_read_through_replaces_prior_failure_state(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([_item("#1")], synced=False)
        state = SyncState(status=SyncStatus.OFFLINE, last_error="offline", offline_reason="no token", retry_count=2)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "get_sync_state", return_value=state)

        operations.list_items(output=Output())

        assert state.status == SyncStatus.IDLE
        assert state.last_success_at is not None
        assert state.completed_at is not None
        assert state.completed_at == state.last_success_at
        assert state.started_at is not None
        assert state.started_at < state.completed_at
        assert state.last_error == ""
        assert state.offline_reason == ""
        assert state.retry_count == 0

    def test_two_overlapping_cold_cache_calls_reconcile_exactly_once(self, mocker: MockerFixture) -> None:
        backend = _CheckpointedBackend([_item("#1")], synced=False)
        state = SyncState()
        refresh_entered = Event()
        release_refresh = Event()
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "get_sync_state", return_value=state)

        def _blocked_refresh(*_args: object, **_kwargs: object) -> dict[str, int]:
            refresh_entered.set()
            assert release_refresh.wait(timeout=2)
            backend._synced = True
            return {"refreshed": 1}

        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github", side_effect=_blocked_refresh)

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(operations.list_items, output=Output())
            assert refresh_entered.wait(timeout=2)
            second = executor.submit(operations.list_items, output=Output())
            try:
                second.result(timeout=1)
            finally:
                release_refresh.set()
            first.result(timeout=2)

        refresh_mock.assert_called_once()


def _snapshot(*, items: list[ProviderItem] | None = None, started_at: str = "2026-08-12T01:00:00Z") -> ProviderSnapshot:
    return ProviderSnapshot(items=items or [], sync_started_at=started_at, pages_fetched=1)


class TestListingProvenance:
    """Fail-safe, two-bit provenance on list_items() (A-critique.md Sec 4, ALT-2/ALT-4).

    Uses a real ``GitHubBackend``/``FileCache`` pair (mirroring
    ``tests_backlog/test_github_reconcile_checkpoint.py``'s pattern) rather
    than the plain stubs above, since these reproduce the actual write-side
    (A1 checkpoint honesty) plus read-side (A4 provenance) interaction.
    """

    def test_a_label_scoped_empty_reconcile_withholds_cached_result_after_refresh_failure(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """A-critique.md Sec 3.1's exact reproduction: a label-scoped reconcile that
        durably observes zero items keeps its checkpoint honestly unset. When
        the implicit repair attempt fails, the default fail-safe contract still
        withholds that cached result with explicit warnings."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(return_value=_snapshot())
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, label="nonexistent-label"))
        assert cache._get_snapshot_checkpoint() is None  # A1: still honestly never-synced

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(
            operations, "refresh_local_cache_from_github", side_effect=BackendUnavailableError("offline")
        )

        result = operations.list_items(output=Output())

        assert result["items"] is None
        assert result["count"] is None
        assert result["from_cache"] is True
        assert any(_EMPTY_CACHE_MARKER in w for w in _warnings(result))

    def test_a_label_scoped_empty_reconcile_serves_items_when_allow_cached(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """The same low-confidence state, opted into explicitly."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(return_value=_snapshot())
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INCREMENTAL, label="nonexistent-label"))

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(
            operations, "refresh_local_cache_from_github", side_effect=BackendUnavailableError("offline")
        )

        result = operations.list_items(allow_cached=True, output=Output())

        assert result["items"] == []
        assert result["count"] == 0
        assert result["from_cache"] is True

    def test_a_cold_cache_with_pending_writes_reports_both_bits_independently(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """The inverse of the warm+pending case above: a cold (never-synced) cache
        already holding a locally-queued mutation. Approach A's own Sec 6.5 folds
        this direction in; A4 must keep it correct alongside the warm direction
        that Approach A missed -- has_pending_writes is independent of
        from_cache/low_confidence in both directions, never derived from one
        another."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend.put_work_item(_item("#1", title="Queued locally"))
        assert cache._get_snapshot_checkpoint() is None  # still honestly never-synced

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})
        mocker.patch.object(
            operations, "refresh_local_cache_from_github", side_effect=BackendUnavailableError("offline")
        )

        result = operations.list_items(output=Output())

        # A failed implicit repair does not bypass the default fail-safe, while
        # has_pending_writes independently names the queued mutation.
        assert result["items"] is None
        assert result["count"] is None
        assert result["from_cache"] is True
        assert result["has_pending_writes"] is True

    def test_a_synced_cache_with_pending_writes_reports_the_pending_writes_bit(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """A-critique.md Sec 4 ALT-4: a fully-synced cache holding a locally-queued
        mutation must not be reported as unqualified-confident -- has_pending_writes
        is a bit independent of from_cache/low_confidence, and this case (warm
        checkpoint + queued item) is exactly the one Approach A's original design
        missed (it only noticed the inverse: a cold cache with queued items)."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(return_value=_snapshot())
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))  # unlabeled -> warm checkpoint
        assert cache._get_snapshot_checkpoint() is not None

        backend.put_work_item(_item("#1", title="Queued locally"))

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        result = operations.list_items(output=Output())

        # Warm + no skipped snapshots => high confidence => items served normally,
        # but has_pending_writes still names the locally-queued mutation.
        assert result["items"] is not None
        assert result["count"] == 1
        assert result["from_cache"] is True
        assert result["has_pending_writes"] is True

    def test_an_honest_empty_checkpoint_does_not_warn_or_withhold_items(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """The legitimate-zero case (post-A1): an unlabeled reconcile against a
        genuinely empty repo produces a durable, honest checkpoint. A later
        listing must serve it normally -- no warning, no withheld items."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(return_value=_snapshot())
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))
        assert cache._get_snapshot_checkpoint() is not None

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))

        result = operations.list_items(output=Output())

        assert result["items"] == []
        assert result["count"] == 0
        assert not any(_EMPTY_CACHE_MARKER in w for w in _warnings(result))
        assert result["from_cache"] is True
        assert result["has_pending_writes"] is False

    def test_a_warm_checkpoint_over_skipped_snapshots_withholds_items(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """A-critique.md Sec 2.5/Sec 3.2 (wired in via A2's WorkItemSnapshotBatch.skipped):
        a warm checkpoint over a partial/corrupted snapshot set must be treated as
        low-confidence too, exactly like a never-synced cache, even though
        has_synced_snapshot() alone reports True."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(
            return_value=_snapshot(items=[_provider_item("#1", "Issue 1"), _provider_item("#2", "Issue 2")])
        )
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))
        assert cache._get_snapshot_checkpoint() is not None

        # Corrupt one of the two snapshot files the reconcile just wrote.
        items_root = tmp_path / "items" / "issues"
        corrupt_files = sorted(items_root.glob("*.yaml"))
        assert corrupt_files
        corrupt_files[0].write_text("not: [valid, yaml:", encoding="utf-8")

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        mocker.patch.object(
            operations, "refresh_local_cache_from_github", side_effect=BackendUnavailableError("offline")
        )

        result = operations.list_items(output=Output())

        assert result["items"] is None
        assert result["count"] is None
        assert result["from_cache"] is True


def _provider_item(reference: str, title: str) -> ProviderItem:
    return ProviderItem(
        provider_id=f"node-{reference}",
        reference=reference,
        title=title,
        body="body",
        state="OPEN",
        labels=[],
        revision="rev-1",
    )


class TestRefreshEscalatesToFullOnSkipSignal:
    """Codex finding 2 (backlog #3546): ``list_items(refresh=True)`` must widen to a
    full provider refresh when the backend's most recent snapshot load flagged the
    on-disk cache incomplete -- an incremental refresh alone only asks GitHub for
    items changed since the checkpoint's watermark, so a locally-corrupted-but-
    upstream-unchanged item is never refetched and the low-confidence signal never
    clears. The common case (no skip signal) must keep its existing incremental
    behavior -- this is a narrow escalation, not a blanket change to every
    ``refresh=True`` call.
    """

    def test_a_refresh_over_a_corrupted_snapshot_escalates_to_full_refresh(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(
            return_value=_snapshot(items=[_provider_item("#1", "Issue 1"), _provider_item("#2", "Issue 2")])
        )
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))
        assert cache._get_snapshot_checkpoint() is not None

        # Corrupt one of the two snapshot files the reconcile just wrote -- the same
        # unreadable-but-present case the warm-checkpoint withholding test above uses.
        items_root = tmp_path / "items" / "issues"
        corrupt_files = sorted(items_root.glob("*.yaml"))
        assert corrupt_files
        corrupt_files[0].write_text("not: [valid, yaml:", encoding="utf-8")

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github")

        operations.list_items(refresh=True, output=Output())

        refresh_mock.assert_called_once()
        assert refresh_mock.call_args.kwargs["full_refresh"] is True

    def test_a_refresh_with_no_skip_signal_stays_incremental(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """The regression guard: a clean warm checkpoint must not be swept into the
        finding-2 escalation just because ``refresh=True`` was passed."""
        cache = FileCache(tmp_path)
        backend = GitHubBackend(cache=cache)
        backend._fetch_snapshot = MagicMock(
            return_value=_snapshot(items=[_provider_item("#1", "Issue 1"), _provider_item("#2", "Issue 2")])
        )
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.INITIAL))
        assert cache._get_snapshot_checkpoint() is not None

        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        refresh_mock = mocker.patch.object(operations, "refresh_local_cache_from_github")

        operations.list_items(refresh=True, output=Output())

        refresh_mock.assert_called_once()
        assert refresh_mock.call_args.kwargs["full_refresh"] is False
