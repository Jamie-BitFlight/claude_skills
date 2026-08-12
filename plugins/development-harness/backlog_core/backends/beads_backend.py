"""BeadsBackend — structural implementation of the WorkItemBackend Protocol.

Routes all supported backlog operations to the ``bd`` (beads) CLI via
:class:`~backlog_core.backends.bd_runner.BdRunner`.

BeadsBackend implements :class:`~backlog_core.backend_types.WorkItemBackend`
only — it does not implement :class:`~backlog_core.backend_types.GitHubExtras`
or :class:`~backlog_core.backend_types.BranchBackend`.  Callers gate
GitHub-specific operations on ``isinstance(backend, GitHubExtras)`` and branch
operations on the ``supports_branches`` capability flag.

ADR-001: GitHub-specific operations (GraphQL, integration branches, task
issues, milestone/project management) are not implemented for beads and have
no stubs here.  These methods require a PyGithub ``Repository`` transport that
has no beads equivalent.

ADR-002: Methods whose Protocol signature uses GitHub issue *numbers* (``int``)
as keys cannot be implemented for beads because beads IDs are strings with no
meaningful integer representation.  Affected methods raise
:exc:`NotImplementedError` with a reference to ADR-002:

- :meth:`BeadsBackend.create_issue_for_item` — takes ``Repository``, returns
  ``int | None``; use the beads-native shadow method
  :meth:`BeadsBackend.create_beads_issue_for_item` (returns a string nanoid)
  instead.
- :meth:`BeadsBackend.fetch_open_issues_by_title` — returns ``dict[str, int]``
  (title → issue number); use the beads-native shadow method
  :meth:`BeadsBackend.fetch_open_issues_by_title_str` instead.
- :meth:`BeadsBackend.fetch_github_issue_body` — takes ``Repository`` + ``int``.
  No beads equivalent.
- :meth:`BeadsBackend.batch_fetch_statuses` — returns ``dict[int, IssueStatus]``
  (issue number → status); use :meth:`BeadsBackend.fetch_item_status` for
  individual beads issue status lookups instead.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Literal, Protocol

from pydantic import ValidationError

from backlog_core import github_sync, rendering as _rendering
from backlog_core.backends.bd_runner import (
    BdInvocationError,
    BdJsonDecodeError,
    BdNotInstalledError,
    BdRunner,
    JsonValue,
)
from backlog_core.backends.beads_models import (
    BeadsIssueType,
    BeadsStatus,
    parse_issue,
    parse_issue_list,
    parse_show_issue,
)
from backlog_core.models import (
    BackendAvailability,
    BackendStatus,
    BacklogItem,
    ContentConflictError,
    ContentKind,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    GroomedData,
    IssueLocalFields,
    IssueStatus,
    MilestoneInfo,
    PullRequestRef,
    ViewItemResult,
)

if TYPE_CHECKING:
    from github.Repository import Repository

    from backlog_core.backend_types import IssueNode, MilestoneNode
    from backlog_core.models import Output

__all__ = ["BeadsBackend"]

_log = logging.getLogger(__name__)
_CONTENT_KEY_PREFIX: Final[str] = "dh.content."


class _BdRunnerLike(Protocol):
    def run_json(self, argv: Sequence[str]) -> JsonValue: ...

    def run_text(self, argv: Sequence[str]) -> str: ...

    def is_available(self) -> bool: ...


# ---------------------------------------------------------------------------
# Type and priority mapping helpers
# ---------------------------------------------------------------------------

#: Mapping from backlog item_type (case-insensitive) to bd issue type string.
_ITEM_TYPE_TO_BEADS: dict[str, str] = {
    "feature": BeadsIssueType.FEATURE,
    "bug": BeadsIssueType.BUG,
    "task": BeadsIssueType.TASK,
    "epic": BeadsIssueType.EPIC,
    "chore": BeadsIssueType.CHORE,
    "decision": BeadsIssueType.DECISION,
    "spike": BeadsIssueType.SPIKE,
    "story": BeadsIssueType.STORY,
    "milestone": BeadsIssueType.MILESTONE,
}


def _beads_type_for_item_type(item_type: str) -> str:
    """Return the bd issue type string for a backlog item_type.

    Falls back to ``"task"`` for unrecognised types.

    Args:
        item_type: BacklogItem item_type string (e.g. ``"Feature"``, ``"Bug"``).

    Returns:
        Beads issue type string safe to pass to ``bd create --type``.
    """
    return _ITEM_TYPE_TO_BEADS.get(item_type.lower(), BeadsIssueType.TASK)


def _beads_priority_for_item_priority(priority: str) -> str:
    """Return the bd priority digit string for a backlog priority.

    Accepts ``"P0"``-``"P4"`` and bare ``"0"``-``"4"`` (case-insensitive).
    Falls back to ``"2"`` for unrecognised values.

    Args:
        priority: BacklogItem priority string (e.g. ``"P2"``, ``"high"``).

    Returns:
        Single-digit priority string safe to pass to ``bd create --priority``.
    """
    normalised = priority.upper().lstrip("P")
    if normalised in {"0", "1", "2", "3", "4"}:
        return normalised
    return "2"


_ADR_001_NOTE = (
    "BeadsBackend does not implement GitHub-specific operations. See ADR-001 in the project architecture documentation."
)

_ADR_002_NOTE = (
    "fetch_open_issues_by_title returns dict[str, int] but beads issue IDs are strings. "
    "Use fetch_open_issues_by_title_str() for beads-native title lookup. See ADR-002."
)

_ADR_002_BATCH_NOTE = (
    "batch_fetch_statuses returns dict[int, IssueStatus] but beads issue IDs are strings "
    "with no meaningful integer representation. "
    "Use fetch_item_status() for individual beads issue status lookups. See ADR-002."
)


class BeadsBackend:
    """Routes backlog operations to the ``bd`` CLI subprocess.

    Implements the :class:`~backlog_core.backend_types.WorkItemBackend` Protocol
    structurally.  Does not implement ``GitHubExtras`` or ``BranchBackend``.

    Capability flags:

    - ``supports_batch_status_fetch = False`` — beads issue IDs are strings;
      :meth:`batch_fetch_statuses` raises :exc:`NotImplementedError` (ADR-002).
      Callers must check this flag before invoking the method.
    - ``supports_batch_issue_update = False`` — beads does not expose GraphQL.
    - ``issue_id_type = "string"`` — beads issues are identified by string
      nanoids (e.g. ``"bd-a3f8"``).  When ``item.issue`` is absent, the item
      title is used as the selector.  The list command skips live batch-status
      fetch and relies on the local YAML cache instead.
    - ``supports_branches = False`` — beads does not manage git branches;
      callers must check this flag before invoking ``BranchBackend`` methods.

    Parameters
    ----------
    runner:
        Optional :class:`~backlog_core.backends.bd_runner.BdRunner` instance.
        When ``None``, a default :class:`~backlog_core.backends.bd_runner.BdRunner`
        is constructed.  The default runner is filesystem-free at construction
        time; the ``bd`` binary is resolved lazily on the first call.
    """

    supports_batch_status_fetch: bool = False
    supports_batch_issue_update: bool = False
    issue_id_type: Literal["integer", "string"] = "string"
    supports_branches: bool = False

    def __init__(self, runner: _BdRunnerLike | None = None) -> None:
        """Store the runner; do not touch the filesystem or spawn processes."""
        self._runner: _BdRunnerLike = runner if runner is not None else BdRunner()

    def list_content(self, query: ContentQuery) -> list[ContentRecord]:
        """Return the requested bounded page from the native Beads KV store."""
        try:
            raw = self._runner.run_json(["kv", "list"])
        except (BdNotInstalledError, BdInvocationError, BdJsonDecodeError) as exc:
            raise ContentUnavailableError("Beads content store is unavailable") from exc
        if not isinstance(raw, dict):
            raise ContentUnavailableError("Beads content store returned an invalid listing")
        records: list[ContentRecord] = []
        for key, value in raw.items():
            if not key.startswith(_CONTENT_KEY_PREFIX):
                continue
            if not isinstance(value, str):
                raise ContentUnavailableError("Beads content store returned an invalid record")
            try:
                record = ContentRecord.model_validate_json(value)
            except ValidationError as exc:
                raise ContentUnavailableError("Beads content store returned an invalid record") from exc
            if (
                record.reference.kind == query.kind
                and record.owner_reference == query.owner_reference
                and query.search.casefold() in record.reference.name.casefold()
            ):
                records.append(record)
        records.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return records[query.offset : query.offset + query.limit]

    def get_content(self, reference: ContentRef) -> ContentRecord:
        """Return one Beads KV content record by logical identity."""
        record = self._find_content(reference)
        if record is None:
            raise ContentUnavailableError(f"Content is unavailable: {reference.model_dump_json()}")
        return record

    def put_content(self, request: ContentWrite) -> ContentRecord:
        """Create or replace one record in the native Beads KV store."""
        current = self._find_content(request.reference)
        current_revision = current.revision if current is not None else ""
        if request.expected_revision and request.expected_revision != current_revision:
            raise ContentConflictError("Content revision no longer matches")
        owner_reference = request.reference.namespace
        if request.reference.kind == ContentKind.PLAN:
            owner_reference = (
                request.owner_reference
                if request.owner_reference is not None
                else current.owner_reference
                if current is not None
                else ""
            )
        record = ContentRecord(
            reference=request.reference,
            owner_reference=owner_reference,
            content=request.content,
            revision=uuid.uuid4().hex,
        )
        try:
            self._runner.run_text([
                "kv",
                "set",
                self._content_key(request.reference),
                json.dumps(record.model_dump(mode="json"), separators=(",", ":")),
            ])
        except (BdNotInstalledError, BdInvocationError, BdJsonDecodeError) as exc:
            raise ContentUnavailableError("Beads content store is unavailable") from exc
        return record

    def _find_content(self, reference: ContentRef) -> ContentRecord | None:
        try:
            raw = self._runner.run_json(["kv", "get", self._content_key(reference)])
        except BdInvocationError as exc:
            if exc.returncode != 1:
                raise ContentUnavailableError("Beads content store is unavailable") from exc
            try:
                raw = json.loads(exc.stdout)
            except json.JSONDecodeError as decode_error:
                raise ContentUnavailableError("Beads content store is unavailable") from decode_error
        except (BdNotInstalledError, BdJsonDecodeError) as exc:
            raise ContentUnavailableError("Beads content store is unavailable") from exc
        if not isinstance(raw, dict):
            raise ContentUnavailableError("Beads content store returned an invalid record")
        if raw.get("found") is False:
            return None
        value = raw.get("value")
        if not isinstance(value, str):
            raise ContentUnavailableError("Beads content store returned an invalid record")
        try:
            return ContentRecord.model_validate_json(value)
        except ValidationError as exc:
            raise ContentUnavailableError("Beads content store returned an invalid record") from exc

    @staticmethod
    def _content_key(reference: ContentRef) -> str:
        digest = hashlib.sha256(reference.model_dump_json().encode()).hexdigest()
        return f"{_CONTENT_KEY_PREFIX}{digest}"

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def try_get_github(self, repo: str = "") -> Repository | None:
        """Return None — beads does not use PyGithub Repository."""
        return None  # type: ignore[return-value]

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Check whether the ``bd`` binary is reachable.

        Returns a :class:`~backlog_core.models.BackendStatus` with
        ``name="Beads"`` and :attr:`~backlog_core.models.BackendAvailability.REACHABLE`
        when ``bd`` is on ``PATH``, or
        :attr:`~backlog_core.models.BackendAvailability.ERROR` otherwise.

        Args:
            repo: Ignored for the beads backend.

        Returns:
            BackendStatus describing availability.
        """
        if self._runner.is_available():
            return BackendStatus(name="Beads", availability=BackendAvailability.REACHABLE)
        return BackendStatus(
            name="Beads",
            availability=BackendAvailability.ERROR,
            error="bd binary not found on PATH. Install beads: https://beads.sh/docs/install",
        )

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Raise NotImplementedError — beads does not use PyGithub Repository.

        The ``WorkItemBackend`` signature returns ``int | None`` (a GitHub issue
        number).  Beads IDs are string nanoids, so this method cannot satisfy
        the contract; use :meth:`create_beads_issue_for_item` instead.  See
        ADR-001 and ADR-002.
        """
        raise NotImplementedError(_ADR_001_NOTE)  # type: ignore[return]

    def create_beads_issue_for_item(self, item: BacklogItem, output: Output | None = None) -> str | None:
        """Create a beads issue via ``bd create`` and return the nanoid.

        Translates the BacklogItem fields to ``bd create`` flags and calls the
        ``bd`` CLI with ``--json`` to capture the created issue ID.  Returns the
        nanoid string (e.g. ``"bd-a3f8"``) on success, or ``None`` when ``bd``
        is unavailable or creation fails.

        Args:
            item: BacklogItem containing title, item_type, and priority.
            output: Optional Output collector for warning messages.

        Returns:
            Beads nanoid string (e.g. ``"bd-a3f8"``) on success, or ``None``
            when ``bd`` is unavailable or creation fails.
        """
        from backlog_core.models import Output  # ruff: ignore[import-outside-top-level]

        out = output or Output()
        bd_type = _beads_type_for_item_type(item.item_type or "task")
        bd_priority = _beads_priority_for_item_priority(item.priority or "P2")
        argv: list[str] = ["create", item.title, "--type", bd_type, "--priority", bd_priority]
        if item.description:
            argv.extend(["--description", item.description])
        try:
            raw = self._runner.run_json(argv)
            parsed = parse_issue(raw)
        except (BdNotInstalledError, BdInvocationError, BdJsonDecodeError) as exc:
            _log.debug("create_beads_issue_for_item: bd invocation failed: %s", exc)
            out.warn(f"  WARNING: bd create failed: {exc}")
            return None
        except ValidationError as exc:
            _log.debug("create_beads_issue_for_item: bd create output validation failed: %s", exc)
            out.warn(f"  WARNING: bd create output did not match expected schema: {exc}")
            return None
        else:
            if not parsed.id:
                out.warn("  WARNING: bd create returned an empty issue ID")
                return None
            return parsed.id

    def close_github_issue(
        self,
        issue_ref: str,
        reason: str,
        *,
        reference: str = "",
        comment: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Close a beads issue via ``bd close``.

        Args:
            issue_ref: Beads issue ID or selector string.
            reason: Human-readable reason forwarded as ``--reason``.
            reference: Ignored for the beads backend.
            comment: Ignored for the beads backend.
            repo: Ignored for the beads backend.
            output: Ignored for the beads backend.
        """
        argv = ["close", issue_ref]
        if reason:
            argv.extend(["--reason", reason])
        self._runner.run_text(argv)

    def resolve_github_issue(
        self,
        issue_ref: str,
        *,
        summary: str,
        method: str = "",
        notes: str = "",
        follow_ups: str = "",
        findings: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Resolve a beads issue via ``bd close --reason``.

        Only ``summary`` is forwarded — beads does not support structured
        resolution fields (method, findings, follow_ups).

        Args:
            issue_ref: Beads issue ID or selector string.
            summary: Resolution summary forwarded as ``--reason``.
            method: Ignored for the beads backend.
            notes: Ignored for the beads backend.
            follow_ups: Ignored for the beads backend.
            findings: Ignored for the beads backend.
            repo: Ignored for the beads backend.
            output: Ignored for the beads backend.
        """
        argv = ["close", issue_ref]
        if summary:
            argv.extend(["--reason", summary])
        self._runner.run_text(argv)

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Raise NotImplementedError — beads IDs are strings; see ADR-002.

        Use :meth:`fetch_open_issues_by_title_str` for beads-native lookup.

        Args:
            repo: Ignored.
        """
        raise NotImplementedError(_ADR_002_NOTE)

    def fetch_open_issues_by_title_str(self) -> dict[str, str]:
        """Return a mapping of open beads issue titles to beads IDs.

        This is the beads-native equivalent of
        :meth:`fetch_open_issues_by_title`.  It returns ``dict[str, str]``
        because beads issue IDs are strings (e.g. ``"bd-a3f8"``).

        Returns:
            Dict mapping issue title to beads ID string for all open issues.

        Raises:
            BdNotInstalledError: When ``bd`` is not on ``PATH``.
            BdInvocationError: When ``bd list`` exits non-zero.
            pydantic.ValidationError: When the JSON response does not match
                the expected schema.
        """
        raw = self._runner.run_json(["list", "--status=open"])
        issues = parse_issue_list(raw)
        return {issue.title: issue.id for issue in issues}

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Raise NotImplementedError — beads does not use PyGithub Repository.

        No beads equivalent exists; the ``WorkItemBackend`` signature takes
        ``Repository`` + ``int`` issue number, which beads cannot satisfy.
        See ADR-001.
        """
        raise NotImplementedError(_ADR_001_NOTE)

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Return an empty list — beads does not expose pull request data.

        Args:
            issue_num: Ignored.
            repo: Ignored.

        Returns:
            Always an empty list.
        """
        return []

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Raise NotImplementedError — beads IDs are strings; see ADR-002.

        The Protocol signature uses ``int`` keys (GitHub issue numbers).
        Beads issue IDs are strings with no meaningful integer representation,
        so this operation cannot be implemented.  Use :meth:`fetch_item_status`
        for individual beads issue status lookups instead.

        Args:
            items: Ignored.
            repo: Ignored.

        Raises:
            NotImplementedError: Always — this operation is not supported for
                the beads backend.
        """
        raise NotImplementedError(_ADR_002_BATCH_NOTE)  # type: ignore[return]

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Return the current status string for a beads issue.

        Uses ``item.issue`` as the beads ID.  Falls back to
        ``item.title`` when ``item.issue`` is absent.

        Args:
            item: BacklogItem whose ``issue`` field holds the beads ID.
            repo: Ignored for the beads backend.
            output: Ignored for the beads backend.

        Returns:
            Status string from the beads issue (e.g. ``"open"``, ``"closed"``).

        Raises:
            BdNotInstalledError: When ``bd`` is not on ``PATH``.
            BdInvocationError: When ``bd show`` exits non-zero.
            pydantic.ValidationError: When the JSON response does not match the expected schema.
        """
        issue_ref = item.issue or item.title
        raw = self._runner.run_json(["show", issue_ref])
        parsed = parse_show_issue(raw)
        return str(parsed.status)

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult with live data from beads via ``bd show``.

        Populates ``result.status``, ``result.state``, ``result.title``,
        ``result.source``, ``result.issue`` (the beads nanoid), and
        ``result.body`` (from the issue description and notes) from the
        beads issue.  Returns ``False`` when the issue cannot be found or
        the data is malformed.

        Args:
            result: ViewItemResult to enrich in place.
            issue_num: Beads issue ID string (e.g. ``"bd-a3f8"``).
            repo: Ignored for the beads backend.

        Returns:
            True if enrichment succeeded, False otherwise.
        """
        try:
            raw = self._runner.run_json(["show", issue_num])
            parsed = parse_show_issue(raw)
        except (BdNotInstalledError, BdInvocationError) as exc:
            _log.debug("view_enrich_from_github: bd invocation failed for %r: %s", issue_num, exc)
            return False
        except ValidationError as exc:
            _log.debug("view_enrich_from_github: validation error for %r: %s", issue_num, exc)
            return False
        except ValueError as exc:
            _log.debug("view_enrich_from_github: bd show returned empty result for %r: %s", issue_num, exc)
            return False

        result.status = str(parsed.status)
        result.state = "closed" if parsed.status == BeadsStatus.CLOSED else "open"
        result.source = "beads"
        result.issue = parsed.id
        if parsed.title:
            result.title = parsed.title
        if parsed.description:
            result.body = parsed.description
        if parsed.notes:
            result.body = f"{result.body}\n\n## Notes\n\n{parsed.notes}" if result.body else parsed.notes
        return True

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert an IssueNode TypedDict to an IssueLocalFields model.

        Translates the GitHub-shaped IssueNode (produced by GraphQL callers)
        to the generic IssueLocalFields boundary model.

        Args:
            issue: IssueNode TypedDict with issue fields.

        Returns:
            IssueLocalFields populated from the IssueNode fields.
        """
        labels: list[str] = [lbl["name"] for lbl in issue.get("labels", [])]
        milestone_node: MilestoneNode | None = issue.get("milestone")
        milestone_title = milestone_node["title"] if milestone_node else ""
        milestone_info = MilestoneInfo(title=milestone_title)
        assignees: list[str] = [a["login"] for a in issue.get("assignees", [])]
        state_str = issue.get("state", "OPEN")
        status = "closed" if state_str.upper() == "CLOSED" else "open"

        return IssueLocalFields(
            title=issue.get("title", ""),
            body=issue.get("body", ""),
            status=status,
            updated_at=issue.get("updatedAt", ""),
            milestone=milestone_title,
            milestone_info=milestone_info,
            assignees=assignees,
            labels=labels,
        )

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Claim a beads issue via ``bd update --claim``.

        Args:
            item: BacklogItem whose ``issue`` field holds the beads ID.
            repo: Ignored for the beads backend.
            output: Ignored for the beads backend.
        """
        issue_ref = item.issue or item.title
        self._runner.run_text(["update", issue_ref, "--claim"])

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """No-op — beads has no dedicated verified lifecycle state.

        Args:
            item: Ignored.
            repo: Ignored.
            output: Ignored.
        """

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """No-op — beads has no dedicated groomed lifecycle state.

        Args:
            item: Ignored.
            repo: Ignored.
            output: Ignored.
        """

    # ------------------------------------------------------------------
    # Sync / serialisation
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Serialise a BacklogItem to markdown via github_sync.render_issue_body.

        Args:
            item: BacklogItem to serialise.
            original_body: Optional existing body to preserve non-managed sections.

        Returns:
            Markdown string suitable for use as an issue body.
        """
        return github_sync.render_issue_body(item, original_body)

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Deserialise a markdown issue body via github_sync.parse_issue_body.

        Args:
            body: Raw issue body markdown string.
            existing: Optional existing BacklogItem to merge parsed data into.

        Returns:
            Populated BacklogItem model.
        """
        return github_sync.parse_issue_body(body, existing)

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Merge two BacklogItems via github_sync.merge_item.

        Args:
            local: Local BacklogItem state.
            remote: Remote BacklogItem state.

        Returns:
            Merged BacklogItem with conflicts resolved.
        """
        return github_sync.merge_item(local, remote)

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert an unknown section key to a heading string.

        Args:
            key: Section key string (e.g. ``"my_section"``).

        Returns:
            Heading text string (e.g. ``"My Section"``).
        """
        return _rendering.unknown_key_to_heading(key)

    @property
    def section_heading(self) -> dict[str, str]:
        """Return the section key-to-heading mapping.

        Returns:
            Dict mapping section storage key to display heading string.
        """
        return _rendering.SECTION_HEADING

    def render_groomed_section(self, groomed: GroomedData) -> str:
        r"""Render a GroomedData to markdown via rendering.render_groomed_section.

        Args:
            groomed: GroomedData to render.

        Returns:
            Markdown string such as ``"## Groomed (2026-03-01)\\n\\n..."``.
        """
        return _rendering.render_groomed_section(groomed)

    def section_display_title(self, key: str, groomed_date: str = "") -> str:
        """Return the human-readable title for a section storage key.

        Args:
            key: Section storage key (e.g. ``"fact_check"``).
            groomed_date: Optional date string appended to the ``"groomed"`` title.

        Returns:
            Display title string (e.g. ``"Fact-Check"``).
        """
        return _rendering.section_display_title(key, groomed_date)
