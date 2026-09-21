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
from typing import TextIO

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from dh_core.portfolio_ledger import (
    Addendum,
    CommandEvidence,
    EvidenceReceipt,
    Inventory,
    LedgerRefusal,
    LedgerStore,
    Mirror,
    PortfolioLedger,
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


def parser() -> argparse.ArgumentParser:
    """Build the command parser.

    Returns:
        Configured parser.
    """
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--ledger", type=Path, required=True)
    result.add_argument("--lock", type=Path, required=True)
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


def request_json(path: Path | None, command: str) -> dict[str, object]:
    """Read a complete request object for one mutating command.

    Args:
        path: Request file path.
        command: Command requiring the file.

    Returns:
        Parsed request object.

    Raises:
        LedgerRefusal: When no request path or a non-object payload is provided.
    """
    if path is None:
        raise LedgerRefusal(f"{command} requires --request")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LedgerRefusal("request JSON must be an object")
    return payload


def instant(value: object) -> datetime:
    """Parse one ISO-8601 request instant without losing timezone data.

    Returns:
        Parsed instant.
    """
    if not isinstance(value, str):
        raise LedgerRefusal("request instant must be an ISO-8601 string")
    return datetime.fromisoformat(value)


def transition(
    command: str, ledger: PortfolioLedger, request: dict[str, object], *, evidence_root: Path
) -> PortfolioLedger:
    """Dispatch one complete request through the public transition service.

    Returns:
        Transitioned ledger.
    """
    service = PortfolioLedgerService(ledger, evidence_root=evidence_root)
    if command == "inventory":
        result = service.record_inventory(
            str(request["car_id"]), Inventory.model_validate(request["inventory"]), actor_id=str(request["actor_id"])
        )
    elif command == "reservation-acquire":
        result = service.acquire_reservation(
            str(request["car_id"]),
            Reservation.model_validate(request["reservation"]),
            actor_id=str(request["actor_id"]),
        )
    elif command in {"reservation-release", "reservation-invalidate"}:
        method = service.release_reservation if command == "reservation-release" else service.invalidate_reservation
        result = method(
            str(request["car_id"]),
            str(request["reservation_id"]),
            actor_id=str(request["actor_id"]),
            at=instant(request["at"]),
            receipt_sha256=str(request["receipt_sha256"]),
            receipt_path=str(request["receipt_path"]),
        )
    elif command == "reservation-recover":
        result = service.recover_reservation(
            str(request["car_id"]), str(request["reservation_id"]), RecoveryEvidence.model_validate(request["evidence"])
        )
    elif command == "implementation-admit":
        command_payload = request["commands"]
        if not isinstance(command_payload, list):
            raise LedgerRefusal("commands must be a JSON array")
        result = service.admit_implementation(
            str(request["car_id"]),
            checker_id=str(request["checker_id"]),
            implementation_sha=str(request["implementation_sha"]),
            expected_base_git_sha=str(request["expected_base_git_sha"]),
            expected_upstream_git_sha=str(request["expected_upstream_git_sha"]),
            report=str(request["report"]),
            receipt=EvidenceReceipt.model_validate(request["receipt"]),
            commands=[CommandEvidence.model_validate(item) for item in command_payload],
            at=instant(request["at"]),
        )
    elif command == "integrate":
        result = service.integrate(
            str(request["car_id"]),
            integrator_id=str(request["integrator_id"]),
            integration_sha=str(request["integration_sha"]),
            expected_implementation_sha=str(request["expected_implementation_sha"]),
            receipt=EvidenceReceipt.model_validate(request["receipt"]),
            at=instant(request["at"]),
        )
    elif command == "aspect-certify":
        result = service.certify_aspect(
            str(request["car_id"]),
            checker_id=str(request["checker_id"]),
            report=str(request["report"]),
            receipt=EvidenceReceipt.model_validate(request["receipt"]),
            at=instant(request["at"]),
        )
    elif command == "addendum-record":
        result = service.record_addendum(Addendum.model_validate(request["addendum"]))
    elif command == "parent-certify":
        result = service.certify_parent(
            checker_id=str(request["checker_id"]),
            revision=str(request["revision"]),
            report=str(request["report"]),
            receipt=EvidenceReceipt.model_validate(request["receipt"]),
        )
    else:
        raise LedgerRefusal(f"unsupported transition command {command!r}")
    mirror_url = request.get("mirror_url")
    if mirror_url is not None:
        result = result.model_copy(update={"mirror": Mirror(url=str(mirror_url))})
    return result


def main(argv: list[str] | None = None) -> int:
    """Execute one ledger command.

    Args:
        argv: Optional explicit arguments.

    Returns:
        Process exit code.
    """
    args = parser().parse_args(argv)
    store = LedgerStore(args.ledger, args.lock, evidence_root=args.evidence_root)
    try:
        if args.command == "initialize":
            ledger = store.initialize(PortfolioLedger.model_validate(request_json(args.request, args.command)))
        elif args.command == "restore":
            request = request_json(args.request, args.command)
            ledger = store.restore_from_mirror(
                mirror_url=str(request["mirror_url"]), expected_sha256=str(request["expected_sha256"])
            )
        else:
            ledger = store.read()
            if ledger.mirror.url is not None:
                ledger = store.verify_mirror()
            if args.command == "verify-mirror":
                ledger = store.verify_mirror()
            elif args.command != "show":
                expected_digest = ledger.ledger_sha256
                ledger = transition(
                    args.command, ledger, request_json(args.request, args.command), evidence_root=args.evidence_root
                )
                ledger = store.write_transition(ledger, expected_ledger_sha256=expected_digest)
        output_json(ledger.model_dump(mode="json"))
    except (KeyError, LedgerRefusal, OSError, TypeError, ValueError) as error:
        output_json({"error": str(error), "error_type": type(error).__name__}, stream=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
