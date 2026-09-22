"""Live revalidation and single-use command contracts for an accounted rebase."""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from rebase_evidence import worktree_branch_owners
from rebase_models import (
    CommandResult,
    ExecutionMode,
    MergePolicy,
    PlanSha256,
    PrepareRequest,
    ReplayExecution,
    ReplayReceipt,
)
from rebase_states import WorkflowState

COMMAND_TIMEOUT_SECONDS = 20
TERMINATION_GRACE_SECONDS = 2


class PrepareFailure(Exception):
    """A failed live gate that must not emit replay argv."""

    def __init__(self, message: str, state: WorkflowState) -> None:
        """Initialize one failure with its canonical workflow state."""
        super().__init__(message)
        self.state = state


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
    if result.exit_code != 0 or result.stdout.strip() != expected_oid:
        raise PrepareFailure(
            f"live ref drift: {result.argv}; exit={result.exit_code}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}",
            WorkflowState.REPLAN_REF_DRIFT,
        )


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
    if request.keep_empty:
        argv.append("--keep-empty")
    if request.merge_policy is MergePolicy.PRESERVE_TOPOLOGY:
        argv.append("--rebase-merges")
    argv.append(request.target_oid)
    if request.execution_mode is ExecutionMode.AUTHORIZED_BRANCH_TRANSFER:
        argv.append(request.branch_ref.removeprefix("refs/heads/"))
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
    recovery = run_git(repository, "rev-parse", "--verify", f"{request.recovery_ref}^{{commit}}")
    if recovery.exit_code != 0 or recovery.stdout.strip() != request.branch_oid:
        raise PrepareFailure(
            f"recovery ref drift: {recovery.argv}; exit={recovery.exit_code}; "
            f"stdout={recovery.stdout!r}; stderr={recovery.stderr!r}",
            WorkflowState.BLOCKED_GIT_STATE,
        )
    return derive_replay_argv(request)


def replay_receipt_path(repository: Path, plan_sha256: str) -> Path:
    """Resolve the durable worktree-local receipt path for one plan hash.

    Returns:
        Git-managed receipt path outside the worktree.
    """
    return resolve_git_path(repository, f"rebase-skill/receipts/{plan_sha256}.json")


def consume_replay_authorization(path: Path, receipt: ReplayReceipt) -> None:
    """Atomically persist single use before starting the destructive replay."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise PrepareFailure(
            f"validated plan hash was already consumed: {receipt.plan_sha256}", WorkflowState.BLOCKED_GIT_STATE
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as receipt_file:
        receipt_file.write(receipt.model_dump_json())
        receipt_file.write("\n")
        receipt_file.flush()
        os.fsync(receipt_file.fileno())


def execute_replay(request: PrepareRequest, repository: Path, plan_sha256: PlanSha256) -> ReplayExecution:
    """Consume one plan hash, then execute only its canonical argv once.

    Returns:
        Durable receipt path and complete replay command result.
    """
    receipt_path = replay_receipt_path(repository, plan_sha256)
    if receipt_path.exists():
        raise PrepareFailure(
            f"validated plan hash was already consumed: {plan_sha256}", WorkflowState.BLOCKED_GIT_STATE
        )
    argv = prepare_replay(request, repository)
    receipt = ReplayReceipt(plan_sha256=plan_sha256, argv=argv)
    consume_replay_authorization(receipt_path, receipt)
    command = run_git(repository, *argv[1:])
    return ReplayExecution(receipt_path=str(receipt_path), command=command)
