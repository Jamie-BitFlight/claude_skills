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

from pr_review_cli_actions import authorize_reply_and_resolve, authorized_action
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
from pr_review_state import (
    load_cycle,
    load_snapshot,
    record_completed_communication,
    record_completed_resolution,
    save_cycle,
    validate_cycle_coverage,
    validate_snapshot_context,
)
from pr_review_state_models import AuthorizedReviewAction
from pr_review_subprocess import DEFAULT_COMMAND_TIMEOUT_SECONDS

app = typer.Typer(help="Review-state operations through a validated provider interface.")

DEFAULT_WATCH_INTERVAL_SECONDS = 90
DEFAULT_WATCH_TIMEOUT_SECONDS = 270
DEFAULT_WATCH_MAX_ATTEMPTS = 4


def validate_github_option(value: str | None) -> str | None:
    """Validate an explicit GitHub owner/repository value.

    Args:
        value: Optional ``owner/repo`` CLI value.

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

    Args:
        github: Explicit ``owner/repo`` value, or ``None`` for detection.
        gh_timeout: Positive bound for repository detection.

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

    Args:
        github: Explicit ``owner/repo`` value, or ``None`` for detection.
        pr: Pull-request number.
        gh_timeout: Positive bound for repository detection.

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


def parse_pr_list(value: str) -> list[int]:
    """Parse positive comma-separated pull-request numbers.

    Args:
        value: Comma-separated CLI value.

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
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Fetch complete canonical review snapshots.

    Args:
        pr: One or more comma-separated pull-request numbers.
        github: Explicit repository identity, or detection when omitted.
        summary: Emit compact status output instead of full action evidence.
        max_body: Optional visible body truncation bound.
        gh_timeout_seconds: Positive bound for every GitHub subprocess.
    """
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
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Sample complete snapshots within one deadline and attempt budget.

    Args:
        pr: Pull-request number.
        github: Explicit repository identity, or detection when omitted.
        summary: Emit compact status output instead of the full snapshot.
        max_body: Optional visible body truncation bound.
        interval_seconds: Delay between complete snapshots.
        timeout_seconds: Overall sampling window.
        max_attempts: Maximum complete snapshots in this call.
        gh_timeout_seconds: Positive bound for every GitHub subprocess.
    """
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


@app.command(name="validate-cycle")
def validate_cycle(snapshot_file: SnapshotFile, state_file: StateFile) -> None:
    """Validate complete-set cycle evidence without performing a mutation.

    Args:
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Assessment and implementation cycle JSON.
    """
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    validate_snapshot_context(snapshot, cycle)
    inputs, assessments, clusters = validate_cycle_coverage(snapshot, cycle)
    typer.echo(
        json.dumps({
            "snapshot_fingerprint": snapshot.snapshot_fingerprint,
            "inputs": len(inputs),
            "assessments": len(assessments),
            "clusters": len(clusters),
            "cycle_state": cycle.cycle_state,
            "cycle_terminal": cycle.cycle_terminal,
        })
    )


@app.command()
def reply(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Post one authorized inline reply.

    Args:
        pr: Pull-request number.
        input_id: Canonical inbound input to answer.
        body: Evidence-bearing disposition.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON.
        github: Explicit repository identity, or detection when omitted.
        gh_timeout_seconds: Positive bound for the GitHub subprocess.
    """
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action, cycle = authorized_action(target, snapshot_file, state_file, input_id, ReplyAction(body=body))
    result = review_provider().act(target, action, command_timeout=gh_timeout_seconds)
    save_cycle(state_file, record_completed_communication(cycle, input_id))
    typer.echo(json.dumps(result.raw))


@app.command()
def resolve(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Resolve one authorized input.

    Args:
        pr: Pull-request number.
        input_id: Canonical inbound input to resolve.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Cycle JSON recording completed communication.
        github: Explicit repository identity, or detection when omitted.
        gh_timeout_seconds: Positive bound for the GitHub subprocess.
    """
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action, cycle = authorized_action(target, snapshot_file, state_file, input_id, ResolveAction())
    result = review_provider().act(target, action, command_timeout=gh_timeout_seconds)
    save_cycle(state_file, record_completed_resolution(cycle, input_id))
    typer.echo(json.dumps(result.raw))


@app.command(name="comment")
def comment(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    reference: Annotated[list[str] | None, typer.Option("--reference")] = None,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Post one authorized top-level response.

    Args:
        pr: Pull-request number.
        input_id: Canonical inbound input to answer.
        body: Evidence-bearing disposition.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON.
        reference: Stable provider references to include exactly once.
        github: Explicit repository identity, or detection when omitted.
        gh_timeout_seconds: Positive bound for the GitHub subprocess.
    """
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    action, cycle = authorized_action(
        target, snapshot_file, state_file, input_id, TopLevelCommentAction(body=body, references=reference or [])
    )
    result = review_provider().act(target, action, command_timeout=gh_timeout_seconds)
    save_cycle(state_file, record_completed_communication(cycle, input_id))
    typer.echo(json.dumps(result.raw))


@app.command(name="reply-and-resolve")
def reply_and_resolve(
    pr: Annotated[int, typer.Option()],
    input_id: Annotated[str, typer.Option()],
    body: Annotated[str, typer.Option()],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Reply successfully before resolving the same authorized input.

    Args:
        pr: Pull-request number.
        input_id: Canonical inbound inline input.
        body: Evidence-bearing disposition.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON with communication pending.
        github: Explicit repository identity, or detection when omitted.
        gh_timeout_seconds: Positive bound for each GitHub subprocess.
    """
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    if snapshot.target != target:
        raise ProviderResponseError("snapshot target does not match command target")
    reply_action, resolve_action, _simulated = authorize_reply_and_resolve(snapshot, cycle, input_id, body)
    provider = review_provider()
    typer.echo(json.dumps(provider.act(target, reply_action, command_timeout=gh_timeout_seconds).raw))
    cycle = record_completed_communication(cycle, input_id)
    save_cycle(state_file, cycle)
    typer.echo(json.dumps(provider.act(target, resolve_action, command_timeout=gh_timeout_seconds).raw))
    cycle = record_completed_resolution(cycle, input_id)
    save_cycle(state_file, cycle)


@app.command(name="reply-and-resolve-batch")
def reply_and_resolve_batch(
    pr: Annotated[int, typer.Option()],
    input_file: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    snapshot_file: SnapshotFile,
    state_file: StateFile,
    github: GithubOption = None,
    gh_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    """Validate the whole batch, then stop on its first failed action.

    Args:
        pr: Pull-request number.
        input_file: Complete batch of canonical input IDs and reply bodies.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON with communication pending.
        github: Explicit repository identity, or detection when omitted.
        gh_timeout_seconds: Positive bound for each GitHub subprocess.
    """
    entries = BatchReviewActions.model_validate(json.loads(input_file.read_text())).root
    target = target_for_github(github, pr, gh_timeout=gh_timeout_seconds)
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    if snapshot.target != target:
        raise ProviderResponseError("snapshot target does not match command target")
    planned: list[tuple[str, AuthorizedReviewAction, AuthorizedReviewAction]] = []
    simulated = cycle
    for entry in entries:
        reply_action, resolve_action, simulated = authorize_reply_and_resolve(
            snapshot, simulated, entry.input_id, entry.body
        )
        planned.append((entry.input_id, reply_action, resolve_action))
    provider = review_provider()
    for input_id, reply_action, resolve_action in planned:
        replied = False
        try:
            provider.act(target, reply_action, command_timeout=gh_timeout_seconds)
            replied = True
            cycle = record_completed_communication(cycle, input_id)
            save_cycle(state_file, cycle)
            provider.act(target, resolve_action, command_timeout=gh_timeout_seconds)
            cycle = record_completed_resolution(cycle, input_id)
            save_cycle(state_file, cycle)
        except (ProviderResponseError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            typer.echo(json.dumps({"input_id": input_id, "replied": replied, "resolved": False, "error": str(exc)}))
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps({"input_id": input_id, "replied": True, "resolved": True}))


if __name__ == "__main__":
    app()
