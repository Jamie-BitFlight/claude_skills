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
"""Canonical review-state CLI with authorized GitHub mutations."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from pr_review_contracts import (
    BatchReviewActions,
    ChangeRequestTarget,
    ReplyAction,
    RepositoryTarget,
    ResolveAction,
    TopLevelCommentAction,
)
from pr_review_gh import RESOLVE_THREAD_MUTATION, build_fetch_result, detect_repo_identity, run_gh
from pr_review_github_provider import GitHubProvider
from pr_review_models import WatchResult, WatchSummary
from pr_review_output import board_entry, summarize
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_state import authorize_action, load_cycle, load_snapshot
from pr_review_state_models import AuthorizedReviewAction

app = typer.Typer(help="Review-state operations through a validated provider interface.")

DEFAULT_WATCH_INTERVAL_SECONDS = 90
DEFAULT_WATCH_TIMEOUT_SECONDS = 270
DEFAULT_WATCH_MAX_ATTEMPTS = 4


def validate_github_option(value: str | None) -> str | None:
    """Validate an explicit GitHub owner/repository value.

    Returns:
        The validated option, or ``None`` when detection is requested.
    """
    if value is None:
        return None
    owner, separator, repo = value.partition("/")
    if not separator or not owner or not repo or "/" in repo:
        raise typer.BadParameter("must be 'owner/repo' -- exactly one '/', with both halves non-empty")
    return value


GithubOption = Annotated[
    str | None,
    typer.Option(
        "--github",
        help="Target repository as 'owner/repo'. Detected via gh repo view when omitted.",
        callback=validate_github_option,
    ),
]


def owner_repo(github: str | None, *, gh_timeout: float | None) -> tuple[str, str]:
    """Resolve an explicit or detected GitHub repository.

    Returns:
        The repository owner and name.
    """
    if github is not None:
        owner, repo = github.split("/", 1)
        return owner, repo
    try:
        return detect_repo_identity(gh_timeout=gh_timeout)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValidationError) as exc:
        typer.echo(
            f"Could not detect this checkout's GitHub repository via gh repo view ({exc}). "
            "Pass --github owner/repo to specify it explicitly.",
            err=True,
        )
        raise typer.Exit(code=1) from exc


def target_for_github(github: str | None, pr: int, *, gh_timeout: float | None) -> ChangeRequestTarget:
    """Resolve one GitHub pull-request target.

    Returns:
        The provider-neutral target identity.
    """
    owner, repo = owner_repo(github, gh_timeout=gh_timeout)
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name=f"{owner}/{repo}"), number=pr
    )


def review_provider() -> ReviewProvider:
    """Construct the GitHub adapter behind the provider interface.

    Returns:
        A provider implementing canonical snapshots and authorized actions.
    """
    return GitHubProvider(
        snapshot_loader=build_fetch_result, command_runner=run_gh, resolve_query=RESOLVE_THREAD_MUTATION
    )


def authorized_action(
    target: ChangeRequestTarget,
    snapshot_file: Path,
    state_file: Path,
    input_id: str,
    action: ReplyAction | ResolveAction | TopLevelCommentAction,
) -> AuthorizedReviewAction:
    """Load and validate one current pre-action gate.

    Returns:
        The action bound to validated snapshot and cycle evidence.
    """
    snapshot = load_snapshot(snapshot_file)
    if snapshot.target != target:
        raise ProviderResponseError("snapshot target does not match command target")
    return authorize_action(snapshot, load_cycle(state_file), input_id, action)


def parse_pr_list(value: str) -> list[int]:
    """Parse positive comma-separated pull-request numbers.

    Returns:
        The validated pull-request numbers in input order.
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


@app.command()
def fetch(
    pr: Annotated[str, typer.Option(help="Pull request number(s), comma-separated.")],
    github: GithubOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Fetch complete canonical review snapshots."""
    numbers = parse_pr_list(pr)
    first_target = target_for_github(github, numbers[0], gh_timeout=gh_timeout_seconds)
    provider = review_provider()
    if len(numbers) == 1 and not summary:
        typer.echo(provider.snapshot(first_target, deadline=None, command_timeout=gh_timeout_seconds).model_dump_json())
        return
    for number in numbers:
        target = first_target.model_copy(update={"number": number})
        result = provider.snapshot(target, deadline=None, command_timeout=gh_timeout_seconds)
        output = summarize(result, pr=number, max_body=max_body) if summary else board_entry(number, result)
        typer.echo(output.model_dump_json())


@app.command()
def watch(
    pr: Annotated[int, typer.Option(help="Pull request number.")],
    github: GithubOption = None,
    summary: SummaryOption = False,
    max_body: MaxBodyOption = None,
    interval_seconds: Annotated[int, typer.Option(min=1)] = DEFAULT_WATCH_INTERVAL_SECONDS,
    timeout_seconds: Annotated[int, typer.Option(min=0)] = DEFAULT_WATCH_TIMEOUT_SECONDS,
    max_attempts: Annotated[int, typer.Option(min=1)] = DEFAULT_WATCH_MAX_ATTEMPTS,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Sample complete snapshots within one deadline and attempt budget."""
    deadline = time.monotonic() + timeout_seconds
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    provider = review_provider()
    current = provider.snapshot(
        target, deadline=deadline if timeout_seconds > 0 else None, command_timeout=gh_timeout_seconds
    )
    attempts = 1
    poll_attempts = 0
    last_poll_ok = True
    while not current.has_outstanding_work() and attempts < max_attempts:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_seconds, remaining))
        if remaining <= interval_seconds:
            break
        poll_attempts += 1
        attempts += 1
        try:
            current = provider.snapshot(target, deadline=deadline, command_timeout=gh_timeout_seconds)
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
    timed_out = not current.has_outstanding_work()
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


SnapshotFile = Annotated[Path, typer.Option(exists=True, dir_okay=False)]
StateFile = Annotated[Path, typer.Option(exists=True, dir_okay=False)]


@app.command()
def reply(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Post one authorized inline reply."""
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action = authorized_action(target, snapshot_file, state_file, input_id, ReplyAction(body=body))
    typer.echo(json.dumps(review_provider().act(target, action, command_timeout=gh_timeout_seconds).raw))


@app.command()
def resolve(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Resolve one authorized input."""
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action = authorized_action(target, snapshot_file, state_file, input_id, ResolveAction())
    typer.echo(json.dumps(review_provider().act(target, action, command_timeout=gh_timeout_seconds).raw))


@app.command(name="comment")
def comment(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    reference: Annotated[list[str] | None, typer.Option("--reference")] = None,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Post one authorized top-level response."""
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action = authorized_action(
        target, snapshot_file, state_file, input_id, TopLevelCommentAction(body=body, references=reference or [])
    )
    typer.echo(json.dumps(review_provider().act(target, action, command_timeout=gh_timeout_seconds).raw))


@app.command(name="reply-and-resolve")
def reply_and_resolve(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Reply successfully before resolving the same authorized input."""
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    reply_action = authorize_action(snapshot, cycle, input_id, ReplyAction(body=body))
    resolve_action = authorize_action(snapshot, cycle, input_id, ResolveAction())
    provider = review_provider()
    typer.echo(json.dumps(provider.act(target, reply_action, command_timeout=gh_timeout_seconds).raw))
    typer.echo(json.dumps(provider.act(target, resolve_action, command_timeout=gh_timeout_seconds).raw))


@app.command(name="reply-and-resolve-batch")
def reply_and_resolve_batch(
    pr: Annotated[int, typer.Option()],
    input_file: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float | None, typer.Option(min=0)] = None,
) -> None:
    """Validate the whole batch, then stop on its first failed action."""
    entries = BatchReviewActions.model_validate(json.loads(input_file.read_text())).root
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    planned = [
        (
            entry.input_id,
            authorize_action(snapshot, cycle, entry.input_id, ReplyAction(body=entry.body)),
            authorize_action(snapshot, cycle, entry.input_id, ResolveAction()),
        )
        for entry in entries
    ]
    provider = review_provider()
    for input_id, reply_action, resolve_action in planned:
        replied = False
        try:
            provider.act(target, reply_action, command_timeout=gh_timeout_seconds)
            replied = True
            provider.act(target, resolve_action, command_timeout=gh_timeout_seconds)
        except (ProviderResponseError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            typer.echo(json.dumps({"input_id": input_id, "replied": replied, "resolved": False, "error": str(exc)}))
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps({"input_id": input_id, "replied": True, "resolved": True}))


if __name__ == "__main__":
    app()
