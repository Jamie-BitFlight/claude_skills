"""Gist-backed task layer wrapping LocalYamlTaskProvider.

This module provides :class:`GistTaskLayer`, a :class:`~sam_schema.core.task_backend.TaskBackend`
implementation that wraps :class:`~sam_schema.core.backends.local_yaml.LocalYamlTaskProvider`
and adds mandatory write-through to GitHub Gist on plan creation.

Architecture (ADR-2509-1):
    ``GistTaskLayer`` is used *only* in the MCP server context.  CLI callers and
    non-MCP code continue to use ``LocalYamlTaskProvider`` directly.  The local YAML
    store becomes a write-through cache; Gist is the durable, environment-independent
    source of truth for plans with an associated GitHub issue.

Write-path contract (ADR-2509-5):
    ``create_plan`` with ``issue`` set MUST upload plan YAML to Gist via
    ``ArtifactRegistryClient.store()``.  On failure, :exc:`ArtifactWriteError` is raised
    and propagates to the MCP handler — **no silent fallback**.

    ``create_plan`` with ``issue=None`` writes to local disk only and returns a warning
    in the MCP response (ADR-2509-4).  No Gist upload is attempted.

T2 scope:
    This file implements ``create_plan`` write-through and plain delegation for all
    other Protocol methods.  T3 wires Gist-first reads; T4 wires write-through
    mutations; T4 also resolves ``claim_task`` atomicity (ADR-2509-3).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .exceptions import ArtifactWriteError, PlanIndexError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.models import Task
    from sam_schema.core.plan_id_index import PlanIdIndex
    from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

_log = logging.getLogger(__name__)

#: Warnings key returned in the MCP create response for local-only plans (ADR-2509-4).
_LOCAL_ONLY_WARNING = (
    "Plan {plan_id} has no associated issue — stored locally only. "
    "This plan is not portable across environments and cannot be retrieved from CI "
    "or fresh checkouts. Associate a GitHub issue with this plan to enable portability."
)


class GistTaskLayer:
    """TaskBackend wrapper adding write-through Gist storage to LocalYamlTaskProvider.

    Implements the full :class:`~sam_schema.core.task_backend.TaskBackend` Protocol
    by delegating every method to *local_backend*, with the following additions for
    ``create_plan``:

    - When ``issue`` is provided: uploads plan YAML to Gist and registers the
      ``plan_id → issue`` mapping in the ``PlanIdIndex``.  Failure raises
      :exc:`ArtifactWriteError` (no silent fallback — ADR-2509-5).
    - When ``issue`` is ``None``: local-only creation; no Gist upload.  The
      MCP handler checks ``config.issue is None`` and adds the non-portability
      warning directly to the response.

    Informational warnings (e.g., plan index registration failure after a
    successful content upload) are stored in :attr:`last_warnings` so the MCP
    handler can surface them without modifying the ``PlanData`` TypedDict.

    All other methods delegate unchanged to *local_backend*.  T3 will replace
    ``read_plan`` / ``list_plans`` with Gist-first logic; T4 will replace the
    mutation methods with read-modify-write-through logic.

    Args:
        local_backend: The :class:`LocalYamlTaskProvider` used for filesystem
            operations and as a read/write cache.
        artifact_client: Thin Gist wrapper for plan YAML store/read operations.
        plan_index: Reverse-map index resolving ``plan_id → issue``.

    Example::

        backend = GistTaskLayer(
            local_backend=LocalYamlTaskProvider(plan_dir),
            artifact_client=ArtifactRegistryClient(),
            plan_index=create_plan_id_index(artifact_client),
        )
        plan_data = backend.create_plan(slug="my-plan", goal="...", tasks=[], issue=42)
        warnings = backend.last_warnings  # informational messages, if any
    """

    def __init__(
        self, local_backend: LocalYamlTaskProvider, artifact_client: ArtifactRegistryClient, plan_index: PlanIdIndex
    ) -> None:
        """Initialise with the three collaborating components.

        Args:
            local_backend: Filesystem-backed task provider (read/write cache).
            artifact_client: Gist-backed artifact store/read client.
            plan_index: Gist-backed ``plan_id → issue`` reverse-map index.
        """
        self._local = local_backend
        self._artifact_client = artifact_client
        self._plan_index = plan_index
        #: Informational warnings from the most recent operation.  Reset at the
        #: start of each ``create_plan`` call.  The MCP handler reads this after
        #: a successful call and includes any messages in the response.
        self.last_warnings: list[str] = []

    # ------------------------------------------------------------------
    # Plan lifecycle — create_plan has write-through logic; others delegate
    # ------------------------------------------------------------------

    def create_plan(
        self,
        slug: str,
        goal: str,
        tasks: Sequence[Task],
        *,
        context: str | None = None,
        issue: int | None = None,
        acceptance_criteria: str | None = None,
    ) -> PlanData:
        """Create a plan and upload YAML to Gist when an issue is provided.

        Write-through flow (``issue`` provided — ADR-2509-5):

        1. Delegate to ``local_backend.create_plan()`` to write local YAML.
        2. Read the YAML content from the local file (``source_path``).
        3. Register ``plan_id → issue`` in the ``PlanIdIndex``.
        4. Upload YAML content to Gist via ``artifact_client.store()``.
        5. On step 3 or 4 failure: raise :exc:`ArtifactWriteError` (no fallback).

        Local-only flow (``issue=None`` — ADR-2509-4):

        1. Delegate to ``local_backend.create_plan()`` to write local YAML.
        2. Return :class:`PlanData` with ``_warnings`` key containing the
           non-portability message.  No Gist upload.

        Args:
            slug: Human-readable identifier slug for the plan.
            goal: One-sentence goal statement for the plan.
            tasks: Ordered sequence of validated Task models.
            context: Optional plan-level context narrative.
            issue: Optional GitHub issue number.  When provided, enables
                Gist write-through.  When ``None``, plan is local-only.
            acceptance_criteria: Optional plan-level acceptance criteria.

        Returns:
            :class:`PlanData` dict.  When ``issue`` is ``None``, the dict
            includes a ``_warnings`` key with the non-portability message.

        Raises:
            ArtifactWriteError: When Gist upload or index registration fails
                and ``issue`` is not ``None``.  Never raised for local-only plans.
            PlanExistsError: Propagated from ``local_backend.create_plan()``.
            TaskValidationError: Propagated from ``local_backend.create_plan()``.
        """
        # Reset warnings at the start of each create_plan call.
        self.last_warnings = []

        # Step 1: local write (always — establishes the plan_id).
        plan_data = self._local.create_plan(
            slug=slug, goal=goal, tasks=tasks, context=context, issue=issue, acceptance_criteria=acceptance_criteria
        )
        plan_id = plan_data["plan_id"]

        if issue is None:
            # Local-only plan: the MCP handler detects config.issue is None and
            # adds the non-portability warning to the response directly.
            # No Gist upload is attempted (ADR-2509-4).
            _log.info("GistTaskLayer.create_plan: plan %s has no issue — local-only, no Gist upload", plan_id)
            return plan_data

        # issue is set — mandatory write-through to Gist.
        source_path_str = plan_data.get("source_path")
        local_path: Path | None = Path(source_path_str) if source_path_str else None

        # Step 2: read YAML content from the local file written by the backend.
        yaml_content = self._read_local_yaml(plan_id, local_path)

        # Step 3 & 4: register index entry and upload content.
        # Index registration failure (PlanIndexError) is treated differently from
        # content upload failure (ArtifactWriteError): a missing index entry is a
        # discoverability degradation (plan is still in Gist, readable by issue),
        # while a missing content upload means the plan is NOT stored remotely.
        #
        # Per architect spec (Failure Propagation section): PlanIndexError →
        # warning (content is still safe); ArtifactWriteError → hard error.

        # First upload content (most important — content must reach Gist).
        try:
            self._artifact_client.store(issue=issue, content=yaml_content)
            _log.info("GistTaskLayer.create_plan: uploaded plan %s YAML to Gist (issue #%d)", plan_id, issue)
        except ArtifactWriteError:
            _log.error(
                "GistTaskLayer.create_plan: Gist content upload failed for plan %s (issue #%d) — raising",
                plan_id,
                issue,
            )
            raise

        # Then register in plan index (best-effort — discoverability only).
        try:
            self._plan_index.register(plan_id=plan_id, issue=issue, slug=slug)
            _log.info("GistTaskLayer.create_plan: registered plan_id %s → issue #%d in plan index", plan_id, issue)
        except PlanIndexError as idx_exc:
            # Index registration failure: content IS in Gist; plan_id resolution
            # across environments may fail.  Store as a warning, do not hard-fail.
            warning_msg = (
                f"Plan index registration failed for {plan_id}: {idx_exc}. "
                "Plan content is stored in Gist but plan_id may not resolve across environments. "
                "Set sam.plan_index_issue in .dh/config.yaml to enable plan_id reverse lookup."
            )
            _log.warning("GistTaskLayer.create_plan: %s", warning_msg)
            self.last_warnings.append(warning_msg)

        return plan_data

    def _read_local_yaml(self, plan_id: str, local_path: Path | None) -> str:
        """Read the local YAML file written by the backend.

        Args:
            plan_id: Plan identifier for error messages.
            local_path: Path to the local YAML file, or ``None`` if unavailable.

        Returns:
            YAML content string.

        Raises:
            ArtifactWriteError: When the local file cannot be read.
        """
        if local_path is None or not local_path.is_file():
            msg = f"local YAML file not found for plan {plan_id} (source_path={local_path!r})"
            _log.error("GistTaskLayer._read_local_yaml: %s", msg)
            raise ArtifactWriteError(plan_id=plan_id, issue=None, reason=msg)
        try:
            return local_path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"failed to read local YAML for plan {plan_id}: {exc}"
            _log.error("GistTaskLayer._read_local_yaml: %s", msg)
            raise ArtifactWriteError(plan_id=plan_id, issue=None, reason=msg) from exc

    # ------------------------------------------------------------------
    # Delegation — all remaining Protocol methods pass through to local_backend.
    # T3 will replace read_plan and list_plans with Gist-first logic.
    # T4 will replace mutation methods with write-through RMW logic.
    # ------------------------------------------------------------------

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by identifier.  Delegates to local backend (T3 adds Gist-first).

        Returns:
            :class:`~sam_schema.core.task_backend_types.PlanData` for the plan.
        """
        return self._local.read_plan(plan_id)

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """List all plans.  Delegates to local backend (T3 adds index merge).

        Returns:
            List of :class:`~sam_schema.core.task_backend_types.PlanSummary` dicts.
        """
        return self._local.list_plans(search=search, offset=offset, limit=limit)

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level plan fields.  Delegates to local backend (T4 adds write-through)."""
        self._local.update_plan_fields(plan_id, context=context, set_fields=set_fields)

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task.  Delegates to local backend.

        Returns:
            :class:`~sam_schema.core.task_backend_types.TaskData` for the task.
        """
        return self._local.read_task(plan_id, task_id)

    def claim_task(self, plan_id: str, task_id: str) -> bool:
        """Claim a task.  Delegates to local backend (T4 resolves atomicity — ADR-2509-3).

        Returns:
            ``True`` if the task was successfully claimed; ``False`` otherwise.
        """
        return self._local.claim_task(plan_id, task_id)

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update task status.  Delegates to local backend (T4 adds write-through)."""
        self._local.update_task_status(plan_id, task_id, status)

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update task fields.  Delegates to local backend (T4 adds write-through)."""
        self._local.update_task_fields(plan_id, task_id, fields)

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace a stored task.  Delegates to local backend (T4 adds write-through)."""
        self._local.update_task(plan_id, task)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append a markdown section to a task.  Delegates to local backend."""
        self._local.append_task_section(plan_id, task_id, section_name, content)

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a task to an existing plan.  Delegates to local backend (T4 adds write-through).

        Returns:
            Dict with ``appended`` (bool) and ``task_id`` (str) keys.
        """
        return self._local.append_task(plan_id, task)

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Finalize a plan from drafting to ready state.  Delegates to local backend (T4 adds write-through).

        Returns:
            Dict with ``finalized`` (bool) and ``state`` (str) keys.
        """
        return self._local.finalize_plan(plan_id)

    def get_ready_tasks(self, plan_id: str) -> list[TaskData]:
        """Return ready tasks.  Delegates to local backend."""
        return self._local.get_ready_tasks(plan_id)

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return plan status summary.  Delegates to local backend."""
        return self._local.get_plan_status(plan_id)

    def store_document(
        self, plan_id: str, task_id: str | None, stage: str, doc_type: str, title: str, content: str, fmt: str = "md"
    ) -> DocumentHandle:
        """Store a document.  Delegates to local backend (document portability is out of scope).

        Returns:
            :class:`~sam_schema.core.task_backend_types.DocumentHandle` for later retrieval.
        """
        return self._local.store_document(plan_id, task_id, stage, doc_type, title, content, fmt)

    def read_document(self, handle: DocumentHandle) -> DocumentData:
        """Retrieve a document.  Delegates to local backend.

        Returns:
            :class:`~sam_schema.core.task_backend_types.DocumentData` with content and metadata.
        """
        return self._local.read_document(handle)
