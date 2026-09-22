"""GitHub adapter for canonical review snapshots and authorized mutations."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from pr_review_contracts import (
    ChangeRequestTarget,
    ReplyAction,
    ResolveAction,
    ReviewActionResult,
    TopLevelCommentAction,
)
from pr_review_gh_models import GitHubCreatedComment, GitHubResolveResponse
from pr_review_models import FetchResult, ReviewSnapshot
from pr_review_provider import ProviderResponseError
from pr_review_provider_text import render_top_level_body
from pr_review_state_models import AuthorizedReviewAction, SnapshotCompleteness

SnapshotLoader = Callable[..., FetchResult | ReviewSnapshot]
CommandRunner = Callable[..., str]


def upgrade_legacy_snapshot(legacy: FetchResult, target: ChangeRequestTarget) -> ReviewSnapshot:
    """Upgrade an injected legacy fixture without fabricating review inputs.

    Args:
        legacy: Pre-seam compatibility snapshot used by a test double.
        target: Canonical target supplied to the provider.

    Returns:
        A canonical wrapper used only by compatibility tests.
    """
    truncated = [thread.id for thread in legacy.unresolved if thread.comments_truncated]
    surfaces = {"threads", "reviews", "comments", "reactions", "identity", "revision"}
    completeness = SnapshotCompleteness(
        transport="github_cli",
        required_surfaces=surfaces,
        completed_surfaces=surfaces,
        truncated_input_ids=truncated,
        unavailable_capabilities=[],
    )
    revision_at = legacy.reviews_with_body[0].submittedAt if legacy.reviews_with_body else None
    if revision_at is None:
        revision_at = datetime(1970, 1, 1, tzinfo=UTC)
    return ReviewSnapshot.model_validate({
        **legacy.model_dump(),
        "provider": "github",
        "target": target,
        "transport": "github_cli",
        "snapshot_complete": completeness.complete,
        "snapshot_fingerprint": "legacy-fixture",
        "head_revision": "legacy-fixture",
        "revision_at": revision_at,
        "completeness": completeness,
        "review_inputs": [],
        "assessments": [],
        "clusters": [],
        "cycle_state": "ASSESSMENT_REQUIRED" if completeness.complete else "SNAPSHOT_INCOMPLETE",
        "codex_approval_equivalence": "available",
    })


class GitHubProvider:
    """GitHub adapter satisfying the two-method review-provider interface."""

    def __init__(self, *, snapshot_loader: SnapshotLoader, command_runner: CommandRunner, resolve_query: str) -> None:
        """Bind transport functions and the versioned GraphQL mutation.

        Args:
            snapshot_loader: Function that fetches a complete GitHub snapshot.
            command_runner: Bounded GitHub command transport.
            resolve_query: Versioned GraphQL review-thread mutation.
        """
        self.snapshot_loader = snapshot_loader
        self.command_runner = command_runner
        self.resolve_query = resolve_query

    @staticmethod
    def owner_repo(target: ChangeRequestTarget) -> tuple[str, str]:
        """Validate a GitHub target.

        Args:
            target: Provider-neutral target expected to identify GitHub.

        Returns:
            The repository owner and name.
        """
        if target.repository.provider != "github":
            message = f"GitHubProvider cannot operate on provider {target.repository.provider!r}"
            raise ValueError(message)
        owner, repo = target.repository.full_name.split("/", 1)
        if "/" in repo:
            message = "GitHub repository target must be exactly 'owner/repo'"
            raise ValueError(message)
        return owner, repo

    def snapshot(
        self, target: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Fetch one complete GitHub CLI snapshot.

        Args:
            target: Canonical pull-request target.
            deadline: Absolute monotonic deadline for the complete snapshot.
            command_timeout: Caller bound for each GitHub command.

        Returns:
            The canonical snapshot.
        """
        owner, repo = self.owner_repo(target)
        kwargs: dict[str, object] = {"gh_timeout": command_timeout, "target": target}
        if deadline is not None:
            kwargs["deadline"] = deadline
        result = self.snapshot_loader(owner, repo, target.number, **kwargs)
        if isinstance(result, ReviewSnapshot):
            return result
        return upgrade_legacy_snapshot(result, target)

    def act(
        self, target: ChangeRequestTarget, action: AuthorizedReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Perform one authorized GitHub mutation.

        Args:
            target: Canonical pull-request target.
            action: Mutation bound to complete current-cycle evidence.
            command_timeout: Caller bound for the GitHub command.

        Returns:
            A normalized result after GitHub confirms success.
        """
        if not isinstance(action, AuthorizedReviewAction):
            message = "GitHubProvider.act requires AuthorizedReviewAction"
            raise TypeError(message)
        if action.target != target:
            message = "authorized action target does not match provider target"
            raise ProviderResponseError(message)
        owner, repo = self.owner_repo(target)
        if isinstance(action.action, ReplyAction):
            comment_id = self.positive_provider_id(action.review_input.provider_ids.reply_target_id, "reply_target_id")
            raw = self.command_runner(
                [
                    "api",
                    "-X",
                    "POST",
                    f"repos/{owner}/{repo}/pulls/{target.number}/comments/{comment_id}/replies",
                    "-f",
                    f"body={action.action.body}",
                ],
                timeout=command_timeout,
            )
            response = self.validate_created_comment(raw, operation="reply")
            return ReviewActionResult(
                provider="github",
                action_kind="reply",
                success=True,
                provider_object_id=str(response.id),
                raw=json.loads(raw),
            )
        if isinstance(action.action, ResolveAction):
            thread_id = action.review_input.provider_ids.resolution_target_id
            if not thread_id:
                message = "GitHub resolve input lacks resolution_target_id"
                raise ProviderResponseError(message)
            raw = self.command_runner(
                ["api", "graphql", "-f", f"query={self.resolve_query}", "-f", f"threadId={thread_id}"],
                timeout=command_timeout,
            )
            response = self.validate_resolve(raw)
            return ReviewActionResult(
                provider="github",
                action_kind="resolve",
                success=True,
                resolved=response.data.resolveReviewThread.thread.isResolved,
                raw=json.loads(raw),
            )
        if isinstance(action.action, TopLevelCommentAction):
            body = render_top_level_body(action.action.body, action.action.references)
            raw = self.command_runner(
                ["api", "-X", "POST", f"repos/{owner}/{repo}/issues/{target.number}/comments", "-f", f"body={body}"],
                timeout=command_timeout,
            )
            response = self.validate_created_comment(raw, operation="top-level comment")
            return ReviewActionResult(
                provider="github",
                action_kind="comment",
                success=True,
                provider_object_id=str(response.id),
                raw=json.loads(raw),
            )
        message = f"unsupported GitHub review action: {type(action.action).__name__}"
        raise TypeError(message)

    @staticmethod
    def positive_provider_id(raw: str | None, name: str) -> int:
        """Read one positive integer identifier owned by the GitHub adapter.

        Args:
            raw: Provider-owned identifier value.
            name: Identifier key required by the operation.

        Returns:
            The parsed identifier.
        """
        try:
            value = int(raw) if raw is not None else 0
        except ValueError as exc:
            message = f"GitHub input has invalid {name}: {raw!r}"
            raise ProviderResponseError(message) from exc
        if value <= 0:
            message = f"GitHub input lacks positive {name}"
            raise ProviderResponseError(message)
        return value

    @staticmethod
    def validate_created_comment(raw: str, *, operation: str) -> GitHubCreatedComment:
        """Validate a created-comment response.

        Args:
            raw: Complete GitHub response body.
            operation: Operation name used in validation errors.

        Returns:
            The validated comment.
        """
        try:
            return GitHubCreatedComment.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            message = f"GitHub {operation} response did not confirm a created comment: {exc}"
            raise ProviderResponseError(message) from exc

    @staticmethod
    def validate_resolve(raw: str) -> GitHubResolveResponse:
        """Validate a confirmed GraphQL resolution.

        Args:
            raw: Complete GitHub GraphQL response body.

        Returns:
            The validated response.
        """
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            message = f"GitHub resolve response was not valid JSON: {exc}"
            raise ProviderResponseError(message) from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("GitHub resolve response must be a JSON object")
        if payload.get("errors"):
            message = f"GitHub resolve returned GraphQL errors: {payload['errors']}"
            raise ProviderResponseError(message)
        try:
            response = GitHubResolveResponse.model_validate(payload)
        except ValidationError as exc:
            message = f"GitHub resolve response did not contain the resolved thread: {exc}"
            raise ProviderResponseError(message) from exc
        if not response.data.resolveReviewThread.thread.isResolved:
            raise ProviderResponseError("GitHub resolve response reported isResolved=false")
        return response
