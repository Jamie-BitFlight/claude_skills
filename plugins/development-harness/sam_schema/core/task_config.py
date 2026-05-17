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

import importlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sam_schema.core.task_backend import TaskBackend

__all__ = ["TaskConfig", "create_task_backend", "get_task_config", "reset_task_config", "set_task_config"]

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
    global _active_config  # noqa: PLW0603
    _active_config = config


def reset_task_config() -> None:
    """Clear the cached TaskConfig singleton.

    Intended for test teardown — call this between tests to force the next
    ``get_task_config()`` call to raise rather than returning a stale config.
    """
    global _active_config  # noqa: PLW0603
    _active_config = None


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------


def _load_backend_toml_name() -> str | None:
    """Read backend name from .dh/config.yaml if present.

    Delegates to DHConfig for YAML-based backend resolution. Returns None
    when the resolved value matches the subsystem default ("local"), so
    the caller's resolution chain can continue to the next step.

    Returns:
        Backend name string when explicitly configured, otherwise ``None``.
    """
    from dh_config import DHConfig  # noqa: PLC0415

    result = DHConfig().get_backend(subsystem="task")
    return result if result != "local" else None


def create_task_backend(name: str | None = None) -> TaskBackend:
    """Instantiate and return a TaskBackend by name.

    Resolution order when *name* is ``None``:

    1. ``TASKBACKEND`` environment variable.
    2. ``task.backend`` in ``.dh/config.yaml`` (project or user home dir, via DHConfig).
    3. Default: ``"local"``.

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
    resolved = name or os.environ.get("TASKBACKEND") or _load_backend_toml_name() or "local"

    if resolved == "local":
        # importlib.import_module defers resolution to runtime: avoids circular imports
        # and handles the case where the backends package is created in T03.
        mod = importlib.import_module("sam_schema.core.backends.local_yaml")
        return mod.LocalYamlTaskProvider()  # type: ignore[return-value]

    if resolved == "memory":
        # importlib.import_module defers resolution to runtime: avoids circular imports
        # and handles the case where the backends package is created in T03.
        mod = importlib.import_module("sam_schema.core.backends.memory")
        return mod.InMemoryTaskProvider()  # type: ignore[return-value]

    if resolved == "beads":
        # importlib.import_module defers resolution to runtime: avoids circular imports
        # and handles the case where the beads backend module is created in T08.
        mod = importlib.import_module("sam_schema.core.backends.beads")
        return mod.BeadsTaskProvider()  # type: ignore[return-value]

    if resolved == "github":
        msg = "GitHub backend requires IssueBackend + DocumentBackend (see #984). Use 'local' or 'memory' instead."
        raise NotImplementedError(msg)

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)
