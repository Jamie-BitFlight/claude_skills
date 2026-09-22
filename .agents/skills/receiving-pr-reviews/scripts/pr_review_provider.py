"""Provider seam for complete review snapshots and validated review actions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pr_review_models import ChangeRequestTarget, ReviewAction, ReviewActionResult, ReviewSnapshot

__all__ = ["ProviderResponseError", "ReviewProvider"]


class ProviderResponseError(RuntimeError):
    """A provider process succeeded but its response did not confirm the requested operation."""


@runtime_checkable
class ReviewProvider(Protocol):
    """Deep interface hiding forge transport, pagination, validation, and wire payloads."""

    def snapshot(
        self, target: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Return one complete snapshot produced through exactly one transport."""
        ...

    def act(
        self, target: ChangeRequestTarget, action: ReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Perform one action and return only after the response validates success."""
        ...
