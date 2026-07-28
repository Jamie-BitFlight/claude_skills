"""TaskConfig — dependency injection container for the active TaskBackend.

Provides the module-level singleton pattern (get_task_config / set_task_config /
reset_task_config) and the factory function create_task_backend, following the
pattern established in backlog_core.backend_protocol.

Resolution order for backend selection:
    1. ``TASKBACKEND`` environment variable
    2. ``[backend] name`` in ``.dh/config.yaml`` (via DHConfig)
    3. Default: ``"local"``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dh_config import DHConfig

from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
from sam_schema.core.backends.beads import BeadsTaskProvider
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.backends.memory import InMemoryTaskProvider
from sam_schema.core.gist_task_layer import GistTaskLayer
from sam_schema.core.plan_id_index import create_plan_id_index

if TYPE_CHECKING:
    from sam_schema.core.task_backend import TaskBackend

__all__ = [
    "TaskConfig",
    "create_task_backend",
    "get_backend",
    "get_task_config",
    "reset_task_config",
    "set_task_config",
]

_PLAN_DIR_SENTINEL = "plan"

_VALID_BACKENDS: tuple[str, ...] = ("beads", "local", "github", "memory")


# ---------------------------------------------------------------------------
# TaskConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class TaskConfig:
    """Container for the active TaskBackend instance.

    This dataclass replaces direct imports from query.py in the MCP server.
    Pass a TaskConfig to server tools so they can work against any conforming
    backend implementation.

    Attributes:
        backend: The active TaskBackend implementation.
    """

    backend: TaskBackend


# ---------------------------------------------------------------------------
# Module-level config accessor
# ---------------------------------------------------------------------------

_active_config: TaskConfig | None = None


def get_task_config() -> TaskConfig:
    """Return the active TaskConfig.

    Unlike backlog_core which auto-initialises, this function requires
    an explicit :func:`set_task_config` call first. This prevents the server
    module from silently falling back to a default backend when misconfigured.

    Returns:
        The active TaskConfig instance.

    Raises:
        RuntimeError: When no config has been set via :func:`set_task_config`.
    """
    if _active_config is None:
        msg = "TaskConfig not set. Call set_task_config() first."
        raise RuntimeError(msg)
    return _active_config


def set_task_config(config: TaskConfig) -> None:
    """Register the active TaskConfig.

    Args:
        config: TaskConfig instance wrapping the chosen backend implementation.
    """
    global _active_config  # ruff: ignore[global-statement]
    _active_config = config


def reset_task_config() -> None:
    """Clear the cached TaskConfig singleton.

    Intended for test teardown — call this between tests to force the next
    ``get_task_config()`` call to raise rather than returning a stale config.
    """
    global _active_config  # ruff: ignore[global-statement]
    _active_config = None


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------


def create_task_backend(name: str | None = None) -> TaskBackend:
    """Instantiate and return a TaskBackend by name.

    When *name* is ``None``, resolution is delegated in full to
    :meth:`dh_config.DHConfig.get_backend`, which implements the complete
    chain: ``TASKBACKEND`` env var → ``task.backend`` (then global
    ``backend.name``) in ``.dh/config.yaml`` → ``.beads/dh-backend`` marker
    auto-detect → default ``"local"``.

    Args:
        name: Backend identifier to instantiate. Pass ``None`` to trigger
            automatic resolution.

    Returns:
        Configured TaskBackend instance.

    Raises:
        ValueError: When *name* (or the resolved name) is not a recognised
            backend identifier. The message lists all valid options.
        NotImplementedError: When the resolved name is ``"github"`` (pending
            IssueBackend + DocumentBackend implementation in #984).
    """
    resolved = name or DHConfig().get_backend(subsystem="task")

    if resolved == "local":
        return LocalYamlTaskProvider()

    if resolved == "memory":
        return InMemoryTaskProvider()

    if resolved == "beads":
        return BeadsTaskProvider()

    if resolved == "github":
        msg = "GitHub backend requires IssueBackend + DocumentBackend (see #984). Use 'local' or 'memory' instead."
        raise NotImplementedError(msg)

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Shared backend resolution (used by both CLI and MCP server)
# ---------------------------------------------------------------------------


def get_backend(plan_dir: str | None = None, *, wrap_gist: bool = False) -> TaskBackend:
    """Return the appropriate TaskBackend for the given plan_dir.

    When *plan_dir* is ``None`` or ``"plan"``, returns the module-level
    configured backend from :func:`get_task_config`, wrapped in
    :class:`~sam_schema.core.gist_task_layer.GistTaskLayer` when the
    underlying backend is a ``LocalYamlTaskProvider`` (matching MCP server
    behaviour — write-through to GitHub Gist).

    When *plan_dir* is a concrete filesystem path, creates a
    :class:`~sam_schema.core.backends.local_yaml.LocalYamlTaskProvider`
    for that path.  When *wrap_gist* is ``True`` (MCP server), wraps it in
    ``GistTaskLayer`` to preserve write-through behaviour for explicit
    plan directories.  When ``False`` (CLI default), returns it directly
    (local-only — an explicit path means no Gist sync).

    Args:
        plan_dir: The ``plan_dir`` parameter from the caller.  ``None`` or
            ``"plan"`` selects the configured backend; any other value is
            treated as a filesystem path.
        wrap_gist: When ``True``, wrap explicit-path backends in
            ``GistTaskLayer`` (MCP server behaviour).  When ``False``
            (default, CLI behaviour), return bare
            ``LocalYamlTaskProvider`` for explicit paths.

    Returns:
        A :class:`~sam_schema.core.task_backend.TaskBackend` instance.
    """
    if plan_dir is None or plan_dir == _PLAN_DIR_SENTINEL:
        return _get_configured_backend()

    local = LocalYamlTaskProvider(Path(plan_dir))

    if not wrap_gist:
        return local

    # MCP server path: wrap explicit-path backends in GistTaskLayer to
    # preserve write-through to GitHub Gist (matching pre-refactor behaviour).
    artifact_client = ArtifactRegistryClient()
    plan_index = create_plan_id_index(artifact_client)
    return GistTaskLayer(local_backend=local, artifact_client=artifact_client, plan_index=plan_index)


def _get_configured_backend() -> TaskBackend:
    """Return the configured backend, wrapped in GistTaskLayer when applicable."""
    configured = get_task_config().backend
    if not isinstance(configured, LocalYamlTaskProvider):
        return configured

    artifact_client = ArtifactRegistryClient()
    plan_index = create_plan_id_index(artifact_client)
    return GistTaskLayer(local_backend=configured, artifact_client=artifact_client, plan_index=plan_index)
