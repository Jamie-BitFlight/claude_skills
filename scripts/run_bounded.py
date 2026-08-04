#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Run one command with a timeout and terminate its process group on expiry."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys

TIMEOUT_EXIT_CODE = 124
TERMINATION_GRACE_SECONDS = 0.5


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Maximum command duration before process-tree termination. Default: 5.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def terminate_process_tree(process: subprocess.Popen[object]) -> None:
    """Terminate the isolated process group, escalating after a short grace period."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    else:
        process.terminate()

    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    else:
        process.kill()
    process.wait()


def run_command(command: list[str], timeout_seconds: float) -> int:
    """Run a command and return its exit status, or 124 after a timeout."""
    if timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be greater than zero")
    if not command:
        raise ValueError("A command is required after --")

    process = subprocess.Popen(
        command,
        start_new_session=os.name == "posix",
    )
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        terminate_process_tree(process)
        print(f"timed out after {timeout_seconds:g} seconds", file=sys.stderr)
        return TIMEOUT_EXIT_CODE


def main() -> int:
    """Run the parsed command within the selected timeout."""
    args = create_parser().parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        return run_command(command, args.timeout_seconds)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
