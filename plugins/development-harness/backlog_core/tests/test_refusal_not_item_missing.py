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

from typing import TYPE_CHECKING

import pytest
from github import GithubException

from backlog_core import gh_client, operations
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    GitHubUnavailableError,
    GraphQLUnavailableError,
    ItemNotFoundError,
    Output,
    ReconcileRequest,
    ReconcileResult,
    ViewEnrichmentResult,
    ViewItemResult,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

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
        mocker.patch.object(
            operations,
            "view_enrich_from_github",
            return_value=ViewEnrichmentResult(
                enriched=False, attempted=True, unavailable_reason="GitHub lookup failed (network error)"
            ),
        )
        out = Output()

        operations.view_item("#519", output=out)

        assert any(w.startswith("backend unreachable — GitHub lookup failed (network error)") for w in out.warnings)

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

    def test_nothing_attempted_emits_no_warning_or_degradation_signal(self, mocker: MockerFixture) -> None:
        """ "Nothing was tried" must not render identically to "the backend refused us".

        A cached item with no resolvable identifier (no issue number, no issue
        ref) and a title selector with ``refresh=True`` reaches the live-check
        branch, but ``_live_lookup_id`` returns ``None`` -- no lookup is ever
        made. Neither the "backend unreachable" prose warning nor the
        ``status_source``/``unavailable_capabilities`` degradation fields (#3546)
        may fire for a call that never attempted anything.
        """
        _patch_view_backend(mocker, [_item("", title="Untracked cached title")])
        enrich_mock = mocker.patch.object(operations, "view_enrich_from_github")

        result = operations.view_item("Untracked cached title", refresh=True, output=Output())

        enrich_mock.assert_not_called()
        assert result.warnings == []
        assert result.status_source == "cache"
        assert result.unavailable_capabilities == []


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
