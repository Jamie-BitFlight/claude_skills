"""Command-line operations for the managed rebase plan interface."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from rebase_capture import capture_rebase
from rebase_contracts import RebasePlan
from rebase_finalize import build_managed_plan
from rebase_managed import atomic_write, managed_root, resolve_managed_plan
from rebase_models import CaptureRequest, FinalizeSemantics, PrepareRequest
from rebase_prepare import PrepareFailure, execute_replay, run_git
from rebase_states import WORKFLOW_STATE_DEFINITIONS, WorkflowState


def create_parser() -> argparse.ArgumentParser:
    """Create the managed rebase CLI parser.

    Returns:
        Parser for every managed operation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="Validate one JSON plan artifact.")
    validate_parser.add_argument("plan", type=Path)
    capture_parser = subparsers.add_parser("capture", help="Capture immutable Git evidence under managed state.")
    capture_parser.add_argument("--branch", required=True)
    capture_parser.add_argument("--target", required=True)
    capture_parser.add_argument("--expected-target-oid")
    finalize_parser = subparsers.add_parser("finalize", help="Merge semantic judgments into one managed plan.")
    finalize_parser.add_argument("capture_id")
    finalize_parser.add_argument("--semantics-json", required=True)
    finalize_parser.add_argument("--approval-receipt", action="append", default=[])
    execute_parser = subparsers.add_parser("execute", help="Consume one plan hash and run its replay argv once.")
    execute_parser.add_argument("plan", type=Path)
    execute_parser.add_argument("--expected-sha256", required=True)
    subparsers.add_parser("schema", help="Print the complete JSON Schema for a plan artifact.")
    subparsers.add_parser("states", help="Print the canonical workflow-state contract.")
    path_state_parser = subparsers.add_parser("path-state", help="Observe one resolved Git path.")
    path_state_parser.add_argument("path", type=Path)
    return parser


def emit_json(value: object) -> None:
    """Emit compact JSON for the agent-only consumer."""
    print(json.dumps(value, separators=(",", ":"), sort_keys=True))


def raw_publication_requires_approval(raw: bytes) -> bool:
    """Return whether raw plan data declares publication."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    publication = data.get("publication")
    return isinstance(publication, dict) and bool(
        publication.get("configured_upstream") or publication.get("remote_refs_containing_old_tip")
    )


def publication_terminal() -> dict[str, object]:
    """Return the fail-closed publication terminal for this harness."""
    return {
        "error": "published-history replay requires a harness-owned human approval channel",
        "state": WorkflowState.NEEDS_USER_DECISION,
        "status": "DECISION_REQUIRED",
        "terminal": True,
    }


def validate_plan(path: Path) -> int:
    """Validate one plan file and emit a structured result.

    Returns:
        Process exit code.
    """
    try:
        raw = path.read_bytes()
        if raw_publication_requires_approval(raw):
            emit_json(publication_terminal())
            return 1
        plan = RebasePlan.model_validate_json(raw)
    except ValidationError as error:
        emit_json({
            "errors": json.loads(error.json(include_url=False)),
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
        })
        return 1
    except OSError as error:
        emit_json({"error": str(error), "state": WorkflowState.PLAN_INVALID, "status": "ERROR"})
        return 2
    if not plan.has_publication_approval():
        emit_json(publication_terminal())
        return 1
    emit_json({
        "plan_id": plan.plan_id,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "state": plan.ready_state,
        "status": "VALID",
    })
    return 0


def load_unchanged_plan(path: Path, expected_sha256: str) -> tuple[RebasePlan, str] | int:
    """Load an unchanged schema-valid plan artifact.

    Returns:
        Validated plan and digest, or an emitted-error exit code.
    """
    try:
        raw = path.read_bytes()
    except OSError as error:
        emit_json({"error": str(error), "state": WorkflowState.PLAN_INVALID, "status": "ERROR"})
        return 2
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        emit_json({
            "error": "plan artifact SHA-256 differs from the validated hash",
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
        })
        return 1
    if raw_publication_requires_approval(raw):
        emit_json(publication_terminal())
        return 1
    try:
        plan = RebasePlan.model_validate_json(raw)
    except ValidationError as error:
        emit_json({
            "errors": json.loads(error.json(include_url=False)),
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
        })
        return 1
    if not plan.has_publication_approval():
        emit_json(publication_terminal())
        return 1
    return plan, actual_sha256


def prepare_request(plan: RebasePlan) -> PrepareRequest:
    """Project a validated plan into the immutable execution request.

    Returns:
        Frozen replay preparation request.
    """
    return PrepareRequest(
        branch_ref=plan.branch.ref,
        branch_oid=plan.branch.oid,
        target_ref=plan.target.ref,
        target_oid=plan.target.oid,
        execution_worktree=plan.execution_worktree,
        execution_mode=plan.execution_mode,
        merge_policy=plan.merge_policy,
        becomes_empty_option=plan.becomes_empty_option,
        keep_empty=any(not candidate.paths for candidate in plan.candidates),
        recovery_ref=plan.recovery_ref,
        required_preflights=plan.required_preflights,
    )


def finalize_plan(capture_id: str, semantics_json: str, approval_receipts: list[str]) -> int:
    """Create one managed plan from captured evidence and semantic-only input.

    Returns:
        Process exit code.
    """
    try:
        semantics = FinalizeSemantics.model_validate_json(semantics_json)
    except ValidationError as error:
        emit_json({
            "errors": json.loads(error.json(include_url=False)),
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
            "terminal": True,
        })
        return 1
    raw_plan, terminal, exit_code = build_managed_plan(
        Path.cwd(), capture_id, semantics, [Path(path) for path in approval_receipts]
    )
    if raw_plan is None:
        emit_json(terminal)
        return exit_code
    try:
        plan = RebasePlan.model_validate(raw_plan)
    except ValidationError as error:
        recovery_ref = str(raw_plan["recovery_ref"])
        branch = raw_plan["branch"]
        if isinstance(branch, dict) and isinstance(branch.get("oid"), str):
            observed = run_git(Path.cwd(), "rev-parse", "--verify", f"{recovery_ref}^{{commit}}")
            if observed.exit_code == 0 and observed.stdout.strip() == branch["oid"]:
                run_git(Path.cwd(), "update-ref", "-d", recovery_ref, branch["oid"])
        emit_json({
            "errors": json.loads(error.json(include_url=False)),
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
            "terminal": True,
        })
        return 1
    payload = plan.model_dump_json().encode() + b"\n"
    sha256 = hashlib.sha256(payload).hexdigest()
    plan_path = managed_root(Path.cwd()) / "plans" / f"{plan.plan_id}.json"
    try:
        atomic_write(plan_path, payload)
    except (FileExistsError, OSError) as error:
        emit_json({
            "error": str(error),
            "state": WorkflowState.BLOCKED_GIT_STATE,
            "status": "BLOCKED",
            "terminal": True,
        })
        return 1
    emit_json({
        "plan_id": plan.plan_id,
        "plan_path": str(plan_path),
        "sha256": sha256,
        "state": WorkflowState.READY_TO_REBASE,
        "status": "FINALIZED",
        "terminal": False,
    })
    return 0


def execute_plan(path: Path, expected_sha256: str) -> int:
    """Consume one unchanged plan hash and execute its replay once.

    Returns:
        Process exit code.
    """
    try:
        managed_path = resolve_managed_plan(Path.cwd(), str(path))
    except (OSError, ValueError) as error:
        emit_json({"error": str(error), "state": WorkflowState.PLAN_INVALID, "status": "INVALID", "terminal": True})
        return 1
    loaded = load_unchanged_plan(managed_path, expected_sha256)
    if isinstance(loaded, int):
        return loaded
    plan, actual_sha256 = loaded
    try:
        execution = execute_replay(prepare_request(plan), Path.cwd(), actual_sha256)
    except PrepareFailure as error:
        emit_json({"error": str(error), "state": error.state, "status": "BLOCKED"})
        return 1
    command = execution.command
    emit_json({
        "argv": command.argv,
        "plan_id": plan.plan_id,
        "receipt_path": execution.receipt_path,
        "replay": command.model_dump(mode="json"),
        "sha256": actual_sha256,
        "status": "REPLAY_FINISHED" if command.exit_code == 0 else "REPLAY_STOPPED",
    })
    return 0 if command.exit_code == 0 else 1


def main() -> int:
    """Run the selected managed rebase operation.

    Returns:
        Process exit code.
    """
    args = create_parser().parse_args()
    if args.command == "validate":
        return validate_plan(args.plan)
    if args.command == "capture":
        request = CaptureRequest(branch=args.branch, target=args.target, expected_target_oid=args.expected_target_oid)
        output, exit_code = capture_rebase(Path.cwd(), request)
        emit_json(output)
        return exit_code
    if args.command == "finalize":
        return finalize_plan(args.capture_id, args.semantics_json, args.approval_receipt)
    if args.command == "execute":
        return execute_plan(args.plan, args.expected_sha256)
    if args.command == "schema":
        emit_json(RebasePlan.model_json_schema())
    elif args.command == "path-state":
        emit_json({"path": str(args.path), "present": args.path.exists()})
    else:
        emit_json([definition.model_dump(mode="json") for definition in WORKFLOW_STATE_DEFINITIONS])
    return 0
