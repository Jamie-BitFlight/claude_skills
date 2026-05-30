"""Gist-backed task layer wrapping LocalYamlTaskProvider.

This module provides :class:`GistTaskLayer`, a :class:`~sam_schema.core.task_backend.TaskBackend`
implementation that wraps :class:`~sam_schema.core.backends.local_yaml.LocalYamlTaskProvider`
and adds mandatory write-through to GitHub Gist on plan creation, plus Gist-first reads.

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

Read-path contract (ADR-2509-5):
    ``read_plan`` resolves ``plan_id → issue`` via ``PlanIdIndex``, fetches YAML from
    Gist, and writes the content to the local filesystem cache (best-effort) so
    subsequent reads by ``get_ready_tasks`` and ``get_plan_status`` succeed without an
    additional Gist round-trip.  When Gist content is absent or the plan has no index
    entry, falls back to ``LocalYamlTaskProvider.read_plan()``.  Both paths annotate
    the source in :attr:`last_read_source`.

    ``list_plans`` merges the ``PlanIdIndex`` (Gist-registered plans) with
    ``LocalYamlTaskProvider.list_plans()`` (local YAML files), deduplicates by
    ``plan_id`` (Gist precedence), then applies search/offset/limit.  For index-only
    plans not present in the local cache, the YAML is fetched from Gist and a summary
    is computed from the blob content.

T2 scope:
    ``create_plan`` write-through.

T3 scope (this commit):
    ``read_plan`` Gist-first dual-read with annotated source.
    ``read_task``, ``get_ready_tasks``, ``get_plan_status`` routing through ``read_plan``.
    ``list_plans`` Gist-index + local merge.

T4 scope:
    Write-through mutations; ``claim_task`` atomicity (ADR-2509-3).
"""

from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

from .exceptions import ArtifactWriteError, PlanIndexError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
    from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
    from sam_schema.core.models import Task
    from sam_schema.core.plan_id_index import PlanIdIndex, PlanIndexEntry
    from sam_schema.core.task_backend_types import DocumentData, DocumentHandle, PlanData, PlanSummary, TaskData

_yaml_safe = YAML(typ="safe")

_log = logging.getLogger(__name__)

#: Warnings key returned in the MCP create response for local-only plans (ADR-2509-4).
_LOCAL_ONLY_WARNING = (
    "Plan {plan_id} has no associated issue — stored locally only. "
    "This plan is not portable across environments and cannot be retrieved from CI "
    "or fresh checkouts. Associate a GitHub issue with this plan to enable portability."
)


class GistTaskLayer:
    """TaskBackend wrapper adding Gist-first reads and write-through storage to LocalYamlTaskProvider.

    Implements the full :class:`~sam_schema.core.task_backend.TaskBackend` Protocol
    by delegating every method to *local_backend*, with the following additions:

    **create_plan (T2)**:

    - When ``issue`` is provided: uploads plan YAML to Gist and registers the
      ``plan_id → issue`` mapping in the ``PlanIdIndex``.  Failure raises
      :exc:`ArtifactWriteError` (no silent fallback — ADR-2509-5).
    - When ``issue`` is ``None``: local-only creation; no Gist upload.  The
      MCP handler checks ``config.issue is None`` and adds the non-portability
      warning directly to the response.

    **read_plan (T3)**:

    - Resolves ``plan_id → issue`` via ``PlanIdIndex``.
    - If issue found: fetches YAML from Gist via ``ArtifactRegistryClient.read()``.
      Writes YAML to local cache (best-effort) so subsequent calls to
      ``read_task``, ``get_ready_tasks``, and ``get_plan_status`` succeed via the
      local backend without additional Gist round-trips.
    - Falls back to ``LocalYamlTaskProvider.read_plan()`` when Gist content is
      absent, the plan has no index entry, or the plan is local-only.
    - Annotates the source in :attr:`last_read_source` (``"gist"`` or ``"local"``).
    - Raises :exc:`PlanNotFoundError` when neither source has the plan.

    **list_plans (T3)**:

    - Merges ``PlanIdIndex.list_all()`` (Gist-registered) with
      ``LocalYamlTaskProvider.list_plans()`` (local YAML files).
    - Deduplicates by ``plan_id`` (Gist entry takes precedence).
    - For index-only plans (not in local cache), fetches YAML from Gist to
      construct a full :class:`PlanSummary`.
    - Applies search/offset/limit after the merge.

    Informational warnings (e.g., plan index registration failure after a
    successful content upload) are stored in :attr:`last_warnings` so the MCP
    handler can surface them without modifying the ``PlanData`` TypedDict.

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
        plan_data = backend.read_plan("Pa9cebb49")
        if backend.last_read_source == "local":
            # plan was served from local cache — Gist unavailable or predates fix
            ...
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
        #: Source annotation from the most recent ``read_plan`` call.
        #: Set to ``"gist"`` when content was fetched from Gist, ``"local"``
        #: when served from the local filesystem cache.  ``None`` before the
        #: first read.  The MCP handler surfaces a warning when this is ``"local"``.
        self.last_read_source: str | None = None

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
    # Read path — Gist-first dual-read with annotated source (T3).
    # T4 will replace mutation methods with write-through RMW logic.
    # ------------------------------------------------------------------

    def read_plan(self, plan_id: str) -> PlanData:
        """Read a plan by identifier using Gist-first dual-read (ADR-2509-5).

        Read flow:

        1. Resolve ``plan_id → issue`` via :meth:`PlanIdIndex.resolve`.
        2. If ``issue`` is not ``None``: call :meth:`ArtifactRegistryClient.read` to
           fetch YAML from Gist.
        3. If Gist content is returned: write it to the local filesystem cache
           (best-effort — failures logged but not raised), set
           :attr:`last_read_source` to ``"gist"``, then delegate to the local
           backend to deserialize and return the :class:`PlanData`.
        4. If Gist returns nothing, or ``issue`` is ``None`` (local-only or
           unconfigured index): fall back to :meth:`LocalYamlTaskProvider.read_plan`,
           set :attr:`last_read_source` to ``"local"``.
        5. If the local backend also raises :exc:`PlanNotFoundError`: re-raise it —
           **no silent empty return**.

        The local cache write in step 3 allows ``read_task``, ``get_ready_tasks``,
        and ``get_plan_status`` to delegate to the local backend without an
        additional Gist round-trip.

        Args:
            plan_id: Plan identifier (e.g. ``"Pa9cebb49"``).

        Returns:
            :class:`~sam_schema.core.task_backend_types.PlanData` for the plan.

        Raises:
            PlanNotFoundError: When neither Gist nor local storage has the plan.
        """
        # Always reset source annotation at the start of each read.
        self.last_read_source = None

        # Step 1: resolve plan_id → issue via PlanIdIndex.
        issue: int | None = None
        try:
            issue = self._plan_index.resolve(plan_id)
        except Exception:  # noqa: BLE001 — index read failures degrade to local fallback
            _log.warning("GistTaskLayer.read_plan: plan_index.resolve failed for %s — falling back to local", plan_id)

        # Steps 2-3: Gist-first attempt when issue is known.
        if issue is not None:
            try:
                yaml_content = self._artifact_client.read(issue)
            except Exception:  # noqa: BLE001 — Gist read failures degrade to local fallback
                yaml_content = None
                _log.warning(
                    "GistTaskLayer.read_plan: artifact_client.read failed for %s (issue #%d) — falling back to local",
                    plan_id,
                    issue,
                )

            if yaml_content is not None:
                # Write to local cache so get_ready_tasks / get_plan_status can delegate
                # without an additional Gist round-trip.
                self._write_local_cache(plan_id, yaml_content)
                self.last_read_source = "gist"
                _log.debug("GistTaskLayer.read_plan: serving %s from Gist (issue #%d)", plan_id, issue)
                return self._local.read_plan(plan_id)

        # Step 4: Gist unavailable or plan has no index entry — fall back to local.
        _log.warning("GistTaskLayer.read_plan(%s): Gist content unavailable, serving from local cache", plan_id)
        # Step 5: propagate PlanNotFoundError if local also has no plan.
        plan_data = self._local.read_plan(plan_id)
        self.last_read_source = "local"
        return plan_data

    def _write_local_cache(self, plan_id: str, yaml_content: str) -> None:
        """Write Gist YAML content to the local filesystem cache (best-effort).

        Parses the YAML to extract the slug, then writes to
        ``{plan_dir}/{plan_id}-{slug}.yaml``.  Failures are logged at WARNING
        level and do not propagate — a cache write failure leaves the local file
        absent but does not affect the Gist-first read result.

        Args:
            plan_id: Plan identifier used to construct the filename.
            yaml_content: YAML string fetched from Gist.
        """
        try:
            data = _yaml_safe.load(StringIO(yaml_content))
        except Exception:  # noqa: BLE001 — ruamel raises many internal types
            _log.warning(
                "GistTaskLayer._write_local_cache: failed to parse YAML for plan %s — skipping cache write", plan_id
            )
            return

        if not isinstance(data, dict):
            _log.warning(
                "GistTaskLayer._write_local_cache: YAML root is not a dict for plan %s — skipping cache write", plan_id
            )
            return

        # Extract slug from YAML data.  Fall back to the plan_id suffix as slug
        # if the YAML doesn't have a top-level ``feature`` key.
        slug: str = ""
        for key in ("slug", "feature"):
            candidate = data.get(key)
            if isinstance(candidate, str) and candidate:
                slug = candidate.replace(" ", "-").lower()
                break

        if not slug:
            _log.warning(
                "GistTaskLayer._write_local_cache: cannot determine slug for plan %s — skipping cache write", plan_id
            )
            return

        cache_path = self._local._plan_dir / f"{plan_id}-{slug}.yaml"  # noqa: SLF001

        # If a file already exists for this plan_id (possibly with a different slug),
        # prefer the existing path to avoid creating a duplicate.
        try:
            existing = self._local._plan_dir.glob(f"{plan_id}-*.yaml")  # noqa: SLF001
            for existing_path in existing:
                cache_path = existing_path
                break
        except OSError:
            pass  # Glob failure — proceed with computed path.

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(yaml_content, encoding="utf-8")
            _log.debug("GistTaskLayer._write_local_cache: wrote %s to %s", plan_id, cache_path)
        except OSError as exc:
            _log.warning("GistTaskLayer._write_local_cache: failed to write %s to %s: %s", plan_id, cache_path, exc)

    def list_plans(self, *, search: str | None = None, offset: int = 0, limit: int | None = None) -> list[PlanSummary]:
        """List all plans merging Gist-registered and local plans (T3, ADR-2509-2).

        Merge strategy:

        1. Call ``plan_index.list_all()`` to enumerate Gist-registered plans.
        2. Call ``local_backend.list_plans()`` to enumerate local YAML plans.
        3. Build a unified dict keyed by ``plan_id`` (Gist entry takes precedence).
        4. For index entries that are not in the local set: fetch YAML from Gist
           via ``artifact_client.read(issue)`` to build a full
           :class:`~sam_schema.core.task_backend_types.PlanSummary`.
           Index entries with ``issue=None`` cannot be fetched from Gist — they
           are included in the merge only when the local backend has them.
        5. Apply ``search`` filter (substring match on feature + goal + description).
        6. Apply ``offset`` and ``limit``.

        This is eventually consistent — a plan registered in the index but not yet
        uploaded to Gist (or vice versa) will appear with degraded metadata.

        Args:
            search: Optional substring to filter by feature name, goal, or description.
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return.  ``None`` means no limit.

        Returns:
            List of :class:`~sam_schema.core.task_backend_types.PlanSummary` dicts.
        """
        # Step 1: fetch Gist-registered plans from the index.
        index_entries: list[PlanIndexEntry] = []
        try:
            index_entries = self._plan_index.list_all()
        except Exception:  # noqa: BLE001 — index read failures degrade to local-only list
            _log.warning("GistTaskLayer.list_plans: plan_index.list_all() failed — listing local plans only")

        # Step 2: fetch local plans (search+pagination handled after merge).
        local_summaries: list[PlanSummary] = self._local.list_plans()

        # Step 3: build a unified dict; Gist entry takes precedence.
        merged: dict[str, PlanSummary] = {s["plan_id"]: s for s in local_summaries}

        # Step 4: incorporate index entries.
        for entry in index_entries:
            if entry.plan_id in merged:
                # Already have local summary — enrich with issue if missing.
                if entry.issue is not None and "issue" not in merged[entry.plan_id]:
                    merged[entry.plan_id]["issue"] = str(entry.issue)  # type: ignore[typeddict-unknown-key]
                continue

            # Index-only plan (not in local cache).  Attempt Gist fetch.
            if entry.issue is None:
                # Local-only plan with no issue — cannot fetch from Gist and not
                # present locally, so there's nothing to include.
                continue

            gist_summary = self._fetch_gist_summary(entry)
            if gist_summary is not None:
                merged[entry.plan_id] = gist_summary

        all_summaries = list(merged.values())

        # Step 5: apply search filter.
        if search is not None:
            search_lower = search.lower()
            all_summaries = [
                s
                for s in all_summaries
                if search_lower in f"{s['feature']} {s.get('goal', '')} {s.get('description', '')}".lower()
            ]

        # Step 6: apply offset and limit.
        paginated = all_summaries[offset:]
        if limit is not None:
            paginated = paginated[:limit]
        return paginated

    def _fetch_gist_summary(self, entry: PlanIndexEntry) -> PlanSummary | None:
        """Fetch plan YAML from Gist and construct a :class:`PlanSummary`.

        Used by ``list_plans`` for index-only plans not present in the local cache.
        Returns ``None`` when the Gist fetch fails or content cannot be parsed.

        Args:
            entry: Plan index entry containing ``plan_id``, ``issue``, and ``slug``.

        Returns:
            :class:`~sam_schema.core.task_backend_types.PlanSummary` or ``None``.
        """
        if entry.issue is None:
            return None
        try:
            yaml_content = self._artifact_client.read(entry.issue)
        except Exception:  # noqa: BLE001 — Gist read failures produce no summary
            _log.warning(
                "GistTaskLayer._fetch_gist_summary: artifact_client.read failed for %s (issue #%d)",
                entry.plan_id,
                entry.issue,
            )
            return None

        if yaml_content is None:
            return None

        try:
            data = _yaml_safe.load(StringIO(yaml_content))
        except Exception:  # noqa: BLE001 — ruamel raises many internal types
            _log.warning("GistTaskLayer._fetch_gist_summary: failed to parse YAML for %s — skipping", entry.plan_id)
            return None

        if not isinstance(data, dict):
            return None

        tasks_raw = data.get("tasks") or []
        task_count = len(tasks_raw) if isinstance(tasks_raw, list) else 0

        summary: PlanSummary = {
            "plan_id": entry.plan_id,
            "feature": str(data.get("feature") or entry.slug),
            "goal": str(data.get("goal") or ""),
            "description": str(data.get("description") or ""),
            "task_count": task_count,
            "source_path": None,
            "issue": str(entry.issue),
        }
        return summary

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level plan fields.  Delegates to local backend (T4 adds write-through)."""
        self._local.update_plan_fields(plan_id, context=context, set_fields=set_fields)

    def read_task(self, plan_id: str, task_id: str) -> TaskData:
        """Read a single task, routing through Gist-first :meth:`read_plan`.

        Calls :meth:`read_plan` first to populate the local cache with Gist content
        when available.  After the cache is warm, delegates to the local backend for
        task extraction (which re-reads the local file rather than holding state in
        memory).

        Args:
            plan_id: Plan identifier.
            task_id: Task identifier within the plan.

        Returns:
            :class:`~sam_schema.core.task_backend_types.TaskData` for the task.

        Raises:
            PlanNotFoundError: When neither Gist nor local storage has the plan.
            TaskNotFoundError: When the task does not exist within the plan.
        """
        # Warm the local cache via Gist-first read_plan.
        self.read_plan(plan_id)
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
        """Return tasks ready for dispatch, routing through Gist-first :meth:`read_plan`.

        Calls :meth:`read_plan` to populate the local cache, then delegates to the
        local backend for dependency-graph computation.

        Args:
            plan_id: Plan identifier.

        Returns:
            List of :class:`~sam_schema.core.task_backend_types.TaskData` for tasks
            with ``not-started`` status and all dependencies resolved.

        Raises:
            PlanNotFoundError: When neither Gist nor local storage has the plan.
        """
        self.read_plan(plan_id)
        return self._local.get_ready_tasks(plan_id)

    def get_plan_status(self, plan_id: str) -> dict[str, object]:
        """Return plan status summary, routing through Gist-first :meth:`read_plan`.

        Calls :meth:`read_plan` to populate the local cache, then delegates to the
        local backend for status computation.

        Args:
            plan_id: Plan identifier.

        Returns:
            Dict with ``feature``, ``total_tasks``, ``by_status``, ``ready_tasks``,
            ``blocked_tasks``, ``completion_pct``, ``has_cycles``, and ``state``.

        Raises:
            PlanNotFoundError: When neither Gist nor local storage has the plan.
        """
        self.read_plan(plan_id)
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
