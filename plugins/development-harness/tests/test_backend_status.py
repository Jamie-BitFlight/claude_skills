"""Tests for BackendStatus model, probe_backend_status(), and backlog_list integration.

Covers:
- BackendAvailability enum members and serialisation (test cases 1-3)
- probe_backend_status() unit tests mocking all GitHub/filesystem operations (4-12)
- backlog_list response integration: "backend" key shape and existing key preservation (13-15)

No real network calls are made. All GitHub API access and filesystem operations are mocked
via pytest monkeypatch and unittest.mock.patch.

asyncio_mode = "auto" is set globally in pyproject.toml — no @pytest.mark.asyncio decorators.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from backlog_core.github import probe_backend_status
from backlog_core.models import BackendAvailability, BackendStatus
from backlog_core.server import mcp
from fastmcp.client import Client
from github import GithubException

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helper: call a tool via in-memory FastMCP transport
# ---------------------------------------------------------------------------


async def _call(tool_name: str, params: dict | None = None) -> dict:
    """Call an MCP tool through the in-memory transport and return parsed JSON.

    Args:
        tool_name: Registered MCP tool name.
        params: Optional parameters dict.

    Returns:
        Parsed JSON response dict from the tool.
    """
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, params or {})
    return json.loads(result.content[0].text)


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


@pytest.fixture
def probe_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up isolated filesystem for probe_backend_status tests.

    Patches BACKLOG_DIR to a temp directory and sets DH_STATE_HOME so that
    dh_paths.state_root() resolves under tmp_path. Returns the BACKLOG_DIR
    path so tests can add .md files to control cache_total_count.

    Args:
        tmp_path: pytest-provided temporary directory.
        monkeypatch: pytest monkeypatch fixture.

    Returns:
        Path to the patched BACKLOG_DIR.
    """
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()

    # Redirect BACKLOG_DIR used by probe_backend_status via _models.BACKLOG_DIR
    monkeypatch.setattr("backlog_core.models.BACKLOG_DIR", backlog_dir)

    # Redirect dh_paths.state_root() so .last_sync resolves under tmp_path
    state_root = tmp_path / "state"
    state_root.mkdir()
    monkeypatch.setattr("backlog_core.github._dh_paths", _make_dh_paths_mock(state_root))

    return backlog_dir


def _make_dh_paths_mock(state_root: Path) -> MagicMock:
    """Build a minimal dh_paths mock that returns a fixed state_root.

    Args:
        state_root: Directory that state_root() should return.

    Returns:
        MagicMock with state_root() configured.
    """
    mock = MagicMock()
    mock.state_root.return_value = state_root
    return mock


# ---------------------------------------------------------------------------
# Probe unit tests — GITHUB_TOKEN not set
# ---------------------------------------------------------------------------


class TestProbeBackendStatusNoToken:
    """probe_backend_status returns NEEDS_AUTHENTICATION when GITHUB_TOKEN is absent.

    Tests: probe_backend_status() authentication gate.
    Why: Without a token, all GitHub operations are impossible — the probe
         must report this clearly so users know to configure credentials.
    """

    def test_no_token_returns_needs_authentication(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GITHUB_TOKEN absent -> availability=NEEDS_AUTHENTICATION.

        Tests: probe_backend_status() with no token
        How: Remove GITHUB_TOKEN env var; call probe; check availability
        Why: Correct classification prevents misleading 'ERROR' messages
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert result.availability == BackendAvailability.NEEDS_AUTHENTICATION

    def test_no_token_error_contains_github_token(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """GITHUB_TOKEN absent -> error field contains 'GITHUB_TOKEN'.

        Tests: probe_backend_status() error message with no token
        How: Remove GITHUB_TOKEN; check result.error contains 'GITHUB_TOKEN'
        Why: Users need actionable error text pointing to the missing variable
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert "GITHUB_TOKEN" in result.error


# ---------------------------------------------------------------------------
# Probe unit tests — token set, GitHub reachable
# ---------------------------------------------------------------------------


class TestProbeBackendStatusReachable:
    """probe_backend_status returns REACHABLE with counts when GitHub is accessible.

    Tests: probe_backend_status() happy path.
    Why: Reachable state with correct counts is the primary positive signal
         that the backend integration is working correctly.
    """

    def test_reachable_returns_reachable_availability(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.REACHABLE

    def test_reachable_returns_correct_open_count(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.open_count == 5

    def test_reachable_returns_correct_total_count(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
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

    def test_unreachable_returns_error_availability(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None -> availability=ERROR.

        Tests: probe_backend_status() with failed connection
        How: Set token; mock try_get_github to return None; check availability
        Why: ERROR distinguishes connection failure from auth failure
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        with patch("backlog_core.github.try_get_github", return_value=None):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.ERROR

    def test_unreachable_error_field_is_populated(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """try_get_github returns None -> error field is non-empty.

        Tests: probe_backend_status() error message on connection failure
        How: Mock try_get_github to return None; verify result.error is non-empty
        Why: Users need a diagnostic message when the connection fails
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        with patch("backlog_core.github.try_get_github", return_value=None):
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

    def test_403_exception_returns_rate_limited(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
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

    def test_non_403_exception_returns_reachable(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException during count fetch -> availability=REACHABLE.

        Tests: probe_backend_status() non-403 exception branch
        How: Mock open_issues_count to raise GithubException(500); check availability
        Why: Server error during count is not an auth or rate-limit issue
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.availability == BackendAvailability.REACHABLE

    def test_non_403_exception_open_count_is_none(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException -> open_count is None.

        Tests: probe_backend_status() count fields when count fetch fails
        How: Mock exception; verify result.open_count is None
        Why: None signals counts were unavailable, distinct from zero
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.open_count is None

    def test_non_403_exception_error_field_is_populated(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-403 GithubException -> error field contains the exception text.

        Tests: probe_backend_status() error capture for non-403 failures
        How: Mock exception; verify result.error is non-empty
        Why: Users need to see what the GitHub API returned
        """
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        mock_repo = MagicMock()
        exc = GithubException(status=500, data={"message": "server error"}, headers={})
        type(mock_repo).open_issues_count = property(lambda self: (_ for _ in ()).throw(exc))

        with patch("backlog_core.github.try_get_github", return_value=mock_repo):
            result = probe_backend_status()

        assert result.error != ""


# ---------------------------------------------------------------------------
# Probe unit tests — cache directory counts
# ---------------------------------------------------------------------------


class TestProbeBackendStatusCacheCounts:
    """probe_backend_status counts .md files in BACKLOG_DIR for cache_total_count.

    Tests: probe_backend_status() cache file counting.
    Why: cache_total_count gives users visibility into local cache size
         without requiring a GitHub connection.
    """

    def test_empty_cache_dir_returns_zero_cache_total_count(
        self, probe_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty BACKLOG_DIR -> cache_total_count=0.

        Tests: probe_backend_status() empty cache directory
        How: Leave BACKLOG_DIR empty; remove token; check cache_total_count
        Why: Zero is the correct count when no cached files exist
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        result = probe_backend_status()

        assert result.cache_total_count == 0

    def test_cache_dir_with_md_files_returns_correct_count(
        self, probe_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BACKLOG_DIR with N .md files -> cache_total_count=N.

        Tests: probe_backend_status() cache file counting
        How: Create 3 .md files in BACKLOG_DIR; remove token; check count
        Why: Count must match actual file presence for reliable status
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        (probe_env / "p1-feature-one.md").write_text("---\ntitle: Feature One\n---")
        (probe_env / "p1-feature-two.md").write_text("---\ntitle: Feature Two\n---")
        (probe_env / "p2-bug-three.md").write_text("---\ntitle: Bug Three\n---")

        result = probe_backend_status()

        assert result.cache_total_count == 3

    def test_non_md_files_not_counted(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-.md files in BACKLOG_DIR do not contribute to cache_total_count.

        Tests: probe_backend_status() glob specificity
        How: Create 1 .md and 2 non-.md files; verify count is 1
        Why: Only .md backlog items should be counted; config/lock files must be excluded
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        (probe_env / "p1-item.md").write_text("---\ntitle: Item\n---")
        (probe_env / "config.json").write_text("{}")
        (probe_env / ".gitkeep").write_text("")

        result = probe_backend_status()

        assert result.cache_total_count == 1


# ---------------------------------------------------------------------------
# Probe unit tests — last_sync timestamp
# ---------------------------------------------------------------------------


class TestProbeBackendStatusLastSync:
    """probe_backend_status reads last_sync from the .last_sync file.

    Tests: probe_backend_status() last_sync field population.
    Why: Clients display the last sync time to help users understand cache
         freshness; missing or wrong values undermine trust in status data.
    """

    def test_last_sync_present_returns_timestamp(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """.last_sync file present -> last_sync equals file contents.

        Tests: probe_backend_status() last_sync from file
        How: Write a timestamp string to .last_sync; verify result.last_sync matches
        Why: The timestamp must be read exactly as stored, not interpreted
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        timestamp = "2026-03-23T10:30:00Z"

        # Get the state_root path that the probe will read from
        import backlog_core.github as _gh_module

        state_root = _gh_module._dh_paths.state_root()
        (state_root / ".last_sync").write_text(timestamp, encoding="utf-8")

        result = probe_backend_status()

        assert result.last_sync == timestamp

    def test_last_sync_absent_returns_empty_string(self, probe_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """.last_sync file absent -> last_sync is ''.

        Tests: probe_backend_status() last_sync when file missing
        How: Ensure .last_sync does not exist in state_root; verify result.last_sync == ''
        Why: Empty string is the defined sentinel for 'never synced'
        """
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        import backlog_core.github as _gh_module

        state_root = _gh_module._dh_paths.state_root()
        last_sync_path = state_root / ".last_sync"
        if last_sync_path.exists():
            last_sync_path.unlink()

        result = probe_backend_status()

        assert result.last_sync == ""


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
            patch("backlog_core.operations.list_items", return_value={"items": []}),
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
            patch("backlog_core.operations.list_items", return_value={"items": []}),
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
                "backlog_core.operations.list_items",
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
            patch("backlog_core.operations.list_items", return_value={"items": []}),
            patch("backlog_core.server._probe_backend_status", return_value=backend_status),
        ):
            response = await _call("backlog_list", {})

        assert response["backend"] == expected_backend
