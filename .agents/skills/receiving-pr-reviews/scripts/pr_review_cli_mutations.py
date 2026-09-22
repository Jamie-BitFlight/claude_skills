"""Authorized review-cycle validation and provider mutation commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Protocol

import typer

from pr_review_cli_actions import authorize_reply_and_resolve, authorized_action, load_current_snapshot
from pr_review_cli_provider_errors import provider_operation_or_exit
from pr_review_cli_target import GithubOption, HostOption, ProviderOption, ProviderTimeoutOption, RepoOption
from pr_review_contracts import (
    BatchReviewActions,
    ChangeRequestTarget,
    ReplyAction,
    ResolveAction,
    ReviewActionResult,
    TopLevelCommentAction,
)
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_state import (
    evaluate_review_complete,
    load_cycle,
    load_snapshot,
    record_completed_communication,
    record_completed_resolution,
    save_cycle,
    validate_cycle_coverage,
    validate_cycle_projection,
    validate_snapshot_context,
)
from pr_review_state_models import AuthorizedReviewAction

SnapshotFile = Annotated[Path, typer.Option(exists=True, dir_okay=False)]
StateFile = Annotated[Path, typer.Option(exists=True, dir_okay=False)]


def emit_batch_provider_error(input_id: str, replied: bool, message: str) -> None:
    """Emit one structured batch failure after a provider process error.

    Args:
        input_id: Canonical input whose action failed.
        replied: Whether its communication persisted before the failure.
        message: Complete provider error text prepared by the shared boundary.
    """
    typer.echo(json.dumps({"input_id": input_id, "replied": replied, "resolved": False, "error": message}))


def require_provider_confirmation(result: ReviewActionResult, operation: str) -> None:
    """Reject a provider response that did not confirm the requested mutation.

    Args:
        result: Provider-normalized mutation result.
        operation: Human-readable mutation name used in the error.

    Raises:
        ProviderResponseError: If the provider did not confirm success.
    """
    if not result.success:
        raise ProviderResponseError(f"provider did not confirm {operation}")


class TargetResolver(Protocol):
    """Callable target resolution contract shared with the entrypoint."""

    def __call__(
        self,
        provider: str | None,
        repo: str | None,
        host: str | None,
        github: str | None,
        number: int,
        *,
        command_timeout: float | None,
    ) -> ChangeRequestTarget:
        """Resolve one provider-neutral change-request target."""
        ...


class ProviderResolver(Protocol):
    """Callable adapter selection contract shared with the entrypoint."""

    def __call__(self, target: ChangeRequestTarget) -> ReviewProvider:
        """Return the adapter for a resolved target."""
        ...


def register_cycle_commands(
    app: typer.Typer, target_resolver: TargetResolver, provider_resolver: ProviderResolver
) -> None:
    """Register cycle validation and completion commands.

    Args:
        app: Root review CLI application.
        target_resolver: Provider-neutral target selector used by completion.
        provider_resolver: Deep adapter selector used by completion.
    """

    @app.command(name="validate-projection")
    def validate_projection(snapshot_file: SnapshotFile, state_file: StateFile) -> None:
        """Validate exhaustive typed dry-run state without authorizing mutation.

        Args:
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Exhaustive projected review-cycle JSON.
        """
        snapshot = load_snapshot(snapshot_file)
        cycle = load_cycle(state_file)
        validate_cycle_projection(snapshot, cycle)
        typer.echo(
            json.dumps({
                "validation": "projection_valid",
                "cycle_state": cycle.cycle_state,
                "cycle_terminal": cycle.cycle_terminal,
                "mutation_authorized": False,
            })
        )

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
        validate_cycle_coverage(snapshot, cycle)
        typer.echo(
            json.dumps({
                "validation": "action_ready",
                "cycle_state": cycle.cycle_state,
                "cycle_terminal": cycle.cycle_terminal,
            })
        )

    @app.command(name="complete-cycle")
    def complete_cycle(
        pr: Annotated[int, typer.Option()],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Evaluate and persist the REVIEW_COMPLETE terminal.

        Args:
            pr: Change-request number.
            snapshot_file: Most recent complete canonical snapshot JSON.
            state_file: Exhaustive per-input lifecycle state JSON.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        snapshot = provider_operation_or_exit(
            "complete-cycle",
            lambda: load_current_snapshot(
                target, snapshot_file, provider=selected_provider, command_timeout=provider_timeout_seconds
            ),
        )
        completed = evaluate_review_complete(snapshot, load_cycle(state_file))
        save_cycle(state_file, completed)
        typer.echo(json.dumps({"cycle_state": completed.cycle_state, "cycle_terminal": completed.cycle_terminal}))


def register_response_commands(
    app: typer.Typer, target_resolver: TargetResolver, provider_resolver: ProviderResolver
) -> None:
    """Register single-input authorized mutation commands.

    Args:
        app: Root review CLI application.
        target_resolver: Provider-neutral target selector.
        provider_resolver: Deep adapter selector.
    """

    @app.command(name="reply")
    def reply(
        pr: Annotated[int, typer.Option()],
        input_id: Annotated[str, typer.Option()],
        body: Annotated[str, typer.Option()],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Post one authorized inline reply.

        Args:
            pr: Change-request number.
            input_id: Canonical inbound input to answer.
            body: Evidence-bearing disposition.
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Complete review-cycle JSON.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        action, cycle = provider_operation_or_exit(
            "reply",
            lambda: authorized_action(
                target,
                snapshot_file,
                state_file,
                input_id,
                ReplyAction(body=body),
                provider=selected_provider,
                command_timeout=provider_timeout_seconds,
            ),
        )
        result = provider_operation_or_exit(
            "reply", lambda: selected_provider.act(target, action, command_timeout=provider_timeout_seconds)
        )
        require_provider_confirmation(result, "reply")
        save_cycle(state_file, record_completed_communication(cycle, input_id))
        typer.echo(json.dumps({"input_id": input_id, "replied": result.success}))

    @app.command(name="resolve")
    def resolve(
        pr: Annotated[int, typer.Option()],
        input_id: Annotated[str, typer.Option()],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Resolve one authorized input.

        Args:
            pr: Change-request number.
            input_id: Canonical inbound input to resolve.
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Cycle JSON recording completed communication.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        action, cycle = provider_operation_or_exit(
            "resolve",
            lambda: authorized_action(
                target,
                snapshot_file,
                state_file,
                input_id,
                ResolveAction(),
                provider=selected_provider,
                command_timeout=provider_timeout_seconds,
            ),
        )
        result = provider_operation_or_exit(
            "resolve", lambda: selected_provider.act(target, action, command_timeout=provider_timeout_seconds)
        )
        require_provider_confirmation(result, "resolution")
        save_cycle(state_file, record_completed_resolution(cycle, input_id))
        typer.echo(json.dumps({"input_id": input_id, "resolved": result.success}))

    @app.command(name="comment")
    def comment(
        pr: Annotated[int, typer.Option()],
        input_id: Annotated[str, typer.Option()],
        body: Annotated[str, typer.Option()],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        reference: Annotated[list[str] | None, typer.Option("--reference")] = None,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Post one authorized top-level response.

        Args:
            pr: Change-request number.
            input_id: Canonical inbound input to answer.
            body: Evidence-bearing disposition.
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Complete review-cycle JSON.
            reference: Stable provider references to include exactly once.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        action, cycle = provider_operation_or_exit(
            "comment",
            lambda: authorized_action(
                target,
                snapshot_file,
                state_file,
                input_id,
                TopLevelCommentAction(body=body, references=reference or []),
                provider=selected_provider,
                command_timeout=provider_timeout_seconds,
            ),
        )
        result = provider_operation_or_exit(
            "comment", lambda: selected_provider.act(target, action, command_timeout=provider_timeout_seconds)
        )
        require_provider_confirmation(result, "comment")
        save_cycle(state_file, record_completed_communication(cycle, input_id))
        typer.echo(json.dumps({"input_id": input_id, "commented": result.success}))

    @app.command(name="reply-and-resolve")
    def reply_and_resolve(
        pr: Annotated[int, typer.Option()],
        input_id: Annotated[str, typer.Option()],
        body: Annotated[str, typer.Option()],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Reply successfully before resolving the same authorized input.

        Args:
            pr: Change-request number.
            input_id: Canonical inbound inline input.
            body: Evidence-bearing disposition.
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Complete review-cycle JSON with communication pending.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        snapshot = provider_operation_or_exit(
            "reply-and-resolve",
            lambda: load_current_snapshot(
                target, snapshot_file, provider=selected_provider, command_timeout=provider_timeout_seconds
            ),
        )
        cycle = load_cycle(state_file)
        reply_action, resolve_action, _simulated = authorize_reply_and_resolve(snapshot, cycle, input_id, body)
        reply_result = provider_operation_or_exit(
            "reply-and-resolve",
            lambda: selected_provider.act(target, reply_action, command_timeout=provider_timeout_seconds),
        )
        require_provider_confirmation(reply_result, "reply")
        cycle = record_completed_communication(cycle, input_id)
        save_cycle(state_file, cycle)
        typer.echo(json.dumps({"input_id": input_id, "replied": reply_result.success, "resolved": False}))
        resolve_result = provider_operation_or_exit(
            "reply-and-resolve",
            lambda: selected_provider.act(target, resolve_action, command_timeout=provider_timeout_seconds),
        )
        require_provider_confirmation(resolve_result, "resolution")
        save_cycle(state_file, record_completed_resolution(cycle, input_id))
        typer.echo(
            json.dumps({"input_id": input_id, "replied": reply_result.success, "resolved": resolve_result.success})
        )


def register_batch_command(
    app: typer.Typer, target_resolver: TargetResolver, provider_resolver: ProviderResolver
) -> None:
    """Register the validated reply-and-resolve batch command.

    Args:
        app: Root review CLI application.
        target_resolver: Provider-neutral target selector.
        provider_resolver: Deep adapter selector.
    """

    @app.command(name="reply-and-resolve-batch")
    def reply_and_resolve_batch(
        pr: Annotated[int, typer.Option()],
        input_file: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
        snapshot_file: SnapshotFile,
        state_file: StateFile,
        github: GithubOption = None,
        provider: ProviderOption = None,
        repo: RepoOption = None,
        host: HostOption = None,
        provider_timeout_seconds: ProviderTimeoutOption = None,
    ) -> None:
        """Validate the whole batch, then stop on its first failed action.

        Args:
            pr: Change-request number.
            input_file: Complete batch of canonical input IDs and reply bodies.
            snapshot_file: Complete canonical snapshot JSON.
            state_file: Complete review-cycle JSON with communication pending.
            github: Legacy explicit GitHub repository.
            provider: Explicit provider selection.
            repo: Provider repository path.
            host: Bare provider hostname.
            provider_timeout_seconds: Positive provider subprocess bound.
        """
        entries = BatchReviewActions.model_validate(json.loads(input_file.read_text())).root
        target = target_resolver(provider, repo, host, github, pr, command_timeout=provider_timeout_seconds)
        selected_provider = provider_resolver(target)
        snapshot = provider_operation_or_exit(
            "reply-and-resolve-batch",
            lambda: load_current_snapshot(
                target, snapshot_file, provider=selected_provider, command_timeout=provider_timeout_seconds
            ),
        )
        cycle = load_cycle(state_file)
        planned: list[tuple[str, AuthorizedReviewAction, AuthorizedReviewAction]] = []
        simulated = cycle
        for entry in entries:
            reply_action, resolve_action, simulated = authorize_reply_and_resolve(
                snapshot, simulated, entry.input_id, entry.body
            )
            planned.append((entry.input_id, reply_action, resolve_action))
        for input_id, reply_action, resolve_action in planned:
            replied = False
            try:
                reply_result = provider_operation_or_exit(
                    "reply-and-resolve-batch",
                    lambda current_action=reply_action: selected_provider.act(
                        target, current_action, command_timeout=provider_timeout_seconds
                    ),
                    emit_error=lambda message, current_input_id=input_id: emit_batch_provider_error(
                        current_input_id, False, message
                    ),
                )
                require_provider_confirmation(reply_result, "reply")
                replied = True
                cycle = record_completed_communication(cycle, input_id)
                save_cycle(state_file, cycle)
                resolve_result = provider_operation_or_exit(
                    "reply-and-resolve-batch",
                    lambda current_action=resolve_action: selected_provider.act(
                        target, current_action, command_timeout=provider_timeout_seconds
                    ),
                    emit_error=lambda message, current_input_id=input_id: emit_batch_provider_error(
                        current_input_id, True, message
                    ),
                )
                require_provider_confirmation(resolve_result, "resolution")
                cycle = record_completed_resolution(cycle, input_id)
                save_cycle(state_file, cycle)
            except ProviderResponseError as exc:
                typer.echo(json.dumps({"input_id": input_id, "replied": replied, "resolved": False, "error": str(exc)}))
                raise typer.Exit(code=1) from exc
            typer.echo(json.dumps({"input_id": input_id, "replied": True, "resolved": True}))


def register_mutation_commands(
    app: typer.Typer, target_resolver: TargetResolver, provider_resolver: ProviderResolver
) -> None:
    """Register every cycle and mutation command through focused registrars.

    Args:
        app: Root review CLI application.
        target_resolver: Provider-neutral target selector.
        provider_resolver: Deep adapter selector.
    """
    register_cycle_commands(app, target_resolver, provider_resolver)
    register_response_commands(app, target_resolver, provider_resolver)
    register_batch_command(app, target_resolver, provider_resolver)
