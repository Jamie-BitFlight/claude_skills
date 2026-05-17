"""Beads CLI artifact provider — full implementation (T09).

Stores artifact manifests in bd metadata (``dh.artifacts`` key) and artifact
content in bd notes using sentinel-delimited blocks.

Manifest storage
----------------
Manifests are serialised as compact JSON and stored via:

.. code-block:: shell

    bd update <issue-id> --metadata "dh.artifacts=<json>"

They are read back via ``bd show <issue-id> --json`` and extracted from
``metadata["dh"]["artifacts"]`` (nested) or ``metadata["dh.artifacts"]``
(flat key), whichever is present.

Content storage
---------------
Each content block is written into the issue's ``notes`` field using an
open/close sentinel pair:

.. code-block:: text

    <!-- artifact-content:type=<artifact_type>:id=<path> -->
    <content>
    <!-- /artifact-content:type=<artifact_type>:id=<path> -->

When a block with the same ``type`` and ``id`` already exists it is replaced
in-place; otherwise it is appended to the notes.

ADR-002 type widening
---------------------
The :class:`~backlog_core.artifact_provider.ArtifactBackend` Protocol defines
``issue_number: int`` parameters, but the beads backend uses string issue IDs
(e.g. ``bd-a3f8``).  The Protocol methods raise :exc:`NotImplementedError`
when called with an actual ``int``.  All beads-aware callers should use the
shadow ``*_bd(issue_id: str)`` methods directly.

At runtime the Protocol methods also accept ``str`` values transparently (type
widening), so code that has already resolved a beads ID string and stores it
in a variable typed as ``int`` will work correctly — this matches the widened
behaviour described in ADR-002.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from backlog_core.backends.bd_runner import BdRunner
from backlog_core.backends.beads_models import BeadsIssueRaw, parse_issue
from backlog_core.models import ArtifactManifest

# dh_paths lives one level above backlog_core (at plugin root).
_plugin_root = Path(__file__).parent.parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import dh_paths as _dh_paths

__all__ = ["BeadsArtifactProvider"]

# ---------------------------------------------------------------------------
# Sentinel templates for note-embedded content blocks
# ---------------------------------------------------------------------------

_SENTINEL_OPEN_TMPL: str = "<!-- artifact-content:type={artifact_type}:id={path} -->"
_SENTINEL_CLOSE_TMPL: str = "<!-- /artifact-content:type={artifact_type}:id={path} -->"

# Metadata key under which the manifest JSON is stored.
_DH_ARTIFACTS_KEY: str = "dh.artifacts"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_manifest_from_metadata(metadata: dict[str, object]) -> ArtifactManifest | None:
    """Extract an ``ArtifactManifest`` from a bd metadata dict.

    Tries the nested representation ``{"dh": {"artifacts": ...}}`` first, then
    the flat-key representation ``{"dh.artifacts": ...}``.  Returns ``None``
    when neither key is present.

    Parameters
    ----------
    metadata:
        The ``metadata`` dict from a parsed :class:`~beads_models.BeadsIssueRaw`.

    Returns:
    -------
    ArtifactManifest | None
        Parsed manifest, or ``None`` when no manifest data is present.

    Raises:
    ------
    json.JSONDecodeError
        When the stored value is a string that is not valid JSON.
    pydantic.ValidationError
        When the decoded value does not match the ``ArtifactManifest`` schema.
    """
    # Try nested: metadata["dh"]["artifacts"]
    dh_section_raw = metadata.get("dh")
    if isinstance(dh_section_raw, dict):
        # cast: ty cannot infer dict type params from isinstance narrowing on `object`
        dh_section = cast("dict[str, object]", dh_section_raw)
        artifacts_raw = dh_section.get("artifacts")
        if artifacts_raw is not None:
            return _parse_manifest_value(artifacts_raw)

    # Try flat: metadata["dh.artifacts"]
    flat_raw = metadata.get(_DH_ARTIFACTS_KEY)
    if flat_raw is not None:
        return _parse_manifest_value(flat_raw)

    return None


def _parse_manifest_value(raw: object) -> ArtifactManifest:
    """Decode a raw manifest value into an ``ArtifactManifest``.

    Parameters
    ----------
    raw:
        Either a JSON string or a dict representing the serialised manifest.

    Returns:
    -------
    ArtifactManifest
        The parsed manifest instance.

    Raises:
    ------
    json.JSONDecodeError
        When *raw* is a string that is not valid JSON.
    pydantic.ValidationError
        When the decoded structure does not match ``ArtifactManifest``.
    ValueError
        When *raw* is neither a ``str`` nor a ``dict``.
    """
    if isinstance(raw, str):
        data = json.loads(raw)
        return ArtifactManifest.model_validate(data)
    if isinstance(raw, dict):
        return ArtifactManifest.model_validate(raw)
    raise ValueError(f"Unexpected manifest value type {type(raw).__name__!r}; expected str or dict.")


def _extract_content_block(notes: str, artifact_type: str, path: str) -> str | None:
    """Extract content between sentinel markers from a notes string.

    Parameters
    ----------

    Notes:
        Raw notes text to search.
    artifact_type:
        Artifact type string used in the sentinel (e.g. ``"architect"``).
    path:
        Logical artifact identifier used as the block ``id``.

    Returns:
    -------
    str | None
        Content string between the sentinels, or ``None`` when not found.
    """
    open_sentinel = _SENTINEL_OPEN_TMPL.format(artifact_type=artifact_type, path=path)
    close_sentinel = _SENTINEL_CLOSE_TMPL.format(artifact_type=artifact_type, path=path)

    pattern = re.escape(open_sentinel) + r"\n(.*?)\n" + re.escape(close_sentinel)
    match = re.search(pattern, notes, flags=re.DOTALL)
    if match is None:
        return None
    return match.group(1)


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------


class BeadsArtifactProvider:
    """Beads CLI implementation of the ``ArtifactBackend`` Protocol.

    Stores artifact manifests in bd metadata (``dh.artifacts`` key) and
    artifact content in bd notes as sentinel-delimited blocks.

    Instantiation is **filesystem-free** and **subprocess-free**: the
    :class:`~bd_runner.BdRunner` is created lazily on the first call, and
    the repository root is resolved lazily from
    :func:`dh_paths.git_project_root` on the first path-safety check.

    Args:
        runner: Optional pre-constructed :class:`~bd_runner.BdRunner`.  When
            ``None``, a default ``BdRunner()`` is created on the first
            ``run_json`` or ``run_text`` call.

    Example::

        provider = BeadsArtifactProvider()
        manifest = provider.get_manifest_bd("bd-a3f8")
        print(manifest.artifacts)
    """

    def __init__(self, *, runner: BdRunner | None = None) -> None:
        """Store configuration only.  Does not touch the filesystem or subprocess."""
        self._runner_instance: BdRunner | None = runner
        self._root_worktree: Path | None = None

    # -----------------------------------------------------------------------
    # ArtifactBackend Protocol implementation
    # -----------------------------------------------------------------------

    def get_manifest(self, issue_number: str | int) -> ArtifactManifest:
        """Retrieve the artifact manifest.

        Accepts a beads string ID at runtime (ADR-002 type widening).
        Raises when called with an actual ``int``, since beads does not use
        integer issue numbers.

        Args:
            issue_number: Beads string ID accepted at runtime (e.g.
                ``"bd-a3f8"``).  Actual ``int`` values raise
                :exc:`NotImplementedError`.

        Returns:
            ``ArtifactManifest``.  Empty manifest (no artifacts) when no
            manifest is stored — this is not an error.

        Raises:
            NotImplementedError: When *issue_number* is an actual ``int``.
        """
        if isinstance(issue_number, str):
            return self.get_manifest_bd(issue_number)
        raise NotImplementedError(
            "BeadsArtifactProvider does not support integer issue numbers. "
            "Call get_manifest_bd(issue_id: str) with a beads ID instead."
        )

    def set_manifest(self, issue_number: str | int, manifest: ArtifactManifest) -> None:
        """Persist *manifest*.

        Accepts a beads string ID at runtime (ADR-002 type widening).
        Raises when called with an actual ``int``.

        Args:
            issue_number: Beads string ID accepted at runtime.  Actual
                ``int`` values raise :exc:`NotImplementedError`.
            manifest: Updated manifest to persist.

        Raises:
            NotImplementedError: When *issue_number* is an actual ``int``.
        """
        if isinstance(issue_number, str):
            self.set_manifest_bd(issue_number, manifest)
            return
        raise NotImplementedError(
            "BeadsArtifactProvider does not support integer issue numbers. "
            "Call set_manifest_bd(issue_id: str, manifest) with a beads ID instead."
        )

    def read_artifact_content(self, path: str) -> str:
        """Read artifact file content from the root worktree.

        Args:
            path: Repo-relative path to the artifact file (e.g.
                ``plan/architect-foo.md``).  Must not escape the repository
                root.

        Returns:
            Raw UTF-8 file content.

        Raises:
            ValueError: When *path* resolves outside the repository root
                (path traversal detected).
            FileNotFoundError: When the file does not exist.
        """
        self._validate_artifact_path(path)
        resolved = (self._resolved_root_worktree / path).resolve()
        return resolved.read_text(encoding="utf-8")

    def store_artifact_content(self, issue_number: str | int, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content in bd notes as a sentinel-delimited block.

        Accepts a beads string ID at runtime (ADR-002 type widening).
        Raises when called with an actual ``int``.

        Args:
            issue_number: Beads string ID accepted at runtime.  Actual
                ``int`` values raise :exc:`NotImplementedError`.
            artifact_type: Artifact type string (e.g. ``"research"``).
            path: Logical artifact identifier used as the block ``id``.
            content: Full artifact content to store.

        Raises:
            NotImplementedError: When *issue_number* is an actual ``int``.
        """
        if isinstance(issue_number, str):
            self.store_artifact_content_bd(issue_number, artifact_type, path, content)
            return
        raise NotImplementedError(
            "BeadsArtifactProvider does not support integer issue numbers. "
            "Call store_artifact_content_bd(issue_id: str, ...) with a beads ID instead."
        )

    def read_artifact_content_from_remote(self, issue_number: str | int, artifact_type: str, path: str) -> str | None:
        """Search bd notes for a stored artifact content block.

        Accepts a beads string ID at runtime (ADR-002 type widening).
        Raises when called with an actual ``int``.

        Args:
            issue_number: Beads string ID accepted at runtime.  Actual
                ``int`` values raise :exc:`NotImplementedError`.
            artifact_type: Artifact type string to match.
            path: Logical artifact identifier to match.

        Returns:
            The stored content string when found, or ``None`` when no
            matching block exists.

        Raises:
            NotImplementedError: When *issue_number* is an actual ``int``.
        """
        if isinstance(issue_number, str):
            return self.read_artifact_content_from_remote_bd(issue_number, artifact_type, path)
        raise NotImplementedError(
            "BeadsArtifactProvider does not support integer issue numbers. "
            "Call read_artifact_content_from_remote_bd(issue_id: str, ...) with a beads ID instead."
        )

    def read_local_artifact_content(self, path: str) -> str | None:
        """Read artifact file content from the local filesystem.

        Same as :meth:`read_artifact_content` but returns ``None`` when the
        file does not exist rather than raising :exc:`FileNotFoundError`.
        Used by ``artifact_register`` to auto-upload local file content.

        Args:
            path: Repo-relative path to the artifact file.

        Returns:
            Raw UTF-8 file content, or ``None`` when the file does not exist.

        Raises:
            ValueError: When *path* resolves outside the repository root.
        """
        self._validate_artifact_path(path)
        resolved = (self._resolved_root_worktree / path).resolve()
        if not resolved.exists():
            return None
        return resolved.read_text(encoding="utf-8")

    # -----------------------------------------------------------------------
    # Shadow methods — beads-native API accepting str issue IDs
    # -----------------------------------------------------------------------

    def get_manifest_bd(self, issue_id: str) -> ArtifactManifest:
        """Retrieve the artifact manifest for a beads issue.

        Fetches issue JSON via ``bd show <issue_id> --json`` and extracts
        the ``dh.artifacts`` manifest from the ``metadata`` field.  Returns
        an empty manifest (no artifacts) when no manifest data is present —
        this is not an error.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).

        Returns:
            ``ArtifactManifest``.  ``issue_number`` is ``0`` for manifests
            returned from the beads backend (no integer ID applies).

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd show`` fails.
            pydantic.ValidationError: When the stored manifest JSON is corrupt.
        """
        manifest, _ = self._fetch_issue_and_manifest(issue_id)
        return manifest

    def set_manifest_bd(self, issue_id: str, manifest: ArtifactManifest) -> None:
        """Persist *manifest* for a beads issue.

        Serialises the manifest as compact JSON and stores it via
        ``bd update <issue_id> --metadata "dh.artifacts=<json>"``.
        Stamps ``last_updated`` to the current UTC ISO-8601 timestamp before
        persisting.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).
            manifest: Updated manifest to persist.

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd update`` fails.
        """
        stamped = manifest.model_copy(update={"last_updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
        manifest_json = stamped.model_dump_json(by_alias=True)
        # --set-metadata sets a single key=value; --metadata expects a full JSON object.
        self._runner.run_text(["update", issue_id, "--set-metadata", f"{_DH_ARTIFACTS_KEY}={manifest_json}"])

    def store_artifact_content_bd(self, issue_id: str, artifact_type: str, path: str, content: str) -> None:
        """Store artifact content in bd notes as a sentinel-delimited block.

        Fetches the current notes, then either replaces an existing block
        with matching ``type`` and ``id`` or appends a new block.  The
        updated notes are written back via ``bd update <issue_id> --notes``.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).
            artifact_type: Artifact type string (e.g. ``"architect"``).
            path: Logical artifact identifier used as the block ``id``.
            content: Full artifact content to store.

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd show`` or ``bd update`` fails.
        """
        raw = self._runner.run_json(["show", issue_id])
        issue = parse_issue(raw)
        current_notes = issue.notes or ""

        open_sentinel = _SENTINEL_OPEN_TMPL.format(artifact_type=artifact_type, path=path)
        close_sentinel = _SENTINEL_CLOSE_TMPL.format(artifact_type=artifact_type, path=path)
        block = f"{open_sentinel}\n{content}\n{close_sentinel}"

        if open_sentinel in current_notes:
            # Replace existing block in-place.
            pattern = re.escape(open_sentinel) + r".*?" + re.escape(close_sentinel)
            new_notes = re.sub(pattern, block, current_notes, flags=re.DOTALL)
        elif current_notes:
            separator = "\n\n" if not current_notes.endswith("\n") else "\n"
            new_notes = current_notes + separator + block
        else:
            new_notes = block

        self._runner.run_text(["update", issue_id, "--notes", new_notes])

    def read_artifact_content_from_remote_bd(self, issue_id: str, artifact_type: str, path: str) -> str | None:
        """Search bd notes for a stored artifact content block.

        Fetches issue JSON and scans the ``notes`` field for a sentinel block
        matching *artifact_type* and *path*.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).
            artifact_type: Artifact type string to match.
            path: Logical artifact identifier to match.

        Returns:
            The stored content string when found, or ``None`` when no
            matching block exists.

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd show`` fails.
        """
        raw = self._runner.run_json(["show", issue_id])
        issue = parse_issue(raw)
        notes = issue.notes or ""
        return _extract_content_block(notes, artifact_type, path)

    def delete_entry(self, issue_number: int, artifact_type: str, path: str) -> None:
        """Remove an artifact entry from the manifest and its content block from notes.

        Accepts a beads string ID at runtime (ADR-002 type widening).
        Raises when called with an actual ``int``.

        Args:
            issue_number: Beads string ID accepted at runtime.  Actual
                ``int`` values raise :exc:`NotImplementedError`.
            artifact_type: Artifact type string to match.
            path: Logical artifact identifier to match.

        Raises:
            NotImplementedError: When *issue_number* is an actual ``int``.
        """
        if isinstance(issue_number, str):
            self.delete_entry_bd(issue_number, artifact_type, path)
            return
        raise NotImplementedError(
            "BeadsArtifactProvider does not support integer issue numbers. "
            "Call delete_entry_bd(issue_id: str, ...) with a beads ID instead."
        )

    def delete_entry_bd(self, issue_id: str, artifact_type: str, path: str) -> None:
        """Remove an artifact entry from the manifest and its content block from notes.

        Reads the current manifest and notes in a single ``bd show`` call,
        removes the manifest entry matching *artifact_type* and *path*, persists
        the updated manifest if changed, then strips the corresponding sentinel
        block from the issue notes.  Both manifest and notes are updated
        independently — a missing entry in one location does not prevent cleanup
        in the other.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).
            artifact_type: Artifact type string to match.
            path: Logical artifact identifier to match.

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd show`` or ``bd update`` fails.
        """
        # Single fetch supplies both manifest and notes; set_manifest_bd only
        # writes metadata (--set-metadata), so the cached notes remain valid.
        manifest, issue = self._fetch_issue_and_manifest(issue_id)

        # Step 1: Update manifest (filter out matching entry).
        updated_artifacts = [
            e for e in manifest.artifacts if not (e.artifact_type == artifact_type and e.artifact_id == path)
        ]
        if len(updated_artifacts) != len(manifest.artifacts):
            updated_manifest = manifest.model_copy(update={"artifacts": updated_artifacts})
            self.set_manifest_bd(issue_id, updated_manifest)

        # Step 2: Strip content block from notes.
        current_notes = issue.notes or ""
        if not current_notes:
            return

        open_sentinel = _SENTINEL_OPEN_TMPL.format(artifact_type=artifact_type, path=path)
        if open_sentinel not in current_notes:
            return

        close_sentinel = _SENTINEL_CLOSE_TMPL.format(artifact_type=artifact_type, path=path)
        pattern = re.escape(open_sentinel) + r".*?" + re.escape(close_sentinel)
        new_notes = re.sub(pattern, "", current_notes, flags=re.DOTALL)
        # Collapse surplus blank lines left by the removal, then strip trailing whitespace.
        new_notes = re.sub(r"\n{3,}", "\n\n", new_notes).strip()
        self._runner.run_text(["update", issue_id, "--notes", new_notes])

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _fetch_issue_and_manifest(self, issue_id: str) -> tuple[ArtifactManifest, BeadsIssueRaw]:
        """Fetch a beads issue and extract its artifact manifest in one call.

        Issues a single ``bd show <issue_id> --json`` request and returns both
        the parsed ``ArtifactManifest`` (empty when absent) and the raw
        ``BeadsIssueRaw`` model.  Callers that need both manifest and notes
        should use this helper to avoid redundant subprocess invocations.

        Args:
            issue_id: Beads issue ID string (e.g. ``"bd-a3f8"``).

        Returns:
            Tuple of ``(ArtifactManifest, BeadsIssueRaw)``.  The manifest is
            an empty ``ArtifactManifest(issue_number=0)`` when no manifest
            data is stored on the issue.

        Raises:
            bd_runner.BdNotInstalledError: When ``bd`` is not on ``PATH``.
            bd_runner.BdInvocationError: When ``bd show`` fails.
            pydantic.ValidationError: When the stored manifest JSON is corrupt.
        """
        raw = self._runner.run_json(["show", issue_id])
        issue = parse_issue(raw)
        if issue.metadata is None:
            return ArtifactManifest(issue_number=0), issue
        manifest = _extract_manifest_from_metadata(issue.metadata)
        if manifest is None:
            return ArtifactManifest(issue_number=0), issue
        return manifest, issue

    @property
    def _runner(self) -> BdRunner:
        """Lazily construct and return the :class:`~bd_runner.BdRunner`."""
        if self._runner_instance is None:
            self._runner_instance = BdRunner()
        return self._runner_instance

    @property
    def _resolved_root_worktree(self) -> Path:
        """Lazily resolve and cache the git project root via ``dh_paths``."""
        if self._root_worktree is None:
            self._root_worktree = _dh_paths.git_project_root()
        return self._root_worktree

    def _validate_artifact_path(self, path: str) -> None:
        """Raise ``ValueError`` when *path* fails the path traversal check.

        The resolved absolute path must be a descendant of the repository root.
        No directory prefix restriction is applied — any repo-relative path is
        permitted as long as it stays inside the root.

        Args:
            path: Repo-relative path string as provided by the caller.

        Raises:
            ValueError: When the resolved path escapes the repository root.
        """
        root = self._resolved_root_worktree
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            raise ValueError(f"Path traversal detected: {path!r} resolves outside the repository root.") from None
