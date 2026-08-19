"""Canonical status-label registry -- single source of truth for GitHub ``status:*`` labels.

``gh_client.py`` previously scattered ~19 raw ``"status:X"`` string literals across its
label-management functions (``apply_status_in_progress``, ``apply_status_verified``,
``apply_status_groomed``, ``apply_status_blocked``, ``_pick_primary_status_label``, ...)
with no shared source of truth, and a second independent copy of ``status:verified`` was
hardcoded in ``.github/workflows/quality-gate-audit.yml``'s inline JS. This module exists
to prevent a renamed or added status label from drifting silently across any of them (#3004).

Dependency direction (must remain acyclic):
    status_registry <- gh_client (and any other consumer)

This module imports nothing from the rest of ``backlog_core`` — it is a leaf, so any
module may import from it without risking a cycle. Mirrors the shape of
``section_registry.py`` (canonical enum + drift-detection test), simplified because
status labels have no display-heading or alias-recovery concerns of their own — the
enum value IS the literal GitHub label name.

How to add a new canonical status label
-----------------------------------------
1. Append a member to :class:`StatusLabel` — the value is the literal GitHub label
   name (e.g. ``ARCHIVED = "status:archived"``).
2. Use the new member everywhere the label is referenced instead of a raw string.
   ``plugins/development-harness/tests/test_status_label_registry_drift.py`` fails
   the build if a raw ``"status:X"`` literal appears in ``gh_client.py`` or the
   quality-gate-audit workflow that is not a registered member.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = ["STATUS_LABEL_PREFIX", "StatusLabel"]

# Shared namespace prefix for every status label — used by callers that filter an
# issue's labels down to "any status label" rather than checking a specific one.
STATUS_LABEL_PREFIX: Final[str] = "status:"


class StatusLabel(StrEnum):
    """Canonical ``status:*`` GitHub label values used across the backlog lifecycle.

    Append new members here when registering a new status label — see the module
    docstring's "How to add a new canonical status label" steps.
    """

    NEEDS_GROOMING = "status:needs-grooming"
    IN_PROGRESS = "status:in-progress"
    GROOMED = "status:groomed"
    VERIFIED = "status:verified"
    BLOCKED = "status:blocked"
