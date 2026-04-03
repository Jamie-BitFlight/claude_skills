"""Backlog MCP package — core logic and FastMCP server."""

from __future__ import annotations

from ._branch_delegates import (
    create_integration_branch,
    delete_integration_branch,
    get_integration_branch_status,
    list_integration_branches,
    merge_integration_branch,
)
from .models import BranchConflictError, BranchInfo, MergeResult

__all__ = [
    "BranchConflictError",
    "BranchInfo",
    "MergeResult",
    "create_integration_branch",
    "delete_integration_branch",
    "get_integration_branch_status",
    "list_integration_branches",
    "merge_integration_branch",
]
