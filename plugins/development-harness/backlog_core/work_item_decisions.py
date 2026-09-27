"""Command-scoped live work-item observations for provider-backed decisions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from ._capability_gates import require_github_extras, require_request_shaped_listing
from .backend_types import (
    GitHubExtras,
    ListPageRequest,
    RepositoryScopedCachedListing,
    RequestShapedListing,
    WorkItemBackend,
)
from .gh_client import selector_fits_search
from .models import (
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    IssueStatus,
    Output,
    ProviderItem,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileScope,
    parse_issue_number,
)
from .parsing import _find_by_title_substring, find_item, parse_issue_selector
from .reconciliation import provider_item_to_backlog_item
from .status_registry import STATUS_LABEL_PREFIX, pick_primary_status_label

if TYPE_CHECKING:
    from collections.abc import Callable

    from .backend_types import IssueNode

__all__ = ["CommandWorkItems", "DecisionTarget", "ListPage", "WorkItemDecisionContext"]


class CommandWorkItems(BaseModel):
    """One command's provider observation and its derived status facts."""

    provider_items: list[BacklogItem] = Field(default_factory=list)
    status_map: dict[int, IssueStatus] = Field(default_factory=dict)
    from_cache: bool = False
    provider_snapshot: ProviderSnapshot | None = None


class ListPage(CommandWorkItems):
    """One request-shaped page: matched rows plus honest pagination facts.

    ``provider_snapshot`` here always carries exactly the rows this page
    hydrated -- never a whole-history observation -- so a caller can write it
    through a TARGETED reconcile (D7 of the request-shaped-reads design
    brief) without ever passing a partial snapshot into an INCREMENTAL or
    INITIAL reconcile (D6).
    """

    total: int | None = None
    has_more: bool = False
    cached_count: int | None = None
    """Unfiltered count of this repository's cached rows, set only on an
    ``allow_cached`` fallback, so a filter matching none of them is not read
    as an empty cache."""


class DecisionTarget(BaseModel):
    """Provider fact and queued local intent selected for one reference."""

    provider: BacklogItem | None = None
    pending: BacklogItem | None = None
    mutation_base: BacklogItem | None = None
    provider_snapshot: ProviderSnapshot | None = None


class WorkItemDecisionContext:
    """Memoize live work-item reads and keep pending local intent separate."""

    def __init__(
        self, backend: WorkItemBackend, *, repo: str = "", allow_cached: bool = False, output: Output | None = None
    ) -> None:
        """Bind one command to its configured backend and fallback policy."""
        self.backend = backend
        self.repo = repo
        self.allow_cached = allow_cached
        self.output = output
        self._cached: CommandWorkItems | None = None
        self._pending_items: list[BacklogItem] | None = None
        self._targeted: dict[str, ProviderSnapshot] = {}

    def page(
        self,
        request: ListPageRequest,
        *,
        match: Callable[[BacklogItem, ProviderItem], bool],
        force_hydration: bool = False,
    ) -> ListPage:
        """Return one request-shaped page: rows GitHub answered, cheaply narrowed.

        Non-GitHub backends have no provider round trip to shape -- they read
        their own authoritative storage directly (``supports_cached_listing``
        is ``False`` for all of them) and never need a write-through, so this
        applies *match*/*offset*/*limit* locally over the full local list and
        returns an empty ``provider_snapshot`` for the caller to skip
        reconciling.

        Returns:
            The matched page plus an honest ``total``/``has_more``.
        """
        if not self._is_github:
            items = self.backend.list_work_items()
            matched = [item for item in items if match(item, _blank_provider_item(item))]
            page_items, has_more = _slice(matched, request.offset, request.limit)
            return ListPage(
                provider_items=page_items,
                from_cache=bool(getattr(self.backend, "supports_cached_listing", False)),
                total=len(matched),
                has_more=has_more,
            )
        try:
            result = self._pages.fetch_page(
                request.model_copy(update={"repo": self.repo}), match=match, force_hydration=force_hydration
            )
        except BackendUnavailableError as exc:
            if not self.allow_cached:
                raise
            self._warn_cached_fallback(exc)
            cached = self._cached_items()
            matched = [item for item in cached.provider_items if match(item, _blank_provider_item(item))]
            page_items, has_more = _slice(matched, request.offset, request.limit)
            return ListPage(
                provider_items=page_items,
                from_cache=True,
                total=len(matched),
                has_more=has_more,
                cached_count=len(cached.provider_items),
            )
        snapshot = ProviderSnapshot(items=result.items, sync_started_at=result.sync_started_at)
        observed = self._from_snapshot(snapshot)
        return ListPage(
            provider_items=observed.provider_items,
            status_map=observed.status_map,
            provider_snapshot=snapshot,
            total=result.total,
            has_more=result.has_more,
        )

    def select(self, selector: str, *, purpose: Literal["read", "mutation"]) -> DecisionTarget:
        """Select live provider fact and separately indexed queued local intent.

        Returns:
            Read selections return provider fact and snapshot without pending intent or a mutation base.
            Mutation selections may also return pending intent and use pending intent or the provider fact as
            the mutation base.
        """
        exact = parse_issue_selector(selector)
        if not self._is_github:
            read = CommandWorkItems(provider_items=self.backend.list_work_items())
            provider = find_item(read.provider_items, selector)
            snapshot = None
        elif exact is not None:
            reference = f"#{exact}"
            try:
                snapshot = self._targeted_snapshot(reference)
            except BackendUnavailableError as exc:
                if not self.allow_cached:
                    raise
                self._warn_cached_fallback(exc)
                read = self._cached_items()
                provider = find_item(read.provider_items, reference)
                snapshot = None
            else:
                provider = next(
                    (
                        provider_item_to_backlog_item(item)
                        for item in snapshot.items
                        if item.reference == reference and item.exists
                    ),
                    None,
                )
        else:
            provider, snapshot = self._select_by_title(selector)
        pending = None
        mutation_base = None
        if purpose == "mutation":
            pending_selector = (
                provider.reference if provider is not None else f"#{exact}" if exact is not None else selector
            )
            pending = find_item(self.pending(), pending_selector)
            mutation_base = pending or provider
        return DecisionTarget(
            provider=provider, pending=pending, mutation_base=mutation_base, provider_snapshot=snapshot
        )

    def _select_by_title(self, selector: str) -> tuple[BacklogItem | None, ProviderSnapshot | None]:
        """Resolve a non-exact selector against pending intent, then GitHub search (D5).

        Pending (not-yet-created) items are checked first -- a slug or
        string-id selector matching queued intent skips the live search
        entirely (D5 point 4). When search finds no title containing the
        selector -- it was skipped as unsafe (too long, or carrying a quote --
        risk R-B), returned nothing, or returned only tokenized near-misses
        (risk R-A: it can also lag a just-created or just-edited issue) -- a
        titles-only scan of open and closed issues decides. With
        ``allow_cached``, a provider failure anywhere in the lookup, including
        the targeted read of the matched issue, falls back to the cache.

        Returns:
            The matched item and its targeted snapshot (``None`` for a
            pending-only match, which has no provider snapshot).
        """
        pending_match = find_item(self.pending(), selector)
        if pending_match is not None and not pending_match.issue:
            # Not yet created -- no provider row exists to find. select()'s
            # normal pending-journal lookup below still resolves this same
            # match as target.pending/mutation_base; skip the search entirely.
            return None, None
        try:
            candidates = (
                self._pages.search_issues_by_title(self.repo, selector) if selector_fits_search(selector) else []
            )
            match = _find_by_title_substring(
                [provider_item_to_backlog_item(_issue_node_to_provider_item(node)) for node in candidates], selector
            )
            if match is None:
                titles = self._pages.fetch_issue_titles(self.repo)
                match = _find_by_title_substring(
                    [BacklogItem(title=title, issue=f"#{number}") for number, title in titles], selector
                )
            if match is None:
                return None, None
            reference = match.issue
            snapshot = self._targeted_snapshot(reference)
        except BackendUnavailableError as exc:
            if not self.allow_cached:
                raise
            self._warn_cached_fallback(exc)
            read = self._cached_items()
            return find_item(read.provider_items, selector), None
        provider = next(
            (
                provider_item_to_backlog_item(item)
                for item in snapshot.items
                if item.reference == reference and item.exists
            ),
            None,
        )
        return provider, snapshot

    def snapshot_for(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Return a memoized live snapshot compatible with one reconciliation request.

        Only ``TARGETED``/``LINKED`` requests reach this context -- no
        in-tree caller resolves a full-observation snapshot through here
        anymore (see ``page()`` for the request-shaped list path).
        """
        references = [self._canonical_reference(reference) for reference in request.references]
        missing = [reference for reference in references if reference not in self._targeted]
        if missing:
            snapshot = self._github.fetch_snapshot(
                request.model_copy(update={"repo": self.repo, "references": missing, "apply_local_patches": False})
            )
            for reference in missing:
                self._targeted[reference] = self._slice_snapshot(snapshot, [reference])
        items = [self._targeted[reference].items[0] for reference in references]
        started_at = self._targeted[references[0]].sync_started_at if references else ""
        return ProviderSnapshot(items=items, sync_started_at=started_at)

    @property
    def _is_github(self) -> bool:
        return bool(getattr(self.backend, "supports_github_extras", False))

    @property
    def _github(self) -> GitHubExtras:
        return require_github_extras(self.backend, "fetch_snapshot")

    @property
    def _pages(self) -> RequestShapedListing:
        return require_request_shaped_listing(self.backend, "fetch_page")

    def _targeted_snapshot(self, reference: str) -> ProviderSnapshot:
        if reference not in self._targeted:
            snapshot = self._github.fetch_snapshot(
                ReconcileRequest(
                    scope=ReconcileScope.TARGETED, repo=self.repo, references=[reference], apply_local_patches=False
                )
            )
            self._targeted[reference] = self._slice_snapshot(snapshot, [reference])
        return self._targeted[reference]

    def pending(self) -> list[BacklogItem]:
        """Return memoized pending intent scoped to this context's repository."""
        if self._pending_items is None:
            if not self._is_github:
                self._pending_items = []
            elif self.repo:
                self._pending_items = self._github.pending_work_items(self.repo)
            else:
                self._pending_items = self._github.pending_work_items()
        return self._pending_items

    def _cached_items(self) -> CommandWorkItems:
        if self._cached is None:
            pending_identities = {
                identity for item in self.pending() for identity in (item.reference, item.issue) if identity
            }
            cached_items = (
                self.backend.cached_work_items(self.repo)
                if isinstance(self.backend, RepositoryScopedCachedListing)
                else self.backend.list_work_items()
            )
            provider_items = [
                item for item in cached_items if not pending_identities.intersection((item.reference, item.issue))
            ]
            self._cached = CommandWorkItems(provider_items=provider_items, from_cache=True)
        return self._cached

    def cached_records(self) -> list[BacklogItem]:
        """Return this repository's provider-private cached rows, no live read.

        Used by callers that only need to detect a local collision (e.g. a
        slug reference) and must not spend a live round trip to do it --
        provider-linked rows can never collide with a slug reference, since
        every provider reference is always ``#N`` (see ``_resolve_reference``).
        """
        return self._cached_items().provider_items

    def _from_snapshot(self, snapshot: ProviderSnapshot) -> CommandWorkItems:
        existing = [item for item in snapshot.items if item.exists]
        provider_items = [provider_item_to_backlog_item(item) for item in existing]
        status_map = {
            number: IssueStatus(
                status=pick_primary_status_label([
                    label for label in item.labels if label.startswith(STATUS_LABEL_PREFIX)
                ]),
                milestone=item.milestone,
                state=item.state,
            )
            for item in existing
            if (number := parse_issue_number(item.reference)) is not None
        }
        return CommandWorkItems(provider_items=provider_items, status_map=status_map, provider_snapshot=snapshot)

    @staticmethod
    def _slice_snapshot(snapshot: ProviderSnapshot | None, references: list[str]) -> ProviderSnapshot:
        if snapshot is None:
            raise BacklogError("A live provider snapshot is required for reconciliation")
        by_reference = {item.reference: item for item in snapshot.items}
        items = [
            by_reference.get(
                reference,
                ProviderItem(
                    provider_id="",
                    reference=reference,
                    title="",
                    body="",
                    state="",
                    labels=[],
                    revision="",
                    exists=False,
                ),
            )
            for reference in references
        ]
        return ProviderSnapshot(
            items=items, sync_started_at=snapshot.sync_started_at, pages_fetched=snapshot.pages_fetched
        )

    @staticmethod
    def _canonical_reference(reference: str) -> str:
        parsed = parse_issue_selector(reference)
        return f"#{parsed}" if parsed is not None else reference

    def _warn_cached_fallback(self, exc: BacklogError) -> None:
        if self.output is not None:
            self.output.warn(f"Live provider read failed; using cached work items: {exc}")


def _blank_provider_item(item: BacklogItem) -> ProviderItem:
    """Return a placeholder ProviderItem for a non-GitHub backend's own record.

    Non-GitHub backends never produce a real ``ProviderItem`` (they have no
    GraphQL milestone/label wire shape) -- ``match`` callables that need
    provider-only fields (e.g. milestone) simply see empty defaults here,
    matching today's non-GitHub behaviour of not resolving those fields live.
    """
    return ProviderItem(
        provider_id="",
        reference=item.reference,
        title=item.title,
        body="",
        state=item.metadata.status or "",
        labels=list(item.metadata.labels),
        revision="",
    )


def _issue_node_to_provider_item(node: IssueNode) -> ProviderItem:
    """Build an unhydrated ``ProviderItem`` from a raw search/list issue node.

    Returns:
        The provider item, carrying the node's raw (unhydrated) body.
    """
    milestone = node["milestone"]
    return ProviderItem(
        provider_id=str(node["id"]),
        reference=f"#{node['number']}",
        title=str(node["title"]),
        body=str(node.get("body", "")),
        state=str(node["state"]),
        labels=[label["name"] for label in node["labels"]],
        revision="",
        milestone=milestone["title"] if milestone else "",
    )


def _slice(matched: list[BacklogItem], offset: int, limit: int) -> tuple[list[BacklogItem], bool]:
    """Apply offset/limit to an already-fully-known local match list.

    Returns:
        The page slice and an exact ``has_more``.
    """
    after_offset = matched[offset:]
    if limit > 0:
        return after_offset[:limit], len(after_offset) > limit
    return after_offset, False
