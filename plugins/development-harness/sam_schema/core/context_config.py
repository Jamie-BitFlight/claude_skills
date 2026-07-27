"""ContextConfig — dependency injection container for the active ContextBackend.

Provides the module-level singleton pattern (get_context_config / set_context_config /
reset_context_config) and the factory function create_context_backend, following the
pattern established in task_config.py.

Resolution order for backend selection:
    1. ``CONTEXTBACKEND`` environment variable
    2. ``context.backend`` key in ``.dh/config.yaml`` (via DHConfig)
    3. Default: ``"local"``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dh_config import DHConfig

from sam_schema.core.backends.beads import BeadsContextBackend
from sam_schema.core.backends.local_context_backend import LocalContextBackend
from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend

if TYPE_CHECKING:
    from sam_schema.core.context_backend import ContextBackend

__all__ = [
    "ContextConfig",
    "create_context_backend",
    "get_context_config",
    "reset_context_config",
    "set_context_config",
]

_VALID_BACKENDS: tuple[str, ...] = ("beads", "local", "github", "memory")


# ---------------------------------------------------------------------------
# ContextConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class ContextConfig:
    """Container for the active ContextBackend instance.

    This dataclass replaces direct imports from server.py in the MCP server.
    Pass a ContextConfig to server tools so they can work against any conforming
    backend implementation.

    Attributes:
        backend: The active ContextBackend implementation.
    """

    backend: ContextBackend


# ---------------------------------------------------------------------------
# Module-level config accessor
# ---------------------------------------------------------------------------

_active_config: ContextConfig | None = None


def get_context_config() -> ContextConfig:
    """Return the active ContextConfig.

    Unlike backlog_core which auto-initialises, this function requires
    an explicit :func:`set_context_config` call first. This prevents the server
    module from silently falling back to a default backend when misconfigured.

    Returns:
        The active ContextConfig instance.

    Raises:
        RuntimeError: When no config has been set via :func:`set_context_config`.
    """
    if _active_config is None:
        msg = "ContextConfig not set. Call set_context_config() first."
        raise RuntimeError(msg)
    return _active_config


def set_context_config(config: ContextConfig) -> None:
    """Register the active ContextConfig.

    Args:
        config: ContextConfig instance wrapping the chosen backend implementation.
    """
    global _active_config  # noqa: PLW0603
    _active_config = config


def reset_context_config() -> None:
    """Clear the cached ContextConfig singleton.

    Intended for test teardown — call this between tests to force the next
    ``get_context_config()`` call to raise rather than returning a stale config.
    """
    global _active_config  # noqa: PLW0603
    _active_config = None


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------


def create_context_backend(name: str | None = None) -> ContextBackend:
    """Instantiate and return a ContextBackend by name.

    When *name* is ``None``, resolution is delegated in full to
    :meth:`dh_config.DHConfig.get_backend`, which implements the complete
    chain: ``CONTEXTBACKEND`` env var → ``context.backend`` (then global
    ``backend.name``) in ``.dh/config.yaml`` → ``.beads/dh-backend`` marker
    auto-detect → default ``"local"``.

    Args:
        name: Backend identifier to instantiate. Pass ``None`` to trigger
            automatic resolution.

    Returns:
        Configured ContextBackend instance.

    Raises:
        ValueError: When *name* (or the resolved name) is not a recognised
            backend identifier. The message lists all valid options.
        NotImplementedError: When the resolved name is ``"github"`` (pending T02
            GitHubContextBackend implementation).
    """
    resolved = name or DHConfig().get_backend(subsystem="context")

    if resolved == "local":
        return LocalContextBackend()

    if resolved == "memory":
        return InMemoryContextBackend()

    if resolved == "beads":
        return BeadsContextBackend()

    if resolved == "github":
        msg = "GitHub context backend is implemented in T02. Use 'local' or 'memory' instead."
        raise NotImplementedError(msg)

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)
