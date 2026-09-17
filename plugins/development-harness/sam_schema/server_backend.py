"""The content backend every MCP action falls back to when the ledger does not hold its plan.

Resolves the session-scoped active-task context backend and the content-store task provider
``sam_plan``, ``sam_task``, and ``sam_active_task`` share -- the one piece of server-construction
plumbing more than one of those tools' operation modules needs, so it lives here rather than in
any one of them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.backend_protocol import get_config as get_backlog_config
from backlog_core.backend_types import ContentProvider
from fastmcp.exceptions import ToolError

from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.context_config import ContextConfig, create_context_backend, get_context_config, set_context_config
from sam_schema.core.exceptions import SamError

if TYPE_CHECKING:
    from sam_schema.core.context_backend import ContextBackend

__all__ = ["get_backend", "get_context_backend"]


def get_context_backend() -> ContextBackend:
    """Resolve the active-task context backend, initialising it on first use.

    Building this at import time made a misconfigured backend name an import error:
    the whole MCP server failed to start, which is worse than a failed call on the one
    tool that needs this backend. Mirrors ``cli_active_task._context_backend``'s lazy
    init so both transports resolve through the same chain -- including which refusals
    they convert: the factory raises ``NotImplementedError`` for the existing but
    factory-disabled ``"github"`` backend as well as ``SamError`` for an unrecognised
    name. Catching only one of the two let ``CONTEXTBACKEND=github`` escape
    ``sam_active_task`` as a raw ``NotImplementedError``. Tests may still call
    ``set_context_config()`` first to inject their own backend.

    Returns:
        The active ContextBackend implementation.

    Raises:
        ToolError: When the configured backend name is not a recognised backend, or is
            the existing GitHub backend, which remains factory-disabled pending #3455.
            ``dh_config.DHConfig.get_backend`` resolves that name, so the input to correct
            is whichever of these is in force: the ``CONTEXTBACKEND`` environment variable,
            ``context.backend`` or the global ``backend.name`` in ``.dh/config.yaml``, or
            the ``.beads/dh-backend`` marker file, which selects ``"beads"``.
    """
    try:
        return get_context_config().backend
    except RuntimeError:
        try:
            backend = create_context_backend()
        except (SamError, NotImplementedError) as exc:
            raise ToolError(str(exc)) from exc
        set_context_config(ContextConfig(backend=backend))
        return backend


def get_backend(plan_dir_str: str) -> ContentTaskProvider:
    """Resolve the active backend as a content-store task provider.

    Args:
        plan_dir_str: Unused; kept so callers can pass a plan directory uniformly with the CLI's
            own backend resolution, which some backends still take a path for.

    Returns:
        The content-store task provider wrapping the active backend.

    Raises:
        ToolError: When the active backend does not support plan content.
    """
    del plan_dir_str
    provider = get_backlog_config().backend
    if not isinstance(provider, ContentProvider):
        raise ToolError("Active backend does not support plan content")
    return ContentTaskProvider(provider)
