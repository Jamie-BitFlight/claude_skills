"""Unified backend protocol for the development harness.

This module defines the data-structure interface that all backends implement.
The protocol is agnostic to storage — a backend can be file-based (local YAML),
SQL, Gist, noSQL, Jira, or any other storage. The operations layer
(``dh_core.operations``) calls methods on this protocol; it never assumes
a specific storage implementation.

During the incremental extraction, this module re-exports the existing
backend protocols so Phase 1 has concrete types to work against. The end
state is a single unified ``DHBackend`` protocol (or a composite of
sub-protocols — see open question #3 in the plan).

Dependency direction (must remain acyclic):
    models <- protocols <- operations <- frontends
    protocols does NOT import from: operations, server, cli, or any backend impl
"""

from __future__ import annotations

from sam_schema.core.task_backend import TaskBackend

__all__ = ["TaskBackend"]
