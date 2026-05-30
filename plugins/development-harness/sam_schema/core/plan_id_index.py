"""Gist-backed plan_id ↔ issue number reverse-map index.

This module provides :class:`PlanIdIndex`, which stores a YAML blob on a
sentinel GitHub issue to resolve ``plan_id`` → ``issue_number`` without
touching local disk.  The index survives fresh checkouts and is readable from
CI environments, worktree-isolated agents, and anywhere with a valid GitHub
token.

Design decisions (see ADR-2509-2):
    - The index lives on a **sentinel** GitHub issue whose number is stored in
      ``.dh/config.yaml`` under ``sam.plan_index_issue``.
    - Index entries are eventually consistent — a missing entry is a
      discoverability degradation, not data loss.  Plan content is stored on
      the plan's own issue Gist regardless of index state.
    - Concurrency: index registration is a whole-blob read-modify-write.
      Concurrent registrations in a planning session are an architectural
      error (ADR-1770-1 single-writer contract).

Index schema (YAML blob stored on the sentinel issue):

.. code-block:: yaml

    version: 1
    entries:
      - plan_id: P3e7e163d
        issue: 2498
        slug: feature-x
        created_at: "2026-05-30T12:00:00Z"
      - plan_id: Pab12cd34
        issue: null          # local-only plan
        slug: local-scratch
        created_at: "2026-05-30T14:00:00Z"
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ruamel.yaml import YAML

from .exceptions import ArtifactWriteError, PlanIndexConfigError, PlanIndexError

if TYPE_CHECKING:
    from .artifact_registry_client import ArtifactRegistryClient

_log = logging.getLogger(__name__)

_yaml = YAML(typ="safe")
_yaml_round_trip = YAML()  # round-trip for writing with order preserved


@dataclass(frozen=True, slots=True)
class PlanIndexEntry:
    """A single entry in the plan_id → issue reverse-map index.

    Attributes:
        plan_id: Plan identifier string, e.g. ``"P3e7e163d"``.
        issue: GitHub issue number, or ``None`` for local-only plans.
        slug: Human-readable plan slug, e.g. ``"feature-x"``.
        created_at: ISO 8601 timestamp of when the entry was registered.
    """

    plan_id: str
    issue: int | None
    slug: str
    created_at: str


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        UTC timestamp string in ``YYYY-MM-DDTHH:MM:SSZ`` format.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_index_yaml(yaml_str: str) -> list[PlanIndexEntry]:
    """Parse a plan-index YAML blob into a list of :class:`PlanIndexEntry`.

    Unknown extra keys in the YAML are silently ignored for forward
    compatibility.

    Args:
        yaml_str: YAML string matching the plan-index schema.

    Returns:
        List of :class:`PlanIndexEntry` objects.  Returns an empty list
        when the YAML is empty, malformed, or contains no entries.
    """
    try:
        data = _yaml.load(yaml_str)
    except Exception:  # noqa: BLE001 — ruamel raises many internal types
        _log.warning("PlanIdIndex: failed to parse plan-index YAML — treating as empty index")
        return []

    if not isinstance(data, dict):
        return []

    raw_entries = data.get("entries") or []
    if not isinstance(raw_entries, list):
        return []

    entries: list[PlanIndexEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            continue
        plan_id = raw.get("plan_id")
        slug = raw.get("slug")
        if not isinstance(plan_id, str) or not isinstance(slug, str):
            continue
        raw_issue = raw.get("issue")
        issue = int(raw_issue) if isinstance(raw_issue, int) else None
        created_at = raw.get("created_at") or ""
        entries.append(PlanIndexEntry(plan_id=plan_id, issue=issue, slug=slug, created_at=created_at))
    return entries


def _serialize_index_yaml(entries: list[PlanIndexEntry]) -> str:
    """Serialize a list of :class:`PlanIndexEntry` to a plan-index YAML string.

    Args:
        entries: List of index entries to serialize.

    Returns:
        YAML string matching the plan-index schema (version 1).
    """
    data: dict[str, Any] = {
        "version": 1,
        "entries": [
            {"plan_id": e.plan_id, "issue": e.issue, "slug": e.slug, "created_at": e.created_at} for e in entries
        ],
    }
    buf = StringIO()
    _yaml_round_trip.dump(data, buf)
    return buf.getvalue()


class PlanIdIndex:
    """Gist-backed reverse-map index resolving plan_id ↔ GitHub issue number.

    The index is a YAML blob stored on a **sentinel** GitHub issue (configured
    via ``sam.plan_index_issue`` in ``.dh/config.yaml``).  It is the only
    mechanism that allows ``read_plan(plan_id)`` to resolve to an issue number
    without local filesystem state.

    Registration and resolution are eventually consistent — a missing entry
    degrades discoverability but does not cause data loss.  Plan content is
    stored on the plan's own issue Gist independently of the index.

    Args:
        artifact_client: Client for Gist read/write operations.
        sentinel_issue: GitHub issue number hosting the plan-index blob.

    Example::

        client = ArtifactRegistryClient()
        index = PlanIdIndex(artifact_client=client, sentinel_issue=42)
        index.register("P3e7e163d", issue=2498, slug="feature-x")
        issue_num = index.resolve("P3e7e163d")  # → 2498
    """

    def __init__(self, artifact_client: ArtifactRegistryClient, sentinel_issue: int) -> None:
        """Initialise with artifact client and sentinel issue number.

        Args:
            artifact_client: Wrapped Gist client for index storage.
            sentinel_issue: GitHub issue number of the stable sentinel index
                issue.  Must be a positive integer.
        """
        self._client = artifact_client
        self._sentinel_issue = sentinel_issue
        # Session-scoped read cache — valid for the lifetime of this object,
        # which is one MCP handler invocation (_get_backend() constructs a
        # fresh GistTaskLayer + PlanIdIndex per call).  Eliminates redundant
        # Gist round-trips when resolve(), list_all(), and register() are
        # called in the same invocation (e.g. create_plan: register + list).
        self._entries_cache: list[PlanIndexEntry] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, plan_id: str, issue: int | None, slug: str) -> None:
        """Add or update the plan_id → issue mapping in the Gist index.

        Performs a read-modify-write on the plan-index blob on the sentinel
        issue.  If an entry for ``plan_id`` already exists it is updated
        in-place; otherwise a new entry is appended.

        When ``issue`` is ``None``, the entry is recorded with ``issue: null``
        to mark the plan as local-only.  This is not an error — it allows
        ``list_all()`` to enumerate local-only plans.

        Args:
            plan_id: Plan identifier to register.
            issue: GitHub issue number for this plan, or ``None`` for a
                local-only plan.
            slug: Human-readable plan slug.

        Raises:
            PlanIndexConfigError: When ``sentinel_issue`` is 0 (unconfigured).
            PlanIndexError: When the Gist write fails.
        """
        if self._sentinel_issue == 0:
            raise PlanIndexConfigError

        entries = self._read_entries()
        new_entry = PlanIndexEntry(plan_id=plan_id, issue=issue, slug=slug, created_at=_now_iso())

        # Upsert — replace existing entry with the same plan_id.
        updated = [e for e in entries if e.plan_id != plan_id]
        updated.append(new_entry)

        yaml_str = _serialize_index_yaml(updated)
        try:
            self._client.store_index(self._sentinel_issue, yaml_str)
        except ArtifactWriteError as exc:
            # Invalidate cache — the write may or may not have committed;
            # the next read must go to Gist for the authoritative state.
            self._entries_cache = None
            raise PlanIndexError(
                plan_id=plan_id, reason=f"Gist write failed for sentinel issue #{self._sentinel_issue}: {exc.reason}"
            ) from exc
        # Success: cache the written state so subsequent resolve()/list_all()
        # calls in this invocation return the updated entries without a Gist
        # round-trip.
        self._entries_cache = updated

    def resolve(self, plan_id: str) -> int | None:
        """Return the GitHub issue number for a registered plan_id.

        Args:
            plan_id: Plan identifier to look up.

        Returns:
            Issue number when found and ``issue`` is not null, or ``None``
            when the plan_id is not in the index or is recorded as
            local-only (``issue: null``).
        """
        if self._sentinel_issue == 0:
            _log.debug("PlanIdIndex.resolve: sentinel_issue not configured — returning None")
            return None

        entries = self._read_entries()
        for entry in entries:
            if entry.plan_id == plan_id:
                return entry.issue
        return None

    def list_all(self) -> list[PlanIndexEntry]:
        """Return all registered plan index entries.

        Used by ``GistTaskLayer.list_plans()`` to enumerate plans registered
        in the Gist index, supplemented by ``LocalYamlTaskProvider.list_plans()``
        for plans not yet registered.

        Returns:
            List of all :class:`PlanIndexEntry` objects.  Returns an empty
            list when the sentinel issue is not configured or when the index
            blob is absent.
        """
        if self._sentinel_issue == 0:
            _log.debug("PlanIdIndex.list_all: sentinel_issue not configured — returning empty list")
            return []

        return self._read_entries()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_entries(self) -> list[PlanIndexEntry]:
        """Fetch and parse the plan-index YAML blob from Gist, with session caching.

        The result is cached in :attr:`_entries_cache` for the lifetime of
        this object (one MCP handler invocation).  Subsequent calls return
        the cached list directly without touching the network.  The cache is
        updated by :meth:`register` after a successful write, and invalidated
        on write failure.

        Returns an empty list when the blob is absent or unparseable.

        Returns:
            List of :class:`PlanIndexEntry` from the current Gist blob.
        """
        if self._entries_cache is not None:
            return self._entries_cache
        yaml_str = self._client.read_index(self._sentinel_issue)
        if yaml_str is None:
            self._entries_cache = []
        else:
            self._entries_cache = _parse_index_yaml(yaml_str)
        return self._entries_cache


def create_plan_id_index(artifact_client: ArtifactRegistryClient) -> PlanIdIndex:
    """Create a :class:`PlanIdIndex` from the configured sentinel issue.

    Reads ``sam.plan_index_issue`` from ``.dh/config.yaml``.  When the key
    is absent, uses ``0`` as a sentinel meaning "unconfigured" — the index
    will return ``None`` on all reads and raise
    :exc:`~sam_schema.core.exceptions.PlanIndexConfigError` on writes.

    Args:
        artifact_client: Wrapped Gist client to pass to the index.

    Returns:
        Configured :class:`PlanIdIndex` instance.
    """
    sentinel_issue = _load_sentinel_issue()
    return PlanIdIndex(artifact_client=artifact_client, sentinel_issue=sentinel_issue)


def _load_sentinel_issue() -> int:
    """Read the sentinel issue number from ``.dh/config.yaml``.

    Looks for ``sam.plan_index_issue`` in the project and user config files,
    in priority order (project first, then user home).  Uses the same YAML
    loading logic as ``dh_config`` without importing its private functions.

    Returns:
        Positive integer sentinel issue number, or ``0`` when not configured.
    """
    for config_path in _config_search_paths():
        data = _load_yaml_file(config_path)
        if data is None:
            continue
        sam_section = data.get("sam")
        if not isinstance(sam_section, dict):
            continue
        raw = cast("dict[str, object]", sam_section).get("plan_index_issue")
        if isinstance(raw, int) and raw > 0:
            _log.debug("_load_sentinel_issue: found plan_index_issue=%d in %s", raw, config_path)
            return raw
    return 0


def _load_yaml_file(path: Path) -> dict[str, object] | None:
    """Read a YAML config file and return the parsed dict, or None on any error.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed dict when the file exists and is valid YAML, otherwise ``None``.
    """
    if not path.is_file():
        return None
    yaml_safe = YAML(typ="safe")
    try:
        data = yaml_safe.load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — ruamel raises many internal exception types
        return None
    if not isinstance(data, dict):
        return None
    return cast("dict[str, object]", data)


def _config_search_paths() -> list[Path]:
    """Return ordered config.yaml search paths.

    Tries project-level ``.dh/config.yaml`` first, then user home ``~/.dh/config.yaml``.

    Returns:
        List of :class:`~pathlib.Path` objects to probe in priority order.
    """
    paths: list[Path] = []

    # Project-level config — resolve via dh_paths when available.
    with contextlib.suppress(ImportError, FileNotFoundError, RuntimeError):
        import dh_paths as _dh_paths  # noqa: PLC0415

        project_root = _dh_paths.git_project_root()
        project_dh_dir = _dh_paths.project_dh_dir(project_root)
        paths.append(project_dh_dir / "config.yaml")

    # User-level config fallback.
    dh_state_home = os.environ.get("DH_STATE_HOME", "")
    if dh_state_home:
        paths.append(Path(dh_state_home) / "config.yaml")
    else:
        paths.append(Path.home() / ".dh" / "config.yaml")

    return paths
