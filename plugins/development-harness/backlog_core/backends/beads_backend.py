"""BeadsBackend — full implementation of the BacklogBackend Protocol.

Routes all supported backlog operations to the ``bd`` (beads) CLI via
:class:`~backlog_core.backends.bd_runner.BdRunner`.

ADR-001: GitHub-specific operations (GraphQL, integration branches, task
issues, milestone/project management) raise :exc:`NotImplementedError` with a
reference to ADR-001.  These methods require a PyGithub ``Repository`` transport
that has no beads equivalent.

ADR-002: Methods whose Protocol signature uses GitHub issue *numbers* (``int``)
as keys cannot be implemented for beads because beads IDs are strings with no
meaningful integer representation.  Affected methods raise
:exc:`NotImplementedError` with a reference to ADR-002:

- :meth:`BeadsBackend.fetch_open_issues_by_title` — returns ``dict[str, int]``
  (title → issue number); use the beads-native shadow method
  :meth:`BeadsBackend.fetch_open_issues_by_title_str` instead.
- :meth:`BeadsBackend.batch_fetch_statuses` — returns ``dict[int, IssueStatus]``
  (issue number → status); use :meth:`BeadsBackend.fetch_item_status` for
  individual beads issue status lookups instead.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from backlog_core import github_sync, rendering as _rendering
from backlog_core.backends.bd_runner import BdInvocationError, BdNotInstalledError, BdRunner
from backlog_core.backends.beads_models import BeadsStatus, parse_issue, parse_issue_list
from backlog_core.models import (
    BackendAvailability,
    BackendStatus,
    BacklogItem,
    BranchInfo,
    GroomedData,
    IssueLocalFields,
    IssueStatus,
    MergeResult,
    MilestoneInfo,
    PullRequestRef,
    ViewItemResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from github.Repository import Repository

    from backlog_core.backend_protocol import IssueCommentNode, IssueNode, MilestoneFullNode, MilestoneNode
    from backlog_core.models import Output, SamTask

__all__ = ["BeadsBackend"]

_log = logging.getLogger(__name__)

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

    Parameters
    ----------
    runner:
        Optional :class:`~backlog_core.backends.bd_runner.BdRunner` instance.
        When ``None``, a default :class:`~backlog_core.backends.bd_runner.BdRunner`
        is constructed.  The default runner is filesystem-free at construction
        time; the ``bd`` binary is resolved lazily on the first call.
    """

    def __init__(self, runner: BdRunner | None = None) -> None:
        """Store the runner; do not touch the filesystem or spawn processes."""
        self._runner: BdRunner = runner if runner is not None else BdRunner()

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)  # type: ignore[return]

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
    # GraphQL utilities — ADR-001
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _fetch_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        first: int = 100,
        since: str | None = None,
    ) -> list[IssueNode]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _update_issue_graphql(
        self,
        repo: Repository,
        issue_node_id: str,
        *,
        state: str | None = None,
        body: str | None = None,
        title: str | None = None,
        label_ids: list[str] | None = None,
        milestone_id: str | None = None,
    ) -> None:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def sync_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        *,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        since: datetime | None = None,
        callback: Callable[[IssueNode], None] | None = None,
        track_timestamp: bool = False,
    ) -> list[IssueNode]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)

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
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
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
        parsed = parse_issue(raw)
        return str(parsed.status)

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult with live data from beads via ``bd show``.

        Populates ``result.status``, ``result.state``, ``result.title``,
        and ``result.source`` from the beads issue.  Returns ``False`` when the
        issue cannot be found or the data is malformed.

        Args:
            result: ViewItemResult to enrich in place.
            issue_num: Beads issue ID string (e.g. ``"bd-a3f8"``).
            repo: Ignored for the beads backend.

        Returns:
            True if enrichment succeeded, False otherwise.
        """
        try:
            raw = self._runner.run_json(["show", issue_num])
            parsed = parse_issue(raw)
        except (BdNotInstalledError, BdInvocationError) as exc:
            _log.debug("view_enrich_from_github: bd invocation failed for %r: %s", issue_num, exc)
            return False
        except ValidationError as exc:
            _log.debug("view_enrich_from_github: validation error for %r: %s", issue_num, exc)
            return False

        result.status = str(parsed.status)
        result.state = "closed" if parsed.status == BeadsStatus.CLOSED else "open"
        result.source = "beads"
        if parsed.title:
            result.title = parsed.title
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
    # Issue comments — ADR-001
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

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

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)

    # ------------------------------------------------------------------
    # Milestones and projects — ADR-001
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Raise NotImplementedError — beads does not expose GraphQL."""
        raise NotImplementedError(_ADR_001_NOTE)

    # ------------------------------------------------------------------
    # Task issues — ADR-001
    # ------------------------------------------------------------------

    def create_task_issue(
        self,
        repo: Repository,
        parent_issue_number: int | str,
        task: SamTask,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        labels: list[str] | None = None,
        output: Output | None = None,
    ) -> IssueNode | None:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Raise NotImplementedError — beads does not use PyGithub Repository."""
        raise NotImplementedError(_ADR_001_NOTE)

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

    # ------------------------------------------------------------------
    # Integration branches — ADR-001
    # ------------------------------------------------------------------

    def create_integration_branch(
        self,
        milestone_number: int,
        slug: str,
        *,
        base_branch: str = "main",
        repo: str = "",
        output: Output | None = None,
    ) -> BranchInfo:
        """Raise NotImplementedError — beads does not manage git branches."""
        raise NotImplementedError(_ADR_001_NOTE)

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Raise NotImplementedError — beads does not manage git branches."""
        raise NotImplementedError(_ADR_001_NOTE)

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Raise NotImplementedError — beads does not manage git branches."""
        raise NotImplementedError(_ADR_001_NOTE)

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Raise NotImplementedError — beads does not manage git branches."""
        raise NotImplementedError(_ADR_001_NOTE)

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """Raise NotImplementedError — beads does not manage git branches."""
        raise NotImplementedError(_ADR_001_NOTE)
