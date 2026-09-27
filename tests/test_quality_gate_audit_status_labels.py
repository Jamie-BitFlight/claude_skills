"""Guards the status label hardcoded in ``quality-gate-audit.yml`` against dh's ``StatusLabel`` (#3004).

The workflow's inline JS keeps its own copy of ``status:verified``. The workflow belongs
to this repository, not to the development-harness plugin, so this consumer-side check
lives here rather than in the plugin's standalone suite. ``StatusLabel`` is loaded from
its file so the check does not depend on the root ``pythonpath`` listing the plugin.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
_STATUS_LABEL_RE = re.compile(r"\bstatus:[a-z][a-z-]*\b")


def _load_status_registry() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "dh_status_registry_under_test", ROOT / "plugins/development-harness/backlog_core/status_registry.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_gate_audit_workflow_verified_label_matches_registry() -> None:
    """The workflow's hardcoded VERIFIED_LABEL JS constant must match StatusLabel.VERIFIED.

    Tests: .github/workflows/quality-gate-audit.yml's ``VERIFIED_LABEL`` constant
    How: Regex-scan the workflow YAML for ``status:X``-shaped substrings, assert
         ``StatusLabel.VERIFIED.value`` is present and every match is canonical.
    Why: This is the cross-language duplicate #3004 flags — a Python-only registry
         does not catch a JS-side rename on its own; this test is the catch.
    """
    status_label = _load_status_registry().StatusLabel
    canonical = {label.value for label in status_label}
    found = set(
        _STATUS_LABEL_RE.findall((ROOT / ".github/workflows/quality-gate-audit.yml").read_text(encoding="utf-8"))
    )
    assert status_label.VERIFIED.value in found, (
        f"Expected quality-gate-audit.yml to reference {status_label.VERIFIED.value!r}, found {sorted(found)}"
    )
    unknown = found - canonical
    assert not unknown, f"quality-gate-audit.yml references status label(s) not in StatusLabel: {sorted(unknown)}"
