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
from pathlib import Path
from typing import TextIO, TypeVar

from pydantic import BaseModel

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from dh_core.portfolio_ledger import (
    CANONICAL_LEDGER_PATH,
    CANONICAL_LOCK_PATH,
    RUNTIME_REQUEST_MODELS,
    LedgerRefusal,
    PortfolioLedger,
    PortfolioLedgerRuntime,
    RestoreRequest,
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
            request_model = RUNTIME_REQUEST_MODELS[args.command]
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
