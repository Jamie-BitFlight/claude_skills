"""GitLab adapter for canonical review snapshots and authorized mutations."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from pydantic import ValidationError

from pr_review_contracts import (
    ApprovalStateAction,
    ChangeRequestTarget,
    ReplyAction,
    ResolveAction,
    ReviewActionResult,
    TopLevelCommentAction,
)
from pr_review_gitlab_normalize import normalize_state
from pr_review_gitlab_transport import collect_state, project_path, run_glab
from pr_review_gitlab_wire import GitLabApprovals, GitLabCreatedNote, GitLabDiscussion, GitLabState, GitLabUser
from pr_review_models import ReviewSnapshot
from pr_review_provider import ProviderResponseError
from pr_review_provider_text import render_top_level_body
from pr_review_state_models import AuthorizedReviewAction

CommandRunner = Callable[..., str]
StateLoader = Callable[..., GitLabState]


class GitLabProvider:
    """GitLab adapter satisfying the two-method review-provider interface."""

    def __init__(self, *, state_loader: StateLoader = collect_state, command_runner: CommandRunner = run_glab) -> None:
        """Bind complete-state and bounded-command transports."""
        self.state_loader = state_loader
        self.command_runner = command_runner

    @staticmethod
    def coordinates(target: ChangeRequestTarget) -> tuple[str, str]:
        """Validate GitLab host/project coordinates.

        Returns:
            The bare host and nested project path.
        """
        if target.repository.provider != "gitlab":
            raise ValueError(f"GitLabProvider cannot operate on provider {target.repository.provider!r}")
        return target.repository.hostname, target.repository.full_name

    def snapshot(
        self, target: ChangeRequestTarget, *, deadline: float | None, command_timeout: float | None
    ) -> ReviewSnapshot:
        """Fetch and normalize one complete GitLab CLI snapshot.

        Returns:
            A canonical provider-neutral snapshot.
        """
        host, full_name = self.coordinates(target)
        timeout = command_timeout
        if deadline is not None:
            remaining = max(0.0, deadline - time.monotonic())
            timeout = remaining if timeout is None else min(timeout, remaining)
        state = self.state_loader(host, full_name, target.number, timeout=timeout, runner=self.command_runner)
        return normalize_state(state, target)

    def act(
        self, target: ChangeRequestTarget, action: AuthorizedReviewAction, *, command_timeout: float | None
    ) -> ReviewActionResult:
        """Perform one cycle-authorized GitLab mutation.

        Returns:
            A provider-neutral confirmed action result.
        """
        if not isinstance(action, AuthorizedReviewAction):
            raise TypeError("GitLabProvider.act requires AuthorizedReviewAction")
        if action.target != target:
            raise ProviderResponseError("authorized action target does not match provider target")
        host, full_name = self.coordinates(target)
        base = f"projects/{project_path(full_name)}/merge_requests/{target.number}"
        if isinstance(action.action, ReplyAction):
            discussion_id = action.review_input.provider_ids.reply_target_id
            if not discussion_id:
                raise ProviderResponseError("GitLab reply input lacks reply_target_id")
            raw = self.command_runner(
                [
                    "api",
                    "--hostname",
                    host,
                    "--method",
                    "POST",
                    f"{base}/discussions/{discussion_id}/notes",
                    "--raw-field",
                    f"body={action.action.body}",
                ],
                timeout=command_timeout,
            )
            note = self.validate_created_note(raw, "reply")
            return ReviewActionResult(
                provider="gitlab",
                action_kind="reply",
                success=True,
                provider_object_id=str(note.id),
                raw=json.loads(raw),
            )
        if isinstance(action.action, ResolveAction):
            discussion_id = action.review_input.provider_ids.resolution_target_id
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
        if isinstance(action.action, TopLevelCommentAction):
            body = render_top_level_body(action.action.body, action.action.references)
            raw = self.command_runner(
                ["api", "--hostname", host, "--method", "POST", f"{base}/notes", "--raw-field", f"body={body}"],
                timeout=command_timeout,
            )
            note = self.validate_created_note(raw, "top-level comment")
            return ReviewActionResult(
                provider="gitlab",
                action_kind="comment",
                success=True,
                provider_object_id=str(note.id),
                raw=json.loads(raw),
            )
        if isinstance(action.action, ApprovalStateAction):
            return self.set_approval_state(
                host=host, base=base, action=action, approved=action.action.approved, command_timeout=command_timeout
            )
        raise TypeError(f"unsupported GitLab review action: {type(action.action).__name__}")

    def set_approval_state(
        self, *, host: str, base: str, action: AuthorizedReviewAction, approved: bool, command_timeout: float | None
    ) -> ReviewActionResult:
        """Mutate and read back the authenticated actor's approval state.

        Returns:
            A provider-neutral confirmed approval-state result.
        """
        operation = "approve" if approved else "unapprove"
        arguments = ["api", "--hostname", host, "--method", "POST", f"{base}/{operation}"]
        if approved:
            arguments.extend(["--raw-field", f"sha={action.revision}"])
        raw = self.command_runner(arguments, timeout=command_timeout)
        try:
            mutation = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError(f"GitLab {operation} response was not valid JSON: {exc}") from exc
        if not isinstance(mutation, dict):
            raise ProviderResponseError(f"GitLab {operation} response must be a JSON object")
        try:
            current_user = GitLabUser.model_validate_json(
                self.command_runner(["api", "--hostname", host, "user"], timeout=command_timeout)
            )
            approval_raw = self.command_runner(
                ["api", "--hostname", host, f"{base}/approvals"], timeout=command_timeout
            )
            approvals = GitLabApprovals.model_validate_json(approval_raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab {operation} verification failed validation: {exc}") from exc
        actor_is_approved = any(item.user.id == current_user.id for item in approvals.approved_by)
        if actor_is_approved != approved:
            raise ProviderResponseError(f"GitLab {operation} verification did not confirm requested state")
        return ReviewActionResult(
            provider="gitlab",
            action_kind="approval_state",
            success=True,
            raw={"mutation": mutation, "verification": json.loads(approval_raw)},
        )

    @staticmethod
    def validate_created_note(raw: str, operation: str) -> GitLabCreatedNote:
        """Require GitLab to return the created note identity.

        Returns:
            The confirmed created note.
        """
        try:
            return GitLabCreatedNote.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab {operation} response did not confirm a created note: {exc}") from exc

    @staticmethod
    def validate_resolved_discussion(raw: str) -> GitLabDiscussion:
        """Require GitLab to return a resolved discussion.

        Returns:
            The confirmed resolved discussion.
        """
        try:
            discussion = GitLabDiscussion.model_validate_json(raw)
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab resolve response failed validation: {exc}") from exc
        if not any(note.resolvable and note.resolved is True for note in discussion.notes):
            raise ProviderResponseError("GitLab resolve response did not confirm resolved=true")
        return discussion
