"""Bounded glab transport and complete GitLab snapshot collection."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from typing import TypeVar
from urllib.parse import quote

from pydantic import BaseModel, ValidationError

from pr_review_gitlab_wire import (
    GitLabApprovals,
    GitLabAwardEmoji,
    GitLabDiffVersion,
    GitLabDiscussion,
    GitLabMergeRequest,
    GitLabNote,
    GitLabState,
    GitLabUser,
)
from pr_review_provider import ProviderResponseError
from pr_review_subprocess import run_capture

CommandRunner = Callable[..., str]
ModelT = TypeVar("ModelT", bound=BaseModel)


def run_glab(arguments: list[str], *, timeout: float | None = None) -> str:
    """Run one bounded glab command.

    Args:
        arguments: Complete glab argument vector after the executable.
        timeout: Positive subprocess bound in seconds.

    Returns:
        Complete standard output.
    """
    return run_capture(["glab", *arguments], timeout=timeout)


def project_path(full_name: str) -> str:
    """Percent-encode a namespaced GitLab project for REST paths.

    Args:
        full_name: Nested GitLab namespace and project path.

    Returns:
        The encoded project path.
    """
    return quote(full_name, safe="")


def parse_object(raw: str, model: type[ModelT], operation: str) -> ModelT:
    """Validate one JSON object response.

    Args:
        raw: Complete JSON object response.
        model: Strict wire model for the response.
        operation: Operation label used in diagnostics.

    Returns:
        The validated model.

    Raises:
        ProviderResponseError: If the response violates the wire model.
    """
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise ProviderResponseError(f"GitLab {operation} response failed validation: {exc}") from exc


def parse_ndjson(raw: str, model: type[ModelT], operation: str) -> list[ModelT]:
    """Validate every object from a completely paginated NDJSON response.

    Args:
        raw: Complete paginated NDJSON response.
        model: Strict wire model for each item.
        operation: Operation label used in diagnostics.

    Returns:
        All validated items in provider order.

    Raises:
        ProviderResponseError: If any page item violates the wire model.
    """
    values: list[ModelT] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            values.append(model.model_validate_json(line))
        except ValidationError as exc:
            raise ProviderResponseError(f"GitLab {operation} page item {line_number} failed validation: {exc}") from exc
    return values


def paginated_args(host: str, endpoint: str) -> list[str]:
    """Build the one supported complete-list command form.

    Args:
        host: Bare GitLab hostname.
        endpoint: REST endpoint relative to the host API root.

    Returns:
        Complete-pagination glab arguments.
    """
    return ["api", "--hostname", host, "--paginate", "--output", "ndjson", endpoint]


def command_timeout(deadline: float | None, caller_timeout: float | None) -> float | None:
    """Return the current per-command bound without exceeding the snapshot deadline.

    Args:
        deadline: Absolute monotonic deadline for the complete stable snapshot.
        caller_timeout: Positive caller-selected command bound.

    Returns:
        The tighter active timeout, or ``None`` when neither bound exists.

    Raises:
        subprocess.TimeoutExpired: If the complete-snapshot deadline has elapsed.
    """
    if deadline is None:
        return caller_timeout
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(cmd=["glab", "api"], timeout=max(remaining, 0.0))
    return remaining if caller_timeout is None else min(caller_timeout, remaining)


def collect_once(
    host: str, full_name: str, iid: int, *, deadline: float | None, caller_timeout: float | None, runner: CommandRunner
) -> GitLabState:
    """Fetch every GitLab review surface once through one transport.

    Args:
        host: Bare GitLab hostname.
        full_name: Nested namespace and project path.
        iid: Project-local merge-request number.
        deadline: Absolute complete-snapshot deadline.
        caller_timeout: Positive caller-selected command bound.
        runner: Bounded glab command transport.

    Returns:
        One validated sequential provider-state observation.
    """
    project = project_path(full_name)
    base = f"projects/{project}/merge_requests/{iid}"
    merge_request = parse_object(
        runner(["api", "--hostname", host, base], timeout=command_timeout(deadline, caller_timeout)),
        GitLabMergeRequest,
        "merge request",
    )
    discussions = parse_ndjson(
        runner(
            paginated_args(host, f"{base}/discussions?per_page=100"), timeout=command_timeout(deadline, caller_timeout)
        ),
        GitLabDiscussion,
        "discussions",
    )
    notes = parse_ndjson(
        runner(paginated_args(host, f"{base}/notes?per_page=100"), timeout=command_timeout(deadline, caller_timeout)),
        GitLabNote,
        "notes",
    )
    approvals = parse_object(
        runner(["api", "--hostname", host, f"{base}/approvals"], timeout=command_timeout(deadline, caller_timeout)),
        GitLabApprovals,
        "approvals",
    )
    awards = parse_ndjson(
        runner(
            paginated_args(host, f"{base}/award_emoji?per_page=100"), timeout=command_timeout(deadline, caller_timeout)
        ),
        GitLabAwardEmoji,
        "award emoji",
    )
    versions = parse_ndjson(
        runner(
            paginated_args(host, f"{base}/versions?per_page=100"), timeout=command_timeout(deadline, caller_timeout)
        ),
        GitLabDiffVersion,
        "diff versions",
    )
    current_user = parse_object(
        runner(["api", "--hostname", host, "user"], timeout=command_timeout(deadline, caller_timeout)),
        GitLabUser,
        "current user",
    )
    return GitLabState(
        merge_request=merge_request,
        discussions=discussions,
        notes=notes,
        approvals=approvals,
        awards=awards,
        versions=versions,
        current_user=current_user,
    )


def collect_state(
    host: str,
    full_name: str,
    iid: int,
    *,
    deadline: float | None,
    command_timeout: float | None,
    runner: CommandRunner = run_glab,
) -> GitLabState:
    """Return a stable complete snapshot observed identically twice.

    Args:
        host: Bare GitLab hostname.
        full_name: Nested namespace and project path.
        iid: Project-local merge-request number.
        deadline: Absolute deadline for both complete observations.
        command_timeout: Positive caller-selected per-command bound.
        runner: Bounded glab command transport.

    Returns:
        The second complete provider state after a stable observation window.

    Raises:
        ProviderResponseError: If any provider surface changes between observations.
        subprocess.TimeoutExpired: If the complete-snapshot deadline elapses.
    """
    first = collect_once(host, full_name, iid, deadline=deadline, caller_timeout=command_timeout, runner=runner)
    second = collect_once(host, full_name, iid, deadline=deadline, caller_timeout=command_timeout, runner=runner)
    if first != second:
        raise ProviderResponseError("GitLab review state changed during collection")
    return second
