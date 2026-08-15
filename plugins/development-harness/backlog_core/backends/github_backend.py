"""GitHubBackend — the composition root for the GitHub work-item provider.

This module owns two things and nothing else:

1. The GitHub API surface — thin delegations to ``gh_client``, ``github_sync``,
   ``github_branches``, and ``rendering``, plus the bounded aliased GraphQL query
   that resolves targeted issues.
2. Composition — wiring the collaborators that hold the provider's behaviour and
   delegating each Protocol-facing method to the collaborator that owns it:

   - :class:`_GitHubContentsStore` (``github_contents``) — the authoritative
     Contents API store.
   - :class:`_GitHubPlanPersistence` / :class:`_GitHubDispatchPersistence`
     (``github_content_stores``) — the legacy Gist-backed stores.
   - :class:`_GitHubContentMigration` / :class:`_GitHubContentCache`
     (``github_content_migration``) — content resolution across those stores,
     and the offline/replay policy wrapped around it.
   - :class:`_GitHubWorkItemSync` / :class:`_GitHubReconciliation`
     (``github_work_items``) — provider snapshot and patch translation, and the
     reconciliation cycle driven against the provider-private cache.

The collaborators reach back through narrow Protocols this class satisfies
structurally, so every GitHub call and every injected store stays substitutable
on the backend instance itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import dh_paths as _dh_paths

from backlog_core import gh_client, github_branches, github_sync, rendering as _rendering
from backlog_core.artifact_provider import ArtifactBackend, GitHubGistArtifactProvider
from backlog_core.backends.github_content_migration import (
    _GitHubContentCache,
    _GitHubContentMigration,
    _PlanPersistence,
)
from backlog_core.backends.github_content_stores import (
    _content_revision as _compute_content_revision,
    _ContentPersistence,
    _GitHubDispatchPersistence,
    _GitHubPlanPersistence,
)
from backlog_core.backends.github_contents import _GitHubContentsStore
from backlog_core.backends.github_work_items import _TARGET_BATCH_SIZE, _GitHubReconciliation, _GitHubWorkItemSync
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
    PatchResult,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    parse_issue_number,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

    from github.Repository import Repository

    from backlog_core.backend_types import IssueCommentNode, IssueNode, MilestoneFullNode
    from backlog_core.file_cache_state import _PendingWorkItemMutation
    from backlog_core.models import (
        BackendStatus,
        BranchInfo,
        GroomedData,
        IssueLocalFields,
        IssueStatus,
        MergeResult,
        Output,
        PullRequestRef,
        SamTask,
        ViewItemResult,
    )
    from backlog_core.reconciliation import LogicalCacheRecord

__all__ = ["GitHubBackend"]


class GitHubBackend:
    """Backend implementation composing the GitHub provider collaborators.

    Every method is either a delegation to a module-level GitHub function or a
    delegation to the collaborator that owns the behaviour.  The constructor
    accepts an optional default repo string that is used when callers pass an
    empty ``repo`` argument.

    Capability flags:

    - ``supports_batch_status_fetch = True`` — GitHub Issues use integer IDs;
      :meth:`batch_fetch_statuses` is fully implemented.
    - ``supports_batch_issue_update = True`` — :meth:`_update_issues_graphql_batch`
      is implemented via aliased GraphQL mutations.
    - ``issue_id_type = "integer"`` — GitHub Issues are identified by integer
      issue numbers.
    """

    supports_batch_status_fetch: bool = True
    supports_batch_issue_update: bool = True
    issue_id_type: Literal["integer", "string"] = "integer"
    supports_branches: bool = True

    def __init__(
        self,
        repo: str = "",
        *,
        cache: FileCache | None = None,
        artifact_provider: ArtifactBackend | None = None,
        plan_persistence: _PlanPersistence | None = None,
        contents: _ContentPersistence | None = None,
    ) -> None:
        """Initialise with an optional default repo string.

        Args:
            repo: Optional ``owner/name`` string used as default for repo-optional methods.
            cache: Provider-private durable cache, injectable for isolated callers.
            artifact_provider: Existing GitHub Gist persistence adapter.
            plan_persistence: Existing GitHub plan-index and Gist composition.
            contents: GitHub Contents persistence, injectable for isolated callers.
        """
        self._repo = repo
        self._cache = cache or FileCache(_dh_paths.state_root() / "github-cache")
        self._artifact_provider = artifact_provider or GitHubGistArtifactProvider(repo=repo)
        self._plan_persistence = plan_persistence or _GitHubPlanPersistence(self._artifact_provider)
        self._dispatch_persistence = _GitHubDispatchPersistence(self._artifact_provider)
        self._contents = contents or _GitHubContentsStore(self.get_github)
        self._content_migration = _GitHubContentMigration(
            contents=lambda: self._contents,
            plan_persistence=self._plan_persistence,
            dispatch_persistence=self._dispatch_persistence,
            artifact_provider=self._artifact_provider,
        )
        self._content_cache = _GitHubContentCache(self._cache, self)
        self._work_items = _GitHubWorkItemSync(self, lambda: self._contents)
        self._reconciliation = _GitHubReconciliation(self._cache, self)

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Return a PyGithub Repository (raises GitHubUnavailableError on failure).

        Returns:
            Authenticated PyGithub Repository object.
        """
        return gh_client.get_github(repo or self._repo, timeout)

    def try_get_github(self, repo: str = "") -> Repository | None:
        """Return a PyGithub Repository or None if unavailable.

        Returns:
            Authenticated PyGithub Repository, or None on any failure.
        """
        return gh_client.try_get_github(repo or self._repo)

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Check backend availability and return a status report.

        Returns:
            BackendStatus with availability enum, last_check timestamp, and message.
        """
        return gh_client.probe_backend_status(repo or self._repo)

    # ------------------------------------------------------------------
    # Work items — delegated to the reconciliation collaborator
    # ------------------------------------------------------------------

    def list_work_items(self) -> list[BacklogItem]:
        """List work items from the provider-private cache.

        Returns:
            Persisted work items.
        """
        return self._reconciliation.list_work_items()

    def get_work_item(self, reference: str) -> BacklogItem:
        """Get a cached work item by stable reference.

        Returns:
            The matching work item.
        """
        return self._reconciliation.get_work_item(reference)

    def put_work_item(self, item: BacklogItem) -> None:
        """Persist a work-item intent for provider reconciliation."""
        self._reconciliation.put_work_item(item)

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Reconcile provider state through the pure engine and private cache.

        Returns:
            Completed reconciliation counts with changed logical references.
        """
        return self._reconciliation.reconcile(request)

    def _load_reconcile_records(
        self, pending_work_items: Sequence[_PendingWorkItemMutation] | None = None
    ) -> list[LogicalCacheRecord]:
        """Merge cached work-item snapshots with queued mutations.

        Returns:
            One logical cache record per work-item reference.
        """
        return self._reconciliation.load_records(pending_work_items)

    def _fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Fetch one normalized bounded GitHub snapshot for reconciliation.

        Returns:
            Provider snapshot whose pagination remains private to this adapter.
        """
        return self._work_items.fetch_snapshot(request)

    def _apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        """Apply optimistic GitHub body patches and return one outcome per patch.

        Returns:
            Patch results indexed by the stable provider reference.
        """
        return self._work_items.apply_patches(patches)

    # ------------------------------------------------------------------
    # GraphQL utilities
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Execute a raw GraphQL query/mutation against the backend.

        Returns:
            Parsed JSON response dict.
        """
        return gh_client._graphql_request(repo, query, variables)

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Resolve label names to backend node IDs.

        Returns:
            List of node ID strings corresponding to the given names.
        """
        return gh_client._resolve_labels_graphql(repo, repo_owner, repo_name, label_names)

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Fetch a single issue by number.

        Returns:
            IssueNode TypedDict with issue fields.
        """
        return gh_client._fetch_issue_graphql(repo, owner, repo_name, issue_number)

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
        """Fetch multiple issues with optional filters.

        Returns:
            List of IssueNode TypedDicts.
        """
        return gh_client._fetch_issues_graphql(repo, owner, repo_name, state, labels, milestone_number, first, since)

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
        """Update an issue's mutable fields via mutation."""
        gh_client._update_issue_graphql(
            repo, issue_node_id, state=state, body=body, title=title, label_ids=label_ids, milestone_id=milestone_id
        )

    def _update_issues_graphql_batch(self, repo: Repository, updates: list[tuple[str, str]]) -> None:
        """Update issue bodies in bulk using aliased GraphQL mutations."""
        gh_client._update_issues_graphql_batch(repo, updates)

    def _fetch_targeted_issues(
        self, repo: Repository, owner: str, repo_name: str, references: list[str]
    ) -> dict[str, IssueNode | None]:
        """Resolve issue references in bounded aliased GraphQL queries.

        Returns:
            A mapping of canonical references to issues, with ``None`` tombstones.
        """
        numbered_references: list[tuple[str, int]] = []
        seen: set[str] = set()
        for reference in references:
            number = parse_issue_number(reference)
            if number is None:
                raise BacklogError(f"Invalid GitHub issue reference: {reference!r}")
            canonical_reference = f"#{number}"
            if canonical_reference not in seen:
                seen.add(canonical_reference)
                numbered_references.append((canonical_reference, number))

        resolved: dict[str, IssueNode | None] = {}
        for offset in range(0, len(numbered_references), _TARGET_BATCH_SIZE):
            chunk = numbered_references[offset : offset + _TARGET_BATCH_SIZE]
            declarations = ", ".join(f"$number{index}: Int!" for index in range(len(chunk)))
            aliases = "\n".join(
                "      "
                f"i{index}: issue(number: $number{index}) {{ "
                "id number title state body createdAt updatedAt "
                "labels(first: 50) { nodes { name id } } "
                "milestone { id number title dueOn state } assignees(first: 10) { nodes { login } } }"
                for index in range(len(chunk))
            )
            query = (
                f"query TargetedIssues($owner: String!, $repo: String!, {declarations}) {{\n"
                f"  repository(owner: $owner, name: $repo) {{\n{aliases}\n  }}\n}}"
            )
            variables: dict[str, object] = {"owner": owner, "repo": repo_name}
            variables.update({f"number{index}": number for index, (_, number) in enumerate(chunk)})
            data = self._graphql_request(repo, query, variables)
            repository_data = data.get("repository")
            if not isinstance(repository_data, dict):
                raise BacklogError("GraphQL targeted issue response omitted repository data")
            for index, (reference, _) in enumerate(chunk):
                alias = f"i{index}"
                if alias not in repository_data:
                    raise BacklogError(f"GraphQL targeted issue response omitted {reference}")
                raw_issue = repository_data[alias]
                if raw_issue is None:
                    resolved[reference] = None
                elif isinstance(raw_issue, dict):
                    resolved[reference] = gh_client._parse_issue_node(raw_issue)
                else:
                    raise BacklogError(f"GraphQL targeted issue response was invalid for {reference}")
        return resolved

    # ------------------------------------------------------------------
    # Logical content — delegated to the content collaborators
    # ------------------------------------------------------------------

    def list_content(self, query: ContentQuery) -> list[ContentRecord]:
        """Return a bounded cache-backed discovery page for GitHub content.

        Returns:
            The requested page of content records.
        """
        return self._content_cache.list_content(query)

    def get_content(self, reference: ContentRef) -> ContentRecord:
        """Read authoritative GitHub content or an explicitly stale cached copy.

        Returns:
            The provider or cached logical content record.
        """
        return self._content_cache.get_content(reference)

    def put_content(self, request: ContentWrite) -> ContentRecord:
        """Write GitHub content, durably queueing it while GitHub is offline.

        Returns:
            The applied or pending logical content record.
        """
        return self._content_cache.put_content(request)

    def _replay_pending_content(self) -> None:
        """Replay durably queued content writes against GitHub."""
        self._content_cache.replay_pending()

    def _list_online_content(self, query: ContentQuery) -> list[ContentRecord]:
        """Enumerate authoritative content merged with the legacy stores.

        Returns:
            Every discoverable record, excluding provider-private work-item heads.
        """
        return self._content_migration.list_online(query)

    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord:
        """Read authoritative content, falling back to the legacy stores.

        Returns:
            The resolved content record.
        """
        return self._content_migration.read(reference)

    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        """Write content, migrating a legacy record into the Contents API when needed.

        Returns:
            The written content record.
        """
        return self._content_migration.write(request)

    @staticmethod
    def _content_revision(content: str) -> str:
        """Return the content-addressed revision for a logical content body.

        Returns:
            Hex SHA-256 digest of the UTF-8 encoded content.
        """
        return _compute_content_revision(content)

    # ------------------------------------------------------------------
    # Issue synchronisation
    # ------------------------------------------------------------------

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
    ) -> list[IssueNode]:
        """Bulk-fetch issues with optional progress callback.

        Returns:
            List of IssueNode TypedDicts.
        """
        return gh_client.sync_issues_graphql(
            repo,
            owner,
            repo_name,
            state=state,
            labels=labels,
            milestone_number=milestone_number,
            since=since,
            callback=callback,
        )

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Create a backend issue from a BacklogItem.

        Returns:
            Issue number on success, or None on failure / dry_run.
        """
        return gh_client.create_issue_for_item(repo, item, dry_run, output)

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
        """Close an issue with a reason comment."""
        gh_client.close_github_issue(
            issue_ref, reason, reference=reference, comment=comment, repo=repo or self._repo, output=output
        )

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
        """Resolve an issue with a structured resolution comment."""
        gh_client.resolve_github_issue(
            issue_ref,
            summary=summary,
            method=method,
            notes=notes,
            follow_ups=follow_ups,
            findings=findings,
            repo=repo or self._repo,
            output=output,
        )

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Return a mapping of open issue titles to issue numbers.

        Returns:
            Dict mapping issue title string to issue number int.
        """
        return gh_client.fetch_open_issues_by_title(repo)

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Fetch the raw body of an issue.

        Returns:
            Issue body markdown string, or None on failure.
        """
        return gh_client.fetch_github_issue_body(repo_obj, issue_num, output)

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Find open pull requests referencing a given issue.

        Returns:
            List of PullRequestRef models for each matching PR.
        """
        return gh_client.check_open_prs_for_issue(issue_num, repo or self._repo)

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Fetch the current status for multiple items in one operation.

        Returns:
            Dict mapping issue_number to IssueStatus model.
        """
        return gh_client.batch_fetch_statuses(items, repo or self._repo)

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Fetch the current status string for a single item.

        Returns:
            Status string (e.g. "open", "closed").
        """
        return gh_client.fetch_item_status(item, repo or self._repo, output)

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult with live data from the backend.

        Returns:
            True if enrichment succeeded, False if the issue was not found.
        """
        return gh_client.view_enrich_from_github(result, issue_num, repo or self._repo)

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert a raw IssueNode to a typed IssueLocalFields model.

        Returns:
            IssueLocalFields model with parsed metadata.
        """
        return gh_client.issue_to_local_fields(issue)

    # ------------------------------------------------------------------
    # Issue comments
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Add a comment to an issue.

        Returns:
            GraphQL node ID of the new comment.
        """
        return gh_client._add_comment_graphql(repo, issue_node_id, body)

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Fetch all comments on an issue.

        Returns:
            List of IssueCommentNode TypedDicts.
        """
        return gh_client._fetch_issue_comments_graphql(repo, owner, repo_name, issue_number)

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Fetch a single comment by its GraphQL node ID.

        Returns:
            IssueCommentNode TypedDict.
        """
        return gh_client._fetch_comment_by_id_graphql(repo, comment_node_id)

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Update an existing comment's body."""
        gh_client._update_issue_comment_graphql(repo, comment_node_id, body)

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to in-progress state on the backend."""
        gh_client.apply_status_in_progress(item, repo or self._repo, output)

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to verified state on the backend."""
        gh_client.apply_status_verified(item, repo or self._repo, output)

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to groomed state on the backend."""
        gh_client.apply_status_groomed(item, repo or self._repo, output)

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Write groomed content into a specific section of an issue body.

        Returns:
            True if the issue body was updated, False if no change was needed.
        """
        return gh_client.sync_groomed_to_github_issue(repo_obj, issue_num, groomed_content, section_name, output)

    # ------------------------------------------------------------------
    # Milestones and projects
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Fetch milestones from the backend.

        Returns:
            List of MilestoneFullNode TypedDicts.
        """
        return gh_client._fetch_milestones_graphql(repo, owner, repo_name, states)

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 list query string and variables.

        Returns:
            Tuple of (query_string, variables_dict).
        """
        return gh_client._projects_v2_list_query(owner, limit)

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 create mutation string and variables.

        Returns:
            Tuple of (mutation_string, variables_dict).
        """
        return gh_client._projects_v2_create_mutation(owner_id, title)

    # ------------------------------------------------------------------
    # Task issues
    # ------------------------------------------------------------------

    def create_task_issue(
        self,
        repo: Repository,
        parent_issue_number: int,
        task: SamTask,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        labels: list[str] | None = None,
        output: Output | None = None,
    ) -> IssueNode | None:
        """Create a child issue for a SAM task under a parent issue.

        Returns:
            IssueNode of the created issue, or None on failure.
        """
        return gh_client.create_task_issue(
            repo, parent_issue_number, task, description, acceptance_criteria, labels, output
        )

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Fetch all child task issues for a parent issue.

        Returns:
            List of IssueNode TypedDicts for child task issues.
        """
        return gh_client.get_task_issues(repo, parent_issue_number, output)

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Update the status label on a task issue.

        Returns:
            True if the status was updated, False if no change was needed.
        """
        return gh_client.update_task_status(repo, issue_number, new_status, output)

    # ------------------------------------------------------------------
    # Sync / serialisation
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Serialise a BacklogItem to backend issue body markdown.

        Returns:
            Markdown string suitable for use as an issue body.
        """
        return github_sync.render_issue_body(item, original_body)

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Deserialise a backend issue body into a BacklogItem.

        Returns:
            Populated BacklogItem model.
        """
        return github_sync.parse_issue_body(body, existing)

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Merge a local BacklogItem with a remote version, resolving conflicts.

        Returns:
            Merged BacklogItem with conflicts resolved.
        """
        return github_sync.merge_item(local, remote)

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert an unknown section key to a markdown heading string.

        Delegates to :func:`backlog_core.rendering.unknown_key_to_heading` so
        that all backends share a single canonical implementation.

        Returns:
            Heading text string (e.g. ``"My Section"``).
        """
        return _rendering.unknown_key_to_heading(key)

    @property
    def section_heading(self) -> dict[str, str]:
        """Return the mapping of section key to display heading.

        Returns:
            Dict mapping section storage key to display heading string.
        """
        return _rendering.SECTION_HEADING

    def render_groomed_section(self, groomed: GroomedData) -> str:
        """Render a GroomedData as ``## Groomed ({date})`` with subsection children.

        Args:
            groomed: GroomedData to render.

        Returns:
            Rendered section string (no trailing newline).
        """
        return _rendering.render_groomed_section(groomed)

    def section_display_title(self, key: str, groomed_date: str = "") -> str:
        """Return the human-readable title for a section storage key.

        Args:
            key: Section storage key (e.g. ``"fact_check"``).
            groomed_date: Optional date string for the ``"groomed"`` key.

        Returns:
            Display title string (e.g. ``"Fact-Check"``).
        """
        return _rendering.section_display_title(key, groomed_date)

    # ------------------------------------------------------------------
    # Integration branches
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
        """Create an integration branch for a milestone.

        Returns:
            BranchInfo TypedDict describing the created branch.
        """
        return github_branches.create_integration_branch(
            milestone_number, slug, base_branch=base_branch, repo=repo or self._repo, output=output
        )

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Get the current status of an integration branch.

        Returns:
            BranchInfo TypedDict, or None if the branch does not exist.
        """
        return github_branches.get_integration_branch_status(branch_name, repo=repo or self._repo, output=output)

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Merge an integration branch into a base branch.

        Returns:
            MergeResult TypedDict with merge outcome.
        """
        return github_branches.merge_integration_branch(
            head_branch, base_branch, commit_message, repo=repo or self._repo, output=output
        )

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Delete an integration branch.

        Returns:
            True if the branch was deleted, False if it did not exist.
        """
        return github_branches.delete_integration_branch(branch_name, repo=repo or self._repo, output=output)

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """List all integration branches in the repository.

        Returns:
            List of BranchInfo TypedDicts for all integration branches.
        """
        return github_branches.list_integration_branches(repo=repo or self._repo, output=output)
