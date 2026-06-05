"""Thin wrapper decoupling GistTaskLayer from the backlog_core artifact surface.

This module provides :class:`ArtifactRegistryClient`, which wraps the
``backlog_core`` artifact provider (``GitHubGistArtifactProvider``) to offer
a typed, SAM-oriented interface for storing and retrieving plan YAML content
via GitHub Gist.

Write contract (ADR-2509-5):
    ``store()`` raises :exc:`~sam_schema.core.exceptions.ArtifactWriteError`
    on any failure.  There is **no** silent fallback to local storage on the
    write path — a write that cannot reach Gist must not silently succeed.

Read contract (ADR-2509-5):
    ``read()`` fetches Gist-first and may fall back to local storage on a
    remote miss.  The caller is responsible for annotating the response to
    indicate which source was used.
"""

from __future__ import annotations

import logging

import backlog_core.models as _backlog_models
from backlog_core.artifact_provider import ArtifactBackend, create_artifact_provider
from backlog_core.artifact_registry import ArtifactRegistry
from backlog_core.models import ArtifactEntry, ArtifactStatus, ArtifactType, BacklogError

from .exceptions import ArtifactWriteError

_log = logging.getLogger(__name__)

#: Artifact type string for task-plan content.
_TASK_PLAN_TYPE = ArtifactType.TASK_PLAN.value  # "task-plan"

#: Logical artifact path used as the Gist filename key for task-plan content.
#: The path is synthetic (not a real filesystem path) — the Gist filename is
#: derived from it via ``/`` → ``--`` substitution.
_TASK_PLAN_PATH_TEMPLATE = "sam-plan/task-plan-issue-{issue}.yaml"

#: Artifact type string for plan-index content.
_PLAN_INDEX_TYPE = "plan-index"

#: Logical path key for the plan-index blob on the sentinel issue.
_PLAN_INDEX_PATH = "sam-plan/plan-index.yaml"

_artifact_registry = ArtifactRegistry()


def _get_provider() -> ArtifactBackend:
    """Create and return the configured artifact provider.

    Uses ``DEFAULT_REPO`` and ``_REPO_ROOT`` from ``backlog_core.models`` to
    construct the provider, matching the pattern in ``server.py``.

    Returns:
        Configured :class:`~backlog_core.artifact_provider.ArtifactBackend`.

    Raises:
        ArtifactWriteError: When ``DEFAULT_REPO`` is not set (configuration error).
        BacklogError: On backend initialisation failures.
    """
    repo = _backlog_models.DEFAULT_REPO
    if not repo:
        msg = "DEFAULT_REPO not set — cannot initialise artifact provider"
        raise BacklogError(msg)
    return create_artifact_provider(
        repo=repo,
        root_worktree=_backlog_models._REPO_ROOT,  # noqa: SLF001
    )


class ArtifactRegistryClient:
    """Typed SAM client for Gist-backed artifact storage and retrieval.

    Wraps the ``backlog_core`` :class:`~backlog_core.artifact_provider.ArtifactBackend`
    to provide a focused interface for plan YAML and plan-index content.

    This client is instantiated once and reused across operations within a
    server request.  It is synchronous — the MCP layer wraps calls in
    ``asyncio.to_thread()`` when needed.

    Args:
        provider: Optional pre-constructed provider for testing.  When
            ``None``, a provider is created on first use via
            :func:`_get_provider`.

    Example::

        client = ArtifactRegistryClient()
        client.store(issue=2509, content=yaml_string)
        yaml_back = client.read(issue=2509)
    """

    def __init__(self, provider: ArtifactBackend | None = None) -> None:
        """Initialise with an optional pre-constructed provider.

        Args:
            provider: Artifact backend implementation.  When ``None``, the
                configured provider is resolved lazily on first use.
        """
        self._provider = provider

    def _provider_instance(self) -> ArtifactBackend:
        """Return the provider, creating it lazily on first call.

        Returns:
            The configured :class:`~backlog_core.artifact_provider.ArtifactBackend`.

        Raises:
            ArtifactWriteError: When ``DEFAULT_REPO`` is not set.
            BacklogError: On provider initialisation failures.
        """
        if self._provider is None:
            self._provider = _get_provider()
        return self._provider

    def store(self, issue: int, content: str, *, artifact_type: str = _TASK_PLAN_TYPE) -> None:
        """Upload plan YAML to GitHub Gist via the artifact registry.

        Registers a manifest entry and stores the content as a Gist file.
        The manifest entry is required so that :func:`backlog_core.server.artifact_read`
        (which resolves by manifest lookup) can later find the content.

        Args:
            issue: GitHub issue number keying the Gist.
            content: Plan YAML string to store.
            artifact_type: Artifact type string.  Defaults to ``"task-plan"``.

        Raises:
            ArtifactWriteError: When the Gist write fails for any reason.
                No silent fallback to local storage is attempted.
        """
        path = _TASK_PLAN_PATH_TEMPLATE.format(issue=issue)
        provider = self._provider_instance()
        try:
            # Step 1: register the manifest entry so artifact_read can resolve it.
            entry = ArtifactEntry(
                artifact_type=ArtifactType.TASK_PLAN,
                artifact_id=path,
                status=ArtifactStatus.CURRENT,
                agent="gist-task-layer",
            )
            manifest = provider.get_manifest(issue)
            # Skip the manifest PATCH when the entry is already registered.
            # After create_plan the entry exists; every subsequent store() call
            # for the same plan only refreshes the created_at timestamp — not
            # worth a Gist PATCH on every task state change.
            entry_exists = any(
                e.artifact_type == entry.artifact_type
                and e.artifact_id == entry.artifact_id
                and e.status == entry.status
                for e in manifest.artifacts
            )
            if not entry_exists:
                updated_manifest = _artifact_registry.register(manifest, entry)
                provider.set_manifest(issue, updated_manifest)
                _log.info(
                    "ArtifactRegistryClient.store: registered new %s manifest entry for issue #%d", artifact_type, issue
                )
            else:
                _log.debug(
                    "ArtifactRegistryClient.store: manifest entry already registered for issue #%d, skipping PATCH",
                    issue,
                )

            # Step 2: upload the content to the Gist file.
            provider.store_artifact_content(issue, artifact_type=artifact_type, path=path, content=content)
            _log.info(
                "ArtifactRegistryClient.store: uploaded %s content to Gist for issue #%d (path=%s)",
                artifact_type,
                issue,
                path,
            )
        except (BacklogError, OSError, ValueError) as exc:
            _log.error(
                "ArtifactRegistryClient.store: write failed for issue #%d (artifact_type=%s): %s",
                issue,
                artifact_type,
                exc,
            )
            raise ArtifactWriteError(plan_id="<unknown>", issue=issue, reason=str(exc)) from exc

    def read(self, issue: int, artifact_type: str = _TASK_PLAN_TYPE) -> str | None:
        """Retrieve plan YAML from GitHub Gist, falling back to local cache.

        Gist-first retrieval strategy:
        1. Resolve the manifest entry for the given artifact type.
        2. Fetch content from the Gist using the registered ``artifact_id`` path.
        3. On Gist miss (no entry or no content): attempt local filesystem read.
        4. Return ``None`` when neither source has content.

        Args:
            issue: GitHub issue number keying the Gist.
            artifact_type: Artifact type string.  Defaults to ``"task-plan"``.

        Returns:
            Content string when found, or ``None`` when absent from both
            Gist and local filesystem.
        """
        path = _TASK_PLAN_PATH_TEMPLATE.format(issue=issue)
        try:
            provider = self._provider_instance()
        except (BacklogError, ArtifactWriteError) as exc:
            _log.warning("ArtifactRegistryClient.read: provider unavailable for issue #%d: %s", issue, exc)
            return None

        # Step 1: try Gist-first via read_artifact_content_from_remote.
        try:
            remote_content = provider.read_artifact_content_from_remote(issue, artifact_type, path)
            if remote_content is not None:
                _log.debug("ArtifactRegistryClient.read: Gist hit for issue #%d (path=%s)", issue, path)
                return remote_content
        except (BacklogError, OSError) as exc:
            _log.warning(
                "ArtifactRegistryClient.read: Gist read failed for issue #%d (path=%s): %s — falling back to local",
                issue,
                path,
                exc,
            )

        # Step 2: fall back to local filesystem.
        try:
            local_content = provider.read_local_artifact_content(path)
            if local_content is not None:
                _log.warning(
                    "ArtifactRegistryClient.read: Gist content unavailable for issue #%d, serving from local cache (path=%s)",
                    issue,
                    path,
                )
                return local_content
        except (ValueError, OSError) as exc:
            _log.warning(
                "ArtifactRegistryClient.read: local read also failed for issue #%d (path=%s): %s", issue, path, exc
            )

        _log.debug("ArtifactRegistryClient.read: content not found for issue #%d (path=%s)", issue, path)
        return None

    def store_index(self, sentinel_issue: int, content: str) -> None:
        """Upload the plan-index YAML to the sentinel issue's Gist.

        Args:
            sentinel_issue: GitHub issue number of the sentinel index issue.
            content: Plan-index YAML string to store.

        Raises:
            ArtifactWriteError: When the Gist write fails.
        """
        provider = self._provider_instance()
        try:
            entry = ArtifactEntry(
                artifact_type=ArtifactType.TASK_PLAN,
                artifact_id=_PLAN_INDEX_PATH,
                status=ArtifactStatus.CURRENT,
                agent="plan-id-index",
            )
            manifest = provider.get_manifest(sentinel_issue)
            entry_exists = any(
                e.artifact_type == entry.artifact_type
                and e.artifact_id == entry.artifact_id
                and e.status == entry.status
                for e in manifest.artifacts
            )
            if not entry_exists:
                updated_manifest = _artifact_registry.register(manifest, entry)
                provider.set_manifest(sentinel_issue, updated_manifest)
            else:
                _log.debug(
                    "ArtifactRegistryClient.store_index: manifest entry already registered for sentinel #%d, skipping PATCH",
                    sentinel_issue,
                )
            provider.store_artifact_content(
                sentinel_issue, artifact_type=_PLAN_INDEX_TYPE, path=_PLAN_INDEX_PATH, content=content
            )
            _log.info("ArtifactRegistryClient.store_index: uploaded plan-index to sentinel issue #%d", sentinel_issue)
        except (BacklogError, OSError, ValueError) as exc:
            _log.error(
                "ArtifactRegistryClient.store_index: write failed for sentinel issue #%d: %s", sentinel_issue, exc
            )
            raise ArtifactWriteError(plan_id="<plan-index>", issue=sentinel_issue, reason=str(exc)) from exc

    def read_index(self, sentinel_issue: int) -> str | None:
        """Retrieve the plan-index YAML from the sentinel issue's Gist.

        Args:
            sentinel_issue: GitHub issue number of the sentinel index issue.

        Returns:
            Plan-index YAML string when found, or ``None`` when absent.
        """
        try:
            provider = self._provider_instance()
        except (BacklogError, ArtifactWriteError) as exc:
            _log.warning(
                "ArtifactRegistryClient.read_index: provider unavailable for sentinel #%d: %s", sentinel_issue, exc
            )
            return None

        try:
            remote_content = provider.read_artifact_content_from_remote(
                sentinel_issue, _PLAN_INDEX_TYPE, _PLAN_INDEX_PATH
            )
            if remote_content is not None:
                return remote_content
        except (BacklogError, OSError) as exc:
            _log.warning(
                "ArtifactRegistryClient.read_index: Gist read failed for sentinel #%d: %s", sentinel_issue, exc
            )

        # Local fallback for plan-index.
        try:
            provider_local = self._provider_instance()
            local_content = provider_local.read_local_artifact_content(_PLAN_INDEX_PATH)
            if local_content is not None:
                _log.warning(
                    "ArtifactRegistryClient.read_index: serving plan-index from local cache for sentinel #%d",
                    sentinel_issue,
                )
                return local_content
        except (ValueError, OSError):
            pass

        return None
