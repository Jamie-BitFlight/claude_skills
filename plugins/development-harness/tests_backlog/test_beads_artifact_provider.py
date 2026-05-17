"""Unit tests for BeadsArtifactProvider.

Coverage target: ≥85% line and ≥80% branch on
backlog_core.backends.beads_artifact_provider.

All BdRunner calls are mocked via pytest-mock (``mocker: MockerFixture``).
No live ``bd`` binary is required.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from backlog_core.artifact_provider import BackendName, create_artifact_provider
from backlog_core.backends.bd_runner import BdInvocationError, BdNotInstalledError, BdRunner
from backlog_core.backends.beads_artifact_provider import BeadsArtifactProvider, _extract_manifest_from_metadata
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISSUE_ID = "bd-a3f8"


def _raw_issue(**overrides: object) -> dict[str, object]:
    """Return a minimal valid ``bd show --json`` dict, with optional overrides."""
    base: dict[str, object] = {
        "id": _ISSUE_ID,
        "title": "Test issue",
        "status": "open",
        "type": "task",
        "priority": 2,
        "notes": None,
        "metadata": None,
    }
    base.update(overrides)
    return base


def _make_entry(
    artifact_type: ArtifactType = ArtifactType.ARCHITECT, artifact_id: str = "plan/architect.md"
) -> ArtifactEntry:
    """Return a minimal ``ArtifactEntry`` for manifest testing."""
    return ArtifactEntry(artifact_type=artifact_type, artifact_id=artifact_id, status=ArtifactStatus.CURRENT)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_runner(mocker: MockerFixture) -> MagicMock:
    """Return a mock BdRunner with spec; no subprocess is ever invoked."""
    return mocker.MagicMock(spec=BdRunner)


@pytest.fixture
def provider(mock_runner: MagicMock) -> BeadsArtifactProvider:
    """Return a BeadsArtifactProvider with the mock runner injected."""
    return BeadsArtifactProvider(runner=mock_runner)


# ---------------------------------------------------------------------------
# TestGetManifestBd
# ---------------------------------------------------------------------------


class TestGetManifestBd:
    def test_returns_empty_manifest_when_metadata_is_none(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When bd show returns no metadata, an empty ArtifactManifest is returned."""
        mock_runner.run_json.return_value = _raw_issue(metadata=None)

        result = provider.get_manifest_bd(_ISSUE_ID)

        assert result.issue_number == 0
        assert result.artifacts == []

    def test_returns_empty_manifest_when_metadata_has_no_dh_key(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When metadata exists but has no dh.artifacts key, returns empty manifest."""
        mock_runner.run_json.return_value = _raw_issue(metadata={"other.key": "value"})

        result = provider.get_manifest_bd(_ISSUE_ID)

        assert result.artifacts == []

    def test_returns_manifest_from_flat_key(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """Flat dh.artifacts key is parsed into an ArtifactManifest."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}
        )

        result = provider.get_manifest_bd(_ISSUE_ID)

        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.ARCHITECT

    def test_returns_manifest_from_nested_key(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """Nested {'dh': {'artifacts': ...}} key is parsed into an ArtifactManifest."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh": {"artifacts": manifest.model_dump_json(by_alias=True)}}
        )

        result = provider.get_manifest_bd(_ISSUE_ID)

        assert len(result.artifacts) == 1

    def test_invokes_show_with_correct_argv(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """get_manifest_bd calls run_json(["show", issue_id])."""
        mock_runner.run_json.return_value = _raw_issue()

        provider.get_manifest_bd(_ISSUE_ID)

        mock_runner.run_json.assert_called_once_with(["show", _ISSUE_ID])

    def test_propagates_bd_not_installed_error(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """BdNotInstalledError from run_json propagates unchanged."""
        mock_runner.run_json.side_effect = BdNotInstalledError("bd not found")

        with pytest.raises(BdNotInstalledError):
            provider.get_manifest_bd(_ISSUE_ID)


# ---------------------------------------------------------------------------
# TestSetManifestBd
# ---------------------------------------------------------------------------


class TestSetManifestBd:
    def test_calls_run_text_with_update_command(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """set_manifest_bd calls run_text with update subcommand and --set-metadata flag."""
        manifest = ArtifactManifest(issue_number=0)

        provider.set_manifest_bd(_ISSUE_ID, manifest)

        call_args = mock_runner.run_text.call_args[0][0]
        assert call_args[0] == "update"
        assert call_args[1] == _ISSUE_ID
        assert call_args[2] == "--set-metadata"
        assert call_args[3].startswith("dh.artifacts=")

    def test_serialised_manifest_contains_valid_json(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """The value part of the --set-metadata arg is valid compact JSON."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])

        provider.set_manifest_bd(_ISSUE_ID, manifest)

        call_args = mock_runner.run_text.call_args[0][0]
        _, json_part = call_args[3].split("=", 1)
        parsed = json.loads(json_part)
        assert parsed["artifacts"][0]["artifact-type"] == "architect"

    def test_stamps_last_updated_timestamp(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """The serialised manifest includes a non-empty last-updated field."""
        manifest = ArtifactManifest(issue_number=0)

        provider.set_manifest_bd(_ISSUE_ID, manifest)

        call_args = mock_runner.run_text.call_args[0][0]
        _, json_part = call_args[3].split("=", 1)
        parsed = json.loads(json_part)
        assert parsed["last-updated"] != ""

    def test_propagates_bd_invocation_error(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """BdInvocationError from run_text propagates unchanged."""
        mock_runner.run_text.side_effect = BdInvocationError(
            "bd failed", argv=["bd", "update"], returncode=1, stdout="", stderr="error"
        )
        manifest = ArtifactManifest(issue_number=0)

        with pytest.raises(BdInvocationError):
            provider.set_manifest_bd(_ISSUE_ID, manifest)


# ---------------------------------------------------------------------------
# TestStoreArtifactContentBd
# ---------------------------------------------------------------------------


class TestStoreArtifactContentBd:
    def test_writes_new_block_when_notes_is_none(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """When notes is None, the new sentinel block becomes the full notes."""
        mock_runner.run_json.return_value = _raw_issue(notes=None)

        provider.store_artifact_content_bd(_ISSUE_ID, "architect", "plan/foo.md", "content here")

        call_args = mock_runner.run_text.call_args[0][0]
        assert call_args[0] == "update"
        assert call_args[2] == "--notes"
        notes = call_args[3]
        assert "<!-- artifact-content:type=architect:id=plan/foo.md -->" in notes
        assert "content here" in notes
        assert "<!-- /artifact-content:type=architect:id=plan/foo.md -->" in notes

    def test_appends_block_when_notes_has_no_matching_sentinel(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When existing notes do not contain the sentinel, block is appended."""
        mock_runner.run_json.return_value = _raw_issue(notes="existing notes")

        provider.store_artifact_content_bd(_ISSUE_ID, "research", "plan/research.md", "new content")

        call_args = mock_runner.run_text.call_args[0][0]
        notes = call_args[3]
        assert "existing notes" in notes
        assert "<!-- artifact-content:type=research:id=plan/research.md -->" in notes

    def test_replaces_block_in_place_when_sentinel_exists(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When existing notes contain the sentinel, the block is replaced in-place."""
        existing_block = (
            "<!-- artifact-content:type=architect:id=plan/foo.md -->\n"
            "old content\n"
            "<!-- /artifact-content:type=architect:id=plan/foo.md -->"
        )
        mock_runner.run_json.return_value = _raw_issue(notes=existing_block)

        provider.store_artifact_content_bd(_ISSUE_ID, "architect", "plan/foo.md", "new content")

        call_args = mock_runner.run_text.call_args[0][0]
        notes = call_args[3]
        assert "old content" not in notes
        assert "new content" in notes

    def test_appends_with_double_newline_separator_when_notes_does_not_end_in_newline(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """Notes not ending in newline get a double newline before the appended block."""
        mock_runner.run_json.return_value = _raw_issue(notes="existing")

        provider.store_artifact_content_bd(_ISSUE_ID, "architect", "plan/foo.md", "content")

        call_args = mock_runner.run_text.call_args[0][0]
        notes = call_args[3]
        # Double newline separates existing content from the new block
        assert "existing\n\n" in notes

    def test_calls_show_then_update(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """store_artifact_content_bd calls run_json(show) then run_text(update)."""
        mock_runner.run_json.return_value = _raw_issue(notes=None)

        provider.store_artifact_content_bd(_ISSUE_ID, "architect", "plan/foo.md", "content")

        mock_runner.run_json.assert_called_once_with(["show", _ISSUE_ID])
        mock_runner.run_text.assert_called_once()


# ---------------------------------------------------------------------------
# TestReadArtifactContentFromRemoteBd
# ---------------------------------------------------------------------------


class TestReadArtifactContentFromRemoteBd:
    def test_returns_content_when_sentinel_block_present(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When the sentinel block exists, returns the content between markers."""
        notes = (
            "<!-- artifact-content:type=architect:id=plan/foo.md -->\n"
            "architect content\n"
            "<!-- /artifact-content:type=architect:id=plan/foo.md -->"
        )
        mock_runner.run_json.return_value = _raw_issue(notes=notes)

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result == "architect content"

    def test_returns_none_when_sentinel_block_absent(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When no matching sentinel block exists, returns None."""
        mock_runner.run_json.return_value = _raw_issue(notes="some unrelated notes")

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result is None

    def test_returns_none_when_notes_is_none(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """When notes is None, returns None."""
        mock_runner.run_json.return_value = _raw_issue(notes=None)

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result is None

    def test_does_not_match_wrong_artifact_type(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """Sentinel matching is type-specific — wrong type returns None."""
        notes = (
            "<!-- artifact-content:type=research:id=plan/foo.md -->\n"
            "research content\n"
            "<!-- /artifact-content:type=research:id=plan/foo.md -->"
        )
        mock_runner.run_json.return_value = _raw_issue(notes=notes)

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result is None

    def test_does_not_match_wrong_path(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """Sentinel matching is path-specific — wrong path returns None."""
        notes = (
            "<!-- artifact-content:type=architect:id=plan/other.md -->\n"
            "other content\n"
            "<!-- /artifact-content:type=architect:id=plan/other.md -->"
        )
        mock_runner.run_json.return_value = _raw_issue(notes=notes)

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result is None

    def test_multiline_content_preserved(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """Multi-line content between sentinel markers is returned intact."""
        content = "line 1\nline 2\nline 3"
        notes = (
            f"<!-- artifact-content:type=architect:id=plan/foo.md -->\n"
            f"{content}\n"
            f"<!-- /artifact-content:type=architect:id=plan/foo.md -->"
        )
        mock_runner.run_json.return_value = _raw_issue(notes=notes)

        result = provider.read_artifact_content_from_remote_bd(_ISSUE_ID, "architect", "plan/foo.md")

        assert result == content


# ---------------------------------------------------------------------------
# TestDeleteEntryBd
# ---------------------------------------------------------------------------


class TestDeleteEntryBd:
    def test_removes_entry_from_manifest_and_content_from_notes(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """delete_entry_bd removes the manifest entry and strips the sentinel block."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        notes = (
            "<!-- artifact-content:type=architect:id=plan/architect.md -->\n"
            "architect content\n"
            "<!-- /artifact-content:type=architect:id=plan/architect.md -->"
        )
        # Single bd show call supplies both manifest and notes.
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}, notes=notes
        )

        provider.delete_entry_bd(_ISSUE_ID, "architect", "plan/architect.md")

        # set_manifest_bd (run_text) + notes update (run_text) = 2 calls
        assert mock_runner.run_text.call_count == 2
        last_notes_call = mock_runner.run_text.call_args_list[1][0][0]
        assert last_notes_call[2] == "--notes"
        stripped_notes = last_notes_call[3]
        assert "artifact-content:type=architect:id=plan/architect.md" not in stripped_notes

    def test_noop_when_manifest_entry_not_found_and_no_sentinel(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When the entry is not in the manifest and no sentinel exists, run_text is never called."""
        manifest = ArtifactManifest(issue_number=0, artifacts=[])
        notes = "some notes without sentinel"
        # Single bd show call supplies both manifest and notes.
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}, notes=notes
        )

        provider.delete_entry_bd(_ISSUE_ID, "architect", "plan/architect.md")

        assert mock_runner.run_text.call_count == 0

    def test_collapses_blank_lines_after_sentinel_strip(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """Stripping a sentinel block collapses surplus blank lines."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        notes = (
            "preamble\n\n"
            "<!-- artifact-content:type=architect:id=plan/architect.md -->\n"
            "content\n"
            "<!-- /artifact-content:type=architect:id=plan/architect.md -->\n\n"
            "postamble"
        )
        # Single bd show call supplies both manifest and notes.
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}, notes=notes
        )

        provider.delete_entry_bd(_ISSUE_ID, "architect", "plan/architect.md")

        last_notes_call = mock_runner.run_text.call_args_list[1][0][0]
        stripped_notes = last_notes_call[3]
        assert "\n\n\n" not in stripped_notes

    def test_skips_notes_update_when_notes_is_empty(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """When notes is empty after get, the notes update run_text is not called."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        # Single bd show call supplies both manifest and notes (notes=None here).
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}, notes=None
        )

        provider.delete_entry_bd(_ISSUE_ID, "architect", "plan/architect.md")

        # set_manifest_bd is called (1 run_text), but notes update is NOT called
        assert mock_runner.run_text.call_count == 1
        assert mock_runner.run_text.call_args[0][0][2] == "--set-metadata"


# ---------------------------------------------------------------------------
# TestADR002TypeWidening
# ---------------------------------------------------------------------------


class TestADR002TypeWidening:
    """Protocol methods accept str IDs at runtime; raise NotImplementedError for int."""

    def test_get_manifest_with_str_delegates_to_get_manifest_bd(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """get_manifest(str) delegates to get_manifest_bd without raising."""
        mock_runner.run_json.return_value = _raw_issue()

        result = provider.get_manifest(_ISSUE_ID)  # type: ignore[arg-type]

        assert result.issue_number == 0
        mock_runner.run_json.assert_called_once()

    def test_get_manifest_with_int_raises_not_implemented(self, provider: BeadsArtifactProvider) -> None:
        """get_manifest(int) raises NotImplementedError per ADR-002."""
        with pytest.raises(NotImplementedError, match="beads ID"):
            provider.get_manifest(42)

    def test_set_manifest_with_str_delegates_to_set_manifest_bd(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """set_manifest(str, manifest) delegates to set_manifest_bd."""
        manifest = ArtifactManifest(issue_number=0)

        provider.set_manifest(_ISSUE_ID, manifest)  # type: ignore[arg-type]

        mock_runner.run_text.assert_called_once()

    def test_set_manifest_with_int_raises_not_implemented(self, provider: BeadsArtifactProvider) -> None:
        """set_manifest(int, manifest) raises NotImplementedError per ADR-002."""
        with pytest.raises(NotImplementedError):
            provider.set_manifest(42, ArtifactManifest(issue_number=0))

    def test_store_artifact_content_with_str_delegates(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """store_artifact_content(str, ...) delegates to store_artifact_content_bd."""
        mock_runner.run_json.return_value = _raw_issue(notes=None)

        provider.store_artifact_content(_ISSUE_ID, "architect", "plan/foo.md", "content")  # type: ignore[arg-type]

        mock_runner.run_text.assert_called_once()

    def test_store_artifact_content_with_int_raises_not_implemented(self, provider: BeadsArtifactProvider) -> None:
        """store_artifact_content(int, ...) raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            provider.store_artifact_content(42, "architect", "plan/foo.md", "content")

    def test_read_artifact_content_from_remote_with_str_delegates(
        self, provider: BeadsArtifactProvider, mock_runner: MagicMock
    ) -> None:
        """read_artifact_content_from_remote(str, ...) delegates to remote_bd variant."""
        mock_runner.run_json.return_value = _raw_issue(notes=None)

        result = provider.read_artifact_content_from_remote(_ISSUE_ID, "architect", "plan/foo.md")  # type: ignore[arg-type]

        assert result is None

    def test_read_artifact_content_from_remote_with_int_raises_not_implemented(
        self, provider: BeadsArtifactProvider
    ) -> None:
        """read_artifact_content_from_remote(int, ...) raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            provider.read_artifact_content_from_remote(42, "architect", "plan/foo.md")

    def test_delete_entry_with_str_delegates(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """delete_entry(str, ...) delegates to delete_entry_bd."""
        manifest = ArtifactManifest(issue_number=0, artifacts=[])
        # Single bd show call supplies both manifest and notes.
        mock_runner.run_json.return_value = _raw_issue(
            metadata={"dh.artifacts": manifest.model_dump_json(by_alias=True)}, notes=None
        )

        provider.delete_entry(_ISSUE_ID, "architect", "plan/architect.md")  # type: ignore[arg-type]

        assert mock_runner.run_json.call_count == 1

    def test_delete_entry_with_int_raises_not_implemented(self, provider: BeadsArtifactProvider) -> None:
        """delete_entry(int, ...) raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            provider.delete_entry(42, "architect", "plan/architect.md")


# ---------------------------------------------------------------------------
# TestExtractManifestFromMetadata
# ---------------------------------------------------------------------------


class TestExtractManifestFromMetadata:
    """Unit tests for the module-level _extract_manifest_from_metadata helper."""

    def test_returns_none_for_empty_metadata(self) -> None:
        """Returns None when metadata is an empty dict."""
        assert _extract_manifest_from_metadata({}) is None

    def test_returns_none_when_neither_key_present(self) -> None:
        """Returns None when metadata contains no dh or dh.artifacts key."""
        assert _extract_manifest_from_metadata({"other": "value"}) is None

    def test_flat_key_string_returns_manifest(self) -> None:
        """Flat 'dh.artifacts' JSON string key returns a parsed ArtifactManifest."""
        data = {"issue_number": 7, "artifacts": [], "last-updated": ""}
        result = _extract_manifest_from_metadata({"dh.artifacts": json.dumps(data)})
        assert result is not None
        assert result.issue_number == 7

    def test_nested_key_returns_manifest(self) -> None:
        """Nested {'dh': {'artifacts': ...}} key returns a parsed ArtifactManifest."""
        data = {"issue_number": 5, "artifacts": [], "last-updated": ""}
        result = _extract_manifest_from_metadata({"dh": {"artifacts": json.dumps(data)}})
        assert result is not None
        assert result.issue_number == 5

    def test_dict_value_directly_parsed(self) -> None:
        """A dict value for dh.artifacts is also accepted (not only strings)."""
        data = {"issue_number": 3, "artifacts": [], "last-updated": ""}
        result = _extract_manifest_from_metadata({"dh.artifacts": data})
        assert result is not None
        assert result.issue_number == 3

    def test_nested_key_takes_precedence_over_flat(self) -> None:
        """When both nested and flat keys are present, nested is tried first."""
        nested_data = {"issue_number": 10, "artifacts": [], "last-updated": ""}
        flat_data = {"issue_number": 20, "artifacts": [], "last-updated": ""}
        result = _extract_manifest_from_metadata({
            "dh": {"artifacts": json.dumps(nested_data)},
            "dh.artifacts": json.dumps(flat_data),
        })
        assert result is not None
        assert result.issue_number == 10

    def test_dh_section_not_dict_falls_through_to_flat(self) -> None:
        """When metadata['dh'] is not a dict, falls through to flat-key lookup."""
        data = {"issue_number": 9, "artifacts": [], "last-updated": ""}
        result = _extract_manifest_from_metadata({"dh": "not-a-dict", "dh.artifacts": json.dumps(data)})
        assert result is not None
        assert result.issue_number == 9


# ---------------------------------------------------------------------------
# TestLazyRunnerConstruction
# ---------------------------------------------------------------------------


class TestLazyRunnerConstruction:
    """The runner is lazily constructed; the constructor is filesystem-free."""

    def test_injected_runner_is_used_directly(self, provider: BeadsArtifactProvider, mock_runner: MagicMock) -> None:
        """When runner is injected, _runner property returns it directly."""
        assert provider._runner is mock_runner

    def test_none_runner_creates_default_on_first_access(self, mocker: MockerFixture) -> None:
        """When no runner is provided, BdRunner() is created lazily on first _runner access."""
        mock_runner_class = mocker.patch(
            "backlog_core.backends.beads_artifact_provider.BdRunner", return_value=mocker.MagicMock(spec=BdRunner)
        )
        p = BeadsArtifactProvider()
        _ = p._runner  # triggers lazy creation

        mock_runner_class.assert_called_once_with()

    def test_constructor_does_not_set_runner_to_non_none(self) -> None:
        """Default constructor leaves _runner_instance as None (deferred)."""
        p = BeadsArtifactProvider()
        assert p._runner_instance is None


# ---------------------------------------------------------------------------
# TestFactoryIntegration
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    def test_create_artifact_provider_beads_returns_beads_provider(self) -> None:
        """create_artifact_provider('beads') returns a BeadsArtifactProvider instance."""
        provider = create_artifact_provider(backend_name="beads")

        assert isinstance(provider, BeadsArtifactProvider)

    def test_backend_name_enum_beads_also_works(self) -> None:
        """BackendName.beads enum value is accepted by create_artifact_provider."""
        provider = create_artifact_provider(backend_name=BackendName.beads)

        assert isinstance(provider, BeadsArtifactProvider)

    def test_backlog_backend_env_var_beads_returns_beads_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BACKLOG_BACKEND=beads env var selects BeadsArtifactProvider via factory."""
        monkeypatch.setenv("BACKLOG_BACKEND", "beads")

        provider = create_artifact_provider()

        assert isinstance(provider, BeadsArtifactProvider)
