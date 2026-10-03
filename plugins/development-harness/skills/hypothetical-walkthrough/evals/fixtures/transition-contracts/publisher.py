"""Publish the parsed CLI values as an event."""

from __future__ import annotations

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    return parser


def publish(argv: list[str]) -> dict[str, str | int]:
    """Parse arguments and construct an event.

    Returns:
        Parsed event.
    """
    args = build_parser().parse_args(argv)
    return {"job_id": args.job_id, "attempt": args.attempt}


if __name__ == "__main__":
    print(json.dumps(publish(sys.argv[1:])))
