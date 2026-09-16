"""The content backend every MCP action falls back to when the ledger does not hold its plan.

Bootstraps the session-scoped active-task context backend at import time and resolves the
content-store task provider ``sam_plan``, ``sam_task``, and ``sam_active_task`` share -- the one
piece of server-construction plumbing more than one of those tools' operation modules needs, so it
lives here rather than in any one of them.
"""

from __future__ import annotations

from backlog_core.backend_protocol import get_config as get_backlog_config
from backlog_core.backend_types import ContentProvider
from fastmcp.exceptions import ToolError

from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.context_config import ContextConfig, create_context_backend, get_context_config, set_context_config

__all__ = ["get_backend"]

# Initialize the context backend at module import time.
# Tests may call set_context_config() before importing this module to inject a custom backend.
try:
    get_context_config()
except RuntimeError:
    set_context_config(ContextConfig(backend=create_context_backend()))


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
