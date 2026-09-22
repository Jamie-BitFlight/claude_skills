#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Validate and execute an accounted local-rebase plan."""

from __future__ import annotations

from rebase_cli import main
from rebase_contracts import Disposition, RebasePlan
from rebase_models import MergePolicy

__all__ = ["Disposition", "MergePolicy", "RebasePlan", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
