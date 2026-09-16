"""backlog_list offline/sync-state divergence signal -- unit tests.

All symbols are now implemented; these tests verify production behaviour.

Behaviors covered (mapped to requirement 5):

5a. backlog_list full response (count_only=False) -- offline state -> sync_state block present
    + warnings non-empty.
5b. backlog_list count_only=True -- offline state -> sync_state + warnings present (not bare
    {"count": N}).
5c. backlog_list count_only=True -- IDLE state, genuine zero matches from populated cache ->
    bare {"count": 0} with NO sync_state block.  This distinguishes the silent-failure case
    from a legitimate empty result.
5d. backlog_list full response -- RUNNING state (sync in progress) -> sync_state block present.
5e. backlog_list full response -- IDLE state (healthy, populated cache) -> NO sync_state block
    (regression guard: normal response shape must not grow).
5f. backlog_list count_only=True -- RUNNING state -> sync_state + warnings present.

Design references:
  Section 7.2 -- backlog_list offline response shape
  Section 7.3 -- count_only path must carry sync_state when not IDLE
  Section 8.3 -- sync_state key present only when status != IDLE
  silent-failure-prevention.md -- reads that hit an offline server must not return count:0 silently.

Source: design doc sections 7, 8.3, 10.1 (Required test categories).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest

from backlog_core import operations
from backlog_core.models import BackendUnavailableError, BacklogItem, ReconcileRequest, ReconcileResult
from backlog_core.sync_state import SyncStatus, get_sync_state, reset_sync_state

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from backlog_core.models import IssueStatus
    from backlog_core.operations import BacklogListItem, ListItemsResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_list_items_result(items: list[BacklogListItem]) -> ListItemsResult:
    """Return a minimal list_items result dict with the given items.

    ``from_cache``/``has_pending_writes`` (backlog #3546 task A4) are set to
    their most boring values here -- these tests exercise sync_state
    divergence signalling, not listing provenance, so a fixed ``False``/
    ``False`` keeps that concern out of this helper's callers.
    """
    return {
        "items": items,
        "count": len(items),
        "from_cache": False,
        "has_pending_writes": False,
        "messages": [],
        "warnings": [],
        "errors": [],
    }


def _item(issue: str, title: str = "An item") -> BacklogItem:
    """Build a minimal open backlog item carrying the given issue reference."""
    return BacklogItem(title=title, issue=issue, section="P1", status="status:in-progress")


class _StatusRefusedBackend:
    """Backend stub whose batch status fetch genuinely fails (real ``BackendUnavailableError``).

    Unlike ``mock_list_items_empty``/``mock_list_items_populated`` (which patch
    ``dh_core.operations.list_items`` wholesale and never run the real function
    body), this stub is installed via ``operations.get_config`` so the real
    ``list_items``/``batch_fetch_statuses`` code path executes — including the
    ``except BackendUnavailableError`` clause that calls ``out.warn()`` — which
    is exactly the code path the wholesale-patch pattern does not exercise
    (B-critique.md §4.5).
    """

    supports_batch_status_fetch = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        raise BackendUnavailableError("simulated GitHub batch status refusal")


class _NoReconcileBackend:
    """Backend stub with no ``reconcile()`` — not a ``SyncProvider``.

    A ``refresh=True`` call against this backend takes
    ``refresh_local_cache_from_github``'s "Active backend does not support
    reconciliation." branch, which calls ``out.info()`` on a genuinely healthy
    read (B-critique.md §2.3's own cited example of the healthy-path
    ``out.info()`` case).
    """

    supports_batch_status_fetch = False

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return self._items


class _DegradedReconcileBackend(_NoReconcileBackend):
    """SyncProvider stub returning every caller-relevant degradation counter."""

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        return ReconcileResult(fetched_items=1, failures=2, pending_mutations=3, rejected_mutations=4)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def reset_state() -> None:
    """Reset SyncState before each test.

    Must be async so the asyncio.Lock() is bound to the running event loop.
    The ``await asyncio.sleep(0)`` ensures the loop is live before the lock
    is created -- see design doc Risk #2.
    """
    await asyncio.sleep(0)
    reset_sync_state()


@pytest.fixture
def mock_list_items_empty(mocker: MockerFixture) -> None:
    """Patch the server-bound list operation to return an empty cache."""
    mocker.patch("dh_core.operations.list_items", return_value=_make_list_items_result([]))


@pytest.fixture
def mock_list_items_populated(mocker: MockerFixture) -> None:
    """Patch the server-bound list operation to return a non-empty cache (3 items)."""
    items: list[BacklogListItem] = [
        {
            "issue": "#1",
            "title": "Alpha",
            "status": "needs-grooming",
            "section": "P1",
            "plan": "",
            "type": "",
            "topic": "",
        },
        {
            "issue": "#2",
            "title": "Beta",
            "status": "needs-grooming",
            "section": "P2",
            "plan": "",
            "type": "",
            "topic": "",
        },
        {
            "issue": "#3",
            "title": "Gamma",
            "status": "needs-grooming",
            "section": "P0",
            "plan": "",
            "type": "",
            "topic": "",
        },
    ]
    mocker.patch("dh_core.operations.list_items", return_value=_make_list_items_result(items))


@pytest.fixture
def mock_probe_not_checked(mocker: MockerFixture) -> None:
    """Patch _probe_backend_status to return NOT_CHECKED (no GitHub call)."""
    from backlog_core.models import BackendAvailability, BackendStatus

    status = BackendStatus(availability=BackendAvailability.NOT_CHECKED)
    mocker.patch("backlog_core.server._probe_backend_status", return_value=status)


# ---------------------------------------------------------------------------
# Behaviour 5a -- Full response, offline -> sync_state + warnings
# ---------------------------------------------------------------------------


class TestBacklogListFullResponseOfflineState:
    """backlog_list full response carries sync_state block when OFFLINE."""

    async def test_offline_state_adds_sync_state_block_to_full_response(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """sync_state block is present in full backlog_list response when OFFLINE.

        Design section 7.2: 'sync_state key: present only when SyncState.status != IDLE'.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list()

        assert "sync_state" in response, (
            "backlog_list must include 'sync_state' in the full response when status is OFFLINE. "
            "Silent failure: returning items without surfacing offline state misleads the caller."
        )
        sync_block = cast("dict[str, object]", response["sync_state"])
        assert sync_block.get("status") == "offline", (
            f"sync_state.status must be 'offline'. Got {sync_block.get('status')!r}."
        )
        assert sync_block.get("offline_reason"), "sync_state.offline_reason must be non-empty when OFFLINE."

    async def test_offline_warnings_list_is_non_empty_in_full_response(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """warnings list has at least one entry describing the offline state.

        Design section 7.2: 'warnings list always gets an entry when offline/error'.
        silent-failure-prevention.md: reads that hit offline must not silently return count:0.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list()

        warnings = cast("list[str]", response.get("warnings", []))
        assert warnings, (
            "backlog_list must populate the 'warnings' list when status is OFFLINE. "
            "An empty warnings list with count:0 is the silent-failure anti-pattern."
        )
        offline_mentioned = any("offline" in w.lower() or "stale" in w.lower() or "sync" in w.lower() for w in warnings)
        assert offline_mentioned, f"No warning mentions the offline/stale-cache condition. Got: {warnings}"

    async def test_error_state_adds_sync_state_block_to_full_response(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """sync_state block is present when status is ERROR (exhausted retries).

        ERROR state (retries exhausted) is the other non-IDLE terminal state that
        indicates stale cache.  It must also surface in the response.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.ERROR
        state.last_error = "GitHub 503 after 3 retries"

        response = await backlog_list()

        assert "sync_state" in response, "backlog_list must include 'sync_state' when status is ERROR."
        assert response.get("warnings"), "warnings must be non-empty when status is ERROR."

    async def test_running_state_adds_sync_state_block_to_full_response(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """sync_state block is present when a sync is currently RUNNING (5d).

        A running sync means the cache may be mid-refresh; callers benefit from
        knowing so they can decide whether to wait or proceed with stale data.
        Design section 8.3: sync_state present when status != IDLE.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.RUNNING

        response = await backlog_list()

        assert "sync_state" in response, "backlog_list must include 'sync_state' when status is RUNNING."


# ---------------------------------------------------------------------------
# Behaviour 5b -- count_only=True, offline -> sync_state + warnings
# ---------------------------------------------------------------------------


class TestBacklogListCountOnlyOfflineState:
    """count_only=True must not return a bare dict when status is not IDLE."""

    async def test_count_only_offline_returns_sync_state_block(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """count_only=True while OFFLINE must include sync_state (not bare count).

        Design section 7.3: 'count_only is never allowed to return a bare {"count": N} dict
        when the sync state is anything other than IDLE and SUCCESSFUL'.

        Current code (server.py:1781) returns {"count": total} bare -- this is the
        silent-failure locus the design identifies.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list(count_only=True)

        assert "count" in response, "count_only response must still include 'count'."
        assert "sync_state" in response, (
            "count_only=True must NOT return a bare {'count': N} when OFFLINE. "
            "The caller cannot distinguish 'offline, cache empty' from 'genuinely zero items'. "
            "This is the core silent-failure anti-pattern from design section 7.3."
        )

    async def test_count_only_offline_returns_non_empty_warnings(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """count_only=True while OFFLINE populates warnings."""
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list(count_only=True)

        warnings = response.get("warnings", [])
        assert warnings, (
            "count_only=True must include a non-empty 'warnings' list when OFFLINE. "
            "A bare {'count': 0} with no warning is the silent-failure this feature fixes."
        )

    async def test_count_only_error_returns_sync_state_block(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """count_only=True while ERROR (retries exhausted) must include sync_state."""
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.ERROR
        state.last_error = "GitHub 503 after 3 retries"

        response = await backlog_list(count_only=True)

        assert "sync_state" in response, "count_only=True must include sync_state when status is ERROR."

    async def test_count_only_running_returns_sync_state_block(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """count_only=True while RUNNING must include sync_state (5f)."""
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.RUNNING

        response = await backlog_list(count_only=True)

        assert "sync_state" in response, "count_only=True must include sync_state when status is RUNNING."


# ---------------------------------------------------------------------------
# Behaviour 5c -- count_only=True, IDLE, zero matches -> NO sync_state (regression guard)
# ---------------------------------------------------------------------------


class TestBacklogListCountOnlyIdleState:
    """IDLE state with genuine zero matches must NOT add sync_state (5c).

    This distinguishes 'offline/stale cache returns 0' from 'healthy search found 0'.
    The design explicitly requires: sync_state key omitted when status == IDLE.
    """

    async def test_count_only_idle_zero_matches_returns_bare_count(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """count_only=True + IDLE + empty cache -> {"count": 0} with no sync_state.

        This is the regression guard: a healthy zero-match must not grow a sync_state
        block.  The sync_state block is reserved for non-IDLE states that indicate
        stale or incomplete data.

        Kept as-is per B-critique.md §4.5: ``sync_state`` is a sync-lifecycle key, not
        a result-size key — that is the actual reason this stays green (the mocked
        ``list_items`` result hard-codes empty messages/warnings/errors, so this test
        was never exercising, and does not need to exercise, the count_only
        warnings/errors merge added for #3546 B4;
        ``test_count_only_surfaces_a_genuine_degradation_warning`` below covers that).
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        assert state.status == SyncStatus.IDLE  # precondition: verify fixture set IDLE

        response = await backlog_list(count_only=True)

        assert response.get("count") == 0
        assert "sync_state" not in response, (
            "count_only=True with IDLE status must NOT include 'sync_state'. "
            "Adding it to a healthy zero-match response bloats the normal-case shape. "
            "sync_state is reserved for non-IDLE states only (design section 8.3)."
        )

    async def test_full_response_idle_no_sync_state_block(
        self, reset_state: None, mock_list_items_populated: None, mock_probe_not_checked: None
    ) -> None:
        """Full backlog_list response with IDLE state must NOT include sync_state (5e).

        Regression guard for the normal-case response shape.  Adding sync_state to
        a healthy response wastes context window and creates caller confusion.

        Kept as-is per B-critique.md §4.5: sync_state is sync-lifecycle, not
        result-size — unaffected by the count_only warnings/errors merge (#3546 B4).
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        assert state.status == SyncStatus.IDLE  # precondition: verify fixture set IDLE

        response = await backlog_list()

        assert "sync_state" not in response, (
            "backlog_list must NOT include 'sync_state' in the normal IDLE response. "
            "sync_state is only emitted when status != IDLE (design section 8.3)."
        )

    async def test_count_only_idle_populated_cache_zero_search_match_no_sync_state(
        self, reset_state: None, mock_list_items_populated: None, mock_probe_not_checked: None
    ) -> None:
        """A search that matches 0 of N healthy cached items must NOT set sync_state.

        This distinguishes 'cache is empty / offline' from 'searched N items, matched 0'.
        Design section 8.3: sync_state is about sync state, not search result size.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        assert state.status == SyncStatus.IDLE  # precondition: verify fixture set IDLE

        response = await backlog_list(search="zzz_no_match_xyz_unique_string_9999", count_only=True)

        assert "sync_state" not in response, (
            "A genuine zero-match against a healthy cache must NOT include sync_state. "
            "Only offline/error/running state adds sync_state -- not the search result."
        )


# ---------------------------------------------------------------------------
# #3546 B4 -- count_only must surface operations-layer output, without
# leaking routine info() prose into the documented bare-count shape.
# ---------------------------------------------------------------------------


class TestCountOnlyPreservesOperationsLayerOutput:
    """``count_only`` must surface a genuine operations-layer degradation
    (``out.warnings``/``out.errors``) while keeping the documented bare-count
    shape on a healthy call that only produced routine ``out.info()`` prose.

    Unlike the fixtures above, these tests do not patch
    ``dh_core.operations.list_items`` wholesale — B-critique.md §4.5 found
    that pattern is exactly why the count_only/out-merge bug went
    unexercised, since the mock ignores the ``output=`` kwarg entirely and
    the real ``list_items`` body (where ``out.warn()``/``out.info()`` are
    actually called) never runs. Instead ``operations.get_config`` is
    patched to a stub backend, so the real ``list_items`` (and, in the
    second test, ``refresh_local_cache_from_github``) code path executes.
    """

    async def test_count_only_surfaces_a_genuine_degradation_warning(
        self, reset_state: None, mock_probe_not_checked: None, mocker: MockerFixture
    ) -> None:
        """A real BackendUnavailableError from batch_fetch_statuses (B1's swallow-point
        fix) reaches out.warn() and must now be visible on the count_only response."""
        from backlog_core.server import backlog_list

        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_StatusRefusedBackend([_item("#1")]))
        )

        response = cast("dict[str, object]", await backlog_list(count_only=True))

        assert response.get("count") == 1
        warnings = cast("list[str]", response.get("warnings", []))
        assert any("Live status unavailable" in w for w in warnings), (
            f"count_only must surface the operations-layer degradation warning (#3546 B4). Got response: {response!r}"
        )

    async def test_count_only_healthy_refresh_stays_bare_despite_info_messages(
        self, reset_state: None, mock_probe_not_checked: None, mocker: MockerFixture
    ) -> None:
        """A healthy refresh populates out.info() (routine reconcile prose) but that
        must NOT leak into count_only's documented bare-count-only shape."""
        from backlog_core.server import backlog_list

        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_NoReconcileBackend([_item("#1")]))
        )

        response = cast("dict[str, object]", await backlog_list(refresh=True, count_only=True))

        assert response.get("count") == 1
        assert "messages" not in response, (
            "A healthy refresh's routine out.info() reconcile summary must not leak "
            f"into count_only's documented bare-count shape (#3546 B4). Got: {response!r}"
        )
        assert "warnings" not in response
        assert "errors" not in response

    async def test_count_only_refresh_surfaces_reconciliation_degradation(
        self, reset_state: None, mock_probe_not_checked: None, mocker: MockerFixture
    ) -> None:
        """A requested refresh must report incomplete reconciliation and queued mutations."""
        from backlog_core.server import backlog_list

        mocker.patch.object(
            operations, "get_config", return_value=mocker.Mock(backend=_DegradedReconcileBackend([_item("#1")]))
        )

        response = cast("dict[str, object]", await backlog_list(refresh=True, count_only=True))

        assert response.get("count") == 1
        assert "messages" not in response
        warnings = cast("list[str]", response.get("warnings", []))
        assert warnings == [
            (
                "Reconciled 1 provider item(s): 0 local updates, 0 patches, 0 no-ops, 2 failures, "
                "3 pending mutation(s), 4 rejected mutation(s)."
            )
        ]


# ---------------------------------------------------------------------------
# Behaviour 5 -- sync_state block shape validation
# ---------------------------------------------------------------------------


class TestSyncStateBlockShape:
    """When sync_state is present, it must contain the documented fields."""

    async def test_sync_state_block_contains_required_fields_when_offline(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """sync_state block in backlog_list response has the shape from design section 7.2."""
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list()

        sync_block = cast("dict[str, object]", response.get("sync_state", {}))
        required_sync_block_fields = {"status", "offline_reason", "last_success_at", "cache_warning"}
        missing = required_sync_block_fields - set(sync_block.keys())
        assert not missing, (
            f"sync_state block is missing required fields: {missing}. "
            "Design section 7.2 specifies: status, offline_reason, last_success_at, cache_warning."
        )

    async def test_sync_state_block_cache_warning_is_non_empty_when_offline(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """sync_state.cache_warning is a non-empty string when OFFLINE."""
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.OFFLINE
        state.offline_reason = "GITHUB_TOKEN not set"

        response = await backlog_list()

        sync_block = cast("dict[str, object]", response.get("sync_state", {}))
        assert sync_block.get("cache_warning"), (
            "sync_state.cache_warning must be a non-empty string when OFFLINE. "
            "Design section 7.2 specifies: 'serving stale cache -- backend sync failed'."
        )


# ---------------------------------------------------------------------------
# Behaviour 5g -- ERROR state warning must name last_error, not just offline_reason
# ---------------------------------------------------------------------------


class TestSyncStateBlockNamesErrorCause:
    """The injected warning must name the sync failure's cause, not just offline_reason.

    ERROR-state syncs (retries exhausted) set ``last_error``, not ``offline_reason`` --
    ``offline_reason`` is only ever populated for the OFFLINE (non-retryable) path. A
    warning built only from ``offline_reason`` is silently empty for every ERROR-state
    sync, so a caller reading the warning has no idea why the cache is stale.
    """

    async def test_error_state_warning_names_last_error_when_offline_reason_empty(
        self, reset_state: None, mock_list_items_empty: None, mock_probe_not_checked: None
    ) -> None:
        """The ERROR-state warning text names last_error, not a blank offline_reason.

        Design reference: sync_state.py SyncState.last_error is the field populated for
        ERROR; offline_reason stays "" on that path. The warning must still say why the
        cache is stale.
        """
        from backlog_core.server import backlog_list

        state = get_sync_state()
        state.status = SyncStatus.ERROR
        state.last_error = "boom"
        assert not state.offline_reason  # precondition: ERROR path leaves this empty

        response = await backlog_list()

        warnings = cast("list[str]", response.get("warnings", []))
        assert any("boom" in w for w in warnings), (
            f"No warning names the sync failure cause (last_error='boom'). Got: {warnings}. "
            "_build_sync_state_block() only reads sync_state.offline_reason, which the ERROR "
            "path never populates -- last_error is dropped."
        )
