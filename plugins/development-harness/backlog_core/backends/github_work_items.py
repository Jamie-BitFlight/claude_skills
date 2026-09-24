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

from backlog_core import gh_client, rendering
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

    from backlog_core.backend_types import AddedCommentNode, IssueCommentNode, IssueNode
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

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> AddedCommentNode: ...

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode: ...


class _ReconcileProvider(Protocol):
    """Provider snapshot and patch operations the reconciliation cycle drives.

    :class:`GitHubBackend` satisfies this Protocol structurally, keeping the
    snapshot and patch steps substitutable on the composing backend.
    """

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot: ...
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
        repo = self._issues.get_github(request.repo)
        owner, repo_name = repo.full_name.split("/", 1)
        labels = [request.label] if request.label else None
        match request.scope:
            case ReconcileScope.INITIAL:
                # A caller who directly requests INITIAL (never routed through
                # _GitHubReconciliation._with_snapshot_checkpoint's incremental
                # upgrade) only needs open issues -- a genuine from-scratch
                # reconcile. request.checkpoint_recovery marks the *other*
                # case: an INCREMENTAL request that had to be upgraded to
                # INITIAL because no trustworthy checkpoint existed to resolve
                # a "since" from (no checkpoint at all, or one that predates
                # scope metadata and may be a pre-A1 artifact -- see
                # _with_snapshot_checkpoint). That upgrade establishes (or
                # re-establishes) the checkpoint every subsequent incremental
                # fetch will trust, so it must also see closed issues: an
                # issue closed (or edited while closed) before this point
                # would otherwise never be observed again once the fresh
                # watermark starts being trusted.
                state = "OPEN,CLOSED" if request.checkpoint_recovery else "OPEN"
                issues = self._issues._fetch_issues_graphql(
                    repo, owner, repo_name, state=state, labels=labels, first=100
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
                added_comment = self._issues._add_comment_graphql(
                    repo, issue["id"], render_work_item_comment(current.revision, patch.body)
                )
                if not added_comment.id:
                    results.append(
                        PatchResult(
                            provider_id=patch.provider_id,
                            reference=patch.reference,
                            status="error",
                            message="GitHub work-item audit comment response was invalid",
                        )
                    )
                    continue
                head = WorkItemHead.create(patch.reference, current.revision, root, patch.body, added_comment.id)
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
            milestone=issue["milestone"]["title"] if issue["milestone"] else "",
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
                comments[comment.id] = comment
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
        # Populated by load_records() (and therefore list_work_items()) on every
        # call from the WorkItemSnapshotBatch.skipped list -- read back by
        # has_skipped_snapshots() with no extra I/O, rather than re-scanning the
        # cache root a second time per listing. Empty before the first load.
        self._last_skipped_snapshots: list[str] = []
        # Populated by load_records() alongside _last_skipped_snapshots --
        # True when the total snapshot file count found on disk (readable +
        # unreadable) falls short of the checkpoint's recorded
        # items_observed inventory (backlog #3546 Codex finding 1). A file
        # that vanished entirely -- deleted, or a partial cache restore --
        # never appears in WorkItemSnapshotBatch.skipped (that list only
        # names files that exist but failed to load), so it is otherwise
        # invisible to has_skipped_snapshots() alone. False before the first
        # load, and False whenever no checkpoint exists yet to compare
        # against.
        self._last_snapshot_shortfall: bool = False

    def list_work_items(self) -> list[BacklogItem]:
        """List work items from the provider-private cache.

        Returns:
            Persisted work items.
        """
        return [record.item for record in self.load_records()]

    def has_synced_snapshot(self) -> bool:
        """Report whether a durable, honest provider snapshot has ever completed.

        Backed by the same checkpoint ``_with_snapshot_checkpoint`` reads to
        pick ``INITIAL`` vs ``INCREMENTAL`` scope -- ``None`` means no
        reconcile has ever advanced it (A-critique.md Sec 4.1: "the
        checkpoint records that a reconcile happened, not what it covered",
        but a ``None`` checkpoint unambiguously means "never"). Callers use
        this to distinguish a never-synced cache, worth one automatic
        read-through, from a warm cache that happens to hold nothing right
        now.

        Returns:
            ``True`` once a reconcile has durably advanced the checkpoint.
        """
        return self._cache._get_snapshot_checkpoint() is not None

    def has_skipped_snapshots(self) -> bool:
        """Report whether the most recent local snapshot load found the cache incomplete.

        True for either of two independent, most-recent-``load_records()``
        discoveries (backlog #3546 tasks A2 and the Codex finding-1 follow-up):

        * ``WorkItemSnapshotBatch.skipped`` is non-empty -- one or more
          snapshot files exist but failed to load (bad YAML, invalid UTF-8,
          an ``OSError``).
        * The total snapshot file count found on disk (readable + unreadable)
          falls short of the checkpoint's recorded ``items_observed``
          inventory -- one or more files that were durably synced have since
          vanished entirely (deleted, or a partial cache restore). A vanished
          file never appears in ``skipped`` -- that list only names files
          that exist but failed to load -- so this second check is the only
          signal that catches it.

        Neither is re-derived by scanning the cache root again here -- both
        are read back from the load that already happened for
        :meth:`list_work_items`, so this costs no extra I/O. Returns
        ``False`` before any load has run. A warm checkpoint over a partial
        or incomplete snapshot set is exactly the case ``operations.list_items``
        (task A4) must not report as confidently servable.

        Returns:
            ``True`` when the most recent load skipped one or more files, or
            found fewer snapshot files on disk than the checkpoint expects.
        """
        return bool(self._last_skipped_snapshots) or self._last_snapshot_shortfall

    def has_pending_writes(self) -> bool:
        """Report whether the cache holds mutations not yet acknowledged by GitHub.

        Read fresh from the durable queue on every call (a lightweight
        ``cache.json`` read, not a directory scan) rather than cached like
        :meth:`has_skipped_snapshots`, since ``put_work_item``/acknowledgement
        can change it between calls within a single process.

        Returns:
            ``True`` when one or more work-item mutations are queued.
        """
        return bool(self._cache._pending_work_item_mutations())

    def pending_work_items(self) -> list[BacklogItem]:
        """Return copied queued work-item intent without cached provider rows."""
        return [mutation.item.model_copy(deep=True) for mutation in self._cache._pending_work_item_mutations()]

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

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
        """Reconcile provider state through the pure engine and private cache.

        Returns:
            Completed reconciliation counts with changed logical references.
        """
        effective_request = self._with_snapshot_checkpoint(request)
        if snapshot is None:
            snapshot = self._provider.fetch_snapshot(effective_request)
        elif effective_request.scope in {ReconcileScope.LINKED, ReconcileScope.TARGETED}:
            observed = {item.reference for item in snapshot.items}
            if missing := set(effective_request.references) - observed:
                raise ValueError(f"Supplied snapshot is missing requested references: {sorted(missing)}")
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

        patch_results = (
            self._provider._apply_patches(plan.provider_patches) if effective_request.apply_local_patches else []
        )
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
            plan,
            ReconcileExecution(
                cache_results=cache_results,
                patch_results=patch_results,
                patches_skipped=not effective_request.apply_local_patches,
            ),
        )
        self._advance_snapshot_checkpoint(
            effective_request.scope, effective_request.label, plan.snapshot_checkpoint, outcome
        )
        if not effective_request.dry_run:
            snapshot_by_reference = {item.reference: item for item in snapshot.items}
            patch_statuses = {patch.reference: "pending" for patch in plan.provider_patches}
            patch_statuses.update({result.reference: result.status for result in patch_results})
            failed_cache_references = {
                action.reference
                for action in plan.cache_actions
                for result in cache_results
                if (action.key, action.phase) == (result.key, result.phase) and result.status == "error"
            }
            self._cache._acknowledge_work_items({
                mutation.idempotency_key
                for mutation in pending_work_items
                if mutation.item.metadata.issue in snapshot_by_reference
                and mutation.item.metadata.issue not in set(plan.conflicted_references)
                and mutation.item.metadata.issue not in failed_cache_references
                and (patch_statuses.get(mutation.item.metadata.issue, "no_patch") in {"no_patch", "applied"})
            })
        return outcome.result.model_copy(
            update={
                "pending_mutations": len(self._cache.pending_mutations())
                + len(self._cache._pending_work_item_mutations()),
                # Schema-invalid entries dead-lettered into corrupt_queue_entries
                # (see _CacheStateStore._salvage_field with preserve=True) count
                # as rejected too: like a key mismatch, they're terminal and need
                # manual recovery, not silently invisible zero pending/zero rejected.
                "rejected_mutations": len(self._cache.rejected_mutations())
                + len(self._cache._rejected_work_item_mutations())
                + len(self._cache._corrupt_queue_entries()),
            }
        )

    def load_records(
        self, pending_work_items: Sequence[_PendingWorkItemMutation] | None = None
    ) -> list[LogicalCacheRecord]:
        """Merge cached work-item snapshots with queued mutations.

        Queued mutations are read from ``_CacheState`` via plain
        ``BacklogItem.model_validate`` (``file_cache_state.py``), which never
        runs ``rendering.normalize_unknown_sections`` — unlike a snapshot,
        which is always loaded through ``yaml_io.load_item`` and normalized on
        the way in. A mutation takes precedence over its snapshot for the same
        reference below, so a reference with a queued mutation would otherwise
        keep serving un-normalized (duplicate/stale-keyed) sections
        indefinitely — including while the mutation itself is stuck pending
        (e.g. the title-mismatch acknowledgement gap tracked in #2963), which
        is exactly when a caller most needs the healed view. Normalizing here
        closes that gap without touching the acknowledgement logic itself.

        Returns:
            One logical cache record per work-item reference.
        """
        batch = self._cache._work_item_snapshots()
        self._last_skipped_snapshots = batch.skipped
        checkpoint = self._cache._get_snapshot_checkpoint()
        # A checkpoint's items_observed records the total snapshot file count
        # (readable + unreadable) the durable cache held immediately after the
        # reconcile that advanced it (see _advance_snapshot_checkpoint). A
        # shortfall here -- fewer files found now than that recorded total --
        # means one or more files vanished entirely between then and now
        # (backlog #3546 Codex finding 1), since WorkItemSnapshotBatch.skipped
        # only ever names a file that still exists but failed to load.
        self._last_snapshot_shortfall = (
            checkpoint is not None and len(batch.snapshots) + len(batch.skipped) < checkpoint.items_observed
        )
        records_by_reference = {item.reference: LogicalCacheRecord(key=key, item=item) for key, item in batch.snapshots}
        for mutation in (
            pending_work_items if pending_work_items is not None else self._cache._pending_work_item_mutations()
        ):
            snapshot = records_by_reference.get(mutation.item.reference)
            item = mutation.item
            if item.sections:
                item = item.model_copy(update={"sections": rendering.normalize_unknown_sections(item.sections)})
            records_by_reference[mutation.item.reference] = LogicalCacheRecord(
                key=snapshot.key if snapshot is not None else mutation.key, item=item
            )
        return list(records_by_reference.values())

    def _with_snapshot_checkpoint(self, request: ReconcileRequest) -> ReconcileRequest:
        """Resolve an incremental request's ``since`` from the durable checkpoint, if trusted.

        No checkpoint at all, and a checkpoint missing its ``scope``/
        ``label``/``items_observed`` metadata
        (:attr:`_ProviderSnapshotCheckpoint.has_scope_metadata` is ``False``),
        are treated the same: neither can be trusted to resolve an
        incremental ``since``. The latter predates task A1 and cannot be told
        apart from one the pre-A1 label-scope bug wrote for a typo'd label
        against a populated repo -- trusting its watermark could leave
        pre-existing issues whose updates precede that watermark permanently
        unobserved by every subsequent incremental fetch. Either way, this
        falls back to a full reconciliation that (re-)establishes a
        checkpoint this method can trust from then on, and marks the request
        with ``checkpoint_recovery`` so :meth:`_GitHubWorkItemSync.fetch_snapshot`
        fetches closed issues too despite the ``INITIAL`` scope: an issue
        closed (or edited while closed) before this point must be observed
        once during this recovery, or the fresh checkpoint about to be
        written would silently cover it forever after (see
        :class:`ReconcileRequest`'s ``checkpoint_recovery`` field and the P1
        review finding on ``github_work_items.py:605`` this guards). A caller
        who explicitly requests ``ReconcileScope.INITIAL`` from the start
        never reaches this method's ``INCREMENTAL`` branch at all, so a
        genuine from-scratch reconcile keeps its plain open-only fetch.

        Returns:
            The request unchanged for every non-incremental scope; for an
            incremental request with no explicit ``since``, the request
            upgraded to ``INITIAL`` with ``checkpoint_recovery=True`` when no
            trustworthy checkpoint exists, or copied with ``since`` set to
            the checkpoint's watermark otherwise.
        """
        match request.scope:
            case ReconcileScope.INCREMENTAL:
                if request.since:
                    return request
                checkpoint = self._cache._get_snapshot_checkpoint()
                if checkpoint is None or not checkpoint.has_scope_metadata:
                    return request.model_copy(update={"scope": ReconcileScope.INITIAL, "checkpoint_recovery": True})
                return request.model_copy(update={"since": checkpoint.watermark})
            case ReconcileScope.INITIAL | ReconcileScope.LINKED | ReconcileScope.TARGETED:
                return request

    def _advance_snapshot_checkpoint(
        self, scope: ReconcileScope, label: str, watermark: str, outcome: ReconcileOutcome
    ) -> None:
        """Advance the durable global snapshot watermark, but only when it is honest.

        A reconcile that observed zero items and finished without failure is
        not the same fact as "the local cache holds the provider's full item
        set" -- it only means "a reconcile ran" (A-critique.md Sec 3.1, Sec
        3.4: a ``dh backlog refresh --label <typo>`` reconcile durably
        observes zero items and, without this guard, marks the checkpoint as
        if it covered the whole repository). A label-scoped reconcile can
        only ever speak for that label's slice of the provider's items, so it
        must never advance the checkpoint a bare, unlabeled read treats as
        covering everything -- refuse outright rather than record a
        watermark a later unlabeled ``since=`` lookup would wrongly trust.

        A separate "zero items with nothing to explain the zero" gate is not
        implemented here: within the two scopes eligible to advance the
        checkpoint (``INITIAL``/``INCREMENTAL``), ``fetch_snapshot``
        (``_GitHubWorkItemSync.fetch_snapshot``) either completes a real
        GraphQL round trip or raises before a ``ProviderSnapshot`` is ever
        constructed -- there is currently no in-tree path that reaches this
        method with an *unlabeled* zero that was not a genuine round trip.
        ``ProviderSnapshot.pages_fetched`` was evaluated as that
        discriminator and rejected: ``fetch_snapshot`` hard-codes
        ``pages_fetched=1`` for every scope, including ``LINKED``/
        ``TARGETED``, which never fetch a page at all (``issues = []`` is
        assigned directly) -- so the field carries no real pagination signal
        to gate on today.

        ``items_observed`` is recorded from a fresh disk scan taken *after*
        this reconcile's cache writes have already landed (both write phases
        in :meth:`reconcile` run before this method is called), not from
        ``outcome.result.fetched_items``. ``fetched_items`` is only the
        provider-side delta this reconcile fetched -- for ``INCREMENTAL``
        scope that is the changed-since-watermark subset, not the cache's
        total item count -- so it cannot stand in for "how many snapshot
        files does the cache expect to hold". A direct disk count can: every
        item untouched by this reconcile still has its file on disk, and a
        provider-side removal never deletes the local file (see
        ``_plan_item``'s ``unlink`` action, which rewrites the file with a
        cleared issue reference rather than removing it), so the count taken
        here is stable across reconciles except when a file vanishes outside
        the reconcile's control entirely -- exactly the condition
        :meth:`load_records` compares a later load against to detect that
        (backlog #3546 Codex finding 1).
        """
        if not (
            outcome.advance_snapshot_checkpoint
            and outcome.result.conflicts == 0
            and scope in {ReconcileScope.INITIAL, ReconcileScope.INCREMENTAL}
        ):
            return
        if label:
            # A label-scoped observation never covers the full unlabeled item
            # set a bare checkpoint is read to mean -- see the docstring above.
            return
        batch = self._cache._work_item_snapshots()
        self._cache._set_snapshot_checkpoint(
            _ProviderSnapshotCheckpoint(
                watermark=watermark,
                scope=scope.value,
                label=label,
                items_observed=len(batch.snapshots) + len(batch.skipped),
            )
        )
