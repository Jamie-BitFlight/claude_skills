"""Backend Protocol — implementation-agnostic abstraction for backlog storage.

This module owns backend selection and re-exports the contracts from
``backend_types``. Operations and server modules depend on this interface;
GitHub-specific implementations live in gh_client, github_sync, and
github_branches.

All protocol methods are synchronous.  The MCP layer wraps calls in
``asyncio.to_thread()`` when needed — see ArtifactBackend in
artifact_provider.py for the established pattern.

Dependency direction (must remain acyclic):
    models <- backend_protocol
    backend_protocol is imported by: operations.py, server.py
    backend_protocol does NOT import from: gh_client, github_sync, github_branches
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from dh_config import DHConfig

from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend

from .backend_types import (
    AssigneeNode,
    BacklogConfig,
    BranchBackend,
    GitHubExtras,
    IssueCommentNode,
    IssueNode,
    LabelNode,
    MilestoneFullNode,
    MilestoneNode,
    WorkItemBackend,
)

if TYPE_CHECKING:
    import types

_dh_paths: types.ModuleType | None = None
with contextlib.suppress(ImportError):
    import dh_paths as _dh_paths  # optional — only present inside the plugin

__all__ = [
    "BEADS_DIR",
    "BEADS_OPT_IN_MARKER",
    "AssigneeNode",
    "BacklogConfig",
    "BranchBackend",
    "GitHubExtras",
    "IssueCommentNode",
    "IssueNode",
    "LabelNode",
    "MilestoneFullNode",
    "MilestoneNode",
    "WorkItemBackend",
    "create_backend",
    "get_config",
    "reset_config",
    "set_config",
]

#: Name of the ``.beads`` workspace directory at the project root.
BEADS_DIR: str = ".beads"

#: Marker file that must exist inside :data:`BEADS_DIR` to opt the project into
#: the beads backlog backend.  The directory alone is insufficient; the marker
#: file is an explicit opt-in that prevents silent mis-routing of projects that
#: happen to have a ``.beads/`` directory for unrelated reasons.
#:
#: Full path relative to project root: ``{BEADS_DIR}/{BEADS_OPT_IN_MARKER}``
BEADS_OPT_IN_MARKER: str = "dh-backend"


# ---------------------------------------------------------------------------
# Module-level config accessor
# ---------------------------------------------------------------------------

_active_config: BacklogConfig | None = None


def get_config() -> BacklogConfig:
    """Return the active BacklogConfig, auto-initialising on first call.

    Resolution order for the backend (when no config has been registered via
    :func:`set_config`):

    1. ``BACKLOG_BACKEND`` environment variable.
    2. ``backlog.backend`` key in ``.dh/config.yaml`` (project config directory).
    3. Auto-detect: ``"beads"`` when ``.beads/dh-backend`` marker file exists at
       the project root (directory alone is not sufficient — explicit opt-in required).
    4. Default: ``"github"``.

    The result is cached as a module-level singleton.  Call :func:`reset_config`
    to clear the cache (useful in tests).

    Returns:
        The active BacklogConfig instance.

    Raises:
        ValueError: When the resolved backend name is not recognised.
    """
    global _active_config  # ruff: ignore[global-statement]
    if _active_config is None:
        _active_config = BacklogConfig(backend=create_backend())
    return _active_config


def set_config(config: BacklogConfig) -> None:
    """Register the active BacklogConfig.

    Args:
        config: BacklogConfig instance wrapping the chosen backend implementation.
    """
    global _active_config  # ruff: ignore[global-statement]
    _active_config = config


def reset_config() -> None:
    """Clear the cached BacklogConfig singleton.

    Intended for test teardown — call this between tests to force the next
    ``get_config()`` call to re-run backend selection.
    """
    global _active_config  # ruff: ignore[global-statement]
    _active_config = None


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

_VALID_BACKENDS: tuple[str, ...] = ("github", "memory", "sqlite", "beads")


def _auto_detect_beads() -> str | None:
    """Return ``"beads"`` when the explicit opt-in marker ``.beads/dh-backend`` exists.

    Requires an explicit opt-in marker file at ``<project_root>/.beads/dh-backend``.
    The ``.beads/`` directory alone is not sufficient — a project may have a
    ``.beads/`` directory for other purposes without intending to use the beads
    backlog backend.

    Uses dh_paths to resolve the project root.  Falls through silently
    (returns ``None``) when dh_paths is absent, the project root cannot
    be determined, or the marker file does not exist.

    Returns:
        ``"beads"`` when the opt-in marker file is present, otherwise ``None``.
    """
    if _dh_paths is None:
        return None
    try:
        project_root = _dh_paths.git_project_root()
    except (FileNotFoundError, RuntimeError):
        return None
    return "beads" if (project_root / BEADS_DIR / BEADS_OPT_IN_MARKER).is_file() else None


def create_backend(name: str | None = None) -> WorkItemBackend:
    """Instantiate and return a backend by name.

    When *name* is ``None``, resolution is delegated in full to
    :meth:`dh_config.DHConfig.get_backend`, which implements the complete
    chain: ``BACKLOG_BACKEND`` env var → ``backlog.backend`` (then global
    ``backend.name``) in ``.dh/config.yaml`` → ``.beads/dh-backend`` marker
    auto-detect → default ``"github"``.

    Args:
        name: Backend identifier to instantiate.  Pass ``None`` to trigger
            automatic resolution.

    Returns:
        Configured ``WorkItemBackend`` instance.

    Raises:
        ValueError: When *name* (or the resolved name) is not a recognised
            backend identifier.  The message lists all valid options.
    """
    resolved = name or DHConfig().get_backend(subsystem="backlog")

    if resolved == "github":
        return GitHubBackend()

    if resolved == "memory":
        return InMemoryBackend()

    if resolved == "sqlite":
        return SQLiteBackend()

    if resolved == "beads":
        return BeadsBackend()

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)
