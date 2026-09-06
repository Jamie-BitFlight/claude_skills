"""Guards ``artifact_type=`` argument values against the ArtifactType enum.

Agents and skills pass ``artifact_type="..."`` to ``artifact_register``,
``artifact_read``, ``artifact_get``, and ``artifact_list``. The value is validated
against ``backlog_core.models.ArtifactType`` at the wire boundary, so an unregistered
spelling in skill prose sends an agent to a call that fails at runtime — after the
agent has already done the work it was trying to store.

Scope is deliberately the ``artifact_type=`` argument only, NOT the ``ARTIFACT:LABEL``
vocabulary used in skill prose. Those labels (``ARTIFACT:DISCOVERY``,
``ARTIFACT:EXECUTION``, ...) name SAM pipeline stages, and their producers and
consumers were verified to agree: ``ARTIFACT:EXECUTION`` is written to a SAM task
section by ``execution/SKILL.md`` and read back from the same section by
``forensic-review/SKILL.md``. Stage labels and wire types are separate vocabularies,
and conflating them would flag correct code.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from backlog_core.models import ArtifactType

_CANONICAL_TYPES = {artifact_type.value for artifact_type in ArtifactType}

# Matches artifact_type="value" / artifact_type='value', the shape used in every
# MCP call example in skills/ and agents/.
_ARTIFACT_TYPE_RE = re.compile(r"""artifact_type\s*=\s*["']([A-Za-z0-9_-]+)["']""")

# Template placeholders, not literal type values.
_PLACEHOLDERS = frozenset({"artifact_type", "type", "TYPE", "value"})

_SEARCH_ROOTS = ("skills", "agents")


def _collect_artifact_types() -> dict[str, list[str]]:
    """Map each artifact_type value passed in prose to the paths that pass it.

    Returns:
        Type value to sorted list of plugin-relative paths using it.
    """
    found: dict[str, set[str]] = defaultdict(set)
    for root in _SEARCH_ROOTS:
        for path in sorted((_PLUGIN_ROOT / root).rglob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in _ARTIFACT_TYPE_RE.finditer(text):
                value = match.group(1)
                if value in _PLACEHOLDERS:
                    continue
                found[value].add(str(path.relative_to(_PLUGIN_ROOT)))
    return {value: sorted(paths) for value, paths in found.items()}


def test_every_artifact_type_argument_is_a_registered_enum_value() -> None:
    """Every artifact_type= value in skills/ or agents/ is a member of ArtifactType."""
    found = _collect_artifact_types()
    unregistered = {value: paths for value, paths in found.items() if value not in _CANONICAL_TYPES}

    assert not unregistered, (
        "artifact_type values not registered in ArtifactType:\n"
        + "\n".join(f"  {value!r} — {', '.join(paths)}" for value, paths in sorted(unregistered.items()))
        + f"\n\nRegistered values: {sorted(_CANONICAL_TYPES)}"
    )
