"""GitLab adapter for canonical review snapshots and authorized mutations."""

from __future__ import annotations

import json
from collections.abc import Callable

from pydantic import ValidationError

from pr_review_contracts import (
    ChangeRequestTarget,
    ReplyAction,
    ResolveAction,
    ReviewActionResult,
    TopLevelCommentAction,
)
from pr_review_gitlab_normalize import normalize_state
from pr_review_gitlab_transport import collect_state, project_path, run_glab
from pr_review_gitlab_wire import GitLabCreatedNote, GitLabDiscussion, GitLabState
from pr_review_models import ReviewSnapshot
from pr_review_provider import ProviderResponseError, dispatch_review_action
from pr_review_provider_text import render_top_level_body
from pr_review_state_models import AuthorizedReviewAction

CommandRunner = Callable[..., str]
StateLoader = Callable[..., GitLabState]


class GitLabProvider:
    """GitLab adapter satisfying the two-method review-provider interface."""

    def __init__(self, *, state_loader: StateLoader = collect_state, command_runner: CommandRunner = run_glab) -> None:
        """Bind complete-state and bounded-command transports.

        Args:
            state_loader: Stable complete-state collector.
            command_runner: Bounded glab command transport.
        """
        self.state_loader = state_loader
        self.command_runner = command_runner

    @staticmethod
    def coordinates(target: ChangeRequestTarget) -> tuple[str, str]:
        """Validate GitLab host/project coordinates.

        Args:
            target: Provider-neutral target expected to identify GitLab.

        Returns:
            The bare host and nested project path.

        Raises:
            ValueError: If the target belongs to another provider.
        """
        if target.repository.provider != "gitlab":
            raise ValueError(f"GitLabProvider cannot operate on provider {target.repository.provider!r}")
        return target.repository.hostname, target.repository.full_name

    def snapshot(
        self, target: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Fetch and normalize one complete GitLab CLI snapshot.

        Args:
            target: Canonical merge-request target.
            deadline: Absolute deadline for the complete stable snapshot.
            command_timeout: Positive caller-selected per-command bound.

        Returns:
            A canonical provider-neutral snapshot.
        """
        host, full_name = self.coordinates(target)
        state = self.state_loader(
            host,
            full_name,
            target.number,
            deadline=deadline,
            command_timeout=command_timeout,
            runner=self.command_runner,
        )
        return normalize_state(state, target)

    def act(
        self, target: ChangeRequestTarget, action: AuthorizedReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Perform one cycle-authorized GitLab mutation.

        Args:
            target: Canonical merge-request target.
            action: Mutation bound to current complete-cycle evidence.
            command_timeout: Positive caller-selected per-command bound.

        Returns:
            A provider-neutral confirmed action result.

        Raises:
            ProviderResponseError: If target evidence or the provider response is invalid.
            TypeError: If the action is not authorized or supported.
        """
        if not isinstance(action, AuthorizedReviewAction):
            raise TypeError("GitLabProvider.act requires AuthorizedReviewAction")
        if action.target != target:
            raise ProviderResponseError("authorized action target does not match provider target")
        host, full_name = self.coordinates(target)
        base = f"projects/{project_path(full_name)}/merge_requests/{target.number}"
        return dispatch_review_action(
            action,
            reply=lambda authorized, requested: self._reply(host, base, authorized, requested, command_timeout),
            resolve=lambda authorized, requested: self._resolve(host, base, authorized, requested, command_timeout),
            comment=lambda authorized, requested: self._comment(host, base, authorized, requested, command_timeout),
        )

    def _reply(
        self,
        host: str,
        base: str,
        authorized: AuthorizedReviewAction,
        requested: ReplyAction,
        command_timeout: float | None,
    ) -> ReviewActionResult:
        """Execute one GitLab inline reply.

        Returns:
            Provider-confirmed reply result.
        """
        discussion_id = authorized.review_input.provider_ids.reply_target_id
        if not discussion_id:
            raise ProviderResponseError("GitLab reply input lacks reply_target_id")
        body = render_top_level_body(requested.body, [authorized.review_input.stable_reference])
        raw = self.command_runner(
            [
                "api",
                "--hostname",
                host,
                "--method",
                "POST",
                f"{base}/discussions/{discussion_id}/notes",
                "--raw-field",
                f"body={body}",
            ],
            timeout=command_timeout,
        )
        note = self.validate_created_note(raw, "reply")
        return ReviewActionResult(
            provider="gitlab", action_kind="reply", success=True, provider_object_id=str(note.id), raw=json.loads(raw)
        )

    def _resolve(
        self,
        host: str,
        base: str,
        authorized: AuthorizedReviewAction,
        requested: ResolveAction,
        command_timeout: float | None,
    ) -> ReviewActionResult:
        """Execute one GitLab discussion resolution.

        Returns:
            Provider-confirmed resolution result.
        """
        del requested
        discussion_id = authorized.review_input.provider_ids.resolution_target_id
        if not discussion_id:
            raise ProviderResponseError("GitLab resolve input lacks resolution_target_id")
        raw = self.command_runner(
            [
                "api",
                "--hostname",
                host,
                "--method",
                "PUT",
                f"{base}/discussions/{discussion_id}",
                "--field",
                "resolved=true",
            ],
            timeout=command_timeout,
        )
        discussion = self.validate_resolved_discussion(raw)
        return ReviewActionResult(
            provider="gitlab",
            action_kind="resolve",
            success=True,
            resolved=True,
            provider_object_id=discussion.id,
            raw=json.loads(raw),
        )

    def _comment(
        self,
        host: str,
        base: str,
        authorized: AuthorizedReviewAction,
        requested: TopLevelCommentAction,
        command_timeout: float | None,
    ) -> ReviewActionResult:
        """Execute one GitLab top-level response.

        Returns:
            Provider-confirmed comment result.
        """
        del authorized
        body = render_top_level_body(requested.body, requested.references)
        raw = self.command_runner(
            ["api", "--hostname", host, "--method", "POST", f"{base}/notes", "--raw-field", f"body={body}"],
            timeout=command_timeout,
        )
        note = self.validate_created_note(raw, "top-level comment")
        return ReviewActionResult(
            provider="gitlab", action_kind="comment", success=True, provider_object_id=str(note.id), raw=json.loads(raw)
        )

    @staticmethod
    def validate_created_note(raw: str, operation: str) -> GitLabCreatedNote:
        """Require GitLab to return the created note identity.

        Args:
            raw: Complete mutation response.
            operation: Operation label used in diagnostics.

        Returns:
            The confirmed created note.

        Raises:
            ProviderResponseError: If the response lacks a created-note identity.
        """
        try:
            return GitLabCreatedNote.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab {operation} response did not confirm a created note: {exc}") from exc

    @staticmethod
    def validate_resolved_discussion(raw: str) -> GitLabDiscussion:
        """Require GitLab to return a resolved discussion.

        Args:
            raw: Complete discussion mutation response.

        Returns:
            The confirmed resolved discussion.

        Raises:
            ProviderResponseError: If the response does not prove resolution.
        """
        try:
            discussion = GitLabDiscussion.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab resolve response failed validation: {exc}") from exc
        if not any(note.resolvable and note.resolved is True for note in discussion.notes):
            raise ProviderResponseError("GitLab resolve response did not confirm resolved=true")
        return discussion
