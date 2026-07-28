"""InMemoryContextBackend — in-memory ContextBackend implementation.

Dict-based test double for the ContextBackend Protocol. No persistence —
all state is lost when the instance is garbage collected.

Dependency direction (acyclic):
    memory_context_backend imports from: models
    memory_context_backend does NOT import from: server, context_config, dh_paths
"""

from __future__ import annotations

from datetime import UTC, datetime

from sam_schema.core.models import ActiveTaskContext

__all__ = ["InMemoryContextBackend"]


class InMemoryContextBackend:
    """In-memory ContextBackend for testing.

    Stores ActiveTaskContext objects in a dict keyed by session_id.
    No persistence — all state is lost when the instance is garbage collected.
    Thread-safe within a single asyncio event loop (all methods synchronous).
    """

    def __init__(self) -> None:
        """Initialise an empty in-memory context store."""
        self._store: dict[str, ActiveTaskContext] = {}

    def get_active_task(self, session_id: str) -> ActiveTaskContext | None:
        """Return the stored context for a session, or None if absent.

        Args:
            session_id: Session identifier.

        Returns:
            ActiveTaskContext if stored, otherwise None.
        """
        return self._store.get(session_id)

    def set_active_task(
        self, session_id: str, plan: str, task: str, plan_dir: str, parent_issue_number: str | int | None = None
    ) -> ActiveTaskContext:
        """Store the active task context for a session.

        Args:
            session_id: Session identifier.
            plan: Plan address (e.g., 'P1' or slug).
            task: Task ID within the plan (e.g., 'T3').
            plan_dir: Plan directory sentinel or absolute path.
            parent_issue_number: Optional GitHub issue number or beads nanoid.

        Returns:
            The stored ActiveTaskContext instance.
        """
        context = ActiveTaskContext(
            task_file_path=f"{plan_dir}/{plan}.yaml",
            task_id=task,
            plan=plan,
            task=task,
            plan_dir=plan_dir,
            parent_issue_number=parent_issue_number,
            session_id=session_id,
            started_at=datetime.now(tz=UTC).isoformat(),
        )
        self._store[session_id] = context
        return context

    def clear_active_task(self, session_id: str) -> bool:
        """Remove the stored context for a session.

        Args:
            session_id: Session identifier.

        Returns:
            True if the context existed and was removed, False otherwise.
        """
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    def list_active_tasks(self) -> list[ActiveTaskContext]:
        """Return all stored active task contexts.

        Returns:
            List of all stored ActiveTaskContext instances.
        """
        return list(self._store.values())
