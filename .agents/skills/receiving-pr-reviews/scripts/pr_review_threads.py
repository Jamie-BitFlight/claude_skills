#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "typer",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Canonical review-state CLI with authorized provider mutations."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from pr_review_cli_mutations import register_mutation_commands
from pr_review_cli_target import (
    DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    GithubOption,
    HostOption,
    ProviderOption,
    ProviderTimeoutOption,
    RepoOption,
    github_target,
    resolve_target,
)
from pr_review_contracts import ChangeRequestTarget
from pr_review_gh import RESOLVE_THREAD_MUTATION, build_fetch_result, detect_repo_identity, run_gh
from pr_review_github_provider import GitHubProvider
from pr_review_gitlab_provider import GitLabProvider
from pr_review_models import WatchResult, WatchSummary
from pr_review_output import board_entry, summarize
from pr_review_provider import ReviewProvider
from pr_review_state import load_cycle, load_snapshot

__all__ = ["load_cycle", "load_snapshot"]

app = typer.Typer(help="Review-state operations through a validated provider interface.")

DEFAULT_WATCH_INTERVAL_SECONDS = 90
DEFAULT_WATCH_TIMEOUT_SECONDS = 270
DEFAULT_WATCH_MAX_ATTEMPTS = 4


def owner_repo(github: str | None, *, gh_timeout: float | None) -> tuple[str, str]:
    """Resolve GitHub coordinates through the compatibility target helper.

    Args:
        github: Optional explicit ``owner/repository`` target.
        gh_timeout: Positive GitHub command bound.

    Returns:
        The owner and repository name.
    """
    resolved = github_target(github, 1, timeout=gh_timeout, detector=detect_repo_identity)
    owner, repo = resolved.repository.full_name.split("/", 1)
    return owner, repo


def target_for_github(github: str | None, pr: int, *, gh_timeout: float | None) -> ChangeRequestTarget:
    """Resolve one GitHub pull-request target.

    Args:
        github: Optional explicit ``owner/repository`` target.
        pr: Positive pull-request number.
        gh_timeout: Positive GitHub command bound.

    Returns:
        The canonical target.
    """
    return github_target(github, pr, timeout=gh_timeout, detector=detect_repo_identity)


def target_for_request(
    provider: str | None,
    repo: str | None,
    host: str | None,
    github: str | None,
    number: int,
    *,
    command_timeout: float | None,
) -> ChangeRequestTarget:
    """Resolve provider-neutral CLI target options.

    Args:
        provider: Optional explicit forge provider.
        repo: Optional provider repository path.
        host: Optional bare provider hostname.
        github: Legacy explicit GitHub repository.
        number: Positive change-request number.
        command_timeout: Positive provider command bound.

    Returns:
        The canonical provider target.
    """
    return resolve_target(
        provider=provider,
        repo=repo,
        host=host,
        github=github,
        number=number,
        timeout=command_timeout,
        github_resolver=lambda value, selected: target_for_github(value, selected, gh_timeout=command_timeout),
    )


def review_provider() -> ReviewProvider:
    """Construct the GitHub adapter behind the provider interface.

    Returns:
        A provider implementing canonical snapshots and authorized actions.
    """
    return GitHubProvider(
        snapshot_loader=build_fetch_result, command_runner=run_gh, resolve_query=RESOLVE_THREAD_MUTATION
    )


def review_provider_for_target(target: ChangeRequestTarget) -> ReviewProvider:
    """Select the deep adapter after the target is resolved.

    Args:
        target: Canonical change-request target.

    Returns:
        The target's provider adapter.
    """
    if target.repository.provider == "github":
        return review_provider()
    return GitLabProvider()


def parse_pr_list(value: str) -> list[int]:
    """Parse positive comma-separated pull-request numbers.

    Args:
        value: Comma-separated pull-request numbers.

    Returns:
        Validated numbers in input order.

    Raises:
        typer.BadParameter: If an item is empty, non-numeric, or non-positive.
    """
    parts = [part.strip() for part in value.split(",")]
    if not all(parts):
        raise typer.BadParameter("must be one or more PR numbers, comma-separated (e.g. '41,42,44')")
    numbers = []
    for part in parts:
        try:
            number = int(part)
        except ValueError as exc:
            raise typer.BadParameter(f"not a valid PR number: {exc}") from exc
        if number <= 0:
            raise typer.BadParameter(f"PR number must be positive, got {number}")
        numbers.append(number)
    return numbers


SummaryOption = Annotated[bool, typer.Option("--summary", help="Print canonical compact JSON.")]
MaxBodyOption = Annotated[
    int | None, typer.Option("--max-body", min=1, help="Visibly truncate compatibility bodies; unlimited by default.")
]
BaselineSnapshotOption = Annotated[
    Path | None,
    typer.Option(
        "--baseline-snapshot-file",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Stop when canonical provider state differs from this complete snapshot.",
    ),
]


@app.command()
def fetch(
    pr: Annotated[str, typer.Option(help="Pull request number(s), comma-separated.")],
    github: GithubOption = None,
    provider: ProviderOption = None,
    repo: RepoOption = None,
    host: HostOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
    provider_timeout_seconds: ProviderTimeoutOption = DEFAULT_PROVIDER_TIMEOUT_SECONDS,
) -> None:
    """Fetch complete canonical review snapshots.

    Args:
        pr: One or more comma-separated pull-request numbers.
        github: Legacy explicit GitHub repository.
        provider: Explicit provider selection.
        repo: Provider repository path.
        host: Bare provider hostname.
        summary: Emit compact status output instead of full action evidence.
        max_body: Optional visible body truncation bound.
        provider_timeout_seconds: Positive provider subprocess bound.
    """
    numbers = parse_pr_list(pr)
    first_target = target_for_request(
        provider, repo, host, github, numbers[0], command_timeout=provider_timeout_seconds
    )
    selected_provider = review_provider_for_target(first_target)
    if len(numbers) == 1 and not summary:
        typer.echo(
            selected_provider.snapshot(
                first_target, deadline=None, command_timeout=provider_timeout_seconds
            ).model_dump_json()
        )
        return
    for number in numbers:
        target = first_target.model_copy(update={"number": number})
        result = selected_provider.snapshot(target, deadline=None, command_timeout=provider_timeout_seconds)
        output = summarize(result, pr=number, max_body=max_body) if summary else board_entry(number, result)
        typer.echo(output.model_dump_json())


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    github: GithubOption = None,
    provider: ProviderOption = None,
    repo: RepoOption = None,
    host: HostOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
    baseline_snapshot_file: BaselineSnapshotOption = None,
    interval_seconds: Annotated[int, typer.Option(min=1)] = DEFAULT_WATCH_INTERVAL_SECONDS,
    timeout_seconds: Annotated[int, typer.Option(min=0)] = DEFAULT_WATCH_TIMEOUT_SECONDS,
    max_attempts: Annotated[int, typer.Option(min=1)] = DEFAULT_WATCH_MAX_ATTEMPTS,
    provider_timeout_seconds: ProviderTimeoutOption = DEFAULT_PROVIDER_TIMEOUT_SECONDS,
) -> None:
    """Sample complete snapshots within one deadline and attempt budget.

    Args:
        pr: Pull-request number.
        github: Legacy explicit GitHub repository.
        provider: Explicit provider selection.
        repo: Provider repository path.
        host: Bare provider hostname.
        summary: Emit compact status output instead of the full snapshot.
        max_body: Optional visible body truncation bound.
        baseline_snapshot_file: Optional complete snapshot establishing pre-watch provider state.
        interval_seconds: Delay between complete snapshots.
        timeout_seconds: Overall sampling window.
        max_attempts: Maximum complete snapshots in this call.
        provider_timeout_seconds: Positive provider subprocess bound.
    """
    deadline = time.monotonic() + timeout_seconds
    target = target_for_request(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
    selected_provider = review_provider_for_target(target)
    current = selected_provider.snapshot(
        target, deadline=deadline if timeout_seconds > 0 else None, command_timeout=provider_timeout_seconds
    )
    baseline = load_snapshot(baseline_snapshot_file) if baseline_snapshot_file is not None else current
    if baseline.target != target:
        raise typer.BadParameter(
            "baseline snapshot target does not match watch target", param_hint="baseline-snapshot-file"
        )
    if not baseline.snapshot_complete or not baseline.completeness.complete:
        raise typer.BadParameter("baseline snapshot is incomplete", param_hint="baseline-snapshot-file")
    baseline_fingerprint = baseline.snapshot_fingerprint
    attempts = 1
    poll_attempts = 0
    last_poll_ok = True
    while not current.has_watch_signal(baseline_fingerprint) and attempts < max_attempts:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_seconds, remaining))
        if remaining <= interval_seconds:
            break
        poll_attempts += 1
        attempts += 1
        try:
            current = selected_provider.snapshot(target, deadline=deadline, command_timeout=provider_timeout_seconds)
            last_poll_ok = True
        except subprocess.TimeoutExpired:
            last_poll_ok = time.monotonic() >= deadline
        except (subprocess.CalledProcessError, ValidationError):
            last_poll_ok = False
    if poll_attempts and not last_poll_ok:
        typer.echo(
            f"watch: the last of {poll_attempts} poll(s) this window failed — final state before deadline was never confirmed",
            err=True,
        )
        raise typer.Exit(code=1)
    timed_out = not current.has_watch_signal(baseline_fingerprint)
    exhausted = timed_out and attempts >= max_attempts
    if summary:
        compact = summarize(current, pr=pr, max_body=max_body)
        typer.echo(
            WatchSummary(
                **compact.model_dump(), timed_out=timed_out, attempts=attempts, attempt_budget_exhausted=exhausted
            ).model_dump_json()
        )
        return
    typer.echo(
        WatchResult(
            timed_out=timed_out, state=current, attempts=attempts, attempt_budget_exhausted=exhausted
        ).model_dump_json()
    )


register_mutation_commands(app, target_for_request, review_provider_for_target)


if __name__ == "__main__":
    app()
