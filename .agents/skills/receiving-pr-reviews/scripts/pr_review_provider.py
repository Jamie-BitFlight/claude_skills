"""Provider seam for complete review snapshots and validated review actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pr_review_contracts import (
    ChangeRequestTarget,
    ReplyAction,
    ResolveAction,
    ReviewActionResult,
    TopLevelCommentAction,
)
from pr_review_models import ReviewSnapshot
from pr_review_state_models import AuthorizedReviewAction

__all__ = ["ProviderResponseError", "ReviewProvider", "dispatch_review_action"]

ReplyHandler = Callable[[AuthorizedReviewAction, ReplyAction], ReviewActionResult]
ResolveHandler = Callable[[AuthorizedReviewAction, ResolveAction], ReviewActionResult]
CommentHandler = Callable[[AuthorizedReviewAction, TopLevelCommentAction], ReviewActionResult]


class ProviderResponseError(RuntimeError):
    """A provider process succeeded but its response did not confirm the requested operation."""


def dispatch_review_action(
    authorized: AuthorizedReviewAction, *, reply: ReplyHandler, resolve: ResolveHandler, comment: CommentHandler
) -> ReviewActionResult:
    """Dispatch one provider-neutral action to its provider-owned operation.

    Args:
        authorized: Cycle-authorized action and provider identity.
        reply: Provider implementation for an inline reply.
        resolve: Provider implementation for discussion resolution.
        comment: Provider implementation for a top-level response.

    Returns:
        Provider-confirmed action result.

    Raises:
        TypeError: If the authorized action type is unsupported.
    """
    action = authorized.action
    if isinstance(action, ReplyAction):
        return reply(authorized, action)
    if isinstance(action, ResolveAction):
        return resolve(authorized, action)
    if isinstance(action, TopLevelCommentAction):
        return comment(authorized, action)
    raise TypeError(f"unsupported review action: {type(action).__name__}")


@runtime_checkable
class ReviewProvider(Protocol):
    """Deep interface hiding forge transport, pagination, validation, and wire payloads."""

    def snapshot(
        self, target: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Return one complete snapshot produced through exactly one transport.

        Args:
            target: Canonical change-request target.
            deadline: Absolute monotonic deadline for the complete snapshot.
            command_timeout: Positive per-command transport bound.

        Returns:
            Complete canonical provider snapshot.
        """
        ...

    def act(
        self, target: ChangeRequestTarget, action: AuthorizedReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Perform one action and return only after the response validates success.

        Args:
            target: Canonical change-request target.
            action: Mutation bound to complete current-cycle evidence.
            command_timeout: Positive per-command transport bound.

        Returns:
            Provider-neutral confirmed action result.
        """
        ...
