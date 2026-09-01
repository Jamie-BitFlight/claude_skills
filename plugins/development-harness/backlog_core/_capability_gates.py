"""Shared capability gates for optional backend protocol subsets.

``GitHubExtras`` and ``BranchBackend`` are both ``runtime_checkable``
Protocols, which means ``isinstance(backend, SomeProtocol)`` checks method
*names* only — a backend can satisfy a Protocol structurally (by
implementing every method, even as a local simulation) without actually
having the underlying capability. ``SQLiteBackend`` and ``InMemoryBackend``
both implement every ``GitHubExtras`` method, but neither can return a real
``Repository``, so ``isinstance`` alone lets them through the gate.

The functions here gate on the backend's explicit capability flag first —
``supports_github_extras`` / ``supports_branches`` — and use ``isinstance``
only as a secondary structural assertion once the flag confirms the
capability is genuinely present. Both raise the same typed
``UnsupportedBackendCapabilityError`` (rather than a bare ``RuntimeError``
or ``TypeError``) so every capability gap in the ``BacklogError`` tree looks
identical to callers.
"""

from __future__ import annotations

from .backend_types import BranchBackend, GitHubExtras, WorkItemBackend
from .models import UnsupportedBackendCapabilityError

__all__ = ["require_branch_support", "require_github_extras"]


def require_github_extras(backend: WorkItemBackend, operation: str) -> GitHubExtras:
    """Return ``backend`` narrowed to ``GitHubExtras``, or raise if unsupported.

    Args:
        backend: The active backend instance to check. Passed in by the
            caller (rather than fetched here) so callers keep patching
            ``get_config()`` directly in tests, and so static type checkers
            narrow the return value at the call site.
        operation: Name of the operation the caller is attempting, recorded
            on the raised error for a specific remediation message.

    Returns:
        The same backend instance, statically narrowed to ``GitHubExtras``.

    Raises:
        UnsupportedBackendCapabilityError: If ``backend.supports_github_extras``
            is falsy, or the backend does not structurally satisfy
            ``GitHubExtras`` despite declaring the flag.
    """
    if not getattr(backend, "supports_github_extras", False):
        raise UnsupportedBackendCapabilityError("github_extras", type(backend).__name__, operation)
    if not isinstance(backend, GitHubExtras):
        raise UnsupportedBackendCapabilityError("github_extras", type(backend).__name__, operation)
    return backend


def require_branch_support(backend: WorkItemBackend, operation: str) -> BranchBackend:
    """Return ``backend`` narrowed to ``BranchBackend``, or raise if unsupported.

    Args:
        backend: The active backend instance to check. Passed in by the
            caller (rather than fetched here) so callers keep patching
            ``get_config()`` directly in tests, and so static type checkers
            narrow the return value at the call site.
        operation: Name of the operation the caller is attempting, recorded
            on the raised error for a specific remediation message.

    Returns:
        The same backend instance, statically narrowed to ``BranchBackend``.

    Raises:
        UnsupportedBackendCapabilityError: If ``backend.supports_branches``
            is falsy, or the backend does not structurally satisfy
            ``BranchBackend`` despite declaring the flag.
    """
    if not getattr(backend, "supports_branches", False):
        raise UnsupportedBackendCapabilityError("branches", type(backend).__name__, operation)
    if not isinstance(backend, BranchBackend):
        raise UnsupportedBackendCapabilityError("branches", type(backend).__name__, operation)
    return backend
