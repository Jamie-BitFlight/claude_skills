"""Tests for BackendStatus model, probe_backend_status(), and backlog_list integration.

Covers:
- BackendAvailability enum members and serialisation (test cases 1-3)
- probe_backend_status() unit tests mocking GitHub operations (4-12)
- backlog_list response integration: "backend" key shape and existing key preservation (13-15)

No real network calls are made. GitHub API access is mocked via pytest monkeypatch and
unittest.mock.patch.

asyncio_mode = "auto" is set globally in pyproject.toml — no @pytest.mark.asyncio decorators.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from backlog_core.gh_client import probe_backend_status
from backlog_core.models import BackendAvailability, BackendStatus
from backlog_core.server import mcp
from github import GithubException

from tests.helpers import call_mcp_tool

# ---------------------------------------------------------------------------
# Helper: call a tool via in-memory FastMCP transport
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory transport and return parsed JSON.

    Delegates to tests.helpers.call_mcp_tool bound to this module's mcp server.
    """
    return await call_mcp_tool(mcp, tool_name, params)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestBackendAvailabilityEnum:
    """BackendAvailability has exactly 5 members with correct string values.

    Tests: BackendAvailability enum completeness and StrEnum serialisation.
    Why: Downstream consumers (MCP clients, docs) depend on these exact string
         values; adding or renaming members is a breaking API change.
    """

    def test_enum_has_exactly_five_members(self) -> None:
        """BackendAvailability defines exactly 5 availability states.

        Tests: BackendAvailability member count
        How: Assert len(BackendAvailability) == 5
        Why: Accidental member removal or addition changes the public contract
        """
        assert len(BackendAvailability) == 5

    def test_reachable_serialises_to_expected_string(self) -> None:
        """REACHABLE serialises to the string 'reachable'.

        Tests: BackendAvailability.REACHABLE value
        How: Assert str(BackendAvailability.REACHABLE) == 'reachable'
        Why: MCP responses embed these strings; clients match on exact values
        """
        assert BackendAvailability.REACHABLE == "reachable"

    def test_not_checked_serialises_to_expected_string(self) -> None:
        """NOT_CHECKED serialises to 'not_checked'.

        Tests: BackendAvailability.NOT_CHECKED value
        How: Direct equality against the expected literal string
        Why: Default state for unchecked probes must be distinguishable
        """
        assert BackendAvailability.NOT_CHECKED == "not_checked"

    def test_needs_authentication_serialises_to_expected_string(self) -> None:
        """NEEDS_AUTHENTICATION serialises to 'needs_authentication'.

        Tests: BackendAvailability.NEEDS_AUTHENTICATION value
        How: Direct equality against the expected literal string
        Why: Clients use this value to prompt token configuration
        """
        assert BackendAvailability.NEEDS_AUTHENTICATION == "needs_authentication"

    def test_rate_limited_serialises_to_expected_string(self) -> None:
        """RATE_LIMITED serialises to 'rate_limited'.

        Tests: BackendAvailability.RATE_LIMITED value
        How: Direct equality against the expected literal string
        Why: Clients use this to distinguish 403 rate-limit from auth failure
        """
        assert BackendAvailability.RATE_LIMITED == "rate_limited"

    def test_error_serialises_to_expected_string(self) -> None:
        """ERROR serialises to 'error'.

        Tests: BackendAvailability.ERROR value
        How: Direct equality against the expected literal string
        Why: Clients distinguish connection failures from auth and rate issues
        """
        assert BackendAvailability.ERROR == "error"

    def test_all_expected_members_present(self) -> None:
        """All five named members exist on the enum.

        Tests: BackendAvailability member presence
        How: Assert each member name is in BackendAvailability.__members__
        Why: Confirms no member was accidentally removed or renamed
        """
        expected = {"REACHABLE", "NOT_CHECKED", "NEEDS_AUTHENTICATION", "RATE_LIMITED", "ERROR"}
        assert expected == set(BackendAvailability.__members__)


class TestBackendStatusDefaults:
    """BackendStatus default construction produces a valid model with availability=NOT_CHECKED.

    Tests: BackendStatus default field values.
    Why: Server code constructs BackendStatus() without arguments as a safe
         initial state; callers must always get a well-formed object.
    """

    def test_default_availability_is_not_checked(self) -> None:
        """BackendStatus() defaults availability to NOT_CHECKED.

        Tests: BackendStatus.availability default
        How: Construct model with no args; check availability field
        Why: NOT_CHECKED signals that no probe was attempted yet
        """
        status = BackendStatus()
        assert status.availability == BackendAvailability.NOT_CHECKED

    def test_default_name_is_github(self) -> None:
        """BackendStatus() defaults name to 'GitHub'.

        Tests: BackendStatus.name default
        How: Construct model with no args; check name field
        Why: Clients display this name in status UI
        """
        status = BackendStatus()
        assert status.name == "GitHub"

    def test_default_open_count_is_none(self) -> None:
        """BackendStatus() defaults open_count to None.

        Tests: BackendStatus.open_count default
        How: Construct model; check open_count is None
        Why: None indicates counts were not fetched (not zero)
        """
        status = BackendStatus()
        assert status.open_count is None

    def test_default_total_count_is_none(self) -> None:
        """BackendStatus() defaults total_count to None.

        Tests: BackendStatus.total_count default
        How: Construct model; check total_count is None
        Why: Distinguishes 'not fetched' from 'zero issues'
        """
        status = BackendStatus()
        assert status.total_count is None

    def test_default_cache_open_count_is_zero(self) -> None:
        """BackendStatus() defaults cache_open_count to 0.

        Tests: BackendStatus.cache_open_count default
        How: Construct model; check cache_open_count == 0
        Why: Zero is safe when no local listing has run
        """
        status = BackendStatus()
        assert status.cache_open_count == 0

    def test_default_cache_total_count_is_zero(self) -> None:
        """BackendStatus() defaults cache_total_count to 0.

        Tests: BackendStatus.cache_total_count default
        How: Construct model; check cache_total_count == 0
        Why: Zero is safe when probe has not counted cache files
        """
        status = BackendStatus()
        assert status.cache_total_count == 0

    def test_default_last_sync_is_empty_string(self) -> None:
        """BackendStatus() defaults last_sync to ''.

        Tests: BackendStatus.last_sync default
        How: Construct model; check last_sync == ''
        Why: Empty string is the sentinel for 'never synced'
        """
        status = BackendStatus()
        assert status.last_sync == ""

    def test_default_error_is_empty_string(self) -> None:
        """BackendStatus() defaults error to ''.

        Tests: BackendStatus.error default
        How: Construct model; check error == ''
        Why: Empty string is the sentinel for 'no error'
        """
        status = BackendStatus()
        assert status.error == ""


class TestBackendStatusAllFieldsPopulated:
    """BackendStatus with all fields populated produces expected model_dump output.

    Tests: BackendStatus.model_dump() with fully populated fields.
    Why: Integration responses embed model_dump() output — keys and values
         must match exactly what consumers expect.
    """

    def test_model_dump_contains_all_expected_keys(self) -> None:
        """model_dump() includes all BackendStatus field names.

        Tests: BackendStatus.model_dump() key set
        How: Build a fully-populated model; check all keys present in dump
        Why: Missing keys break MCP clients that access fields by name
        """
        status = BackendStatus(
            name="GitHub",
            availability=BackendAvailability.REACHABLE,
            open_count=10,
            total_count=42,
            cache_open_count=7,
            cache_total_count=15,
            last_sync="2026-03-23T12:00:00Z",
            error="",
        )
        dumped = status.model_dump()
        expected_keys = {
            "name",
            "availability",
            "open_count",
            "total_count",
            "cache_open_count",
            "cache_total_count",
            "last_sync",
            "error",
        }
        assert expected_keys == set(dumped.keys())

    def test_model_dump_values_match_input(self) -> None:
        """model_dump() returns each field value as provided.

        Tests: BackendStatus.model_dump() value fidelity
        How: Construct with known values; assert each dumped value matches
        Why: Pydantic coercion could silently change values; this confirms parity
        """
        status = BackendStatus(
            name="GitHub",
            availability=BackendAvailability.REACHABLE,
            open_count=10,
            total_count=42,
            cache_open_count=7,
            cache_total_count=15,
            last_sync="2026-03-23T12:00:00Z",
            error="some warning",
        )
        dumped = status.model_dump()
        assert dumped["name"] == "GitHub"
        assert dumped["availability"] == "reachable"
        assert dumped["open_count"] == 10
        assert dumped["total_count"] == 42
        assert dumped["cache_open_count"] == 7
        assert dumped["cache_total_count"] == 15
        assert dumped["last_sync"] == "2026-03-23T12:00:00Z"
        assert dumped["error"] == "some warning"

    def test_model_dump_availability_serialises_to_string(self) -> None:
        """model_dump() serialises BackendAvailability enum to its string value.

        Tests: BackendStatus.model_dump() enum serialisation
        How: Populate availability; assert dumped value is a plain string
        Why: JSON serialisation requires strings, not enum instances
        """
        status = BackendStatus(availability=BackendAvailability.RATE_LIMITED)
        dumped = status.model_dump()
        assert dumped["availability"] == "rate_limited"
        assert isinstance(dumped["availability"], str)


# ---------------------------------------------------------------------------
# Probe unit tests — fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Probe unit tests — GITHUB_TOKEN not set
# ---------------------------------------------------------------------------


class TestProbeBackendStatusNoToken:
    """probe_backend_status returns NEEDS_AUTHENTICATION when GITHUB_TOKEN is absent.

    Tests: probe_backend_status() authentication gate.
    Why: Without a token, all GitHub operations are impossible — the probe
         must report this clearly so users know to configure credentials.
    """

    def test_no_token_returns_needs_authentication(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GITHUB_TOKEN absent -> availability=NEEDS_AUTHENTICATION.

        Tests: probe_backend_status() with no token
        How: Remove GITHUB_TOKEN env var; call probe; check availability
        Why: Correct classification prevents misleading 'ERROR' messages
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert result.availability == BackendAvailability.NEEDS_AUTHENTICATION

    def test_no_token_error_contains_github_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GITHUB_TOKEN absent -> error field contains 'GITHUB_TOKEN'.

        Tests: probe_backend_status() error message with no token
        How: Remove GITHUB_TOKEN; check result.error contains 'GITHUB_TOKEN'
        Why: Users need actionable error text pointing to the missing variable
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert "GITHUB_TOKEN" in result.error

    def test_no_token_uses_provider_status_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert result.cache_total_count == 0
        assert result.last_sync == ""


# ---------------------------------------------------------------------------
# Probe unit tests — token set, GitHub reachable
# ---------------------------------------------------------------------------


class TestProbeBackendStatusReachable:
    """probe_backend_status returns REACHABLE with counts when GitHub is accessible.

    Tests: probe_backend_status() happy path.
    Why: Reachable state with correct counts is the primary positive signal
         that the backend integration is working correctly.
    """

    def test_reachable_returns_reachable_availability(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Token set, GitHub reachable -> availability=REACHABLE.

        Tests: probe_backend_status() happy path availability
        How: Set token; mock try_get_github to return a repo; check availability
        Why: REACHABLE is the expected state when all conditions are met
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        mock_repo.open_issues_count = 5
        mock_issues = MagicMock()
        mock_issues.totalCount = 20
        mock_repo.get_issues.return_value = mock_issues

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.REACHABLE

    def test_reachable_returns_correct_open_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Token set, GitHub reachable -> open_count matches repo.open_issues_count.

        Tests: probe_backend_status() open_count extraction
        How: Mock repo.open_issues_count=5; verify result.open_count == 5
        Why: open_count is displayed in status output; wrong value misleads users
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        mock_repo.open_issues_count = 5
        mock_issues = MagicMock()
        mock_issues.totalCount = 20
        mock_repo.get_issues.return_value = mock_issues

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.open_count == 5

    def test_reachable_returns_correct_total_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Token set, GitHub reachable -> total_count matches repo.get_issues().totalCount.

        Tests: probe_backend_status() total_count extraction
        How: Mock get_issues().totalCount=20; verify result.total_count == 20
        Why: total_count is used to report all-time issue volume
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        mock_repo.open_issues_count = 5
        mock_issues = MagicMock()
        mock_issues.totalCount = 20
        mock_repo.get_issues.return_value = mock_issues

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.total_count == 20


# ---------------------------------------------------------------------------
# Probe unit tests — try_get_github returns None
# ---------------------------------------------------------------------------


class TestProbeBackendStatusGitHubUnreachable:
    """probe_backend_status returns ERROR when try_get_github returns None.

    Tests: probe_backend_status() when GitHub connection fails.
    Why: Token present but connection failing is a distinct state from no token;
         ERROR classification helps diagnose firewall or network issues.
    """

    def test_unreachable_returns_error_availability(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None -> availability=ERROR.

        Tests: probe_backend_status() with failed connection
        How: Set token; mock try_get_github to return None; check availability
        Why: ERROR distinguishes connection failure from auth failure
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        with patch("backlog_core.gh_client.try_get_github", return_value=None):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.ERROR

    def test_unreachable_error_field_is_populated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None -> error field is non-empty.

        Tests: probe_backend_status() error message on connection failure
        How: Mock try_get_github to return None; verify result.error is non-empty
        Why: Users need a diagnostic message when the connection fails
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        with patch("backlog_core.gh_client.try_get_github", return_value=None):
            result = probe_backend_status()

        assert result.error != ""


# ---------------------------------------------------------------------------
# Probe unit tests — rate limited (403 GithubException)
# ---------------------------------------------------------------------------


class TestProbeBackendStatusRateLimited:
    """probe_backend_status returns RATE_LIMITED when repo access raises a 403.

    Tests: probe_backend_status() 403 classification.
    Why: Rate limiting is a recoverable transient condition — RATE_LIMITED
         lets clients back off rather than treating it as a hard error.
    """

    def test_403_exception_returns_rate_limited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GithubException with status=403 -> availability=RATE_LIMITED.

        Tests: probe_backend_status() 403 rate-limit branch
        How: Mock repo.open_issues_count to raise GithubException(403);
             verify result.availability == RATE_LIMITED
        Why: Distinguishes rate limiting from general errors for client retry logic
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=403, data={"message": "rate limited"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.RATE_LIMITED


# ---------------------------------------------------------------------------
# Probe unit tests — count fetch fails (non-403 GithubException)
# ---------------------------------------------------------------------------


class TestProbeBackendStatusCountFetchFailure:
    """probe_backend_status returns REACHABLE with None counts on non-403 GithubException.

    Tests: probe_backend_status() non-fatal count fetch failure.
    Why: The repo is reachable but issue count fetch may fail for other reasons
         (e.g., permission restriction). REACHABLE with error lets users know
         the backend works but counts are unavailable.
    """

    def test_non_403_exception_returns_reachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException during count fetch -> availability=REACHABLE.

        Tests: probe_backend_status() non-403 exception branch
        How: Mock open_issues_count to raise GithubException(500); check availability
        Why: Server error during count is not an auth or rate-limit issue
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.REACHABLE

    def test_non_403_exception_open_count_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException -> open_count is None.

        Tests: probe_backend_status() count fields when count fetch fails
        How: Mock exception; verify result.open_count is None
        Why: None signals counts were unavailable, distinct from zero
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.open_count is None

    def test_non_403_exception_error_field_is_populated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException -> error field contains the exception text.

        Tests: probe_backend_status() error capture for non-403 failures
        How: Mock exception; verify result.error is non-empty
        Why: Users need to see what the GitHub API returned
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.gh_client.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.error != ""


# ---------------------------------------------------------------------------
# Integration tests — backlog_list response shape
# ---------------------------------------------------------------------------


class TestBacklogListBackendIntegration:
    """backlog_list response always contains a 'backend' key with BackendStatus shape.

    Tests: backlog_list MCP tool backend response integration.
    Why: The 'backend' key is a new strictly additive field. Existing clients
         must not see changed response structure and new clients must find the
         backend dict with all documented fields.
    """

    async def test_backlog_list_response_contains_backend_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """backlog_list response dict contains a 'backend' key.

        Tests: backlog_list response — backend key presence
        How: Mock operations.list_items and _probe_backend_status; call tool;
             check 'backend' key present in response
        Why: Missing key breaks all clients expecting backend availability info
        """
        backend_status = BackendStatus(
            availability=BackendAvailability.NEEDS_AUTHENTICATION, error="GITHUB_TOKEN not set"
        )

        with (
            patch("dh_core.operations.list_items", return_value={"items": []}),
            patch("backlog_core.server._probe_backend_status", return_value=backend_status),
        ):
            response = await _call("backlog_list", {})

        assert "backend" in response

    async def test_backlog_list_response_backend_contains_all_backend_status_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """backlog_list 'backend' value includes all BackendStatus field names.

        Tests: backlog_list response — backend field completeness
        How: Mock probe; call tool; compare backend dict keys to BackendStatus fields
        Why: Any missing field is a silent regression for status-reading clients
        """
        backend_status = BackendStatus(
            availability=BackendAvailability.REACHABLE,
            open_count=7,
            total_count=30,
            cache_open_count=5,
            cache_total_count=12,
            last_sync="2026-03-23T09:00:00Z",
            error="",
        )

        with (
            patch("dh_core.operations.list_items", return_value={"items": []}),
            patch("backlog_core.server._probe_backend_status", return_value=backend_status),
        ):
            response = await _call("backlog_list", {})

        backend = response["backend"]
        expected_keys = {
            "name",
            "availability",
            "open_count",
            "total_count",
            "cache_open_count",
            "cache_total_count",
            "last_sync",
            "error",
        }
        assert expected_keys == set(backend.keys())

    async def test_backlog_list_existing_response_keys_remain_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """backlog_list adding 'backend' does not remove existing response keys.

        Tests: backlog_list response — existing key preservation
        How: Call tool with mocked list_items; verify items, count, pagination,
             messages, and warnings keys all still present
        Why: Additive change must not break any existing client expectations
        """
        backend_status = BackendStatus()

        with (
            patch(
                "dh_core.operations.list_items",
                return_value={"items": [{"title": "Feature X", "priority": "P1", "issue": "", "plan": ""}]},
            ),
            patch("backlog_core.server._probe_backend_status", return_value=backend_status),
        ):
            response = await _call("backlog_list", {})

        assert "items" in response
        assert "count" in response
        assert "pagination" in response
        assert "messages" in response
        assert "warnings" in response

    async def test_backlog_list_backend_shape_matches_backend_status_model_dump(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """backlog_list 'backend' value matches BackendStatus.model_dump(mode='json').

        Tests: backlog_list response — backend value fidelity
        How: Create known BackendStatus with empty items list (cache_open_count=0 after
             ADR-5 server assignment); mock probe; call tool; compare backend dict to
             model_dump(mode='json') output which serialises enum values to strings
        Why: Any transformation between model_dump and response output is a bug.
             cache_open_count is always overwritten by server.py (ADR-5) with len(items),
             so the expected value must match items=[] -> total=0.
        """
        backend_status = BackendStatus(
            availability=BackendAvailability.REACHABLE,
            open_count=3,
            total_count=10,
            # cache_open_count will be overwritten by server.py ADR-5 to len(items)==0
            cache_open_count=0,
            cache_total_count=8,
            last_sync="2026-03-23T08:00:00Z",
            error="",
        )
        # model_dump(mode="json") produces plain strings for StrEnum values,
        # matching the JSON-serialised response that the MCP transport returns
        expected_backend = backend_status.model_dump(mode="json")

        with (
            patch("dh_core.operations.list_items", return_value={"items": []}),
            patch("backlog_core.server._probe_backend_status", return_value=backend_status),
        ):
            response = await _call("backlog_list", {})

        assert response["backend"] == expected_backend
