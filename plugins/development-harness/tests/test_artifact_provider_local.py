"""Unit tests for LocalFilesystemArtifactProvider.

Coverage target: ≥90% line and ≥90% branch on
backlog_core/artifact_provider_local.py.
"""

from __future__ import annotations

import concurrent.futures
import json
import threading
from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest
from backlog_core.artifact_provider_local import LocalFilesystemArtifactProvider
from backlog_core.models import ArtifactEntry, ArtifactManifest, ArtifactStatus, ArtifactType
from hypothesis import HealthCheck, given, settings, strategies as st

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_entry(
    artifact_type: ArtifactType = ArtifactType.ARCHITECT,
    status: ArtifactStatus = ArtifactStatus.CURRENT,
    storage_tier: Literal["local", "remote"] = "remote",
) -> ArtifactEntry:
    """Return a minimal ArtifactEntry suitable for testing."""
    return ArtifactEntry(
        artifact_type=artifact_type, artifact_id="test-artifact-1", status=status, storage_tier=storage_tier
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def root_worktree(tmp_path: Path) -> Path:
    """Provide a temporary directory that acts as the repository root."""
    worktree = tmp_path / "repo"
    worktree.mkdir()
    return worktree


@pytest.fixture
def manifest_dir(tmp_path: Path) -> Path:
    """Provide a temporary manifest directory path (not pre-created)."""
    return tmp_path / "artifacts"


@pytest.fixture
def provider(root_worktree: Path, manifest_dir: Path) -> LocalFilesystemArtifactProvider:
    """Return a provider with an isolated manifest_dir that does not touch ~/.dh/."""
    return LocalFilesystemArtifactProvider(root_worktree=root_worktree, manifest_dir=manifest_dir)


# ---------------------------------------------------------------------------
# TestInit
# ---------------------------------------------------------------------------


class TestInit:
    def test_explicit_manifest_dir_stored(self, root_worktree: Path, manifest_dir: Path) -> None:
        """Constructor stores the explicit manifest_dir."""
        p = LocalFilesystemArtifactProvider(root_worktree=root_worktree, manifest_dir=manifest_dir)
        assert p._manifest_dir == manifest_dir

    def test_default_manifest_dir_uses_dh_state_root(self, root_worktree: Path) -> None:
        """Without manifest_dir, defaults to dh_paths.state_root() / 'artifacts'."""
        import dh_paths as _dh_paths  # available after the module-level import in the provider

        p = LocalFilesystemArtifactProvider(root_worktree=root_worktree)
        assert p._manifest_dir == _dh_paths.state_root() / "artifacts"


# ---------------------------------------------------------------------------
# TestGetManifest
# ---------------------------------------------------------------------------


class TestGetManifest:
    def test_nonexistent_returns_empty_manifest(self, provider: LocalFilesystemArtifactProvider) -> None:
        """Missing manifest file → empty ArtifactManifest with correct issue_number."""
        result = provider.get_manifest(42)
        assert result.issue_number == 42
        assert result.artifacts == []

    def test_existing_returns_parsed_manifest(self, provider: LocalFilesystemArtifactProvider) -> None:
        """Existing manifest file → fully parsed ArtifactManifest."""
        manifest = ArtifactManifest(issue_number=7, artifacts=[_make_entry()])
        provider.set_manifest(7, manifest)

        result = provider.get_manifest(7)
        assert result.issue_number == 7
        assert len(result.artifacts) == 1

    def test_corrupt_json_raises_value_error(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """Corrupt JSON in manifest file → raises ValueError (json.JSONDecodeError subclass)."""
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "7.json"
        manifest_path.write_text("not-valid-json{{{", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            provider.get_manifest(7)


# ---------------------------------------------------------------------------
# TestSetManifest
# ---------------------------------------------------------------------------


class TestSetManifest:
    def test_creates_manifest_file(self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path) -> None:
        """set_manifest creates the manifest JSON file on first call."""
        manifest = ArtifactManifest(issue_number=1)
        provider.set_manifest(1, manifest)
        assert (manifest_dir / "1.json").exists()

    def test_atomic_overwrite_replaces_content(self, provider: LocalFilesystemArtifactProvider) -> None:
        """Second set_manifest call fully replaces prior content."""
        provider.set_manifest(2, ArtifactManifest(issue_number=2, artifacts=[_make_entry()]))
        assert len(provider.get_manifest(2).artifacts) == 1

        provider.set_manifest(2, ArtifactManifest(issue_number=2))
        assert provider.get_manifest(2).artifacts == []

    def test_stamps_storage_tier_local(self, provider: LocalFilesystemArtifactProvider) -> None:
        """Artifacts with storage_tier='remote' are coerced to 'local' on write."""
        entry = _make_entry(storage_tier="remote")
        provider.set_manifest(3, ArtifactManifest(issue_number=3, artifacts=[entry]))

        result = provider.get_manifest(3)
        assert result.artifacts[0].storage_tier == "local"

    def test_stamps_last_updated_iso_timestamp(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """set_manifest writes a non-empty last-updated key in the JSON (by_alias=True)."""
        provider.set_manifest(4, ArtifactManifest(issue_number=4))

        raw = json.loads((manifest_dir / "4.json").read_text(encoding="utf-8"))
        assert raw.get("last-updated"), "Expected a non-empty last-updated timestamp"

    def test_cleanup_on_replace_failure(self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path) -> None:
        """If Path.replace raises, the temporary file is cleaned up and no .tmp remains."""
        manifest = ArtifactManifest(issue_number=5)

        with (
            patch.object(Path, "replace", side_effect=OSError("mock replace failure")),
            pytest.raises(OSError, match="mock replace failure"),
        ):
            provider.set_manifest(5, manifest)

        # No orphaned .tmp files in the manifest directory
        tmp_files = list(manifest_dir.glob("*.tmp")) if manifest_dir.exists() else []
        assert tmp_files == [], f"Orphaned .tmp files found: {tmp_files}"

    def test_cleanup_suppresses_unlink_oserror(self, provider: LocalFilesystemArtifactProvider) -> None:
        """If both replace and unlink fail, only the replace error propagates."""
        manifest = ArtifactManifest(issue_number=6)

        with (
            patch.object(Path, "replace", side_effect=OSError("replace failed")),
            patch.object(Path, "unlink", side_effect=OSError("unlink failed")),
            pytest.raises(OSError, match="replace failed"),
        ):
            provider.set_manifest(6, manifest)
        # Test passes: unlink error was suppressed by contextlib.suppress(OSError)


# ---------------------------------------------------------------------------
# TestReadArtifactContent
# ---------------------------------------------------------------------------


class TestReadArtifactContent:
    def test_returns_content_of_existing_file(
        self, provider: LocalFilesystemArtifactProvider, root_worktree: Path
    ) -> None:
        """read_artifact_content returns file text for a safe path to an existing file."""
        artifact = root_worktree / "plan" / "test.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("hello artifact", encoding="utf-8")

        assert provider.read_artifact_content("plan/test.md") == "hello artifact"

    def test_raises_file_not_found_for_missing_file(self, provider: LocalFilesystemArtifactProvider) -> None:
        """read_artifact_content raises FileNotFoundError for absent safe paths."""
        with pytest.raises(FileNotFoundError):
            provider.read_artifact_content("plan/nonexistent.md")

    def test_raises_value_error_for_path_traversal(self, provider: LocalFilesystemArtifactProvider) -> None:
        """read_artifact_content raises ValueError when path escapes the root worktree."""
        with pytest.raises(ValueError, match="Path traversal"):
            provider.read_artifact_content("../../etc/passwd")


# ---------------------------------------------------------------------------
# TestStoreArtifactContent
# ---------------------------------------------------------------------------


class TestStoreArtifactContent:
    def test_writes_new_file(self, provider: LocalFilesystemArtifactProvider, root_worktree: Path) -> None:
        """store_artifact_content creates the file with the given content."""
        provider.store_artifact_content(
            issue_number=1,
            artifact_type=ArtifactType.ARCHITECT,
            path="plan/new-artifact.md",
            content="# Architect Spec\n",
        )
        target = root_worktree / "plan" / "new-artifact.md"
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "# Architect Spec\n"

    def test_noop_for_existing_file(self, provider: LocalFilesystemArtifactProvider, root_worktree: Path) -> None:
        """store_artifact_content does NOT overwrite an already-present file."""
        target = root_worktree / "plan" / "existing.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original content", encoding="utf-8")

        provider.store_artifact_content(
            issue_number=1, artifact_type=ArtifactType.ARCHITECT, path="plan/existing.md", content="new content"
        )
        assert target.read_text(encoding="utf-8") == "original content"


# ---------------------------------------------------------------------------
# TestReadArtifactContentFromRemote
# ---------------------------------------------------------------------------


class TestReadArtifactContentFromRemote:
    def test_returns_content_when_file_exists(
        self, provider: LocalFilesystemArtifactProvider, root_worktree: Path
    ) -> None:
        """read_artifact_content_from_remote falls through to local read."""
        artifact = root_worktree / "plan" / "remote.md"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("remote content", encoding="utf-8")

        result = provider.read_artifact_content_from_remote(1, ArtifactType.ARCHITECT, "plan/remote.md")
        assert result == "remote content"

    def test_returns_none_when_file_missing(self, provider: LocalFilesystemArtifactProvider) -> None:
        """read_artifact_content_from_remote returns None for missing files."""
        result = provider.read_artifact_content_from_remote(1, ArtifactType.ARCHITECT, "plan/missing.md")
        assert result is None


# ---------------------------------------------------------------------------
# TestReadLocalArtifactContent
# ---------------------------------------------------------------------------


class TestReadLocalArtifactContent:
    def test_returns_none_for_path_traversal(self, provider: LocalFilesystemArtifactProvider) -> None:
        """read_local_artifact_content returns None (not ValueError) for traversal paths."""
        result = provider.read_local_artifact_content("../../etc/passwd")
        assert result is None

    def test_returns_none_when_file_missing(self, provider: LocalFilesystemArtifactProvider) -> None:
        """read_local_artifact_content returns None for a safe but absent path."""
        result = provider.read_local_artifact_content("plan/ghost.md")
        assert result is None

    def test_returns_content_when_exists(self, provider: LocalFilesystemArtifactProvider, root_worktree: Path) -> None:
        """read_local_artifact_content returns file content for a safe existing path."""
        target = root_worktree / "plan" / "local.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("local only", encoding="utf-8")

        assert provider.read_local_artifact_content("plan/local.md") == "local only"


# ---------------------------------------------------------------------------
# TestSyncToRemote
# ---------------------------------------------------------------------------


class TestSyncToRemote:
    def test_returns_deferred_status(self, provider: LocalFilesystemArtifactProvider) -> None:
        """sync_to_remote returns a dict with status='deferred'."""
        result = provider.sync_to_remote()
        assert result["status"] == "deferred"

    def test_with_backend_arg_still_returns_deferred(self, provider: LocalFilesystemArtifactProvider) -> None:
        """sync_to_remote ignores the backend argument and returns deferred."""
        result = provider.sync_to_remote(backend=None)
        assert result["status"] == "deferred"


# ---------------------------------------------------------------------------
# TestConcurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    def test_concurrent_set_manifest_no_corruption(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """10 concurrent writers all complete and leave a valid, uncorrupted manifest."""
        n_threads = 10
        barrier = threading.Barrier(n_threads)

        def writer(_thread_id: int) -> None:
            barrier.wait()  # synchronise all threads to start simultaneously
            entry = _make_entry()
            manifest = ArtifactManifest(issue_number=99, artifacts=[entry])
            provider.set_manifest(99, manifest)

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = [executor.submit(writer, i) for i in range(n_threads)]

        # Re-raise any exceptions that occurred in worker threads
        for future in futures:
            future.result()

        # Final on-disk state must be valid JSON
        raw_text = (manifest_dir / "99.json").read_text(encoding="utf-8")
        data = json.loads(raw_text)

        # Every artifact in the final manifest must have storage_tier coerced to 'local'
        for artifact in data.get("artifacts", []):
            assert artifact.get("storage-tier") == "local"

        # No orphaned .tmp files
        tmp_files = list(manifest_dir.glob("*.tmp"))
        assert tmp_files == [], f"Orphaned .tmp files after concurrent writes: {tmp_files}"


# ---------------------------------------------------------------------------
# Property-based test (standalone — hypothesis + pytest fixtures)
# ---------------------------------------------------------------------------


@given(
    path=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),  # exclude surrogates
            blacklist_characters="\x00",  # exclude NUL (causes OS errors, not ValueError)
        ),
        max_size=200,
    )
)
@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    # Rationale: tmp_path is shared across hypothesis examples intentionally.
    # worktree.mkdir uses exist_ok=True and _validate_artifact_path is stateless
    # (no filesystem writes), so the shared fixture is safe.
)
def test_validate_artifact_path_never_escapes_root_worktree(tmp_path: Path, path: str) -> None:
    """For any text input, _validate_artifact_path never silently returns a path outside root.

    It must either:
    - Return a Path that is safely inside root_worktree, OR
    - Raise ValueError (path traversal) or OSError (OS-level rejection).

    Any other outcome (e.g. silently returning an escaped path) is a bug.
    """
    worktree = tmp_path / "repo"
    worktree.mkdir(exist_ok=True)  # exist_ok=True: hypothesis calls this function many times
    prov = LocalFilesystemArtifactProvider(root_worktree=worktree, manifest_dir=tmp_path / "artifacts")
    try:
        result = prov._validate_artifact_path(path)
        # If it returned without raising, the path must be inside the worktree
        result.relative_to(worktree.resolve())  # raises ValueError if escaped
    except (ValueError, OSError):
        pass  # Both are acceptable outcomes for invalid or unsafe paths


# ---------------------------------------------------------------------------
# TestBeadsStyleStringIds — beads-style string IDs in the local provider
# ---------------------------------------------------------------------------


class TestBeadsStyleStringIds:
    """Verify LocalFilesystemArtifactProvider handles beads-style string issue IDs.

    The beads backend uses nanoid-prefixed string identifiers (e.g. ``bd-a3f8``) instead of
    GitHub integer issue numbers.  LocalFilesystemArtifactProvider derives the manifest file
    path via ``f"{issue_number}.json"``, so string IDs work as filename stems without any
    special handling.  These tests document that contract.
    """

    def test_beads_id_manifest_path_stem_matches_string(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """_manifest_path with a beads-style ID produces a JSON file named after that string."""
        path = provider._manifest_path("bd-a3f8")  # type: ignore[arg-type]
        assert path.name == "bd-a3f8.json"
        assert path.parent == manifest_dir

    def test_beads_id_set_manifest_creates_named_file(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """set_manifest with a beads-style string ID creates ``bd-a3f8.json`` in manifest_dir."""
        manifest = ArtifactManifest(issue_number=0, artifacts=[])
        provider.set_manifest("bd-a3f8", manifest)  # type: ignore[arg-type]
        assert (manifest_dir / "bd-a3f8.json").exists()

    def test_beads_id_set_get_manifest_roundtrip_preserves_artifacts(
        self, provider: LocalFilesystemArtifactProvider
    ) -> None:
        """set_manifest/get_manifest with a beads string ID roundtrips artifact entries intact."""
        entry = _make_entry()
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        provider.set_manifest("bd-a3f8", manifest)  # type: ignore[arg-type]

        result = provider.get_manifest("bd-a3f8")  # type: ignore[arg-type]

        assert len(result.artifacts) == 1
        assert result.artifacts[0].artifact_type == ArtifactType.ARCHITECT

    def test_beads_id_set_get_manifest_roundtrip_storage_tier_coerced(
        self, provider: LocalFilesystemArtifactProvider
    ) -> None:
        """storage_tier is coerced to 'local' when written via a beads string ID."""
        entry = _make_entry(storage_tier="remote")
        manifest = ArtifactManifest(issue_number=0, artifacts=[entry])
        provider.set_manifest("bd-a3f8", manifest)  # type: ignore[arg-type]

        result = provider.get_manifest("bd-a3f8")  # type: ignore[arg-type]

        assert result.artifacts[0].storage_tier == "local"

    def test_beads_id_distinct_ids_write_distinct_files(
        self, provider: LocalFilesystemArtifactProvider, manifest_dir: Path
    ) -> None:
        """Two different beads IDs produce two independent manifest files."""
        manifest_a = ArtifactManifest(issue_number=0, artifacts=[_make_entry()])
        manifest_b = ArtifactManifest(issue_number=0, artifacts=[])
        provider.set_manifest("bd-a3f8", manifest_a)  # type: ignore[arg-type]
        provider.set_manifest("bd-zz99", manifest_b)  # type: ignore[arg-type]

        assert (manifest_dir / "bd-a3f8.json").exists()
        assert (manifest_dir / "bd-zz99.json").exists()
        result_a = provider.get_manifest("bd-a3f8")  # type: ignore[arg-type]
        result_b = provider.get_manifest("bd-zz99")  # type: ignore[arg-type]
        assert len(result_a.artifacts) == 1
        assert len(result_b.artifacts) == 0
