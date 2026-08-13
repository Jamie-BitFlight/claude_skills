"""GitHubBackend — concrete backend delegating to gh_client, github_sync, github_branches.

This module provides a thin wrapper class that implements the backlog
backend Protocols (WorkItemBackend, GitHubExtras, BranchBackend) by
delegating every method to the corresponding module-level function in
gh_client, github_sync, or github_branches.  No business logic lives here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, Protocol, assert_never, runtime_checkable

import dh_paths as _dh_paths
from sam_schema.core.artifact_registry_client import (
    ArtifactRegistryClient,
    PlanContentUnavailableError,
    PlanIndexUnavailableError,
)
from sam_schema.core.exceptions import ArtifactWriteError, PlanIndexError
from sam_schema.core.plan_id_index import PlanIndexEntry, create_plan_id_index

from backlog_core import gh_client, github_branches, github_sync, rendering as _rendering
from backlog_core.artifact_provider import ArtifactBackend, GitHubGistArtifactProvider
from backlog_core.file_cache import FileCache, ReplayAcknowledgement, _ProviderSnapshotCheckpoint
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    ContentConflictError,
    ContentKind,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    UnsupportedCapabilityError,
    parse_issue_number,
)
from backlog_core.reconciliation import (
    ActionResult,
    LogicalCacheRecord,
    ReconcileExecution,
    ReconcileOutcome,
    finalize_reconciliation,
    reconcile_backlog,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from github.Repository import Repository

    from backlog_core.backend_types import IssueCommentNode, IssueNode, MilestoneFullNode
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

__all__ = ["GitHubBackend"]


class _PlanPersistence(Protocol):
    def list(self, query: ContentQuery) -> Sequence[ContentRecord]: ...
    def get(self, reference: ContentRef) -> ContentRecord: ...
    def put(self, request: ContentWrite) -> ContentRecord: ...


@runtime_checkable
class _RemoteArtifactContentLister(Protocol):
    def list_artifact_content_from_remote(
        self, item_id: int, artifact_type: str, path_prefix: str
    ) -> dict[str, str]: ...


class _GitHubPlanPersistence:
    def __init__(self, provider: ArtifactBackend) -> None:
        client = ArtifactRegistryClient(provider)
        self._index = create_plan_id_index(client)
        self._sentinel_issue = self._index._sentinel_issue
        self._client = client
        self._provider = provider

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        entries = [
            entry
            for entry in self._entries()
            if (query.owner_reference is None or self._owner(entry) == query.owner_reference)
            and query.search.casefold() in f"{entry.plan_id} {entry.slug}".casefold()
        ]
        return [self._record(entry) for entry in entries[query.offset : query.offset + query.limit]]

    def get(self, reference: ContentRef) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.plan_id == reference.name), None)
        if entry is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return self._record(entry)

    def put(self, request: ContentWrite) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.plan_id == request.reference.name), None)
        current = self._record(entry) if entry is not None else None
        owner = (
            request.owner_reference
            if request.owner_reference is not None
            else current.owner_reference
            if current is not None
            else ""
        )
        if current is not None and current.content == request.content and current.owner_reference == owner:
            return current
        if request.expected_revision:
            raise ContentConflictError("Content revision no longer matches")
        raise UnsupportedCapabilityError("GitHub plan writes require a compare-and-swap revision")

    def _entries(self) -> Sequence[PlanIndexEntry]:
        try:
            return self._index.list_all()
        except PlanIndexUnavailableError as exc:
            raise BacklogError(str(exc)) from exc
        except (ArtifactWriteError, PlanIndexError) as exc:
            raise BacklogError(str(exc)) from exc

    def _record(self, entry: PlanIndexEntry) -> ContentRecord:
        try:
            content = (
                self._client.read(entry.issue, plan_id=entry.plan_id)
                if entry.issue is not None
                else self._provider.read_artifact_content_from_remote(
                    self._sentinel_issue, "plan", self._unlinked_path(entry.plan_id)
                )
            )
        except PlanContentUnavailableError as exc:
            raise BacklogError(str(exc)) from exc
        reference = ContentRef(kind=ContentKind.PLAN, name=entry.plan_id)
        if content is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return ContentRecord(
            reference=reference,
            owner_reference=self._owner(entry),
            content=content,
            revision=GitHubBackend._content_revision(content),
        )

    @staticmethod
    def _owner(entry: PlanIndexEntry) -> str:
        return f"#{entry.issue}" if entry.issue is not None else ""

    @staticmethod
    def _unlinked_path(plan_id: str) -> str:
        return f"sam-plan/unlinked/{plan_id}.yaml"


class _GitHubDispatchPersistence:
    _CONTENT_TYPE = "dispatch-plan"
    _INDEX_TYPE = "dispatch-plan-index"
    _INDEX_PATH = "dispatch-plan/index.json"
    _ENVELOPE_VERSION_KEY = "dispatch-content-version"

    def __init__(self, provider: ArtifactBackend) -> None:
        self._provider = provider
        self._sentinel_issue = create_plan_id_index(ArtifactRegistryClient(provider))._sentinel_issue

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        entries = [
            entry
            for entry in self._entries()
            if (query.owner_reference is None or entry.owner_reference == query.owner_reference)
            and query.search.casefold() in entry.name.casefold()
        ]
        records = [self._record(entry) for entry in entries]
        return records[query.offset : query.offset + query.limit]

    def get(self, reference: ContentRef) -> ContentRecord:
        entry = next((entry for entry in self._entries() if entry.name == reference.name), None)
        if entry is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return self._record(entry)

    def put(self, request: ContentWrite) -> ContentRecord:
        entries = self._entries()
        entry = next((entry for entry in entries if entry.name == request.reference.name), None)
        current = self._record(entry) if entry is not None else None
        owner_reference = (
            request.owner_reference if request.owner_reference is not None else current and current.owner_reference
        )
        if current is not None and current.content == request.content and current.owner_reference == owner_reference:
            return current
        raise UnsupportedCapabilityError("GitHub dispatch writes are not supported")

    def _record(self, entry: _DispatchIndexEntry) -> ContentRecord:
        stored_content = self._provider.read_artifact_content_from_remote(
            self._sentinel_issue, self._CONTENT_TYPE, self._content_path(entry.name)
        )
        if stored_content is None:
            reference = ContentRef(kind=ContentKind.DISPATCH_PLAN, name=entry.name)
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        envelope = self._parse_envelope(stored_content)
        if entry.legacy:
            content = stored_content
        else:
            if envelope is None:
                raise ContentUnavailableError("Dispatch content envelope is invalid")
            content = envelope[2]
        return ContentRecord(
            reference=ContentRef(kind=ContentKind.DISPATCH_PLAN, name=entry.name),
            owner_reference=entry.owner_reference,
            content=content,
            revision=GitHubBackend._content_revision(content),
        )

    def _entries(self) -> Sequence[_DispatchIndexEntry]:
        provider = self._provider
        if not isinstance(provider, _RemoteArtifactContentLister):
            raise ContentUnavailableError("GitHub artifact provider cannot enumerate dispatch plans")
        current_entries: list[_DispatchIndexEntry] = []
        for stored_content in provider.list_artifact_content_from_remote(
            self._sentinel_issue, self._CONTENT_TYPE, "dispatch-plan/"
        ).values():
            envelope = self._parse_envelope(stored_content)
            if envelope is not None:
                current_entries.append(_DispatchIndexEntry(name=envelope[0], owner_reference=envelope[1]))

        current_names = {entry.name for entry in current_entries}
        return [*current_entries, *(entry for entry in self._legacy_entries() if entry.name not in current_names)]

    def _legacy_entries(self) -> Sequence[_DispatchIndexEntry]:
        content = self._provider.read_artifact_content_from_remote(
            self._sentinel_issue, self._INDEX_TYPE, self._INDEX_PATH
        )
        if content is None:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ContentUnavailableError("Dispatch content index is invalid") from exc
        if isinstance(data, list) and all(isinstance(name, str) for name in data):
            return [_DispatchIndexEntry(name=name, owner_reference="", legacy=True) for name in data]
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ContentUnavailableError("Dispatch content index is invalid")
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            raise ContentUnavailableError("Dispatch content index is invalid")
        entries: list[_DispatchIndexEntry] = []
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                raise ContentUnavailableError("Dispatch content index is invalid")
            name = raw_entry.get("name")
            owner_reference = raw_entry.get("owner_reference")
            if not isinstance(name, str) or not isinstance(owner_reference, str):
                raise ContentUnavailableError("Dispatch content index is invalid")
            entries.append(_DispatchIndexEntry(name=name, owner_reference=owner_reference, legacy=True))
        return entries

    @classmethod
    def _serialize_envelope(cls, name: str, owner_reference: str, content: str) -> str:
        return json.dumps(
            {cls._ENVELOPE_VERSION_KEY: 1, "name": name, "owner_reference": owner_reference, "content": content},
            separators=(",", ":"),
        )

    @classmethod
    def _parse_envelope(cls, stored_content: str) -> tuple[str, str, str] | None:
        try:
            data = json.loads(stored_content)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict) or cls._ENVELOPE_VERSION_KEY not in data:
            return None
        if data[cls._ENVELOPE_VERSION_KEY] != 1:
            raise ContentUnavailableError("Dispatch content envelope is invalid")
        name = data.get("name")
        owner_reference = data.get("owner_reference")
        content = data.get("content")
        if not isinstance(name, str) or not isinstance(owner_reference, str) or not isinstance(content, str):
            raise ContentUnavailableError("Dispatch content envelope is invalid")
        return name, owner_reference, content

    @staticmethod
    def _content_path(name: str) -> str:
        return f"dispatch-plan/{name}.json"


@dataclass(frozen=True, slots=True)
class _DispatchIndexEntry:
    name: str
    owner_reference: str
    legacy: bool = False


class GitHubBackend:
    """Backend implementation delegating to gh_client, github_sync, and github_branches.

    Each method is a 1-3 line delegation.  The constructor accepts an optional
    default repo string that is used when callers pass an empty ``repo`` argument.

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

    _TARGET_BATCH_SIZE = 100

    def __init__(
        self,
        repo: str = "",
        *,
        cache: FileCache | None = None,
        artifact_provider: ArtifactBackend | None = None,
        plan_persistence: _PlanPersistence | None = None,
    ) -> None:
        """Initialise with an optional default repo string.

        Args:
            repo: Optional ``owner/name`` string used as default for repo-optional methods.
            cache: Provider-private durable cache, injectable for isolated callers.
            artifact_provider: Existing GitHub Gist persistence adapter.
            plan_persistence: Existing GitHub plan-index and Gist composition.
        """
        self._repo = repo
        self._cache = cache or FileCache(_dh_paths.state_root() / "github-cache")
        self._artifact_provider = artifact_provider or GitHubGistArtifactProvider(repo=repo)
        self._plan_persistence = plan_persistence or _GitHubPlanPersistence(self._artifact_provider)
        self._dispatch_persistence = _GitHubDispatchPersistence(self._artifact_provider)

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

    def list_work_items(self) -> list[BacklogItem]:
        """List work items from the provider-private cache.

        Returns:
            Persisted work items.
        """
        return [record.item for record in self._load_reconcile_records()]

    def get_work_item(self, reference: str) -> BacklogItem:
        """Get a cached work item by stable reference.

        Returns:
            The matching work item.
        """
        for record in self._load_reconcile_records():
            if reference == record.item.reference:
                return record.item
        raise KeyError(reference)

    def put_work_item(self, item: BacklogItem) -> None:
        """Persist a work-item intent for provider reconciliation."""
        reference = item.reference or item.issue or hashlib.sha256(item.title.encode()).hexdigest()
        self._cache._queue_work_item(reference, item.model_copy(update={"reference": reference}))

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
        for offset in range(0, len(numbered_references), self._TARGET_BATCH_SIZE):
            chunk = numbered_references[offset : offset + self._TARGET_BATCH_SIZE]
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

    def _preflight_patches(
        self, patches: list[ProviderPatch], current_by_reference: dict[str, IssueNode | None]
    ) -> dict[str, PatchResult]:
        results_by_reference: dict[str, PatchResult] = {}
        for patch in patches:
            issue = current_by_reference.get(patch.reference)
            if issue is None:
                results_by_reference[patch.reference] = PatchResult(
                    provider_id=patch.provider_id, reference=patch.reference, status="error", message="Issue not found"
                )
                continue
            if issue["updatedAt"] != patch.expected_revision:
                results_by_reference[patch.reference] = PatchResult(
                    provider_id=patch.provider_id,
                    reference=patch.reference,
                    status="conflict",
                    revision=issue["updatedAt"],
                )
                continue
            if issue["body"].replace("\r\n", "\n") == patch.body.replace("\r\n", "\n"):
                results_by_reference[patch.reference] = PatchResult(
                    provider_id=patch.provider_id,
                    reference=patch.reference,
                    status="applied",
                    revision=issue["updatedAt"],
                )
                continue
            results_by_reference[patch.reference] = PatchResult(
                provider_id=patch.provider_id, reference=patch.reference, status="conflict", revision=issue["updatedAt"]
            )
        return results_by_reference

    def _fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Fetch one normalized bounded GitHub snapshot for reconciliation.

        Returns:
            Provider snapshot whose pagination remains private to this adapter.
        """
        sync_started_at = datetime.now(UTC).isoformat()
        repo = self.get_github()
        owner, repo_name = repo.full_name.split("/", 1)
        labels = [request.label] if request.label else None
        match request.scope:
            case ReconcileScope.INITIAL:
                issues = self._fetch_issues_graphql(repo, owner, repo_name, state="OPEN", labels=labels, first=100)
            case ReconcileScope.INCREMENTAL:
                issues = self._fetch_issues_graphql(
                    repo, owner, repo_name, state="OPEN,CLOSED", labels=labels, first=100, since=request.since or None
                )
            case ReconcileScope.LINKED | ReconcileScope.TARGETED:
                issues = []

        items_by_identity = {
            (f"#{issue['number']}", issue["updatedAt"]): ProviderItem(
                provider_id=issue["id"],
                reference=f"#{issue['number']}",
                title=issue["title"],
                body=issue["body"],
                state=issue["state"],
                labels=[label["name"] for label in issue["labels"]],
                revision=issue["updatedAt"],
            )
            for issue in issues
        }
        listed_references = {item.reference for item in items_by_identity.values()}
        target_references = [reference for reference in request.references if reference not in listed_references]
        targeted = self._fetch_targeted_issues(repo, owner, repo_name, target_references)
        for reference, issue in targeted.items():
            if issue is None:
                item = ProviderItem(
                    provider_id="",
                    reference=reference,
                    title="",
                    body="",
                    state="",
                    labels=[],
                    revision="",
                    exists=False,
                )
            else:
                item = ProviderItem(
                    provider_id=issue["id"],
                    reference=f"#{issue['number']}",
                    title=issue["title"],
                    body=issue["body"],
                    state=issue["state"],
                    labels=[label["name"] for label in issue["labels"]],
                    revision=issue["updatedAt"],
                )
            items_by_identity[item.reference, item.revision] = item
        return ProviderSnapshot(
            items=list(items_by_identity.values()), sync_started_at=sync_started_at, pages_fetched=1
        )

    def _apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        """Apply optimistic GitHub body patches and return one outcome per patch.

        Returns:
            Patch results indexed by the stable provider reference.
        """
        if not patches:
            return []
        repo = self.get_github()
        owner, repo_name = repo.full_name.split("/", 1)
        try:
            current_by_reference = self._fetch_targeted_issues(
                repo, owner, repo_name, [patch.reference for patch in patches]
            )
        except BacklogError as exc:
            return [
                PatchResult(provider_id=patch.provider_id, reference=patch.reference, status="error", message=str(exc))
                for patch in patches
            ]

        results_by_reference = self._preflight_patches(patches, current_by_reference)
        return [results_by_reference[patch.reference] for patch in patches]

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Reconcile provider state through the pure engine and private cache.

        Returns:
            Completed reconciliation counts with changed logical references.
        """
        effective_request = self._with_snapshot_checkpoint(request)
        snapshot = self._fetch_snapshot(effective_request)
        plan = reconcile_backlog(self._load_reconcile_records(), snapshot, effective_request)
        cache_results: list[ActionResult] = []
        for action in (entry for entry in plan.cache_actions if entry.phase == "before_provider"):
            try:
                self._cache._save_work_item_snapshot(action.key, action.record.item)
            except OSError:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="error"))
            else:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="applied"))

        patch_results = self._apply_patches(plan.provider_patches)
        applied_revisions = {
            result.reference: result.revision for result in patch_results if result.status == "applied"
        }
        for action in (entry for entry in plan.cache_actions if entry.phase == "checkpoint"):
            revision = applied_revisions.get(action.requires_patch)
            if revision is None:
                continue
            metadata = action.record.item.metadata.model_copy(update={"updated_at": revision})
            item = action.record.item.model_copy(update={"metadata": metadata})
            try:
                self._cache._save_work_item_snapshot(action.key, item)
            except OSError:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="error"))
            else:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="applied"))

        outcome = finalize_reconciliation(
            plan, ReconcileExecution(cache_results=cache_results, patch_results=patch_results)
        )
        self._advance_snapshot_checkpoint(effective_request.scope, plan.snapshot_checkpoint, outcome)
        if outcome.result.failures == 0 and outcome.result.conflicts == 0 and not effective_request.dry_run:
            acknowledged = {
                mutation.key
                for mutation in self._cache._pending_work_item_mutations()
                if mutation.item.metadata.issue in {item.reference for item in snapshot.items}
            }
            self._cache._acknowledge_work_items(acknowledged)
        pending_mutations = len(self._cache.pending_mutations()) + len(self._cache._pending_work_item_mutations())
        return outcome.result.model_copy(update={"pending_mutations": pending_mutations})

    def _with_snapshot_checkpoint(self, request: ReconcileRequest) -> ReconcileRequest:
        match request.scope:
            case ReconcileScope.INCREMENTAL:
                if request.since:
                    return request
                checkpoint = self._cache._get_snapshot_checkpoint()
                if checkpoint is None:
                    return request.model_copy(update={"scope": ReconcileScope.INITIAL})
                return request.model_copy(update={"since": checkpoint.watermark})
            case ReconcileScope.INITIAL | ReconcileScope.LINKED | ReconcileScope.TARGETED:
                return request

    def _advance_snapshot_checkpoint(self, scope: ReconcileScope, watermark: str, outcome: ReconcileOutcome) -> None:
        if (
            outcome.advance_snapshot_checkpoint
            and outcome.result.conflicts == 0
            and scope in {ReconcileScope.INITIAL, ReconcileScope.INCREMENTAL}
        ):
            self._cache._set_snapshot_checkpoint(_ProviderSnapshotCheckpoint(watermark=watermark))

    def _load_reconcile_records(self) -> list[LogicalCacheRecord]:
        records_by_key = {
            key: LogicalCacheRecord(key=key, item=item) for key, item in self._cache._work_item_snapshots()
        }
        for mutation in self._cache._pending_work_item_mutations():
            records_by_key[mutation.key] = LogicalCacheRecord(key=mutation.key, item=mutation.item)
        return list(records_by_key.values())

    def list_content(self, query: ContentQuery) -> list[ContentRecord]:
        """Return a bounded cache-backed discovery page for GitHub content."""
        online = self.try_get_github() is not None
        if online:
            self._replay_pending_content()
            if query.kind == ContentKind.PLAN:
                try:
                    records = list(self._plan_persistence.list(query))
                except ContentNotFoundError:
                    raise
                except (BacklogError, ContentUnavailableError, OSError):
                    online = False
                else:
                    for record in records:
                        self._cache.cache_content(record)
                    return records
            if query.kind == ContentKind.DISPATCH_PLAN:
                try:
                    records = list(self._dispatch_persistence.list(query))
                except ContentNotFoundError:
                    raise
                except (BacklogError, ContentUnavailableError, OSError):
                    online = False
                else:
                    for record in records:
                        self._cache.cache_content(record)
                    return records
        records = [
            record.model_copy(update={"stale": not online})
            for record in self._cache._load_state().records
            if record.reference.kind == query.kind
            and (query.owner_reference is None or record.owner_reference == query.owner_reference)
            and query.search.casefold() in record.reference.name.casefold()
        ]
        records.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return records[query.offset : query.offset + query.limit]

    def get_content(self, reference: ContentRef) -> ContentRecord:
        """Read authoritative GitHub content or an explicitly stale cached copy.

        Returns:
            The provider or cached logical content record.
        """
        if self.try_get_github() is None:
            return self._cache.get_content(reference, stale=True)
        self._replay_pending_content()
        cached = self._cached_content(reference)
        try:
            record = self._read_online_content(reference, cached)
        except ContentNotFoundError:
            raise
        except (BacklogError, ContentUnavailableError, OSError):
            return self._cache.get_content(reference, stale=True)
        self._cache.cache_content(record)
        return record

    def put_content(self, request: ContentWrite) -> ContentRecord:
        """Write GitHub content, durably queueing it while GitHub is offline.

        Returns:
            The applied or pending logical content record.
        """
        cached = self._cached_content(request.reference)
        if self.try_get_github() is None:
            if request.create_only and cached is not None:
                raise ContentConflictError("Content already exists")
            if request.expected_revision and (cached is None or cached.revision != request.expected_revision):
                raise ContentConflictError("Content revision no longer matches")
            base = cached or ContentRecord(
                reference=request.reference,
                owner_reference=request.reference.namespace,
                content="",
                revision=request.expected_revision,
            )
            self._cache.queue_write(base, request)
            return self._cache.get_content(request.reference)
        self._replay_pending_content()
        cached = self._cached_content(request.reference)
        try:
            record = self._write_online_content(request, cached)
        except ContentNotFoundError:
            raise
        except (BacklogError, ContentUnavailableError, OSError):
            base = cached or ContentRecord(
                reference=request.reference,
                owner_reference=request.reference.namespace,
                content="",
                revision=request.expected_revision,
            )
            self._cache.queue_write(base, request)
            return self._cache.get_content(request.reference)
        self._cache.cache_content(record)
        return record

    def _cached_content(self, reference: ContentRef) -> ContentRecord | None:
        try:
            return self._cache.get_content(reference)
        except ContentUnavailableError:
            return None

    def _read_online_content(self, reference: ContentRef, cached: ContentRecord | None) -> ContentRecord:
        owner_reference = reference.namespace
        match reference.kind:
            case ContentKind.PLAN:
                return self._plan_persistence.get(reference)
            case ContentKind.DISPATCH_PLAN:
                return self._dispatch_persistence.get(reference)
            case ContentKind.ARTIFACT_MANIFEST:
                manifest = self._artifact_provider.get_manifest(self._owner_number(reference.namespace))
                content = manifest.model_dump_json(by_alias=True)
            case ContentKind.ARTIFACT_CONTENT:
                content = self._artifact_provider.read_artifact_content_from_remote(
                    self._owner_number(reference.namespace),
                    reference.artifact_type,
                    f"{reference.artifact_type}/{reference.name}",
                )
        if content is None:
            raise ContentNotFoundError(f"Content was not found: {reference.model_dump_json()}")
        return ContentRecord(
            reference=reference,
            owner_reference=owner_reference,
            content=content,
            revision=self._content_revision(content),
        )

    def _write_online_content(self, request: ContentWrite, cached: ContentRecord | None) -> ContentRecord:
        match request.reference.kind:
            case ContentKind.PLAN:
                return self._plan_persistence.put(request)
            case ContentKind.DISPATCH_PLAN:
                return self._dispatch_persistence.put(request)
            case ContentKind.ARTIFACT_MANIFEST | ContentKind.ARTIFACT_CONTENT:
                raise UnsupportedCapabilityError("GitHub artifact writes require compare-and-swap support")
            case unreachable:
                assert_never(unreachable)

    def _replay_pending_content(self) -> None:
        acknowledgements: list[ReplayAcknowledgement] = []
        for mutation in self._cache.pending_mutations():
            cached = self._cached_content(mutation.write.reference)
            try:
                record = self._write_online_content(mutation.write, cached)
            except (ContentConflictError, UnsupportedCapabilityError):
                continue
            except (BacklogError, ContentUnavailableError, OSError):
                break
            acknowledgements.append(
                ReplayAcknowledgement(
                    idempotency_key=mutation.idempotency_key,
                    record=record,
                    fingerprint=self._content_revision(record.content),
                )
            )
        if acknowledgements:
            self._cache.acknowledge_replay(acknowledgements)

    @staticmethod
    def _owner_number(reference: str) -> int:
        number = parse_issue_number(reference)
        if number is None:
            raise ContentUnavailableError(f"Invalid GitHub owner reference: {reference!r}")
        return number

    @staticmethod
    def _content_revision(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

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
