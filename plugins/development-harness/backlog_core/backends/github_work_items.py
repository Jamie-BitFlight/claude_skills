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

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from github import GithubException

from backlog_core import gh_client, rendering
from backlog_core.backend_types import ListPageResult
from backlog_core.backends._github_work_item_versions import (
    WorkItemHead,
    WorkItemVersion,
    find_work_item_comment,
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
    HEAD_FIELDS,
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
    GitHubMutationOutcomeUnknownError,
    GroomingIntent,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    ValidationError,
)
from backlog_core.reconciliation import (
    ActionResult,
    LogicalCacheRecord,
    ReconcileExecution,
    ReconcileOutcome,
    finalize_reconciliation,
    provider_item_to_backlog_item,
    reconcile_backlog,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from github.Repository import Repository

    from backlog_core.backend_types import AddedCommentNode, IssueCommentNode, IssueNode, ListPageRequest
    from backlog_core.file_cache import FileCache
    from backlog_core.file_cache_state import _PendingWorkItemMutation

#: Prefix identifying a priority label on a raw GitHub issue node -- present
#: whenever ``create_issue_for_item`` created the issue, and the sole signal
#: :meth:`_GitHubWorkItemSync.fetch_page` can check without hydration to know
#: a candidate's ``section`` (== ``metadata.priority``) is non-empty (D2').
_PRIORITY_LABEL_PREFIX = "priority:"

# Bounded aliased GraphQL batch size for issue-node and comment-node batches,
# which carry small metadata fields rather than full content bodies.
_TARGET_BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Compliance -- contract for the future migrate command (design doc §"one
# new requirement"). check_work_item_compliance is a pure function: given
# one issue's labels and head record, it reports whether they meet the
# current item-fields-in-head-record standard, with no I/O of its own.
# _GitHubWorkItemSync.check_compliance_for_issue and .upgrade_work_item are
# the live counterparts a migrate command drives directly.
# ---------------------------------------------------------------------------

#: No head record exists for this issue at all (or the stored record is
#: malformed/rejected by ``parse_work_item_head`` -- fail-closed the same way
#: ``parse_work_item_head`` itself does), or the live wrapper found an
#: existing head that no longer matches the issue's current root (D5's
#: "stale head" case) -- either way there is no head to validate the audit
#: comment against, so the two are reported identically.
NO_HEAD = "no_head"
#: A head exists but its raw stored JSON has no ``"fields"`` key at all --
#: the shape an older plugin version (predating this design) writes. Checked
#: against the raw dict, not the parsed ``WorkItemHead``, because pydantic's
#: ``extra="ignore"`` default makes an absent key and an explicit ``{}``
#: indistinguishable once parsed (see design doc R1).
HEAD_WITHOUT_FIELDS_MAP = "head_without_fields_map"
#: The head has a ``fields`` map, but it is missing at least one of the
#: current ``models.HEAD_FIELDS`` keys (a partial/incomplete write).
FIELDS_MISSING = "fields_missing"
#: The issue's current priority:/type:/status: labels do not match the set
#: ``gh_client._desired_label_set`` would compute from the head's field
#: values -- i.e. a human or an out-of-band write moved a label without the
#: head (or vice versa) catching up.
LABELS_OUT_OF_STEP = "labels_out_of_step"
#: The head's referenced audit comment cannot be resolved and validated
#: against it (deleted, edited, or otherwise fails ``parse_work_item_comment``).
MISSING_AUDIT_COMMENT = "missing_audit_comment"


@dataclass(frozen=True)
class ComplianceReport:
    """Whether one GitHub issue's labels and head record meet the current standard.

    ``defects`` is empty if and only if ``compliant`` is True. Every
    applicable defect is reported -- this does not short-circuit on the
    first one -- so a caller (the migrate command) can plan a single
    corrective write that addresses everything at once.
    """

    compliant: bool
    defects: tuple[str, ...]


def check_work_item_compliance(
    *, labels: Sequence[str], head_content: str | None, comment_resolved: bool
) -> ComplianceReport:
    """Report whether one issue's labels and head record meet the current standard.

    Pure function: no I/O, no exceptions raised for any input shape --
    every failure mode this function itself needs to distinguish is
    expressed as a defect in the returned report, not an exception. See
    :meth:`_GitHubWorkItemSync.check_compliance_for_issue` for the live
    counterpart that fetches these three inputs for one real issue.

    Args:
        labels: The issue's current label names.
        head_content: The head record's raw stored JSON (``ContentRecord.content``),
            or ``None`` when the issue has no head record at all, or when the
            live caller found one but it no longer matches the issue's
            current root (see ``NO_HEAD``'s docstring) -- pass the raw
            string, not a pre-parsed ``WorkItemHead``: distinguishing
            :data:`HEAD_WITHOUT_FIELDS_MAP` from :data:`FIELDS_MISSING`
            requires inspecting the raw dict for whether the ``"fields"``
            key is present at all, which the parsed model cannot tell you
            (pydantic's ``extra="ignore"`` default hides it).
        comment_resolved: Whether the caller has already confirmed, via
            ``parse_work_item_comment``, that the head's referenced audit
            comment still exists and validates. A caller uninterested in
            this particular defect may pass ``False`` unconditionally --
            that only ever adds a false-positive :data:`MISSING_AUDIT_COMMENT`,
            never masks a real compliance gap, so it is a safe default.

    Returns:
        A report naming every applicable defect, or ``compliant=True`` with
        an empty ``defects`` tuple.
    """
    if head_content is None:
        return ComplianceReport(compliant=False, defects=(NO_HEAD,))
    try:
        raw = json.loads(head_content)
        head = parse_work_item_head(head_content)
    except (json.JSONDecodeError, ContentUnavailableError):
        return ComplianceReport(compliant=False, defects=(NO_HEAD,))
    if not isinstance(raw, dict):
        return ComplianceReport(compliant=False, defects=(NO_HEAD,))

    defects: list[str] = []
    if "fields" not in raw:
        defects.append(HEAD_WITHOUT_FIELDS_MAP)
    elif set(HEAD_FIELDS) - set(head.fields):
        defects.append(FIELDS_MISSING)

    desired = gh_client._desired_label_set(
        list(labels), head.fields.get("priority", ""), head.fields.get("item_type", ""), head.fields.get("status", "")
    )
    if set(desired) != set(labels):
        defects.append(LABELS_OUT_OF_STEP)

    if not comment_resolved:
        defects.append(MISSING_AUDIT_COMMENT)

    return ComplianceReport(compliant=not defects, defects=tuple(defects))


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

    def _fetch_issues_page_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        *,
        states: list[str],
        labels: list[str] | None = None,
        first: int = 100,
        after: str | None = None,
        light: bool = False,
    ) -> gh_client.IssuesPage: ...

    def _fetch_targeted_issues(
        self, repo: Repository, owner: str, repo_name: str, references: list[str]
    ) -> dict[str, IssueNode | None]: ...

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> AddedCommentNode: ...

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode: ...

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int, *, latest: int | None = None
    ) -> list[IssueCommentNode]: ...


class _ReconcileProvider(Protocol):
    """Provider snapshot and patch operations the reconciliation cycle drives.

    :class:`GitHubBackend` satisfies this Protocol structurally, keeping the
    snapshot and patch steps substitutable on the composing backend.
    """

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot: ...
    def _apply_patches(self, patches: list[ProviderPatch], repo: str = "") -> list[PatchResult]: ...


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

    def _classify_page_candidates(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        issues: list[IssueNode],
        *,
        match: Callable[[BacklogItem, ProviderItem], bool],
        force_hydration: bool,
    ) -> list[tuple[IssueNode, ProviderItem, bool]]:
        """Hydrate as needed (D2') and match one GraphQL page's issues.

        Returns:
            Each matching raw node, in page order, with its provider item and
            whether that item was hydrated (``False`` for a row matched on the
            label shortcut, whose item carries the raw issue body).
        """
        needs_hydration = {
            issue["number"]: force_hydration
            or not any(label["name"].startswith(_PRIORITY_LABEL_PREFIX) for label in issue["labels"])
            for issue in issues
        }
        hydrate_now = [issue for issue in issues if needs_hydration[issue["number"]]]
        heads, comments = self._work_item_contexts(repo, hydrate_now) if hydrate_now else ({}, {})
        matched: list[tuple[IssueNode, ProviderItem, bool]] = []
        for issue in issues:
            use_content = needs_hydration[issue["number"]]
            candidate = self.provider_item_from_issue(
                repo, owner, repo_name, issue, heads if use_content else {}, comments if use_content else {}
            )
            if match(provider_item_to_backlog_item(candidate), candidate):
                matched.append((issue, candidate, use_content))
        return matched

    def fetch_page(
        self, request: ListPageRequest, *, match: Callable[[BacklogItem, ProviderItem], bool], force_hydration: bool
    ) -> ListPageResult:
        """Walk issues in ``UPDATED_AT DESC`` order, stopping as soon as enough match.

        Implements D3/D4 of the request-shaped-reads design brief: the page
        size starts at ``min(100, offset + limit + 1)`` and doubles each round
        (capped at 100) while matches stay short, and the walk stops the
        moment it has found match number ``offset + limit + 1`` -- or, when
        ``request.limit`` is 0, once the connection is exhausted.

        A candidate is hydrated during the walk only when *force_hydration*
        is set or it carries no ``priority:`` label (D2') -- an issue with
        that label always has a non-empty ``section``, so *match* can decide
        that part of the base "has a section" rule without reading its body.
        A returned row that matched on that shortcut is hydrated once more
        before return: a caller displaying or caching a row needs its real,
        tracked content, not the raw issue body the shortcut used only to
        decide inclusion cheaply. A row hydrated during the walk keeps that
        provider item and is never read again. A count-only request
        (``request.hydrate`` false) skips that final pass. Hydration
        is batched per GraphQL page (one ``_work_item_contexts`` call per
        page's candidates that need it), not per issue, so a broken head on
        an unrelated issue never touched by this walk cannot abort it
        (groom risk R1) and a whole-set force_hydration walk still costs one
        batch per page rather than one per issue.

        Returns:
            The matched, fully hydrated page slice plus an honest
            ``has_more``/``total`` (see :class:`ListPageResult`).
        """
        sync_started_at = datetime.now(UTC).isoformat()
        repo = self._issues.get_github(request.repo)
        owner, repo_name = repo.full_name.split("/", 1)
        states = ["OPEN", "CLOSED"] if request.include_closed else ["OPEN"]
        labels = request.labels or None
        target = request.offset + request.limit + 1 if request.limit > 0 else None
        page_size = min(100, target) if target else 100

        matched: list[tuple[IssueNode, ProviderItem, bool]] = []
        cursor: str | None = None
        has_next_page = True
        while True:
            page = self._issues._fetch_issues_page_graphql(
                repo, owner, repo_name, states=states, labels=labels, first=page_size, after=cursor, light=True
            )
            matched.extend(
                self._classify_page_candidates(
                    repo, owner, repo_name, page["issues"], match=match, force_hydration=force_hydration
                )
            )
            has_next_page = page["has_next_page"]
            cursor = page["end_cursor"]
            if target is not None and len(matched) >= target:
                break
            if not has_next_page:
                break
            page_size = min(100, page_size * 2)

        after_offset = matched[request.offset :]
        if request.limit > 0:
            has_more = len(after_offset) > request.limit
            page_slice = after_offset[: request.limit]
        else:
            has_more = False
            page_slice = after_offset

        # Final hydration pass, only for returned rows that matched on the
        # label shortcut and so still carry the raw issue body.
        shortcut = [issue for issue, _, hydrated in page_slice if not hydrated] if request.hydrate else []
        heads, comments = self._work_item_contexts(repo, shortcut) if shortcut else ({}, {})
        items = [
            item
            if hydrated or not request.hydrate
            else self.provider_item_from_issue(repo, owner, repo_name, issue, heads, comments)
            for issue, item, hydrated in page_slice
        ]

        # Only an exhausted walk knows the filtered total. totalCount counts
        # rows *match* would reject, and every list caller's *match* carries
        # the local "has a section" rule, so it is never the filtered total.
        total = None if has_next_page else len(matched)

        return ListPageResult(items=items, has_more=has_more, total=total, sync_started_at=sync_started_at)

    def apply_patches(self, patches: list[ProviderPatch], repo: str = "") -> list[PatchResult]:
        """Apply optimistic GitHub body patches and return one outcome per patch.

        Args:
            patches: Provider patches derived from the reconciliation snapshot.
            repo: Repository slug used to fetch that snapshot.

        Returns:
            Patch results indexed by the stable provider reference.
        """
        if not patches:
            return []
        repository = self._issues.get_github(repo)
        owner, repo_name = repository.full_name.split("/", 1)
        try:
            current_by_reference = self._issues._fetch_targeted_issues(
                repository, owner, repo_name, [patch.reference for patch in patches]
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
                current, head_record, root = self.work_item_version(repository, owner, repo_name, issue)
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
            results.append(
                self._apply_one_patch(repository, owner, repo_name, patch, issue, current, head_record, root)
            )
        return results

    def _audit_comment_id(self, repository: Repository, issue: IssueNode, revision: str, body: str) -> str:
        """Return the audit comment for this revision and body, posting one only if none exists.

        A comment from an earlier write whose outcome was unknown may already be on the issue with
        no head pointing at it; reusing it keeps a retried reconcile from posting a duplicate.

        Returns:
            The audit comment's node id (empty when GitHub answered the post with none).
        """
        owner, repo_name = repository.full_name.split("/", 1)
        # Only the newest gh_client.RECENT_COMMENT_WINDOW comments are searched; see its ceiling note.
        recent = self._issues._fetch_issue_comments_graphql(
            repository, owner, repo_name, issue["number"], latest=gh_client.RECENT_COMMENT_WINDOW
        )
        if (existing := find_work_item_comment(recent, revision, body)) is not None:
            return existing.id
        return self._issues._add_comment_graphql(repository, issue["id"], render_work_item_comment(revision, body)).id

    def _apply_one_patch(
        self,
        repository: Repository,
        owner: str,
        repo_name: str,
        patch: ProviderPatch,
        issue: IssueNode,
        current: WorkItemVersion,
        head_record: ContentRecord | None,
        root: str,
    ) -> PatchResult:
        """Mirror labels, then write the audit comment and/or head for one patch (design D3).

        Split out of ``apply_patches`` to keep that loop's complexity within
        the project's ceiling -- this is the per-patch body of steps 1-3, run
        only once ``apply_patches`` has confirmed *patch* is still current
        (``expected_revision`` matched the freshly fetched issue).

        Returns:
            The patch's outcome: ``error``/``conflict`` from either the label
            mirror or the comment/head write, or ``applied`` (including the
            no-op case where neither the body nor the fields actually changed).

        Raises:
            GitHubMutationOutcomeUnknownError: When a label or audit-comment write timed out.
                Recording an error instead would let a later reconcile repeat the write.
        """
        # patch.fields is None means "do not touch fields" (see ProviderPatch's
        # docstring) -- distinct from an empty dict, which is a caller-supplied
        # fields map that happens to be empty. Neither the label mirror nor the
        # fields_changed check below run for a body-only patch that never set
        # fields at all (e.g. one built directly rather than through
        # reconciliation._candidate, which always sets it when a patch is
        # emitted).
        touches_fields = patch.fields is not None
        patch_fields = patch.fields or {}
        if touches_fields:
            # Design D3 step 1: labels first, before either the comment or the
            # head are touched. A label write failure here leaves the head
            # untouched and the mutation queued for retry -- see the ordering
            # rationale in the design doc's D3 section.
            try:
                gh_client.mirror_work_item_labels(
                    repository,
                    owner,
                    repo_name,
                    issue,
                    priority=patch_fields.get("priority", ""),
                    item_type=patch_fields.get("item_type", ""),
                    status=patch_fields.get("status", ""),
                )
            except GitHubMutationOutcomeUnknownError:
                raise
            except (GithubException, BacklogError) as exc:
                return PatchResult(
                    provider_id=patch.provider_id,
                    reference=patch.reference,
                    status="error",
                    message=f"GitHub work-item label mirror failed: {exc}",
                )

        current_head = parse_work_item_head(head_record.content) if head_record is not None else None
        body_changed = current.body.replace("\r\n", "\n") != patch.body.replace("\r\n", "\n")
        fields_changed = touches_fields and (current_head is None or current_head.fields != patch_fields)
        if not body_changed and not fields_changed:
            return PatchResult(
                provider_id=patch.provider_id, reference=patch.reference, status="applied", revision=current.revision
            )

        # Design D3 step 2/3: reuse the existing head's body/digest/comment_id
        # verbatim for a field-only change on a valid (non-stale) head -- no
        # new audit comment, so a plan/status/etc. update never floods the
        # issue with comments. A body change, or no valid head to reuse,
        # uses an audit comment -- reusing one already posted for this exact
        # revision and body (see _audit_comment_id) before posting a fresh one.
        try:
            if (
                current_head is not None
                and head_record is not None
                and current.revision == head_record.revision
                and not body_changed
            ):
                new_head = current_head.model_copy(update={"fields": patch_fields})
            else:
                comment_id = self._audit_comment_id(repository, issue, current.revision, patch.body)
                if not comment_id:
                    return PatchResult(
                        provider_id=patch.provider_id,
                        reference=patch.reference,
                        status="error",
                        message="GitHub work-item audit comment response was invalid",
                    )
                # A body-only patch (touches_fields False) carries forward the
                # existing head's fields unchanged, rather than wiping them to
                # {} -- "do not touch fields" applies here too, not only to
                # the fields_changed/label-mirror checks above.
                carried_fields = patch_fields if touches_fields else (current_head.fields if current_head else {})
                new_head = WorkItemHead.create(
                    patch.reference, current.revision, root, patch.body, comment_id, fields=carried_fields
                )
            written = self._contents().put(
                ContentWrite(
                    reference=work_item_head_ref(patch.reference),
                    content=new_head.model_dump_json(),
                    expected_revision=head_record.revision if head_record is not None else "",
                    create_only=head_record is None,
                )
            )
        except GitHubMutationOutcomeUnknownError:
            raise
        except ContentConflictError as exc:
            return PatchResult(
                provider_id=patch.provider_id, reference=patch.reference, status="conflict", message=str(exc)
            )
        except (BacklogError, ContentUnavailableError) as exc:
            return PatchResult(
                provider_id=patch.provider_id, reference=patch.reference, status="error", message=str(exc)
            )
        return PatchResult(
            provider_id=patch.provider_id, reference=patch.reference, status="applied", revision=written.revision
        )

    def check_compliance_for_issue(
        self, repo: Repository, owner: str, repo_name: str, issue: IssueNode
    ) -> ComplianceReport:
        """Check one live issue's labels and head record against the current standard.

        Live counterpart of :func:`check_work_item_compliance` -- resolves
        the three inputs that function needs (labels, raw head content,
        whether the audit comment validates) for one real issue, then
        delegates the actual judgement to it.

        Returns:
            See :func:`check_work_item_compliance`. A head that exists but no
            longer matches the issue's current root (D5's "stale head" case)
            is reported identically to :data:`NO_HEAD` -- its fields are
            still readable by ``_compose`` (D2), but its audit comment cannot
            be validated against a root it no longer matches, so treating it
            as compliant here would understate what a migrate command still
            needs to do.
        """
        reference = f"#{issue['number']}"
        labels = [label["name"] for label in issue["labels"]]
        root = root_revision(reference, issue["id"], issue["body"])
        try:
            head_record = self._contents().get(work_item_head_ref(reference))
        except ContentNotFoundError:
            return check_work_item_compliance(labels=labels, head_content=None, comment_resolved=False)
        try:
            head = parse_work_item_head(head_record.content)
        except ContentUnavailableError:
            return check_work_item_compliance(labels=labels, head_content=None, comment_resolved=False)
        if head.issue_reference != reference or head.root_revision != root:
            return check_work_item_compliance(labels=labels, head_content=None, comment_resolved=False)
        try:
            comment = self._issues._fetch_comment_by_id_graphql(repo, head.comment_id)
            parse_work_item_comment(head, comment)
        except (BacklogError, ContentUnavailableError):
            comment_resolved = False
        else:
            comment_resolved = True
        return check_work_item_compliance(
            labels=labels, head_content=head_record.content, comment_resolved=comment_resolved
        )

    def upgrade_work_item(
        self, repo: Repository, owner: str, repo_name: str, issue: IssueNode, *, fields: dict[str, str]
    ) -> PatchResult:
        """Bring one issue's labels and head record to the current standard.

        For the future migrate command (design doc, "one new requirement").
        Writes in exactly ``apply_patches``'s order -- labels, then an audit
        comment only if one is actually needed, then the head record -- by
        building a :class:`~backlog_core.models.ProviderPatch` whose body is
        the issue's own current (unaudited-if-none) body and delegating to
        :meth:`_apply_one_patch`, the same per-patch step ``apply_patches``
        uses. Idempotent: run against an issue :meth:`check_compliance_for_issue`
        already reports compliant for these *fields*, this makes zero writes
        -- the body is unchanged (so no new comment), the fields already
        match (so no head write), and ``mirror_work_item_labels`` only writes
        when the desired label set actually differs from the current one.

        Args:
            repo: PyGithub Repository to operate on.
            owner: Repository owner login.
            repo_name: Repository name.
            issue: The issue's current IssueNode (already fetched by the caller).
            fields: The full desired head-field map (see
                :data:`~backlog_core.models.HEAD_FIELDS`) this issue should
                carry -- the migrate command derives this from whatever
                source it trusts (the existing head, or the D6 label-derived
                legacy fallback for an issue with none).

        Returns:
            The single outcome for this issue, exactly like one entry of
            ``apply_patches``'s return value.
        """
        current, head_record, root = self.work_item_version(repo, owner, repo_name, issue)
        patch = ProviderPatch(
            provider_id=issue["id"],
            reference=f"#{issue['number']}",
            expected_revision=current.revision,
            body=current.body,
            fields=fields,
        )
        return self._apply_one_patch(repo, owner, repo_name, patch, issue, current, head_record, root)

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
        version, head_record, _root = self.work_item_version(repo, owner, repo_name, issue, heads, comments)
        # A stale head (root_revision no longer matches, per work_item_version)
        # still carries its last-known head fields -- see design D1/D2: a human
        # body rewrite invalidates the head's *body*, not its structured fields.
        fields = parse_work_item_head(head_record.content).fields if head_record is not None else None
        return ProviderItem(
            provider_id=issue["id"],
            reference=f"#{issue['number']}",
            title=issue["title"],
            body=version.body,
            state=issue["state"],
            labels=[label["name"] for label in issue["labels"]],
            revision=version.revision,
            milestone=issue["milestone"]["title"] if issue["milestone"] else "",
            fields=fields,
            created_at=issue["createdAt"],
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

    def __init__(self, cache: FileCache, provider: _ReconcileProvider, *, default_repo: str = "") -> None:
        """Bind the provider-private cache to the snapshot and patch seam.

        Args:
            cache: Provider-private durable cache.
            provider: Snapshot and patch operations, resolved at call time.
            default_repo: Repository assigned to writes and legacy unscoped intent.
        """
        self._cache = cache
        self._provider = provider
        self._default_repo = default_repo
        self._cache._set_default_repo(default_repo)
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
        self._reconcile_locks: dict[str, Lock] = {}
        self._reconcile_locks_lock = Lock()

    def list_work_items(self, repo: str = "") -> list[BacklogItem]:
        """List work items from the provider-private cache.

        Returns:
            Persisted work items.
        """
        return [record.item for record in self.load_records(repo=repo or self._default_repo)]

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

    def pending_work_items(self, repo: str = "") -> list[BacklogItem]:
        """Return copied queued work-item intent without cached provider rows."""
        selected_repo = repo or self._default_repo
        return [
            mutation.item.model_copy(deep=True)
            for mutation in self._cache._pending_work_item_mutations(selected_repo, default_repo=self._default_repo)
        ]

    def get_work_item(self, reference: str) -> BacklogItem:
        """Get a cached work item by stable reference.

        Returns:
            The matching work item.

        Raises:
            KeyError: If no cached work item carries the reference.
        """
        for record in self.load_records(repo=self._default_repo):
            if reference == record.item.reference:
                return record.item
        raise KeyError(reference)

    def put_work_item(self, item: BacklogItem, repo: str = "", grooming_intent: GroomingIntent | None = None) -> None:
        """Persist a work-item intent for provider reconciliation.

        ``item.reference`` is guaranteed non-empty by
        :class:`~backlog_core.models.BacklogItem`'s ``_sync_metadata``
        validator, which self-heals it at construction time — no fallback
        derivation is needed here. A copy is queued (rather than ``item``
        itself) so a caller mutating its own ``item`` after this call cannot
        retroactively alter the queued mutation.

        Empty ``repo`` selects the backend's configured repository. Repository
        identity is persisted with the mutation so equal issue references in
        different repositories remain independent.
        """
        self._cache._queue_work_item(item.reference, item.model_copy(), repo or self._default_repo, grooming_intent)

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
        """Reconcile one repository with exclusive provider-patch ownership.

        Returns:
            Completed reconciliation counts with changed logical references.
        """
        repo = request.repo or self._default_repo
        with self._reconcile_lock(repo):
            return self._reconcile(request, snapshot=snapshot)

    def _reconcile_lock(self, repo: str) -> Lock:
        """Return the reconciliation lock for one repository."""
        with self._reconcile_locks_lock:
            lock = self._reconcile_locks.get(repo)
            if lock is None:
                lock = Lock()
                self._reconcile_locks[repo] = lock
            return lock

    def _reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult:
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
                raise ValidationError(f"Supplied snapshot is missing requested references: {sorted(missing)}")
        pending_work_items = self._cache._pending_work_item_mutations(
            effective_request.repo or self._default_repo, default_repo=self._default_repo
        )
        plan = reconcile_backlog(
            self.load_records(pending_work_items, repo=effective_request.repo or self._default_repo),
            snapshot,
            effective_request,
        )
        cache_results: list[ActionResult] = []
        for action in (entry for entry in plan.cache_actions if entry.phase == "before_provider"):
            try:
                self._cache._save_work_item_snapshot(
                    action.key, action.record.item, repo=effective_request.repo or self._default_repo
                )
            except OSError:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="error"))
            else:
                cache_results.append(ActionResult(key=action.key, phase=action.phase, status="applied"))

        patch_results = (
            self._provider._apply_patches(plan.provider_patches, effective_request.repo or self._default_repo)
            if effective_request.apply_local_patches and plan.provider_patches
            else []
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
                self._cache._save_work_item_snapshot(
                    action.key, item, repo=effective_request.repo or self._default_repo
                )
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
            effective_request.scope,
            effective_request.label,
            plan.snapshot_checkpoint,
            outcome,
            repo=effective_request.repo or self._default_repo,
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
        self, pending_work_items: Sequence[_PendingWorkItemMutation] | None = None, *, repo: str = ""
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
        selected_repo = repo or self._default_repo
        batch = self._cache._work_item_snapshots(selected_repo, default_repo=self._default_repo)
        self._last_skipped_snapshots = batch.skipped
        checkpoint = (
            self._cache._get_snapshot_checkpoint()
            if selected_repo == self._default_repo
            else self._cache._get_snapshot_checkpoint(selected_repo)
        )
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
            pending_work_items
            if pending_work_items is not None
            else self._cache._pending_work_item_mutations(selected_repo, default_repo=self._default_repo)
        ):
            snapshot = records_by_reference.get(mutation.item.reference)
            item = mutation.item
            if item.sections:
                item = item.model_copy(update={"sections": rendering.normalize_unknown_sections(item.sections)})
            records_by_reference[mutation.item.reference] = LogicalCacheRecord(
                key=snapshot.key if snapshot is not None else mutation.key, item=item, pending=True
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
                selected_repo = request.repo or self._default_repo
                checkpoint = (
                    self._cache._get_snapshot_checkpoint()
                    if selected_repo == self._default_repo
                    else self._cache._get_snapshot_checkpoint(selected_repo)
                )
                if checkpoint is None or not checkpoint.has_scope_metadata:
                    return request.model_copy(update={"scope": ReconcileScope.INITIAL, "checkpoint_recovery": True})
                return request.model_copy(update={"since": checkpoint.watermark})
            case ReconcileScope.INITIAL | ReconcileScope.LINKED | ReconcileScope.TARGETED:
                return request

    def _advance_snapshot_checkpoint(
        self, scope: ReconcileScope, label: str, watermark: str, outcome: ReconcileOutcome, *, repo: str = ""
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
        selected_repo = repo or self._default_repo
        batch = self._cache._work_item_snapshots(selected_repo, default_repo=self._default_repo)
        self._cache._set_snapshot_checkpoint(
            _ProviderSnapshotCheckpoint(
                watermark=watermark,
                scope=scope.value,
                label=label,
                items_observed=len(batch.snapshots) + len(batch.skipped),
            ),
            repo=selected_repo,
        )
