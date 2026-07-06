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
    plans not present in the local cache, a minimal summary is synthesised from the
    index entry metadata (``plan_id``, ``slug``, ``issue``) — no extra Gist round-trip.

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

import hashlib
import logging
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

from .exceptions import ArtifactWriteError, ConcurrentClaimUnsupportedError, PlanIndexError, PlanNotFoundError

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
    - For index-only plans (not in local cache), synthesises a minimal
      :class:`PlanSummary` from the index entry (``plan_id``, ``slug``,
      ``issue``) — no Gist API call, preventing N+1 growth.
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
        #: Plan IDs whose local YAML is known to be ahead of Gist because a
        #: rate-limited ``_write_through`` skipped the upload.  ``read_plan``
        #: bypasses the Gist-first read for these plans to prevent stale Gist
        #: content from overwriting the in-flight local mutation.  Entries are
        #: cleared when a subsequent successful write-through syncs the plan.
        self._local_authoritative_plans: set[str] = set()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_local_authoritative(self, plan_id: str) -> bool:
        """Return ``True`` when local YAML is known to be ahead of the Gist copy.

        Checks the in-memory set first (fast path), then falls back to the
        ``.stale`` sidecar file on disk.  The sidecar check is necessary
        because ``_get_backend()`` in ``server.py`` constructs a fresh
        ``GistTaskLayer`` per MCP tool call — the in-memory set resets to
        empty each time, so the sidecar is the only durable signal that
        survives across calls.
        """
        if plan_id in self._local_authoritative_plans:
            return True
        try:
            local_path = self._local._resolve_path(plan_id)  # noqa: SLF001
            if local_path.with_suffix(".stale").exists():
                self._local_authoritative_plans.add(plan_id)
                return True
        except (PlanNotFoundError, OSError):
            pass
        return False

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

        # Skip Gist-first read when local YAML is known to be ahead of Gist because a
        # rate-limited _write_through skipped the upload.  Fetching stale Gist content
        # here would overwrite the in-flight local mutation via _write_local_cache.
        # _is_local_authoritative checks both the in-memory set (same-call fast path)
        # and a .stale sidecar file (cross-call persistence — _get_backend constructs
        # a fresh GistTaskLayer per MCP call, so the in-memory set alone is not enough).
        if self._is_local_authoritative(plan_id):
            _log.debug(
                "GistTaskLayer.read_plan: %s is local-authoritative (pending Gist sync), serving from local", plan_id
            )
            plan_data = self._local.read_plan(plan_id)
            self.last_read_source = "local"
            return plan_data

        # Step 1: resolve plan_id → issue via PlanIdIndex.
        issue: int | None = None
        try:
            issue = self._plan_index.resolve(plan_id)
        except Exception:  # noqa: BLE001 — plan_index.resolve delegates to ruamel.yaml and Gist API; network and ruamel internal exception types are not enumerable from this call site
            _log.warning("GistTaskLayer.read_plan: plan_index.resolve failed for %s — falling back to local", plan_id)

        # Steps 2-3: Gist-first attempt when issue is known.
        if issue is not None:
            try:
                yaml_content = self._artifact_client.read(issue)
            except Exception:  # noqa: BLE001 — artifact_client.read wraps GitHub API calls; requests transport and authentication exceptions are not enumerable from this call site
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

        if not cache_path.resolve().is_relative_to(self._local._plan_dir.resolve()):  # noqa: SLF001
            raise ValueError(f"Slug produces unsafe cache path: {cache_path}")

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
        4. For index entries that are not in the local set: synthesise a minimal
           :class:`~sam_schema.core.task_backend_types.PlanSummary` from the index
           entry metadata (``plan_id``, ``slug``, ``issue``) without any Gist API call.
           ``goal``, ``description``, and ``task_count`` default to empty/zero because
           that data is only available in the full plan YAML blob.
           Index entries with ``issue=None`` are skipped — they are not in local cache
           and cannot be reconstructed without a Gist fetch.
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
        except Exception:  # noqa: BLE001 — plan_index.list_all delegates to ruamel.yaml and Gist API; network and ruamel internal exception types are not enumerable from this call site
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

            # Index-only plan (not in local cache).
            if entry.issue is None:
                # Local-only plan recorded with issue=null — cannot reconstruct
                # without a Gist fetch and is not present locally; skip.
                continue

            # Build a metadata-only summary from the index entry.  goal,
            # description, and task_count are unknown without fetching the
            # full plan YAML blob, but list_plans only needs these fields for
            # optional search filtering — the trade-off eliminates one Gist
            # API call per index-only plan (prevents unbounded N+1 growth).
            merged[entry.plan_id] = {
                "plan_id": entry.plan_id,
                "feature": entry.slug,
                "goal": "",
                "description": "",
                "task_count": 0,
                "source_path": None,
                "issue": str(entry.issue),
            }

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

    # ------------------------------------------------------------------
    # Mutation helpers (T4)
    # ------------------------------------------------------------------

    def _resolve_issue(self, plan_id: str) -> int | None:
        """Resolve plan_id to its GitHub issue number via the plan index.

        Returns ``None`` when the plan is local-only or the index has no entry.
        Index read failures are treated as a non-fatal miss — the caller decides
        whether to degrade to local-only or raise.

        Args:
            plan_id: Plan identifier to resolve.

        Returns:
            GitHub issue number, or ``None`` when not found.
        """
        try:
            return self._plan_index.resolve(plan_id)
        except Exception:  # noqa: BLE001 — plan_index.resolve delegates to ruamel.yaml and Gist API; network and ruamel internal exception types are not enumerable from this call site
            _log.warning(
                "GistTaskLayer._resolve_issue: plan_index.resolve failed for %s — treating as local-only", plan_id
            )
            return None

    def _read_local_yaml_for_plan(self, plan_id: str) -> str:
        """Read the current local YAML file for a plan.

        Used after a local-backend mutation to retrieve the updated YAML
        content for Gist write-through.

        Args:
            plan_id: Plan identifier whose local YAML to read.

        Returns:
            YAML content string of the current (post-mutation) local file.

        Raises:
            ArtifactWriteError: When the local file cannot be found or read.
        """
        try:
            local_path = self._local._resolve_path(plan_id)  # noqa: SLF001
        except Exception as exc:
            msg = f"cannot resolve local path for plan {plan_id}: {exc}"
            _log.error("GistTaskLayer._read_local_yaml_for_plan: %s", msg)
            raise ArtifactWriteError(plan_id=plan_id, issue=None, reason=msg) from exc
        return self._read_local_yaml(plan_id, local_path)

    def _resolve_write_through_sidecars(self, plan_id: str) -> tuple[Path | None, Path | None]:
        """Resolve the ``.sha256`` and ``.stale`` sidecar paths for a plan, best-effort.

        ``hash_sidecar`` — content-hash dedup to skip unchanged Gist PATCHes.
        ``stale_sidecar`` — durable marker that local YAML is ahead of Gist after
        a rate-limited write-through skip.  Persists across ``GistTaskLayer``
        instances (a fresh instance is created per MCP call) so ``read_plan``
        bypasses Gist-first in subsequent calls even though the in-memory
        ``_local_authoritative_plans`` set resets to empty.

        Returns:
            A ``(hash_sidecar, stale_sidecar)`` tuple, or ``(None, None)`` when the
            local path cannot be resolved — sidecar handling is best-effort and
            callers must tolerate both being absent.
        """
        try:
            local_path = self._local._resolve_path(plan_id)  # noqa: SLF001
        except PlanNotFoundError:
            _log.debug(
                "GistTaskLayer._write_through: path resolution failed for plan %s — skipping hash dedup", plan_id
            )
            return None, None
        return local_path.with_suffix(".sha256"), local_path.with_suffix(".stale")

    def _write_through_content_unchanged(
        self, hash_sidecar: Path | None, content_hash: str, plan_id: str, issue: int
    ) -> bool:
        """Return ``True`` when ``content_hash`` matches the last uploaded hash sidecar."""
        if hash_sidecar is None:
            return False
        try:
            if hash_sidecar.read_text().strip() == content_hash:
                _log.debug(
                    "GistTaskLayer._write_through: content unchanged for plan %s (issue #%d), skipping Gist PATCH",
                    plan_id,
                    issue,
                )
                return True
        except OSError:
            _log.debug(
                "GistTaskLayer._write_through: sidecar read failed for plan %s — uploading as normal",
                plan_id,
                exc_info=True,
            )
        return False

    def _clear_stale_sidecar(self, stale_sidecar: Path | None, plan_id: str) -> None:
        """Best-effort removal of the ``.stale`` sidecar after a successful upload."""
        if stale_sidecar is None:
            return
        try:
            stale_sidecar.unlink(missing_ok=True)
        except OSError:
            _log.debug(
                "GistTaskLayer._write_through: failed to clear stale sidecar for plan %s — "
                "read_plan will re-check on next call",
                plan_id,
            )

    def _mark_stale_sidecar(self, stale_sidecar: Path | None, plan_id: str) -> None:
        """Best-effort write of the ``.stale`` sidecar after a rate-limited upload skip."""
        if stale_sidecar is None:
            return
        try:
            stale_sidecar.touch()
        except OSError:
            _log.debug(
                "GistTaskLayer._write_through: failed to write stale sidecar for plan %s — "
                "local-authoritative bypass will not persist across MCP calls",
                plan_id,
            )

    def _write_hash_sidecar(self, hash_sidecar: Path | None, content_hash: str, plan_id: str) -> None:
        """Best-effort write of the ``.sha256`` sidecar after a successful upload."""
        if hash_sidecar is None:
            return
        try:
            hash_sidecar.write_text(content_hash)
        except OSError:
            _log.debug(
                "GistTaskLayer._write_through: sidecar write failed for plan %s — dedup skipped next call",
                plan_id,
                exc_info=True,
            )

    def _write_through(self, plan_id: str, issue: int) -> None:
        """Read the current local YAML and upload it to Gist.

        Implements the mandatory write-through step in mutation operations
        (ADR-2509-5): reads the post-mutation local YAML and calls
        ``artifact_client.store()``.  Raises ``ArtifactWriteError`` on any
        failure — no silent fallback.

        Content-hash deduplication: uploads are skipped when the YAML content
        is identical to the last successfully uploaded version, tracked via a
        ``.sha256`` sidecar file next to the local YAML.  Sidecar read/write
        failures are non-fatal; the upload proceeds when the sidecar is absent
        or unreadable.

        Args:
            plan_id: Plan identifier whose YAML to upload.
            issue: GitHub issue number keying the Gist artifact.

        Raises:
            ArtifactWriteError: When the local YAML cannot be read, or when
                the Gist upload fails due to a genuine error (e.g. wrong token
                scope).  Rate-limit responses (secondary rate limit, abuse
                detection) are handled by logging a WARNING and returning
                without raising — local YAML state is preserved and the MCP
                call succeeds.
        """
        yaml_content = self._read_local_yaml_for_plan(plan_id)
        content_hash = hashlib.sha256(yaml_content.encode()).hexdigest()

        hash_sidecar, stale_sidecar = self._resolve_write_through_sidecars(plan_id)

        if self._write_through_content_unchanged(hash_sidecar, content_hash, plan_id, issue):
            return

        RATE_LIMIT_SIGNALS = ("secondary rate limit", "abuse detection")

        try:
            self._artifact_client.store(issue=issue, content=yaml_content)
            _log.info("GistTaskLayer._write_through: uploaded plan %s YAML to Gist (issue #%d)", plan_id, issue)
            self._local_authoritative_plans.discard(plan_id)
            self._clear_stale_sidecar(stale_sidecar, plan_id)
        except ArtifactWriteError as exc:
            reason_lower = exc.reason.lower()
            if any(signal in reason_lower for signal in RATE_LIMIT_SIGNALS):
                _log.warning(
                    "GistTaskLayer._write_through: Gist upload skipped for plan %s (issue #%d) due to rate limit"
                    " — local YAML is preserved; remote may be stale. Reason: %s",
                    plan_id,
                    issue,
                    exc.reason,
                )
                self._local_authoritative_plans.add(plan_id)
                self._mark_stale_sidecar(stale_sidecar, plan_id)
                return
            _log.error(
                "GistTaskLayer._write_through: Gist upload failed for plan %s (issue #%d) — raising", plan_id, issue
            )
            raise

        self._write_hash_sidecar(hash_sidecar, content_hash, plan_id)

    def update_plan_fields(
        self, plan_id: str, *, context: str | None = None, set_fields: dict[str, str | int | list[str]] | None = None
    ) -> None:
        """Update top-level plan fields with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate mutation to ``local_backend.update_plan_fields()`` (writes local YAML).
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: read the post-mutation local YAML and upload to Gist
           via ``artifact_client.store()`` (raises ``ArtifactWriteError`` on failure).
        4. If issue is ``None`` (local-only plan): log a warning; local write is the
           only persistence (no Gist key available).

        Args:
            plan_id: Backend-assigned plan identifier.
            context: When provided, replaces the plan context narrative.
            set_fields: Optional mapping of field names to new values.

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
        """
        # Step 1: apply mutation locally first.
        self._local.update_plan_fields(plan_id, context=context, set_fields=set_fields)

        # Steps 2-4: Gist write-through when issue is known.
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning(
                "GistTaskLayer.update_plan_fields: plan %s has no issue — local-only write, not portable", plan_id
            )
            return
        self._write_through(plan_id, issue)

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
        """Claim a task, raising for local-only plans; delegating to local backend otherwise.

        **Atomicity decision (ADR-2509-3 resolution — Option 3: Serialized Dispatch):**

        GitHub's label mutation API (``addLabels``/``removeLabels``) is idempotent and
        non-conditional as of 2026-05-30 — there is no native compare-and-swap primitive.
        Gist blob read-modify-write also provides no CAS guarantee.

        **Chosen mechanism**: The exactly-once guarantee is provided by the caller
        (dispatch orchestrator), not by ``claim_task`` itself.  The MCP dispatch loop
        in ``implement-feature`` sequences claim calls one at a time — only one task
        is claimed per orchestrator per dispatch wave, and the orchestrator waits for
        the claim response before dispatching the next task.  Under this single-writer
        dispatch pattern, two agents never race on the same task.

        **Declared contract deviation**: ``GistTaskLayer.claim_task()`` does NOT provide
        exactly-once in isolation.  If two callers invoke ``claim_task`` concurrently on
        the same task, both may return ``True``.  Exactly-once is guaranteed only when the
        caller serializes claims (Dispatch pattern, ADR-1770-1 single-writer scope).
        This deviation is documented here and must be noted in CLAUDE.md (T6).

        **Why not Option 1 (GitHub conditional mutation)**: No such primitive exists in
        the GitHub REST or GraphQL API as of 2026-05-30.  ``addLabels``/``removeLabels``
        are idempotent, not conditional.  Prescribing a non-existent primitive would be
        a silent failure.

        **Why not Option 2 (external lock)**: Adds operational complexity (Redis, or a
        separate Gist-based lock file with its own race conditions) with no benefit when
        the dispatch pattern already serializes via Option 3.

        **Why not Option 4 (accept eventual consistency)**: Duplicate work detection
        requires idempotent task outputs, which is not guaranteed by the TaskBackend
        Protocol.  It is the highest-ambiguity option and produces the weakest guarantee.

        **Verification**: Two concurrent ``claim_task`` calls on the same local-YAML plan
        through the existing ``LocalYamlTaskProvider`` both return ``True`` (a known race
        in the pre-T4 state — the local YAML provider reads then writes non-atomically).
        Under the serialized-dispatch contract the orchestrator prevents this race at the
        caller level.  A unit test demonstrating the deviation is in ``tests_sam/`` (T5).

        **Write-back after claim**: After a successful local claim, a best-effort Gist
        write-back updates the YAML blob so ``read_plan`` returns consistent task status.
        A write-back failure logs a WARNING and does not roll back the claim — the local
        YAML is the authoritative claim record.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.

        Returns:
            ``True`` if the task was successfully claimed; ``False`` if the task was
            not in ``not-started`` status (already claimed, complete, or skipped).

        Raises:
            ConcurrentClaimUnsupportedError: When ``plan_id`` resolves to a local-only
                plan (``issue=None``).  Parallel claim has no GitHub anchor for
                coordination.
            PlanNotFoundError: Propagated from local backend.
            TaskNotFoundError: Propagated from local backend.
        """
        # Resolve issue to gate on local-only plans.
        issue = self._resolve_issue(plan_id)
        if issue is None:
            # Raise immediately — local-only plans cannot support concurrent claim.
            # Single-agent workflows that do not share plans across agents may still
            # call claim_task on local-only plans via LocalYamlTaskProvider directly.
            raise ConcurrentClaimUnsupportedError(plan_id)

        # Delegate claim to the local backend (non-atomic read-then-write under ADR-2509-3).
        claimed = self._local.claim_task(plan_id, task_id)

        if claimed:
            # Best-effort write-back: update Gist YAML so read_plan returns in-progress.
            try:
                self._write_through(plan_id, issue)
                _log.info(
                    "GistTaskLayer.claim_task: wrote back claimed status for %s/%s to Gist (issue #%d)",
                    plan_id,
                    task_id,
                    issue,
                )
            except ArtifactWriteError as exc:
                # Write-back failure: claim is still valid (label/local already updated).
                # Log at WARNING; do not roll back the claim.
                _log.warning(
                    "GistTaskLayer.claim_task: Gist write-back failed for %s/%s (issue #%d): %s "
                    "— claim is recorded locally but Gist YAML may be stale",
                    plan_id,
                    task_id,
                    issue,
                    exc,
                )

        return claimed

    def update_task_status(self, plan_id: str, task_id: str, status: str) -> None:
        """Update task status with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate mutation to ``local_backend.update_task_status()``.
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            status: New status string (must be a valid ``TaskStatus`` value).

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
            TaskNotFoundError: Propagated from ``local_backend``.
            TaskValidationError: When ``status`` is not a valid ``TaskStatus`` value.
        """
        self._local.update_task_status(plan_id, task_id, status)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning(
                "GistTaskLayer.update_task_status: plan %s has no issue — local-only write, not portable", plan_id
            )
            return
        self._write_through(plan_id, issue)

    def update_task_fields(self, plan_id: str, task_id: str, fields: dict[str, str | int | list[str]]) -> None:
        """Update task fields with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate mutation to ``local_backend.update_task_fields()``.
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            fields: Mapping of field names to new values.

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
            TaskNotFoundError: Propagated from ``local_backend``.
        """
        self._local.update_task_fields(plan_id, task_id, fields)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning(
                "GistTaskLayer.update_task_fields: plan %s has no issue — local-only write, not portable", plan_id
            )
            return
        self._write_through(plan_id, issue)

    def update_task(self, plan_id: str, task: Task) -> None:
        """Replace a stored task with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate full task replacement to ``local_backend.update_task()``.
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Backend-assigned plan identifier.
            task: Fully-validated Task model whose ``id`` identifies the target
                task within the plan.

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
            TaskNotFoundError: Propagated from ``local_backend``.
        """
        self._local.update_task(plan_id, task)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning("GistTaskLayer.update_task: plan %s has no issue — local-only write, not portable", plan_id)
            return
        self._write_through(plan_id, issue)

    def append_task_section(self, plan_id: str, task_id: str, section_name: str, content: str) -> None:
        """Append a markdown section to a task with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate to ``local_backend.append_task_section()``.
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Backend-assigned plan identifier.
            task_id: Task identifier within the plan.
            section_name: Markdown heading name for the section (without ``##``).
            content: Markdown content to append.

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
            TaskNotFoundError: Propagated from ``local_backend``.
        """
        self._local.append_task_section(plan_id, task_id, section_name, content)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning(
                "GistTaskLayer.append_task_section: plan %s has no issue — local-only write, not portable", plan_id
            )
            return
        self._write_through(plan_id, issue)

    def append_task(self, plan_id: str, task: Task) -> dict[str, Any]:
        """Append a task to an existing plan with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate to ``local_backend.append_task()`` (single-writer per ADR-1770-1).
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Plan identifier.
            task: Validated Task model to append.

        Returns:
            ``{"appended": True, "task_id": task.id}``

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
            TaskValidationError: When the task ID already exists in the plan.
        """
        result = self._local.append_task(plan_id, task)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning("GistTaskLayer.append_task: plan %s has no issue — local-only write, not portable", plan_id)
            return result
        self._write_through(plan_id, issue)
        return result

    def finalize_plan(self, plan_id: str) -> dict[str, Any]:
        """Finalize a plan with mandatory Gist write-through (ADR-2509-5).

        Read-modify-write flow:

        1. Delegate to ``local_backend.finalize_plan()`` to set ``state=ready``.
        2. Resolve ``plan_id → issue`` via ``PlanIdIndex``.
        3. If issue is set: upload post-mutation local YAML to Gist (raises on failure).
        4. If issue is ``None``: log warning; local-only write.

        Args:
            plan_id: Plan identifier.

        Returns:
            ``{"finalized": True, "state": "ready"}``

        Raises:
            ArtifactWriteError: When Gist write fails and plan has an issue.
            PlanNotFoundError: Propagated from ``local_backend``.
        """
        result = self._local.finalize_plan(plan_id)
        issue = self._resolve_issue(plan_id)
        if issue is None:
            _log.warning("GistTaskLayer.finalize_plan: plan %s has no issue — local-only write, not portable", plan_id)
            return result
        self._write_through(plan_id, issue)
        return result

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
