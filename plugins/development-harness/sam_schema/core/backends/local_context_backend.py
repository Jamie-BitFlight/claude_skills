"""LocalContextBackend — filesystem-based ContextBackend implementation.

Reads and writes active-task-{session_id}.json files under dh_paths.context_dir().
JSON is the canonical format consumed by the SubagentStop hook.

Writes are atomic: temp file + os.replace() — matching the yaml_writer pattern.
Files are keyed per session_id — no cross-session contention.

Dependency direction (acyclic):
    local_context_backend imports from: models, dh_paths
    local_context_backend does NOT import from: server, context_config
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import dh_paths

from sam_schema.core.models import ActiveTaskContext

__all__ = ["LocalContextBackend"]


class LocalContextBackend:
    """Filesystem-backed ContextBackend.

    Writes active-task-{session_id}.json files to dh_paths.context_dir().
    Each session has its own file — no cross-session contention.
    Writes are atomic via temp file + rename.
    """

    def get_active_task(self, session_id: str) -> ActiveTaskContext | None:
        """Read and return the active task context from the filesystem.

        Args:
            session_id: Session identifier used as filename key.

        Returns:
            Parsed ActiveTaskContext, or None if the file does not exist.
        """
        path = self._context_path(session_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ActiveTaskContext.model_validate(data)

    def set_active_task(
        self, session_id: str, plan: str, task: str, plan_dir: str, parent_issue_number: str | int | None = None
    ) -> ActiveTaskContext:
        """Write active task context to the filesystem as JSON.

        Args:
            session_id: Session identifier used as filename key.
            plan: Plan address (e.g., 'P1' or slug).
            task: Task ID within the plan (e.g., 'T3').
            plan_dir: Plan directory sentinel 'plan' or an absolute path.
            parent_issue_number: Optional GitHub issue number or beads nanoid for the parent story.

        Returns:
            The stored ActiveTaskContext instance.
        """
        ctx_dir = dh_paths.context_dir()
        ctx_dir.mkdir(parents=True, exist_ok=True)

        context = ActiveTaskContext(
            task_file_path=self._resolve_task_file_path(plan, plan_dir),
            task_id=task,
            plan=plan,
            task=task,
            plan_dir=plan_dir,
            parent_issue_number=parent_issue_number,
            session_id=session_id,
            started_at=datetime.now(tz=UTC).isoformat(),
        )

        path = ctx_dir / f"active-task-{session_id}.json"
        _atomic_write(path, context.model_dump(exclude_none=False))
        return context

    def clear_active_task(self, session_id: str) -> bool:
        """Delete the active task context file for a session.

        Args:
            session_id: Session identifier used as filename key.

        Returns:
            True if the file existed and was deleted, False otherwise.
        """
        path = self._context_path(session_id)
        if path.is_file():
            path.unlink()
            return True
        return False

    def list_active_tasks(self) -> list[ActiveTaskContext]:
        """Return all active task contexts from the filesystem.

        Silently skips missing or unreadable files.

        Returns:
            List of parsed ActiveTaskContext instances sorted by filename.
        """
        ctx_dir = dh_paths.context_dir()
        if not ctx_dir.is_dir():
            return []

        results: list[ActiveTaskContext] = []
        for path in sorted(ctx_dir.glob("active-task-*.json")):
            with contextlib.suppress(json.JSONDecodeError, OSError, ValueError):
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append(ActiveTaskContext.model_validate(data))
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _context_path(self, session_id: str) -> Path:
        return dh_paths.context_dir() / f"active-task-{session_id}.json"

    @staticmethod
    def _resolve_task_file_path(plan: str, plan_dir: str) -> str:
        """Resolve the absolute path to the plan YAML file.

        Args:
            plan: Plan address (e.g., 'P1' or slug).
            plan_dir: Plan directory sentinel 'plan' or an absolute path.

        Returns:
            Absolute path string to the plan YAML file.
        """
        base = dh_paths.plan_dir() if plan_dir == "plan" else Path(plan_dir)
        return str(base / f"{plan}.yaml")


def _atomic_write(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    """Write JSON atomically using temp file + os.replace().

    Args:
        path: Target file path.
        data: JSON-serializable dict.
    """
    content = json.dumps(data, indent=2, default=str)
    dir_ = path.parent
    fd, tmp_path_str = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        Path(tmp_path_str).replace(path)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp_path_str).unlink()
        raise
