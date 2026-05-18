"""Local filesystem implementation of the ArtifactBackend protocol.

Stores artifact manifests at ``~/.dh/projects/{slug}/artifacts/{issue_number}.json``
(one file per issue, matching architect ADR-001) and artifact content files at
``{root_worktree}/{artifact_id}`` (same convention as remote providers).

Advisory locking via ``fcntl.flock(LOCK_EX)`` on a per-issue ``.lock`` file
prevents manifest corruption under concurrent writes.  Reads are lock-free
because ``os.replace`` is atomic — a reader sees either the old or the new
manifest, never a partial write.

All writes are atomic: content is written to a temporary file, then
``os.replace`` replaces the target atomically.  The temporary file is deleted
on failure via a ``try/finally`` guard.

Lock files are never deleted (TOCTOU risk per architect ADR-003).

Uses only the standard library (``json``, ``os``, ``fcntl``, ``tempfile``,
``pathlib``, ``datetime``, ``typing``), plus Pydantic models already available
in this package.
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from backlog_core.models import ArtifactEntry, ArtifactManifest

# dh_paths lives one level above backlog_core (at plugin root).
_plugin_root = Path(__file__).parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import contextlib

import dh_paths as _dh_paths

if TYPE_CHECKING:
    # Imported for type annotations only.  At runtime this module may be loaded
    # before artifact_provider.py (T03 wires the two together), so the runtime
    # import is deferred to TYPE_CHECKING to avoid a circular import.
    from backlog_core.artifact_provider import ArtifactBackend


class LocalFilesystemArtifactProvider:
    """Local filesystem implementation of the :class:`~backlog_core.artifact_provider.ArtifactBackend` protocol.

    Stores manifests at ``{manifest_dir}/{issue_number}.json`` using atomic
    writes protected by advisory ``fcntl.flock(LOCK_EX)`` on a per-issue
    ``.lock`` file.  Artifact content files are written to
    ``{root_worktree}/{artifact_id}`` — the same repo-relative convention used
    by remote providers.

    This provider activates automatically when no remote backend is reachable
    (fallback chain in ``server._get_artifact_provider``).  It can also be
    selected explicitly via ``BACKLOG_BACKEND=local``.

    Args:
        root_worktree: Absolute path to the repository root worktree.  Artifact
            content files are read and written relative to this directory.
        manifest_dir: Directory for per-issue manifest JSON files.  Defaults to
            ``dh_paths.state_root() / "artifacts"`` when ``None``.

    Example::

        provider = LocalFilesystemArtifactProvider(root_worktree=Path("/repo"))
        manifest = provider.get_manifest(965)
        print(manifest.artifacts)
    """

    def __init__(self, root_worktree: Path, manifest_dir: Path | None = None) -> None:
        """Initialise the local provider.

        Args:
            root_worktree: Absolute path to the repository root worktree.
            manifest_dir: Directory for per-issue manifest files.  When
                ``None``, defaults to ``dh_paths.state_root() / "artifacts"``.
        """
        self._root_worktree = root_worktree
        self._manifest_dir: Path = manifest_dir if manifest_dir is not None else _dh_paths.state_root() / "artifacts"

    # ------------------------------------------------------------------
    # ArtifactBackend protocol implementation
    # ------------------------------------------------------------------

    def get_manifest(self, issue_number: str | int) -> ArtifactManifest:
        """Retrieve the artifact manifest for *issue_number*.

        Returns an empty manifest when no manifest file exists for the issue —
        this is not an error.  Reads are lock-free (``os.replace`` atomicity
        guarantees a reader sees either the old or new file, never torn data).

        Args:
            issue_number: Issue number (positive integer).

        Returns:
            ``ArtifactManifest`` for the issue.  Empty manifest when no file
            exists.

        Raises:
            ValueError: When the manifest file exists but contains invalid JSON
                (``json.JSONDecodeError`` is a subclass of ``ValueError``).
        """
        manifest_path = self._manifest_path(issue_number)
        if not manifest_path.exists():
            # Use 0 as a sentinel when issue_number is a beads string — the manifest
            # field is typed int, but the local provider stores by filename stem only.
            issue_int = issue_number if isinstance(issue_number, int) else 0
            return ArtifactManifest(issue_number=issue_int)
        content = manifest_path.read_text(encoding="utf-8")
        # json.loads raises json.JSONDecodeError (a ValueError subclass) for corrupt JSON.
        # Using two-step parse so corrupt JSON raises ValueError, not pydantic.ValidationError.
        data = json.loads(content)
        return ArtifactManifest.model_validate(data)

    def set_manifest(self, issue_number: str | int, manifest: ArtifactManifest) -> None:
        """Persist *manifest* for *issue_number* atomically.

        Acquires an exclusive advisory lock on the per-issue lock file before
        writing, then writes to a temporary file and replaces the target
        atomically via ``os.replace``.  The temporary file is deleted on any
        failure.  Lock files are never deleted.

        Stamps ``last_updated`` to the current UTC ISO 8601 timestamp and
        ensures all entries carry ``storage_tier='local'`` before writing.

        Args:
            issue_number: Issue number (positive integer).
            manifest: Updated manifest to persist.
        """
        manifest_path = self._manifest_path(issue_number)
        lock_path = self._lock_path(issue_number)

        # Create the manifest directory on first write (mode 0o700 — not world-readable).
        manifest_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Enforce storage_tier='local' on all entries and stamp last_updated.
        local_artifacts: list[ArtifactEntry] = [
            e.model_copy(update={"storage_tier": "local"}) for e in manifest.artifacts
        ]
        stamped = manifest.model_copy(
            update={"artifacts": local_artifacts, "last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
        )
        content = stamped.model_dump_json(by_alias=True)

        # Open (or create) the lock file in append mode.  Never delete it.
        lock_fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            tmp_path: str | None = None
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=str(manifest_path.parent), suffix=".tmp", delete=False
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(content)
            # tmp is closed; tmp_path is the written-but-not-yet-replaced file.
            try:
                Path(tmp_path).replace(str(manifest_path))
                tmp_path = None  # replace succeeded — no cleanup needed
            finally:
                if tmp_path is not None:
                    # Replace failed; delete the orphaned temporary file.
                    with contextlib.suppress(OSError):
                        Path(tmp_path).unlink()
        finally:
            os.close(lock_fd)

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree.

        Args:
            path: Repo-relative path to the artifact file (e.g.
                ``plan/architect-foo.md``).

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* resolves outside the repository root
                (path traversal detected).
            FileNotFoundError: When the file does not exist.
        """
        resolved = self._validate_artifact_path(path)
        return resolved.read_text(encoding="utf-8")

    def store_artifact_content(self, issue_number: str | int, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content as a file in the repository worktree.

        Writes content only when the target file does **not** already exist.
        When the file is already present this method is a no-op (idempotent).
        Manifest updates are the caller's responsibility via :meth:`set_manifest`.

        Args:
            issue_number: Issue number (positive integer or beads string).  Not used by this
                provider — included to satisfy the :class:`ArtifactBackend`
                protocol.
            artifact_type: Artifact type string (e.g. ``"research"``).  Not
                used by this provider.
            path: Repo-relative path to write the artifact to.
            content: Full artifact content (UTF-8 string).

        Raises:
            ValueError: When *path* resolves outside the repository root.
        """
        target = self._validate_artifact_path(path)
        if target.exists():
            return  # no-op when the file already exists (Q7 resolution)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_artifact_content_from_remote(self, issue_number: str | int, artifact_type: str, path: str) -> str | None:
        """Read artifact content.

        This provider has no remote backend.  Delegates to
        :meth:`read_local_artifact_content`.

        Args:
            issue_number: Issue number (positive integer or beads string).  Not used.
            artifact_type: Artifact type string.  Not used.
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file is missing or
            the path is unsafe.
        """
        return self.read_local_artifact_content(path)

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content without raising on missing file or unsafe path.

        Unlike :meth:`read_artifact_content`, this method returns ``None``
        for both unsafe paths (path traversal) and missing files.  It never
        raises — callers that require an exception on missing files should use
        :meth:`read_artifact_content` instead.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not exist
            or *path* resolves outside the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            return None  # unsafe path — return None, do not raise
        if not candidate.exists():
            return None
        return candidate.read_text(encoding="utf-8")

    def sync_to_remote(self, backend: ArtifactBackend | None = None) -> dict[str, str]:
        """Stub sync — this provider stores artifacts locally only.

        No remote backend is configured; sync is deferred.

        Args:
            backend: Unused.  Accepted to satisfy the ``sync_to_remote``
                convention used by callers that support remote sync.

        Returns:
            ``{"status": "deferred", "reason": "local provider has no configured remote"}``
        """
        return {"status": "deferred", "reason": "local provider has no configured remote"}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _manifest_path(self, issue_number: str | int) -> Path:
        """Return the path to the manifest JSON file for *issue_number*.

        Args:
            issue_number: Issue number (integer or beads string — used as filename stem).

        Returns:
            Absolute path: ``{manifest_dir}/{issue_number}.json``.
        """
        return self._manifest_dir / f"{issue_number}.json"

    def _lock_path(self, issue_number: str | int) -> Path:
        """Return the path to the advisory lock file for *issue_number*.

        Lock files are created on first acquire and **never** deleted
        (TOCTOU risk per architect ADR-003).

        Args:
            issue_number: Issue number.

        Returns:
            Absolute path: ``{manifest_dir}/{issue_number}.lock``.
        """
        return self._manifest_dir / f"{issue_number}.lock"

    def _validate_artifact_path(self, path: str) -> Path:
        """Resolve *path* relative to the root worktree and check for traversal.

        Reuses the exact validation pattern from
        :class:`~backlog_core.artifact_provider.GitHubGistArtifactProvider`
        (lines 609-614 of ``artifact_provider.py``).

        Args:
            path: Repo-relative path string as provided by the caller.

        Returns:
            Resolved absolute :class:`~pathlib.Path` when the path is safe.

        Raises:
            ValueError: When the resolved path escapes the repository root.
        """
        candidate = (self._root_worktree / path).resolve()
        try:
            candidate.relative_to(self._root_worktree.resolve())
        except ValueError:
            msg = f"Path traversal detected: {path!r} resolves outside the repository root."
            raise ValueError(msg) from None
        return candidate
