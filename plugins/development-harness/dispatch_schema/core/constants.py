"""Shared constants for dispatch_schema.

Kept in a leaf module (no imports from backlog_core or dispatch_schema.__init__)
so both dispatch_schema.core.validator and backlog_core.operations can import
from here without triggering a circular dependency.
"""

# Minimum conflict-group size for co-wave placement checks to be meaningful.
from __future__ import annotations

MIN_CONFLICT_GROUP_SIZE = 2
