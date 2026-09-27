"""Guards against status-label drift between raw string literals and StatusLabel (#3004).

``backlog_core/gh_client.py`` previously defined an under-used ``DH_LABELS`` dict plus
~19 raw ``"status:X"`` string literals scattered through label-management functions
(``apply_status_in_progress``, ``apply_status_verified``, ``apply_status_groomed``,
``apply_status_blocked``, primary-status selection, ...), with no canonical
source of truth. A second, independent copy of one of those labels
(``VERIFIED_LABEL = 'status:verified'``) is hardcoded in the host repository's
``.github/workflows/quality-gate-audit.yml``; the repository's root
``tests/test_quality_gate_audit_status_labels.py`` guards that copy, because this
plugin's suite also runs standalone, where the workflow does not exist.
``backlog_core/server.py`` and ``backlog_core/operations.py`` also reference concrete ``status:X`` labels in
their MCP tool/CLI descriptions and docstrings (e.g. "Filter by status value e.g.
'status:in-progress'") — an agent reads these strings to decide what to pass back
in, so a rename that only touches ``StatusLabel`` would silently mislead callers.
Nothing kept any of these in sync — a renamed or added status label could drift
silently across any of them.

This test parses ``gh_client.py``, ``server.py`` and ``operations.py`` for every
``status:X``-shaped literal and fails if any is not a member of ``backlog_core.status_registry.StatusLabel`` (mirrors the grep-based drift-detection
pattern in ``test_section_name_registry_drift.py``, not a general duplicate-literal
linter — see issue #3004 for why a general linter was rejected). The regex requires a
lowercase word immediately after the colon, so generic GitHub-state mentions like
``status:open``/``status:closed`` (issue open/closed state, not a ``StatusLabel``
member) match the pattern shape but are exercised the same as any other literal: they
must also be registered in ``StatusLabel`` or the test fails, prompting a deliberate
decision (register it, or reword the doc to not look like a label) rather than a
silent scope gap.
"""

from __future__ import annotations

import re
from pathlib import Path

from backlog_core.status_registry import StatusLabel

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

_STATUS_LABEL_RE = re.compile(r"\bstatus:[a-z][a-z-]*\b")

_CANONICAL_LABELS = {label.value for label in StatusLabel}

# Every backlog_core module known to reference concrete status:X label literals —
# in label-management code (gh_client.py) or in agent-facing tool/CLI descriptions
# and docstrings (server.py, operations.py). Extend this tuple, not the regex, when
# a new module starts mentioning status:X literals.
_SCANNED_MODULES = ("gh_client.py", "server.py", "operations.py")


def _scan(path: Path) -> set[str]:
    return set(_STATUS_LABEL_RE.findall(path.read_text(encoding="utf-8")))


def test_backlog_core_status_literals_are_canonical() -> None:
    """Every ``status:X`` literal in backlog_core must be a registered StatusLabel member.

    Tests: backlog_core.status_registry.StatusLabel completeness against real usage
    How: Regex-scan gh_client.py, server.py, and operations.py for ``status:X``-shaped
         substrings, diff against the canonical StatusLabel value set.
    Why: A status label used in code, an MCP tool description, or a docstring but
         never registered in StatusLabel is exactly the drift #3004 describes — this
         fails loudly instead of silently. server.py and operations.py are in scope
         because their ``status:X`` mentions are user/agent-facing documentation an
         agent reads to decide what value to pass back — a stale copy there is as
         misleading as a stale literal in gh_client.py itself.
    """
    for module in _SCANNED_MODULES:
        found = _scan(_PLUGIN_ROOT / "backlog_core" / module)
        unknown = found - _CANONICAL_LABELS
        assert not unknown, (
            f"{module} references status label(s) not registered in StatusLabel: {sorted(unknown)}. "
            "Register them in backlog_core/status_registry.py or fix the typo."
        )
