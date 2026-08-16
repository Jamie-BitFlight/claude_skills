"""Work-item snapshot and reconciliation collaborators for the GitHub backend.

Two collaborators split the work-item lane at the boundary between provider
translation and the reconciliation cycle:

``_GitHubWorkItemSync``
    Translates GitHub issues into normalized provider snapshots and applies
    provider patches. It resolves the authoritative body through the audit
    comment referenced by each work-item head record, so a body edited outside
    the harness never silently overwrites a tracked revision.

``_GitHubReconciliation``
    Drives the reconciliation cycle: snapshot checkpoint selection, cache record
    loading, pure-engine invocation, ordered cache writes around the provider
    patches, and acknowledgement of queued work-item mutations.

Both reach GitHub through narrow Protocols (``_IssueGateway``,
``_ReconcileProvider``) that :class:`GitHubBackend` satisfies, so the backend
remains the single composition root and the substitutable seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from backlog_core import gh_client
from backlog_core.backends._github_work_item_versions import (
    WorkItemHead,
    WorkItemVersion,
    is_work_item_head_ref,
    parse_work_item_comment,
    parse_work_item_head,
    render_work_item_comment,
    root_revision,
    work_item_head_ref,
)
from backlog_core.backends.github_content_stores import _CONTENT_PAGE_SIZE, _ContentPersistence, _list_all_content
from backlog_core.file_cache import _ProviderSnapshotCheckpoint
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
    from collections.abc import Callable, Sequence

    from github.Repository import Repository

    from backlog_core.backend_types import IssueCommentNode, IssueNode
    from backlog_core.file_cache import FileCache
    from backlog_core.file_cache_state import _PendingWorkItemMutation

# Bounded aliased GraphQL batch size for issue-node and comment-node batches,
# which carry small metadata fields rather than full content bodies.
_TARGET_BATCH_SIZE = 100


@runtime_checkable
class _ReferenceContentPersistence(Protocol):
    """Content stores that can resolve many references in one round trip."""

    def get_many(self, references: Sequence[ContentRef]) -> list[ContentRecord]: ...


class _IssueGateway(Protocol):
    """GitHub issue API operations the work-item translator depends on.

    :class:`GitHubBackend` satisfies this Protocol structurally, so every call
    resolves against the live backend attribute at call time instead of a
    reference captured during construction.
    """

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository: ...

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]: ...

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
    ) -> list[IssueNode]: ...

    def _fetch_targeted_issues(
        self, repo: Repository, owner: str, repo_name: str, references: list[str]
    ) -> dict[str, IssueNode | None]: ...

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str: ...

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode: ...


class _ReconcileProvider(Protocol):
    """Provider snapshot and patch operations the reconciliation cycle drives.

    :class:`GitHubBackend` satisfies this Protocol structurally, keeping the
    snapshot and patch steps substitutable on the composing backend.
    """

    def _fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot: ...
    def _apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]: ...


class _GitHubWorkItemSync:
    """Translate GitHub issues into provider snapshots and apply provider patches."""

    def __init__(self, issues: _IssueGateway, contents: Callable[[], _ContentPersistence]) -> None:
        """Bind the issue gateway to the content store holding work-item heads.

        Args:
            issues: GitHub issue API operations, resolved at call time.
            contents: Resolver for the content store holding work-item head
                records. Kept as a callable so a substituted store on the
                composing backend takes effect for calls made after construction.
        """
        self._issues = issues
        self._contents = contents

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Fetch one normalized bounded GitHub snapshot for reconciliation.

        Returns:
            Provider snapshot whose pagination remains private to this adapter.
        """
        sync_started_at = datetime.now(UTC).isoformat()
        repo = self._issues.get_github()
        owner, repo_name = repo.full_name.split("/", 1)
        labels = [request.label] if request.label else None
        match request.scope:
            case ReconcileScope.INITIAL:
                issues = self._issues._fetch_issues_graphql(
                    repo, owner, repo_name, state="OPEN", labels=labels, first=100
                )
            case ReconcileScope.INCREMENTAL:
                issues = self._issues._fetch_issues_graphql(
                    repo, owner, repo_name, state="OPEN,CLOSED", labels=labels, first=100, since=request.since or None
                )
            case ReconcileScope.LINKED | ReconcileScope.TARGETED:
                issues = []

        listed_references = {f"#{issue['number']}" for issue in issues}
        target_references = [reference for reference in request.references if reference not in listed_references]
        targeted = self._issues._fetch_targeted_issues(repo, owner, repo_name, target_references)
        existing_issues = [*issues, *(issue for issue in targeted.values() if issue is not None)]
        heads, comments = self._work_item_contexts(repo, existing_issues)
        items_by_identity: dict[tuple[str, str], ProviderItem] = {}
        for issue in issues:
            item = self.provider_item_from_issue(repo, owner, repo_name, issue, heads, comments)
            items_by_identity[item.reference, item.revision] = item
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
                item = self.provider_item_from_issue(repo, owner, repo_name, issue, heads, comments)
            items_by_identity[item.reference, item.revision] = item
        return ProviderSnapshot(
            items=list(items_by_identity.values()), sync_started_at=sync_started_at, pages_fetched=1
        )

    def apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        """Apply optimistic GitHub body patches and return one outcome per patch.

        Returns:
            Patch results indexed by the stable provider reference.
        """
        if not patches:
            return []
        repo = self._issues.get_github()
        owner, repo_name = repo.full_name.split("/", 1)
        try:
            current_by_reference = self._issues._fetch_targeted_issues(
                repo, owner, repo_name, [patch.reference for patch in patches]
            )
        except BacklogError as exc:
            return [
                PatchResult(provider_id=patch.provider_id, reference=patch.reference, status="error", message=str(exc))
                for patch in patches
            ]

        results: list[PatchResult] = []
        for patch in patches:
            issue = current_by_reference.get(patch.reference)
            if issue is None:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id,
                        reference=patch.reference,
                        status="error",
                        message="Issue not found",
                    )
                )
                continue
            try:
                current, head_record, root = self.work_item_version(repo, owner, repo_name, issue)
            except ContentConflictError as exc:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id, reference=patch.reference, status="conflict", message=str(exc)
                    )
                )
                continue
            except (BacklogError, ContentUnavailableError) as exc:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id, reference=patch.reference, status="error", message=str(exc)
                    )
                )
                continue
            if current.revision != patch.expected_revision:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id,
                        reference=patch.reference,
                        status="conflict",
                        revision=current.revision,
                    )
                )
                continue
            if current.body.replace("\r\n", "\n") == patch.body.replace("\r\n", "\n"):
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id,
                        reference=patch.reference,
                        status="applied",
                        revision=current.revision,
                    )
                )
                continue
            try:
                comment_id = self._issues._add_comment_graphql(
                    repo, issue["id"], render_work_item_comment(current.revision, patch.body)
                )
                if not comment_id:
                    results.append(
                        PatchResult(
                            provider_id=patch.provider_id,
                            reference=patch.reference,
                            status="error",
                            message="GitHub work-item audit comment response was invalid",
                        )
                    )
                    continue
                head = WorkItemHead.create(patch.reference, current.revision, root, patch.body, comment_id)
                written = self._contents().put(
                    ContentWrite(
                        reference=work_item_head_ref(patch.reference),
                        content=head.model_dump_json(),
                        expected_revision=head_record.revision if head_record is not None else "",
                        create_only=head_record is None,
                    )
                )
            except ContentConflictError as exc:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id, reference=patch.reference, status="conflict", message=str(exc)
                    )
                )
                continue
            except (BacklogError, ContentUnavailableError) as exc:
                results.append(
                    PatchResult(
                        provider_id=patch.provider_id, reference=patch.reference, status="error", message=str(exc)
                    )
                )
                continue
            results.append(
                PatchResult(
                    provider_id=patch.provider_id,
                    reference=patch.reference,
                    status="applied",
                    revision=written.revision,
                )
            )
        return results

    def provider_item_from_issue(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        issue: IssueNode,
        heads: dict[str, ContentRecord] | None = None,
        comments: dict[str, IssueCommentNode] | None = None,
    ) -> ProviderItem:
        """Normalize one GitHub issue into a provider item at its tracked revision.

        Returns:
            The normalized provider item.
        """
        version, _head_record, _root = self.work_item_version(repo, owner, repo_name, issue, heads, comments)
        return ProviderItem(
            provider_id=issue["id"],
            reference=f"#{issue['number']}",
            title=issue["title"],
            body=version.body,
            state=issue["state"],
            labels=[label["name"] for label in issue["labels"]],
            revision=version.revision,
        )

    def work_item_version(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        issue: IssueNode,
        heads: dict[str, ContentRecord] | None = None,
        comments: dict[str, IssueCommentNode] | None = None,
    ) -> tuple[WorkItemVersion, ContentRecord | None, str]:
        """Resolve the authoritative body and revision tracked for one issue.

        Returns:
            The resolved version, its backing head record if any, and the issue's
            root revision.
        """
        reference = f"#{issue['number']}"
        root = root_revision(reference, issue["id"], issue["body"])
        if heads is None:
            try:
                head_record = self._contents().get(work_item_head_ref(reference))
            except ContentNotFoundError:
                return WorkItemVersion(revision=root, body=issue["body"]), None, root
        else:
            head_record = heads.get(reference)
            if head_record is None:
                return WorkItemVersion(revision=root, body=issue["body"]), None, root
        head = parse_work_item_head(head_record.content)
        if head.issue_reference != reference or head.root_revision != root:
            return WorkItemVersion(revision=root, body=issue["body"]), head_record, root
        comment = (
            comments.get(head.comment_id)
            if comments is not None
            else self._issues._fetch_comment_by_id_graphql(repo, head.comment_id)
        )
        return (
            WorkItemVersion(revision=head_record.revision, body=parse_work_item_comment(head, comment)),
            head_record,
            root,
        )

    def _work_item_contexts(
        self, repo: Repository, issues: list[IssueNode]
    ) -> tuple[dict[str, ContentRecord], dict[str, IssueCommentNode]]:
        contents = self._contents()
        namespaces = {f"#{issue['number']}" for issue in issues}
        if isinstance(contents, _ReferenceContentPersistence):
            records = contents.get_many([work_item_head_ref(reference) for reference in namespaces])
        else:
            records = _list_all_content(
                contents, ContentQuery(kind=ContentKind.ARTIFACT_CONTENT, search="head", limit=_CONTENT_PAGE_SIZE)
            )
        heads = {
            record.reference.namespace: record
            for record in records
            if record.reference.namespace in namespaces and is_work_item_head_ref(record.reference)
        }
        issue_by_reference = {f"#{issue['number']}": issue for issue in issues}
        comment_ids = [
            head.comment_id
            for reference, record in heads.items()
            if (head := parse_work_item_head(record.content)).root_revision
            == root_revision(reference, issue_by_reference[reference]["id"], issue_by_reference[reference]["body"])
        ]
        comments: dict[str, IssueCommentNode] = {}
        for offset in range(0, len(comment_ids), _TARGET_BATCH_SIZE):
            ids = comment_ids[offset : offset + _TARGET_BATCH_SIZE]
            response = self._issues._graphql_request(
                repo,
                "query AuditComments($ids: [ID!]!) { nodes(ids: $ids) { "
                "... on IssueComment { id body url author { login } createdAt updatedAt } } }",
                {"ids": ids},
            )
            nodes = response.get("nodes")
            if not isinstance(nodes, list) or len(nodes) != len(ids):
                raise ContentUnavailableError("GitHub work-item audit comment response was invalid")
            for node in nodes:
                if not isinstance(node, dict):
                    raise ContentUnavailableError("GitHub work-item audit comment response was invalid")
                comment = gh_client._parse_comment_node(node)
                comments[comment["id"]] = comment
        return heads, comments


class _GitHubReconciliation:
    """Drive the reconciliation cycle between the private cache and the provider."""

    def __init__(self, cache: FileCache, provider: _ReconcileProvider) -> None:
        """Bind the provider-private cache to the snapshot and patch seam.

        Args:
            cache: Provider-private durable cache.
            provider: Snapshot and patch operations, resolved at call time.
        """
        self._cache = cache
        self._provider = provider

    def list_work_items(self) -> list[BacklogItem]:
        """List work items from the provider-private cache.

        Returns:
            Persisted work items.
        """
        return [record.item for record in self.load_records()]

    def get_work_item(self, reference: str) -> BacklogItem:
        """Get a cached work item by stable reference.

        Returns:
            The matching work item.

        Raises:
            KeyError: If no cached work item carries the reference.
        """
        for record in self.load_records():
            if reference == record.item.reference:
                return record.item
        raise KeyError(reference)

    def put_work_item(self, item: BacklogItem) -> None:
        """Persist a work-item intent for provider reconciliation.

        ``item.reference`` is guaranteed non-empty by
        :class:`~backlog_core.models.BacklogItem`'s ``_sync_metadata``
        validator, which self-heals it at construction time — no fallback
        derivation is needed here. A copy is queued (rather than ``item``
        itself) so a caller mutating its own ``item`` after this call cannot
        retroactively alter the queued mutation.
        """
        self._cache._queue_work_item(item.reference, item.model_copy())

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        """Reconcile provider state through the pure engine and private cache.

        Returns:
            Completed reconciliation counts with changed logical references.
        """
        effective_request = self._with_snapshot_checkpoint(request)
        snapshot = self._provider._fetch_snapshot(effective_request)
        pending_work_items = self._cache._pending_work_item_mutations()
        plan = reconcile_backlog(self.load_records(pending_work_items), snapshot, effective_request)
        cache_results: list[ActionResult] = []
        for action in (entry for entry in plan.cache_actions if entry.phase == "before_provider"):
            try:
                self._cache._save_work_item_snapshot(action.key, action.record.item)
            except OSError:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="error"))
            else:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="applied"))

        patch_results = self._provider._apply_patches(plan.provider_patches)
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
        if not effective_request.dry_run:
            snapshot_by_reference = {item.reference: item for item in snapshot.items}
            patch_statuses = {patch.reference: "pending" for patch in plan.provider_patches}
            patch_statuses.update({result.reference: result.status for result in patch_results})
            failed_cache_references = {
                action.record.item.metadata.issue
                for action in plan.cache_actions
                for result in cache_results
                if (action.key, action.phase) == (result.key, result.phase) and result.status == "error"
            }
            self._cache._acknowledge_work_items({
                mutation.idempotency_key
                for mutation in pending_work_items
                if mutation.item.metadata.issue in snapshot_by_reference
                and mutation.item.title == snapshot_by_reference[mutation.item.metadata.issue].title
                and mutation.item.metadata.issue not in failed_cache_references
                and (patch_statuses.get(mutation.item.metadata.issue, "no_patch") in {"no_patch", "applied"})
            })
        pending_mutations = len(self._cache.pending_mutations()) + len(self._cache._pending_work_item_mutations())
        return outcome.result.model_copy(update={"pending_mutations": pending_mutations})

    def load_records(
        self, pending_work_items: Sequence[_PendingWorkItemMutation] | None = None
    ) -> list[LogicalCacheRecord]:
        """Merge cached work-item snapshots with queued mutations.

        Returns:
            One logical cache record per work-item reference.
        """
        records_by_reference = {
            item.reference: LogicalCacheRecord(key=key, item=item) for key, item in self._cache._work_item_snapshots()
        }
        for mutation in (
            pending_work_items if pending_work_items is not None else self._cache._pending_work_item_mutations()
        ):
            snapshot = records_by_reference.get(mutation.item.reference)
            records_by_reference[mutation.item.reference] = LogicalCacheRecord(
                key=snapshot.key if snapshot is not None else mutation.key, item=mutation.item
            )
        return list(records_by_reference.values())

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
