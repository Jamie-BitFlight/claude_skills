"""Command-scoped live work-item observations for provider-backed decisions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ._capability_gates import require_github_extras
from .backend_types import GitHubExtras, WorkItemBackend
from .models import (
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
from .parsing import find_item, parse_issue_selector
from .reconciliation import provider_item_to_backlog_item
from .status_registry import STATUS_LABEL_PREFIX, pick_primary_status_label

__all__ = ["CommandWorkItems", "DecisionTarget", "WorkItemDecisionContext"]


class CommandWorkItems(BaseModel):
    """One command's provider observation and its derived status facts."""

    provider_items: list[BacklogItem] = Field(default_factory=list)
    status_map: dict[int, IssueStatus] = Field(default_factory=dict)
    from_cache: bool = False
    provider_snapshot: ProviderSnapshot | None = None


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
        self._bulk: CommandWorkItems | None = None
        self._cached: CommandWorkItems | None = None
        self._pending_items: list[BacklogItem] | None = None
        self._targeted: dict[str, ProviderSnapshot] = {}

    def all(self) -> CommandWorkItems:
        """Return one memoized complete provider observation for this command."""
        if self._bulk is not None:
            return self._bulk
        if not self._is_github:
            self._bulk = CommandWorkItems(provider_items=self.backend.list_work_items())
            return self._bulk
        request = ReconcileRequest(scope=ReconcileScope.INCREMENTAL, since="", apply_local_patches=False)
        try:
            snapshot = self._github.fetch_snapshot(request)
        except BacklogError as exc:
            if not self.allow_cached:
                raise
            self._warn_cached_fallback(exc)
            self._bulk = self._cached_items()
            return self._bulk
        self._bulk = self._from_snapshot(snapshot)
        return self._bulk

    def select(self, selector: str, *, purpose: Literal["read", "mutation"]) -> DecisionTarget:
        """Select live provider fact and separately indexed queued local intent.

        Returns:
            Provider fact, pending intent, and mutation base for the selector.
        """
        del purpose
        exact = parse_issue_selector(selector)
        if self._bulk is not None or not self._is_github or exact is None:
            read = self.all()
            provider = find_item(read.provider_items, selector)
            snapshot = (
                self._slice_snapshot(read.provider_snapshot, [provider.issue])
                if provider is not None and read.provider_snapshot is not None
                else None
            )
        else:
            reference = f"#{exact}"
            try:
                snapshot = self._targeted_snapshot(reference)
            except BacklogError as exc:
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
        pending = find_item(self._pending(), f"#{exact}" if exact is not None else selector)
        return DecisionTarget(
            provider=provider, pending=pending, mutation_base=pending or provider, provider_snapshot=snapshot
        )

    def snapshot_for(self, request: ReconcileRequest) -> ProviderSnapshot:
        """Return a memoized live snapshot compatible with one reconciliation request."""
        if request.scope in {ReconcileScope.INITIAL, ReconcileScope.INCREMENTAL}:
            snapshot = self.all().provider_snapshot
            if snapshot is None:
                raise BacklogError("A live provider snapshot is required for reconciliation")
            return snapshot
        references = [self._canonical_reference(reference) for reference in request.references]
        if self._bulk is not None:
            return self._slice_snapshot(self._bulk.provider_snapshot, references)
        missing = [reference for reference in references if reference not in self._targeted]
        if missing:
            snapshot = self._github.fetch_snapshot(
                request.model_copy(update={"references": missing, "apply_local_patches": False})
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

    def _targeted_snapshot(self, reference: str) -> ProviderSnapshot:
        if reference not in self._targeted:
            snapshot = self._github.fetch_snapshot(
                ReconcileRequest(scope=ReconcileScope.TARGETED, references=[reference], apply_local_patches=False)
            )
            self._targeted[reference] = self._slice_snapshot(snapshot, [reference])
        return self._targeted[reference]

    def _pending(self) -> list[BacklogItem]:
        if self._pending_items is None:
            self._pending_items = self._github.pending_work_items() if self._is_github else []
        return self._pending_items

    def _cached_items(self) -> CommandWorkItems:
        if self._cached is None:
            self._cached = CommandWorkItems(provider_items=self.backend.list_work_items(), from_cache=True)
        return self._cached

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
