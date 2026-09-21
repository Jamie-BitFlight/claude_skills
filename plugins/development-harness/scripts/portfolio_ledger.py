#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.12.3",
# ]
#
# [tool.ty.environment]
# extra-paths = [".."]
# ///
"""Agent-facing compact-JSON CLI for the canonical portfolio merge ledger."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO, TypeVar

from pydantic import BaseModel, ConfigDict

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from dh_core.portfolio_ledger import (
    CANONICAL_LEDGER_PATH,
    CANONICAL_LOCK_PATH,
    Addendum,
    CommandEvidence,
    EvidenceReceipt,
    Inventory,
    LedgerRefusal,
    Mirror,
    PortfolioLedger,
    PortfolioLedgerRuntime,
    PortfolioLedgerService,
    RecoveryEvidence,
    Reservation,
)

COMMANDS = (
    "initialize",
    "inventory",
    "reservation-acquire",
    "reservation-release",
    "reservation-invalidate",
    "reservation-recover",
    "implementation-admit",
    "integrate",
    "aspect-certify",
    "addendum-record",
    "parent-certify",
    "verify-mirror",
    "restore",
    "show",
)


class RequestModel(BaseModel):
    """Strict base for validated CLI request payloads."""

    model_config = ConfigDict(extra="forbid")
    mirror_url: str | None = None


class InventoryRequest(RequestModel):
    """Typed inventory request."""

    car_id: str
    actor_id: str
    inventory: Inventory


class ReservationAcquireRequest(RequestModel):
    """Typed reservation acquisition request."""

    car_id: str
    actor_id: str
    reservation: Reservation


class ReservationConclusionRequest(RequestModel):
    """Typed reservation release or invalidation request."""

    car_id: str
    reservation_id: str
    actor_id: str
    at: datetime
    receipt_sha256: str
    receipt_path: str


class ReservationRecoverRequest(RequestModel):
    """Typed stale reservation recovery request."""

    car_id: str
    reservation_id: str
    evidence: RecoveryEvidence


class ImplementationAdmitRequest(RequestModel):
    """Typed implementation admission request."""

    car_id: str
    checker_id: str
    implementation_sha: str
    expected_base_git_sha: str
    expected_upstream_git_sha: str
    report: str
    receipt: EvidenceReceipt
    commands: list[CommandEvidence]
    at: datetime


class IntegrateRequest(RequestModel):
    """Typed integration request."""

    car_id: str
    integrator_id: str
    integration_sha: str
    expected_implementation_sha: str
    receipt: EvidenceReceipt
    at: datetime


class AspectCertifyRequest(RequestModel):
    """Typed aspect certification request."""

    car_id: str
    checker_id: str
    report: str
    receipt: EvidenceReceipt
    at: datetime


class AddendumRecordRequest(RequestModel):
    """Typed addendum request."""

    addendum: Addendum


class ParentCertifyRequest(RequestModel):
    """Typed parent certification request."""

    checker_id: str
    revision: str
    report: str
    receipt: EvidenceReceipt


class RestoreRequest(RequestModel):
    """Typed mirror restoration request."""

    mirror_url: str
    expected_sha256: str


TRANSITION_REQUEST_MODELS: dict[str, type[RequestModel]] = {
    "inventory": InventoryRequest,
    "reservation-acquire": ReservationAcquireRequest,
    "reservation-release": ReservationConclusionRequest,
    "reservation-invalidate": ReservationConclusionRequest,
    "reservation-recover": ReservationRecoverRequest,
    "implementation-admit": ImplementationAdmitRequest,
    "integrate": IntegrateRequest,
    "aspect-certify": AspectCertifyRequest,
    "addendum-record": AddendumRecordRequest,
    "parent-certify": ParentCertifyRequest,
}

RequestT = TypeVar("RequestT", bound=BaseModel)


def parser() -> argparse.ArgumentParser:
    """Build the command parser.

    Returns:
        Configured parser.
    """
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--ledger", type=Path, default=CANONICAL_LEDGER_PATH)
    result.add_argument("--lock", type=Path, default=CANONICAL_LOCK_PATH)
    result.add_argument("--evidence-root", type=Path, default=Path.cwd())
    result.add_argument("command", choices=COMMANDS)
    result.add_argument("--request", type=Path)
    return result


def output_json(value: object, *, stream: TextIO = sys.stdout) -> None:
    """Emit one complete compact JSON value.

    Args:
        value: JSON-serializable output.
        stream: Output stream.
    """
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str), file=stream)


def request_json(path: Path | None, command: str, model: type[RequestT]) -> RequestT:
    """Read a complete request object for one mutating command.

    Args:
        path: Request file path.
        command: Command requiring the file.
        model: Pydantic model that immediately validates the boundary payload.

    Returns:
        Parsed typed request object.

    Raises:
        LedgerRefusal: When no request path or a non-object payload is provided.
    """
    if path is None:
        raise LedgerRefusal(f"{command} requires --request")
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def transition(command: str, ledger: PortfolioLedger, request: RequestModel, *, evidence_root: Path) -> PortfolioLedger:
    """Dispatch one complete request through the public transition service.

    Returns:
        Transitioned ledger.
    """
    service = PortfolioLedgerService(ledger, evidence_root=evidence_root)
    if isinstance(request, InventoryRequest):
        result = service.record_inventory(request.car_id, request.inventory, actor_id=request.actor_id)
    elif isinstance(request, ReservationAcquireRequest):
        result = service.acquire_reservation(request.car_id, request.reservation, actor_id=request.actor_id)
    elif isinstance(request, ReservationConclusionRequest):
        method = service.release_reservation if command == "reservation-release" else service.invalidate_reservation
        result = method(
            request.car_id,
            request.reservation_id,
            actor_id=request.actor_id,
            at=request.at,
            receipt_sha256=request.receipt_sha256,
            receipt_path=request.receipt_path,
        )
    elif isinstance(request, ReservationRecoverRequest):
        result = service.recover_reservation(request.car_id, request.reservation_id, request.evidence)
    elif isinstance(request, ImplementationAdmitRequest):
        result = service.admit_implementation(
            request.car_id,
            checker_id=request.checker_id,
            implementation_sha=request.implementation_sha,
            expected_base_git_sha=request.expected_base_git_sha,
            expected_upstream_git_sha=request.expected_upstream_git_sha,
            report=request.report,
            receipt=request.receipt,
            commands=request.commands,
            at=request.at,
        )
    elif isinstance(request, IntegrateRequest):
        result = service.integrate(
            request.car_id,
            integrator_id=request.integrator_id,
            integration_sha=request.integration_sha,
            expected_implementation_sha=request.expected_implementation_sha,
            receipt=request.receipt,
            at=request.at,
        )
    elif isinstance(request, AspectCertifyRequest):
        result = service.certify_aspect(
            request.car_id, checker_id=request.checker_id, report=request.report, receipt=request.receipt, at=request.at
        )
    elif isinstance(request, AddendumRecordRequest):
        result = service.record_addendum(request.addendum)
    elif isinstance(request, ParentCertifyRequest):
        result = service.certify_parent(
            checker_id=request.checker_id, revision=request.revision, report=request.report, receipt=request.receipt
        )
    else:
        raise LedgerRefusal(f"unsupported transition command {command!r}")
    if request.mirror_url is not None:
        result = result.model_copy(update={"mirror": Mirror(url=request.mirror_url)})
    return result


def main(argv: list[str] | None = None) -> int:
    """Execute one ledger command.

    Args:
        argv: Optional explicit arguments.

    Returns:
        Process exit code.
    """
    args = parser().parse_args(argv)
    try:
        runtime = PortfolioLedgerRuntime(evidence_root=args.evidence_root, ledger_path=args.ledger, lock_path=args.lock)
        if args.command == "initialize":
            request: BaseModel | None = request_json(args.request, args.command, PortfolioLedger)
        elif args.command == "restore":
            request = request_json(args.request, args.command, RestoreRequest)
        elif args.command in {"show", "verify-mirror"}:
            request = None
        else:
            request_model = TRANSITION_REQUEST_MODELS[args.command]
            request = request_json(args.request, args.command, request_model)
        ledger = runtime.execute(args.command, request)
        output_json(ledger.model_dump(mode="json"))
    except LedgerRefusal as error:
        output_json(
            {"error": {"category": error.category, "code": error.code, "message": str(error)}}, stream=sys.stderr
        )
        return 1
    except (KeyError, OSError, TypeError, ValueError) as error:
        output_json(
            {"error": {"category": "contract", "code": "invalid_request", "message": str(error)}}, stream=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
