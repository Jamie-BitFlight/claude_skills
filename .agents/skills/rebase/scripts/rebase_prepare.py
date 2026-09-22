"""Live revalidation and single-use command contracts for an accounted rebase."""

from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rebase_evidence import ExecutionMode, worktree_branch_owners
from rebase_states import WorkflowState

COMMAND_TIMEOUT_SECONDS = 20
TERMINATION_GRACE_SECONDS = 2
GIT_COMMAND_PREFIX_LENGTH = 2


@dataclass(frozen=True)
class PrepareRequest:
    """Immutable fields needed to authorize one replay command."""

    branch_ref: str
    branch_oid: str
    target_ref: str
    target_oid: str
    execution_worktree: str
    execution_mode: ExecutionMode
    merge_policy: str
    becomes_empty_option: str
    recovery_ref: str


class PrepareFailure(Exception):
    """A failed live gate that must not emit replay argv."""

    def __init__(self, message: str, state: WorkflowState) -> None:
        """Initialize one failure with its canonical workflow state."""
        super().__init__(message)
        self.state = state


@dataclass(frozen=True)
class CommandResult:
    """Complete result from one bounded Git inspection."""

    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str


def run_git(repository: Path, *arguments: str) -> CommandResult:
    """Run one bounded Git inspection in the execution worktree.

    Returns:
        Complete command evidence.
    """
    argv = ["git", *arguments]
    process = subprocess.Popen(
        argv, cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    )
    try:
        stdout, stderr = process.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        terminate_process_group(process)
        stdout, stderr = process.communicate()
        raise PrepareFailure(
            f"live preflight timed out: {argv}; stdout={stdout!r}; stderr={stderr!r}",
            WorkflowState.BLOCKED_PREFLIGHT_FAILED,
        ) from error
    return CommandResult(argv=argv, exit_code=process.returncode, stdout=stdout, stderr=stderr)


def terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Terminate a timed-out command and its descendants."""
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()


def require_success(result: CommandResult) -> str:
    """Return stdout or fail the live preparation gate with complete output."""
    if result.exit_code != 0:
        raise PrepareFailure(
            f"live preflight failed: {result.argv}; exit={result.exit_code}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}",
            WorkflowState.BLOCKED_PREFLIGHT_FAILED,
        )
    return result.stdout


def require_oid(repository: Path, ref: str, expected_oid: str) -> None:
    """Require one live ref to resolve to its planned immutable OID."""
    result = run_git(repository, "rev-parse", "--verify", f"{ref}^{{commit}}")
    observed_oid = require_success(result).strip()
    if observed_oid != expected_oid:
        raise PrepareFailure(f"live ref drift: {ref}", WorkflowState.REPLAN_REF_DRIFT)


def resolve_git_path(repository: Path, name: str) -> Path:
    """Resolve one live Git-managed path against the repository root.

    Returns:
        Absolute or repository-relative resolved Git path.
    """
    raw_path = Path(require_success(run_git(repository, "rev-parse", "--git-path", name)).strip())
    return raw_path if raw_path.is_absolute() else repository / raw_path


def require_operation_absence(repository: Path) -> None:
    """Reject every active rebase, merge, or cherry-pick marker."""
    for name in ("rebase-merge", "rebase-apply"):
        if resolve_git_path(repository, name).is_dir():
            raise PrepareFailure(f"active Git operation: {name}", WorkflowState.BLOCKED_GIT_STATE)
    for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD"):
        result = run_git(repository, "rev-parse", "--verify", "--quiet", name)
        if result.exit_code == 0:
            raise PrepareFailure(f"active Git operation: {name}", WorkflowState.BLOCKED_GIT_STATE)
        if result.exit_code != 1:
            raise PrepareFailure(
                f"operation-marker inspection failed: {result.argv}; exit={result.exit_code}; "
                f"stdout={result.stdout!r}; stderr={result.stderr!r}",
                WorkflowState.BLOCKED_PREFLIGHT_FAILED,
            )


def require_worktree_authority(repository: Path, request: PrepareRequest) -> None:
    """Recheck exact worktree ownership and execution mode."""
    observed_root = Path(require_success(run_git(repository, "rev-parse", "--show-toplevel")).strip()).resolve()
    planned_root = Path(request.execution_worktree).resolve()
    if observed_root != planned_root or repository.resolve() != planned_root:
        raise PrepareFailure("execution worktree drift", WorkflowState.BLOCKED_WORKTREE_IN_USE)

    worktrees = require_success(run_git(repository, "worktree", "list", "--porcelain"))
    owners = [path.resolve() for path in worktree_branch_owners(worktrees, request.branch_ref)]
    current_branch = require_success(run_git(repository, "symbolic-ref", "--quiet", "--short", "HEAD")).strip()
    planned_branch = request.branch_ref.removeprefix("refs/heads/")
    if request.execution_mode is ExecutionMode.CURRENT_BRANCH:
        if current_branch != planned_branch or owners != [planned_root]:
            raise PrepareFailure("current-branch worktree authority drift", WorkflowState.BLOCKED_WORKTREE_IN_USE)
    elif current_branch == planned_branch or owners:
        raise PrepareFailure("authorized branch-transfer authority drift", WorkflowState.BLOCKED_WORKTREE_IN_USE)


def derive_replay_argv(request: PrepareRequest) -> list[str]:
    """Derive the only replay command authorized by the typed plan.

    Returns:
        Canonical replay argument vector.
    """
    argv = ["git", "rebase", "--reapply-cherry-picks", f"--empty={request.becomes_empty_option}"]
    if request.merge_policy == "PRESERVE_TOPOLOGY":
        argv.append("--rebase-merges")
    argv.append(request.target_oid)
    if request.execution_mode is ExecutionMode.AUTHORIZED_BRANCH_TRANSFER:
        argv.append(request.branch_ref)
    return argv


def prepare_replay(request: PrepareRequest, repository: Path) -> list[str]:
    """Pass every live gate and return one canonical single-use replay argv.

    Returns:
        Canonical replay argument vector.
    """
    require_worktree_authority(repository, request)
    require_oid(repository, request.branch_ref, request.branch_oid)
    require_oid(repository, request.target_ref, request.target_oid)
    status = require_success(run_git(repository, "status", "--porcelain=v1", "--untracked-files=all"))
    if status:
        raise PrepareFailure("execution worktree is not clean", WorkflowState.BLOCKED_GIT_STATE)
    require_operation_absence(repository)
    recovery = require_success(
        run_git(repository, "rev-parse", "--verify", f"{request.recovery_ref}^{{commit}}")
    ).strip()
    if recovery != request.branch_oid:
        raise PrepareFailure("recovery ref drift", WorkflowState.BLOCKED_GIT_STATE)
    return derive_replay_argv(request)


def audit_single_use_trace(prepared_argv: list[str], commands: list[list[str]], terminal: WorkflowState) -> list[str]:
    """Reject unprepared replay argv and post-start history rewrites for one plan hash.

    Returns:
        Every single-use or freeze-contract failure.
    """
    failures: list[str] = []
    replay_positions = [
        index
        for index, command in enumerate(commands)
        if len(command) >= GIT_COMMAND_PREFIX_LENGTH
        and command[:GIT_COMMAND_PREFIX_LENGTH] == ["git", "rebase"]
        and not is_active_rebase_action(command)
    ]
    if len(replay_positions) != 1:
        failures.append("validated plan hash must authorize exactly one initial replay")
    elif commands[replay_positions[0]] != prepared_argv:
        failures.append("initial replay argv differs from validator-emitted argv")

    if replay_positions:
        first_replay = replay_positions[0]
        failures.extend(
            f"history mutation after single-use replay: {command}"
            for command in commands[first_replay + 1 :]
            if is_history_rewrite(command)
        )
    if terminal is WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED and not replay_positions:
        failures.append("validation-failed terminal lacks its initial replay evidence")
    return failures


def is_active_rebase_action(command: list[str]) -> bool:
    """Return whether a rebase command continues, skips, or aborts the active replay."""
    return any(option in command for option in ("--continue", "--skip", "--abort"))


def is_history_rewrite(command: list[str]) -> bool:
    """Return whether a post-start command rewrites history or a ref."""
    if len(command) < GIT_COMMAND_PREFIX_LENGTH or command[0] != "git":
        return False
    if command[1] == "rebase" and not is_active_rebase_action(command):
        return True
    if command[1] in {"reset", "update-ref"}:
        return True
    if command[1] == "branch" and any(option in command for option in ("-f", "--force", "-D", "-M")):
        return True
    if command[1] == "switch" and "-C" in command:
        return True
    return command[1] == "checkout" and "-B" in command
