"""Bounded glab transport and complete GitLab snapshot collection."""

from __future__ import annotations

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

    Returns:
        Complete standard output.
    """
    return run_capture(["glab", *arguments], timeout=timeout)


def project_path(full_name: str) -> str:
    """Percent-encode a namespaced GitLab project for REST paths.

    Returns:
        The encoded project path.
    """
    return quote(full_name, safe="")


def parse_object(raw: str, model: type[ModelT], operation: str) -> ModelT:
    """Validate one JSON object response.

    Returns:
        The validated model.
    """
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise ProviderResponseError(f"GitLab {operation} response failed validation: {exc}") from exc


def parse_ndjson(raw: str, model: type[ModelT], operation: str) -> list[ModelT]:
    """Validate every object from a completely paginated NDJSON response.

    Returns:
        All validated items in provider order.
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

    Returns:
        Complete-pagination glab arguments.
    """
    return ["api", "--hostname", host, "--paginate", "--output", "ndjson", endpoint]


def collect_state(
    host: str, full_name: str, iid: int, *, timeout: float | None, runner: CommandRunner = run_glab
) -> GitLabState:
    """Fetch and validate every GitLab merge-request review surface.

    Returns:
        Complete validated raw GitLab state.
    """
    project = project_path(full_name)
    base = f"projects/{project}/merge_requests/{iid}"
    merge_request = parse_object(
        runner(["api", "--hostname", host, base], timeout=timeout), GitLabMergeRequest, "merge request"
    )
    discussions = parse_ndjson(
        runner(paginated_args(host, f"{base}/discussions?per_page=100"), timeout=timeout),
        GitLabDiscussion,
        "discussions",
    )
    notes = parse_ndjson(
        runner(paginated_args(host, f"{base}/notes?per_page=100"), timeout=timeout), GitLabNote, "notes"
    )
    approvals = parse_object(
        runner(["api", "--hostname", host, f"{base}/approvals"], timeout=timeout), GitLabApprovals, "approvals"
    )
    awards = parse_ndjson(
        runner(paginated_args(host, f"{base}/award_emoji?per_page=100"), timeout=timeout),
        GitLabAwardEmoji,
        "award emoji",
    )
    versions = parse_ndjson(
        runner(paginated_args(host, f"{base}/versions?per_page=100"), timeout=timeout),
        GitLabDiffVersion,
        "diff versions",
    )
    current_user = parse_object(
        runner(["api", "--hostname", host, "user"], timeout=timeout), GitLabUser, "current user"
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
