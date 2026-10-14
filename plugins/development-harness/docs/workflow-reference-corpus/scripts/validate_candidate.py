# /// script
# requires-python = ">=3.11"
# ///
"""Validate a blind candidate against its non-gold recursive output contract."""

from __future__ import annotations

import argparse
import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
candidate_schema_failures = cast(
    "Callable[[dict[str, Any], dict[str, Any]], list[dict[str, str]]]",
    runpy.run_path(str(Path(__file__).with_name("candidate_schema.py")))["candidate_schema_failures"],
)


def load(path: Path) -> dict[str, Any]:
    """Read one JSON object.

    Returns:
        Parsed JSON object.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def main() -> None:
    """Emit one structured pass or failure result for a candidate file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "blind-candidate-contract.json")
    arguments = parser.parse_args()
    failures = candidate_schema_failures(load(arguments.candidate), load(arguments.contract))
    result = {"status": "passed" if not failures else "failed", "schema_failures": failures}
    print(json.dumps(result, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
