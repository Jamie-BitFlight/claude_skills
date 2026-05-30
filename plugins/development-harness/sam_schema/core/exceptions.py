"""SAM exception hierarchy for TaskBackend operations.

All TaskBackend Protocol methods raise exceptions from this module.
These replace the broad exception tuples in server.py with semantically
meaningful, typed errors that callers can catch narrowly.
"""

from __future__ import annotations

__all__ = [
    "ArtifactWriteError",
    "ConcurrentClaimUnsupportedError",
    "DocumentNotFoundError",
    "PlanExistsError",
    "PlanIndexConfigError",
    "PlanIndexError",
    "PlanNotFoundError",
    "SamError",
    "TaskNotFoundError",
    "TaskValidationError",
]


class SamError(Exception):
    """Base exception for all SAM operations."""


class PlanNotFoundError(SamError):
    """Raised when a plan_id does not resolve to a known plan."""

    def __init__(self, plan_id: str) -> None:
        """Initialize with the plan ID that could not be found.

        Args:
            plan_id: The plan identifier that was not found.
        """
        self.plan_id = plan_id
        super().__init__(f"Plan not found: {plan_id}")


class PlanExistsError(SamError):
    """Raised when attempting to create a plan that already exists."""

    def __init__(self, plan_id: str) -> None:
        """Initialize with the duplicate plan ID.

        Args:
            plan_id: The plan identifier that already exists.
        """
        self.plan_id = plan_id
        super().__init__(f"Plan already exists: {plan_id}")


class TaskNotFoundError(SamError):
    """Raised when a task_id does not resolve within a known plan."""

    def __init__(self, plan_id: str, task_id: str) -> None:
        """Initialize with the plan and task identifiers.

        Args:
            plan_id: The plan the task was expected to belong to.
            task_id: The task identifier that was not found.
        """
        self.plan_id = plan_id
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id} in plan {plan_id}")


class TaskValidationError(SamError):
    """Raised when a task definition fails validation."""

    def __init__(self, task_index: int, detail: str) -> None:
        """Initialize with the index of the invalid task and a description.

        Args:
            task_index: Zero-based index of the task in the input list.
            detail: Human-readable description of the validation failure.
        """
        self.task_index = task_index
        self.detail = detail
        super().__init__(f"Task at index {task_index} failed validation: {detail}")


class ArtifactWriteError(SamError):
    """Raised when a Gist write fails during plan create or mutation.

    Indicates the plan is NOT durably stored remotely.  The local YAML cache
    may still exist, but the plan is not portable across environments.
    """

    def __init__(self, plan_id: str, issue: int | None, reason: str) -> None:
        """Initialize with the plan ID, issue number, and failure reason.

        Args:
            plan_id: The plan identifier whose artifact write failed.
            issue: GitHub issue number keying the Gist artifact, or None for
                local-only plans.
            reason: Human-readable description of the underlying failure.
        """
        self.plan_id = plan_id
        self.issue = issue
        self.reason = reason
        super().__init__(f"Artifact write failed for plan {plan_id} (issue #{issue}): {reason}")


class PlanIndexError(SamError):
    """Raised when plan_id registration or resolution fails in the Gist index."""

    def __init__(self, plan_id: str, reason: str) -> None:
        """Initialize with the plan ID and failure reason.

        Args:
            plan_id: The plan identifier whose index operation failed.
            reason: Human-readable description of the failure.
        """
        self.plan_id = plan_id
        self.reason = reason
        super().__init__(f"Plan index error for {plan_id}: {reason}")


class PlanIndexConfigError(PlanIndexError):
    """Raised when sam.plan_index_issue is not configured in .dh/config.yaml.

    Subclass of PlanIndexError so callers catching PlanIndexError also handle
    this configuration variant.
    """

    def __init__(self) -> None:
        """Initialize with a descriptive configuration guidance message."""
        super().__init__(
            plan_id="<unknown>",
            reason=(
                "sam.plan_index_issue is not set in .dh/config.yaml. "
                "Set it to a stable GitHub issue number to enable plan_id reverse lookup. "
                "Plans will still be stored on their own issue's Gist, but plan_id resolution "
                "across environments will not work until the sentinel issue is configured."
            ),
        )


class ConcurrentClaimUnsupportedError(SamError):
    """Raised by claim_task when the plan has no associated issue.

    Parallel claim requires an atomic mechanism anchored to a GitHub issue
    (label swap).  Local-only plans (issue=None) have no such anchor and
    cannot safely support concurrent claim attempts.
    """

    def __init__(self, plan_id: str) -> None:
        """Initialize with the plan ID that cannot be claimed concurrently.

        Args:
            plan_id: The local-only plan whose concurrent claim was attempted.
        """
        self.plan_id = plan_id
        super().__init__(
            f"Concurrent claim is not supported for local-only plan {plan_id} (issue=None). "
            "Parallel dispatch requires a GitHub issue to anchor atomic label-swap claim semantics."
        )


class DocumentNotFoundError(SamError):
    """Raised when a document content_ref cannot be resolved."""

    def __init__(self, content_ref: str) -> None:
        """Initialize with the opaque content reference that failed.

        Args:
            content_ref: The backend-specific reference string that was not found.
        """
        self.content_ref = content_ref
        super().__init__(f"Document not found: {content_ref}")
