"""Guards against status-label drift between raw string literals and StatusLabel (#3004).

``backlog_core/gh_client.py`` previously defined an under-used ``DH_LABELS`` dict plus
~19 raw ``"status:X"`` string literals scattered through label-management functions
(``apply_status_in_progress``, ``apply_status_verified``, ``apply_status_groomed``,
``apply_status_blocked``, ``_pick_primary_status_label``, ...), with no canonical
source of truth. A second, independent copy of one of those labels
(``VERIFIED_LABEL = 'status:verified'``) is hardcoded in
``.github/workflows/quality-gate-audit.yml``'s inline JS. Nothing kept these in sync —
a renamed or added status label could drift silently across any of them.

This test parses ``gh_client.py`` and the workflow file for every ``status:X``-shaped
literal and fails if any is not a member of ``backlog_core.status_registry.StatusLabel``
(mirrors the grep-based drift-detection pattern in
``test_section_name_registry_drift.py``, not a general duplicate-literal linter — see
issue #3004 for why a general linter was rejected).
"""

from __future__ import annotations

import re
from pathlib import Path

from backlog_core.status_registry import StatusLabel

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_ROOT.parent.parent

_STATUS_LABEL_RE = re.compile(r"\bstatus:[a-z][a-z-]*\b")

_CANONICAL_LABELS = {label.value for label in StatusLabel}


def _scan(path: Path) -> set[str]:
    return set(_STATUS_LABEL_RE.findall(path.read_text(encoding="utf-8")))


def test_gh_client_status_literals_are_canonical() -> None:
    """Every ``status:X`` literal in gh_client.py must be a registered StatusLabel member.

    Tests: backlog_core.status_registry.StatusLabel completeness against real usage
    How: Regex-scan gh_client.py for ``status:X``-shaped substrings, diff against the
         canonical StatusLabel value set.
    Why: A status label used in code but never registered in StatusLabel is exactly
         the drift #3004 describes — this fails loudly instead of silently.
    """
    found = _scan(_PLUGIN_ROOT / "backlog_core" / "gh_client.py")
    unknown = found - _CANONICAL_LABELS
    assert not unknown, (
        f"gh_client.py references status label(s) not registered in StatusLabel: {sorted(unknown)}. "
        "Register them in backlog_core/status_registry.py or fix the typo."
    )


def test_quality_gate_audit_workflow_verified_label_matches_registry() -> None:
    """The workflow's hardcoded VERIFIED_LABEL JS constant must match StatusLabel.VERIFIED.

    Tests: .github/workflows/quality-gate-audit.yml's ``VERIFIED_LABEL`` constant
    How: Regex-scan the workflow YAML for ``status:X``-shaped substrings, assert
         ``StatusLabel.VERIFIED.value`` is present and every match is canonical.
    Why: This is the cross-language duplicate #3004 flags — a Python-only registry
         does not catch a JS-side rename on its own; this test is the catch.
    """
    found = _scan(_REPO_ROOT / ".github" / "workflows" / "quality-gate-audit.yml")
    assert StatusLabel.VERIFIED.value in found, (
        f"Expected quality-gate-audit.yml to reference {StatusLabel.VERIFIED.value!r}, found {sorted(found)}"
    )
    unknown = found - _CANONICAL_LABELS
    assert not unknown, f"quality-gate-audit.yml references status label(s) not in StatusLabel: {sorted(unknown)}"
